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

Functionally, that means Promeos already knows how to take a legacy Enedis delivery from "file received" to "raw data safely archived" for the first wave of supported flows. Operators can run one ingestion pipeline, engineers can inspect one raw archive layer, and downstream work can trust that the incoming file was stored before any business interpretation happens.

In practice, the current pipeline is built around one dominant technical contract:

1. classify from filename
2. decrypt AES ciphertext with `KEY_n/IV_n`
3. validate XML
4. parse XML
5. store raw rows in dedicated raw archive tables in `flux_data.db`

SF5 matters because the next Enedis data families that unblock product work do not follow that contract. The platform now needs to ingest new files that are still "raw Enedis inputs", but they arrive with different transport, packaging, and payload rules.

The new SF5 scope breaks the legacy assumptions in several ways:

- `R63` / `R64` are **R6X M023 response flows**, not legacy XML supplier-perimeter flows
- the official R6X guide states the publication format is **JSON**, with **CSV** also possible
- `C68` is an **ITC punctual response flow** whose delivery contract is a **primary ZIP containing 1..n secondary ZIPs**
- `C68` payloads contain large technical and contractual snapshots, not simple point-series measurements
- the real local corpus is mixed-format and includes malformed archives that must fail cleanly

What this means in plain English is simple: the existing "decrypt XML and archive it" path is no longer enough. A user waiting for fine-grain curves, index histories, or PRM contractual snapshots does not care that the source file changed from encrypted XML to nested ZIP + JSON/CSV. They care that the data arrives through the same operational pipeline and is archived reliably for later use.

Concrete example: a mixed Enedis drop can contain a legacy `R50` encrypted XML file, a direct-ZIP `R63` response, and a nested-ZIP `C68` request result. The operator should still be able to run one ingestion command, get one coherent stats surface, archive all valid raw data in `flux_data.db`, and see malformed archives fail cleanly without corrupting downstream storage.

If we do nothing, SF6 remains blocked. It already treats SF5 as the upstream prerequisite for raw ingestion of `R63`, `R64`, and `C68`.

Since SGE4.5, this is no longer only a parser-extension question. The storage boundary is part of the feature contract just as much as the parser behavior:

- raw file registry rows, raw measurement/snapshot rows, retry history, and ingest-control tables stay in `flux_data.db`
- `promeos.db` remains reserved for later promotion/audit/product tables
- SF5 must preserve that split instead of reintroducing raw Enedis storage into the main platform database

### Why this matters

- `R63` is the raw entry point for fine-grain load-curve data outside the older R4x/R50 perimeter, so without SF5 those usage surfaces stay unavailable upstream.
- `R64` is the raw entry point for fine-grain indexes plus their measurement context, which means later consumers cannot reconstruct the business meaning of the values unless SF5 preserves that raw detail.
- `C68` is the raw entry point for PRM technical and contractual snapshots, so downstream contract and power features depend on SF5 even though SF5 itself should not perform business promotion.
- the platform now has a deliberate 2-DB contract: `flux_data.db` archives exactly what Enedis sent, while `promeos.db` is reserved for later interpreted or promoted data.
- the ingestion CLI, API, and stats surfaces should continue to behave like one product surface across mixed directories instead of forcing operators into a second ad hoc toolchain for "new" flows.

SF5 therefore extends the existing pipeline, but stays strictly in the **raw archive layer** stored in `flux_data.db`. No functional promotion, PRM matching, or business normalization belongs here.

---

## 2. Research Findings

This draft is grounded in the local documentation under `docs/base_documentaire/enedis/guides_flux/` and the real archives under `flux_enedis/`.

### 2.1 Official Guide Findings

#### R6X (`Enedis-R6X.pdf`)

- this local guide is about **publication recurrente** for `R63` and `R64`, not punctual `M023` responses; the feature text should therefore describe it as the contract for recurring measurement publications configured in the Enedis enterprise account
- functionally, `R63` is the recurring raw source for infra-daily load curves (`Courbes de charge`), while `R64` is the recurring raw source for indexes (`Index`)
- the guide states the subscribed payload format can be **JSON** or **CSV**
- CSV is not universally available: the guide says CSV is only possible for a perimeter of **less than 100 PRM**
- the guide also states an operational rule with direct ingestion impact: when files are delivered outside the Enedis enterprise account over channels such as **email** or **FTP**, they are encrypted for security
- SF5 should therefore keep one decryption-capable ingestion pipeline and detect whether each incoming file still needs decryption, instead of assuming that all R6X files bypass decryption just because our local corpus is already plain ZIP
- each recurring publication is first delivered as a **ZIP archive**
- each archive contains data for one **SIREN** and one measurement family (`CdC` or `Index`)
- the outer archive nomenclature is:

```text
Enedis_<codeFlux>_<modePublication>_<typeDonnees>_<idDemande>_<SIREN>_<horodate>.zip
```

- the inner JSON/CSV payload nomenclature is:

```text
Enedis_<codeFlux>_<modePublication>_<typeDonnees>_<idDemande>_<numSequence>_<horodate>.<extension>
```

- `codeFlux` is itself business-significant and must be preserved raw:
  - `R63A` / `R64A` = meters with power **> 36 kVA**
  - `R63B` / `R64B` = **Linky** meters with power **<= 36 kVA**
- `modePublication` is also meaningful to a non-technical reader because it encodes the delivery rhythm chosen in the subscription:
  - `Q` = daily
  - `H` = weekly
  - `M` = monthly
- the JSON header carries request/publication metadata in addition to the measure payload, so SF5 should treat filename metadata and JSON header metadata as complementary raw evidence rather than trying to collapse them too early
- for `R63`, the JSON contract is `header + mesures[]`, then `grandeur[]`, then `points[]`
- for `R64`, the JSON contract is `header + mesures[]`, then `contexte[]`, then `grandeur[]`, then `calendrier[]`, then `classeTemporelle[]`, then `valeur[]`
- for a business reader, `R63` is not just "a list of values": it is a recurring publication of consumption or production curves at infra-daily granularity, with step sizes that depend on meter family (`PT5M`, `PT10M`, `PT15M`, `PT30M`, `PT60M`)
- the guide makes clear that `R63` raw point qualifiers carry useful operational meaning and should be archived as-is:
  - `n` explains the nature of the point (`brut`, `estimé`, outage-related, clock-adjusted, etc.)
  - `tc` explains the correction/completion type when relevant
  - `iv` and `ec` qualify Linky point reliability and context
- the guide also clarifies that `dateDebut` and `dateFin` are publication-window boundaries tied to what Enedis collected in its SI, not a simplified business period label; this matters when later consumers interpret partial-day recurring publications
- for `R64` Linky (`<= 36 kVA`), the guide states that the raw data can contain both **totalizer indexes** and indexes attached to **supplier** and **distributor** grids
- preserving those raw grid, calendar, temporal-class, and cadran fields is functionally essential:
  - the supplier grid helps compare published consumption against the supplier invoice logic
  - the distributor grid helps validate regulated grid-cost logic such as TURPE
- for `R64` meters with power **> 36 kVA**, the guide states there are **no totalizer indexes**
- in that higher-power case, indexes remain attached to either a **supplier** or **distributor** grid, and the flow can also return additional overrun-related information such as `DD`, `DE`, `DQ`, `PMA`, and `TF`
- those `> 36 kVA` fields are not implementation noise: they are raw ingredients for later optimisation and tariff analysis, so SF5 should archive them without business reduction
- the guide defines `iv` for `R64` Linky active-energy indexes as a **0..15 plausibility code** carrying Enedis quality semantics
- that detailed plausibility interpretation is not central to SF5 ingestion decisions, but it is valuable raw evidence to preserve now and will likely be much more useful in SF6 staging and quality assessment

#### C68 (`Enedis.SGE.GUI.0504.Flux_C68_v1.2.0.pdf`)

- `C68` is the punctual ITC flow for technical and contractual information
- one **primary archive** corresponds to one request
- the primary archive contains **1 to 10 secondary archives**
- each secondary archive contains **one JSON or CSV file**
- each secondary archive can contain data for up to **1000 PRMs**
- the official publication contract also includes a `CR.M023` compte rendu file, but SF5 only ingests the C68 data archive; `CR.M023` parsing/reconciliation is explicitly out of scope for this wave
- nomenclature is also request-oriented:

```text
ENEDIS_<codeFlux>_<modePublication>_<typeDonnee>_<idDemande>_<numSequence>_<horodate>.<extension>
```

- the primary archive sequence is expected to be fixed at `00001`
- secondary archives and their JSON/CSV payload files use the same nomenclature, with sequence values from `00001` to `00010` depending on the number of requested PRMs
- JSON and CSV do not carry identical business richness:
  - the guide explicitly notes some technical/contractual sections are JSON-only
  - CSV is a flattened export surface, not a perfect semantic twin of the nested JSON model
- C68 field absence can be business-significant:
  - `T` = transmitted without customer consent
  - `O` = transmitted only with customer consent
  - `A` = absent/unavailable for the requester context
  - therefore, missing non-identity fields are not automatically parser defects; they may point to consent/requester-right gaps that data-management users need to act on
- v1.2.0 adds four notable CSV/JSON data points:
  - `Type Injection` / `situationsContractuelles[].typeInjection`
  - `Refus de pose Linky` / `situationsContractuelles[].refusPoseAMM`
  - `Date refus de pose Linky` / `situationsContractuelles[].dateRefusPoseAMM`
  - `Borne Fixe` / `donneesGenerales.typage.borneFixe`
- JSON-only branches such as `rattachements` and `optionsContractuelles` must be preserved in the raw payload, but SF5 does not normalize them into dedicated tables

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
- the local corpus mostly reflects files that are already usable as archives, but this must not be over-interpreted as a global transport rule:
  - the official guides still allow encrypted delivery depending on publication channel
  - SF5 should therefore treat "already-openable archive" as a per-file state to detect, not as a separate family-level pipeline contract
- observed `C68` primary ZIP cardinality:
  - 246 files with 1 secondary archive
  - 8 files with 2 secondary archives
- every observed valid secondary `C68` archive contains exactly 1 JSON or CSV payload file
- observed `C68` payload row counts range from 1 to 1000 PRM snapshots
- observed `C68` CSV headers include both:
  - legacy 207-column files
  - v1.2-style 211-column files with `Type Injection`, `Refus de pose Linky`, `Date refus de pose Linky`, and `Borne Fixe`
- these corpus facts are empirical implementation evidence, not universal Enedis rules; the official guide still defines up to 10 secondary archives per primary publication

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
| Transport | raw AES ciphertext that must decrypt before parsing | mixed per-file transport: some deliveries may still arrive encrypted, then yield ZIP/JSON/CSV after decryption; others may already be directly openable archives |
| Payload format | XML only | JSON + CSV |
| Archive depth | one ciphertext -> one XML | direct ZIP for some files; `C68` = ZIP -> ZIP -> JSON/CSV; encrypted deliveries add a pre-archive unwrap step rather than a separate pipeline |
| Metadata source | XML headers | JSON header for R63/R64 JSON, but filename metadata is authoritative for CSV and C68 |
| Row granularity | measurement-like rows only | mixed: measurement points (`R63`), index values (`R64`), PRM snapshots (`C68`) |

Functionally, the operator experience should still feel like one ingestion product: one run accepts mixed files, conditionally decrypts when needed, then routes the usable payload into the right raw parser.

SF5 must therefore generalize the ingestion surface without regressing the old XML path or introducing a second "new flows only" pipeline.

---

## 3. Architecture Overview

```text
Existing legacy path (unchanged happy path)
-------------------------------------------
file -> classify -> AES/XML decrypt -> XML parser -> raw archive table (`flux_data.db`)

Unified SF1-SF5 path
--------------------
file -> classify -> detect whether transport is still encrypted
                  -> if encrypted: decrypt
                  -> if already openable: continue
                  -> open container / payload
                  -> detect member format and depth
                  -> XML parser or JSON/CSV parser
                  -> raw archive table (`flux_data.db`)
                  \-> invalid encryption/container/payload -> FluxStatus.ERROR

Mixed run support
-----------------
one ingest_directory() run can contain:
- legacy encrypted XML files
- `R63` / `R64` files that still need decryption before archive handling
- `R63` / `R64` files already present as direct ZIP archives
- `C68` files that still need decryption before nested ZIP handling
- `C68` files already present as primary+secondary ZIP archives
- skipped out-of-scope files
- all persisted raw results land in `flux_data.db`; SF5 never writes promoted data into `promeos.db`
```

### New high-level rule

The ingestion pipeline becomes **transport-aware and container-aware** instead of assuming “all in-scope files must decrypt to XML” or “new files never need decryption”.

- legacy XML families keep using the current AES/XML path
- `R63`, `R64`, `C68` stay on the same shared ingestion backbone:
  - detect whether the incoming file is still encrypted because of its delivery channel
  - decrypt when needed
  - then continue into ZIP/member extraction and JSON/CSV parsing
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
- no `CR.M023` compte rendu parsing/reconciliation

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
| D8 | Raw typing | **Store most extracted raw-archive values as raw strings, with curated value/unit splits for high-value C68 power fields** | Preserve fidelity while making key power filters usable without normalizing the whole C68 model |
| D9 | Key loading | **Decryption keys become lazy/conditional** | A directory containing only direct ZIP R63/R64/C68 should not fail before scan time just because legacy AES keys are absent |
| D10 | C68 row granularity | **1 row = 1 PRM snapshot from one payload file** | Matches both JSON array items and CSV rows, and fits downstream traceability needs |
| D11 | Database boundary | **All SF5 persistence stays in `flux_data.db`** | Preserves SGE4.5. Raw archive/control tables remain isolated from promoted/product data in `promeos.db` |
| D12 | C68 sensitivity posture | **POC stores full C68 `payload_raw`; production privacy/RGPD storage is an open architecture question** | SF5 needs source fidelity for reprocessing, but production must revisit redaction, encryption, access control, and deletion/anonymization strategy |

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
| `contractual_situation_count` | Integer nullable | number of `situationsContractuelles[]` items when available |
| `date_debut_situation_contractuelle` | String(30) nullable | `dateDebut` of the contractual situation used for extracted contractual columns |
| `segment` | String(20) nullable | extracted when available |
| `etat_contractuel` | String(20) nullable | extracted when available |
| `formule_tarifaire_acheminement` | String(50) nullable | extracted when available |
| `code_tarif_acheminement` | String(30) nullable | extracted when available |
| `siret` | String(20) nullable | organization identifier extracted when available |
| `siren` | String(20) nullable | organization identifier extracted when available |
| `domaine_tension` | String(20) nullable | extracted when available |
| `tension_livraison` | String(30) nullable | extracted when available |
| `type_comptage` | String(30) nullable | extracted when available |
| `mode_releve` | String(30) nullable | extracted when available |
| `media_comptage` | String(30) nullable | extracted when available |
| `periodicite_releve` | String(30) nullable | extracted when available |
| `puissance_souscrite_valeur` | Numeric nullable | extracted when available |
| `puissance_souscrite_unite` | String(20) nullable | extracted when available |
| `puissance_limite_soutirage_valeur` | Numeric nullable | extracted when available |
| `puissance_limite_soutirage_unite` | String(20) nullable | extracted when available |
| `puissance_raccordement_soutirage_valeur` | Numeric nullable | extracted when available |
| `puissance_raccordement_soutirage_unite` | String(20) nullable | extracted when available |
| `puissance_raccordement_injection_valeur` | Numeric nullable | extracted when available |
| `puissance_raccordement_injection_unite` | String(20) nullable | extracted when available |
| `borne_fixe` | String(10) nullable | extracted when available |
| `refus_pose_linky` | String(10) nullable | extracted when available |
| `date_refus_pose_linky` | String(30) nullable | extracted when available |

**Indexes**

- `(point_id)`
- `(flux_file_id)`
- `(point_id, flux_file_id)`
- `(siret)`
- `(siren)`

**Why `payload_raw` is acceptable here**

This is the one deliberate exception to the earlier “no fourre-tout JSON” instinct:

- `C68` is a nested document snapshot, not a homogeneous point series
- JSON and CSV are not semantically equivalent
- fidelity matters more than a premature full flattening
- downstream usage is still outside SF5
- POC raw storage intentionally preserves the full Enedis payload, including fields that may be sensitive
- production architecture must revisit RGPD-compliant storage, access control, deletion/anonymization, and whether personal subtrees should be separated from anonymized technical/metering data

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

For `C68`:

- the primary file must match the C68 filename pattern to be classified as `C68`
- the primary sequence is expected to be `00001`
- secondary archive and payload filenames should also match the official nomenclature and use sequence values from `00001` to `00010`
- mismatched secondary/payload names are non-conformant and should be surfaced as warnings, but they do not block ingestion when the archive structure and payload data are otherwise usable
- secondary sequence gaps are non-conformant but non-fatal if all present payloads parse

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
- missing `idPrm` in JSON or `PRM` in CSV is a fatal structural error for the whole physical C68 file
- the accompanying `CR.M023` report file is not parsed by SF5; if present in the input directory, it should be skipped or classified outside the C68 data-archive path rather than causing C68 data ingestion to fail

### 7.4 Format Detection

Detection order:

1. member extension (case-insensitive) if trustworthy
2. first non-whitespace byte:
   - `{` or `[` => JSON
   - otherwise parse as CSV with `;` delimiter

CSV rules:

- accept UTF-8 and UTF-8-SIG
- delimiter = `;`
- parse by header name, not column position
- preserve original header labels through explicit column mapping
- accept both observed C68 CSV layouts:
  - legacy 207-column files
  - v1.2 211-column files
- preserve unknown extra columns in `payload_raw`
- surface unknown extra columns as schema-drift warnings/alerts so the team can decide whether to extend extracted columns and reprocess
- fail C68 CSV only when essential structure is unusable, such as missing `PRM`

JSON rules:

- C68 JSON must be syntactically valid and have a top-level array of PRM objects
- parse best-effort against the official v1.2 JSON schema rather than making schema validation a hard gate
- preserve unknown fields in `payload_raw`
- surface schema drift as warnings/alerts
- fail only when the payload is structurally impossible to ingest, such as missing `idPrm`

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
  - `situationsContractuelles[]` remains nested inside `payload_raw`; it does not multiply raw rows
  - extracted contractual columns come from the latest contractual situation by greatest parseable `dateDebut`
  - if `dateDebut` is missing/tied/ambiguous across multiple contractual situations, ingest the PRM snapshot but surface an ambiguity warning and avoid pretending the extracted fields are authoritative
- CSV:
  - one row per CSV line
  - `payload_raw` stores the row converted to JSON object `{csv_header: raw_string_value}`
- extracted code/libelle fields store the stable code/scalar value in first-class columns; the full object or flattened source value remains in `payload_raw`
- person names, emails, phone numbers, postal address lines, and interlocutor contact details are not extracted into query columns
- `SIRET` and `SIREN` are extracted as useful organization identifiers for BACS, decret tertiaire, and multi-client filtering
- high-value power fields are split into value/unit columns; less-used value/unit technical fields remain only in `payload_raw`

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

For `C68`, archive/package diagnostics such as secondary archive count and payload member count should be exposed separately when the stats/debug surface supports them. They must not be folded into `measures_count`.

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
- non-fatal schema drift warnings for unknown C68 CSV columns or JSON fields
- non-fatal C68 filename/sequence non-conformance warnings for usable secondary archives or payload members
- C68 contractual-situation ambiguity warnings when extracted summary columns cannot be tied to one clear latest situation

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
- `C68` CSV with legacy 207-column headers
- `C68` CSV with v1.2 211-column headers

Mandatory assertions:

- row counts
- required raw fields preserved exactly
- PRM format preserved
- JSON arrays and nested contexts/classes are fully exploded
- CSV header mapping is correct
- C68 CSV extraction is header-name based, not position-based
- C68 v1.2 fields are preserved/extracted when present and tolerated when absent
- unknown C68 CSV columns and JSON fields remain in `payload_raw` and produce warnings rather than hard failures
- C68 JSON nested arrays such as `rattachements`, `installationsProduction`, and `optionsContractuelles` remain intact in `payload_raw`
- C68 extracted contractual columns use the latest `situationsContractuelles[]` item by `dateDebut`
- ambiguous C68 contractual-situation selection produces a warning
- C68 missing `idPrm` / `PRM` fails the physical file and rolls back inserts

### 10.2 Container Tests

Add extraction tests for:

- direct ZIP with single JSON member
- direct ZIP with single CSV member
- `C68` primary ZIP with one secondary ZIP
- `C68` primary ZIP with multiple secondary ZIPs
- invalid outer ZIP
- invalid secondary ZIP
- C68 primary ZIP where one secondary archive is invalid and the entire physical file is rolled back
- C68 secondary/payload filename mismatch that ingests successfully with a non-fatal warning
- unsupported member extension

### 10.3 Integration Tests

Add representative real-file integration tests covering all observed happy-path combinations:

- `R63` JSON real sample
- `R63` CSV real sample
- `R64` JSON real sample
- `R64` CSV real sample
- `C68` JSON real sample
- `C68` CSV real sample
- `C68` legacy 207-column CSV real sample
- `C68` v1.2 211-column CSV real sample

Recommended real-sample references from the local corpus:

- `flux_enedis/R63/ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip`
- `flux_enedis/R63/ENEDIS_R63_P_CdC_M057W4YR_00001_20231016154951.zip`
- `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip`
- `flux_enedis/R64/ENEDIS_R64_P_INDEX_M06CX26D_00001_20240523105124.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M05GIGM1_00001_20231204101954.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip`
- `flux_enedis/C68/ENEDIS_C68_P_ITC_M08GV8IG_00001_20250721134328.zip`

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
| OQ1 | C68 extracted column set | Settled for SF5 | Use `payload_raw` + curated query columns, including SIRET/SIREN and split value/unit columns for the small high-value power set. Full all-columns flattening remains out of scope |
| OQ2 | Out-of-scope R6X recognition | Open | We may want to classify `R63A/B`, `R64A/B`, `R65`, `R66`, `R67` explicitly as known-but-skipped instead of `UNKNOWN` |
| OQ3 | `R6X` table naming | Open | `enedis_flux_mesure_r6x` is concise and matches roadmap intent, but `r63_r64` would be more explicit |
| OQ4 | Stats granularity | Open | It may be useful to expose JSON vs CSV counts in stats/debug output, but it is not required for SF5 |
| OQ5 | Invalid non-zip files | Open but non-blocking | This draft treats them as corrupt publication files; if Enedis later confirms an alternate encryption contract, we can add it in a later wave |
| OQ6 | Production C68 privacy/RGPD architecture | Open for production | POC stores full C68 `payload_raw`. Before production, decide whether personal/contact subtrees should be separated, encrypted, access-controlled, redacted, selectively deletable, or anonymized while retaining useful technical/metering data for model development |

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
- [ ] `C68` legacy 207-column CSV and v1.2 211-column CSV both ingest successfully
- [ ] C68 unknown CSV/JSON fields are preserved in `payload_raw` and surfaced as warnings, not hard failures
- [ ] C68 missing `idPrm` / `PRM` fails the physical file and rolls back inserts
- [ ] C68 extracted contractual columns use the latest `situationsContractuelles[]` item by `dateDebut`
- [ ] `C68` primary archives with multiple secondary ZIPs ingest correctly
- [ ] one invalid C68 secondary archive rolls back the whole physical file
- [ ] malformed `R63` / `C68` archives are recorded as clean file errors
- [ ] C68 `measures_count` reports PRM snapshot rows, not archive/member counts
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
