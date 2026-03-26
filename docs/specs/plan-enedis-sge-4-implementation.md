# SF4 — Operationalization Pipeline Enedis SGE — Plan d'implementation

> **Status** : Plan v1 — approuve, pret pour implementation phase par phase
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
| CLI scope | **Minimaliste** — `ingest` uniquement (+ `--dry-run`) | Les stats restent cote API, evite la duplication de logique |
| Auth API | **Pas d'auth** pour le POC | Usage ops/admin, ajout facile ulterieurement |
| Schemas Pydantic | **Dans le router** (`routes/enedis.py`) | Pattern dominant du codebase |
| `.env.example` | **Les deux** fichiers (racine + `backend/`) | Coherence avec les conventions existantes |
| Tests API | **`backend/tests/test_enedis_api.py`** | Coherent avec les autres tests d'API (`test_bacs_api.py`, etc.) |

---

## Phase 0 — Mise a jour de la spec

**Commit** : `docs(enedis): update SF4 spec with architecture decisions`

| Fichier | Action |
|---------|--------|
| `docs/specs/feature-enedis-sge-4-operationalization.md` | Ajouter section "Decisions d'architecture" avec les 6 decisions. Status → "Spec v4 — decisions validated, implementation plan ready" |

---

## Phase 1 — Configuration externalisee

**Commit** : `feat(enedis): externalize flux directory config (SF4)`

### Creer

| Fichier | Description |
|---------|-------------|
| `backend/data_ingestion/enedis/config.py` | `get_flux_dir(override, validate) -> Path` |
| `backend/data_ingestion/enedis/tests/test_config.py` | Tests unitaires |

### Modifier

| Fichier | Modification |
|---------|-------------|
| `.env.example` (racine) | Ajouter `ENEDIS_FLUX_DIR` section External Data Connectors |
| `backend/.env.example` | Ajouter `ENEDIS_FLUX_DIR` |

### Comportement `get_flux_dir()`

```
1. Si override fourni et non vide → Path(override)
2. Sinon os.environ.get("ENEDIS_FLUX_DIR") → Path(env_value)
3. Sinon fallback → Path(__file__).resolve().parents[4] / "flux_enedis"
4. Si validate=True et le path n'est pas un repertoire → ValueError
```

### Tests

| Classe | Cas |
|--------|-----|
| `TestGetFluxDir` | env var set, env var absent (fallback), override explicite, repertoire inexistant → ValueError, validate=False bypass |

---

## Phase 2 — Modele d'historique d'erreurs

**Commit** : `feat(enedis): add EnedisFluxFileError model for error audit trail (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/models.py` | + classe `EnedisFluxFileError`, + relation `errors` sur `EnedisFluxFile`, + colonne `retry_count` |

### Schema `EnedisFluxFileError`

```
Table: enedis_flux_file_error
  id             Integer PK
  flux_file_id   Integer FK → enedis_flux_file.id (CASCADE)
  error_message  Text NOT NULL
  created_at     DateTime (TimestampMixin)
  updated_at     DateTime (TimestampMixin)

Index: ix_enedis_flux_file_error_flux_file (flux_file_id)
```

Sur `EnedisFluxFile` :
- `errors = relationship("EnedisFluxFileError", ..., order_by=created_at)`
- `retry_count = Column(Integer, default=0)`

### Tests

| Fichier | Cas |
|---------|-----|
| `test_models.py` (extend) | Creation, cascade delete, ordering par `created_at`, `retry_count` increment |

---

## Phase 3 — Correction audit d'erreurs dans le pipeline

**Commit** : `fix(enedis): preserve error history on retry instead of deleting (SF4)`

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/data_ingestion/enedis/pipeline.py` | Remplacer `session.delete(existing)` par `_archive_error()` + reuse in-place |

### Changement cle dans `ingest_file()`

**Avant** (lignes 106-109) :
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
- Si `flux_file.error_message` non vide : creer `EnedisFluxFileError` + incrementer `retry_count`
- Sinon : no-op

**Impact `_record_file()`** : si `existing` a un `error_message`, archiver avant de remplacer.

**Impact `ingest_directory()`** : aucun changement structurel.

### Tests

| Fichier | Cas |
|---------|-----|
| `test_pipeline.py` (extend) | `TestErrorHistoryPreserved` : (1) echoue 2x → 2 entries, retry_count=2, (2) echoue puis reussit → history preservee + status=PARSED, (3) decrypt error puis parse error → 2 messages distincts |
| `test_pipeline_full.py` (extend) | `TestErrorRetryInBatch` : retry dans un batch preserve l'historique. Regression check sur tous les tests existants |

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

Pattern `argparse` (ref: `services.demo_seed.__main__`, `jobs.run`).

```
sys.path.insert + load_dotenv
├── main() → argparse → dispatch
├── cmd_ingest(args) → logique principale
│   ├── mode normal: get_flux_dir → load_keys → ingest_directory → _print_report
│   └── mode dry-run: get_flux_dir → scan → classify → _dry_run_report
├── _print_report(counters, session, duration)
└── _dry_run_report(directory, session, recursive)
```

### Rapport mode normal

```
=== ENEDIS SGE INGESTION REPORT ===
Source:          /path/to/flux_enedis (recursive)
Duration:        3.2s
Files received:  45
  parsed:        38
  skipped:       5  (R172: 3, X14: 1, HDM: 1)
  error:         1
  needs_review:  1
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

### Tests

| Classe | Cas |
|--------|-----|
| `TestCliIngest` | Mode normal avec fichiers synthetiques, compteurs corrects |
| `TestCliDryRun` | Aucune modification en base |
| `TestCliVerbose` | Logging DEBUG active |
| `TestCliMissingDir` | Repertoire inexistant → erreur propre |
| `TestCliNoKeys` | Cles absentes → erreur propre |

---

## Phase 5 — API REST + Wiring applicatif

**Commit** : `feat(enedis): add REST API endpoints and wire router into app (SF4)`

### Creer

| Fichier | Description |
|---------|-------------|
| `backend/routes/enedis.py` | Router `/api/enedis` + schemas Pydantic |
| `backend/tests/test_enedis_api.py` | Tests API (TestClient) |

### Modifier

| Fichier | Modification |
|---------|-------------|
| `backend/routes/__init__.py` | + `from .enedis import router as enedis_router` + `__all__` |
| `backend/main.py` | + import + `app.include_router(enedis_router)` |

### Endpoints

| Methode | Path | Description |
|---------|------|-------------|
| `POST` | `/api/enedis/ingest` | Declencher ingestion (sync, body JSON) |
| `GET` | `/api/enedis/flux-files` | Liste paginee + filtres (status, flux_type) |
| `GET` | `/api/enedis/stats` | Stats agregees (fichiers, mesures, PRMs) |
| `GET` | `/api/enedis/flux-files/{id}` | Detail fichier + header_raw + error history |

### Schemas Pydantic

**Ingestion :**
```python
IngestRequest     { directory?, recursive=True, dry_run=False }
IngestResponse    { received, parsed, needs_review, skipped, error,
                    already_processed, errors: [IngestErrorDetail],
                    duration_seconds, dry_run }
IngestErrorDetail { filename, error_message }
```

**Flux files :**
```python
FluxFileResponse       { id, filename, file_hash, flux_type, status,
                         error_message?, measures_count?, version,
                         supersedes_file_id?, created_at, updated_at }
FluxFileListResponse   { total, items: [FluxFileResponse] }
FluxFileDetailResponse { ...FluxFileResponse, header_raw?, errors_history: [ErrorHistoryItem] }
ErrorHistoryItem       { error_message, created_at }
```

**Stats :**
```python
StatsResponse    { files: FileStats, measures: MeasureStats,
                   prms: PrmStats, last_ingestion?: LastIngestion }
FileStats        { total, by_status: {}, by_flux_type: {} }
MeasureStats     { total, r4x, r171, r50, r151 }
PrmStats         { count, identifiers: [] }
LastIngestion    { timestamp, files_count }
```

### Wiring

`routes/__init__.py` : ajouter import + `__all__` entry
`main.py` : ajouter dans le bloc d'imports et `app.include_router(enedis_router)  # Enedis SGE Flux`

### Tests

| Classe | Cas |
|--------|-----|
| `TestIngestEndpoint` | POST normal, POST dry-run, repertoire inexistant |
| `TestFluxFilesEndpoint` | Liste paginee, filtre status, filtre flux_type |
| `TestStatsEndpoint` | Stats correctes apres ingestion |
| `TestFluxFileDetailEndpoint` | Detail + header_raw, detail + error_history, 404 |

---

## Fichiers de reference (patterns a suivre)

| Pattern | Fichier |
|---------|---------|
| Router registration | `backend/routes/__init__.py`, `backend/main.py:20-73,114-168` |
| Router structure | `backend/routes/sites.py` |
| Pagination offset/limit | `backend/routes/billing.py` |
| CLI argparse | `backend/services/demo_seed/__main__.py` |
| DB test fixture | `backend/data_ingestion/enedis/tests/conftest.py` |
| API test fixture | `backend/tests/test_bacs_api.py` |
| Models + TimestampMixin | `backend/models/base.py` |

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
| 0 | `docs(enedis): update SF4 spec with architecture decisions` | Spec |
| 1 | `feat(enedis): externalize flux directory config (SF4)` | Config |
| 2 | `feat(enedis): add EnedisFluxFileError model for error audit trail (SF4)` | Model |
| 3 | `fix(enedis): preserve error history on retry instead of deleting (SF4)` | Pipeline |
| 4 | `feat(enedis): add CLI for ingestion with dry-run and structured report (SF4)` | CLI |
| 5 | `feat(enedis): add REST API endpoints and wire router into app (SF4)` | API + Wiring |
