# SF5 — Enedis R6X + C68 Raw Ingestion Extension

> **Status**: PRD v0.2 — reviewed on 2026-04-23 against the post-SGE4.5 raw/product DB split; grounded in the roadmap, official local guides, JSON schemas, and real `flux_enedis/` samples inspected on 2026-04-18
> **Depends on**: SF1 (decrypt), SF2 (R4x raw archive), SF3 (R171/R50/R151 raw archive), SF4 (operationalization), SGE4.5 (raw DB split to `flux_data.db`) — complete and validated
> **Module**: `backend/data_ingestion/enedis/`
> **Goal**: extend the existing raw archive pipeline with `R63`, `R64`, and `C68` while preserving SF1-SF4 behavior for legacy XML flows and the SGE4.5 storage split to `flux_data.db`; SF5 must not create or mutate promoted/product tables in `promeos.db`

---

## 1. Problem Statement

SF1-SF4 delivered a stable raw-ingestion backbone for the first six Enedis SGE flows:

- `R4H`, `R4M`, `R4Q`
- `R171`
- `R50`
- `R151`

That pipeline assumes one dominant technical contract:

1. classify from filename
2. decrypt AES ciphertext with `KEY_n/IV_n`
3. validate XML
4. parse XML
5. store raw rows in dedicated raw archive tables in `flux_data.db`

The new SF5 scope breaks those assumptions in several ways:

- `R63` / `R64` are **R6X M023 response flows**, not legacy XML supplier-perimeter flows
- the official R6X guide states the publication format is **JSON**, with **CSV** also possible
- `C68` is an **ITC punctual response flow** whose delivery contract is a **primary ZIP containing 1..n secondary ZIPs**
- `C68` payloads contain large technical and contractual snapshots, not simple point-series measurements
- the real local corpus is mixed-format and includes malformed archives that must fail cleanly

If we do nothing, SF6 remains blocked: it already treats SF5 as the upstream prerequisite for raw ingestion of `R63` / `R64` and `C68`.

Since SGE4.5, this is no longer only a parser-extension question. The persistence contract now matters just as much as the payload contract:

- raw file registry rows, raw measurement/snapshot rows, retry history, and ingest-control tables stay in `flux_data.db`
- `promeos.db` remains reserved for later promotion/audit/product tables
- SF5 must preserve that split instead of reintroducing raw Enedis storage into the main platform database

### Why this matters

- `R63` is the raw source for fine-grain load curves outside the legacy R4x/R50 perimeter
- `R64` is the raw source for fine-grain indexes and related measurement contexts
- `C68` is the raw source for technical and contractual PRM snapshots needed by downstream power/contract features
- the platform now has a deliberate 2-DB contract: `flux_data.db` archives what Enedis sent, while `promeos.db` is where later functional promotion will happen
- the current ingestion CLI/API/stats should continue to work across mixed Enedis directories instead of splitting into a second ad hoc toolchain

SF5 therefore extends the existing pipeline, but stays strictly in the **raw archive layer** stored in `flux_data.db`. No functional promotion, PRM matching, or business normalization belongs here.

---

## 2. Research Findings

This draft is grounded in the local documentation under `docs/base_documentaire/enedis/guides_flux/` and the real archives under `flux_enedis/`.

### 2.1 Official Guide Findings

#### R6X (`Enedis.SGE.GUI.0503.Flux.R6X_v1.5.2.pdf`)

- `R63` = fine-grain load curves (`Courbes de charge`)
- `R64` = indexes (`Index`)
- `R65`, `R66`, `R67` also exist in the guide but are outside this SF5 roadmap scope
- the guide explicitly states the published file format is **JSON**
- it also documents **CSV** as a supported format for punctual M023 requests
- R6X M023 file nomenclature is:

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnees>_<idDemande>_<numSequence>_<horodate>.<extension>
```

- for `R63`, the JSON contract is `header + mesures[]`, then `grandeur[]`, then `points[]`
- for `R64`, the JSON contract is `header + mesures[]`, then `contexte[]`, then `grandeur[]`, then `calendrier[]`, then `classeTemporelle[]`, then `valeur[]`
- the guide states an important semantic rule that SF5 must preserve raw, not normalize away:
  - `R63` timestamps are not uniformly interpreted across all segments
  - `R64` values carry measurement context (`contexteReleve`, `typeReleve`, `motifReleve`, calendars, classes, cadrans)

#### C68 (`Enedis.SGE.GUI.0504.Flux_C68_v1.2.0.pdf`)

- `C68` is the punctual ITC flow for technical and contractual information
- one **primary archive** corresponds to one request
- the primary archive contains **1 to 10 secondary archives**
- each secondary archive contains **one JSON or CSV file**
- each secondary archive can contain data for up to **1000 PRMs**
- nomenclature is also request-oriented:

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<numSequence>_<horodate>.<extension>
```

- JSON and CSV do not carry identical business richness:
  - the guide explicitly notes some technical/contractual sections are JSON-only
  - CSV is a flattened export surface, not a perfect semantic twin of the nested JSON model

### 2.2 Real Corpus Findings (`flux_enedis/`)

Observed local directories:

- `flux_enedis/R63`
- `flux_enedis/R64`
- `flux_enedis/C68`

Observed archive counts:

| Family | Files observed | Main observed formats | Invalid/non-zip files |
|--------|----------------|-----------------------|-----------------------|
| `R63` | 38,007 | 37,378 JSON members, 411 CSV members | 218 |
| `R64` | 114 | 81 JSON members, 33 CSV members | 0 |
| `C68` | 255 | 231 nested CSV payloads, 31 nested JSON payloads | 1 |

Observed packaging behavior:

- `R63` / `R64` valid files are direct ZIP archives with a single JSON or CSV member
- `C68` valid files are primary ZIPs whose members are secondary ZIPs
- observed `C68` primary ZIP cardinality:
  - 246 files with 1 secondary archive
  - 8 files with 2 secondary archives
- every observed valid secondary `C68` archive contains exactly 1 JSON or CSV payload file

Observed content examples:

- `R63` JSON sample:
  - top-level `header`
  - `mesures[].idPrm`
  - `mesures[].etapeMetier`
  - `mesures[].modeCalcul`
  - `grandeur[].grandeurMetier/grandeurPhysique/unite`
  - `points[].v/d/p/n/iv/ec`
- `R63` CSV sample columns:
  - `Identifiant PRM`
  - `Date de début`
  - `Date de fin`
  - `Grandeur physique`
  - `Grandeur métier`
  - `Etape métier`
  - `Unité`
  - `Horodate`
  - `Valeur`
  - `Nature`
  - `Pas`
  - `Indice de vraisemblance`
  - `Etat complémentaire`
- `R64` JSON sample:
  - `mesures[].idPrm`
  - `periode.dateDebut/dateFin`
  - `contexte[].contexteReleve/typeReleve/motifReleve`
  - `grandeur[].grandeurMetier/grandeurPhysique/unite`
  - `calendrier[].idCalendrier/libelleCalendrier/libelleGrille`
  - `classeTemporelle[].idClasseTemporelle/libelleClasseTemporelle`
  - `valeur[].d/v/iv`
- `R64` CSV sample columns:
  - `Identifiant PRM`
  - `Date de début`
  - `Date de fin`
  - `Grandeur physique`
  - `Grandeur metier`
  - `Etape metier`
  - `Unite`
  - `Horodate`
  - `Contexte de relève`
  - `Type de releve`
  - `Motif de relève`
  - `Grille`
  - `Identifiant calendrier`
  - `Libellé calendrier`
  - `Identifiant classe temporelle`
  - `Libellé classe temporelle`
  - `Cadran`
  - `Valeur`
  - `Indice de vraisemblance`
- `C68` JSON sample:
  - one top-level array
  - one object per PRM
  - nested sections such as `donneesGenerales`, `situationAlimentation`, `situationComptage`, `syntheseContractuelle`, `situationsContractuelles`
- `C68` CSV sample:
  - one flat row per PRM
  - very wide contract/technical export
  - fields such as `PRM`, `Domaine de tension`, `Tension de Livraison`, `Type de comptage`, `Mode de releve`, `Puissance souscrite`, `Refus de pose Linky`, `Date refus de pose Linky`

### 2.3 Critical Delta vs SF1-SF4

The new families are not just “three more parsers”.

| Topic | Legacy SF1-SF4 contract | New SF5 reality |
|------|--------------------------|-----------------|
| Transport | raw AES ciphertext | mostly direct ZIP archives |
| Payload format | XML only | JSON + CSV |
| Archive depth | one ciphertext -> one XML | direct ZIP; `C68` = ZIP -> ZIP -> JSON/CSV |
| Metadata source | XML headers | JSON header for R63/R64 JSON, but filename metadata is authoritative for CSV and C68 |
| Row granularity | measurement-like rows only | mixed: measurement points (`R63`), index values (`R64`), PRM snapshots (`C68`) |

SF5 must therefore generalize the ingestion surface without regressing the old XML path.

---

## 3. Architecture Overview

```text
Existing legacy path (unchanged happy path)
-------------------------------------------
file -> classify -> AES/XML decrypt -> XML parser -> raw archive table (`flux_data.db`)

New SF5 path
------------
file -> classify -> archive open -> member detection -> JSON/CSV parser -> raw archive table (`flux_data.db`)
                                 \-> invalid archive -> FluxStatus.ERROR

Mixed run support
-----------------
one ingest_directory() run can contain:
- legacy encrypted XML files
- new direct ZIP R63/R64 files
- new primary+secondary ZIP C68 files
- skipped out-of-scope files
- all persisted raw results land in `flux_data.db`; SF5 never writes promoted data into `promeos.db`
```

### New high-level rule

The ingestion pipeline becomes **container-aware** instead of assuming “all in-scope files must decrypt to XML”.

- legacy XML families keep using the current AES/XML path
- `R63`, `R64`, `C68` use ZIP/member extraction and JSON/CSV parsing
- the registry, retry logic, republication/versioning logic, CLI, REST scaffolding, and run counters remain shared

SF5 still ends at raw persistence. The later `backend/data_staging/` module from SF6 is the separate bridge that reads raw rows from `flux_data.db` and writes promoted functional rows to `promeos.db`. That promotion boundary is intentionally outside SF5.

---

## 4. Scope Boundary

### SF5 In

- add raw-ingestion support for `R63`, `R64`, and `C68`
- support both **JSON and CSV** for these families on day one
- support `C68` nested archive extraction
- add 2 new raw archive tables in `flux_data.db`:
  - one shared raw table for atomic `R63` / `R64` rows
  - one raw table for `C68` per-PRM snapshots
- extend file metadata capture so request/publication fields from filenames are queryable
- extend CLI/API/stats/tests so the existing raw-ingestion operational surfaces cover the new tables without changing the `promeos.db` contract

### SF5 Out

- no promotion to functional tables (`meter_load_curve`, `meter_energy_index`, etc.)
- no creation or mutation of promotion/audit/product tables in `promeos.db`
- no PRM matching to `DeliveryPoint` / `Meter`
- no deduplication/republication resolution at measurement level
- no dependency on `backend/data_staging/` for persistence
- no support in this wave for:
  - `R63A`, `R63B`
  - `R64A`, `R64B`
  - `R65`
  - `R66`
  - `R67`
- no C68 business normalization into contract/power models
- no completeness SLA monitoring for M023 publication sequences

---

## 5. Key Decisions

| ID | Topic | Decision | Why |
|----|-------|----------|-----|
| D1 | Supported formats | **JSON + CSV required from day one** | The official guides allow both and the local corpus is already mixed; shipping JSON-only would knowingly reject real files |
| D2 | Archive handling | **Do not send `R63/R64/C68` through the XML decrypt path** | Their happy path is ZIP publication, not AES/XML |
| D3 | Invalid non-zip files | **Treat as `ERROR`, not alternate happy path** | The guides define ZIP delivery and the sampled invalid files did not open as valid ZIPs nor decrypt with current legacy AES keys |
| D4 | Table count | **2 new raw archive tables total** | Aligns with roadmap scope and keeps SF5 bounded |
| D5 | `R63` + `R64` storage model | **One shared raw table** with nullable context columns | Both are R6X request-response measurement families with one atomic temporal value per leaf row |
| D6 | `C68` storage model | **One per-PRM snapshot table with full raw payload + curated extracted columns** | C68 is too wide and heterogeneous for a pure all-columns-first model in SF5, but a pure blob would be too opaque |
| D7 | Metadata authority | **Filename nomenclature is authoritative** for request/publication fields; payload headers are supplemental | CSV variants and C68 do not provide all metadata inside the payload |
| D8 | Raw typing | **Store extracted raw-archive values as raw strings** (same archive philosophy as SF2/SF3) | Preserve fidelity and avoid premature normalization across JSON/CSV variants |
| D9 | Key loading | **Decryption keys become lazy/conditional** | A directory containing only direct ZIP R63/R64/C68 should not fail before scan time just because legacy AES keys are absent |
| D10 | C68 row granularity | **1 row = 1 PRM snapshot from one payload file** | Matches both JSON array items and CSV rows, and fits downstream traceability needs |
| D11 | Database boundary | **All SF5 persistence stays in `flux_data.db`** | Preserves SGE4.5. Raw archive/control tables remain isolated from promoted/product data in `promeos.db` |

---

## 6. Data Model Changes

### 6.1 `enedis_flux_file` Extensions

`EnedisFluxFile` remains the physical file registry in `flux_data.db`. SF5 extends it with filename-derived publication metadata that is useful across `R63`, `R64`, and `C68`.

| Column | Type | Description |
|--------|------|-------------|
| `type_donnee` | String(20) nullable | e.g. `CdC`, `INDEX`, `ITC` from filename |
| `id_demande` | String(20) nullable | M023 request identifier from filename and/or JSON header |
| `mode_publication` | String(5) nullable | e.g. `P` |
| `payload_format` | String(10) nullable | `XML`, `JSON`, `CSV` — actual parsed payload format |
| `num_sequence` | String(10) nullable | raw sequence segment from filename |
| `publication_horodatage` | String(20) nullable | raw `AAAAMMJJHHMMSS` from filename |
| `archive_members_count` | Integer nullable | number of first-level archive members actually opened |

`header_raw` semantics broaden slightly:

- legacy XML flows: raw XML header JSON as today
- `R63`/`R64` JSON: raw `header` object
- CSV variants and `C68`: filename-derived metadata envelope and archive manifest

This keeps one raw-file registry abstraction in `flux_data.db` instead of creating a parallel file table or leaking raw-ingestion metadata into `promeos.db`.

### 6.2 New Raw Table: `enedis_flux_mesure_r6x`

Shared raw archive table in `flux_data.db` for atomic `R63` and `R64` rows.

**Granularity**

- `R63`: 1 row per point of `points[]` or CSV measurement line
- `R64`: 1 row per leaf value of `valeur[]` or CSV value line

**Why one shared table**

- both families are M023 response measurement datasets
- both are flattened into one atomic time/value leaf row
- both share query keys: PRM, period, physical quantity, business quantity, timestamp/value, file provenance

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `flux_file_id` | FK → `enedis_flux_file.id` | physical source file |
| `flux_type` | String(10) | `R63` or `R64` |
| `source_format` | String(10) | `JSON` or `CSV` |
| `archive_member_name` | String(255) | actual payload member filename inside the ZIP |
| `point_id` | String(14) | PRM |
| `periode_date_debut` | String(50) | raw period start |
| `periode_date_fin` | String(50) | raw period end |
| `etape_metier` | String(20) nullable | raw stage/business step |
| `mode_calcul` | String(20) nullable | `R63` only |
| `contexte_releve` | String(20) nullable | `R64` only |
| `type_releve` | String(20) nullable | `R64` only |
| `motif_releve` | String(20) nullable | `R64` only |
| `grandeur_metier` | String(20) nullable | raw |
| `grandeur_physique` | String(20) nullable | raw |
| `unite` | String(20) nullable | raw |
| `horodatage` | String(50) | raw measurement/index timestamp |
| `pas` | String(20) nullable | `R63` only, raw ISO duration like `PT5M` |
| `nature_point` | String(10) nullable | `R63` only |
| `valeur` | String(30) nullable | raw value as text |
| `indice_vraisemblance` | String(10) nullable | raw text form of `iv` |
| `etat_complementaire` | String(10) nullable | `R63` only, raw text form of `ec` |
| `code_grille` | String(20) nullable | `R64` CSV/derived grid code when available |
| `id_calendrier` | String(30) nullable | `R64` only |
| `libelle_calendrier` | String(100) nullable | `R64` only |
| `libelle_grille` | String(100) nullable | `R64` JSON only when available |
| `id_classe_temporelle` | String(30) nullable | `R64` only |
| `libelle_classe_temporelle` | String(100) nullable | `R64` only |
| `code_cadran` | String(30) nullable | `R64` only |

**Indexes**

- `(point_id, horodatage)`
- `(flux_file_id)`
- `(flux_type)`
- `(point_id, flux_type, grandeur_physique)`

**No unique constraint**

As with every existing raw archive table, republications/corrections remain archived side by side.

### 6.3 New Raw Table: `enedis_flux_itc_c68`

Raw archive table in `flux_data.db` for `C68` technical/contractual PRM snapshots.

**Granularity**

- 1 row per PRM object in a JSON payload
- 1 row per CSV line in a CSV payload

**Important design note**

Unlike `R63` / `R64`, `C68` is not a compact measurement family. It is a very wide, nested snapshot whose exact leaf set differs between JSON and CSV. For SF5, the canonical source-of-truth inside the raw archive row is therefore the **full per-PRM raw payload**, plus a small extracted column set that supports filtering and future downstream use.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `flux_file_id` | FK → `enedis_flux_file.id` | physical source file |
| `source_format` | String(10) | `JSON` or `CSV` |
| `secondary_archive_name` | String(255) | nested archive name inside primary ZIP |
| `payload_member_name` | String(255) | JSON/CSV payload filename inside secondary ZIP |
| `point_id` | String(14) | PRM |
| `payload_raw` | Text | full per-PRM payload serialized as JSON text |
| `segment` | String(20) nullable | extracted when available |
| `etat_contractuel` | String(20) nullable | extracted when available |
| `formule_tarifaire_acheminement` | String(50) nullable | extracted when available |
| `code_tarif_acheminement` | String(30) nullable | extracted when available |
| `domaine_tension` | String(20) nullable | extracted when available |
| `tension_livraison` | String(30) nullable | extracted when available |
| `type_comptage` | String(30) nullable | extracted when available |
| `mode_releve` | String(30) nullable | extracted when available |
| `media_comptage` | String(30) nullable | extracted when available |
| `periodicite_releve` | String(30) nullable | extracted when available |
| `puissance_souscrite` | String(30) nullable | extracted when available |
| `puissance_limite_soutirage` | String(30) nullable | extracted when available |
| `puissance_raccordement_soutirage` | String(30) nullable | extracted when available |
| `borne_fixe` | String(10) nullable | extracted when available |
| `refus_pose_linky` | String(10) nullable | extracted when available |
| `date_refus_pose_linky` | String(30) nullable | extracted when available |

**Indexes**

- `(point_id)`
- `(flux_file_id)`
- `(point_id, flux_file_id)`

**Why `payload_raw` is acceptable here**

This is the one deliberate exception to the earlier “no fourre-tout JSON” instinct:

- `C68` is a nested document snapshot, not a homogeneous point series
- JSON and CSV are not semantically equivalent
- fidelity matters more than a premature full flattening
- downstream usage is still outside SF5

Without `payload_raw`, SF5 would either discard information or balloon into a very large schema-design project that the roadmap does not ask for.

---

## 7. Parsing and Extraction Rules

### 7.1 Classification

Add new `FluxType` values:

- `R63`
- `R64`
- `C68`

Recommended but out-of-scope recognition-as-skipped:

- `R63A`
- `R63B`
- `R64A`
- `R64B`
- `R65`
- `R66`
- `R67`

### 7.2 Filename Parsing

Add a shared filename parser for M023 publication nomenclature:

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<numSequence>_<horodate>.<extension>
```

It must extract at minimum:

- `code_flux`
- `mode_publication`
- `type_donnee`
- `id_demande`
- `num_sequence`
- `publication_horodatage`

Filename parsing is not optional. It is the authoritative metadata source for:

- `R63` CSV
- `R64` CSV
- `C68` JSON
- `C68` CSV

### 7.3 Container Rules

#### Legacy families (`R4H`, `R4M`, `R4Q`, `R171`, `R50`, `R151`)

- keep current AES/XML path unchanged

#### `R63` / `R64`

- open the physical file as a ZIP archive
- require exactly 1 payload member for the happy path
- detect `JSON` vs `CSV` from member extension or first non-whitespace byte
- invalid archive or unsupported member shape => `FluxStatus.ERROR`

#### `C68`

- open the physical file as a primary ZIP
- iterate all secondary ZIP members
- for each secondary ZIP:
  - require exactly 1 payload file
  - detect `JSON` vs `CSV`
  - parse and flatten into per-PRM raw archive rows
- if one secondary archive fails:
  - the whole physical file is recorded as `ERROR`
  - partial inserts from that file must be rolled back, same as current pipeline behavior

### 7.4 Format Detection

Detection order:

1. member extension (case-insensitive) if trustworthy
2. first non-whitespace byte:
   - `{` or `[` => JSON
   - otherwise parse as CSV with `;` delimiter

CSV rules:

- accept UTF-8 and UTF-8-SIG
- delimiter = `;`
- preserve original header labels through explicit column mapping

### 7.5 Parser Contracts

Add new parser modules:

- `parsers/r63.py`
- `parsers/r64.py`
- `parsers/c68.py`

Expected pure-function style remains the same:

- typed dataclasses for parsed results
- no DB logic inside parsers
- one parser entry point per family, with internal JSON/CSV helpers

Suggested parser surface:

```python
parse_r63_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedR63File
parse_r64_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedR64File
parse_c68_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedC68Payload
```

### 7.6 Flattening Rules

#### `R63`

- explode one row per `points[]` leaf or CSV line
- preserve:
  - PRM
  - period start/end
  - business step
  - calculation mode
  - business/physical quantity
  - unit
  - timestamp
  - value
  - point nature
  - step/pas
  - plausibility index
  - complementary state

#### `R64`

- explode one row per `valeur[]` leaf or CSV line
- preserve:
  - PRM
  - period start/end
  - business step
  - read context
  - read type
  - read reason
  - business/physical quantity
  - unit
  - grid/calendar/class/cadran context
  - timestamp
  - value
  - plausibility index

#### `C68`

- JSON:
  - one row per top-level PRM object
  - `payload_raw` stores that PRM object
- CSV:
  - one row per CSV line
  - `payload_raw` stores the row converted to JSON object `{csv_header: raw_string_value}`

No cross-format synthesis is allowed in SF5. If CSV omits a JSON-only branch, it stays omitted.

---

## 8. Pipeline Changes

### 8.1 Shared Dispatcher

Keep the current `ingest_file()` orchestration model:

1. classify
2. idempotence / retry / republication handling
3. parse container + payload
4. insert/update file row + raw archive rows in `flux_data.db`
5. commit

But replace the assumption “in-scope means decrypt to XML” with “in-scope means use the family-specific extractor”.

### 8.2 New Dispatch Families

| Flux family | Extraction path | Parser | Target table |
|-------------|-----------------|--------|--------------|
| `R4H/R4M/R4Q` | AES/XML | existing | `enedis_flux_mesure_r4x` |
| `R171` | AES/XML | existing | `enedis_flux_mesure_r171` |
| `R50` | AES/XML | existing | `enedis_flux_mesure_r50` |
| `R151` | AES/XML | existing | `enedis_flux_mesure_r151` |
| `R63` | ZIP -> JSON/CSV | new | `enedis_flux_mesure_r6x` |
| `R64` | ZIP -> JSON/CSV | new | `enedis_flux_mesure_r6x` |
| `C68` | ZIP -> ZIP -> JSON/CSV | new | `enedis_flux_itc_c68` |

### 8.3 Key Loading / CLI Behavior

Current CLI behavior fails up front if no AES keys are present. SF5 should relax that rule:

- if the scanned run contains only direct ZIP publication families (`R63`, `R64`, `C68`), the run must proceed without AES keys
- if at least one legacy AES/XML family is discovered and no keys are available, the run fails clearly before processing those files

This keeps mixed-directory support while making the new direct publication flows independently ingestible.

### 8.4 `measures_count` Semantics

`EnedisFluxFile.measures_count` stays as the per-file extracted row count:

- `R63`: number of atomic point rows inserted
- `R64`: number of atomic value rows inserted
- `C68`: number of PRM snapshot rows inserted

### 8.5 Republication Behavior

Keep current file-level rules:

- same `file_hash` => already processed / retry logic as today
- same filename + different hash => versioned republication as today

SF5 does **not** add request-level or PRM-level deduplication.

### 8.6 Database Responsibility

The raw-ingestion operational surface stays bound to the dedicated raw database:

- raw CLI execution continues to open the dedicated raw session/engine
- raw REST list/stats surfaces continue to query the raw DB dependency
- SF5 migrations/bootstrap create the new raw tables in `flux_data.db`
- `promeos.db` is not a fallback persistence target and should remain unchanged by an SF5 ingest run

---

## 9. Operational Surfaces

### CLI

The existing `python -m data_ingestion.enedis.cli ingest` command stays the only CLI entrypoint.

The report must include the two new raw archive totals, queried from `flux_data.db`:

- `R6X`
- `C68`

Suggested output section:

```text
Measures stored (raw archive totals):
  R4x:     ...
  R171:    ...
  R50:     ...
  R151:    ...
  R6X:     ...
  C68:     ...
  TOTAL:   ...
```

### API / Stats

`GET /api/enedis/stats` and any equivalent stats scaffolding from SF4 should continue to use the dedicated raw DB dependency and extend the breakdown with:

- total `R6X` rows
- total `C68` rows
- optional distinct PRM counts for these new tables

No new endpoint family is required in SF5.

### Error Observability

Expected new error classes:

- invalid ZIP archive
- invalid nested ZIP archive (`C68`)
- unsupported payload member type
- malformed JSON
- malformed CSV headers / missing mandatory columns

These must follow the same `EnedisFluxFile.status=error` + archived error history conventions already delivered in SF4.

---

## 10. Test Strategy

### 10.1 Unit Tests

Add parser tests for:

- `R63` JSON
- `R63` CSV
- `R64` JSON
- `R64` CSV
- `C68` JSON
- `C68` CSV

Mandatory assertions:

- row counts
- required raw fields preserved exactly
- PRM format preserved
- JSON arrays and nested contexts/classes are fully exploded
- CSV header mapping is correct

### 10.2 Container Tests

Add extraction tests for:

- direct ZIP with single JSON member
- direct ZIP with single CSV member
- `C68` primary ZIP with one secondary ZIP
- `C68` primary ZIP with multiple secondary ZIPs
- invalid outer ZIP
- invalid secondary ZIP
- unsupported member extension

### 10.3 Integration Tests

Add representative real-file integration tests covering all observed happy-path combinations:

- `R63` JSON real sample
- `R63` CSV real sample
- `R64` JSON real sample
- `R64` CSV real sample
- `C68` JSON real sample
- `C68` CSV real sample

Recommended real-sample references from the local corpus:

- `flux_enedis/R63/ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip`
- `flux_enedis/R63/ENEDIS_R63_P_CdC_M057W4YR_00001_20231016154951.zip`
- `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip`
- `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06CX26D_00001_20240523105124.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M05GIGM1_00001_20231204101954.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip`

Add explicit bad-file tests using observed malformed samples:

- `flux_enedis/R63/ENEDIS_R63_P_CdC_M06DSGVE_00001_20240528163243.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M082FQJM_00001_20250424205829.zip`

### 10.4 Regression Tests

Legacy SF1-SF4 tests must continue to pass unchanged for:

- decrypt/classify of old fluxes
- XML parsers
- pipeline idempotence/retry/republication
- CLI run/reporting

### 10.5 Cross-DB Boundary Tests

Add explicit boundary tests so the SGE4.5 split remains enforced after SF5:

- bootstrapping `promeos.db` must **not** create `enedis_flux_mesure_r6x` or `enedis_flux_itc_c68`
- bootstrapping `flux_data.db` **must** create `enedis_flux_mesure_r6x` and `enedis_flux_itc_c68`
- raw ingestion stats/list endpoints must still read through the dedicated raw DB dependency
- ingesting representative SF5 files must change `flux_data.db` only; promoted/product tables in `promeos.db` remain untouched

---

## 11. Risks and Open Questions

| ID | Topic | Status | Notes |
|----|-------|--------|-------|
| OQ1 | C68 extracted column set | Open | This draft proposes `payload_raw` + curated query columns. If the team wants a full all-columns flattening, SF5 scope expands materially |
| OQ2 | Out-of-scope R6X recognition | Open | We may want to classify `R63A/B`, `R64A/B`, `R65`, `R66`, `R67` explicitly as known-but-skipped instead of `UNKNOWN` |
| OQ3 | `R6X` table naming | Open | `enedis_flux_mesure_r6x` is concise and matches roadmap intent, but `r63_r64` would be more explicit |
| OQ4 | Stats granularity | Open | It may be useful to expose JSON vs CSV counts in stats/debug output, but it is not required for SF5 |
| OQ5 | Invalid non-zip files | Open but non-blocking | This draft treats them as corrupt publication files; if Enedis later confirms an alternate encryption contract, we can add it in a later wave |

---

## 12. Acceptance Checklist

- [ ] `FluxType` and classification support `R63`, `R64`, `C68`
- [ ] raw DB bootstrap creates `enedis_flux_mesure_r6x` and `enedis_flux_itc_c68` in `flux_data.db`
- [ ] main `promeos.db` bootstrap does not create the new raw Enedis tables
- [ ] one mixed `ingest_directory()` run can process legacy XML flows and new ZIP publication flows together
- [ ] `R63` JSON ingests successfully into `enedis_flux_mesure_r6x`
- [ ] `R63` CSV ingests successfully into `enedis_flux_mesure_r6x`
- [ ] `R64` JSON ingests successfully into `enedis_flux_mesure_r6x`
- [ ] `R64` CSV ingests successfully into `enedis_flux_mesure_r6x`
- [ ] `C68` JSON ingests successfully into `enedis_flux_itc_c68`
- [ ] `C68` CSV ingests successfully into `enedis_flux_itc_c68`
- [ ] `C68` primary archives with multiple secondary ZIPs ingest correctly
- [ ] malformed `R63` / `C68` archives are recorded as clean file errors
- [ ] CLI/reporting/stats show the two new raw archive tables through the dedicated raw DB surface
- [ ] ingesting SF5 files leaves `promeos.db` unchanged
- [ ] legacy SF1-SF4 ingestion behavior remains green

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| **M023** | Enedis request/response service family for punctual data access publications |
| **R63** | Fine-grain load curve response flow |
| **R64** | Fine-grain index response flow |
| **C68** | Technical and contractual information response flow |
| **Primary archive** | Outer ZIP published by Enedis for one request |
| **Secondary archive** | Nested ZIP inside `C68` primary publication |
| **Raw archive layer** | The `flux_data.db` database and tables that preserve Enedis data without business normalization |
| **Functional promotion layer** | The later SF6 layer in `promeos.db` that reads raw archive rows and writes promoted product-usable tables |
