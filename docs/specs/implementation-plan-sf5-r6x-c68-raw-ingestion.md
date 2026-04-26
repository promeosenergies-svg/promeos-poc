# SF5 Implementation Plan - Enedis R6X + C68 Raw Ingestion

Source PRD: `docs/specs/feature-enedis-sge-5-r6x-c68-raw-ingestion.md`

Branch context: `feat/sf5-r6x-c68`

Status: implementation plan only. No code changes are included in this document.

## Functional Outcome

SF5 extends the existing Enedis raw ingestion pipeline so one ingestion run can archive:

- legacy SF1-SF4 XML flows: `R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`
- new punctual SF5 flows: `R63`, `R64`, `C68`
- known but unsupported flows as clean skips: `R63A`, `R63B`, `R64A`, `R64B`, `R65`, `R66`, `R66B`, `R67`, `CR_M023`

What this means for the user:

Operators keep one ingestion command and one API/stats surface. A mixed drop containing a legacy encrypted XML file, a direct ZIP `R63`, and a nested ZIP `C68` should be processed in one run. Valid raw data is archived, unsupported known flows are skipped clearly, and malformed archives fail cleanly without partial inserts.

The database boundary is mandatory:

- all SF5 raw persistence stays in `flux_data.db`
- `promeos.db` remains untouched by SF5 ingestion
- promotion, PRM matching, product tables, and business normalization remain outside SF5

## Current Codebase Anchors

Existing raw ingestion is concentrated under `backend/data_ingestion/enedis/`.

Likely touched modules:

- `backend/data_ingestion/enedis/enums.py`
- `backend/data_ingestion/enedis/decrypt.py`
- `backend/data_ingestion/enedis/models.py`
- `backend/data_ingestion/enedis/migrations.py`
- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/cli.py`
- `backend/routes/enedis.py`
- `backend/data_ingestion/enedis/parsers/__init__.py`
- new `backend/data_ingestion/enedis/filename.py`
- new `backend/data_ingestion/enedis/transport.py`
- new `backend/data_ingestion/enedis/containers.py`
- new `backend/data_ingestion/enedis/parsers/r63.py`
- new `backend/data_ingestion/enedis/parsers/r64.py`
- new `backend/data_ingestion/enedis/parsers/c68.py`

Likely touched tests:

- `backend/data_ingestion/enedis/tests/test_decrypt.py`
- `backend/data_ingestion/enedis/tests/test_models.py`
- `backend/data_ingestion/enedis/tests/test_pipeline.py`
- `backend/data_ingestion/enedis/tests/test_pipeline_full.py`
- `backend/data_ingestion/enedis/tests/test_cli.py`
- `backend/data_ingestion/enedis/tests/test_integration.py`
- `backend/data_ingestion/enedis/tests/test_e2e_real_files.py`
- `backend/tests/test_flux_data_split.py`
- `backend/tests/test_enedis_api.py`
- new `backend/data_ingestion/enedis/tests/test_filename_sf5.py`
- new `backend/data_ingestion/enedis/tests/test_transport_sf5.py`
- new `backend/data_ingestion/enedis/tests/test_containers_sf5.py`
- new `backend/data_ingestion/enedis/tests/test_parsers_r63.py`
- new `backend/data_ingestion/enedis/tests/test_parsers_r64.py`
- new `backend/data_ingestion/enedis/tests/test_parsers_c68.py`
- new `backend/data_ingestion/enedis/tests/test_pipeline_sf5.py`

## Codebase-Fit Notes

- `pipeline.py` currently means "supported flux = decrypt to XML, then parse"; do not wire SF5 into that tuple until a transport/payload abstraction exists.
- Keep `decrypt_file()` behavior stable for legacy XML. Add byte-oriented helpers beside it so SF5 can unwrap AES without XML validation.
- `cli.py` and `routes/enedis.py` currently call `load_keys_from_env()` before scanning. SF5 requires optional/lazy key loading so direct ZIP files can ingest when keys are absent.
- Test DB fixtures call `FluxDataBase.metadata.create_all()`. New raw models must be imported before metadata creation in fixtures and API/split tests.
- `ENEDIS_RAW_TABLES` is the split-boundary contract used by `tests/test_flux_data_split.py`; add SF5 raw tables there and keep them out of main `models.base.Base`.
- Existing retry, idempotence, republication, and no measure-level deduplication behavior is product behavior from SF1-SF4. Preserve it unless a milestone explicitly says otherwise.

## Ordering Dependencies

1. Add classification and filename parsing before parser or pipeline work.
2. Add raw DB models and migrations before pipeline storage work.
3. Add optional/lazy key loading and transport/container helpers before integrating SF5 into `ingest_file()`.
4. Refactor `pipeline.py` to support a parsed-result handler contract while keeping the legacy XML path green.
5. Add parser modules before enabling `R63`, `R64`, and `C68` dispatch.
6. Update CLI/API/stats after raw rows exist and `measures_count` semantics are stable.
7. Add real-sample tests last, and keep them opt-in so CI does not depend on sensitive local payloads.

## Milestone 1 - Classification And Filename Metadata

### Functional Outcome

The ingestion layer can identify supported SF5 files and known unsupported Enedis files before any parsing. Unsupported-but-known files are recorded as `SKIPPED`, not `UNKNOWN`.

What this means for the user:

If an operator drops `R63A`, `R66`, or `CR.M023` into the folder, the run reports "recognized but skipped" instead of looking broken or mysterious.

### Implementation Scope

Add new `FluxType` values:

- supported: `R63`, `R64`, `C68`
- known skipped: `R63A`, `R63B`, `R64A`, `R64B`, `R65`, `R66`, `R66B`, `R67`, `CR_M023`

Add filename parser for:

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<numSequence>_<horodate>.<extension>
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<codeContratOrSiren>_<numSequence>_<horodate>.zip
```

Parser output should preserve:

- `code_flux`
- `mode_publication`
- `type_donnee`
- `id_demande`
- `num_sequence`
- `publication_horodatage`
- `siren_publication`
- `code_contrat_publication`
- original filename/member name
- extension

For the seven-token R6X-REC shape, populate `siren_publication` only for SIREN-like identifiers; otherwise populate `code_contrat_publication`.

Keep classification conservative:

- Extend the current `classify_flux()` rules without broad substring catches that could reclassify legacy files.
- Classify the full SF5 code before any prefix-like code. For example, `R63A` must be evaluated before `R63`.
- Treat `CR.M023`, `CR_M023`, and comparable filename punctuation variants as `CR_M023` only when the filename code segment really denotes the compte rendu.
- Preserve the original filename/member casing in parsed metadata, but compare code segments case-insensitively.

### Files Likely Touched

- `backend/data_ingestion/enedis/enums.py`
- `backend/data_ingestion/enedis/decrypt.py`
- new `backend/data_ingestion/enedis/filename.py`
- `backend/data_ingestion/enedis/tests/test_decrypt.py`
- new `backend/data_ingestion/enedis/tests/test_filename_sf5.py`

### Acceptance Criteria

- `R63`, `R64`, and `C68` classify exactly from Enedis publication filenames.
- `R63A/B`, `R64A/B`, `R65`, `R66`, `R66B`, `R67`, and standalone `CR.M023` classify as known flux types.
- Known unsupported SF5-adjacent fluxes are included in `SKIP_FLUX_TYPES`.
- `R63A/B` and `R64A/B` are never normalized to `R63` or `R64`.
- Filename parsing is case-insensitive for technical matching but preserves original raw values.
- Invalid SF5 filename shapes produce a structured filename error for supported families.
- Legacy classifications for `R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`, `R172`, `X14`, and `HDM` remain unchanged.

### Test Coverage

- Unit tests for M023 six-token filenames.
- Unit tests for REC/legacy seven-token filenames.
- Unit tests for SIREN vs non-SIREN extra segment preservation.
- Classification tests for every supported and known-skipped code.
- Regression tests for legacy `R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`, `R172`, `X14`, `HDM`.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_decrypt.py \
  data_ingestion/enedis/tests/test_filename_sf5.py
```

### Risks

- Filename pattern matching may accidentally catch legacy files if rules are too broad.
- `CR.M023` naming can appear with punctuation, so classification should explicitly test observed variants.

## Milestone 2 - Raw DB Schema And Bootstrap

### Functional Outcome

SF5 has raw archive tables in `flux_data.db` and queryable filename metadata on `enedis_flux_file`.

What this means for the user:

The raw archive remains searchable by request ID, sequence, payload format, and flux family without leaking raw ingestion into the main application database.

### Implementation Scope

Extend `EnedisFluxFile` with nullable columns:

- `code_flux`
- `type_donnee`
- `id_demande`
- `mode_publication`
- `payload_format`
- `num_sequence`
- `siren_publication`
- `code_contrat_publication`
- `publication_horodatage`
- `archive_members_count`

Add split R63/R64 raw tables:

- `EnedisFluxMesureR63` / `enedis_flux_mesure_r63`: one row per `R63` load-curve point
- `EnedisFluxIndexR64` / `enedis_flux_index_r64`: one row per `R64` cumulative index value
- raw strings only; no numeric or timezone normalization
- R63 indexes on `(point_id, horodatage)`, `flux_file_id`, and `(point_id, grandeur_physique)`
- R64 indexes on `(point_id, horodatage)`, `flux_file_id`, `(point_id, grandeur_physique)`, and calendar/class context
- optional `enedis_flux_mesure_r6x` compatibility object is a read-only SQL view, never canonical storage

Add `EnedisFluxItcC68` table:

- table name: `enedis_flux_itc_c68`
- one row per C68 PRM snapshot
- `payload_raw` stores full per-PRM JSON text
- extracted allowlisted columns only, including SIRET/SIREN and selected technical/power fields
- indexes on `point_id`, `flux_file_id`, `(point_id, flux_file_id)`, `siret`, `siren`

Update `ENEDIS_RAW_TABLES` and idempotent migrations.

Implementation notes:

- New models must inherit from `FluxDataBase` through `data_ingestion.enedis.models.Base`, not `models.base.Base`.
- Add new nullable `enedis_flux_file` columns through both the ORM model and `_add_enedis_columns()`.
- Add the three canonical raw table names to `ENEDIS_RAW_TABLES`; this is how the raw DB bootstrap and split tests know about them.
- Keep all SF5 metadata columns nullable so existing SF1-SF4 rows and databases migrate additively.
- Store `payload_format` as a short raw string such as `JSON` or `CSV`; do not infer product semantics from it.

### Files Likely Touched

- `backend/data_ingestion/enedis/models.py`
- `backend/data_ingestion/enedis/migrations.py`
- `backend/tests/test_flux_data_split.py`
- `backend/data_ingestion/enedis/tests/test_models.py`

### Acceptance Criteria

- `run_flux_data_migrations()` creates `enedis_flux_mesure_r63`, `enedis_flux_index_r64`, and `enedis_flux_itc_c68` in `flux_data.db`.
- `run_flux_data_migrations()` splits any legacy physical `enedis_flux_mesure_r6x` rows into the new R63/R64 tables, verifies row counts, drops the old physical table, and recreates `enedis_flux_mesure_r6x` as a non-canonical compatibility view.
- `run_flux_data_migrations()` additively creates all new nullable `enedis_flux_file` metadata columns when missing.
- `Base.metadata.create_all()` for `promeos.db` plus main migrations does not create SF5 raw tables.
- Raw table relationships cascade on file delete like existing raw tables.
- Raw value columns store strings.
- No unique constraints are added at measurement/snapshot level.
- Existing databases gain the new `enedis_flux_file` columns without dropping or rewriting legacy rows.

### Test Coverage

- Model creation tests for all three new canonical tables.
- Duplicate raw rows allowed.
- Relationship/cascade tests.
- Migration idempotence tests.
- Cross-DB split tests proving `promeos.db` does not receive raw tables.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_models.py \
  tests/test_flux_data_split.py
```

### Risks

- `database/migrations.py` delegates some raw migrations; ensure new raw tables stay under `FluxDataBase`.
- API tests that create in-memory raw DBs must import models before `metadata.create_all()`.

## Milestone 3 - Transport Resolver And Container Validation

### Functional Outcome

The pipeline can decide per file whether bytes are already usable or need AES unwrap, then pass coherent XML/ZIP payloads to family-specific handlers.

What this means for the user:

Direct SF5 ZIP publications can ingest without AES keys, while encrypted legacy or encrypted SF5 files still work when keys exist. Missing keys for one encrypted file do not block direct-openable files in the same directory.

### Implementation Scope

Keep legacy `decrypt_file()` available for XML compatibility, but add a lower-level AES unwrap helper that returns plaintext bytes without XML validation.

Add a transport resolver:

```text
raw file bytes
-> check expected family payload/container
-> if already usable, continue
-> otherwise try AES unwrap when keys are available
-> validate resolved bytes as expected XML or ZIP
-> return resolved bytes plus transport metadata
```

Recommended resolver contract:

```python
ResolvedPayload(
    bytes: bytes,
    transport: str,  # direct or aes
    payload_kind: str,  # xml or zip
    key_index: int | None,
)
```

Keys should be supplied as an optional callable or optional list. The resolver should load keys only after direct-open checks fail and only for files that are eligible for AES unwrap.

Container rules:

- legacy families require XML after resolver.
- `R63`/`R64` require a direct ZIP with exactly one non-directory JSON or CSV member.
- `C68` requires a primary ZIP with 1..10 non-directory members, each a secondary ZIP.
- ZIP directory entries are ignored.
- Any non-directory sidecar such as `.DS_Store`, `__MACOSX`, direct JSON/CSV inside C68 primary, `CR.M023`, or extra payload member is fatal.
- SF5 decrypted ZIP/JSON/CSV artifacts are never written to `archive_dir`; only existing XML audit behavior remains.

### Files Likely Touched

- `backend/data_ingestion/enedis/decrypt.py`
- new `backend/data_ingestion/enedis/transport.py`
- new `backend/data_ingestion/enedis/containers.py`
- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/tests/conftest.py`
- new `backend/data_ingestion/enedis/tests/test_transport_sf5.py`
- new `backend/data_ingestion/enedis/tests/test_containers_sf5.py`

### Acceptance Criteria

- Direct-openable SF5 ZIP files ingestable without loading keys.
- Encrypted synthetic `R63`, `R64`, and `C68` ZIP fixtures unwrap in memory with test keys.
- Missing keys only fail files that need decrypt/unwrap.
- Existing encrypted legacy XML flows still decrypt and parse as before.
- Invalid ZIPs produce file-level `ERROR`.
- R63/R64 extra non-directory archive members produce file-level `ERROR`.
- C68 invalid primary/secondary ZIP or sidecar produces file-level `ERROR`.
- No decrypted SF5 artifact appears in `archive_dir` or filesystem temp output.

### Test Coverage

- Direct ZIP single JSON and single CSV member.
- AES-wrapped ZIP for `R63`, `R64`, and nested `C68`.
- Missing-key behavior for direct vs encrypted files in one run.
- Invalid outer ZIP and invalid secondary ZIP.
- Sidecar and extra member failures.
- Legacy `decrypt_file()` tests unchanged or updated only for compatible helper extraction.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_decrypt.py \
  data_ingestion/enedis/tests/test_transport_sf5.py \
  data_ingestion/enedis/tests/test_containers_sf5.py \
  data_ingestion/enedis/tests/test_pipeline.py
```

### Risks

- Relaxing upfront key loading affects CLI/API behavior; regression tests must prove legacy encrypted XML files still fail clearly when keys are needed.
- Archive validation must not silently ignore hidden macOS files because the PRD treats those as fatal sidecars.
- Be careful not to write a direct-ZIP branch only for SF5; encrypted SF5 still needs the same resolver path.

## Milestone 4 - R63 Parser And Storage

### Functional Outcome

Punctual `R63` JSON and CSV load curve publications archive into `enedis_flux_mesure_r63`.

What this means for the user:

Fine-grain R63 curve points become available in the raw DB with PRM, timestamp, value, quality, and publication metadata preserved for later staging.

### Implementation Scope

Add `parsers/r63.py` with pure parser functions and dataclasses.

JSON flattening:

- top-level `header`
- `mesures[]`
- `grandeur[]`
- `points[]`
- one output row per `points[]` leaf

CSV flattening:

- delimiter `;`
- UTF-8 and UTF-8-SIG
- header-name based mapping with accent/case/spacing normalization for matching, while preserving raw header names in diagnostics
- mandatory headers:
  - `Identifiant PRM`
  - `Date de début` / `Date de debut`
  - `Date de fin`
  - `Grandeur physique`
  - `Grandeur métier` / `Grandeur metier`
  - `Etape métier` / `Etape metier`
  - `Unité` / `Unite`
  - `Horodate`
  - `Valeur`
  - `Nature`
  - `Pas`

Preserve raw fields:

- PRM
- period start/end
- `etape_metier`
- `mode_calcul`
- `grandeur_metier`
- `grandeur_physique`
- `unite`
- `horodatage`
- `valeur`
- `nature_point`
- `type_correction`
- `pas`
- `indice_vraisemblance`
- `etat_complementaire`

Add R63 pipeline storage into `EnedisFluxMesureR63`.

### Files Likely Touched

- new `backend/data_ingestion/enedis/parsers/r63.py`
- `backend/data_ingestion/enedis/parsers/__init__.py`
- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/tests/test_parsers_r63.py`
- `backend/data_ingestion/enedis/tests/test_pipeline_sf5.py`

### Acceptance Criteria

- `R63` JSON parses and stores one row per point.
- `R63` CSV parses and stores one row per CSV line.
- Filename metadata and payload header metadata are stored in `header_raw`.
- Payload member filename must match outer archive request metadata.
- `payload_format` is `JSON` or `CSV`.
- `measures_count` equals inserted R63 point rows.
- Unknown JSON fields produce `header_raw.warnings` rather than hard failure when structure is ingestable.

### Test Coverage

- Synthetic JSON fixture with multiple PRMs/grandeurs/points.
- Synthetic CSV fixture with mandatory columns and optional quality columns.
- Header-name based CSV mapping.
- Missing mandatory header fails.
- Malformed mandatory row fails and rolls back.
- Payload filename mismatch fails.
- Direct ZIP with no keys succeeds.
- AES-wrapped synthetic R63 succeeds with test keys.
- Parser unit tests stay pure and do not require database setup; pipeline tests cover storage.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_parsers_r63.py \
  data_ingestion/enedis/tests/test_pipeline_sf5.py
```

### Risks

- Real R63 JSON may contain schema drift; parser should be strict on structural essentials but tolerant on extra fields.
- CSV accents may vary; tests should include observed accent/no-accent header variants where already known.

## Milestone 5 - R64 Parser And Storage

### Functional Outcome

Punctual `R64` JSON and CSV index publications archive into `enedis_flux_index_r64`.

What this means for the user:

Raw index values are preserved with their read context, grid/calendar/class, and plausibility information for future interpretation.

R64 values are cumulative indexes, not interval load-curve points. They must stay physically separate from R63 so SF6 cannot accidentally sum or chart indexes as interval consumption.

### Implementation Scope

Add `parsers/r64.py` with pure parser functions and dataclasses.

JSON flattening:

- `mesures[]`
- `periode.dateDebut/dateFin`
- `contexte[]`
- `grandeur[]`
- `calendrier[]`
- `classeTemporelle[]`
- `valeur[]`
- one output row per reachable `valeur[]` leaf

CSV flattening:

- delimiter `;`
- UTF-8 and UTF-8-SIG
- header-name based mapping with accent/case/spacing normalization for matching, while preserving raw header names in diagnostics
- mandatory headers:
  - `Identifiant PRM`
  - `Date de début` / `Date de debut`
  - `Date de fin`
  - `Grandeur physique`
  - `Grandeur métier` / `Grandeur metier`
  - `Etape métier` / `Etape metier`
  - `Unité` / `Unite`
  - `Horodate`
  - `Valeur`

Preserve raw fields:

- PRM
- period start/end
- `etape_metier`
- `contexte_releve`
- `type_releve`
- `motif_releve`
- quantity fields and unit
- grid/calendar/class/cadran context
- timestamp
- value
- plausibility index

No cross-product synthesis is allowed. Ambiguous or disconnected JSON structures should fail the physical file.

### Files Likely Touched

- new `backend/data_ingestion/enedis/parsers/r64.py`
- `backend/data_ingestion/enedis/parsers/__init__.py`
- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/tests/test_parsers_r64.py`
- `backend/data_ingestion/enedis/tests/test_pipeline_sf5.py`

### Acceptance Criteria

- `R64` JSON parses and stores one row per value leaf.
- `R64` CSV parses and stores one row per CSV line.
- Calendar, grid, class, and cadran fields are preserved when available.
- `payload_format` is stored.
- `measures_count` equals inserted R64 value rows.
- Structurally ambiguous JSON fails cleanly with no partial inserts.
- Unknown JSON fields produce warnings when the core structure remains ingestable.

### Test Coverage

- Synthetic JSON fixture with context/calendar/class/value nesting.
- Synthetic CSV fixture with observed R64 headers.
- Missing mandatory CSV header fails.
- Ambiguous JSON structure fails.
- Payload filename mismatch fails.
- Direct ZIP with no keys succeeds.
- AES-wrapped synthetic R64 succeeds with test keys.
- Parser unit tests stay pure and do not require database setup; pipeline tests cover storage.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_parsers_r64.py \
  data_ingestion/enedis/tests/test_pipeline_sf5.py
```

### Risks

- R64 JSON relationships can be represented through nested IDs; implementation should follow real structure and avoid speculative cartesian joins.
- The parser should preserve high-power fields such as `DD`, `DE`, `DQ`, `PMA`, and `TF` when present.

## Milestone 6 - C68 Parser, Corrected Sequence Rule, And Storage

### Functional Outcome

C68 primary archives with one or more secondary archives ingest into one raw snapshot row per PRM.

What this means for the user:

Technical and contractual PRM snapshots are archived exactly enough for future staging while preserving the full raw payload inside `flux_data.db`.

### Implementation Scope

Add `parsers/c68.py` with pure parser functions and dataclasses.

Archive rules:

- primary archive filename must parse as `C68`
- primary sequence must be `00001`
- primary ZIP must contain 1..10 secondary ZIPs
- every secondary ZIP contains exactly one JSON or CSV payload
- one payload format per physical C68 archive; mixed JSON/CSV is fatal
- no sidecars, direct payloads, or `CR.M023` inside primary archive

Corrected C68 sequence/timestamp rule:

- primary archive sequence is `00001`
- secondary sequences are contiguous `00001..N`
- secondary archive sequence and payload sequence must match each other
- secondary archive timestamp and payload timestamp must match each other
- secondary sequence/timestamp do not need to equal the primary archive sequence/timestamp
- request-level metadata must match across primary, secondary, and payload:
  - `code_flux`
  - `mode_publication`
  - `type_donnee`
  - `id_demande`

JSON parsing:

- top-level array of PRM objects
- one row per PRM object
- missing `idPrm` is fatal
- full PRM object stored in `payload_raw`
- `situationsContractuelles[]` remains nested
- extracted contractual columns use the sole `situationsContractuelles[]` item when only one exists, even if `dateDebut` is absent
- when multiple contractual situations exist, extracted contractual columns use latest parseable `dateDebut`
- ambiguous multi-situation contractual selection stores raw payload, nulls summary columns, and records a structured warning
- real-file reality check on 2026-04-26: local row `enedis_flux_itc_c68.id = 22` / PRM `30000119007533` had a single undated contractual situation with `segment = C1`, `informationsContractuelles.etatContractuel = SERVC`, and `structureTarifaire.formuleTarifaireAcheminement.code = HTALU5`; the parser must extract those dedicated columns instead of treating the row as ambiguous
- also extract observed nested v1.2 aliases such as `situationComptage.dispositifComptage.media`, `situationComptage.caracteristiquesReleve.periodicite`, `clientFinal.informationsClient.personneMorale.numSiret`, and `numSiren`

CSV parsing:

- delimiter `;`
- UTF-8 and UTF-8-SIG
- one row per CSV line
- missing `PRM` header or blank row PRM is fatal
- accept both legacy 207-column and v1.2 211-column layouts
- preserve unknown columns in `payload_raw`
- observed CSV reality check on 2026-04-26: the flattened `Puissance souscrite` column may carry the value and unit together, for example `36 kVA` or `36kVA`; parser/storage must split it into `puissance_souscrite_valeur = 36` and `puissance_souscrite_unite = kVA`, while leaving the original CSV cell in `payload_raw`
- extract v1.2 additions when present:
  - `Type Injection`
  - `Refus de pose Linky`
  - `Date refus de pose Linky`
  - `Borne Fixe`

Extraction policy:

- `payload_raw` is canonical.
- Extract only allowlisted query columns.
- Do not extract person names, emails, phone numbers, postal address lines, street details, civilite, prenom, nom, free-text contact fields, or interlocutor contact details.
- Extract SIRET/SIREN.
- Store power values and units as raw strings, with no numeric conversion.
- When CSV provides a combined subscribed-power cell, split value and unit before writing the dedicated columns; do not let `puissance_souscrite_valeur` contain text such as `36 kVA`.

Storage notes:

- `payload_raw` should contain the per-PRM JSON object or a JSON object reconstructed from the CSV row, including unknown columns.
- `header_raw.archive_manifest` should record the primary archive, each secondary archive, payload filename, payload format, row count, and any structured warnings.
- Do not persist secondary ZIP bytes or extracted JSON/CSV files to ordinary filesystem paths.

### Files Likely Touched

- new `backend/data_ingestion/enedis/parsers/c68.py`
- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/models.py`
- `backend/data_ingestion/enedis/tests/test_parsers_c68.py`
- `backend/data_ingestion/enedis/tests/test_containers_sf5.py`
- `backend/data_ingestion/enedis/tests/test_pipeline_sf5.py`

### Acceptance Criteria

- C68 JSON ingests into `enedis_flux_itc_c68`.
- C68 CSV ingests into `enedis_flux_itc_c68`.
- C68 legacy 207-column CSV and v1.2 211-column CSV both ingest.
- C68 CSV combined `Puissance souscrite` cells are split into separate value/unit raw columns.
- `measures_count` equals PRM snapshot rows, not archive/member count.
- `archive_members_count` records first-level member count.
- `header_raw.archive_manifest` records secondary archive and payload names.
- Multi-secondary C68 archive with secondary sequence/timestamp differing from primary succeeds when each secondary matches its payload.
- Sequence gaps fail.
- Secondary/payload sequence mismatch fails.
- Secondary/payload timestamp mismatch fails.
- Primary sequence other than `00001` fails.
- Mixed JSON/CSV secondary payloads fail.
- One invalid secondary rolls back the whole physical file.
- Missing JSON `idPrm` or CSV `PRM` fails and rolls back.
- Unknown fields/columns are preserved and warning-recorded.
- A single undated `situationsContractuelles[]` item is accepted as the selected contractual situation and projects `segment`, contract status, and tariff fields.

### Test Coverage

- Synthetic C68 JSON top-level array.
- Synthetic C68 JSON regression matching the real id `22` nested shape: one undated contractual situation projects `segment = C1`, `etat_contractuel = SERVC`, `formule_tarifaire_acheminement = HTALU5`, `media_comptage = IP`, and `periodicite_releve = QUOTID`.
- Synthetic C68 CSV 207-column-style fixture.
- Synthetic C68 CSV 211-column-style fixture with fake `Type Injection`, `Refus de pose Linky`, `Date refus de pose Linky`, and `Borne Fixe`.
- Synthetic C68 CSV fixture where `Puissance souscrite` is a combined value/unit cell, with assertions that value and unit are stored separately.
- Multi-secondary archive where primary timestamp differs from secondary/payload timestamp.
- Sequence gap failure.
- Secondary/payload mismatch failures.
- Mixed payload format failure.
- Sidecar failure.
- Ambiguous `situationsContractuelles[]` warning test.
- Missing PRM fatal tests.
- Rollback test proving no partial rows after a later secondary fails.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_parsers_c68.py \
  data_ingestion/enedis/tests/test_containers_sf5.py \
  data_ingestion/enedis/tests/test_pipeline_sf5.py
```

### Risks

- C68 is sensitive and wide; committed fixtures must remain synthetic or sanitized.
- C68 CSV headers are numerous; tests should prove header-name mapping rather than positional mapping.
- Full payload persistence is appropriate for the raw DB but needs production access/retention policy before deployment beyond POC.

## Milestone 7 - Unified Pipeline Integration

### Functional Outcome

`ingest_file()` and `ingest_directory()` process legacy XML, R63/R64 ZIP, C68 nested ZIP, known skipped files, retry, idempotence, and republication through one orchestration path.

What this means for the user:

The same command or API call works for mixed Enedis folders. Operators do not need a separate "new flow" ingestion process.

### Implementation Scope

Refactor dispatch from `parser_fn(xml_bytes)` to family-specific extraction handlers while preserving current orchestration:

1. classify
2. idempotence/retry/republication
3. skip known unsupported types
4. resolve transport
5. parse container/payload
6. create/update `EnedisFluxFile`
7. batch insert rows
8. commit or rollback

Suggested internal handler contract:

```python
ParsedIngestionResult(
    header_raw=dict,
    rows_iterable=...,
    measures_count=int,
    payload_format=str | None,
    archive_members_count=int | None,
    filename_metadata=...
)
```

Recommended implementation order inside this milestone:

1. Introduce the result dataclass and adapt legacy XML handlers to return it without behavior changes.
2. Keep the existing `_store_r4x`, `_store_r171`, `_store_r50`, and `_store_r151` row generation intact behind the adapter.
3. Change `keys` from mandatory list to optional list/callable at the pipeline boundary, then update call sites.
4. Wire direct ZIP/container resolution for SF5 behind feature-specific handlers.
5. Add R63, R64, and C68 storage handlers only after legacy regression tests pass with the new contract.

Keep existing legacy behavior:

- same file hash idempotence
- same retry and `PERMANENTLY_FAILED` logic
- same same-filename/different-hash republication versioning
- same no measure-level deduplication
- same `archive_dir` XML-only audit behavior
- same counter keys returned by `ingest_directory()` unless adding fields is explicitly covered by CLI/API tests

### Files Likely Touched

- `backend/data_ingestion/enedis/pipeline.py`
- `backend/data_ingestion/enedis/decrypt.py`
- `backend/data_ingestion/enedis/transport.py`
- `backend/data_ingestion/enedis/containers.py`
- `backend/data_ingestion/enedis/models.py`
- `backend/data_ingestion/enedis/tests/test_pipeline.py`
- `backend/data_ingestion/enedis/tests/test_pipeline_full.py`
- new `backend/data_ingestion/enedis/tests/test_pipeline_sf5.py`

### Acceptance Criteria

- Legacy SF1-SF4 pipeline tests pass unchanged or with only expected lazy-key updates.
- `R63`, `R64`, and `C68` supported files return `FluxStatus.PARSED`.
- Known unsupported SF5-adjacent files return `FluxStatus.SKIPPED`.
- Missing AES keys do not fail direct-openable files.
- Files needing decrypt with missing keys become `ERROR` records.
- Storage errors rollback rows and record file-level `ERROR`.
- C68 partial secondary failure leaves no C68 rows for that physical file.
- Republication works for SF5 files exactly as for legacy files.
- `ingest_directory(dry_run=True)` classifies SF5 and known-skipped files without loading keys or mutating the DB.

### Test Coverage

- Mixed directory: one legacy encrypted XML, one direct R63, one C68, one known skipped, one corrupt.
- Idempotence for SF5 direct files.
- Republication for R63 or C68 same filename/different hash.
- Retry after SF5 parse error.
- Permanent failure after max retries.
- Rollback on simulated DB insert failure.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_pipeline.py \
  data_ingestion/enedis/tests/test_pipeline_full.py \
  data_ingestion/enedis/tests/test_pipeline_sf5.py
```

### Risks

- Refactoring `pipeline.py` is the highest regression point. Keep legacy handlers small and covered before wiring SF5.
- Batch insert row dictionaries must align exactly with SQLAlchemy column names.
- The current code catches `DecryptError` and parser-specific errors separately. The new handler path should preserve file-level `ERROR` recording for container, filename, parser, and storage failures.

## Milestone 8 - CLI, API, And Stats Surfaces

### Functional Outcome

CLI reports and REST stats include SF5 totals while continuing to read from the raw DB dependency.

What this means for the user:

After a run, operators can see separate R63 load-curve, R64 index, compatibility R6X aggregate, and C68 row totals without querying SQLite manually.

### Implementation Scope

CLI:

- stop requiring `load_keys_from_env()` before every run
- pass lazy/optional key resolver or loaded optional keys into pipeline
- include raw archive totals:
  - `R4x`
  - `R171`
  - `R50`
  - `R151`
  - `R63`
  - `R64`
  - `R6X` compatibility aggregate
  - `C68`
  - `TOTAL`

API:

- update `/api/enedis/ingest` to match lazy key behavior
- extend `FluxFileResponse`/detail with SF5 metadata if appropriate
- extend `/api/enedis/stats` with:
  - `r63`
  - `r64`
  - `r6x`
  - `c68`
  - total including all raw rows
  - distinct PRMs from R63, R64, and C68
  - optional source format breakdown if cheap

Keep promotion endpoints unchanged. SF5 must not wire R63/R64/C68 into SF6 promotion unless a separate staging milestone explicitly does that.

Compatibility notes:

- Existing CLI/API tests patch `load_keys_from_env()` and `ingest_directory()`; update them to assert lazy behavior rather than eager preflight failure.
- Preserve additive API response changes. Do not remove existing fields from `FluxFileResponse`, `MeasureStats`, `PrmStats`, or `StatsResponse`.
- Stats currently derive row totals from `EnedisFluxFile.measures_count` and distinct PRMs from a `UNION` across raw measure tables. Add R63, R64, and C68 explicitly to both calculations; keep `r6x = r63 + r64` only as a compatibility aggregate.

### Files Likely Touched

- `backend/data_ingestion/enedis/cli.py`
- `backend/routes/enedis.py`
- `backend/data_ingestion/enedis/tests/test_cli.py`
- `backend/tests/test_enedis_api.py`

### Acceptance Criteria

- CLI runs with direct-openable SF5 files even when AES env vars are absent.
- CLI still records per-file `ERROR` for encrypted files that need missing keys.
- CLI report displays separate R63/R64 totals plus an R6X compatibility aggregate and C68 totals.
- `/api/enedis/stats` returns separate R63/R64 totals plus an R6X compatibility aggregate and C68 row totals.
- `/api/enedis/stats` distinct PRM count includes R63, R64, and C68 PRMs.
- API and CLI still use `get_flux_data_db` / `FluxDataSessionLocal`, not main DB.
- Promotion endpoints continue to use main `get_db` plus raw `get_flux_data_db` exactly as before.

### Test Coverage

- CLI normal run with synthetic SF5 direct ZIP.
- CLI missing-key mixed run.
- CLI report output includes R6X/C68.
- API stats seeded with R6X/C68 rows.
- API ingest missing-key behavior.
- Flux file detail returns `header_raw` with SF5 `filename_metadata`, `archive_manifest`, and warnings.

### Validation Commands

```bash
cd backend
pytest data_ingestion/enedis/tests/test_cli.py \
  tests/test_enedis_api.py
```

### Risks

- Existing API schemas may be consumed by frontend code. Additive fields are safer than shape changes.
- Current stats use `measures_count`; ensure C68 row count semantics are clearly documented in model comments and tests.

## Milestone 9 - Fixtures, Real-Sample Tests, And Regression Gate

### Functional Outcome

The default test suite uses synthetic fixtures, while local engineers can opt into real corpus validation without committing sensitive C68 payloads.

What this means for the user:

CI remains safe and deterministic, and local validation can still prove the implementation against observed Enedis files.

### Implementation Scope

Default synthetic fixtures:

- R63 JSON and CSV direct ZIPs
- R64 JSON and CSV direct ZIPs
- C68 JSON nested ZIP
- C68 CSV nested ZIP with 207-column-style header
- C68 CSV nested ZIP with 211-column-style header and fake v1.2 fields
- malformed archives for rollback tests
- AES-wrapped versions for R63/R64/C68 using existing test key helpers

Fixture implementation notes:

- Extend existing AES test helpers in `backend/data_ingestion/enedis/tests/conftest.py` instead of adding production-only crypto helpers for tests.
- Build ZIPs in memory with `zipfile` and synthetic JSON/CSV strings; keep fixture values fake and small.
- For C68, include one fixture with two secondary ZIPs to exercise sequence/timestamp rules.

Opt-in real tests:

- gated by explicit env var such as `PROMEOS_RUN_REAL_SF5_TESTS=1`
- skip unless `flux_enedis/` exists
- do not require committing real payloads
- sample references may include:
  - `flux_enedis/R63/ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip`
  - `flux_enedis/R63/ENEDIS_R63_P_CdC_M057W4YR_00001_20231016154951.zip`
  - `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip`
  - `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06CX26D_00001_20240523105124.zip`
  - `flux_enedis/C68/ENEDIS_C68_P_ITC_M05GIGM1_00001_20231204101954.zip`
  - `flux_enedis/C68/ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip`
  - `flux_enedis/C68/ENEDIS_C68_P_ITC_M08GV8IG_00001_20250721134328.zip`

Observed malformed samples can be used only in opt-in tests:

- `flux_enedis/R63/ENEDIS_R63_P_CdC_M06DSGVE_00001_20240528163243.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M082FQJM_00001_20250424205829.zip`

### Files Likely Touched

- `backend/data_ingestion/enedis/tests/conftest.py`
- `backend/data_ingestion/enedis/tests/test_e2e_real_files.py`
- `backend/data_ingestion/enedis/tests/test_integration.py`
- new synthetic fixture helpers under tests, not production modules

### Acceptance Criteria

- Default tests do not depend on real Enedis files.
- No sensitive real C68 payloads are committed.
- Opt-in real tests cover R63 JSON/CSV, R64 JSON/CSV, C68 JSON/CSV.
- Opt-in tests cover malformed real R63/C68 samples as clean `ERROR`.
- Full legacy test suite remains green.

### Test Coverage

- Synthetic fixture builders for direct and encrypted SF5 archives.
- Real file discovery updated for R63/R64/C68.
- Real SF5 tests skipped unless explicitly enabled.
- Cross-family full directory test can build a symlink tree with supported legacy and SF5 files when enabled.

### Validation Commands

Default:

```bash
cd backend
pytest data_ingestion/enedis/tests tests/test_flux_data_split.py tests/test_enedis_api.py
```

Opt-in real SF5:

```bash
cd backend
PROMEOS_RUN_REAL_SF5_TESTS=1 pytest \
  data_ingestion/enedis/tests/test_e2e_real_files.py \
  data_ingestion/enedis/tests/test_integration.py
```

### Risks

- Real corpus paths live outside the repo root; tests must skip gracefully.
- Real C68 payloads are sensitive; never copy them into committed fixture folders.

## Final End-To-End Acceptance Gate

Run before opening the implementation PR:

```bash
cd backend
pytest data_ingestion/enedis/tests tests/test_flux_data_split.py tests/test_enedis_api.py
```

Recommended focused gates during development:

```bash
cd backend
pytest data_ingestion/enedis/tests/test_decrypt.py
pytest data_ingestion/enedis/tests/test_models.py tests/test_flux_data_split.py
pytest data_ingestion/enedis/tests/test_parsers_r63.py
pytest data_ingestion/enedis/tests/test_parsers_r64.py
pytest data_ingestion/enedis/tests/test_parsers_c68.py
pytest data_ingestion/enedis/tests/test_pipeline.py data_ingestion/enedis/tests/test_pipeline_sf5.py
pytest data_ingestion/enedis/tests/test_cli.py tests/test_enedis_api.py
```

Optional local corpus gate:

```bash
cd backend
PROMEOS_RUN_REAL_SF5_TESTS=1 pytest data_ingestion/enedis/tests/test_e2e_real_files.py
```

## Cross-Milestone Risks

- Legacy regression: `pipeline.py` currently assumes "supported means decrypt to XML"; refactor in small steps and keep legacy tests green after Milestone 3.
- Key loading: current CLI/API fail before scanning when keys are missing. SF5 requires per-file lazy behavior, so missing-key tests must cover direct-openable success and encrypted failure in the same run.
- C68 privacy: raw payload persistence is required for SF5 fidelity but must remain inside `flux_data.db`; do not write decrypted C68 JSON/CSV to ordinary file storage.
- C68 sequence rule: multi-secondary C68 must not incorrectly require secondary sequence/timestamp to equal the primary archive. The secondary archive and payload must match each other, and secondary sequences must be contiguous `00001..N`.
- Schema drift: unknown fields should be warnings when core structure is ingestable, but packaging/provenance mismatches are fatal.
- CSV variants: parse by header name, never by fixed column position.
- Database split: every new model must inherit from `FluxDataBase`, not the main `Base`.
- Test coupling: many existing tests call `ingest_file(..., keys)` directly. Keep backward-compatible call signatures where practical, or update tests in the same milestone as the signature change.
- File hash semantics: continue hashing the original physical file bytes, not decrypted or extracted payload bytes.

## Definition Of Done

- Legacy XML ingestion behavior for SF1-SF4 is preserved.
- `R63`, `R64`, and `C68` punctual files ingest into `flux_data.db`.
- `R63A/B`, `R64A/B`, `R65`, `R66`, `R66B`, `R67`, and `CR_M023` are recognized and skipped.
- Filename metadata is parsed, stored, and used for archive coherence checks.
- Transport resolver supports direct-openable and encrypted deliveries per file.
- C68 corrected sequence/timestamp rule is covered by tests.
- Synthetic fixtures cover default CI without sensitive real payloads.
- Opt-in real-sample tests validate observed local corpus behavior.
- CLI and API stats expose R63, R64, R6X compatibility, and C68 raw archive totals.
- `promeos.db` remains untouched by SF5 raw ingestion.
