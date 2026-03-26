# SF4 — Operationalization Pipeline Enedis SGE — Plan d'implementation

> **Status** : Plan v4 — aligne avec spec v7, integre decisions revue finale
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
| Fichiers PERMANENTLY_FAILED | **Nouveau statut `FluxStatus.PERMANENTLY_FAILED`** quand MAX_RETRIES atteint | Identification immediate par le data manager. Plus de retry automatique |
| Fichiers NEEDS_REVIEW | **Pas de retry automatique** — donnees chargees, attente review humaine | Traitement initial reussi, republication detectee. Pas un cas d'erreur |
| Suivi d'execution | **Table `IngestionRun`** avec **compteurs incrementaux** fichier par fichier | Si crash mid-run : compteurs fiables, status "failed", run suivant traite les restants |
| Statuts IngestionRun | **running / completed / failed** | failed = crash ou erreur apres creation du run. Compteurs incrementaux fiables |
| Session API | **`Depends(get_db)`** standard | Pipeline commits per-file (by design). Tracabilite via `IngestionRun` |
| Concurrence | **Verrou simple** : refuser si IngestionRun en status "running" | 5 lignes, empeche compteurs incoherents en parallele |
| Validation pre-flight | **Verifier cles + repertoire AVANT creation d'IngestionRun** | Fail fast, pas de run "failed" inutile dans l'historique |
| Variable ENEDIS_FLUX_DIR | **Obligatoire** dans `.env` — pas de fallback | La clarte prime. Les chemins relatifs sont source d'erreurs |
| Rapport CLI mesures | **Requetes DB post-ingestion** (pattern `ingest_real_db.py`) | `ingest_directory()` retourne des compteurs de fichiers, pas de mesures. `_print_report()` calcule les volumes via queries sur les tables staging |
| Mesures dans IngestResponse | **Non** — compteurs fichiers uniquement | Les volumes de mesures sont des totaux staging, pas des deltas du run. Disponibles via GET /stats |
| CLI scope | **Minimaliste** — `ingest` uniquement (+ `--dry-run`) | Les stats restent cote API, evite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ulterieurement |
| Schemas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) | Coherence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Coherent avec les autres tests d'API (`test_bacs_api.py`, etc.) |
| Scripts ad-hoc | **Deprecation** phase 1, suppression apres validation SF4 complete | Reference pendant la transition |

---

## Phase 0 — Mise a jour de la spec

**Commit** : `docs(enedis): update SF4 spec v6 with final architecture decisions`

| Fichier | Action |
|---------|--------|
| `docs/specs/feature-enedis-sge-4-operationalization.md` | Aligner sur spec v6 (toutes decisions finales integrees) |
| `docs/specs/plan-enedis-sge-4-implementation.md` | Aligner sur plan v3 |

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
| `backend/data_ingestion/enedis/scripts/ingest_real_db.py` | Ajouter commentaire de deprecation en tete de fichier |
| `backend/data_ingestion/enedis/scripts/decrypt_samples.py` | Ajouter commentaire de deprecation en tete de fichier |

### Contenu de `config.py`

```python
MAX_RETRIES: int = 3  # Nombre max de retries sur un fichier en erreur (4 tentatives au total)

def get_flux_dir(override: str | None = None) -> Path:
    """Resolve le repertoire de flux Enedis.

    Priorite : override > env var ENEDIS_FLUX_DIR.
    Pas de fallback — ENEDIS_FLUX_DIR est obligatoire si pas d'override.
    """
```

### Comportement `get_flux_dir()`

```
1. Si override fourni et non vide -> Path(override)
2. Sinon os.environ.get("ENEDIS_FLUX_DIR") -> Path(env_value)
3. Sinon -> ValueError("ENEDIS_FLUX_DIR environment variable is required — set it in .env")
4. Dans tous les cas : si le path n'est pas un repertoire -> ValueError("... is not a directory")
```

### Tests

| Classe | Cas |
|--------|-----|
| `TestGetFluxDir` | env var set → correct path, env var absent + no override → ValueError avec message explicite, override explicite → correct path, repertoire inexistant → ValueError, override vide string → fallback sur env var |
| `TestMaxRetries` | Constante accessible et correctement typee |

---

## Phase 2 — Modeles d'audit (erreurs + suivi d'execution)

**Commit** : `feat(enedis): add EnedisFluxFileError, IngestionRun models and PERMANENTLY_FAILED status (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/models.py` | + classe `EnedisFluxFileError`, + classe `IngestionRun`, + relation `errors` sur `EnedisFluxFile` |
| `backend/data_ingestion/enedis/enums.py` | + `PERMANENTLY_FAILED = "permanently_failed"` dans `FluxStatus`, + classe `IngestionRunStatus(str, Enum)` avec `RUNNING/COMPLETED/FAILED` |

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
  status                  String(20) NOT NULL default "running"  (IngestionRunStatus: running / completed / failed)
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

Note : `files_max_retries` comptabilise tous les fichiers non-retentables (nouvellement PERMANENTLY_FAILED + deja en PERMANENTLY_FAILED).

### Enum `FluxStatus` — extension

```python
class FluxStatus(str, Enum):
    RECEIVED = "received"
    PARSED = "parsed"
    ERROR = "error"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    PERMANENTLY_FAILED = "permanently_failed"  # NEW — MAX_RETRIES atteint


class IngestionRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

### Tests

| Fichier | Cas |
|---------|-----|
| `test_models.py` (extend) | `EnedisFluxFileError` : creation, cascade delete, ordering par `created_at` |
| `test_models.py` (extend) | `IngestionRun` : creation, status transitions (running→completed, running→failed), default values, all counter columns |
| `test_models.py` (extend) | `FluxStatus.PERMANENTLY_FAILED` : valeur accessible, distinct de ERROR |
| `test_models.py` (extend) | `IngestionRunStatus` : valeurs RUNNING/COMPLETED/FAILED accessibles |

---

## Phase 3 — Correction audit d'erreurs + retry batch + dry-run + compteurs incrementaux

**Commit** : `fix(enedis): preserve error history, enable batch retry, dry-run and incremental run tracking (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/pipeline.py` | (1) Fix retry dans `ingest_file()`. (2) Retry ERROR + PERMANENTLY_FAILED + NEEDS_REVIEW dans `ingest_directory()`. (3) Parametre `dry_run`. (4) Parametre `run` pour compteurs incrementaux. |

### Changement 1 : Fix du retry + garde MAX_RETRIES + skip PERMANENTLY_FAILED dans `ingest_file()`

**Localisation** : les blocs d'idempotence et de retry dans la fonction `ingest_file()`.

**Avant** :
```python
if existing.status in (FluxStatus.PARSED, FluxStatus.SKIPPED, FluxStatus.NEEDS_REVIEW):
    ...
    return FluxStatus(existing.status)
if existing.status == FluxStatus.ERROR:
    session.delete(existing)
    session.flush()
```

**Apres** :
```python
if existing.status in (FluxStatus.PARSED, FluxStatus.SKIPPED, FluxStatus.NEEDS_REVIEW, FluxStatus.PERMANENTLY_FAILED):
    ...
    return FluxStatus(existing.status)
if existing.status == FluxStatus.ERROR:
    if len(existing.errors) >= MAX_RETRIES:
        existing.status = FluxStatus.PERMANENTLY_FAILED
        session.commit()
        logger.info("File %s reached MAX_RETRIES — marked PERMANENTLY_FAILED", filename)
        return FluxStatus.PERMANENTLY_FAILED
    _archive_error(session, existing)
    existing.error_message = None
    pre_registered = existing  # reuse same record in-place
```

La garde `MAX_RETRIES` dans `ingest_file()` est necessaire pour les appels directs (futur endpoint UX de re-ingestion fichier par fichier). `ingest_directory()` a sa propre garde en Phase 1 pour eviter d'ajouter le fichier a `to_process`.

**Nouveau helper** `_archive_error(session, flux_file)` :
- Si `flux_file.error_message` non vide : creer `EnedisFluxFileError(flux_file_id=flux_file.id, error_message=flux_file.error_message)`
- Sinon : no-op

### Changement 2 : Retry ERROR + gestion PERMANENTLY_FAILED et NEEDS_REVIEW dans `ingest_directory()`

**Localisation** : Phase 1 de `ingest_directory()`, le bloc `else` apres le check `if existing.status == FluxStatus.RECEIVED` qui compte actuellement tous les autres statuts comme `already_processed`.

**Avant** :
```python
else:
    # Already processed (PARSED/ERROR/SKIPPED/NEEDS_REVIEW)
    counters["already_processed"] += 1
```

**Apres** :
```python
elif existing.status == FluxStatus.NEEDS_REVIEW:
    # Data loaded, awaiting human review (republication) — no retry
    counters["already_processed"] += 1
elif existing.status == FluxStatus.PERMANENTLY_FAILED:
    # Max retries reached — skip, needs manual intervention
    counters["max_retries_reached"] += 1
elif existing.status == FluxStatus.ERROR:
    error_count = len(existing.errors)
    if error_count < MAX_RETRIES:
        logger.info("Retrying ERROR file %s (attempt %d/%d)",
                     file_path.name, error_count + 1, MAX_RETRIES)
        to_process.append((file_path, file_hash, existing))
        counters["retried"] += 1
    else:
        # Transition to PERMANENTLY_FAILED (skip in dry-run)
        if not dry_run:
            existing.status = FluxStatus.PERMANENTLY_FAILED
            session.commit()
        logger.info("File %s reached MAX_RETRIES (%d) — %s",
                     file_path.name, MAX_RETRIES,
                     "marked PERMANENTLY_FAILED" if not dry_run else "would mark PERMANENTLY_FAILED (dry-run)")
        counters["max_retries_reached"] += 1
else:
    # PARSED, SKIPPED
    counters["already_processed"] += 1
```

**Compteurs ajoutes** dans le dict de retour de `ingest_directory()` :
- `retried: int` — fichiers ERROR retentes dans cette execution
- `max_retries_reached: int` — fichiers ignores car PERMANENTLY_FAILED (nouveau ou existant)

**Import necessaire** : `from data_ingestion.enedis.config import MAX_RETRIES`

### Changement 3 : Parametre `dry_run` dans `ingest_directory()`

**Signature** : ajouter `dry_run: bool = False` a `ingest_directory()`.

**Comportement** :
- Phase 1 : scan, hash, classify, check DB — identique, mais **pas de commit** des enregistrements RECEIVED, pas de creation de nouveaux records. Les transitions ERROR → PERMANENTLY_FAILED ne sont **pas commitees** en dry-run (comptees mais pas appliquees). Seulement compter.
- Phase 2 : **skipped entierement** en mode dry_run
- Retour : meme dict de compteurs (`received` = nombre de fichiers qui seraient traites, `retried` et `max_retries_reached` comme en mode normal, les compteurs de processing a 0)

### Changement 4 : Parametre `run` pour compteurs incrementaux

**Signature** : ajouter `run: IngestionRun | None = None` a `ingest_directory()`.

**Comportement** :
- Si `run` est fourni, les compteurs de l'IngestionRun sont mis a jour **apres chaque fichier traite** dans Phase 2 :
```python
# After each file in Phase 2 processing loop:
if run:
    if status == FluxStatus.PARSED:
        run.files_parsed += 1
    elif status == FluxStatus.ERROR:
        run.files_error += 1
    elif status == FluxStatus.SKIPPED:
        run.files_skipped += 1
    elif status == FluxStatus.NEEDS_REVIEW:
        run.files_needs_review += 1
    session.commit()  # commit incremental counter update
```
- Apres Phase 1 (scan), les compteurs de scan sont aussi mis a jour sur le run :
```python
if run:
    run.files_received = counters["received"]
    run.files_already_processed = counters["already_processed"]
    run.files_retried = counters["retried"]
    run.files_max_retries = counters["max_retries_reached"]
    session.commit()
```
- A la fin de `ingest_directory()`, si tout s'est bien passe :
```python
if run:
    run.status = "completed"
    run.finished_at = datetime.now(timezone.utc)
    session.commit()
```
- Si une exception non geree survient, elle remonte au caller (CLI/API) qui mettra `run.status = IngestionRunStatus.FAILED`.

### Signature finale de `ingest_directory()`

```python
def ingest_directory(
    dir_path: Path,
    session: Session,
    keys: list[tuple[bytes, bytes]],
    *,
    recursive: bool = True,
    dry_run: bool = False,
    run: IngestionRun | None = None,
) -> dict[str, int]:
```

### Tests

| Fichier | Cas |
|---------|-----|
| `test_pipeline.py` (extend) | `TestErrorHistoryPreserved` : (1) echoue 2x → 2 entries error history + `len(errors)==2`, (2) echoue puis reussit → history preservee + status=PARSED, (3) decrypt error puis parse error → 2 messages distincts |
| `test_pipeline_full.py` (extend) | `TestErrorRetryInBatch` : fichier ERROR dans `ingest_directory()` est retente, history preservee. Fichier avec MAX_RETRIES atteint → status PERMANENTLY_FAILED, compteur `max_retries_reached`. Fichier PERMANENTLY_FAILED dans un run suivant → skip + compteur `max_retries_reached`. |
| `test_pipeline_full.py` (extend) | `TestNeedsReviewNoRetry` : fichier NEEDS_REVIEW dans `ingest_directory()` → comptabilise comme `already_processed`, pas retente |
| `test_pipeline.py` (extend) | `TestDryRun` : `ingest_directory(dry_run=True)` retourne les bons compteurs sans modifier la DB |
| `test_pipeline_full.py` (extend) | `TestIncrementalCounters` : passer un `IngestionRun` a `ingest_directory()`, verifier que les compteurs sont mis a jour apres chaque fichier (pas seulement a la fin). Simuler un crash mid-run et verifier que les compteurs refletent le travail partiel |

---

## Phase 4 — CLI

**Commit** : `feat(enedis): add CLI for ingestion with dry-run, pre-flight validation and structured report (SF4)`

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
| `--dir PATH` | env var `ENEDIS_FLUX_DIR` (obligatoire) | Repertoire source |
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

    # === PRE-FLIGHT VALIDATION ===
    flux_dir = get_flux_dir(override=args.dir)      # ValueError if missing
    keys = load_keys_from_env()                       # MissingKeyError if missing

    session = SessionLocal()

    # === CONCURRENCY GUARD ===
    running = session.query(IngestionRun).filter_by(status="running").first()
    if running:
      print(f"ERROR: Run #{running.id} is already in progress (started {running.started_at})")
      sys.exit(1)

    # === CREATE RUN (only after all validations pass) ===
    run = IngestionRun(triggered_by="cli", directory=str(flux_dir),
                       recursive=args.recursive, dry_run=args.dry_run,
                       started_at=datetime.now(timezone.utc))
    session.add(run) ; session.commit()

    try:
      mode normal  -> ingest_directory(session, keys, ..., run=run) -> _print_report
      mode dry-run -> ingest_directory(session, keys, ..., dry_run=True, run=run) -> _dry_run_report
      # run.status already set to "completed" by ingest_directory()
    except Exception as exc:
      run.status = IngestionRunStatus.FAILED  # counters are already incremental
      run.finished_at = datetime.now(timezone.utc)
      run.error_message = str(exc)
      session.commit()
      print(f"ERROR: Run #{run.id} interrupted — status: failed")
      traceback.print_exc()
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
Run #42        triggered_by: cli        status: completed
Source:          /path/to/flux_enedis (recursive)
Duration:        3.2s
Files received:  45
  parsed:        38
  skipped:       5  (R172: 3, X14: 1, HDM: 1)
  error:         1
  needs_review:  1
Retried:         2  (from previous errors)
Max retries:     0  (permanently failed — skipped)
Already processed: 46
Measures stored (staging totals):
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
Max retries:     1   (permanently failed — will be skipped)
Already processed: 46
No data modifications made.
```

### Tests

| Classe | Cas |
|--------|-----|
| `TestCliIngest` | Mode normal avec fichiers synthetiques, compteurs corrects, IngestionRun created avec status=completed |
| `TestCliDryRun` | Aucune modification sur les donnees d'ingestion, IngestionRun avec dry_run=True |
| `TestCliVerbose` | Logging DEBUG active |
| `TestCliMissingDir` | ENEDIS_FLUX_DIR absent + no --dir → erreur propre "ENEDIS_FLUX_DIR environment variable is required", sys.exit(1), pas d'IngestionRun cree |
| `TestCliMissingKeys` | Cles absentes → erreur propre, sys.exit(1), pas d'IngestionRun cree |
| `TestCliConcurrentRun` | IngestionRun en status "running" existe deja → erreur propre, sys.exit(1), pas de nouveau run cree |
| `TestCliCrashRun` | Simuler crash mid-ingestion → run.status="failed", compteurs incrementaux corrects |

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
| `GET` | `/api/enedis/flux-files` | Liste paginee + filtres (status incluant PERMANENTLY_FAILED, flux_type) |
| `GET` | `/api/enedis/stats` | Stats agregees (fichiers, mesures, PRMs, dernier run) |
| `GET` | `/api/enedis/flux-files/{id}` | Detail fichier + header_raw + error history |

### Schemas Pydantic

**Ingestion :**
```python
IngestRequest     { directory?, recursive=True, dry_run=False }
IngestResponse    { run_id, status, received, parsed, needs_review, skipped, error,
                    retried, max_retries_reached, already_processed,
                    errors: [IngestErrorDetail], duration_seconds, dry_run }
IngestErrorDetail { filename, error_message }
```

Note : `IngestResponse` ne contient PAS de volumes de mesures — ceux-ci sont des totaux staging disponibles via GET /stats.

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

**Note `PrmStats`** : la requete exacte (UNION DISTINCT de `point_id` sur les 4 tables mesure) est laissee a l'architecte d'implementation. Hint : `union_all()` sur `select(distinct(Table.point_id))` pour chaque table. Dans le POC, la liste PRM est globale. En production, filtrer par contrat/portefeuille — point d'attention futur.

### Pattern de l'endpoint `POST /api/enedis/ingest`

```python
@router.post("/ingest", response_model=IngestResponse)
def trigger_ingest(body: IngestRequest, db: Session = Depends(get_db)):
    # === PRE-FLIGHT VALIDATION ===
    try:
        flux_dir = get_flux_dir(override=body.directory)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        keys = load_keys_from_env()
    except MissingKeyError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # === CONCURRENCY GUARD ===
    running = db.query(IngestionRun).filter_by(status="running").first()
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"Run #{running.id} is already in progress (started {running.started_at})"
        )

    # === CREATE RUN (only after all validations pass) ===
    run = IngestionRun(
        triggered_by="api", directory=str(flux_dir),
        recursive=body.recursive, dry_run=body.dry_run,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()

    # === EXECUTE PIPELINE ===
    t0 = time.time()
    try:
        counters = ingest_directory(
            flux_dir, db, keys,
            recursive=body.recursive, dry_run=body.dry_run,
            run=run,
        )
    except Exception as exc:
        # Incremental counters are already committed
        run.status = IngestionRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = str(exc)
        db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Run #{run.id} interrupted (status: failed) — {str(exc)}"
        )
    duration = time.time() - t0

    # run.status already set to "completed" by ingest_directory()

    return IngestResponse(
        run_id=run.id, status=run.status,
        duration_seconds=round(duration, 2), ...
    )
```

### Wiring

**`routes/__init__.py`** : ajouter `from .enedis import router as enedis_router` dans le bloc d'imports existant + `"enedis_router"` dans la liste `__all__`.

**`main.py`** : ajouter `enedis_router` dans le tuple `from routes import (...)` + `app.include_router(enedis_router)  # Enedis SGE Flux` apres la derniere ligne `app.include_router(...)`.

### Tests

**Fixture** : pattern identique a `test_bacs_api.py` — le fixture `client` yield un tuple `(TestClient(app), session)`. Chaque test depack : `c, session = client`. Seed helpers sont des fonctions plain qui prennent `session`.

| Classe | Cas |
|--------|-----|
| `TestIngestEndpoint` | POST normal (IngestionRun created, run_id + status dans la reponse), POST dry-run, repertoire inexistant → 422 |
| `TestIngestPreFlight` | POST sans cles → 422 avec message explicite, POST sans ENEDIS_FLUX_DIR → 422, POST avec run concurrent → 409 avec run_id existant |
| `TestIngestCrash` | Simuler erreur mid-ingestion → status "failed", compteurs incrementaux dans la reponse 500 |
| `TestFluxFilesEndpoint` | Liste paginee, filtre status (incluant PERMANENTLY_FAILED), filtre flux_type |
| `TestStatsEndpoint` | Stats correctes apres ingestion, last_ingestion populated avec run_id, PRM count et identifiers |
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
| 0 | `docs(enedis): update SF4 spec v6 with final architecture decisions` | Spec |
| 1 | `feat(enedis): externalize flux directory config (SF4)` | Config |
| 2 | `feat(enedis): add EnedisFluxFileError, IngestionRun models and PERMANENTLY_FAILED status (SF4)` | Models |
| 3 | `fix(enedis): preserve error history, enable batch retry, dry-run and incremental run tracking (SF4)` | Pipeline |
| 4 | `feat(enedis): add CLI for ingestion with dry-run, pre-flight validation and structured report (SF4)` | CLI |
| 5 | `feat(enedis): add REST API endpoints and wire router into app (SF4)` | API + Wiring |
