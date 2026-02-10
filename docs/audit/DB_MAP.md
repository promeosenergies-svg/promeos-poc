# DATABASE MAP - PROMEOS POC
**Date**: 2026-02-09
**Engine**: SQLite (⚠️ dev only, not production-ready)
**Total Tables**: 18

---

## SCHEMA OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORGANISATION                                 │
│  id, nom, type_client, siren                                        │
└───────────────┬─────────────────────────────────────────────────────┘
                │
                ├─→ entites_juridiques (1:N)
                │    ├─→ portefeuilles (1:N)
                │    │    └─→ sites (1:N) ← CORE
                │    │         ├─→ batiments (1:N)
                │    │         ├─→ compteurs (1:N)
                │    │         │    └─→ consommations (1:N)
                │    │         ├─→ usages (1:N)
                │    │         ├─→ obligations (1:N)
                │    │         ├─→ evidences (1:N)
                │    │         ├─→ alertes (1:N)
                │    │         ├─→ datapoints (1:N) ← NEW
                │    │         └─→ reg_assessments (1:1 cached) ← NEW
                │
                ├─→ ai_insights (1:N, object_type=org/site) ← NEW
                └─→ job_outbox (1:N, async jobs) ← NEW

┌─────────────────────────────────────────────────────────────────────┐
│                    REGULATORY MONITORING                             │
│  reg_source_events (independent, RSS feeds) ← NEW                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TABLE DETAILS

### 1. ORGANISATION (Hierarchy Root)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| nom | String(200) | ❌ | ✅ | Organisation name |
| type_client | String(50) | ✅ | ❌ | Client type (retail, industry, etc.) |
| siren | String(9) | ✅ | ❌ | SIREN number (French business ID) |
| actif | Boolean | ❌ | ❌ | Active flag |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `entites_juridiques` (1:N)

**File**: `backend/models/organisation.py`

---

### 2. ENTITE_JURIDIQUE (Legal Entity)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| organisation_id | Integer | ❌ | FK | → organisations.id |
| nom | String(200) | ❌ | ✅ | Legal entity name |
| naf_code | String(5) | ✅ | ❌ | NAF activity code |
| region_code | String(3) | ✅ | ❌ | French region code |
| insee_code | String(5) | ✅ | ❌ | INSEE commune code |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `organisation` (N:1)
- `portefeuilles` (1:N)

**File**: `backend/models/entite_juridique.py`

---

### 3. PORTEFEUILLE (Portfolio)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| entite_juridique_id | Integer | ❌ | FK | → entites_juridiques.id |
| nom | String(200) | ❌ | ✅ | Portfolio name |
| description | Text | ✅ | ❌ | Portfolio description |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `entite_juridique` (N:1)
- `sites` (1:N)

**File**: `backend/models/portefeuille.py`

---

### 4. SITE ⭐ (Core Table)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| portefeuille_id | Integer | ✅ | FK | → portefeuilles.id |
| nom | String(200) | ❌ | ✅ | Site name |
| type | Enum(TypeSite) | ❌ | ❌ | BUREAU, MAGASIN, USINE, etc. |
| adresse | String(300) | ✅ | ❌ | Postal address |
| code_postal | String(10) | ✅ | ✅ | Postal code |
| ville | String(100) | ✅ | ✅ | City |
| region | String(100) | ✅ | ❌ | Region |
| surface_m2 | Float | ✅ | ❌ | Total surface (m²) |
| nombre_employes | Integer | ✅ | ❌ | Number of employees |
| latitude | Float | ✅ | ❌ | GPS latitude |
| longitude | Float | ✅ | ❌ | GPS longitude |
| actif | Boolean | ❌ | ❌ | Active flag |
| **statut_decret_tertiaire** | Enum | ❌ | ❌ | Legacy compliance status |
| **avancement_decret_pct** | Float | ❌ | ❌ | Legacy % progress (0-100) |
| **statut_bacs** | Enum | ❌ | ❌ | Legacy BACS status |
| anomalie_facture | Boolean | ❌ | ❌ | Bill anomaly flag |
| action_recommandee | String | ✅ | ❌ | Recommended action |
| risque_financier_euro | Float | ❌ | ❌ | Financial risk (€) |
| **siret** ⭐ | String(14) | ✅ | ❌ | SIRET (NEW RegOps) |
| **insee_code** ⭐ | String(5) | ✅ | ❌ | INSEE code (NEW RegOps) |
| **naf_code** ⭐ | String(5) | ✅ | ❌ | NAF code override (NEW RegOps) |
| **tertiaire_area_m2** ⭐ | Float | ✅ | ❌ | Tertiary surface (m²) (NEW RegOps) |
| **roof_area_m2** ⭐ | Float | ✅ | ❌ | Roof surface (m²) (NEW RegOps) |
| **parking_area_m2** ⭐ | Float | ✅ | ❌ | Parking surface (m²) (NEW RegOps) |
| **parking_type** ⭐ | Enum | ✅ | ❌ | OUTDOOR/INDOOR/UNDERGROUND (NEW RegOps) |
| **is_multi_occupied** ⭐ | Boolean | ❌ | ❌ | Multi-tenant flag (NEW RegOps) |
| **operat_status** ⭐ | Enum | ✅ | ❌ | OPERAT declaration status (NEW RegOps) |
| **operat_last_submission_year** ⭐ | Integer | ✅ | ❌ | Last OPERAT year (NEW RegOps) |
| **annual_kwh_total** ⭐ | Float | ✅ | ❌ | Annual consumption (kWh) (NEW RegOps) |
| **last_energy_update_at** ⭐ | DateTime | ✅ | ❌ | Last energy data update (NEW RegOps) |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `portefeuille` (N:1)
- `batiments` (1:N)
- `compteurs` (1:N)
- `usages` (1:N)
- `obligations` (1:N)
- `evidences` (1:N)
- `alertes` (1:N)

**Critical Indexes Missing**:
```sql
CREATE INDEX idx_site_portefeuille ON sites(portefeuille_id);
CREATE INDEX idx_site_tertiaire_area ON sites(tertiaire_area_m2);
CREATE INDEX idx_site_parking_area ON sites(parking_area_m2);
```

**File**: `backend/models/site.py` (82 lines)

---

### 5. BATIMENT (Building)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| nom | String(200) | ❌ | ❌ | Building name |
| surface_m2 | Float | ✅ | ❌ | Surface (m²) |
| annee_construction | Integer | ✅ | ❌ | Construction year |
| cvc_power_kw | Float | ✅ | ❌ | HVAC power (kW) ⭐ CRITICAL for BACS |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)

**File**: `backend/models/batiment.py`

---

### 6. COMPTEUR (Meter)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| nom | String(100) | ❌ | ✅ | Meter name |
| type | Enum | ❌ | ❌ | ELECTRIQUE, GAZ, EAU, CHALEUR |
| numero | String(50) | ✅ | ✅ | Meter number |
| actif | Boolean | ❌ | ❌ | Active flag |
| **meter_id** ⭐ | String(14) | ✅ | ❌ | External meter ID (Enedis PRM) (NEW) |
| **energy_vector** ⭐ | Enum | ✅ | ❌ | ELECTRICITY/GAS/HEAT/OTHER (NEW) |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)
- `consommations` (1:N)

**File**: `backend/models/compteur.py`

---

### 7. CONSOMMATION (Consumption)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| compteur_id | Integer | ❌ | FK+IDX | → compteurs.id |
| date | Date | ❌ | ✅ | Consumption date |
| valeur | Float | ❌ | ❌ | Value (kWh, m³, etc.) |
| unite | String(20) | ❌ | ❌ | Unit (kWh, m3, MWh) |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Critical Index**:
```sql
CREATE UNIQUE INDEX idx_conso_compteur_date ON consommations(compteur_id, date);
```

**File**: `backend/models/consommation.py`

---

### 8. USAGE (Usage Type)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| type | Enum | ❌ | ❌ | CHAUFFAGE, CLIM, ECLAIRAGE, etc. |
| surface_concernee_m2 | Float | ✅ | ❌ | Affected surface |
| description | Text | ✅ | ❌ | Description |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)

**File**: `backend/models/usage.py`

---

### 9. OBLIGATION (Compliance Obligation)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| type | Enum | ❌ | ❌ | DECRET_TERTIAIRE, BACS, etc. |
| description | Text | ❌ | ❌ | Obligation description |
| echeance | Date | ✅ | ✅ | Deadline |
| statut | Enum | ❌ | ❌ | CONFORME, A_RISQUE, NON_CONFORME |
| priorite | Integer | ❌ | ❌ | Priority (1-5) |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)

**File**: `backend/models/conformite.py`

---

### 10. EVIDENCE (Compliance Evidence)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| type | Enum | ❌ | ❌ | AUDIT, FACTURE, RAPPORT, CERTIFICAT, etc. |
| statut | Enum | ❌ | ❌ | EN_ATTENTE, VALIDE, REJETE |
| date_document | Date | ✅ | ❌ | Document date |
| fichier_url | String(500) | ✅ | ❌ | File URL/path |
| note | Text | ✅ | ❌ | Notes |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)

**⚠️ Issue**: TypeEvidence enum missing `AUDIT_ENERGETIQUE` (test_regops_rules.py:260 fails)

**File**: `backend/models/evidence.py`

---

### 11. ALERTE (Alert)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| site_id | Integer | ❌ | FK | → sites.id |
| type | String(50) | ❌ | ❌ | Alert type |
| severite | Enum | ❌ | ❌ | BASSE, MOYENNE, HAUTE, CRITIQUE |
| message | Text | ❌ | ❌ | Alert message |
| date_debut | DateTime | ❌ | ❌ | Start date |
| date_fin | DateTime | ✅ | ❌ | End date (if resolved) |
| statut_actif | Boolean | ❌ | ✅ | Active flag |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- `site` (N:1)

**File**: `backend/models/alerte.py`

---

### 12. DATAPOINT ⭐ (NEW - External Data Lineage)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| object_type | String(20) | ❌ | ✅ | "site", "org", "entity" |
| object_id | Integer | ❌ | ✅ | FK to object |
| metric | String(100) | ❌ | ✅ | "grid_co2_intensity", "pv_prod_estimate_kwh", etc. |
| ts_start | DateTime | ❌ | ✅ | Period start |
| ts_end | DateTime | ✅ | ❌ | Period end (NULL=instant) |
| value | Float | ❌ | ❌ | Metric value |
| unit | String(20) | ❌ | ❌ | Unit (gCO2/kWh, kWh/year, °C) |
| source_type | Enum | ❌ | ❌ | MANUAL, IMPORT, API, SCRAPE |
| source_name | String(100) | ❌ | ❌ | "rte_eco2mix", "pvgis", "meteofrance" |
| quality_score | Float | ✅ | ❌ | Quality score (0-1) |
| coverage_ratio | Float | ✅ | ❌ | Coverage ratio (0-1) |
| retrieved_at | DateTime | ❌ | ❌ | Fetch timestamp |
| source_ref | String(500) | ✅ | ❌ | External API reference |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- Polymorphic to Site/Organisation/Entity via (object_type, object_id)

**Use Cases**:
- RTE eCO2mix: metric="grid_co2_intensity", source_name="rte_eco2mix"
- PVGIS: metric="pv_prod_estimate_kwh", source_name="pvgis"
- Enedis: metric="meter_kwh_consumed", source_name="enedis_dataconnect"
- Météo-France: metric="temperature_c", source_name="meteofrance"

**Critical Index**:
```sql
CREATE INDEX idx_datapoint_lookup ON datapoints(object_type, object_id, metric, ts_start);
```

**File**: `backend/models/datapoint.py`

---

### 13. REG_ASSESSMENT ⭐ (NEW - Cached RegOps Evaluations)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| object_type | String(20) | ❌ | ✅ | "site", "entity", "org" |
| object_id | Integer | ❌ | ✅ | FK to object |
| computed_at | DateTime | ❌ | ❌ | Evaluation timestamp |
| global_status | Enum(RegStatus) | ❌ | ❌ | COMPLIANT, AT_RISK, NON_COMPLIANT, UNKNOWN |
| compliance_score | Float | ❌ | ❌ | Score 0-100 |
| next_deadline | Date | ✅ | ❌ | Next regulatory deadline |
| findings_json | Text | ✅ | ❌ | JSON array of Finding objects |
| top_actions_json | Text | ✅ | ❌ | JSON array of Action objects |
| missing_data_json | Text | ✅ | ❌ | JSON array of missing fields |
| deterministic_version | String(64) | ❌ | ❌ | Hash of YAML+rules |
| ai_version | String(64) | ✅ | ❌ | AI model version |
| data_version | String(64) | ❌ | ❌ | Hash of input data |
| is_stale | Boolean | ❌ | ❌ | Cache invalidation flag |
| stale_reason | String(200) | ✅ | ❌ | Why stale (data changed, rules changed) |

**Relations**:
- Polymorphic to Site/Entity/Organisation via (object_type, object_id)

**Cache Invalidation Logic**:
```python
# Recompute if:
deterministic_version != current_rules_hash OR
data_version != current_data_hash OR
is_stale == True
```

**Critical Index**:
```sql
CREATE UNIQUE INDEX idx_reg_assessment_object ON reg_assessments(object_type, object_id);
```

**File**: `backend/models/reg_assessment.py`

---

### 14. JOB_OUTBOX ⭐ (NEW - Async Job Queue)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| job_type | Enum(JobType) | ❌ | ✅ | RECOMPUTE_ASSESSMENT, SYNC_CONNECTOR, RUN_WATCHER, RUN_AI_AGENT |
| payload_json | Text | ❌ | ❌ | Job parameters (JSON) |
| priority | Integer | ❌ | ❌ | Priority (1-10, higher=more urgent) |
| status | Enum(JobStatus) | ❌ | ✅ | PENDING, RUNNING, DONE, FAILED |
| created_at | DateTime | ❌ | ✅ | Job creation timestamp |
| started_at | DateTime | ✅ | ❌ | Job start timestamp |
| finished_at | DateTime | ✅ | ❌ | Job finish timestamp |
| error | Text | ✅ | ❌ | Error message if FAILED |

**Use Cases**:
- Cascade recompute: meter update → enqueue site job → enqueue entity job → enqueue org job
- Scheduled connector sync: Daily Enedis data fetch
- Scheduled watcher run: Hourly RSS check
- AI agent batch: Nightly portfolio brief generation

**Critical Index**:
```sql
CREATE INDEX idx_job_status_priority ON job_outbox(status, priority DESC, created_at);
```

**Worker Pattern** (jobs/worker.py):
```python
# Fetch next job
job = db.query(JobOutbox).filter(
    JobOutbox.status == JobStatus.PENDING
).order_by(
    JobOutbox.priority.desc(),
    JobOutbox.created_at
).first()

# Process
job.status = JobStatus.RUNNING
# ... do work ...
job.status = JobStatus.DONE
```

**File**: `backend/models/job_outbox.py`

---

### 15. AI_INSIGHT ⭐ (NEW - AI Agent Outputs)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| object_type | String(20) | ❌ | ✅ | "site", "org", "entity" |
| object_id | Integer | ❌ | ✅ | FK to object |
| insight_type | Enum(InsightType) | ❌ | ❌ | EXPLAIN, SUGGEST, CHANGE_IMPACT, EXEC_BRIEF, DATA_QUALITY |
| content_json | Text | ❌ | ❌ | AI output (JSON: brief, analysis, sources_used, needs_human_review) |
| ai_version | String(50) | ✅ | ❌ | AI model version (e.g., "claude-sonnet-4-5") |
| sources_used_json | Text | ✅ | ❌ | JSON array of sources (DataPoints, RegSourceEvents, etc.) |
| created_at | DateTime | ❌ | ❌ | Timestamp |
| updated_at | DateTime | ❌ | ❌ | Timestamp |

**Relations**:
- Polymorphic to Site/Organisation/Entity via (object_type, object_id)

**HARD RULE**: AI agents **NEVER** modify deterministic status/score. They only create insights.

**Use Cases**:
- EXPLAIN: 2-min site compliance brief for non-technical users
- SUGGEST: AI action recommendations (tagged with is_ai_suggestion=True)
- DATA_QUALITY: Missing critical data + anomaly detection
- CHANGE_IMPACT: Impact analysis of new RegSourceEvent
- EXEC_BRIEF: Portfolio narrative for executives

**Critical Index**:
```sql
CREATE INDEX idx_ai_insight_lookup ON ai_insights(object_type, object_id, insight_type);
```

**File**: `backend/models/ai_insight.py`

---

### 16. REG_SOURCE_EVENT ⭐ (NEW - Regulatory News)

| Column | Type | Nullable | Index | Description |
|--------|------|----------|-------|-------------|
| id | Integer | ❌ | PK | Auto-increment |
| source_name | String(50) | ❌ | ✅ | "legifrance_watcher", "cre_watcher", "rte_watcher" |
| title | String(500) | ❌ | ❌ | News title |
| url | String(1000) | ❌ | ❌ | News URL |
| content_hash | String(64) | ❌ | 🔑 UNIQUE | SHA256 hash for deduplication |
| snippet | String(500) | ✅ | ❌ | First 500 chars of content |
| tags | String(200) | ✅ | ❌ | Comma-separated tags |
| published_at | DateTime | ✅ | ✅ | Publication date (from RSS) |
| retrieved_at | DateTime | ❌ | ❌ | Fetch timestamp |
| reviewed | Boolean | ❌ | ✅ | Human review flag |
| review_note | Text | ✅ | ❌ | Review notes |
| created_at | DateTime | ❌ | ❌ | Timestamp |

**Hash Deduplication**:
```python
content_hash = hashlib.sha256(f"{title}|{url}".encode()).hexdigest()
# UNIQUE constraint prevents duplicate events
```

**Use Cases**:
- Legifrance RSS: New decrees, ministerial orders
- CRE RSS: Energy regulator decisions
- RTE RSS: Grid operator technical requirements

**Critical Index**:
```sql
CREATE UNIQUE INDEX idx_reg_event_hash ON reg_source_events(content_hash);
CREATE INDEX idx_reg_event_source_date ON reg_source_events(source_name, published_at DESC);
```

**File**: `backend/models/reg_source_event.py`

---

## ENUMS

### TypeSite
`BUREAU, MAGASIN, USINE, ENTREPOT, DATACENTER, HOPITAL, HOTEL, AUTRE`

### ParkingType ⭐ NEW
`OUTDOOR, INDOOR, UNDERGROUND, SILO, UNKNOWN`

### OperatStatus ⭐ NEW
`NOT_STARTED, IN_PROGRESS, SUBMITTED, VERIFIED, UNKNOWN`

### EnergyVector ⭐ NEW
`ELECTRICITY, GAS, HEAT, OTHER`

### SourceType ⭐ NEW
`MANUAL, IMPORT, API, SCRAPE`

### JobType ⭐ NEW
`RECOMPUTE_ASSESSMENT, SYNC_CONNECTOR, RUN_WATCHER, RUN_AI_AGENT`

### JobStatus ⭐ NEW
`PENDING, RUNNING, DONE, FAILED`

### RegStatus ⭐ NEW
`COMPLIANT, AT_RISK, NON_COMPLIANT, UNKNOWN, OUT_OF_SCOPE, EXEMPTION_POSSIBLE`

### Severity ⭐ NEW
`LOW, MEDIUM, HIGH, CRITICAL`

### Confidence ⭐ NEW
`HIGH, MEDIUM, LOW`

### InsightType ⭐ NEW
`EXPLAIN, SUGGEST, CHANGE_IMPACT, EXEC_BRIEF, DATA_QUALITY`

### RegulationType ⭐ NEW
`TERTIAIRE_OPERAT, BACS, APER, CEE_P6`

**File**: `backend/models/enums.py`

---

## CRITICAL MISSING INDEXES

### High Priority (N+1 Query Risk)

```sql
-- Site lookups by portefeuille (most common query)
CREATE INDEX idx_site_portefeuille ON sites(portefeuille_id);

-- Site lookups by RegOps thresholds
CREATE INDEX idx_site_tertiaire_area ON sites(tertiaire_area_m2)
  WHERE tertiaire_area_m2 IS NOT NULL;
CREATE INDEX idx_site_parking_area ON sites(parking_area_m2)
  WHERE parking_area_m2 IS NOT NULL;

-- Batiment aggregations (BACS rule - max CVC power)
CREATE INDEX idx_batiment_site ON batiments(site_id);

-- Consommation time-series queries
CREATE INDEX idx_consommation_date_range ON consommations(compteur_id, date);

-- DataPoint metric lookups
CREATE INDEX idx_datapoint_metric_lookup ON datapoints(
  object_type, object_id, metric, ts_start
);

-- RegAssessment cache lookup
CREATE UNIQUE INDEX idx_reg_assessment_object ON reg_assessments(
  object_type, object_id
);

-- JobOutbox worker queries
CREATE INDEX idx_job_worker_queue ON job_outbox(
  status, priority DESC, created_at
) WHERE status = 'PENDING';

-- AI insights lookup
CREATE INDEX idx_ai_insight_object ON ai_insights(
  object_type, object_id, insight_type
);

-- RegSourceEvent deduplication
CREATE UNIQUE INDEX idx_reg_event_hash ON reg_source_events(content_hash);

-- RegSourceEvent feed queries
CREATE INDEX idx_reg_event_source_reviewed ON reg_source_events(
  source_name, reviewed, published_at DESC
);
```

**Effort**: 15 minutes to add all indexes (via Alembic migration)

---

## FOREIGN KEY INTEGRITY

### Current State: ⚠️ **WEAK**

SQLite by default does NOT enforce foreign keys. The application relies on ORM cascade deletes.

**Recommendation**: Enable FK constraints:
```python
# In db init (main.py or seed_data.py)
from sqlalchemy import event, Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### CASCADE DELETE Behavior

| Parent | Child | Cascade | Risk |
|--------|-------|---------|------|
| Organisation | EntiteJuridique | ✅ | OK |
| EntiteJuridique | Portefeuille | ✅ | OK |
| Portefeuille | Site | ❌ | Orphan sites if portfolio deleted |
| Site | Batiment | ✅ | OK |
| Site | Compteur | ✅ | OK |
| Compteur | Consommation | ✅ | OK (many rows) |
| Site | RegAssessment | ❌ | Orphan assessments |
| Site | AiInsight | ❌ | Orphan insights |

**Recommendation**: Add ON DELETE CASCADE or implement soft deletes (actif=False).

---

## SQLITE LIMITATIONS (Production Blockers)

### 1. Concurrency

SQLite supports **1 writer at a time**. Concurrent writes = SQLITE_BUSY errors.

**Impact**:
- JobOutbox worker + API writes = conflicts
- Multiple connector syncs = locked DB

**Fix**: Migrate to PostgreSQL.

### 2. No Row-Level Locking

Entire table locks on write = slow for high-traffic tables (consommations, datapoints).

**Fix**: PostgreSQL with row-level locks.

### 3. Limited ALTER TABLE

Cannot drop columns, rename columns with FK constraints, etc.

**Impact**: Schema migrations painful (requires recreate table + data copy).

**Fix**: PostgreSQL + Alembic.

### 4. No Connection Pooling

Each request = new connection overhead.

**Fix**: PostgreSQL + connection pool (pgbouncer).

### 5. File-Based = Backup Issues

- No point-in-time recovery
- Backup requires locking entire DB
- No replication

**Fix**: PostgreSQL with WAL backups + replicas.

---

## SCHEMA MIGRATION STRATEGY

### Current: ❌ **NONE** (Drop/Recreate)

seed_data.py does:
```python
Base.metadata.drop_all(bind=engine)  # ⚠️ DESTROYS ALL DATA
Base.metadata.create_all(bind=engine)
```

**Risk**: Cannot run in production without data loss.

### Recommended: ✅ **Alembic**

1. **Initialize**:
   ```bash
   cd backend
   alembic init migrations
   ```

2. **Auto-generate migration**:
   ```bash
   alembic revision --autogenerate -m "Add RegOps fields"
   ```

3. **Apply**:
   ```bash
   alembic upgrade head
   ```

4. **Rollback**:
   ```bash
   alembic downgrade -1
   ```

**Effort**: 30 minutes setup + 5 min per migration

---

## DATA VOLUME ESTIMATES (120 Sites, 1 Year)

| Table | Rows | Size | Growth Rate |
|-------|------|------|-------------|
| Organisation | 1 | 1 KB | Static |
| EntiteJuridique | 5 | 5 KB | Slow |
| Portefeuille | 10 | 10 KB | Slow |
| **Site** | 120 | 50 KB | Slow |
| Batiment | 250 | 30 KB | Slow |
| Compteur | 500 | 40 KB | Slow |
| **Consommation** | 182,500 (500 meters × 365 days) | 15 MB | **1.5 MB/month** |
| Usage | 300 | 50 KB | Static |
| Obligation | 600 | 100 KB | Slow |
| Evidence | 1,200 | 200 KB | Medium |
| Alerte | 500 | 80 KB | Medium |
| **DataPoint** | 50,000 (hourly external data) | 5 MB | **500 KB/month** |
| RegAssessment | 120 (1 per site cached) | 500 KB | Recomputed |
| JobOutbox | 10,000 (90 days retention) | 2 MB | **200 KB/week** |
| AiInsight | 1,000 | 2 MB | **100 KB/week** |
| RegSourceEvent | 500 (1 year RSS) | 500 KB | **20 KB/week** |

**Total Year 1**: ~25 MB (SQLite file size)

**PostgreSQL Estimate**: ~100 MB (with indexes + overhead)

---

## PERFORMANCE QUERIES

### Slowest Expected Queries (with 120 sites)

1. **Compliance Dashboard** (aggregation across org):
   ```sql
   SELECT
     s.id, s.nom,
     ra.compliance_score, ra.global_status
   FROM sites s
   LEFT JOIN reg_assessments ra ON (ra.object_type='site' AND ra.object_id=s.id)
   WHERE s.portefeuille_id IN (
     SELECT id FROM portefeuilles WHERE entite_juridique_id IN (
       SELECT id FROM entites_juridiques WHERE organisation_id = ?
     )
   )
   ```
   **Expected Time**: 50ms (SQLite), 10ms (PostgreSQL with indexes)

2. **RegOps Batch Evaluation** (120 sites):
   ```python
   # Current implementation (regops/engine.py:evaluate_batch)
   sites = db.query(Site).filter(...).all()  # 1 query
   batiments = db.query(Batiment).filter(site_id.in_(...)).all()  # 1 query
   evidences = db.query(Evidence).filter(site_id.in_(...)).all()  # 1 query
   # Process in memory - NO N+1
   ```
   **Expected Time**: 2s (4 rules × 120 sites + 3 bulk queries)

3. **Connector Sync** (RTE eCO2mix, 120 sites, monthly data):
   ```python
   # Bulk insert 120 DataPoints
   db.bulk_insert_mappings(DataPoint, datapoints)
   ```
   **Expected Time**: 100ms

---

## NEXT STEPS

1. **Immediate**:
   - Add critical indexes (15 min)
   - Enable SQLite foreign key constraints (2 min)
   - Fix TypeEvidence enum (add AUDIT_ENERGETIQUE) (5 min)

2. **Short Term**:
   - Setup Alembic migrations (30 min)
   - Add soft delete pattern (actif=False instead of DELETE) (1 hour)
   - Document cascade delete behavior (30 min)

3. **Medium Term**:
   - Migrate to PostgreSQL (4 hours)
   - Add row-level audit trail (created_by, updated_by) (2 hours)
   - Add connection pooling (30 min)

4. **Long Term**:
   - Add TimescaleDB extension for consommations time-series (2 hours)
   - Add PostGIS extension for geospatial queries (lat/lon) (1 hour)
   - Setup read replicas for analytics (4 hours)

---

**Status**: 🟡 **AMBER** - Schema complete, missing indexes + prod DB
**Blocker**: SQLite not production-ready (concurrency, backups, migrations)
**Priority**: Add indexes + Alembic before integration
