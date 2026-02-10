# API MAP - PROMEOS POC
**Date**: 2026-02-09
**Total Endpoints**: 37

---

## OVERVIEW

| Category | Count | Auth | File |
|----------|-------|------|------|
| **Compliance (Legacy)** | 8 | ❌ None | routes/compliance.py |
| **Sites** | 6 | ❌ None | routes/sites.py |
| **RegOps (NEW)** | 4 | ❌ None | routes/regops.py |
| **Connectors (NEW)** | 3 | ❌ None | routes/connectors_route.py |
| **Watchers (NEW)** | 4 | ❌ None | routes/watchers_route.py |
| **AI Agents (NEW)** | 5 | ❌ None | routes/ai_route.py |
| **Cockpit** | 3 | ❌ None | routes/cockpit.py |
| **Demo** | 2 | ❌ None | routes/demo.py |
| **Guidance** | 2 | ❌ None | routes/guidance.py |

**Security Status**: 🔴 **CRITICAL** - NO authentication on ANY endpoint

---

## DETAILED ROUTE MAP

### 1. COMPLIANCE (Legacy Engine) - 8 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/compliance/site/{id}/assessment | Full compliance assessment | ❌ | PUBLIC | - | ComplianceAssessment | Site, Batiment, Obligation, Usage, Evidence, Consommation | compliance.py:15 |
| GET | /api/compliance/sites | List sites with compliance status | ❌ | PUBLIC | - | List[SiteComplianceSummary] | Site, Obligation | compliance.py:45 |
| POST | /api/compliance/site/{id}/validate | Validate compliance manually | ❌ | ADMIN | validation_note: str | Success | Site, Obligation | compliance.py:75 |
| GET | /api/compliance/actions | List recommended actions | ❌ | PUBLIC | site_id?: int | List[Action] | Site, Obligation | compliance.py:105 |
| POST | /api/compliance/actions/{id}/complete | Mark action as completed | ❌ | USER | completion_note?: str | Success | Action | compliance.py:130 |
| GET | /api/compliance/deadlines | Upcoming deadlines dashboard | ❌ | PUBLIC | org_id?: int | List[Deadline] | Obligation | compliance.py:155 |
| GET | /api/compliance/gaps | Compliance gaps report | ❌ | PUBLIC | site_id?: int | List[Gap] | Site, Obligation, Evidence | compliance.py:180 |
| POST | /api/compliance/evidence/upload | Upload compliance evidence | ❌ | USER | file: UploadFile, type: str, site_id: int | Evidence | Evidence | compliance.py:205 |

**Notes**:
- Legacy engine (56 tests passing)
- No RBAC - PUBLIC access to sensitive data
- Critical: /validate and /evidence/upload need auth
- DB: Heavy queries with N+1 risk (compliance_engine.py does 6+ queries per site)

---

### 2. SITES - 6 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/sites | List all sites | ❌ | PUBLIC | org_id?: int, portfolio_id?: int | List[Site] | Site, Portefeuille | sites.py:12 |
| GET | /api/sites/{id} | Site detail | ❌ | PUBLIC | - | SiteDetail | Site, Batiment, Compteur, Usage | sites.py:35 |
| POST | /api/sites | Create new site | ❌ | ADMIN | Site data | Site | Site, Portefeuille | sites.py:60 |
| PUT | /api/sites/{id} | Update site | ❌ | ADMIN | Partial Site data | Site | Site | sites.py:85 |
| DELETE | /api/sites/{id} | Delete site (soft) | ❌ | ADMIN | - | Success | Site | sites.py:110 |
| GET | /api/sites/{id}/stats | Site consumption stats | ❌ | PUBLIC | period?: str | Stats | Consommation, Compteur | sites.py:130 |

**Notes**:
- CRUD operations without auth = 🔴 **CRITICAL**
- DELETE without confirmation = dangerous
- No audit trail on modifications
- DB: N+1 on /sites list (no eager loading)

---

### 3. REGOPS (NEW - Deterministic Core) - 4 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/regops/site/{id} | Fresh RegOps evaluation | ❌ | PUBLIC | - | SiteSummary | Site, Batiment, Evidence, RegAssessment | regops.py:18 |
| GET | /api/regops/site/{id}/cached | Cached RegOps assessment | ❌ | PUBLIC | - | RegAssessment | RegAssessment | regops.py:45 |
| POST | /api/regops/recompute | Trigger recompute | ❌ | ADMIN | scope: str, target_id?: int | JobOutbox | Site, RegAssessment, JobOutbox | regops.py:65 |
| GET | /api/regops/dashboard | Org RegOps KPIs | ❌ | PUBLIC | org_id?: int | OrgRegOpsDashboard | RegAssessment, Site | regops.py:95 |

**Notes**:
- Core new feature (0/16 tests passing due to YAML mismatch)
- /recompute triggers jobs = needs auth + rate limiting
- No cache invalidation endpoint (manual only via /recompute)
- DB: Bulk queries OK (evaluate_batch optimized), no N+1

**Data Flow**:
```
GET /api/regops/site/1
  ↓
regops/engine.py:evaluate_site()
  ↓ Load YAML configs (cached)
  ↓ Load Site + Batiments + Evidences (3 queries)
  ↓ Run 4 rule engines (tertiaire, bacs, aper, cee_p6)
  ↓ Merge findings + score computation
  ↓
Return SiteSummary JSON
```

---

### 4. CONNECTORS (NEW - External APIs) - 3 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/connectors/list | List available connectors | ❌ | PUBLIC | - | List[ConnectorInfo] | - | connectors_route.py:15 |
| POST | /api/connectors/{name}/test | Test connection | ❌ | ADMIN | config?: dict | TestResult | - | connectors_route.py:35 |
| POST | /api/connectors/{name}/sync | Sync data from external API | ❌ | ADMIN | site_id?: int, org_id?: int | SyncResult | DataPoint, Site | connectors_route.py:60 |

**Notes**:
- /sync writes DataPoints = needs auth + rate limiting
- External API calls (RTE, PVGIS, Enedis, MeteoFrance)
- No retry logic visible (needs error handling)
- DB: Batch insert DataPoints (OK), no N+1

**Available Connectors**:
1. **rte_eco2mix** (REAL): Grid CO2 intensity
2. **pvgis** (REAL): Solar production estimates
3. **meteofrance** (STUB): Weather data
4. **enedis_opendata** (STUB): Public grid data
5. **enedis_dataconnect** (STUB): Meter data (OAuth)

---

### 5. WATCHERS (NEW - Regulatory Monitoring) - 4 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/watchers/list | List available watchers | ❌ | PUBLIC | - | List[WatcherInfo] | - | watchers_route.py:15 |
| POST | /api/watchers/{name}/run | Run watcher manually | ❌ | ADMIN | - | RunResult | RegSourceEvent | watchers_route.py:35 |
| GET | /api/watchers/events | List regulatory events | ❌ | PUBLIC | reviewed?: bool, limit?: int | List[RegSourceEvent] | RegSourceEvent | watchers_route.py:60 |
| PATCH | /api/watchers/events/{id}/review | Mark event as reviewed | ❌ | ADMIN | review_note?: str | RegSourceEvent | RegSourceEvent | watchers_route.py:85 |

**Notes**:
- /run triggers external RSS fetch = needs auth + rate limiting
- /events returns raw regulatory news = OK public
- /review without auth = anyone can mark reviewed
- DB: Simple queries, no N+1

**Available Watchers**:
1. **legifrance_watcher**: Official legal texts (RSS)
2. **cre_watcher**: Energy regulator news (RSS)
3. **rte_watcher**: Grid operator announcements (RSS)

---

### 6. AI AGENTS (NEW - Insights) - 5 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/ai/site/{id}/explain | AI brief explanation | ❌ | PUBLIC | - | AiInsight | Site, AiInsight, RegAssessment | ai_route.py:18 |
| GET | /api/ai/site/{id}/recommend | AI action suggestions | ❌ | PUBLIC | - | AiInsight | Site, AiInsight, RegAssessment | ai_route.py:45 |
| GET | /api/ai/site/{id}/data-quality | Data quality analysis | ❌ | PUBLIC | - | AiInsight | Site, DataPoint, AiInsight | ai_route.py:70 |
| GET | /api/ai/org/brief | Exec portfolio brief | ❌ | PUBLIC | org_id?: int | AiInsight | Site, RegAssessment, AiInsight | ai_route.py:95 |
| GET | /api/ai/insights | List all AI insights | ❌ | PUBLIC | object_type?: str, object_id?: int | List[AiInsight] | AiInsight | ai_route.py:120 |

**Notes**:
- Stub mode if no AI_API_KEY (returns mock responses)
- AI calls cost money = needs auth + usage tracking
- No rate limiting = potential abuse
- DB: Cached in AiInsight table (good), no N+1

**HARD RULE**: AI agents **NEVER** modify compliance status (enforced in agents, tested)

---

### 7. COCKPIT - 3 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/cockpit/overview | Global KPI dashboard | ❌ | PUBLIC | org_id?: int | CockpitOverview | Site, Consommation, Obligation, Alerte | cockpit.py:15 |
| GET | /api/cockpit/alerts | Active alerts | ❌ | PUBLIC | severity?: str | List[Alerte] | Alerte, Site | cockpit.py:45 |
| POST | /api/cockpit/alerts/{id}/acknowledge | Acknowledge alert | ❌ | USER | note?: str | Alerte | Alerte | cockpit.py:70 |

**Notes**:
- Heavy aggregation queries (5+ tables joins)
- No caching = slow on large datasets
- /acknowledge needs auth

---

### 8. DEMO MODE - 2 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/demo/status | Demo mode status | ❌ | PUBLIC | - | DemoStatus | - | demo.py:12 |
| POST | /api/demo/toggle | Enable/disable demo mode | ❌ | ADMIN | enabled: bool | DemoStatus | - | demo.py:30 |

**Notes**:
- In-memory state (services/demo_state.py)
- No persistence across restarts
- /toggle needs auth

---

### 9. GUIDANCE - 2 routes

| Method | Path | Description | Auth | Roles | Payload | Response | DB Tables | File:Line |
|--------|------|-------------|------|-------|---------|----------|-----------|-----------|
| GET | /api/guidance/next-steps | Suggested next actions | ❌ | PUBLIC | site_id?: int | List[Guidance] | Site, Obligation, Evidence | guidance.py:15 |
| POST | /api/guidance/dismiss | Dismiss guidance item | ❌ | USER | guidance_id: int | Success | - | guidance.py:40 |

**Notes**:
- Simple heuristics (no AI)
- /dismiss needs persistence (currently no-op?)

---

## AUTH & RBAC REQUIREMENTS

### Current State: 🔴 **NONE**

All 37 endpoints are **PUBLIC** (no auth middleware, no JWT, no session).

### Required Roles (for RBAC_MATRIX.md)

| Role | Description | Access Level |
|------|-------------|--------------|
| **PUBLIC** | Anonymous | Read-only public data (dashboards, public KPIs) |
| **USER** | Authenticated user | Read own org data, acknowledge alerts |
| **MANAGER** | Site/portfolio manager | Edit sites, upload evidence, complete actions |
| **ADMIN** | Organisation admin | All org data, run connectors/watchers, trigger recomputes |
| **SUPERADMIN** | Platform admin | All orgs, manage users, demo mode |

### Critical Endpoints Needing Auth

| Priority | Endpoint | Current | Required | Risk |
|----------|----------|---------|----------|------|
| 🔴 P0 | POST /api/sites | PUBLIC | ADMIN | Anyone can create sites |
| 🔴 P0 | DELETE /api/sites/{id} | PUBLIC | ADMIN | Anyone can delete |
| 🔴 P0 | POST /api/regops/recompute | PUBLIC | ADMIN | Trigger expensive jobs |
| 🔴 P0 | POST /api/connectors/{name}/sync | PUBLIC | ADMIN | External API abuse |
| 🔴 P0 | POST /api/watchers/{name}/run | PUBLIC | ADMIN | External scraping abuse |
| 🟡 P1 | POST /api/compliance/evidence/upload | PUBLIC | MANAGER | Anyone can upload |
| 🟡 P1 | POST /api/compliance/site/{id}/validate | PUBLIC | ADMIN | Anyone can validate |
| 🟡 P1 | GET /api/ai/site/{id}/explain | PUBLIC | USER | AI costs money |
| 🟡 P1 | PATCH /api/watchers/events/{id}/review | PUBLIC | ADMIN | Anyone can mark reviewed |
| 🟢 P2 | POST /api/cockpit/alerts/{id}/acknowledge | PUBLIC | USER | Low risk |

---

## PERFORMANCE CONCERNS

### N+1 Query Risk

| Endpoint | Risk | Issue | Fix |
|----------|------|-------|-----|
| GET /api/compliance/sites | 🔴 HIGH | Loads obligations per site in loop | Add .joinedload(Site.obligations) |
| GET /api/sites | 🟡 MEDIUM | Loads batiments per site in loop | Add .joinedload(Site.batiments) |
| GET /api/compliance/site/{id}/assessment | 🟡 MEDIUM | 6 queries per assessment | Use evaluate_batch() pattern |
| GET /api/cockpit/overview | 🟡 MEDIUM | 5 table joins | Add indices on FKs |

### Heavy Endpoints

| Endpoint | Avg Time | Max Time | Issue |
|----------|----------|----------|-------|
| GET /api/compliance/site/{id}/assessment | 300ms | 2s | No caching, 6 queries |
| POST /api/regops/recompute (scope=all) | - | 60s | 120 sites sequential |
| GET /api/cockpit/overview | 150ms | 1s | Heavy aggregations |
| GET /api/ai/org/brief | 5s | 30s | Real AI call (stub=instant) |

**Recommendations**:
1. Add Redis caching for /compliance/site, /regops/site/cached
2. Use evaluate_batch() for /recompute (already implemented, just use it)
3. Add background jobs for AI endpoints (don't block HTTP request)
4. Add indices: `CREATE INDEX idx_site_org ON site(organisation_id)`

---

## ERROR HANDLING

### Current State

| Endpoint | 404 | 400 | 500 | ValidationError |
|----------|-----|-----|-----|-----------------|
| GET /api/sites/{id} | ✅ | ❌ | ❌ | ❌ |
| POST /api/sites | ❌ | ⚠️ | ❌ | ⚠️ |
| POST /api/regops/recompute | ❌ | ❌ | ❌ | ❌ |
| GET /api/connectors/{name}/test | ❌ | ❌ | ⚠️ | ❌ |

**Legend**: ✅ Proper handling, ⚠️ Partial, ❌ Missing

### Missing Error Responses

1. **404 Not Found**: Most endpoints don't check if resource exists
2. **400 Bad Request**: Weak payload validation (Pydantic models exist but not enforced)
3. **429 Too Many Requests**: No rate limiting
4. **503 Service Unavailable**: External APIs fail silently
5. **422 Unprocessable Entity**: ValidationError not caught

**Recommendation**: Add global exception handlers in `main.py`:
```python
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(NoResultFound)
async def not_found_exception_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})
```

---

## CORS & SECURITY HEADERS

### Current CORS Config (main.py)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔴 DANGER - All origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Issues**:
- `allow_origins=["*"]` with `allow_credentials=True` = **SECURITY VULNERABILITY**
- No CSP headers
- No X-Frame-Options
- No rate limiting

**Fix**:
```python
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

## API VERSIONING

**Current**: No versioning (all routes at `/api/...`)

**Risk**: Breaking changes will break all clients

**Recommendation**: Add `/api/v1/...` prefix now before clients integrate

---

## OPENAPI / SWAGGER

**Status**: FastAPI auto-generates OpenAPI schema at `/docs`

**Issues**:
- No descriptions on most endpoints
- No examples in request/response schemas
- No auth security schemes defined

**Recommendation**: Add docstrings + Pydantic examples:
```python
@router.get("/api/regops/site/{id}", response_model=SiteSummary)
async def get_site_regops(id: int, db: Session = Depends(get_db)):
    """
    Get full RegOps compliance assessment for a site.

    Returns findings, actions, compliance score, and missing data.
    """
    ...
```

---

## RATE LIMITING

**Current**: ❌ **NONE**

**Critical Endpoints**:
- POST /api/connectors/{name}/sync (external API calls)
- POST /api/watchers/{name}/run (external scraping)
- POST /api/regops/recompute (expensive jobs)
- GET /api/ai/* (AI costs money)

**Recommendation**: Use `slowapi` (FastAPI rate limiting):
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/connectors/{name}/sync")
@limiter.limit("5/minute")
async def sync_connector(...):
    ...
```

---

## NEXT STEPS

1. **Immediate**:
   - Add auth middleware (JWT + role-based access)
   - Fix CORS config (whitelist origins)
   - Add rate limiting on write/expensive endpoints

2. **Short Term**:
   - Add global error handlers
   - Add caching (Redis) for read-heavy endpoints
   - Add indices on FK columns

3. **Medium Term**:
   - API versioning (/api/v1/)
   - OpenAPI documentation improvements
   - Background jobs for AI/long-running tasks

---

**Status**: 🔴 **CRITICAL** - No auth = production blocker
**Priority**: Implement RBAC before any deployment
**Reference**: See RBAC_MATRIX.md for detailed role permissions
