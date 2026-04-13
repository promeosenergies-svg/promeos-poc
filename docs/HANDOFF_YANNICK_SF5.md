# Handoff Yannick — Conflit potentiel SF1-SF4 (Yannick) ↔ Sprints 1-8 (Claude)

> **Date** : 2026-04-13
> **Auteur** : Claude (assistant Amine)
> **Destinataire** : Yannick (`feat/enedis-sge-ingestion`) + reviewers PR
> **Statut** : ⚠️ Conflits de merge anticipés — résolution requise avant merge `feat/enedis-sge-ingestion → main`

---

## Contexte

Le commit `779f2885` (PR #203, mergé 2026-04-12) ajoute sur `main` les Sprints 1-8 d'exploitation Enedis :

1. **Pipeline SF5** (promotion staging → fonctionnel) — `backend/data_staging/`
2. **Bridge dual-source** promoted/legacy — `backend/data_staging/bridge.py`
3. **Open Data connector** (conso-sup36/inf36) — `backend/connectors/enedis_opendata.py`
4. **3 services analytics** (load_profile, energy_signature, enedis_benchmarks)
5. **Recommendation Engine** — `backend/services/recommendation_engine.py`
6. **NAF estimator** — `backend/services/naf_estimator.py`
7. **Frontend** dashboard `/admin/enedis-health` + Site360 TabAnalytics

**Yannick** travaille en parallèle sur SF1-SF4 (ingestion brute SGE) sur `feat/enedis-sge-ingestion` avec 30+ commits non encore mergés.

**Mon code dépend du sien** : les promoters lisent les staging tables que ses parsers remplissent.

---

## Conflits de merge anticipés (3 fichiers critiques)

### 1. `backend/routes/enedis.py` ⚠️ CONFLIT LIGNES

**Ce que Yannick a (probablement)** : nouveaux endpoints SF1-SF4 (ingestion, flux-files, stats, peut-être refactor du router).

**Ce que j'ai ajouté (lignes 431-820)** : 7 endpoints SF5 + ODS + monitoring.

#### Endpoints à PRÉSERVER lors de la résolution :

```
POST /api/enedis/promotion/promote          # Trigger run de promotion
GET  /api/enedis/promotion/runs              # List runs
GET  /api/enedis/promotion/runs/{run_id}     # Détail run
GET  /api/enedis/promotion/metrics           # Prometheus metrics
GET  /api/enedis/promotion/health            # Health dashboard
GET  /api/enedis/promotion/backlog           # PRMs non résolus
POST /api/enedis/opendata/refresh            # Trigger ODS sync
GET  /api/enedis/opendata/freshness          # État des données ODS
```

#### Helpers ajoutés (lignes 39-72) à PRÉSERVER :

```python
def _require_auth():
    """Gate auth pour endpoints de promotion (DEMO_MODE = pass-through)."""

_PROMOTION_RATE_LIMIT_WINDOW = 60.0
_last_promotion_trigger: dict[str, float] = {}

def _check_promotion_rate_limit(triggered_by: str = "api"):
    """Rate limit : max 1 run démarré par fenêtre de 60s. Anti DoS."""
```

#### Stratégie de résolution

**Garder les 2 zones** : les endpoints SF1-SF4 de Yannick ET mes endpoints SF5/ODS/monitoring sont **indépendants**. Pas de logique partagée.

```python
# Ordre recommandé dans le fichier après merge :
# 1. router = APIRouter(...)
# 2. _require_auth() + rate limit helpers (mes ajouts)
# 3. Endpoints ingestion (Yannick) : /ingest, /flux-files, /stats
# 4. Endpoints promotion (mes ajouts) : /promotion/*
# 5. Endpoints opendata (mes ajouts) : /opendata/*
```

---

### 2. `backend/database/migrations.py` ⚠️ CONFLIT AJOUT

**Ce que Yannick a** : `_create_enedis_tables()`, `_add_enedis_columns()` pour SF1-SF4.

**Ce que j'ai ajouté** :

```python
# Lignes 106-108 dans run_migrations() :
_create_enedis_opendata_tables(engine)
_create_sf5_promotion_tables(engine)

# Lignes 137-179 :
def _create_sf5_promotion_tables(engine):
    """Create SF5 promotion pipeline tables if missing."""
    from data_staging.models import SF5_TABLES
    # ... crée 6 tables : meter_load_curve, meter_energy_index,
    #    meter_power_peak, promotion_run, promotion_event, unmatched_prm

def _create_enedis_opendata_tables(engine):
    """Create Enedis Open Data benchmark tables if missing."""
    # ... crée 2 tables : enedis_opendata_conso_sup36/inf36
```

#### Stratégie de résolution

**Préserver les 2 appels dans `run_migrations()`** après les migrations SF1-SF4 de Yannick :

```python
def run_migrations(engine):
    # ... migrations existantes ...
    
    # Yannick — SF1-SF4 ingestion
    _create_enedis_tables(engine)
    _add_enedis_columns(engine)
    
    # Claude — SF5 promotion + Open Data (À PRÉSERVER)
    _create_enedis_opendata_tables(engine)
    _create_sf5_promotion_tables(engine)
```

**Les 8 nouvelles tables ne touchent PAS les tables SF1-SF4 de Yannick** (pas de FK, pas de modification de colonnes existantes). Conflit purement positionnel.

---

### 3. `backend/data_ingestion/enedis/models.py` ⚠️ CONFLIT SÉMANTIQUE

**C'est le plus critique.** Yannick refactore probablement ces modèles. Mes promoters dans `backend/data_staging/promoters.py` lisent **des champs précis** sur ces modèles via `getattr()` ou accès direct.

Si Yannick **renomme** ou **supprime** un champ, mes promoters retournent silencieusement `None` ou crashent au runtime.

#### Champs LUS par mes promoters (état actuel, vérifié 2026-04-13)

##### `EnedisFluxMesureR4x` (table `enedis_flux_mesure_r4x`)

Utilisé dans `promote_r4x_row()` :

| Champ | Type actuel | Usage |
|---|---|---|
| `point_id` | VARCHAR(14) | PRM matcher |
| `flux_type` | VARCHAR(10) | source_flux_type |
| `horodatage` | VARCHAR(50) | parse_iso_datetime → MeterLoadCurve.timestamp |
| `valeur_point` | VARCHAR(20) | safe_float → active_power_kw / reactive_*_kvar |
| `statut_point` | VARCHAR(2) | quality_r4x() → quality_score, is_estimated |
| `granularite` | VARCHAR(10) | int(...) → MeterLoadCurve.pas_minutes |
| `grandeur_physique` | VARCHAR(10) | Routing : "EA"→active, "ERI"→reactive_inductive, "ERC"→reactive_capacitive |

##### `EnedisFluxMesureR50` (table `enedis_flux_mesure_r50`)

Utilisé dans `promote_r50_row()` :

| Champ | Type actuel | Usage |
|---|---|---|
| `point_id` | VARCHAR(14) | PRM matcher |
| `horodatage` | VARCHAR(50) | parse_iso_datetime puis **soustrait 30 min** (R50 = fin d'intervalle) |
| `valeur` | VARCHAR(20) | safe_float **en W** puis `/1000` → kW |
| `indice_vraisemblance` | VARCHAR(5) | quality_r50() : "0"=1.00, "1"=0.70 |

##### `EnedisFluxMesureR171` (table `enedis_flux_mesure_r171`)

Utilisé dans `promote_r171_row()` :

| Champ | Type actuel | Usage |
|---|---|---|
| `point_id` | VARCHAR(14) | PRM matcher |
| `grandeur_physique` | VARCHAR(10) | **filtre `EA` only**, sinon skip |
| `unite` | VARCHAR(10) | **filtre `Wh` only**, sinon skip |
| `valeur` | VARCHAR(20) | safe_float → MeterEnergyIndex.value_wh |
| `date_fin` | VARCHAR(50) | parse_date → date_releve |
| `type_calendrier` | VARCHAR(5) | `"D"`→tariff_grid="CT_DIST", autre→"CT" |
| `code_classe_temporelle` | VARCHAR(10) | tariff_class_code (HCE/HPE/etc) |
| `libelle_classe_temporelle` | VARCHAR(100) | tariff_class_label |

##### `EnedisFluxMesureR151` (table `enedis_flux_mesure_r151`)

Utilisé dans `promote_r151_row()` :

| Champ | Type actuel | Usage |
|---|---|---|
| `point_id` | VARCHAR(14) | PRM matcher |
| `type_donnee` | VARCHAR(10) | Routing : `"PMAX"`→MeterPowerPeak, `"CT"`/`"CT_DIST"`→MeterEnergyIndex |
| `valeur` | VARCHAR(20) | safe_float → value_va (PMAX) ou value_wh (index) |
| `date_releve` | VARCHAR(20) | parse_date → date_releve |
| `id_classe_temporelle` | VARCHAR(10) | tariff_class_code (sauf PMAX) |
| `libelle_classe_temporelle` | VARCHAR(100) | tariff_class_label (lu via `getattr`, peut être None) |

##### `EnedisFluxFile` (table `enedis_flux_file`) et `EnedisFluxFileError`

**Mes promoters ne touchent PAS** ces tables. Yannick peut les refactorer librement.

#### Si Yannick renomme un champ

**Symptôme** : tests verts en local (mocks), mais en production le promoter saute silencieusement la row (retourne `None`).

**Détection** : le test E2E `tests/test_sf5_e2e.py::TestE2ESF5Pipeline::test_full_chain_matched_and_promoted` insère des rows avec ces noms exacts via `_seed_r4x_measures()` lignes 87-105. Si Yannick renomme un champ, **ce test casse immédiatement**.

**Action recommandée pour Yannick** : avant de merger, lancer :
```bash
cd backend && python -m pytest tests/test_sf5_e2e.py -v
```

Si le test casse, c'est qu'un nom de champ a changé. La fix est dans `backend/data_staging/promoters.py` (changer `row.<old_name>` → `row.<new_name>`).

---

## Fichiers que mes Sprints 1-8 ont créés (0 conflit, sauf import)

Ces fichiers sont **nouveaux**, donc 0 conflit Git :

### Backend
```
backend/data_staging/__init__.py
backend/data_staging/models.py          # 6 tables SF5 fonctionnelles
backend/data_staging/quality.py         # Mapping statut → quality_score
backend/data_staging/prm_matcher.py     # PRM 14 chiffres → meter.id
backend/data_staging/promoters.py       # ⚠️ DÉPEND des modèles Yannick
backend/data_staging/engine.py          # Moteur de promotion
backend/data_staging/bridge.py          # Dual-source promoted/legacy
backend/data_staging/cli.py             # CLI

backend/services/enedis_benchmarks.py
backend/services/load_profile_service.py
backend/services/energy_signature_service.py  # M (existe avant)
backend/services/naf_estimator.py
backend/services/recommendation_engine.py

backend/models/enedis_opendata.py       # 2 tables Open Data

backend/connectors/enedis_opendata.py   # M (était stub)

backend/utils/parsing.py                # safe_float, parse_date partagés

backend/tests/test_data_staging.py
backend/tests/test_sf5_e2e.py           # ⚠️ Test qui détecte les renames de champs
backend/tests/test_recommendation_engine.py
backend/tests/test_enedis_benchmarks.py
backend/tests/test_load_profile.py
```

### Frontend
```
frontend/src/pages/EnedisPromotionHealthPage.jsx   # /admin/enedis-health
frontend/src/services/api/enedis.js                # Helpers API
frontend/src/components/analytics/LoadProfileCard.jsx       # Sprint A
frontend/src/components/analytics/EnergySignatureCard.jsx   # Sprint A
frontend/src/components/analytics/RecommendationsCard.jsx   # Sprint A
```

### Docs
```
docs/adr/006-enedis-dual-source-bridge.md
docs/adr/007-sf5-quality-first-upsert.md
docs/adr/008-recommendation-engine-rules.md
docs/audit/RAPPORT_ENEDIS_EXPLORATION.md
```

---

## Procédure de merge recommandée pour Yannick

### Étape 1 : Rebase sur main à jour

```bash
git fetch origin
git checkout feat/enedis-sge-ingestion
git rebase origin/main
# OU si trop de conflits :
git merge origin/main
```

### Étape 2 : Résoudre les 3 fichiers critiques

#### `backend/routes/enedis.py`

Garder les 2 zones :
- Endpoints ingestion (les tiens) : `/ingest`, `/flux-files`, `/stats`
- Endpoints promotion + opendata (les miens) : `/promotion/*`, `/opendata/*`

Préserver les helpers `_require_auth` et `_check_promotion_rate_limit` en tête de fichier.

#### `backend/database/migrations.py`

Garder les 2 séquences d'appels dans `run_migrations()` :
```python
_create_enedis_tables(engine)              # Yannick
_add_enedis_columns(engine)                # Yannick
_create_enedis_opendata_tables(engine)     # Claude
_create_sf5_promotion_tables(engine)       # Claude
```

Et les 2 fonctions de création :
- `_create_enedis_tables` (Yannick, lignes ~700+)
- `_create_sf5_promotion_tables` + `_create_enedis_opendata_tables` (Claude, lignes 137-179)

#### `backend/data_ingestion/enedis/models.py`

**C'est ton fichier**. Garde tes refactorings, mais vérifie que les noms de champs listés ci-dessus existent toujours **avec le même nom**.

Si tu en renommes un (ex: `valeur_point` → `value`), il faut aussi modifier :
- `backend/data_staging/promoters.py` (3 fonctions promote_*)
- `backend/tests/test_sf5_e2e.py` (helper `_seed_r4x_measures`)

### Étape 3 : Lancer les 2 suites de tests

```bash
cd backend

# Tests SF1-SF4 (les tiens)
python -m pytest tests/test_enedis_api.py data_ingestion/enedis/tests/ -v

# Tests SF5 (les miens) — DOIT passer après merge
python -m pytest tests/test_sf5_e2e.py tests/test_data_staging.py tests/test_recommendation_engine.py -v
```

**Si `test_sf5_e2e.py` casse**, c'est probablement un rename de champ. Voir section "Champs LUS par mes promoters" ci-dessus.

### Étape 4 : Smoke test live

```bash
# Lancer le backend
cd backend && python main.py

# Vérifier que les 2 ensembles d'endpoints répondent
curl http://localhost:8001/api/enedis/stats              # Yannick
curl http://localhost:8001/api/enedis/promotion/health   # Claude
curl http://localhost:8001/api/enedis/opendata/freshness # Claude
```

---

## Contact

- **Owner code Sprint 1-8 (Claude)** : Amine Ben Amara
- **Branche Yannick** : `feat/enedis-sge-ingestion`
- **PR Sprint 1-8** : #203 (mergée)
- **Spec SF5** : `docs/specs/feature-enedis-sge-5-data-staging.md`
- **ADRs** : `docs/adr/006-008`

En cas de doute sur un champ ou une dépendance, le test `tests/test_sf5_e2e.py` est la source de vérité — il insère des rows avec les noms exacts attendus par les promoters.

---

## Annexe : commandes utiles

```bash
# Lister les fichiers modifiés par mes Sprints 1-8 (sur main)
git diff --name-only 16b3e5b5..779f2885 -- backend/data_staging/ backend/services/ backend/routes/enedis.py backend/database/migrations.py

# Voir les conflits exacts avant merge
git fetch origin
git merge-tree $(git merge-base origin/main feat/enedis-sge-ingestion) origin/main feat/enedis-sge-ingestion | grep "^changed in both\|^added in both"

# Si les modèles changent, vérifier impact promoters
cd backend && python -c "from data_ingestion.enedis.models import EnedisFluxMesureR4x, EnedisFluxMesureR50, EnedisFluxMesureR171, EnedisFluxMesureR151; [print(m.__name__, [c.name for c in m.__table__.columns]) for m in [EnedisFluxMesureR4x, EnedisFluxMesureR50, EnedisFluxMesureR171, EnedisFluxMesureR151]]"
```

Compare la sortie aux tableaux "Champs LUS par mes promoters" ci-dessus. Toute différence sur un champ listé = modification requise dans `data_staging/promoters.py`.
