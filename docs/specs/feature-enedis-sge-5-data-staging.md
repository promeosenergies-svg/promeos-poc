# SF5 — Enedis Data Staging: Raw → Functional Promotion Pipeline

> **Status**: PRD v2.3 — R4x v2.0.3 + R50 v2.2.0 review integrated
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion), SF4 (operationalization) — all complete and merged
> **Module**: `backend/data_staging/` (new, separate from `data_ingestion/`)

---

## 1. Problem Statement

SF1-SF4 delivered a complete raw ingestion pipeline: 6 flux types parsed, 5 staging tables, 91 real files ingested, 123,846 measures — all stored as raw strings with zero transformation. This raw archive is the **source of truth** for everything Enedis sends us.

However, **no bridge exists** between the raw staging tables and the functional layer that powers every downstream service: consumption dashboards, anomaly detection, monitoring alerts, regulatory compliance, and billing reconciliation.

Today, `MeterReading` is populated exclusively by synthetic seed data. The raw staging data — real Enedis measurements — is invisible to the application.

This is intentional for the prototype: the current seeded/demo metering universe stays live during SF5 so we do not break the platform while the Enedis backbone is being built. SF5 creates a **parallel real-data promotion layer**. The later migration of services and calculations from dummy tables to real Enedis-promoted tables is a **separate feature wave**, not part of SF5 itself.

Furthermore, the existing `MeterReading` model conflates two fundamentally different physical quantities:
- **Power (kW)** — average power over a forward interval (what CDC load curves measure)
- **Energy (kWh)** — cumulative consumption over a period (what index readings measure)

These require **separate functional tables** with distinct semantics, units, and downstream consumers.

### Why this matters

Correctly and reliably handling Enedis data is one of Promeos's core MOATs. Competitors that cut corners on data quality lose client trust. This pipeline must be:

- **Transparent**: every promoted value traceable to its source staging row and flux file
- **Safe**: no unidentified data leaks to production — unknown PRMs are flagged, not silently promoted
- **Auditable**: full trail of what was promoted, when, why, and what it replaced
- **Incremental**: designed for scale (10,000 PRMs, 175M readings at 2 years hourly)
- **Extensible**: the `data_staging/` module will grow to handle GRDF, GTB, sub-meters, other ELDs

---

## 2. Architecture Overview

```
                SF1-SF4 (existing)                       SF5 (this feature)
                ──────────────────                       ──────────────────

Encrypted ──→ Decrypt ──→ Parse ──→ Raw Staging    ──→  Promotion Pipeline
  .zip         (AES)      (XML)     (5 tables)          (data_staging/)
  (FTP)                              │                        │
                                     │              ┌─────────┴──────────────┐
                                     │              │  1. PRM Matching       │
                                     │              │  2. Republication Res. │
                                     │              │  3. Value Conversion   │
                                     │              │  4. Quality Scoring    │
                                     │              │  5. Gap Visibility     │
                                     │              │  6. Backlog Replay     │
                                     │              │  7. Route & UPSERT     │
                                     │              │  8. Audit Trail        │
                                     │              └────┬───────┬───────┬───┘
                                     │                   │       │       │
                                PromotionRun       ┌─────▼──┐ ┌─▼────┐ ┌▼──────────┐
                                (audit trail)      │ meter_ │ │meter_│ │meter_     │
                                                   │ load_  │ │energy│ │power_peak │
                                                   │ curve  │ │index │ │           │
                                                   └────────┘ └──────┘ └───────────┘
                                                   R4x, R50   R171     R151 PMAX
                                                   CDC power   R151     peak demand
                                                   (kW)       CT/CT_D   (VA)
                                                              energy
                                                              (Wh)
```

SF5 does **not** replace the currently live prototype tables during this phase. `meter_reading` and `power_readings` remain part of the seeded/demo universe, while `meter_load_curve`, `meter_energy_index`, and `meter_power_peak` become the canonical promoted targets for future real-data migration.

Gap detection remains an important downstream objective of this architecture. SF5 v2 preserves **gap visibility** by keeping missing periods as visible absences in promoted tables and by auditing skipped invalid rows, but a fuller completeness / gap-detection layer is deferred to a later follow-up session.

> **Dependency note from the official R4x guide**: an R4x ZIP archive may legally contain one or more XML files, one curve per XML. SF5 assumes SF1-SF4 staging has already materialized every XML member found in an archive; otherwise promotion completeness is impossible by construction. The current POC corpus only exposed mono-XML archives, so this remains a hardening dependency rather than SF5 scope.

### Three Functional Tables

| Table | Physical quantity | Unit | Source flux | Downstream consumers |
|-------|------------------|------|-------------|---------------------|
| **`meter_load_curve`** | Interval-valued CDC row: average power over `[timestamp ; timestamp + pas_minutes[` plus related reactive/tension values | kW / kVAr / V | R4x, R50 | Future real-data monitoring, anomaly detection, peak analysis, off-hours, load profile |
| **`meter_energy_index`** | Cumulative energy per tariff class | Wh | R171, R151 (CT/CT_DIST) | Billing reconciliation, regulatory compliance, annual kWh, OPERAT |
| **`meter_power_peak`** | Max power demand per period | VA | R151 (PMAX) | Subscribed power optimization, depassement alerts |

### Data flow per CDC reading (R4x / R50 → `meter_load_curve`)

```
enedis_flux_mesure_r4x.point_id  (string "14-digit PRM")
        │
        ▼
DeliveryPoint.code  (string, 14 digits)
        │
        ▼
Meter.delivery_point_id  (FK → delivery_points.id)
        │
        ▼
meter_load_curve.meter_id  (FK → meter.id)
        with:
          timestamp                = start of covered interval (UTC-naive from ISO8601+TZ)
          pas_minutes              = exact Enedis interval size (5 / 10 / 30)
          active_power_kw          = populated when grandeur_physique=EA
          reactive_inductive_kvar  = populated when grandeur_physique=ERI
          reactive_capacitive_kvar = populated when grandeur_physique=ERC
          voltage_v                = populated when grandeur_physique=E and unit=V
          quality_score            = mapped from statut_point / indice_vraisemblance
          is_estimated             = mapped from the official status semantics / vraisemblance code

R50-specific normalization nuance:
- raw `enedis_flux_mesure_r50.horodatage` (`H`) is the **end** timestamp of the covered half-hour
- raw `enedis_flux_mesure_r50.valeur` (`V`) is the **average active power in W** during the **30 minutes preceding** `H`
- therefore the canonical promoted interval start is `H - 30 minutes`, and `active_power_kw = valeur_w / 1000`
- for `Date_Releve = D`, a complete local day covers `[D 00:00 ; D+1 00:00[` even though the raw `H` values run from `00:30` to `00:00` next day

Rows with the same `(meter_id, timestamp, pas_minutes)` are merged into one logical promoted interval row before UPSERT.
```

### Data flow per index reading (R171 / R151 → `meter_energy_index`)

```
enedis_flux_mesure_r171.point_id  (string "14-digit PRM")
        │
        ▼
DeliveryPoint.code → Meter.delivery_point_id → meter.id
        │
        ▼
meter_energy_index.meter_id  (FK → meter.id)
        with:
          date_releve       = parsed date
          tariff_class_code = code_classe_temporelle (HCE/HCH/HPE/HPH/P)
          tariff_class_label = libelle humain
          value_wh          = parsed float (cumulative index)
          quality_score     = mapped quality
          is_estimated      = mapped from quality indicator
```

---

## 3. Design Decisions

| # | Question | Decision | Justification |
|---|----------|----------|---------------|
| D1 | Scope | CDC (R4x, R50) **and** Index (R171, R151) | Both are in scope. Implementation phases will separate them, but the PRD and architecture cover both |
| D2 | Blocked PRMs | **Flag and block** — never promote unidentified or ambiguously linked data | No data leaks to production. The PRM backlog captures missing DeliveryPoints, missing active meters, and ambiguous meter matches. Once resolved, the next promotion run picks them up |
| D3 | Pipeline mode | **Incremental + backlog replay** | Each run processes new staging rows beyond the high-water mark **and** previously blocked PRMs still pending resolution. This avoids missing historical data after a PRM is fixed |
| D4 | Republication strategy | **Quality-first overwrite policy** | Better quality auto-promotes. Equal quality uses the latest republication. Worse quality is flagged and does not overwrite the current promoted row |
| D5 | Production versioning | **Option A — Current truth + audit trail** | Functional tables always hold the latest best value (UPSERT). Staging keeps full history. `PromotionEvent` table provides full traceability. No `WHERE is_current` tax on all downstream queries |
| D6 | Quality gate | **Promote all data with correct quality flags** | No minimum threshold blocking promotion. Even poor-quality data is promoted with appropriate `quality_score` and `is_estimated` flags. Downstream services already compute quality scores from these fields |
| D7 | Gap handling | **Preserve gap visibility now; explicit gap detection later** | Null or unparsable values are never converted to synthetic zeroes. Gaps stay visible as missing promoted rows, with audit events explaining why they were skipped. Completeness scoring and richer gap detection remain planned follow-up work |
| D8 | Quality score mapping | **Official R4x status semantics + Promeos heuristic score** (see Section 5) | The Enedis guide defines the meaning of `statut_point`, but not a numeric confidence score. SF5 keeps a product-owned heuristic for republication comparison |
| D9 | Module location | **`backend/data_staging/`** (new, separate module) | Separation of concerns. Will grow to handle GRDF, GTB, sub-meters, other ELDs. `data_ingestion/` = raw archive, `data_staging/` = normalization + promotion |
| D10 | Trigger model | **Separate from ingestion** — dedicated CLI command + minimal API | Natural break point: ingest → data backlog review → promote. Decoupled failure domains. POC: CLI `promote` command + minimal `/api/enedis/promotion/*` API |
| D11 | Atomicity | **Per-PRM** | Each PRM is fully promoted or not at all. One bad PRM doesn't block the fleet. Prevents misleading partial data. Aligns with business unit (site managers care about their PRMs) |
| D12 | Audit trail | **Yes — `PromotionRun` + `PromotionEvent` tables** | Core MOAT. Every promoted reading traceable to source staging row, flux file, and promotion run. Every replacement logged |
| D13 | API surface | **CLI + minimal API scaffolding** (no review UX yet) | POST `/api/enedis/promotion/promote`, GET `/api/enedis/promotion/runs`, GET `/api/enedis/promotion/stats` |
| D14 | Scale target | **175M rows** (10,000 PRMs x 2 years hourly) | Code must handle this volume even if POC runs on SQLite. Batch processing, chunked inserts, indexed lookups |
| D15 | Initial run | **Full backfill** — promote all historical staging data | First run processes everything. Subsequent runs are incremental |
| D16 | Functional data model | **Three separate promoted tables**: `meter_load_curve`, `meter_energy_index`, `meter_power_peak` | Power and energy are different physical quantities with different units, granularities, and consumers. Mixing them in one table creates semantic confusion |
| D17 | Legacy/demo coexistence | **Coexist then migrate** — promoted Enedis tables are canonical for real data, while `meter_reading` and `power_readings` remain part of the prototype/demo universe until later migration | Don't break what works. SF5 builds the real backbone first; service migration happens later |
| D18 | `meter_load_curve` schema | **One row per interval with separate columns** | `meter_load_curve` stores one row per `(meter_id, timestamp, pas_minutes)` and merges multiple CDC grandeurs into separate columns (`active_power_kw`, reactive columns, `voltage_v`) |
| D19 | PRM matching ambiguity | **Exact-one-meter rule** | A PRM is promotable only when it resolves to exactly one valid active electricity meter. No active meter or multiple candidates both block promotion and create backlog entries |
| D20 | R4x timezone / DST handling | **Trust the XML offset, convert to UTC, and treat official DST patterns as expected** | The official R4x guide uses Paris legal time with offset. Autumn duplicate local hours must survive as distinct UTC instants; spring missing local hour is not a data gap |
| D21 | CDC temporal semantics | **Store and expose CDC values as forward interval averages after flux-specific timestamp normalization** | R4x raw `H` is already an interval start; R50 raw `H` is an interval end and must be shifted back by 30 minutes. Analytics and UX must not present CDC as instantaneous spot readings |
| D22 | Publication SLA awareness | **Distinguish not-yet-due publication from overdue missing publication** | Enedis publishes R4x on explicit deadlines (`R4Q` J+1 calendaire, `R4H`/`R4M` by 3rd business day). Freshness decisions must respect those windows before surfacing a "missing publication" condition |
| D23 | R50 temporal normalization | **Convert raw R50 interval-end timestamps into canonical interval starts before promotion** | The official R50 guide defines `H` as the end of the covered 30-minute interval and `V` as average power in W over the preceding 30 minutes. Promoted `meter_load_curve.timestamp` must therefore be `H - 30 min`, not raw `H` |
| D24 | R50 publication cadence modeling | **Use filename cadence (`_Q_` / `_M_`) and file-group counters for freshness/completeness, not `Pas_Publication`** | `Pas_Publication=30` describes the curve step, while the guide defines daily vs monthly delivery cadence and multi-file completeness through filename nomenclature |

---

## 4. Data Model Changes

### 4.1 New Functional Tables

#### `meter_load_curve` — CDC time-series power data

The canonical promoted table for real Enedis load curve (courbe de charge) data. It is built in parallel to the current seeded/demo tables and will become the future real-data source for downstream migration. Each row represents **one logical interval** for one meter.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `meter_id` | FK → `meter.id` | Linked meter (resolved from PRM via DeliveryPoint) |
| `timestamp` | DateTime | Start of covered interval (UTC-naive, converted from ISO8601+TZ) |
| `pas_minutes` | Integer | Exact Enedis interval size (`5`, `10`, `30`) |
| `active_power_kw` | Float | nullable — average active power (`EA`) over the covered interval, in kW |
| `reactive_inductive_kvar` | Float | nullable — interval value for inductive reactive power (`ERI`) in kVAr |
| `reactive_capacitive_kvar` | Float | nullable — interval value for capacitive reactive power (`ERC`) in kVAr |
| `voltage_v` | Float | nullable — voltage (`E`) in volts when present |
| `quality_score` | Float | 0-1 confidence (mapped from statut_point / indice_vraisemblance) |
| `is_estimated` | Boolean | True if not a real measurement |
| `source_flux_type` | String(10) | `R4H`/`R4M`/`R4Q`/`R50` — provenance |
| `promotion_run_id` | FK → `promotion_run.id` | nullable — which run promoted this row |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**Unique constraint**: `(meter_id, timestamp, pas_minutes)` — one promoted CDC interval per meter and cadence.

**Indexes**: `(meter_id, timestamp)`, `(meter_id, pas_minutes)`, `promotion_run_id`.

**Merge rule**: when the raw staging layer carries multiple CDC rows for the same `(meter_id, timestamp, pas_minutes)` with different `grandeur_physique` values, SF5 merges them into one promoted row before UPSERT. Staging remains the place where the original row-per-grandeur fidelity is preserved.

#### `meter_energy_index` — Cumulative energy index per tariff class

The canonical table for index readings (cumulative counters per tariff class).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `meter_id` | FK → `meter.id` | Linked meter |
| `date_releve` | Date | Reading date |
| `tariff_class_code` | String(10) | `HCE`/`HCH`/`HPE`/`HPH`/`P`/`HC`/`HP`/`HCB`/`HPB` etc. |
| `tariff_class_label` | String(100) | nullable — human-readable label from Enedis |
| `tariff_grid` | String(10) | `CT` (supplier) / `CT_DIST` (distributor) |
| `value_wh` | Float | Cumulative index in Wh |
| `quality_score` | Float | 0-1 confidence |
| `is_estimated` | Boolean | |
| `source_flux_type` | String(10) | `R171`/`R151` — provenance |
| `promotion_run_id` | FK → `promotion_run.id` | nullable |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**Unique constraint**: `(meter_id, date_releve, tariff_class_code, tariff_grid)` — one index value per meter per date per class per grid.

**Indexes**: `(meter_id, date_releve)`, `promotion_run_id`.

> **Note on consumption computation**: Energy consumed between two readings = `index[t] - index[t-1]` for the same tariff class. This delta computation is a downstream service responsibility, not a promotion concern. The promotion pipeline stores the raw index faithfully.

#### `meter_power_peak` — Maximum power demand per period

The canonical table for peak power demand (puissance maximale atteinte).

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `meter_id` | FK → `meter.id` | Linked meter |
| `date_releve` | Date | Measurement period date |
| `value_va` | Float | Peak demand in VA (volt-amperes) |
| `quality_score` | Float | 0-1 confidence |
| `is_estimated` | Boolean | |
| `source_flux_type` | String(10) | `R151` |
| `promotion_run_id` | FK → `promotion_run.id` | nullable |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**Unique constraint**: `(meter_id, date_releve)` — one peak per meter per reading date.

**Indexes**: `(meter_id, date_releve)`, `promotion_run_id`.

### 4.2 New Operational Tables

#### `promotion_run` — Execution audit trail

Mirrors `IngestionRun` pattern from SF4.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `started_at` | DateTime | |
| `finished_at` | DateTime | nullable |
| `status` | String | `running` / `completed` / `failed` |
| `triggered_by` | String | `cli` / `api` |
| `mode` | String | `incremental` / `full` |
| `scope_flux_types` | String | Comma-separated flux types processed (e.g. "R4H,R4M,R50") |
| `high_water_mark_before` | JSON | Per-table high-water marks at start of run |
| `high_water_mark_after` | JSON | Per-table high-water marks at end of run |
| `prms_total` | Integer | Distinct PRMs found in staging data to process |
| `prms_matched` | Integer | PRMs successfully matched to a Meter |
| `prms_unmatched` | Integer | PRMs blocked for unresolved matching reasons (`no_delivery_point`, `no_active_meter`, `multiple_active_meters`) |
| `prms_promoted` | Integer | PRMs whose readings were successfully promoted |
| `prms_failed` | Integer | PRMs that failed during promotion |
| `rows_load_curve` | Integer | Total `meter_load_curve` rows upserted |
| `rows_energy_index` | Integer | Total `meter_energy_index` rows upserted |
| `rows_power_peak` | Integer | Total `meter_power_peak` rows upserted |
| `rows_skipped` | Integer | Rows skipped (e.g. superseded by better republication) |
| `rows_flagged` | Integer | Rows flagged for review (quality degradation) |
| `error_message` | Text | nullable — run-level error if failed |

Concurrency guard: same partial unique index pattern as `IngestionRun` (`WHERE status = 'running'`).

#### `promotion_event` — Per-row audit trail

One row per functional table row that was created, updated, or flagged during a promotion run.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `promotion_run_id` | FK → `promotion_run.id` | Which run produced this event |
| `target_table` | String | `meter_load_curve` / `meter_energy_index` / `meter_power_peak` |
| `target_row_id` | Integer | PK of the row in the target table |
| `action` | String | `created` / `updated` / `skipped` / `flagged` |
| `source_table` | String | `enedis_flux_mesure_r4x` / `r50` / `r171` / `r151` |
| `source_row_id` | Integer | PK of the staging row that produced this |
| `source_flux_file_id` | FK → `enedis_flux_file.id` | The originating flux file |
| `previous_payload_json` | JSON | nullable — prior promoted payload for the target row before update |
| `previous_quality_score` | Float | nullable — old quality if action=updated |
| `new_payload_json` | JSON | Snapshot of the promoted payload written to the target row |
| `new_quality_score` | Float | The promoted quality score |
| `reason` | String | nullable — human-readable (e.g. "republication with better quality R>E") |
| `created_at` | DateTime | |

> **Note on scale**: At 175M readings, this table could grow very large. For the POC, we store all events. For production, we may evolve to: (a) only store `updated`/`flagged` events (not `created` on first load), or (b) partition by date, or (c) move to a separate audit database.

#### `unmatched_prm` — Backlog of PRMs that cannot yet be safely promoted

Historical name kept for the POC. In practice this table covers both truly unmatched PRMs and PRMs blocked by ambiguous meter linkage.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `point_id` | String(14) | The PRM from staging |
| `first_seen_at` | DateTime | When first encountered |
| `last_seen_at` | DateTime | Updated on each promotion run |
| `flux_types` | String | Comma-separated flux types where this PRM appears |
| `measures_count` | Integer | Total staging measures for this PRM (across all flux types) |
| `status` | String | `pending` / `resolved` / `ignored` |
| `block_reason` | String | `no_delivery_point` / `no_active_meter` / `multiple_active_meters` |
| `resolved_at` | DateTime | nullable |
| `resolved_by` | String | nullable — user or "auto" |
| `resolved_meter_id` | FK → `meter.id` | nullable — the Meter it was linked to |
| `notes` | Text | nullable — data manager comments |

### 4.3 Existing Legacy Tables

`meter_reading` remains unchanged. It continues to serve existing services with seed/demo consumption data during SF5. `power_readings` also remains part of the current prototype universe for existing power-focused services.

SF5 does **not** migrate product services to the new promoted tables. It creates the canonical real-data targets first. A later migration effort will transition services to read from `meter_load_curve`, `meter_energy_index`, and `meter_power_peak`.

During the transition period:
- **`meter_reading`** = seed/demo consumption data + CSV imports (legacy/demo)
- **`power_readings`** = current prototype power dataset for existing power services (legacy/demo)
- **`meter_load_curve`** = real Enedis promoted CDC data (new, canonical for future migration)
- **`meter_energy_index`** = real Enedis promoted index data (new, canonical for future migration)
- **`meter_power_peak`** = real Enedis promoted PMAX data (new, canonical for future migration)

During SF5, there is no product cutover. Existing services stay on the legacy/demo universe while the promoted Enedis layer is validated in parallel.

---

## 5. Quality Score Mapping

### 5.1 CDC flux (R4x) — `statut_point` codes

The official Enedis R4x guide defines the semantics of each status code, but **does not** define a numeric quality score. The scores below are therefore **Promeos heuristics** used for conflict resolution and downstream filtering.

| Code | Official meaning (FR) | Promotion interpretation | `quality_score` | `is_estimated` |
|------|------------------------|--------------------------|-----------------|----------------|
| **R** | Réel | Measured point | 1.00 | False |
| **C** | Corrigé | Corrected by Enedis | 0.95 | False |
| **S** | Coupure secteur | Confirmed outage marker | 0.90 | False |
| **T** | Coupure secteur courte | Confirmed short-outage marker | 0.90 | False |
| **F** | Début coupure secteur | Confirmed outage boundary marker | 0.90 | False |
| **G** | Fin coupure secteur | Confirmed outage boundary marker | 0.90 | False |
| **D** | Importé manuellement par le métier Enedis | Manual business import / correction | 0.85 | False |
| **H** | Puissance reconstituée (changements d'heure, conversions de pas) | Deterministic Enedis reconstruction | 0.80 | True |
| **K** | Calculé, point issu d'un calcul basé sur d'autres courbes de charge | Derived from other curves | 0.75 | True |
| **P** | Puissance reconstituée et coupure secteur | Derived point during outage context | 0.70 | True |
| **E** | Estimé | Estimated by Enedis | 0.60 | True |
| *(null/unknown)* | Code inconnu | Unknown status | 0.50 | True |

> **Important provenance note**: `Nature_De_Courbe_Demandee` (`Brute` / `Corrigee`) should be preserved in audit metadata, but the official guide states that Enedis corrections/completions currently apply only to **active energy**. Reactive energy and voltage are not corrected by Enedis.

### 5.2 CDC flux (R50) — `indice_vraisemblance`

| Value | Meaning | `quality_score` | `is_estimated` |
|-------|---------|-----------------|----------------|
| `"0"` | Valeur OK | 1.00 | False |
| `"1"` | Valeur sujette a caution | 0.70 | False |
| *(null/unknown)* | Unknown / absent | 0.50 | False |

> **Confirmed fact from the official R50 guide**: `IV` is a **vraisemblance / quality** flag, not an estimation flag. The guide defines only `0 = valeur OK` and `1 = valeur sujette a caution`.

> **Observed fact from the real corpus**: points with missing `V` are emitted as `<PDC><H>...</H></PDC>` and are skipped at promotion time because there is no numeric value to convert.

### 5.3 Index flux (R151) — `indice_vraisemblance`

Provisional Promeos heuristic for now: keep using the same numeric mapping as R50 until the official R151 guide is re-reviewed, but treat that as a **temporary Promeos choice**, not a confirmed Enedis fact.

### 5.4 Index flux (R171) — No quality indicator

R171 does not carry a per-value quality indicator. All R171 values are assumed measured:
- `quality_score` = 0.90 (slightly below R=1.0 because we cannot confirm)
- `is_estimated` = False

> **To refine**: the official R4x meanings are now validated by Enedis v2.0.3. The remaining work is calibrating the Promeos heuristic ordering on real republications and outage-heavy samples. Current working order: `R > C > S=T=F=G > D > H > K > P > E > unknown`.

---

## 6. Routing & Cadence Mapping

Each staging flux type routes to a specific functional table:

| Staging source | Flux type | Target table | Cadence / `pas_minutes` | Unit |
|----------------|-----------|-------------|------------------------|------|
| `enedis_flux_mesure_r4x` | R4H | **`meter_load_curve`** | parsed from raw `granularite` (`5` or `10`) | kW / kVAr / V |
| `enedis_flux_mesure_r4x` | R4M | **`meter_load_curve`** | parsed from raw `granularite` (`5` or `10`) | kW / kVAr / V |
| `enedis_flux_mesure_r4x` | R4Q | **`meter_load_curve`** | parsed from raw `granularite` (`5` or `10`) | kW / kVAr / V |
| `enedis_flux_mesure_r50` | R50 | **`meter_load_curve`** | `30` | raw `W` -> promoted `kW` |
| `enedis_flux_mesure_r171` | R171 | **`meter_energy_index`** | Per `date_fin` (daily) | Wh |
| `enedis_flux_mesure_r151` | R151 (CT/CT_DIST) | **`meter_energy_index`** | Per `date_releve` | Wh |
| `enedis_flux_mesure_r151` | R151 (PMAX) | **`meter_power_peak`** | Per `date_releve` | VA |

> **Important**: R4x publication cadence (`R4H`, `R4M`, `R4Q`) is **not** the same as measurement cadence. The promoted CDC row stores the exact interval size in `pas_minutes`, not a shared `FrequencyType`.

> **Important**: R4x publication cadence also has an official delivery SLA and should inform later freshness/completeness logic:
>
> | Flux | Covered period | Official publication deadline |
> |------|----------------|-------------------------------|
> | `R4Q` | Day D | `J+1` calendar day |
> | `R4H` | Week ending Friday 23:50 | no later than the 3rd business day after week end, before midnight |
> | `R4M` | Calendar month | no later than the 3rd business day after month end, before midnight |

> **Important**: R50 has its own official publication semantics and they matter for freshness/completeness:
>
> | R50 cadence | Covered period | Official publication rule |
> |-------------|----------------|---------------------------|
> | Daily (`_Q_`) | Day `J` | published during the night from `J+1` to `J+2` |
> | Monthly (`_M_`) | Subscription monthly window, not necessarily calendar month | no later than the 3rd business day after the last collection day |
>
> Additional official constraints:
> - if day `J` was unavailable at the initial daily publication, Enedis may republish it later in a daily R50 flow when the data arrives
> - that delayed daily replay is allowed only while the daily subscription is still active and only if the replay date stays within 20 days of `J`
> - file-group completeness for one subscription + sequence is checked through the filename counters `XXXXX` / `YYYYY`

> **Observed fact from the real monthly corpus**: the monthly R50 files are not aligned to civil months. They cover windows such as `2023-01-04 -> 2023-02-03`, then `2023-02-04 -> 2023-03-03`, which is consistent with the official "publication day 1-28" subscription model.

> **Note on CDC units**: Enedis CDC values are interval averages, not consumption deltas and not instantaneous spot readings. For active power, downstream services that need interval energy compute `energy_kwh = active_power_kw * pas_minutes / 60`.

> **UX interpretation note**: charts, tables, and tooltips should describe a CDC point as "average power over `10:00-10:30`" or equivalent, not "power at 10:30". Step charts, bars, and interval labels are safer defaults than point-sample wording.

> **R4x transport rules to honor in SF5**:
> - parse the explicit XML timezone offset and convert to UTC before enforcing uniqueness
> - treat autumn DST duplicate local timestamps as valid distinct instants
> - treat the missing local hour at spring DST transition as an expected absence, not a gap
> - trust raw `granularite` rather than hardcoding Enedis' 10' → 5' switchover date; unexpected R4x granularities should be flagged

---

## 7. Pipeline Stages (Detailed)

### Stage 1: Discover — Identify new staging data

```
For each staging table (r4x, r50, r171, r151):
    1. Discover new candidates:
        SELECT DISTINCT point_id, flux_file_id, COUNT(*)
        FROM enedis_flux_mesure_<table>
        WHERE id > high_water_mark[table]
          AND flux_file.status IN ('parsed', 'needs_review')
        GROUP BY point_id, flux_file_id

    2. Replay backlog candidates:
        SELECT DISTINCT point_id
        FROM unmatched_prm
        WHERE status = 'pending'
```

The high-water mark (last promoted staging row ID per table) is stored in `promotion_run.high_water_mark_after` (JSON). First run: high-water mark = 0 (process everything). Incremental runs always combine **new candidates** with **still-pending backlog PRMs** so historical raw data is replayed when a PRM is later resolved.

Publication freshness should be tracked separately from PRM backlog:
- no file yet, but official publication deadline not reached -> `expected_not_due`
- no file yet, and official publication deadline exceeded -> `late_publication`
- file received, but some intervals are missing inside the delivered dataset -> data gap / completeness issue

These states should not be collapsed into a single "missing data" bucket because they drive different operational responses.

For R50 specifically:
- freshness must distinguish **daily cadence** from **monthly cadence** using filename nomenclature, not `Pas_Publication`
- monthly completeness must not assume calendar-month boundaries
- multi-file completeness for one subscription/sequence should use `XXXXX` / `YYYYY`

### Stage 2: Match — Resolve PRMs to Meters

```
For each distinct point_id found in Stage 1:
    DeliveryPoint = SELECT * FROM delivery_points WHERE code = point_id AND deleted_at IS NULL
    IF NOT FOUND:
        → INSERT or UPDATE unmatched_prm (status=pending, block_reason=no_delivery_point)
        → Skip this PRM entirely
    Meters = SELECT * FROM meter
             WHERE delivery_point_id = DeliveryPoint.id
               AND is_active = True
               AND energy_vector = 'ELECTRICITY'
    IF COUNT(Meters) = 0:
        → INSERT or UPDATE unmatched_prm (status=pending, block_reason=no_active_meter)
        → Skip
    IF COUNT(Meters) > 1:
        → INSERT or UPDATE unmatched_prm (status=pending, block_reason=multiple_active_meters)
        → Skip
    Meter = the single matching meter
    → PRM is matched: proceed to Stage 3
```

### Stage 3: Resolve — Handle republications

For each matched PRM, across all staging rows to promote:

```
Group staging rows by (point_id, timestamp/horodatage)
For each group:
    IF single row → use it
    IF multiple rows (republications):
        Sort by flux_file.version DESC (latest first)
        Compare quality: latest vs current promoted row (if exists)
        IF latest quality > current quality:
            → Auto-promote latest (action=updated, reason logged)
        ELSE IF latest quality = current quality:
            → Latest wins (action=updated, reason logged)
        ELSE:
            → Flag for review (action=flagged)
            → Do NOT overwrite current promoted row
```

Quality comparison uses the working hierarchy from Section 5: `R > C > S=T=F=G > D > H > K > P > E > unknown`.

### Stage 4: Convert & Route — Transform and assign target table

For each staging row to promote, determine the target table and convert values:

**CDC rows (R4x, R50) → `meter_load_curve`:**
```
if flux_type in ('R4H', 'R4M', 'R4Q'):
    timestamp     = parse_iso8601_to_naive_utc(horodatage)  # raw H is already interval start
    pas_minutes   = int(granularite)
    quality_score = QUALITY_MAP[statut_point]  # Section 5
    is_estimated  = ESTIMATED_MAP[statut_point]  # Section 5
elif flux_type == 'R50':
    interval_end  = parse_iso8601_to_naive_utc(horodatage)
    pas_minutes   = 30
    timestamp     = interval_end - timedelta(minutes=30)  # raw H is interval end in the official guide
    quality_score = R50_IV_QUALITY_MAP[indice_vraisemblance]  # Section 5.2
    is_estimated  = False  # IV is a caution flag, not an estimation flag
    active_power_kw = float(valeur) / 1000  # raw V is average power in W

source_flux_type = flux_type

if flux_type in ('R4H', 'R4M', 'R4Q') and pas_minutes not in (5, 10):
    skip row, log unexpected official R4x granularite

if flux_type in ('R4H', 'R4M', 'R4Q') and grandeur_physique == 'EA':
    active_power_kw = float(raw_value)
if flux_type in ('R4H', 'R4M', 'R4Q') and grandeur_physique == 'ERI':
    reactive_inductive_kvar = float(raw_value)
if flux_type in ('R4H', 'R4M', 'R4Q') and grandeur_physique == 'ERC':
    reactive_capacitive_kvar = float(raw_value)
if flux_type in ('R4H', 'R4M', 'R4Q') and grandeur_physique == 'E' and unite_mesure == 'V':
    voltage_v = float(raw_value)

Merge all CDC rows sharing (meter_id, timestamp, pas_minutes) into one promoted interval row
before UPSERT.

# Semantics:
# - R4x raw H represents the covered interval start: [H ; H + pas_minutes[
# - R50 raw H represents the covered interval end: promoted timestamp = H - 30 min,
#   so the canonical row still represents [timestamp ; timestamp + 30 min[
# any later aggregation to hourly/daily energy must respect this half-open interval model
```

**Index rows (R171, R151 CT/CT_DIST) → `meter_energy_index`:**
```
date_releve         = parse_date(date_fin or date_releve)
tariff_class_code   = code_classe_temporelle or id_classe_temporelle
tariff_class_label  = libelle_classe_temporelle
tariff_grid         = 'CT' or 'CT_DIST' (from R151 type_donnee) or 'CT' (R171 default)
value_wh            = float(valeur)
quality_score       = QUALITY_MAP[indice_vraisemblance]  # Section 5
is_estimated        = mapped from quality indicator
source_flux_type    = flux_type
```

**PMAX rows (R151 PMAX) → `meter_power_peak`:**
```
date_releve    = parse_date(date_releve)
value_va       = float(valeur)
quality_score  = 0.90  # PMAX has no quality indicator; assumed reliable
is_estimated   = False
source_flux_type = 'R151'
```

**Error handling per value:**
- Unparseable float → skip row, log in promotion_event (action=skipped, reason="unparseable value: '{raw}'")
- Unparseable timestamp/date → skip row, log
- Null value with non-null timestamp → skip row, log (never synthesize `0.0`)
- Expected spring DST missing intervals in R4x are not promotion errors and must not be turned into synthetic zeroes or backlog gaps
- Value conversion errors do NOT fail the entire PRM (per-PRM atomicity applies to DB writes, not individual parse errors — but if >50% of readings for a PRM fail to parse, flag the PRM for review)

### Stage 5: Promote — UPSERT into target tables

```
For each PRM (within a DB transaction):
    # Route batches to correct tables
    load_curve_batch = []    # merged CDC interval rows → meter_load_curve
    energy_index_batch = []  # Index rows → meter_energy_index
    power_peak_batch = []    # PMAX rows → meter_power_peak
    
    For each converted row:
        route to appropriate batch based on Stage 4 routing
    
    # Bulk UPSERT each table
    # meter_load_curve: conflict on (meter_id, timestamp, pas_minutes)
    # meter_energy_index: conflict on (meter_id, date_releve, tariff_class_code, tariff_grid)
    # meter_power_peak: conflict on (meter_id, date_releve)
    # On conflict: UPDATE the merged interval columns, quality_score, is_estimated,
    # promotion_run_id, updated_at
    
    for table, batch in [(meter_load_curve, lc_batch), ...]:
        session.execute(upsert_statement(table), batch, chunk_size=1000)
    
    session.commit()  # Per-PRM transaction boundary
```

### Stage 6: Audit — Record promotion events

For each reading processed in Stage 5:

```
INSERT INTO promotion_event (
    promotion_run_id, target_table, target_row_id, action,
    source_table, source_row_id, source_flux_file_id,
    previous_payload_json, previous_quality_score,
    new_payload_json, new_quality_score, reason
)
```

For R4x promotions, the audit payload should also preserve the key source-header provenance already available in staging: `frequence_publication`, `nature_courbe_demandee`, and `reference_demande` (from `header_raw`). This keeps each promoted interval traceable back to the subscribed publication option, not just the raw point row.

### Stage 7: Finalize — Update promotion run

```
UPDATE promotion_run SET
    status = 'completed',
    finished_at = now(),
    high_water_mark_after = {updated marks per table},
    prms_promoted = ..., readings_promoted = ..., etc.
```

**Gap detection note:** SF5 v2 does not yet compute completeness windows, expected-interval counts, or gap-alert objects during promotion. Instead, it preserves the raw conditions needed for a later gap-detection layer:
- missing periods remain visible as absent promoted rows
- invalid values are skipped with audit reasons
- exact CDC cadence is stored in `pas_minutes`
- backlog replay prevents historical gaps caused by late PRM resolution from being silently forgotten
- official publication windows are now documented so a later freshness layer can distinguish `not_due_yet` from `late_publication`

**Publication SLA note:** a missing R4x file before its official publication deadline is not yet evidence of a failed publication. Conversely, once the SLA window has expired, the issue is first an operational publication-lateness signal, and only secondarily a completeness concern for downstream analytics.

---

## 8. Index & PMAX Data Specifics

### 8.1 R171 — Daily index per tariff class (C2-C4)

R171 provides cumulative index values per `code_classe_temporelle` (HCE, HCH, HPE, HPH, P, etc.). These are running totals, not consumption deltas.

**Decision**: Store raw index values in `meter_energy_index`. The `tariff_class_code` column preserves the per-class granularity. Downstream services compute consumption as `index[t] - index[t-1]` for each class separately, or sum all classes for total consumption.

Example promotion of one R171 row:
```
Staging:  point_id=30001234567890, code_classe_temporelle=HPE,
          date_fin=2024-06-15, valeur=12345678
    ↓
meter_energy_index:  meter_id=42, date_releve=2024-06-15,
                     tariff_class_code=HPE, tariff_grid=CT,
                     value_wh=12345678.0, quality_score=0.90
```

### 8.2 R151 — Index + Puissance max per tariff class (C5)

R151 carries three data types via `type_donnee`, routed to **two different tables**:

| `type_donnee` | Data | Target table | Description |
|---------------|------|-------------|-------------|
| `CT` | Supplier index | `meter_energy_index` | Energy index per supplier tariff class (HP/HC etc.) |
| `CT_DIST` | Distributor index | `meter_energy_index` | Energy index per distributor grid class (TURPE) |
| `PMAX` | Peak power | `meter_power_peak` | Maximum demand in VA for the period |

The `tariff_grid` column in `meter_energy_index` distinguishes CT from CT_DIST, allowing billing services to use the appropriate grid for their calculations (supplier billing uses CT, TURPE billing uses CT_DIST).

### 8.3 PMAX — Subscribed Power Monitoring

PMAX values go to the dedicated `meter_power_peak` table (D16). This data feeds:
- Subscribed power optimization (is the client paying for more kVA than they use?)
- Depassement alerts (did demand exceed subscribed power?)
- Contract renegotiation recommendations

PMAX has no `indice_vraisemblance` in R151, so `quality_score` defaults to 0.90.

---

## 9. Blocked / Unmatched PRM Workflow

### Operational backlog (future UX, no dedicated review endpoints in SF5)

`unmatched_prm` acts as an operational backlog for PRMs that cannot yet be safely promoted. In SF5, this backlog is stored in the database and replayed by each incremental run, but the dedicated manual review UX/API is deferred.

The data manager can:
1. **Link to existing**: If the PRM belongs to an existing site, create/update the DeliveryPoint + Meter link
2. **Onboard new site**: Create a new Site + DeliveryPoint + Meter for this PRM
3. **Ignore**: Mark as `ignored` (e.g., test PRM, competitor data)

Once resolved, the next promotion run automatically replays the pending historical staging data for that PRM from the backlog.

### Auto-resolution (future evolution)

When a new DeliveryPoint is created (via patrimoine onboarding or Enedis DataConnect), the system could automatically check the `unmatched_prm` table and resolve matches. Not in SF5 scope, but the data model supports it.

---

## 10. CLI Interface

```
python -m data_staging.cli promote [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--mode` | `incremental` | `incremental` (new data only) or `full` (rebuild from scratch) |
| `--flux-types` | All | Comma-separated: `R4H,R4M,R4Q,R50,R171,R151` |
| `--dry-run` | Off | Analyze without writing to promoted tables |
| `--verbose` | Off | Detailed per-PRM logging |

### Output

```
=== Promotion Run #12 ===
Mode:          incremental
Flux types:    R4H, R4M, R4Q, R50, R171, R151
Duration:      4.1s

PRMs:
  Total found:    142
  Matched:        138
  Blocked:          4  (pending backlog for manual resolution)
  Promoted:       138
  Failed:           0

Rows promoted:
  meter_load_curve:    11,200 created  +  1,256 updated  =  12,456
  meter_energy_index:     830 created  +     42 updated  =     872
  meter_power_peak:        68 created  +      0 updated  =      68
  Skipped:         34  (superseded by better republication)
  Flagged:          8  (quality degradation — review needed)

Quality breakdown (CDC):
  R (measured):   11,890  (95.5%)
  E (estimated):     412  ( 3.3%)
  Other:             154  ( 1.2%)
```

---

## 11. API Scaffolding

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/enedis/promotion/promote` | Trigger promotion run. Body: `{mode, flux_types, dry_run}` |
| GET | `/api/enedis/promotion/runs` | List promotion runs with pagination |
| GET | `/api/enedis/promotion/runs/{id}` | Run detail + counters |
| GET | `/api/enedis/promotion/stats` | Aggregated stats: promoted rows by target table, quality distribution, backlog summary |

Manual review workflows for blocked PRMs remain out of scope for SF5.

---

## 12. Implementation Phases

This feature is too large for a single implementation session. Proposed phasing:

### Phase A: Foundation & Data Model (1-2 sessions)
- Create `backend/data_staging/` module skeleton
- New functional tables: `meter_load_curve`, `meter_energy_index`, `meter_power_peak`
- Operational tables: `PromotionRun`, `PromotionEvent`, `UnmatchedPrm`
- PRM matching logic (point_id → DeliveryPoint → exactly one active electricity Meter)
- High-water mark tracking
- Backlog replay for pending PRMs
- CLI skeleton with `--dry-run`
- Migration script for new tables
- Tests: matching logic, unmatched PRM detection, model creation

### Phase B: CDC Promotion — R4x (2-3 sessions)
- R4x promotion pipeline (R4H/R4M/R4Q → `meter_load_curve`)
- Value conversion (string → typed power columns, ISO8601 → datetime UTC-naive)
- Quality score mapping (statut_point → quality_score)
- `pas_minutes` fidelity (preserve raw `granularite`, do not map to `FrequencyType`)
- Merge multi-grandeur CDC rows into one promoted interval row
- Bulk UPSERT with per-PRM atomicity
- Audit trail (PromotionEvent for created/updated)
- Tests: full pipeline with fixtures

### Phase C: CDC Promotion — R50 (1 session)
- R50 promotion pipeline (→ `meter_load_curve`)
- `indice_vraisemblance` quality mapping
- Tests

### Phase D: Republication Handling (1-2 sessions)
- Republication resolution logic (better quality auto-promote, equal quality latest wins, worse quality flags)
- Quality degradation detection and flagging
- PromotionEvent logging for updates
- Tests: republication scenarios

### Phase E: Index Promotion — R171 + R151 (2-3 sessions)
- R171 promotion (→ `meter_energy_index`, daily index per tariff class)
- R151 CT/CT_DIST promotion (→ `meter_energy_index`, with `tariff_grid` column)
- R151 PMAX promotion (→ `meter_power_peak`)
- Tests: index promotion, PMAX routing, tariff class handling

### Phase F: API + Operations (1 session)
- Minimal REST endpoints (trigger, runs, stats)
- Stats endpoint (per-table breakdowns)
- Wiring into `main.py`
- Tests

### Phase G: Backfill + Validation (1 session)
- Full backfill mode (`--mode full`)
- Performance profiling on full dataset
- Documentation update

### Post-SF5 follow-up — Service Migration (separate feature wave)
- Migrate monitoring/anomaly services from `meter_reading` → `meter_load_curve`
- Migrate billing/regulatory services to consume `meter_energy_index`
- Migrate power analysis to consume `meter_power_peak`
- Update consumption_unified_service to use new tables
- Update EMS timeseries_service
- Update consumption_diagnostic
- Tests: verify all downstream services work with real Enedis data

---

## 13. Open Questions (for future iterations)

| # | Question | Status | Context |
|---|----------|--------|---------|
| OQ1 | ~~R171 index storage: store raw index, computed delta, or both?~~ | **Resolved (D16)** | Store raw index in `meter_energy_index`. Delta is downstream service responsibility |
| OQ2 | ~~R151 PMAX: separate table or metadata in MeterReading?~~ | **Resolved (D16)** | Separate `meter_power_peak` table |
| OQ3 | ~~R171 tariff class columns: extend MeterReading or new model?~~ | **Resolved (D16)** | `meter_energy_index` has `tariff_class_code` and `tariff_grid` columns |
| OQ4 | `promotion_event` table growth at scale (175M+ rows) | Open | May need partitioning, archival, or selective logging strategy |
| OQ5 | Gap detection, completeness scoring, and interpolation / estimation service | Open | Future feature to detect missing intervals explicitly, score completeness, and optionally fill gaps with statistical estimates |
| OQ6 | R4x `statut_point` score calibration on real republications/outage cases | Open | Official meanings are now validated by Enedis R4x v2.0.3; the remaining question is whether Promeos' heuristic scores and `is_estimated` buckets need tuning on real data |
| OQ7 | Auto-resolution of unmatched PRMs when new DeliveryPoints are onboarded | Open | Natural extension of the unmatched PRM workflow |
| OQ8 | Multi-XML R4x archive support in SF1-SF4 raw ingestion | Open | The official guide allows 1..n XML per ZIP archive. Current POC observations were mono-XML, but staging completeness depends on hardening this assumption |
| OQ9 | Business-day calendar for R4H/R4M SLA evaluation | Open | "3rd business day" needs an explicit calendar/timezone policy before we operationalize `late_publication` detection |
| OQ10 | R50 cadence/file-group completeness tracking from filename nomenclature | Open | Daily vs monthly cadence, subscription monthly day, and `XXXXX`/`YYYYY` completeness are official R50 rules but are not yet modeled as first-class staging metadata |

---

## 14. Success Criteria

- [ ] CDC data (R4x, R50) promoted to `meter_load_curve` with correct typed power columns and exact `pas_minutes`
- [ ] Index data (R171, R151 CT/CT_DIST) promoted to `meter_energy_index` with tariff class granularity
- [ ] PMAX data (R151) promoted to `meter_power_peak`
- [ ] Unmatched PRMs are flagged, zero unidentified data in production
- [ ] Ambiguous PRM mappings are blocked and replayed from backlog once resolved
- [ ] Every promoted row is traceable to its source staging row via `promotion_event`
- [ ] Republications with better quality auto-replace, equal-quality ties use latest version, worse quality is flagged without overwrite
- [ ] Incremental mode processes both new data and pending backlog
- [ ] Full backfill mode can rebuild from scratch
- [ ] Per-PRM atomicity: one bad PRM doesn't block others
- [ ] CLI provides clear per-table promotion report
- [ ] API scaffolding endpoints functional for trigger, runs, and stats
- [ ] Quality scores correctly mapped from Enedis status codes
- [ ] R4x DST spring/fall behavior handled without false gaps or unique-key collisions
- [ ] Pipeline handles 175M-row scale (batch processing, chunked inserts)
- [ ] All promotion runs audited with full counters
- [ ] Null or unparsable Enedis values never produce synthetic zero rows in promoted tables
- [ ] Existing `meter_reading`, `power_readings`, and downstream services remain unaffected during SF5
- [ ] SF5 prepares canonical real-data tables for later service migration

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **PRM** | Point de Reference Mesure — 14-digit Enedis delivery point identifier |
| **CDC** | Courbe De Charge — load curve (time-series power data, kW at each interval) |
| **Index** | Cumulative meter reading per tariff class (energy in Wh) |
| **PMAX** | Puissance Maximale Atteinte — peak power demand in VA for a period |
| **Power (kW)** | Average power over the covered forward interval — what CDC measures. Stored in `meter_load_curve` |
| **Energy (kWh/Wh)** | Cumulative consumption over a period — what index measures. Stored in `meter_energy_index` |
| **Staging** | Raw Enedis data stored as-is (strings, no transformation) in `enedis_flux_mesure_*` tables |
| **Promotion** | Transforming and writing staging data into functional tables (`meter_load_curve`, `meter_energy_index`, `meter_power_peak`) |
| **Republication** | When Enedis sends a new version of previously-sent data (corrections) |
| **High-water mark** | The last staging row ID processed per table for newly discovered data. Pending backlog PRMs are replayed separately during incremental runs |
| **`pas_minutes`** | Exact CDC interval size stored on promoted `meter_load_curve` rows (`5`, `10`, `30`) |
| **`[start ; end[`** | Half-open interval semantics used for CDC rows: start included, end excluded |
| **Statut_point** | Enedis measurement-status / provenance code (R/H/P/S/T/F/G/E/C/K/D) carried by R4x points |
| **Indice_vraisemblance** | Quality indicator whose meaning depends on the flux. For R50, the official guide defines `0=valeur OK`, `1=valeur sujette a caution` |
| **Tariff class** | Time-of-use period (HCE=heures creuses ete, HPH=heures pleines hiver, etc.) |
| **CT / CT_DIST** | Supplier grid (CT) vs distributor grid (CT_DIST) — two parallel tariff classification systems |
