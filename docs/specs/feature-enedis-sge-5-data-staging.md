# SF5 — Enedis Data Staging: Raw → Functional Promotion Pipeline

> **Status**: PRD v2 — Separate functional tables (CDC / Energy Index / Power Peak)
> **Depends on**: SF1 (decrypt), SF2 (CDC ingestion), SF3 (index ingestion), SF4 (operationalization) — all complete and merged
> **Module**: `backend/data_staging/` (new, separate from `data_ingestion/`)

---

## 1. Problem Statement

SF1-SF4 delivered a complete raw ingestion pipeline: 6 flux types parsed, 5 staging tables, 91 real files ingested, 123,846 measures — all stored as raw strings with zero transformation. This raw archive is the **source of truth** for everything Enedis sends us.

However, **no bridge exists** between the raw staging tables and the functional layer that powers every downstream service: consumption dashboards, anomaly detection, monitoring alerts, regulatory compliance, and billing reconciliation.

Today, `MeterReading` is populated exclusively by synthetic seed data. The raw staging data — real Enedis measurements — is invisible to the application.

Furthermore, the existing `MeterReading` model conflates two fundamentally different physical quantities:
- **Power (kW)** — instantaneous demand at a point in time (what CDC load curves measure)
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
                                     │              │  5. Gap Detection      │
                                     │              │  6. Route & UPSERT    │
                                     │              │  7. Audit Trail        │
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

### Three Functional Tables

| Table | Physical quantity | Unit | Source flux | Downstream consumers |
|-------|------------------|------|-------------|---------------------|
| **`meter_load_curve`** | Power at each interval (CDC) | kW (kVAr for reactive) | R4x, R50 | Monitoring, anomaly detection, peak analysis, off-hours, load profile |
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
          timestamp     = parsed datetime (UTC-naive from ISO8601+TZ)
          value_kw      = parsed float from raw string (power, not energy)
          frequency     = mapped FrequencyType from flux granularity
          quality_score = mapped from statut_point / indice_vraisemblance
          is_estimated  = True if statut_point not in (R, C, K, H)
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
| D2 | Unmatched PRMs | **Flag and block** — never promote unidentified data | No data leaks to production. Data manager review screen shows unmatched PRMs. Once resolved, next promotion run picks them up |
| D3 | Pipeline mode | **Incremental** — only process new/changed staging data since last promotion | Designed for scale. Easier to evolve to production-grade. Tracks a high-water mark per flux table |
| D4 | Republication strategy | **Auto-promote if quality improves**, flag if quality degrades | If newer version has equal or better `statut_point`, auto-replace. If worse, flag for human review. Full audit trail in both cases |
| D5 | Production versioning | **Option A — Current truth + audit trail** | Functional tables always hold the latest best value (UPSERT). Staging keeps full history. `PromotionEvent` table provides full traceability. No `WHERE is_current` tax on all downstream queries |
| D6 | Quality gate | **Promote all data with correct quality flags** | No minimum threshold blocking promotion. Even poor-quality data is promoted with appropriate `quality_score` and `is_estimated` flags. Downstream services already compute quality scores from these fields |
| D7 | Gap handling | **Promote transparently** — gaps are visible as missing MeterReading rows | Downstream gap detection (monitoring, diagnostic) naturally picks up missing periods. Future feature may add interpolation/estimation |
| D8 | Quality score mapping | **Enedis statut_point → 0-1 float** (see Section 5) | Research-based mapping from official Enedis SGE documentation. Refinement planned when official docs are available |
| D9 | Module location | **`backend/data_staging/`** (new, separate module) | Separation of concerns. Will grow to handle GRDF, GTB, sub-meters, other ELDs. `data_ingestion/` = raw archive, `data_staging/` = normalization + promotion |
| D10 | Trigger model | **Separate from ingestion** — dedicated CLI command + API endpoint | Natural break point: ingest → data manager reviews unmatched PRMs → promote. Decoupled failure domains. POC: CLI `promote` command. Prod: orchestrator chains them |
| D11 | Atomicity | **Per-PRM** | Each PRM is fully promoted or not at all. One bad PRM doesn't block the fleet. Prevents misleading partial data. Aligns with business unit (site managers care about their PRMs) |
| D12 | Audit trail | **Yes — `PromotionRun` + `PromotionEvent` tables** | Core MOAT. Every promoted reading traceable to source staging row, flux file, and promotion run. Every replacement logged |
| D13 | API surface | **CLI + API scaffolding** (no UX yet) | POST `/api/staging/promote`, GET `/api/staging/runs`, GET `/api/staging/unmatched-prms`, GET `/api/staging/stats` |
| D14 | Scale target | **175M rows** (10,000 PRMs x 2 years hourly) | Code must handle this volume even if POC runs on SQLite. Batch processing, chunked inserts, indexed lookups |
| D15 | Initial run | **Full backfill** — promote all historical staging data | First run processes everything. Subsequent runs are incremental |
| D16 | Functional data model | **Three separate tables**: `meter_load_curve` (CDC power kW), `meter_energy_index` (cumulative energy Wh per tariff class), `meter_power_peak` (max demand VA) | Power and energy are different physical quantities with different units, granularities, and consumers. Mixing them in one table creates semantic confusion. `meter_reading` (legacy) remains for seed data until services are migrated |
| D17 | Legacy `meter_reading` | **Coexist then migrate** — new tables are canonical for real data, `meter_reading` stays for seed/legacy until services migrate | Don't break what works. Services migrate to new tables incrementally after SF5 is complete |
| D18 | `meter_load_curve` value column | **TBD** — `value_kw` with separate `unit` column, or `value_kw` + `value_kvar` | Needs deeper analysis of reactive power (ERC/ERI) use cases before deciding |

---

## 4. Data Model Changes

### 4.1 New Functional Tables

#### `meter_load_curve` — CDC time-series power data

The canonical table for load curve (courbe de charge) data. Stores power measurements at regular intervals.

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `meter_id` | FK → `meter.id` | Linked meter (resolved from PRM via DeliveryPoint) |
| `timestamp` | DateTime | Measurement instant (UTC-naive, converted from ISO8601+TZ) |
| `frequency` | Enum FrequencyType | `15min` / `30min` / `hourly` |
| `value_kw` | Float | Active power in kW |
| `grandeur_physique` | String(10) | nullable — `EA`/`ERI`/`ERC`/`E` from Enedis (for future reactive power support) |
| `quality_score` | Float | 0-1 confidence (mapped from statut_point / indice_vraisemblance) |
| `is_estimated` | Boolean | True if not a real measurement |
| `source_flux_type` | String(10) | `R4H`/`R4M`/`R4Q`/`R50` — provenance |
| `promotion_run_id` | FK → `promotion_run.id` | nullable — which run promoted this row |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

**Unique constraint**: `(meter_id, timestamp, frequency)` — same pattern as MeterReading.

**Indexes**: `(meter_id, timestamp)`, `(meter_id, frequency)`, `promotion_run_id`.

> **D18 (TBD)**: The `value_kw` column handles active power (EA). For reactive power (ERI/ERC), we may later add `value_kvar` or use the `grandeur_physique` column to distinguish. The `grandeur_physique` column is stored from staging to preserve this information for future use.

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
| `prms_unmatched` | Integer | PRMs with no matching DeliveryPoint/Meter |
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
| `previous_value` | Float | nullable — old value if action=updated |
| `previous_quality_score` | Float | nullable — old quality if action=updated |
| `new_value` | Float | The promoted value |
| `new_quality_score` | Float | The promoted quality score |
| `reason` | String | nullable — human-readable (e.g. "republication with better quality R>E") |
| `created_at` | DateTime | |

> **Note on scale**: At 175M readings, this table could grow very large. For the POC, we store all events. For production, we may evolve to: (a) only store `updated`/`flagged` events (not `created` on first load), or (b) partition by date, or (c) move to a separate audit database.

#### `unmatched_prm` — PRMs found in staging with no matching DeliveryPoint

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer PK | |
| `point_id` | String(14) | The PRM from staging |
| `first_seen_at` | DateTime | When first encountered |
| `last_seen_at` | DateTime | Updated on each promotion run |
| `flux_types` | String | Comma-separated flux types where this PRM appears |
| `measures_count` | Integer | Total staging measures for this PRM (across all flux types) |
| `status` | String | `pending` / `resolved` / `ignored` |
| `resolved_at` | DateTime | nullable |
| `resolved_by` | String | nullable — user or "auto" |
| `resolved_meter_id` | FK → `meter.id` | nullable — the Meter it was linked to |
| `notes` | Text | nullable — data manager comments |

### 4.3 Existing Table: `meter_reading` (legacy)

`meter_reading` remains unchanged. It continues to serve existing services (consumption dashboards, monitoring, anomaly detection) with seed data. After SF5 is complete, a dedicated migration effort will transition these services to read from `meter_load_curve` and `meter_energy_index` instead.

During the transition period:
- **`meter_reading`** = seed data + CSV imports (legacy)
- **`meter_load_curve`** = real Enedis CDC power data (new, canonical)
- **`meter_energy_index`** = real Enedis index data (new, canonical)
- **`meter_power_peak`** = real Enedis PMAX data (new, canonical)

No service reads from both — there is no cross-contamination risk.

---

## 5. Quality Score Mapping

### 5.1 CDC flux (R4x) — `statut_point` codes

Based on Enedis SGE technical documentation for courbes de charge:

| Code | Meaning (FR) | Meaning (EN) | `quality_score` | `is_estimated` |
|------|-------------|--------------|-----------------|----------------|
| **R** | Reel | Measured (real) | 1.00 | False |
| **C** | Corrige | Corrected by Enedis | 0.95 | False |
| **K** | Corrige v2 | Corrected by Enedis (variant) | 0.95 | False |
| **H** | Reel modifie | Adjusted measured value | 0.90 | False |
| **S** | Substitue | Substituted after validation | 0.85 | True |
| **G** | Calcule/Agrege | Calculated/aggregated | 0.75 | True |
| **E** | Estime | Estimated by Enedis | 0.60 | True |
| **T** | Temporaire | Temporary/provisional | 0.50 | True |
| **F** | Forfaitaire | Flat-rate estimate | 0.40 | True |
| **P** | Absence de donnees | No data / interpolated | 0.10 | True |
| **D** | Donnees manquantes | Data missing/deleted | 0.05 | True |
| *(null/unknown)* | Code inconnu | Unknown status | 0.50 | True |

### 5.2 CDC flux (R50) — `indice_vraisemblance`

| Value | Meaning | `quality_score` | `is_estimated` |
|-------|---------|-----------------|----------------|
| `"0"` | Reel (measured) | 1.00 | False |
| `"1"` | Estime/reconstitue | 0.60 | True |
| *(null/unknown)* | Unknown | 0.50 | True |

### 5.3 Index flux (R151) — `indice_vraisemblance`

Same mapping as R50.

### 5.4 Index flux (R171) — No quality indicator

R171 does not carry a per-value quality indicator. All R171 values are assumed measured:
- `quality_score` = 0.90 (slightly below R=1.0 because we cannot confirm)
- `is_estimated` = False

> **To refine**: These mappings should be validated against official Enedis documentation when available. The hierarchy (R > C/K > H > S > G > E > T > F > P > D) is the key invariant for republication comparison (D4).

---

## 6. Routing & Frequency Mapping

Each staging flux type routes to a specific functional table:

| Staging source | Flux type | Target table | Frequency / Granularity | Unit |
|----------------|-----------|-------------|------------------------|------|
| `enedis_flux_mesure_r4x` | R4H | **`meter_load_curve`** | `HOURLY` | kW |
| `enedis_flux_mesure_r4x` | R4M | **`meter_load_curve`** | `MIN_30` | kW |
| `enedis_flux_mesure_r4x` | R4Q | **`meter_load_curve`** | `MIN_15` | kW |
| `enedis_flux_mesure_r50` | R50 | **`meter_load_curve`** | `MIN_30` | kW |
| `enedis_flux_mesure_r171` | R171 | **`meter_energy_index`** | Per `date_fin` (daily) | Wh |
| `enedis_flux_mesure_r151` | R151 (CT/CT_DIST) | **`meter_energy_index`** | Per `date_releve` | Wh |
| `enedis_flux_mesure_r151` | R151 (PMAX) | **`meter_power_peak`** | Per `date_releve` | VA |

> **Note on R4x units**: Enedis CDC values are instantaneous power (kW), not energy (kWh). They are stored as-is in `meter_load_curve.value_kw`. Downstream services that need energy (kWh) compute it as: `value_kw × interval_hours` (e.g., hourly: ×1, 30min: ×0.5, 15min: ×0.25).

---

## 7. Pipeline Stages (Detailed)

### Stage 1: Discover — Identify new staging data

```
For each staging table (r4x, r50, r171, r151):
    SELECT DISTINCT point_id, flux_file_id, COUNT(*)
    FROM enedis_flux_mesure_<table>
    WHERE id > high_water_mark[table]
      AND flux_file.status IN ('parsed', 'needs_review')
    GROUP BY point_id, flux_file_id
```

The high-water mark (last promoted staging row ID per table) is stored in `promotion_run.high_water_mark_after` (JSON). First run: high-water mark = 0 (process everything).

### Stage 2: Match — Resolve PRMs to Meters

```
For each distinct point_id found in Stage 1:
    DeliveryPoint = SELECT * FROM delivery_points WHERE code = point_id
    IF NOT FOUND:
        → INSERT or UPDATE unmatched_prm (status=pending)
        → Skip this PRM entirely
    Meter = SELECT * FROM meter WHERE delivery_point_id = DeliveryPoint.id AND is_active = True
    IF NOT FOUND:
        → Same: flag as unmatched (DeliveryPoint exists but no active Meter)
        → Skip
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
        Compare quality: latest vs current MeterReading (if exists)
        IF latest quality >= current quality:
            → Auto-promote latest (action=updated, reason logged)
        ELSE:
            → Flag for review (action=flagged)
            → Do NOT overwrite current MeterReading
```

Quality comparison uses the hierarchy from Section 5: R > C/K > H > S > G > E > T > F > P > D.

### Stage 4: Convert & Route — Transform and assign target table

For each staging row to promote, determine the target table and convert values:

**CDC rows (R4x, R50) → `meter_load_curve`:**
```
timestamp   = parse_iso8601_to_naive_utc(horodatage)
value_kw    = float(valeur_point)
frequency   = FREQUENCY_MAP[flux_type]  # Section 6
quality_score = QUALITY_MAP[statut_point or indice_vraisemblance]  # Section 5
is_estimated  = statut_point not in ('R', 'C', 'K', 'H')
grandeur_physique = from staging row (EA/ERI/ERC/E)
source_flux_type  = flux_type
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
- Null value with non-null timestamp → promote with `value=0.0`, `quality_score=0.05`, `is_estimated=True` (explicit zero, not silent gap)
- Value conversion errors do NOT fail the entire PRM (per-PRM atomicity applies to DB writes, not individual parse errors — but if >50% of readings for a PRM fail to parse, flag the PRM for review)

### Stage 5: Promote — UPSERT into target tables

```
For each PRM (within a DB transaction):
    # Route batches to correct tables
    load_curve_batch = []    # CDC rows → meter_load_curve
    energy_index_batch = []  # Index rows → meter_energy_index
    power_peak_batch = []    # PMAX rows → meter_power_peak
    
    For each converted row:
        route to appropriate batch based on Stage 4 routing
    
    # Bulk UPSERT each table
    # meter_load_curve: conflict on (meter_id, timestamp, frequency)
    # meter_energy_index: conflict on (meter_id, date_releve, tariff_class_code, tariff_grid)
    # meter_power_peak: conflict on (meter_id, date_releve)
    # On conflict: UPDATE value, quality_score, is_estimated, promotion_run_id, updated_at
    
    for table, batch in [(meter_load_curve, lc_batch), ...]:
        session.execute(upsert_statement(table), batch, chunk_size=1000)
    
    session.commit()  # Per-PRM transaction boundary
```

### Stage 6: Audit — Record promotion events

For each reading processed in Stage 5:

```
INSERT INTO promotion_event (
    promotion_run_id, meter_reading_id, action,
    source_table, source_row_id, source_flux_file_id,
    previous_value_kwh, previous_quality_score,
    new_value_kwh, new_quality_score, reason
)
```

### Stage 7: Finalize — Update promotion run

```
UPDATE promotion_run SET
    status = 'completed',
    finished_at = now(),
    high_water_mark_after = {updated marks per table},
    prms_promoted = ..., readings_promoted = ..., etc.
```

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

## 9. Unmatched PRM Workflow

### Data manager screen (future UX, API scaffolded in SF5)

```
GET /api/staging/unmatched-prms
→ [
    {
      "point_id": "30001234567890",
      "first_seen_at": "2024-01-15T10:00:00",
      "flux_types": ["R4H", "R50"],
      "measures_count": 8760,
      "status": "pending"
    },
    ...
  ]
```

The data manager can:
1. **Link to existing**: If the PRM belongs to an existing site, create/update the DeliveryPoint + Meter link
2. **Onboard new site**: Create a new Site + DeliveryPoint + Meter for this PRM
3. **Ignore**: Mark as `ignored` (e.g., test PRM, competitor data)

Once resolved, the next promotion run automatically picks up the pending staging data for that PRM.

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
| `--dry-run` | Off | Analyze without writing to MeterReading |
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
  Unmatched:       4  (see /api/staging/unmatched-prms)
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
| POST | `/api/staging/promote` | Trigger promotion run. Body: `{mode, flux_types, dry_run}` |
| GET | `/api/staging/runs` | List promotion runs with pagination |
| GET | `/api/staging/runs/{id}` | Run detail + counters |
| GET | `/api/staging/unmatched-prms` | List unmatched PRMs with filters (status, flux_type) |
| PATCH | `/api/staging/unmatched-prms/{id}` | Update status (resolve, ignore) |
| GET | `/api/staging/stats` | Aggregated stats: promoted readings by flux type, quality distribution, gap summary |

---

## 12. Implementation Phases

This feature is too large for a single implementation session. Proposed phasing:

### Phase A: Foundation & Data Model (1-2 sessions)
- Create `backend/data_staging/` module skeleton
- New functional tables: `meter_load_curve`, `meter_energy_index`, `meter_power_peak`
- Operational tables: `PromotionRun`, `PromotionEvent`, `UnmatchedPrm`
- PRM matching logic (point_id → DeliveryPoint → Meter)
- High-water mark tracking
- CLI skeleton with `--dry-run`
- Migration script for new tables
- Tests: matching logic, unmatched PRM detection, model creation

### Phase B: CDC Promotion — R4x (2-3 sessions)
- R4x promotion pipeline (R4H/R4M/R4Q → `meter_load_curve`)
- Value conversion (string → float kW, ISO8601 → datetime UTC-naive)
- Quality score mapping (statut_point → quality_score)
- Frequency mapping (granularity → FrequencyType)
- Bulk UPSERT with per-PRM atomicity
- Audit trail (PromotionEvent for created/updated)
- Tests: full pipeline with fixtures

### Phase C: CDC Promotion — R50 (1 session)
- R50 promotion pipeline (→ `meter_load_curve`)
- `indice_vraisemblance` quality mapping
- Tests

### Phase D: Republication Handling (1-2 sessions)
- Republication resolution logic (compare quality, auto-promote or flag)
- Quality degradation detection and flagging
- PromotionEvent logging for updates
- Tests: republication scenarios

### Phase E: Index Promotion — R171 + R151 (2-3 sessions)
- R171 promotion (→ `meter_energy_index`, daily index per tariff class)
- R151 CT/CT_DIST promotion (→ `meter_energy_index`, with `tariff_grid` column)
- R151 PMAX promotion (→ `meter_power_peak`)
- Tests: index promotion, PMAX routing, tariff class handling

### Phase F: API + Operations (1 session)
- REST endpoints (scaffolding)
- Unmatched PRM list/update endpoints
- Stats endpoint (per-table breakdowns)
- Wiring into `main.py`
- Tests

### Phase G: Backfill + Validation (1 session)
- Full backfill mode (`--mode full`)
- Performance profiling on full dataset
- Documentation update

### Phase H: Service Migration (2-3 sessions) — post-SF5
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
| OQ5 | `meter_load_curve` reactive power columns (D18) | **TBD** | `value_kw` + `unit` column, or `value_kw` + `value_kvar`? Depends on ERI/ERC use cases |
| OQ6 | Gap interpolation / estimation service | Open | Future feature to fill gaps with statistical estimates |
| OQ7 | Enedis `statut_point` quality mapping refinement | Open | Needs validation against official SGE documentation |
| OQ8 | Auto-resolution of unmatched PRMs when new DeliveryPoints are onboarded | Open | Natural extension of the unmatched PRM workflow |
| OQ9 | ~~R4x units: kW vs kWh conversion strategy~~ | **Resolved (D16)** | `meter_load_curve.value_kw` stores power. kW→kWh conversion is downstream |
| OQ10 | Service migration scope and sequencing (Phase H) | Open | Which services to migrate first? Priority by real-data impact |
| OQ11 | `meter_reading` deprecation timeline | Open | When can the legacy table be dropped? Depends on Phase H completion |

---

## 14. Success Criteria

- [ ] CDC data (R4x, R50) promoted to `meter_load_curve` with correct kW values and frequency
- [ ] Index data (R171, R151 CT/CT_DIST) promoted to `meter_energy_index` with tariff class granularity
- [ ] PMAX data (R151) promoted to `meter_power_peak`
- [ ] Unmatched PRMs are flagged, zero unidentified data in production
- [ ] Every promoted row is traceable to its source staging row via `promotion_event`
- [ ] Republications with better quality auto-replace, worse quality flagged
- [ ] Incremental mode processes only new data (high-water mark works)
- [ ] Full backfill mode can rebuild from scratch
- [ ] Per-PRM atomicity: one bad PRM doesn't block others
- [ ] CLI provides clear per-table promotion report
- [ ] API scaffolding endpoints functional
- [ ] Quality scores correctly mapped from Enedis status codes
- [ ] Pipeline handles 175M-row scale (batch processing, chunked inserts)
- [ ] All promotion runs audited with full counters
- [ ] Existing `meter_reading` and downstream services unaffected (no breaking changes)

---

## 15. Glossary

| Term | Definition |
|------|-----------|
| **PRM** | Point de Reference Mesure — 14-digit Enedis delivery point identifier |
| **CDC** | Courbe De Charge — load curve (time-series power data, kW at each interval) |
| **Index** | Cumulative meter reading per tariff class (energy in Wh) |
| **PMAX** | Puissance Maximale Atteinte — peak power demand in VA for a period |
| **Power (kW)** | Instantaneous demand — what CDC measures. Stored in `meter_load_curve` |
| **Energy (kWh/Wh)** | Cumulative consumption over a period — what index measures. Stored in `meter_energy_index` |
| **Staging** | Raw Enedis data stored as-is (strings, no transformation) in `enedis_flux_mesure_*` tables |
| **Promotion** | Transforming and writing staging data into functional tables (`meter_load_curve`, `meter_energy_index`, `meter_power_peak`) |
| **Republication** | When Enedis sends a new version of previously-sent data (corrections) |
| **High-water mark** | The last staging row ID processed per table, used for incremental runs |
| **Statut_point** | Enedis quality code (R/H/P/S/T/F/G/E/C/K/D) indicating measurement reliability |
| **Indice_vraisemblance** | R50/R151 quality indicator (0=measured, 1=estimated) |
| **Tariff class** | Time-of-use period (HCE=heures creuses ete, HPH=heures pleines hiver, etc.) |
| **CT / CT_DIST** | Supplier grid (CT) vs distributor grid (CT_DIST) — two parallel tariff classification systems |
