# SF4 — Enedis SGE Operational Ingestion Pipeline

> **Status**: Draft — to be developed into thorough specs
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion) — all complete on `feat/enedis-sge-ingestion`

## Context

SF1-SF3 delivered a complete ingestion pipeline: decrypt, parse, and store real Enedis flux files (R4H, R4M, R4Q, R171, R50, R151) into 4 staging tables. 221 tests pass, 91 real files ingest with 0 errors, 123,846 measures total.

Two ad-hoc scripts exist in `backend/data_ingestion/enedis/scripts/`:
- `decrypt_samples.py` — decrypts all files to `flux_enedis/decrypted_xml/` for inspection
- `ingest_real_db.py` — one-shot ingestion into promeos.db

**Problem:** The pipeline has no proper operational entry point. The scripts were bolted on after the fact. We need to design how ingestion is actually called and used in the PROMEOS workflow.

## Open Questions

### 1. Trigger Mechanism

How should ingestion be triggered?

- **CLI command** (`python -m ...`) run manually?
- **JobOutbox integration** (existing `jobs/run.py` pattern)?
- **API endpoint** (POST /api/enedis/ingest) for future UI integration?
- **Directory watcher** that auto-ingests new files?
- Some combination?

### 2. Observability

How do we surface ingestion results?

- Logging (already exists via `promeos.enedis.pipeline` logger)
- API endpoint to query ingestion status (GET /api/enedis/flux-files)?
- Dashboard/UI page showing file counts, errors, last ingestion?

### 3. Error Handling & Retry

The pipeline already handles per-file errors without blocking the batch, and RECEIVED status enables crash recovery. But:

- How should ERROR files be surfaced to the user?
- Should there be a retry mechanism?
- Should we alert on ingestion failures?

### 4. Configuration

Currently keys are in `.env` and the flux directory path is hardcoded.

- Add `ENEDIS_FLUX_DIR` to `.env`?
- Support multiple source directories?

## Starting Point for Development

Explore the existing codebase (especially `jobs/run.py`, the JobOutbox pattern, and existing API routers) to understand how other batch operations are triggered. Propose an approach aligned with existing patterns. Keep it minimal — this is still POC stage.

## Current Inventory

| Asset | Path |
|-------|------|
| Pipeline | `backend/data_ingestion/enedis/pipeline.py` |
| Models | `backend/data_ingestion/enedis/models.py` |
| Parsers | `backend/data_ingestion/enedis/parsers/` |
| Decrypt | `backend/data_ingestion/enedis/decrypt.py` |
| Ad-hoc scripts | `backend/data_ingestion/enedis/scripts/` |
| Tests (221) | `backend/data_ingestion/enedis/tests/` |
| Real flux files | `flux_enedis/` (outside repo, 91 in-scope) |
| Decrypted XMLs | `flux_enedis/decrypted_xml/` (91 files, 23.8 MB) |
