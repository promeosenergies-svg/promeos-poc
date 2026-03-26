# SF4 — Operationalization Pipeline Enedis SGE — Plan d'implementation

> **Status** : Plan v2 — aligne avec spec v5, pret pour implementation phase par phase
> **Spec** : `docs/specs/feature-enedis-sge-4-operationalization.md`
> **Branche** : `feat/enedis-sge-sf4-operationalization` (depuis `feat/enedis-sge-ingestion`)

## Context

SF1-SF3 ont livre un pipeline d'ingestion complet (decrypt, parse, store) pour 6 types de flux Enedis dans 5 tables staging. 221 tests passent, 91 fichiers reels ingeres. Deux scripts ad-hoc existent mais le pipeline n'a ni CLI propre, ni API REST, ni configuration externalisee, et un bug detruit l'historique d'erreurs au retry.

SF4 rend le pipeline **fiable, complet et auditable** en livrant : config, error history, CLI, API REST, wiring applicatif.

---

## Decisions d'architecture (issues du Q&A)

| Question | Decision | Justification |
|----------|----------|---------------|
| Historique d'erreurs | **Table separee** `enedis_flux_file_error` | Propre, extensible, requetable en SQL directement |
| Compteur de tentatives | **Derive** de `len(flux_file.errors)` — pas de colonne `retry_count` | Pas de desynchronisation, source unique de verite |
| Retry ERROR en batch | **Auto-retry** dans `ingest_directory()` si `len(errors) < MAX_RETRIES` (default 3) | Un seul point d'entree fait tout, pas de fichiers oublies. Garde max_retries empeche les boucles infinies |
| Suivi d'execution | **Table `IngestionRun`** (1 row par execution CLI/API) | Audit trail lisible, `LastIngestion` = latest completed run |
| Session API | **`Depends(get_db)`** standard | Pipeline commits per-file (by design). Tracabilite via `IngestionRun` |
| Rapport CLI mesures | **Requetes DB post-ingestion** (pattern `ingest_real_db.py`) | `ingest_directory()` retourne des compteurs de fichiers, pas de mesures. `_print_report()` calcule les volumes via queries sur les tables staging |
| CLI scope | **Minimaliste** — `ingest` uniquement (+ `--dry-run`) | Les stats restent cote API, evite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ulterieurement |
| Schemas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) | Coherence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Coherent avec les autres tests d'API (`test_bacs_api.py`, etc.) |

---

## Phase 0 — Mise a jour de la spec

**Commit** : `docs(enedis): update SF4 spec v5 with full architecture decisions`

| Fichier | Action |
|---------|--------|
| `docs/specs/feature-enedis-sge-4-operationalization.md` | Aligner sur spec v5 (decisions architecture completes, IngestionRun, MAX_RETRIES, retry batch, session API) |

---

## Phase 1 — Configuration externalisee

**Commit** : `feat(enedis): externalize flux directory config (SF4)`

### Creer

| Fichier | Description |
|---------|-------------|
| `backend/data_ingestion/enedis/config.py` | `get_flux_dir()`, `MAX_RETRIES`, constantes |
| `backend/data_ingestion/enedis/tests/test_config.py` | Tests unitaires |

### Modifier

| Fichier | Modification |
|---------|-------------|
| `.env.example` (racine) | Ajouter `ENEDIS_FLUX_DIR` section External Data Connectors |
| `backend/.env.example` | Ajouter `ENEDIS_FLUX_DIR` |

### Contenu de `config.py`

```python
MAX_RETRIES: int = 3  # Nombre max de tentatives sur un fichier en erreur

def get_flux_dir(override: str | None = None, validate: bool = True) -> Path:
    """Resolve le repertoire de flux Enedis.

    Priorite : override > env var ENEDIS_FLUX_DIR > fallback projet.
    """
```

### Comportement `get_flux_dir()`

```
1. Si override fourni et non vide -> Path(override)
2. Sinon os.environ.get("ENEDIS_FLUX_DIR") -> Path(env_value)
3. Sinon fallback -> Path(__file__).resolve().parents[4] / "flux_enedis"
4. Si validate=True et le path n'est pas un repertoire -> ValueError
```

### Tests

| Classe | Cas |
|--------|-----|
| `TestGetFluxDir` | env var set, env var absent (fallback), override explicite, repertoire inexistant -> ValueError, validate=False bypass |
| `TestMaxRetries` | Constante accessible et correctement typee |

---

## Phase 2 — Modeles d'audit (erreurs + suivi d'execution)

**Commit** : `feat(enedis): add EnedisFluxFileError and IngestionRun models (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/models.py` | + classe `EnedisFluxFileError`, + classe `IngestionRun`, + relation `errors` sur `EnedisFluxFile` |

### Schema `EnedisFluxFileError`

```
Table: enedis_flux_file_error
  id             Integer PK
  flux_file_id   Integer FK -> enedis_flux_file.id (CASCADE)
  error_message  Text NOT NULL
  created_at     DateTime (TimestampMixin)
  updated_at     DateTime (TimestampMixin)

Index: ix_enedis_flux_file_error_flux_file (flux_file_id)
```

Sur `EnedisFluxFile` :
- `errors = relationship("EnedisFluxFileError", ..., order_by=created_at, cascade="all, delete-orphan")`

### Schema `IngestionRun`

```
Table: enedis_ingestion_run
  id                      Integer PK
  started_at              DateTime NOT NULL
  finished_at             DateTime (nullable — null while running)
  directory               String(500) NOT NULL
  recursive               Boolean NOT NULL default True
  dry_run                 Boolean NOT NULL default False
  status                  String(20) NOT NULL default "running"  (running / completed / failed)
  triggered_by            String(10) NOT NULL  (cli / api)
  files_received          Integer default 0
  files_parsed            Integer default 0
  files_skipped           Integer default 0
  files_error             Integer default 0
  files_needs_review      Integer default 0
  files_already_processed Integer default 0
  files_retried           Integer default 0
  files_max_retries       Integer default 0
  error_message           Text (nullable — for run-level errors)
  created_at              DateTime (TimestampMixin)
  updated_at              DateTime (TimestampMixin)
```

### Tests

| Fichier | Cas |
|---------|-----|
| `test_models.py` (extend) | `EnedisFluxFileError` : creation, cascade delete, ordering par `created_at` |
| `test_models.py` (extend) | `IngestionRun` : creation, status transitions, default values, all counter columns |

---

## Phase 3 — Correction audit d'erreurs + retry batch + dry-run dans le pipeline

**Commit** : `fix(enedis): preserve error history, enable batch retry and dry-run (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/pipeline.py` | (1) Fix retry dans `ingest_file()`. (2) Retry ERROR + garde MAX_RETRIES dans `ingest_directory()`. (3) Parametre `dry_run` dans `ingest_directory()`. |

### Changement 1 : Fix du retry dans `ingest_file()`

**Localisation** : le bloc `if existing.status == FluxStatus.ERROR` dans la fonction `ingest_file()` (actuellement un `session.delete(existing)` + `session.flush()`).

**Avant** :
```python
if existing.status == FluxStatus.ERROR:
    session.delete(existing)
    session.flush()
```

**Apres** :
```python
if existing.status == FluxStatus.ERROR:
    _archive_error(session, existing)
    existing.error_message = None
    pre_registered = existing  # reuse same record in-place
```

**Nouveau helper** `_archive_error(session, flux_file)` :
- Si `flux_file.error_message` non vide : creer `EnedisFluxFileError(flux_file_id=flux_file.id, error_message=flux_file.error_message)`
- Sinon : no-op

### Changement 2 : Retry ERROR dans `ingest_directory()`

**Localisation** : Phase 1 de `ingest_directory()`, le bloc `else` apres le check `if existing.status == FluxStatus.RECEIVED` qui compte actuellement tous les autres statuts comme `already_processed`.

**Avant** :
```python
else:
    # Already processed (PARSED/ERROR/SKIPPED/NEEDS_REVIEW)
    counters["already_processed"] += 1
```

**Apres** :
```python
elif existing.status == FluxStatus.ERROR:
    error_count = len(existing.errors)
    if error_count < MAX_RETRIES:
        logger.info("Retrying ERROR file %s (attempt %d/%d)",
                     file_path.name, error_count + 1, MAX_RETRIES)
        to_process.append((file_path, file_hash, existing))
        counters["retried"] += 1
    else:
        logger.info("Skipping %s — max retries reached (%d)",
                     file_path.name, MAX_RETRIES)
        counters["max_retries_reached"] += 1
else:
    counters["already_processed"] += 1
```

**Compteurs ajoutes** dans le dict de retour de `ingest_directory()` :
- `retried: int` — fichiers ERROR retentes dans cette execution
- `max_retries_reached: int` — fichiers ignores car MAX_RETRIES atteint

**Import necessaire** : `from data_ingestion.enedis.config import MAX_RETRIES`

### Changement 3 : Parametre `dry_run` dans `ingest_directory()`

**Signature** : ajouter `dry_run: bool = False` a `ingest_directory()`.

**Comportement** :
- Phase 1 : scan, hash, classify, check DB — identique, mais **pas de commit** des enregistrements RECEIVED, pas de creation de nouveaux records. Seulement compter.
- Phase 2 : **skipped entierement** en mode dry_run
- Retour : meme dict de compteurs (`received` = nombre de fichiers qui seraient traites, `retried` et `max_retries_reached` comme en mode normal, les compteurs de processing a 0)

### Tests

| Fichier | Cas |
|---------|-----|
| `test_pipeline.py` (extend) | `TestErrorHistoryPreserved` : (1) echoue 2x -> 2 entries error history + `len(errors)==2`, (2) echoue puis reussit -> history preservee + status=PARSED, (3) decrypt error puis parse error -> 2 messages distincts |
| `test_pipeline_full.py` (extend) | `TestErrorRetryInBatch` : fichier ERROR dans `ingest_directory()` est retente automatiquement, history preservee. Fichier avec `MAX_RETRIES` atteint est ignore (compteur `max_retries_reached`). |
| `test_pipeline.py` (extend) | `TestDryRun` : `ingest_directory(dry_run=True)` retourne les bons compteurs sans modifier la DB |

---

## Phase 4 — CLI

**Commit** : `feat(enedis): add CLI for ingestion with dry-run and structured report (SF4)`

### Creer

| Fichier | Description |
|---------|-------------|
| `backend/data_ingestion/enedis/cli.py` | `python -m data_ingestion.enedis.cli ingest [OPTIONS]` |
| `backend/data_ingestion/enedis/tests/test_cli.py` | Tests CLI |

### Interface

```
python -m data_ingestion.enedis.cli ingest [--dir PATH] [--recursive] [--dry-run] [--verbose]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--dir PATH` | env var ou fallback | Repertoire source |
| `--recursive` | Active | Scanner les sous-repertoires |
| `--dry-run` | Desactive | Scan + classify sans ingerer |
| `--verbose` | Desactive | Logging DEBUG |

### Architecture

Pattern `argparse` (ref: `services.demo_seed.__main__`).

```
sys.path.insert + load_dotenv
from database import SessionLocal, engine
from database import run_migrations
from models.base import Base

main() -> argparse -> dispatch
  cmd_ingest(args):
    _ensure_tables(engine)            # Base.metadata.create_all() + run_migrations()
    session = SessionLocal()
    run = IngestionRun(triggered_by="cli", directory=..., dry_run=args.dry_run, ...)
    session.add(run) ; session.commit()
    try:
      mode normal  -> get_flux_dir -> load_keys -> ingest_directory(session, ...) -> _print_report
      mode dry-run -> get_flux_dir -> ingest_directory(session, ..., dry_run=True) -> _dry_run_report
      update run (status="completed", counters, finished_at) -> session.commit()
    except Exception:
      run.status = "failed" ; run.error_message = str(exc) ; session.commit()
      sys.exit(1)
    finally:
      session.close()

  _print_report(counters, session, run, duration)
    # Affiche les compteurs de ingest_directory()
    # + requetes DB pour les volumes de mesures par table staging :
    #   session.query(EnedisFluxMesureR4x).count(), etc.
    #   (pattern identique a scripts/ingest_real_db.py)

  _dry_run_report(counters)
    # Affiche received, retried, max_retries_reached, already_processed
```

### Rapport mode normal

```
=== ENEDIS SGE INGESTION REPORT ===
Run #42        triggered_by: cli
Source:          /path/to/flux_enedis (recursive)
Duration:        3.2s
Files received:  45
  parsed:        38
  skipped:       5  (R172: 3, X14: 1, HDM: 1)
  error:         1
  needs_review:  1
Retried:         2  (from previous errors)
Max retries:     0  (skipped — limit reached)
Already processed: 46
Measures stored:
  R4x:    98,432
  R171:   12,310
  R50:     8,450
  R151:    4,654
  TOTAL: 123,846
ERRORS (1):
  ENEDIS_23X_CORRUPT.zip: none of the 3 keys could decrypt
```

### Rapport mode dry-run

```
=== ENEDIS SGE DRY-RUN REPORT ===
Run #43        triggered_by: cli  (dry-run)
Source:          /path/to/flux_enedis (recursive)
New files:       12
Retryable errors: 2  (eligible for retry, < MAX_RETRIES)
Max retries:     1   (will be skipped — limit reached)
Already processed: 46
No data modifications made.
```

### Tests

| Classe | Cas |
|--------|-----|
| `TestCliIngest` | Mode normal avec fichiers synthetiques, compteurs corrects, IngestionRun created avec status=completed |
| `TestCliDryRun` | Aucune modification sur les donnees d'ingestion, IngestionRun avec dry_run=True |
| `TestCliVerbose` | Logging DEBUG active |
| `TestCliMissingDir` | Repertoire inexistant -> erreur propre, sys.exit(1) |
| `TestCliNoKeys` | Cles absentes -> erreur propre, sys.exit(1) |

---

## Phase 5 — API REST + Wiring applicatif

**Commit** : `feat(enedis): add REST API endpoints and wire router into app (SF4)`

### Creer

| Fichier | Description |
|---------|-------------|
| `backend/routes/enedis.py` | Router `/api/enedis` + schemas Pydantic |
| `backend/tests/test_enedis_api.py` | Tests API |

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/routes/__init__.py` | + `from .enedis import router as enedis_router` dans le bloc d'imports + `"enedis_router"` dans `__all__` |
| `backend/main.py` | + `enedis_router` dans le tuple `from routes import (...)` + `app.include_router(enedis_router)  # Enedis SGE Flux` dans le bloc d'enregistrement |

### Endpoints

| Methode | Path | Description |
|---------|------|-------------|
| `POST` | `/api/enedis/ingest` | Declencher ingestion (sync, body JSON) |
| `GET` | `/api/enedis/flux-files` | Liste paginee + filtres (status, flux_type) |
| `GET` | `/api/enedis/stats` | Stats agregees (fichiers, mesures, PRMs, dernier run) |
| `GET` | `/api/enedis/flux-files/{id}` | Detail fichier + header_raw + error history |

### Schemas Pydantic

**Ingestion :**
```python
IngestRequest     { directory?, recursive=True, dry_run=False }
IngestResponse    { run_id, received, parsed, needs_review, skipped, error,
                    retried, max_retries_reached, already_processed,
                    errors: [IngestErrorDetail], duration_seconds, dry_run }
IngestErrorDetail { filename, error_message }
```

**Flux files :**
```python
FluxFileResponse       { id, filename, file_hash, flux_type, status,
                         error_message?, measures_count?, version,
                         supersedes_file_id?, created_at, updated_at }
FluxFileListResponse   { total, items: [FluxFileResponse] }
FluxFileDetailResponse { ...FluxFileResponse, header_raw?,
                         errors_history: [ErrorHistoryItem] }
ErrorHistoryItem       { error_message, created_at }
```

**Stats :**
```python
StatsResponse    { files: FileStats, measures: MeasureStats,
                   prms: PrmStats, last_ingestion?: LastIngestion }
FileStats        { total, by_status: {}, by_flux_type: {} }
MeasureStats     { total, r4x, r171, r50, r151 }
PrmStats         { count, identifiers: [] }
LastIngestion    { run_id, timestamp, files_count, triggered_by }
```

**Logique `LastIngestion`** : query `IngestionRun` le plus recent avec `status='completed'` et `dry_run=False`, ordonne par `finished_at DESC`, limit 1. Champ nullable dans `StatsResponse` (null si aucune ingestion reussie).

**Note `PrmStats`** : la requete exacte (UNION DISTINCT de `point_id` sur les 4 tables mesure) est laissee a l'architecte d'implementation. Hint : `union_all()` sur `select(distinct(Table.point_id))` pour chaque table.

### Pattern de l'endpoint `POST /api/enedis/ingest`

```python
@router.post("/ingest", response_model=IngestResponse)
def trigger_ingest(body: IngestRequest, db: Session = Depends(get_db)):
    flux_dir = get_flux_dir(override=body.directory)
    keys = load_keys_from_env()

    # 1. Create IngestionRun record
    run = IngestionRun(
        triggered_by="api", directory=str(flux_dir),
        recursive=body.recursive, dry_run=body.dry_run,
    )
    db.add(run)
    db.commit()

    # 2. Execute pipeline (pipeline commits per-file internally — by design)
    t0 = time.time()
    counters = ingest_directory(
        flux_dir, db, keys,
        recursive=body.recursive, dry_run=body.dry_run,
    )
    duration = time.time() - t0

    # 3. Update IngestionRun with results
    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    run.files_received = counters["received"]
    # ... (all counters)
    db.commit()

    # 4. Return response with run_id
    return IngestResponse(run_id=run.id, duration_seconds=round(duration, 2), ...)
```

### Wiring

**`routes/__init__.py`** : ajouter `from .enedis import router as enedis_router` dans le bloc d'imports existant + `"enedis_router"` dans la liste `__all__`.

**`main.py`** : ajouter `enedis_router` dans le tuple `from routes import (...)` + `app.include_router(enedis_router)  # Enedis SGE Flux` apres la derniere ligne `app.include_router(...)`.

### Tests

**Fixture** : pattern identique a `test_bacs_api.py` — le fixture `client` yield un tuple `(TestClient(app), session)`. Chaque test depack : `c, session = client`. Seed helpers sont des fonctions plain qui prennent `session`.

| Classe | Cas |
|--------|-----|
| `TestIngestEndpoint` | POST normal (IngestionRun created, run_id dans la reponse), POST dry-run, repertoire inexistant |
| `TestFluxFilesEndpoint` | Liste paginee, filtre status, filtre flux_type |
| `TestStatsEndpoint` | Stats correctes apres ingestion, last_ingestion populated avec run_id |
| `TestFluxFileDetailEndpoint` | Detail + header_raw, detail + error_history, 404 |

---

## Fichiers de reference (patterns a suivre)

| Pattern | Reference |
|---------|-----------|
| Router registration | `backend/routes/__init__.py` (bloc imports + `__all__`), `backend/main.py` (bloc `from routes import (...)` + bloc `app.include_router(...)`) |
| Router structure | `backend/routes/sites.py` (prefix, tags, Depends, schemas inline) |
| Pagination offset/limit | `backend/routes/billing.py` (Query params avec bornes ge/le) |
| CLI argparse + _ensure_tables | `backend/services/demo_seed/__main__.py` (`_ensure_tables`, argparse, SessionLocal, sys.exit) |
| DB imports pour CLI/scripts | `from database import SessionLocal, engine` (via `database/__init__.py` re-export) |
| DB test fixture (pipeline) | `backend/data_ingestion/enedis/tests/conftest.py` (in-memory SQLite, create_all) |
| API test fixture | `backend/tests/test_bacs_api.py` (yield `(TestClient(app), session)` tuple, `Depends` override, unpack `c, session = client`) |
| Models + TimestampMixin | `backend/models/base.py` (TimestampMixin -> created_at, updated_at UTC) |
| Rapport mesures post-ingestion | `backend/data_ingestion/enedis/scripts/ingest_real_db.py` (queries count sur tables staging) |

---

## Verification

### Apres chaque phase (1-4)

```bash
cd promeos-poc && ./backend/venv/bin/pytest backend/data_ingestion/enedis/tests/ -x -v
```

### Apres Phase 5

```bash
cd promeos-poc && ./backend/venv/bin/pytest backend/tests/test_enedis_api.py -x -v
```

### Test complet final

```bash
cd promeos-poc && ./backend/venv/bin/pytest backend/tests/ backend/data_ingestion/enedis/tests/ -x -v
```

---

## Sequence des commits

| # | Commit | Phase |
|---|--------|-------|
| 0 | `docs(enedis): update SF4 spec v5 with full architecture decisions` | Spec |
| 1 | `feat(enedis): externalize flux directory config (SF4)` | Config |
| 2 | `feat(enedis): add EnedisFluxFileError and IngestionRun models (SF4)` | Models |
| 3 | `fix(enedis): preserve error history, enable batch retry and dry-run (SF4)` | Pipeline |
| 4 | `feat(enedis): add CLI for ingestion with dry-run and structured report (SF4)` | CLI |
| 5 | `feat(enedis): add REST API endpoints and wire router into app (SF4)` | API + Wiring |
