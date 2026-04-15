# AUDIT SUMMARY - PROMEOS POC

**Date**: 2026-02-13
**Auditeur**: Claude Code (Opus 4.6)
**Commit**: HEAD (post Smart Intake DIAMANT)

---

## 1. Vue d'ensemble

| Metrique | Valeur |
|----------|--------|
| Endpoints API | **196** (30 routers + 2 app-level + modules kb/bill) |
| Tables DB (SQLAlchemy) | **62** |
| Tests backend | **824 passed, 0 failed** |
| Fichiers test | **38** |
| Frontend build | **OK** (608.52 kB JS, 52.61 kB CSS) |
| Pages frontend | **30** |
| Services backend | **33** |
| Enums domaine | **36** |
| Roles IAM | **11** |
| Warnings deprecation | 54942 (datetime.utcnow) |

---

## 2. Matrice de maturite des briques

| # | Brique | Mat. | Backend | Frontend | Tests | Notes |
|---|--------|------|---------|----------|-------|-------|
| 1 | **IAM / Auth** | 2 | auth.py, admin_users.py, iam_service.py | LoginPage, Admin* (4 pages) | 61 | JWT HS256, 11 roles, 3 scope levels, audit log |
| 2 | **Patrimoine DIAMANT** | 2 | patrimoine.py, patrimoine_service.py, quality_rules.py | Patrimoine.jsx, PatrimoineWizard.jsx | 29 | Staging pipeline, quality gate, activation, lineage, sync |
| 3 | **Smart Intake DIAMANT** | 2 | intake.py, intake_engine.py, intake_service.py | IntakeWizard.jsx | 25 | Question bank, prefill, before/after, demo autofill |
| 4 | **Conformite / Compliance** | 2 | compliance.py, compliance_engine.py, compliance_rules.py | ConformitePage, CompliancePage | 20 | YAML rules, 3 packs (DT/BACS/APER), findings, batches |
| 5 | **RegOps** | 2 | regops.py, regops/engine.py | RegOps.jsx | 16 | Evaluation reglementaire, assessments, cache |
| 6 | **Bill Intelligence** | 2 | billing.py, app/bill_intelligence/ | BillIntelPage.jsx | 73 | Contrats, factures, shadow audit, PDF parser, CSV import |
| 7 | **Achat Energie** | 2 | purchase.py, purchase_service.py | PurchasePage.jsx | 18 | Scenarios fixe/indexe/spot, renouvellements |
| 8 | **Knowledge Base** | 2 | kb_usages.py, app/kb/, kb_service.py | KBExplorerPage.jsx | 26 | Archetypes, anomaly rules, recommendations, search |
| 9 | **Diagnostic Conso** | 2 | consumption_diagnostic.py (routes+service) | ConsumptionDiagPage.jsx | 28 | Detecteurs (baseline, pointe, weekend, nuit), insights |
| 10 | **Energy / Monitoring** | 2 | energy.py, monitoring.py, electric_monitoring/ | MonitoringPage.jsx | 24 | Meters, KPI engine, alerts, snapshots |
| 11 | **Cockpit / Dashboard** | 1 | cockpit.py, dashboard_2min.py | Cockpit.jsx, Dashboard.jsx | 0 | Fonctionnel mais 0 tests |
| 12 | **Actions Hub** | 1 | actions.py, action_hub_service.py | ActionsPage.jsx | 7 | Sync, workflow, export CSV |
| 13 | **Notifications** | 1 | notifications.py, notification_service.py | NotificationsPage.jsx | 8 | Events, preferences. Pas de push real-time |
| 14 | **Onboarding** | 1 | onboarding.py, onboarding_service.py | UpgradeWizard.jsx | 5 | Overlap avec Patrimoine |
| 15 | **Segmentation** | 1 | segmentation.py, segmentation_service.py | SegmentationPage.jsx | 6 | Questionnaire, profil NAF |
| 16 | **Sites** | 1 | sites.py, site_config.py | Site360.jsx | 1 | 3 TabStub dans Site360 |
| 17 | **Import CSV** | 1 | import_sites.py | ImportPage.jsx | 4 | Template + import |
| 18 | **Connectors** | 1 | connectors_route.py | ConnectorsPage.jsx | 7 | RTE Eco2Mix, PVGIS |
| 19 | **Watchers** | 1 | watchers_route.py | WatchersPage.jsx | 6 | RSS veille reglementaire |
| 20 | **AI Agents** | 0 | ai_route.py, ai_layer/client.py | - | 7 | Stub: TODO real API call |
| 21 | **Reports** | 0 | reports.py, audit_report_service.py | - | 3 | Audit JSON/PDF stub |
| 22 | **Demo Mode** | 1 | demo.py, demo_state.py | - | 0 | Enable/disable/seed |
| 23 | **Alertes** | 1 | alertes.py | - | 0 | CRUD basique |
| 24 | **Guidance** | 0 | guidance.py | ActionPlan.jsx | 0 | Action plan stub |
| 25 | **Compteurs** | 1 | compteurs.py | - | 0 | CRUD basique |

**Legende**: 0 = stub/placeholder, 1 = fonctionnel partiel, 2 = complet (service + routes + tests + UI)

---

## 3. Top 10 Blockers

| # | Fichier | Ligne | Cause | Fix estime |
|---|---------|-------|-------|------------|
| 1 | `services/iam_service.py` | L24 | **JWT secret hardcode** `"dev-secret-change-me-in-prod"` en fallback | 10 min |
| 2 | `ai_layer/client.py` | L23 | **AI client stub** — `# TODO: Real API call` — pas d'appel reel | 30 min |
| 3 | `pages/Site360.jsx` | L416-419 | **3 TabStub** (Conso, Factures, Actions) non branchees sur API | 2h |
| 4 | `scripts/seed_data.py` | L867 | **Password identique** `"demo2024"` pour les 10 users seed | 15 min |
| 5 | `jobs/worker.py` | L106 | **TODO: entity/org level recompute** non implemente | 1h |
| 6 | `services/kb_service.py` | L100, L215 | **TODO: temporal_signature, implementation_steps** toujours null | 30 min |
| 7 | `routes/cockpit.py` | - | **0 tests** pour le cockpit (brique visible #1) | 1h |
| 8 | `database/connection.py` | L17 | **SQLite** en prod, pas de migration Alembic | 2h |
| 9 | `services/notification_service.py` | - | **Pas de push real-time** (polling HTTP seulement) | 4h |
| 10 | Backend (33 fichiers) | - | **454 print()** au lieu de `logging` | 2h |

---

## 4. Plan d'action

### Phase 1: 60-90 minutes (securite + couverture)

| # | Action | Temps | Impact |
|---|--------|-------|--------|
| 1 | Forcer `PROMEOS_JWT_SECRET` env var (crash si absent en prod) | 10 min | Securite |
| 2 | Ajouter 5 tests cockpit aggregation | 20 min | Couverture |
| 3 | Ajouter 3 tests alertes CRUD | 15 min | Couverture |
| 4 | Ajouter 3 tests demo mode | 15 min | Couverture |
| 5 | Fix `datetime.utcnow()` -> `datetime.now(UTC)` (supprime 54942 warnings) | 15 min | Hygiene |
| 6 | Interceptor axios 401 -> redirect /login | 10 min | UX |

**Resultat**: ~840 tests verts, 0 deprecation warnings, JWT securise.

### Phase 2: 48 heures (completude + ops)

| # | Action | Temps | Impact |
|---|--------|-------|--------|
| 1 | Brancher 3 TabStub Site360 sur les API existantes | 4h | UX |
| 2 | Implementer AI client Anthropic (httpx) | 2h | Fonctionnel |
| 3 | Setup Alembic migrations | 3h | Ops |
| 4 | Middleware RBAC `require_permission` sur tous les endpoints | 4h | Securite |
| 5 | WebSocket/SSE notifications temps reel | 4h | UX |
| 6 | Code-splitting frontend (dynamic import, < 500kB) | 2h | Performance |
| 7 | Remplacer `print()` par `logging` (454 occurrences / 33 fichiers) | 2h | Ops |
| 8 | KB seed: ingestion batch docs reglementaires | 4h | KB completude |
| 9 | Health check DB + endpoint `/ready` pour k8s | 1h | Ops |
| 10 | CI/CD GitHub Actions (lint + tests + build) | 3h | DevOps |
| 11 | Worker entity/org level recompute | 2h | Completude |
| 12 | Tests E2E Playwright (5 scenarios cles) | 4h | Qualite |

---

## 5. Architecture

```
promeos-poc/
backend/
  main.py                    # FastAPI, 32+ routers incluant auth
  database/connection.py     # SQLite + SQLAlchemy
  models/ (34 fichiers)      # 62 tables, 36 enums
  services/ (33 fichiers)    # Logique metier
  routes/ (30 fichiers)      # 196 endpoints API
  rules/                     # YAML compliance rules (DT/BACS/APER)
  tests/ (38 fichiers)       # 824 tests
  scripts/                   # seed_data, kb_*, referential
  app/                       # Sub-apps (kb, bill_intelligence)
  ai_layer/                  # AI client (stub)
  connectors/                # RTE Eco2Mix, PVGIS
  watchers/                  # RSS veille reglementaire
  jobs/                      # Worker async (JobOutbox)
  regops/                    # RegOps engine
frontend/src/
  pages/ (30)                # 30 pages React
  components/ (~15)          # Wizards, modals, tables
  services/api.js            # Axios (~80 fonctions API)
  contexts/AuthContext.jsx   # JWT auth state + auto-refresh
  layout/AppShell.jsx        # Sidebar 24 entries + topbar
  ui/                        # Design system Tailwind
docs/audits/general/                  # Ce dossier
```

## 6. Stack technique

| Couche | Technologie | Version |
|--------|-------------|---------|
| Backend | Python | 3.14 |
| API | FastAPI | latest |
| ORM | SQLAlchemy | 2.x |
| DB | SQLite | embarque |
| Auth | python-jose + bcrypt | JWT HS256 |
| Frontend | React | 18 |
| Build | Vite | 5.4.21 |
| CSS | TailwindCSS | 4.x |
| Router | React Router | 6 |
| HTTP | Axios | latest |
| Icons | Lucide React | - |
| Charts | Recharts | - |
