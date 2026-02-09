# PROMEOS RegOps Ultimate Guide

**Living Compliance & Monitoring System**
Version: 1.0.0
Last Updated: 2026-02-09

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Deterministic vs AI](#deterministic-vs-ai)
3. [Plugin Architecture](#plugin-architecture)
4. [Regulations Covered](#regulations-covered)
5. [Data Lineage & Evidence](#data-lineage--evidence)
6. [Security & Scraping Policy](#security--scraping-policy)
7. [How to Extend](#how-to-extend)
8. [API Reference](#api-reference)
9. [Environment Variables](#environment-variables)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

PROMEOS RegOps is a **living compliance system** that combines:

- **Deterministic Core**: Rule engines that compute compliance status, scores, deadlines from structured regulations
- **AI Agents**: Explainers and recommenders that add context, suggestions, and insights (never modify deterministic status)
- **Connectors**: Plugin architecture for external data APIs (RTE, PVGIS, Enedis, Météo-France)
- **Watchers**: Regulatory change monitors via RSS/API (Légifrance, CRE, RTE)
- **Lifecycle Management**: JobOutbox pattern for safe async recompute cascades

### Core Principles

1. **Evidence-First**: All outputs reference inputs with source + retrieval timestamp
2. **Minimal Storage**: Regulatory scraping stores only hash + 500-char snippet (no mass copying)
3. **Auditable**: Deterministic core is source of truth, fully traceable, explainable
4. **Separation of Concerns**: AI suggestions are tagged `is_ai_suggestion=True` and stored separately
5. **Performance**: N+1 query prevention with bulk patterns (3 queries for batch evaluation)
6. **Extensibility**: Plugin architecture for connectors, watchers, agents, rules

---

## Deterministic vs AI

### The Hard Rule

**AI agents NEVER modify compliance status or score.**

| Aspect | Deterministic Core | AI Layer |
|--------|-------------------|----------|
| **Purpose** | Compute legal compliance status | Explain, suggest, analyze |
| **Source** | YAML configs + Python rule engines | LLM (Claude Sonnet 4.5) |
| **Outputs** | RegAssessment (status, score, findings) | AiInsight (explain, suggest, brief) |
| **Audit** | Fully traceable to inputs + rules | Includes sources_used, confidence, assumptions |
| **Trust** | High (rule-based, deterministic) | Medium (AI suggestions need human review) |
| **Storage** | `reg_assessment` table | `ai_insight` table |
| **Tags** | Deterministic actions | `is_ai_suggestion=True` |

### Why This Matters

- **Legal**: Compliance status must be defensible in audits (AI suggestions are not)
- **Trust**: Users need to understand why they're non-compliant (rules are explicit)
- **Safety**: AI can hallucinate; deterministic core cannot

### Example

**Deterministic Output** (from `tertiaire_operat.py`):
```json
{
  "regulation": "TERTIAIRE_OPERAT",
  "rule_id": "DEADLINE_2026_ATTESTATION",
  "status": "AT_RISK",
  "severity": "HIGH",
  "legal_deadline": "2026-07-01",
  "explanation": "Attestation d'affichage obligatoire avant 2026-07-01. Site soumis (1200 m² ≥ 1000 m²).",
  "inputs_used": ["tertiaire_area_m2=1200", "operat_status=IN_PROGRESS"]
}
```

**AI Output** (from `regops_explainer.py`):
```json
{
  "brief": "Ce site de 1200m² est soumis au Décret Tertiaire. La déclaration OPERAT est en cours mais l'attestation d'affichage doit être déployée avant juillet 2026. Recommandation : préparer le modèle d'affichage dès maintenant.",
  "sources_used": ["site_data", "reg_assessment"],
  "assumptions": ["Pas de données multi-occupation disponibles"],
  "confidence": "MEDIUM",
  "needs_human_review": true,
  "is_ai_suggestion": true
}
```

---

## Plugin Architecture

All extensible components follow the same pattern:

1. **Base Class** (ABC): Defines interface
2. **Registry**: Auto-discovers implementations via subclass enumeration
3. **Implementations**: Inherit from base, implement required methods

### Connectors

**File**: `backend/connectors/`

```
base.py         # ABC: Connector with test_connection(), sync()
registry.py     # Auto-discovery + get_connector(name)
rte_eco2mix.py  # REAL: Grid CO2 intensity (public API)
pvgis.py        # REAL: Solar production estimates (public API)
meteofrance.py  # STUB: Weather data (needs METEOFRANCE_API_KEY)
enedis_*.py     # STUB: Electricity meter data (needs OAuth)
```

**Returns**: `DataPoint` objects with lineage (source_type, source_name, quality_score, retrieved_at)

### Watchers

**File**: `backend/watchers/`

```
base.py            # ABC: Watcher with check(db)
registry.py        # Auto-discovery + list_watchers(), run_watcher()
rss_watcher.py     # Generic RSS parser (stdlib xml.etree)
legifrance_*.py    # Specific RSS feeds with tag extraction
```

**Returns**: `RegSourceEvent` objects with content_hash, snippet (max 500 chars), tags

### AI Agents

**File**: `backend/ai_layer/`

```
client.py                    # AIClient with stub mode
registry.py                  # Auto-discovery + run_agent()
agents/
  regops_explainer.py        # 2-min site compliance brief
  regops_recommender.py      # AI suggestions (tagged is_ai_suggestion=True)
  data_quality_agent.py      # Missing/anomalous data detection
  reg_change_agent.py        # RegSourceEvent impact analysis
  exec_brief_agent.py        # Org-level narrative
prompts/
  explain_site.md            # System prompts for agents
  ...
```

**Returns**: `AiInsight` objects with content_json, sources_used, needs_human_review

### Rule Engines

**File**: `backend/regops/rules/`

```
tertiaire_operat.py  # Décret Tertiaire / OPERAT
bacs.py              # GTB/GTC automation
aper.py              # Parking + roof solar
cee_p6.py            # CEE audit requirements
```

**Config**: `backend/regops/config/regs.yaml` (deadlines, thresholds, penalties)

**Returns**: List of `Finding` objects with status, severity, confidence, inputs_used, missing_inputs

---

## Regulations Covered

### 1. Tertiaire / OPERAT

**Scope**: Tertiary buildings ≥ 1000 m²
**Deadlines**:
- 2026-07-01: Attestation d'affichage
- 2026-09-30: Déclaration OPERAT 2025

**Required Inputs**:
- `site.tertiaire_area_m2` (scope check)
- `site.operat_status` (compliance tracking)
- `site.annual_kwh_total` (consumption reporting)
- `site.is_multi_occupied` (governance flag)

**Statuses**:
- OUT_OF_SCOPE: < 1000 m²
- UNKNOWN: tertiaire_area_m2 = NULL
- AT_RISK: In deadline window, data missing
- NON_COMPLIANT: Past deadline, not submitted
- COMPLIANT: Submitted & verified

**Actions Generated**:
- Collect tertiaire surface data (if missing)
- Start OPERAT declaration (if NOT_STARTED)
- Prepare attestation d'affichage (if < 90 days to deadline)
- Multi-occupied coordination (if is_multi_occupied=True)

---

### 2. BACS (Building Automation)

**Scope**: Buildings with HVAC power (Putile) > 70 kW
**Deadlines**:
- 2025-01-01: > 290 kW (CRITICAL)
- 2030-01-01: 70-290 kW (MEDIUM)

**Required Inputs**:
- `batiment.cvc_power_kw` (Putile calculation)
- Evidence: `ATTESTATION_BACS`, `INSPECTION_BACS`

**Statuses**:
- OUT_OF_SCOPE: max(cvc_power_kw) < 70 kW
- UNKNOWN: All cvc_power_kw = NULL
- NON_COMPLIANT: > 290 kW, no BACS installed, past 2025-01-01
- AT_RISK: 70-290 kW, deadline approaching 2030-01-01
- EXEMPTION_POSSIBLE: TRI > 10 years (low ROI)

**Actions Generated**:
- Install GTB/GTC (if not installed)
- Schedule BACS inspection (if no inspection evidence)
- Conduct TRI study (if exemption possible)

---

### 3. APER (Parking + Roof Solar)

**Scope**: Outdoor parking ≥ 1500 m² OR roof ≥ 500 m²
**Deadlines**:
- 2026-07-01: Parking > 10000 m² (HIGH)
- 2028-07-01: Parking 1500-10000 m² (MEDIUM)
- 2028-01-01: Roof > 500 m² (MEDIUM)

**Required Inputs**:
- `site.parking_area_m2`
- `site.parking_type` (OUTDOOR only)
- `site.roof_area_m2`

**Statuses**:
- OUT_OF_SCOPE: parking_type ≠ OUTDOOR, or areas below thresholds
- UNKNOWN: parking_area_m2 or roof_area_m2 = NULL
- AT_RISK: In deadline window
- NON_COMPLIANT: Past deadline, no solar installation

**Actions Generated**:
- Solar feasibility study (parking > 1500 m²)
- Roof solarization study (roof > 500 m²)
- PVGIS connector sync (for production estimates)

---

### 4. CEE P6 (Energy Audit)

**Scope**: All sites (audit requirements vary by size/activity)
**Period**: 4-year cycle

**Required Inputs**:
- Evidence: `AUDIT_ENERGETIQUE`, `PRE_DIAGNOSTIC`
- Site size, activity, energy consumption

**Statuses**:
- AT_RISK: Audit > 3 years old
- NON_COMPLIANT: No audit evidence
- COMPLIANT: Recent audit (< 4 years)

**Actions Generated**:
- Schedule energy audit (mapped to CEE catalog)
- Implement audit recommendations (with CEE hints)

**Catalog**: `backend/regops/config/cee_p6_catalog.yaml` (10 action codes with ROI/complexity hints)

---

## Data Lineage & Evidence

### DataPoint Table

Every external data point is tracked:

```python
DataPoint(
    object_type="site",        # site, meter, batiment
    object_id=42,              # Foreign key
    metric="grid_co2_intensity",
    ts_start=datetime(...),
    ts_end=datetime(...),
    value=85.5,
    unit="gCO2/kWh",
    source_type=SourceType.API,
    source_name="rte_eco2mix",
    quality_score=0.95,        # Confidence in data quality
    coverage_ratio=1.0,        # % of requested period covered
    retrieved_at=datetime.now(),
    source_ref="https://odre.opendatasoft.com/..."
)
```

**Lineage Benefits**:
- Traceability: Know where every number comes from
- Quality: Track data gaps, anomalies
- Freshness: Know when data was last updated
- Audit: Provide source URLs for compliance checks

### Evidence Documents

Critical compliance documents are tracked:

```python
Evidence(
    site_id=42,
    type=EvidenceType.ATTESTATION_BACS,
    title="Attestation GTB Magasin Lyon",
    url="s3://promeos/evidence/...",
    uploaded_at=datetime.now(),
    validity_end=date(2030, 12, 31)
)
```

**Rule engines check for evidence**:
- BACS: Requires `ATTESTATION_BACS` or `INSPECTION_BACS`
- CEE P6: Requires `AUDIT_ENERGETIQUE`
- Tertiaire: Requires `ATTESTATION_AFFICHAGE`

---

## Security & Scraping Policy

### Minimal Storage Principle

**Regulatory watchers** (Légifrance, CRE, RTE) only store:

1. **content_hash**: SHA-256 of title+url (deduplication)
2. **snippet**: First 500 characters of description
3. **metadata**: tags, published_at, source_name

**We do NOT store**:
- Full article text
- Images, PDFs
- User comments

**Why**:
- Legal: Avoid copyright issues
- Storage: Keep database small
- Performance: Fast queries

### Example

```python
# ✅ GOOD: Minimal storage
RegSourceEvent(
    source_name="legifrance_rss",
    title="Décret n° 2024-XXX modifiant le décret tertiaire",
    url="https://www.legifrance.gouv.fr/...",
    content_hash="a3f5b2c1...",  # SHA-256
    snippet="Le décret du 23 juillet 2019 est modifié comme suit : Article 1...",  # 500 chars max
    tags=["energie", "tertiaire"],
    published_at=date(2024, 1, 15)
)

# ❌ BAD: Full scraping (DO NOT DO)
# Storing full article text, images, etc.
```

### RSS Parsing

**Library**: stdlib `xml.etree.ElementTree` (no feedparser dependency)

**Safety**:
- Limit to 10 most recent items per feed
- Hash-based deduplication (no re-processing)
- Error handling for malformed XML
- User-Agent header: "PROMEOS Regulatory Watcher v1.0"

---

## How to Extend

### Add a New Connector

1. Create `backend/connectors/my_connector.py`:

```python
from .base import Connector
from models import DataPoint, SourceType

class MyConnector(Connector):
    name = "my_connector"
    description = "Fetches data from MyAPI"
    requires_auth = True

    def test_connection(self) -> dict:
        # Test API credentials
        return {"status": "ok", "message": "Connected"}

    def sync(self, db, object_type, object_id, **kwargs) -> list[DataPoint]:
        # Fetch data, create DataPoints
        datapoints = []
        # ... your logic ...
        return datapoints
```

2. Connector is auto-discovered by registry (no registration needed)

3. Test: `GET /api/connectors/list` → should see `my_connector`

4. Sync: `POST /api/connectors/my_connector/sync?object_type=site&object_id=1`

---

### Add a New Watcher

1. Create `backend/watchers/my_watcher.py`:

```python
from .base import Watcher
from .rss_watcher import RSSWatcher

class MyWatcher(RSSWatcher):
    name = "my_watcher"
    description = "Watches MyRegulatorySource"
    rss_url = "https://example.com/rss"

    def extract_tags(self, item) -> list[str]:
        # Custom tag extraction
        return ["energie", "custom_tag"]
```

2. Auto-discovered by registry

3. Test: `POST /api/watchers/my_watcher/run` → creates RegSourceEvents

4. Review: `GET /api/watchers/events?source=my_watcher`

---

### Add a New Rule Engine

1. Create `backend/regops/rules/my_regulation.py`:

```python
from ..schemas import Finding
from models import RegStatus, Severity, Confidence

def evaluate(site, batiments, evidences, config) -> list[Finding]:
    findings = []

    # Your rule logic
    if condition:
        findings.append(Finding(
            regulation="MY_REGULATION",
            rule_id="MY_RULE_001",
            status=RegStatus.AT_RISK,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            legal_deadline=date(2027, 1, 1),
            trigger_condition="Site meets threshold",
            config_params={"threshold": 1000},
            inputs_used=["site.my_field=123"],
            missing_inputs=[],
            explanation="Votre explication ici"
        ))

    return findings
```

2. Add config to `backend/regops/config/regs.yaml`:

```yaml
my_regulation:
  threshold: 1000
  deadline: "2027-01-01"
  required_inputs:
    - my_field
```

3. Register in `backend/regops/engine.py`:

```python
from .rules import tertiaire_operat, bacs, aper, cee_p6, my_regulation

def evaluate_site(db, site_id) -> SiteSummary:
    # ...
    all_findings.extend(my_regulation.evaluate(site, batiments, evidences, configs["my_regulation"]))
```

4. Test: `GET /api/regops/site/1` → should include findings from `MY_REGULATION`

---

### Add a New AI Agent

1. Create `backend/ai_layer/agents/my_agent.py`:

```python
from ..client import get_client
from models import AiInsight, InsightType
import json

def run(db, site_id, **kwargs):
    client = get_client()

    # Load context
    site = db.query(Site).filter(Site.id == site_id).first()

    # Prepare prompts
    system_prompt = "You are an energy compliance assistant..."
    user_prompt = f"Analyze site {site.nom}..."

    # Call AI
    response = client.complete(system_prompt, user_prompt)

    # Save insight
    insight = AiInsight(
        object_type="site",
        object_id=site_id,
        insight_type=InsightType.SUGGEST,  # or EXPLAIN, DATA_QUALITY, etc.
        content_json=json.dumps({
            "analysis": response,
            "sources_used": ["site_data"],
            "assumptions": ["Assumed X"],
            "confidence": "MEDIUM",
            "needs_human_review": True
        }),
        ai_version="claude-sonnet-4-5-20250929"
    )
    db.add(insight)
    db.commit()

    return insight
```

2. Auto-discovered by registry

3. Test: `GET /api/ai/insights` → should see insights from your agent

---

## API Reference

### RegOps Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/regops/site/{id}` | Full assessment (fresh compute) |
| GET | `/api/regops/site/{id}/cached` | Cached RegAssessment |
| POST | `/api/regops/recompute` | Trigger recompute (scope: site, entity, org, all) |
| GET | `/api/regops/dashboard` | Org-level KPIs |

**Example**:
```bash
curl http://localhost:8000/api/regops/site/1
```

**Response**:
```json
{
  "site_id": 1,
  "global_status": "AT_RISK",
  "compliance_score": 72.5,
  "next_deadline": "2026-07-01",
  "findings": [
    {
      "regulation": "TERTIAIRE_OPERAT",
      "rule_id": "DEADLINE_2026_ATTESTATION",
      "status": "AT_RISK",
      "severity": "HIGH",
      "explanation": "Attestation obligatoire avant 2026-07-01"
    }
  ],
  "actions": [
    {
      "action_code": "COLLECT_TERTIAIRE_AREA",
      "label": "Collecter surface tertiaire déclarée",
      "priority_score": 85,
      "is_ai_suggestion": false
    }
  ],
  "missing_data": ["tertiaire_area_m2"]
}
```

---

### Connectors Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/connectors/list` | List all connectors |
| POST | `/api/connectors/{name}/test` | Test connection |
| POST | `/api/connectors/{name}/sync` | Sync data |

**Example**:
```bash
curl -X POST "http://localhost:8000/api/connectors/rte_eco2mix/sync?object_type=site&object_id=1"
```

**Response**:
```json
{
  "connector": "rte_eco2mix",
  "object_type": "site",
  "object_id": 1,
  "datapoints_created": 12
}
```

---

### Watchers Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchers/list` | List all watchers |
| POST | `/api/watchers/{name}/run` | Run watcher |
| GET | `/api/watchers/events` | List events (filter: source, reviewed) |
| PATCH | `/api/watchers/events/{id}/review` | Mark reviewed |

**Example**:
```bash
curl -X POST "http://localhost:8000/api/watchers/legifrance_watcher/run"
```

**Response**:
```json
{
  "watcher": "legifrance_watcher",
  "new_events": 3
}
```

---

### AI Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ai/site/{id}/explain` | 2-min compliance brief |
| GET | `/api/ai/site/{id}/recommend` | AI suggestions |
| GET | `/api/ai/site/{id}/data-quality` | Data quality check |
| GET | `/api/ai/org/brief` | Exec brief (org_id param) |
| GET | `/api/ai/insights` | List all insights |

**Example**:
```bash
curl http://localhost:8000/api/ai/site/1/explain
```

**Response** (stub mode):
```json
{
  "site_id": 1,
  "brief": "[AI Stub Mode] Analyse non disponible. Configurez AI_API_KEY...",
  "sources_used": [],
  "needs_human_review": true
}
```

---

## Environment Variables

See `.env.example` for full reference.

**Required**:
- None (all connectors/agents degrade gracefully)

**Optional**:
- `AI_API_KEY`: Anthropic API key for AI agents (stub mode if not set)
- `AI_MODEL`: Model to use (default: claude-sonnet-4-5-20250929)
- `METEOFRANCE_API_KEY`: Météo-France API access
- `ENEDIS_CLIENT_ID`, `ENEDIS_CLIENT_SECRET`: Enedis DataConnect OAuth

---

## Troubleshooting

### Issue: AI agents return stub responses

**Cause**: `AI_API_KEY` not set in `.env`

**Fix**:
```bash
echo "AI_API_KEY=sk-ant-..." >> .env
```

---

### Issue: Connector sync fails with "Connection error"

**Cause**: Missing API credentials or network issue

**Debug**:
```bash
curl -X POST "http://localhost:8000/api/connectors/my_connector/test"
```

**Fix**: Check `.env` for required keys, verify network access

---

### Issue: RegAssessment is stale

**Cause**: Data version changed (new meter data, site update)

**Fix**: Trigger recompute
```bash
curl -X POST "http://localhost:8000/api/regops/recompute?scope=site&site_id=1"
```

**Auto-fix**: JobOutbox worker runs periodically to recompute stale assessments

---

### Issue: Watcher returns no events

**Cause**: All events already processed (hash deduplication)

**Debug**: Check `reg_source_event` table for existing hashes

**Normal**: Watchers only return new events (not re-processed)

---

### Issue: Compliance score seems wrong

**Debug**:
1. Check findings: `GET /api/regops/site/{id}`
2. Review YAML config: `backend/regops/config/regs.yaml`
3. Check inputs_used vs missing_inputs in findings
4. Verify severity/urgency/confidence weights

**Formula**:
```python
compliance_score = 100 - (
    sum(severity_weight * urgency_weight * confidence_weight for f in findings)
    / total_possible_weight * 100
)
```

---

### Issue: N+1 queries detected

**Check**: `evaluate_batch()` should use 3 bulk queries (sites, batiments, evidences)

**Anti-pattern**:
```python
for site in sites:
    batiments = db.query(Batiment).filter(Batiment.site_id == site.id).all()  # ❌ N+1
```

**Correct pattern**:
```python
batiments = db.query(Batiment).filter(Batiment.site_id.in_(site_ids)).all()
batiments_by_site = defaultdict(list)
for b in batiments:
    batiments_by_site[b.site_id].append(b)
```

---

## Support

**GitHub**: https://github.com/your-org/promeos
**Docs**: https://promeos.example.com/docs
**Contact**: support@promeos.example.com

---

**Built with ❤️ for energy compliance professionals**
