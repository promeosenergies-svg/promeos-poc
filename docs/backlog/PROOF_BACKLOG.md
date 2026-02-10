# PROOF BACKLOG - PROMEOS POC
**Date**: 2026-02-09
**Purpose**: Prioritized list of evidence and improvements needed

---

## OVERVIEW

This backlog tracks **proofs** (evidence, tests, documentation, features) needed to strengthen PROMEOS POC before production.

**Prioritization**: ICE Framework
- **I**mpact (1-10): Business value / risk reduction
- **C**onfidence (1-10): Certainty we can deliver
- **E**ffort (1-10): Time/complexity (10 = quick, 1 = hard)
- **ICE Score** = (I × C × E) / 10

---

## BRIQUE 1: REGOPS (16 items)

### P0: Critical Blockers (ICE ≥ 90)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| R1 | Fix YAML config access (16 tests failing) | 10 | 10 | 9 | 90 | DEV | Tonight |
| R2 | Add auth middleware (JWT + roles) | 10 | 9 | 8 | 72 | DEV | This week |
| R3 | Fix TypeEvidence enum (add AUDIT_ENERGETIQUE) | 8 | 10 | 10 | 80 | DEV | Tonight |
| R4 | Fix AI agents fixture (organisation_id issue) | 7 | 10 | 9 | 63 | DEV | Tonight |

**Total P0 Effort**: 2 hours (tonight) + 8 hours (auth this week)

---

### P1: High Priority (ICE 50-89)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| R5 | Add critical DB indexes (10 indexes) | 9 | 10 | 9 | 81 | DBA | This week |
| R6 | Fix JobOutbox return type + cascade SQL | 7 | 10 | 8 | 56 | DEV | This week |
| R7 | Add RegOps integration tests (10 tests) | 8 | 8 | 7 | 44.8 | QA | Next week |
| R8 | Setup Alembic migrations | 9 | 9 | 6 | 48.6 | DBA | Next week |
| R9 | Add rate limiting (slowapi) | 8 | 9 | 8 | 57.6 | DEV | Next week |
| R10 | Fix CORS config (whitelist origins) | 9 | 10 | 10 | 90 | DEV | Tonight |

**Total P1 Effort**: 12 hours (this week)

---

### P2: Medium Priority (ICE 30-49)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| R11 | Add audit logging (AuditLog table + middleware) | 7 | 8 | 7 | 39.2 | DEV | 2 weeks |
| R12 | Migrate SQLite → PostgreSQL | 10 | 7 | 4 | 28 | DBA | Before prod |
| R13 | Add 8 ADRs to KB | 6 | 9 | 7 | 37.8 | TECH-LEAD | 1 month |
| R14 | Create evidence templates (4 regulations) | 5 | 8 | 8 | 32 | COMPLIANCE | 1 month |
| R15 | Add Prometheus /metrics endpoint | 6 | 9 | 9 | 48.6 | DEV | 2 weeks |
| R16 | Document all API endpoints (OpenAPI descriptions) | 5 | 9 | 8 | 36 | DEV | 2 weeks |

**Total P2 Effort**: 24 hours (1-2 months)

---

## BRIQUE 2: BILL INTELLIGENCE (10 items - Planned)

### P0: Foundation (ICE ≥ 70)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| B1 | Design DB schema (3 tables: bills, anomalies, tariffs) | 9 | 9 | 9 | 72.9 | TECH-LEAD | Q1 2026 |
| B2 | Research OCR solutions (Tesseract vs AWS Textract) | 8 | 7 | 8 | 44.8 | DEV | Q1 2026 |
| B3 | Implement bill upload endpoint + file storage (S3) | 9 | 8 | 7 | 50.4 | DEV | Q1 2026 |
| B4 | Build price anomaly detection (3σ threshold) | 9 | 9 | 8 | 64.8 | DATA | Q1 2026 |

**Total P0 Effort**: 40 hours (1 month)

---

### P1: Core Features (ICE 50-69)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| B5 | Implement volume mismatch detection (vs RegOps kWh) | 8 | 8 | 8 | 51.2 | DATA | Q1 2026 |
| B6 | Build tariff reference database (CRE open data) | 7 | 7 | 7 | 34.3 | DATA | Q2 2026 |
| B7 | Create BillsPage.jsx (upload + list + drill-down) | 7 | 8 | 8 | 44.8 | FRONTEND | Q1 2026 |
| B8 | Create BillAnalyticsPage.jsx (savings dashboard) | 6 | 8 | 8 | 38.4 | FRONTEND | Q2 2026 |

**Total P1 Effort**: 32 hours (1-2 months)

---

### P2: Advanced Features (ICE 30-49)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| B9 | Implement tariff error detection (compare billed vs reference) | 6 | 7 | 7 | 29.4 | DATA | Q2 2026 |
| B10 | Add AI bill analysis agent (suggest optimizations) | 5 | 6 | 6 | 18 | AI-ENG | Q2 2026 |

**Total P2 Effort**: 16 hours (2-3 months)

---

## BRIQUE 3: SCÉNARIOS ACHAT POST-ARENH (10 items - Planned)

### P0: Foundation (ICE ≥ 70)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| P1 | Design DB schema (4 tables: scenarios, options, market_data, strategies) | 9 | 8 | 9 | 64.8 | TECH-LEAD | Q2 2026 |
| P2 | Research market data APIs (EPEX SPOT, EEX, RTE) | 8 | 6 | 7 | 33.6 | DEV | Q2 2026 |
| P3 | Implement scenario creation endpoint | 8 | 7 | 8 | 44.8 | DEV | Q2 2026 |
| P4 | Build basic Monte Carlo simulator (spot vs forward) | 9 | 6 | 5 | 27 | QUANT | Q2 2026 |

**Total P0 Effort**: 60 hours (2 months)

---

### P1: Core Features (ICE 50-69)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| P5 | Implement market data connector (EPEX SPOT API) | 8 | 6 | 7 | 33.6 | DEV | Q2 2026 |
| P6 | Build scenario comparison UI (table + charts) | 7 | 8 | 8 | 44.8 | FRONTEND | Q2 2026 |
| P7 | Add PPA option modeling (fixed price + volume) | 7 | 7 | 7 | 34.3 | QUANT | Q3 2026 |
| P8 | Create ProcurementPage.jsx (scenario builder) | 6 | 8 | 8 | 38.4 | FRONTEND | Q3 2026 |

**Total P1 Effort**: 48 hours (2-3 months)

---

### P2: Advanced Features (ICE 30-49)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| P9 | Add VaR calculation (Value at Risk) | 6 | 5 | 6 | 18 | QUANT | Q3 2026 |
| P10 | Implement AI strategy recommender (RL-based) | 5 | 4 | 4 | 8 | AI-ENG | Q3 2026 |

**Total P2 Effort**: 24 hours (3-4 months)

---

## CROSS-CUTTING CONCERNS (15 items)

### P0: Security (ICE ≥ 80)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| S1 | Implement JWT auth (login, refresh, logout) | 10 | 9 | 8 | 72 | DEV | This week |
| S2 | Add RBAC enforcement (6 roles) | 10 | 8 | 7 | 56 | DEV | 2 weeks |
| S3 | Secure secrets management (Vault or AWS Secrets) | 9 | 7 | 6 | 37.8 | OPS | 1 month |
| S4 | Add 2FA for ADMIN/SUPERADMIN | 8 | 7 | 6 | 33.6 | DEV | 1 month |
| S5 | Implement rate limiting (per role) | 9 | 9 | 8 | 64.8 | DEV | 2 weeks |

**Total P0 Effort**: 24 hours (1 month)

---

### P1: Observability (ICE 50-79)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| O1 | Add structured logging (JSON logs) | 8 | 9 | 9 | 64.8 | DEV | 2 weeks |
| O2 | Add Prometheus metrics (/metrics endpoint) | 8 | 9 | 9 | 64.8 | DEV | 2 weeks |
| O3 | Setup Grafana dashboards (3 dashboards) | 7 | 7 | 7 | 34.3 | OPS | 1 month |
| O4 | Add distributed tracing (OpenTelemetry) | 6 | 6 | 6 | 21.6 | DEV | 2 months |
| O5 | Implement error tracking (Sentry) | 7 | 8 | 9 | 50.4 | DEV | 2 weeks |

**Total P1 Effort**: 20 hours (1-2 months)

---

### P2: DevOps (ICE 40-59)

| # | Proof | Impact | Confidence | Effort | ICE | Owner | Deadline |
|---|-------|--------|------------|--------|-----|-------|----------|
| D1 | Dockerize backend + frontend | 8 | 8 | 7 | 44.8 | OPS | 2 weeks |
| D2 | Setup CI/CD pipeline (GitHub Actions) | 8 | 8 | 7 | 44.8 | OPS | 2 weeks |
| D3 | Create production deployment guide | 6 | 9 | 9 | 48.6 | OPS | 1 month |
| D4 | Setup staging environment | 7 | 7 | 6 | 29.4 | OPS | 1 month |
| D5 | Implement blue-green deployment | 6 | 6 | 5 | 18 | OPS | 2 months |

**Total P2 Effort**: 24 hours (1-2 months)

---

## PROOF COLLECTION STRATEGY

### Phase 1: Stabilize Brique 1 (2 weeks)

**Goal**: Fix all P0 issues, get to 100% tests passing, add auth

**Items**: R1, R2, R3, R4, R10, S1, S2
**Effort**: 40 hours (1 week full-time, 2 weeks part-time)
**Success Criteria**:
- ✅ 98/98 tests passing
- ✅ JWT auth implemented
- ✅ RBAC enforced on 37 endpoints
- ✅ CORS secured
- ✅ Ready for limited production pilot (1 org, 10 sites)

---

### Phase 2: Production-Ready Brique 1 (1 month)

**Goal**: Add observability, migrations, performance optimizations

**Items**: R5, R6, R7, R8, R9, R11, O1, O2, O5, D1, D2
**Effort**: 80 hours (2 weeks full-time, 1 month part-time)
**Success Criteria**:
- ✅ PostgreSQL migration complete
- ✅ Alembic migrations working
- ✅ Critical indexes added
- ✅ Prometheus + Sentry integrated
- ✅ Docker + CI/CD pipeline
- ✅ Ready for production (multi-org, 120+ sites)

---

### Phase 3: Launch Brique 2 (2 months)

**Goal**: Deliver Bill Intelligence MVP

**Items**: B1, B2, B3, B4, B5, B7
**Effort**: 120 hours (3 weeks full-time, 2 months part-time)
**Success Criteria**:
- ✅ Bills upload + OCR working
- ✅ Price anomaly detection (3σ)
- ✅ Volume mismatch detection
- ✅ BillsPage UI complete
- ✅ Tested with 50+ bills

---

### Phase 4: Launch Brique 3 (3 months)

**Goal**: Deliver Procurement Scenarios MVP

**Items**: P1, P2, P3, P4, P5, P6, P7, P8
**Effort**: 180 hours (4-5 weeks full-time, 3 months part-time)
**Success Criteria**:
- ✅ Scenario builder UI
- ✅ EPEX SPOT market data integration
- ✅ Monte Carlo simulator (spot vs forward vs PPA)
- ✅ Scenario comparison UI
- ✅ Tested with 10+ scenarios

---

## PROOF BY TYPE

### Code Proofs (Features)

| Type | Count | Total Effort |
|------|-------|--------------|
| Bug fixes | 4 (R1-R4) | 4 hours |
| Security | 5 (S1-S5) | 24 hours |
| Observability | 5 (O1-O5) | 20 hours |
| DevOps | 5 (D1-D5) | 24 hours |
| Brique 1 improvements | 12 (R5-R16) | 36 hours |
| Brique 2 foundation | 10 (B1-B10) | 88 hours |
| Brique 3 foundation | 10 (P1-P10) | 132 hours |

**Total Code Effort**: 328 hours (~8 weeks full-time)

---

### Documentation Proofs

| Type | Count | Total Effort |
|------|-------|--------------|
| ADRs | 8 | 4 hours |
| Evidence templates | 4 | 2 hours |
| Playbooks | 5 | 3 hours |
| API documentation | 37 endpoints | 4 hours |
| Deployment guide | 1 | 2 hours |

**Total Docs Effort**: 15 hours (~2 days)

---

### Test Proofs

| Type | Count | Total Effort |
|------|-------|--------------|
| Fix existing tests | 26 failures | 2 hours |
| RegOps integration tests | 10 tests | 4 hours |
| RBAC tests | 20 tests | 4 hours |
| Brique 2 tests | 15 tests | 6 hours |
| Brique 3 tests | 15 tests | 8 hours |
| Contract tests (cross-brick) | 10 tests | 4 hours |

**Total Test Effort**: 28 hours (~4 days)

---

## TRACKING & METRICS

### Burndown Chart (Weekly)

Target: 328 hours code + 15 hours docs + 28 hours tests = **371 hours total**

```
Week 0:  371h remaining (0% complete)
Week 2:  331h remaining (11% complete) ← Phase 1 done
Week 6:  251h remaining (32% complete) ← Phase 2 done
Week 14: 131h remaining (65% complete) ← Phase 3 done
Week 26: 0h remaining (100% complete) ← Phase 4 done
```

### Velocity Tracking

**Assumption**: 20 hours/week per developer (part-time on POC)

- **1 dev**: 26 weeks (6 months)
- **2 devs**: 13 weeks (3 months)
- **3 devs**: 9 weeks (2 months)

---

## RISK MITIGATION

### High-Risk Items (Low Confidence)

| # | Proof | Confidence | Risk | Mitigation |
|---|-------|------------|------|------------|
| B2 | OCR solution research | 7 | OCR accuracy < 80% | Fallback: manual data entry UI |
| P2 | Market data APIs | 6 | API access denied / expensive | Fallback: use public historical data |
| P4 | Monte Carlo simulator | 6 | Complexity underestimated | Start simple (spot vs forward only) |
| P10 | AI strategy recommender | 4 | RL model doesn't converge | Fallback: rule-based heuristics |

---

## DEPENDENCIES

### External Dependencies

| Item | Depends On | Blocker If Missing |
|------|------------|-------------------|
| B3 | S3/file storage | ✅ Critical - Need storage for bill PDFs |
| B4 | Brique 1 annual_kwh_total | ✅ Critical - Need baseline for volume comparison |
| B6 | CRE open data API | ⚠️ Medium - Can use static CSV initially |
| P5 | EPEX SPOT API access | ✅ Critical - Need account + credentials |
| P7 | PPA contract examples | ⚠️ Medium - Can simulate with fake data |

### Internal Dependencies

| Item | Depends On | Blocker If Missing |
|------|------------|-------------------|
| R7 | R1 (fix YAML config) | ✅ Critical - Can't test if code broken |
| R8 | R12 (PostgreSQL) | ⚠️ Medium - Alembic works with SQLite too |
| S2 | S1 (JWT auth) | ✅ Critical - RBAC needs auth first |
| B4 | B1 (DB schema) | ✅ Critical - Need tables to store anomalies |
| P4 | P1 (DB schema) | ✅ Critical - Need tables to store scenarios |

---

## NEXT STEPS

### Tonight (4 hours)

1. Fix R1 (YAML config) → +16 tests passing
2. Fix R3 (TypeEvidence enum) → +4 tests passing
3. Fix R4 (AI agents fixture) → +5 tests passing
4. Fix R10 (CORS config) → Security improved

**Goal**: 98/98 tests passing ✅

---

### This Week (8 hours)

1. S1: Implement JWT auth (4 hours)
2. S2: Add RBAC enforcement (4 hours)

**Goal**: Auth implemented, 5 critical endpoints protected

---

### Next 2 Weeks (20 hours)

1. R5: Add DB indexes (2 hours)
2. R6: Fix JobOutbox (2 hours)
3. R8: Setup Alembic (3 hours)
4. R9: Add rate limiting (2 hours)
5. O1: Structured logging (3 hours)
6. O2: Prometheus metrics (3 hours)
7. O5: Sentry error tracking (2 hours)
8. D1: Dockerize (3 hours)

**Goal**: Production-ready infrastructure

---

### Q1 2026 (80 hours)

Launch Brique 2 MVP:
- B1, B2, B3, B4, B5, B7

**Goal**: Bill Intelligence pilot with 1 organisation

---

### Q2 2026 (120 hours)

Launch Brique 3 MVP:
- P1, P2, P3, P4, P5, P6, P7, P8

**Goal**: Procurement Scenarios pilot with 1 organisation

---

**Status**: 🟢 **BACKLOG READY** - 51 items prioritized with ICE scores
**Next Action**: Execute "Tonight" plan (4 hours) → 100% tests passing
**Reference**: See TEST_REPORT.md for detailed test failures
