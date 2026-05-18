# Seeds — Seed V4 (Centre d'Action)

> Sprint M2-4.1.bis. Couvre le seed des tables V4 introduites par la migration
> `m2s2v4`. Le seed HELIOS legacy (`python -m services.demo_seed`) reste
> documenté dans le `README.md` (§ Données de demo).

## Objet

`backend/seeds/v4_seed.py` seede un jeu **minimal** de données V4 :
3 `action_center_items`, un par état de cycle de vie représentatif.

| slug | `kind` | `lifecycle_state` | `priority_bracket` | clôture |
|---|---|---|---|---|
| `ouvert` | `anomaly` | `new` | P1 | — |
| `en-cours` | `action` | `in_progress` | P2 | — |
| `resolu` | `action` | `closed` | P2 | `closed_at` + `closure_reason='resolved'` |

Le périmètre est volontairement réduit (M2-4.1.bis) : les 7 autres tables V4
ne sont pas seedées (prévu sprints ultérieurs).

## Prérequis

1. **Migration `m2s2v4` appliquée** — les 8 tables V4 doivent exister :
   ```bash
   cd backend && alembic upgrade m2s2v4
   ```
2. **Organisation cible existante** — le seed V4 ne crée **pas** d'organisation.
   Par défaut il cible `org_id=1` (HELIOS). Lancer le seed HELIOS au préalable
   si la DB est vierge :
   ```bash
   cd backend && python -m services.demo_seed --pack helios --size S
   ```
   Si l'organisation est absente, le seed lève `SeedError` (aucun item inséré).

## Exécution (CLI)

```bash
cd backend
python -m seeds.v4_seed              # org HELIOS id=1 (défaut)
python -m seeds.v4_seed --org-id 2   # autre organisation
```

Sortie : `seed V4 — org_id=1 · items créés=3 · ignorés (déjà présents)=0`.

Usage programmatique :

```python
from database.connection import SessionLocal
from seeds.v4_seed import seed_v4_minimal

db = SessionLocal()
report = seed_v4_minimal(db, org_id=1)   # SeedReport(org_id, items_created, items_skipped)
db.close()
```

## Idempotence

Chaque `action_center_item` porte une **PK UUID5 déterministe** (dérivée d'un
slug stable, cf. `v4_seed_constants.seed_item_uuid`). Un item déjà présent est
ignoré — équivalent portable de `INSERT OR IGNORE`, sans SQL dialecte-spécifique.

Conséquence : **relancer le seed est sûr**. Deux runs consécutifs produisent un
`COUNT` identique, zéro doublon. Le second run rapporte `items_created=0,
items_skipped=3`.

## FK `organisation_id` ON DELETE RESTRICT

`action_center_items.organisation_id` est une FK Integer vers `organisations.id`
avec `ON DELETE RESTRICT` (ADR-009 Option D, M2-4.1). Tant que des items V4
référencent une organisation, sa suppression est **refusée** (`IntegrityError`).

Cette contrainte n'est effective sous SQLite que si `PRAGMA foreign_keys=ON` —
garanti pour toute session de production par `database/connection.py`.

## Cycle migration + seed

Le seed survit à un cycle complet de migration :

```bash
cd backend
alembic downgrade p37bilan   # supprime les 8 tables V4
alembic upgrade m2s2v4       # les recrée (vides)
python -m seeds.v4_seed      # re-seede à neuf
```

## Tests

`backend/tests/unit/test_v4_seed.py` — 8 tests : idempotence, PK déterministes,
`SeedError` org absente, `chk_closure_consistency`, FK RESTRICT effective,
PRAGMA de production, intégration `BaseRepositoryV4` org-scopée.
