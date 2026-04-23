# Promeos POC — Roadmap

Progress tracker for all features and initiatives. Each feature shows its current phase in the [7-step workflow](docs/process/feature-workflow.md).

**Phases:** 1-SPEC | 2-REVIEW | 3-PLAN | 4-BUILD | 5-VERIFY | 6-VALIDATE | 7-SHIP

---

## Enedis SGE — Real Flux Ingestion

Replace synthetic seed data with real Enedis SGE flux (load curves + index).

| Feature | Description | Phase | Refs |
|---------|-------------|-------|------|
| SF1 — Decrypt | AES-128-CBC decryption, classification of 6 flux types | 7-SHIP ✅ | [spec](docs/specs/feature-enedis-sge-1-decrypt.md) · PR #148 |
| SF2 — CDC R4x | R4H/R4M/R4Q parser, raw archive model, pipeline | 7-SHIP ✅ | [spec](docs/specs/feature-enedis-sge-2-ingestion-cdc.md) · PR #163 |
| SF3 — R171 + Index | R171, R50, R151 parsers, multi-flux dispatch | 7-SHIP ✅ | [spec](docs/specs/feature-enedis-sge-3-ingestion-index.md) · [plan](docs/specs/plan-enedis-sge-3-implementation.md) · PRs #167–#174 |
| SF4 — Operationalization | Config, error audit, batch retry, CLI, REST API | 7-SHIP ✅ | [spec](docs/specs/feature-enedis-sge-4-operationalization.md) · [plan](docs/specs/plan-enedis-sge-4-implementation.md) · PR #177 |
| SGE4.5 — Flux Data DB Split | Retarget the existing Enedis raw pipeline to `flux_data.db` without changing CLI/API/parser behavior | 6-VALIDATE | [spec](docs/specs/feature-enedis-sge-4-5-flux-data-db-split.md) |
| SF5 — R6X + C68 Raw Ingestion | Extend the raw ingestion pipeline with 2 new raw archive tables: `R63`/`R64` (R6X family) and `C68` | 1-SPEC | [spec](docs/specs/feature-enedis-sge-5-r6x-c68-raw-ingestion.md) |
| SF6 — Raw → Functional Promotion | Promote Enedis raw archive data from `flux_data.db` into 3 functional tables in `promeos.db` (`meter_load_curve`, `meter_energy_index`, `meter_power_peak`), with PRM matching, quality scoring, republication handling, and audit trail | 1-SPEC | [spec](docs/specs/feature-enedis-sge-6-data-staging.md) |

**Result after SF4:** 6 flux types, 5 raw archive tables, 91 real files ingested, 123,846 measures. CLI + 4 API endpoints operational.

**SGE4.5 scope:** keep the current Enedis raw pipeline intact, but move its raw tables and ingest control tables to `flux_data.db`.

**SGE4.5 result:** implementation complete and validated locally on real data; raw Enedis storage now lives in `flux_data.db`, while `promeos.db` stays focused on app-facing and promoted data.

**SF5 scope:** raw-ingestion extension for `R63`, `R64` (R6X family), and `C68` via 2 new raw archive tables in the existing raw ingest pipeline stored in `flux_data.db`.

**SF6 scope (8 phases):** read raw archive data from `flux_data.db`, write promoted/audit tables to `promeos.db`, then deliver A-Foundation & data model · B-R4x CDC promotion · C-R50 CDC promotion · D-Republication handling · E-R171/R151 index+PMAX · F-API scaffolding · G-Backfill & validation · H-Service migration

---

## Other Modules

| Feature | Description | Phase | Refs |
|---------|-------------|-------|------|
| — | — | — | — |

_Add new features here as they are scoped._

---

## Legend

- **Not started** — No spec yet
- **1-SPEC** — Iterating on functional requirements
- **2-REVIEW** — Challenging the spec (questions, decisions, edge cases)
- **3-PLAN** — Implementation plan being written
- **4-BUILD** — Coding in progress (phases N/M)
- **5-VERIFY** — Walking spec against implementation
- **6-VALIDATE** — Implementation complete and validated locally (real-data smoke passed)
- **7-SHIP ✅** — PR merged on main
