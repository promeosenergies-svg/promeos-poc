# V119.3 — Plan migration PostgreSQL + pg_trgm pour le référentiel Sirene

**Contexte** : SQLite ne tient pas la charge d'un import full du stock INSEE (≈35M établissements + 25M unités légales). Pour le pilote production, migration vers PostgreSQL avec extension `pg_trgm` pour la recherche full-text par nom.

## 1. Pourquoi PostgreSQL maintenant ?

| Critère | SQLite | PostgreSQL |
|---------|--------|-----------|
| Volume max raisonnable | ~1M lignes | 100M+ lignes |
| Recherche full-text | `ILIKE` (table scan) | `pg_trgm` (index GIN) |
| Concurrence | WAL serialise | MVCC parallèle |
| Backup live | Fichier copié | `pg_dump`/streaming |
| Cron import simultané | Lock global | Pas de blocage |

**Trigger** : dès le premier client pilote avec import full, SQLite explose en taille (>15 GB) et la recherche par nom prend >5s.

## 2. Migration plan (3 étapes)

### Étape 1 — Provisioning (1h)
- Postgres 16 dédié (ex: Supabase, Neon, Scaleway, ou managed AWS RDS)
- Connection string dans `DATABASE_URL`
- Pool size : `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`

### Étape 2 — Schema bootstrap (30min)
```bash
# Sur PostgreSQL frais
cd backend
DATABASE_URL=postgresql://... python -c "
from database.connection import engine
from models.base import Base
import models  # noqa: F401
Base.metadata.create_all(bind=engine)
"
DATABASE_URL=postgresql://... python -m alembic upgrade head
```

### Étape 3 — Activation pg_trgm (15min)
```sql
-- À exécuter UNE FOIS sur la base prod
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Index GIN sur denomination (recherche par nom)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sirene_ul_denomination_trgm
  ON sirene_unites_legales USING gin (denomination gin_trgm_ops);

-- Index GIN sur libelle_commune (recherche par ville)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sirene_etab_commune_trgm
  ON sirene_etablissements USING gin (libelle_commune gin_trgm_ops);

-- Index GIN sur enseigne (recherche par enseigne)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sirene_etab_enseigne_trgm
  ON sirene_etablissements USING gin (enseigne gin_trgm_ops);
```

## 3. Code à adapter

### A. Recherche `routes/sirene.py::search_sirene`
**Avant** (SQLite-friendly, table scan sur PostgreSQL) :
```python
query = query.filter(
    or_(
        SireneUniteLegale.denomination.ilike(pattern, escape="\\"),
        SireneUniteLegale.sigle.ilike(pattern, escape="\\"),
    )
)
```

**Après** (PostgreSQL `pg_trgm`, index GIN) :
```python
from sqlalchemy import func

# Sur PostgreSQL : utilise l'opérateur similarity (%)
if engine.dialect.name == "postgresql":
    query = query.filter(
        func.similarity(SireneUniteLegale.denomination, q_clean) > 0.3
    ).order_by(func.similarity(SireneUniteLegale.denomination, q_clean).desc())
else:
    # Fallback SQLite : ILIKE
    query = query.filter(SireneUniteLegale.denomination.ilike(pattern, escape="\\"))
```

**Recommandation** : créer un helper `services/sirene_search.py::similarity_filter()` qui dispatche selon le dialect.

### B. Import bulk : passer à `INSERT ... ON CONFLICT`
**Avant** : ORM-based upsert (SQLAlchemy `_upsert_batch`)
```python
existing = db.query(model).filter(key.in_(keys)).all()  # SELECT
for row in batch:
    if key in existing: setattr(...)  # UPDATE one by one
    else: db.add(model(**row))         # INSERT one by one
```
→ ~35K SELECT/INSERT round-trips pour 35M rows = plusieurs heures.

**Après** : SQL natif PostgreSQL
```python
from sqlalchemy.dialects.postgresql import insert

stmt = insert(SireneUniteLegale).values(batch)
stmt = stmt.on_conflict_do_update(
    index_elements=['siren'],
    set_={c.name: c for c in stmt.excluded if c.name != 'siren'}
)
db.execute(stmt)
```
→ 1 SQL statement par batch de 1000 rows = ~35K statements total = quelques minutes.

**Gain attendu** : import full 25M UL + 35M etabs = **~30 min** au lieu de **~6h** sur SQLite.

### C. Partitionnement `sirene_etablissements`
Pour les requêtes par CP, partitionner par les 2 premiers chiffres du `code_postal` :
```sql
CREATE TABLE sirene_etablissements (
  ...
) PARTITION BY LIST (substring(code_postal from 1 for 2));

CREATE TABLE sirene_etab_75 PARTITION OF sirene_etablissements FOR VALUES IN ('75');
CREATE TABLE sirene_etab_69 PARTITION OF sirene_etablissements FOR VALUES IN ('69');
-- ... 1 partition par département
```
**Bénéfice** : recherche par CP ne scanne qu'une partition (~3% des données).

**Note** : non bloquant pour V119, à faire seulement si la recherche par CP devient un goulot.

## 4. Plan de bascule (zéro downtime)

1. **Provisioning** PostgreSQL prod (J0)
2. **Bootstrap schema + indexes** (J0)
3. **Import CSV initial** depuis stock du mois (J1, ~30 min)
4. **Tests parallèles** : pointer un environnement staging sur la nouvelle DB et lancer la suite Sirene complète
5. **Bascule DNS/env var** `DATABASE_URL` (J2, downtime <5 min)
6. **Activation cron mensuel** (workflow GitHub Actions V119)
7. **Décommissionnement SQLite** après 1 mois de validation

## 5. Risques connus

| Risque | Mitigation |
|--------|-----------|
| Perte de données pendant la bascule | `pg_dump` SQLite → import PostgreSQL en staging avant prod |
| Différence comportement `ILIKE` vs `pg_trgm` | Tests unitaires `test_sirene_search` couvrent les 2 dialectes |
| `synchronize_session=False` sur les UPDATE bulk | Documenté, pas d'objets ORM live à invalider |
| Timeout cron sur import 35M rows | `timeout-minutes: 180` dans `.github/workflows/sirene-monthly-import.yml` |
| Coût hosting PostgreSQL | ~25-50 EUR/mois pour Supabase/Neon (insignifiant) |

## 6. Roadmap V120+

- [ ] V119.4 : helper `services/sirene_search.py::similarity_filter()` pour dispatch SQLite/PostgreSQL
- [ ] V120 : migration vers `INSERT ... ON CONFLICT` dans `_upsert_batch`
- [ ] V120 : test fixture PostgreSQL via `pytest-postgresql` pour CI
- [ ] V121 : partitionnement `sirene_etablissements` par département (si recherche CP devient lente)
- [ ] V122 : streaming backup `pg_basebackup` + PITR pour les pilotes en production

## 7. Ce que ce document N'EST PAS

- Pas une migration immédiate à exécuter ce sprint (V119)
- Pas un changement de schéma : les modèles Sirene actuels sont **portable PostgreSQL** sans modification
- Pas un blocage : tant qu'on est en démo SQLite, tout fonctionne

**Trigger d'exécution** : premier client pilote qui demande l'import CSV complet.
