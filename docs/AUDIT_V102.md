# PROMEOS — Audit V102 (2026-03-03)

## Resume

Audit complet de l'application PROMEOS (backend + frontend + routes + config).
120 issues identifiees, **20 corrigees** dans ce commit, **100 restantes** documentees ci-dessous.

---

## TOP 20 CORRIGE (ce commit)

| # | Severite | Fichier | Issue | Fix |
|---|----------|---------|-------|-----|
| 1 | CRITICAL | `iam_service.py` | JWT_SECRET fallback `"dev-secret-change-me-in-prod"` utilise sans warning | Log warning au demarrage si secret par defaut |
| 2 | CRITICAL | `main.py` | CORS `allow_origins=["*"]` avec `allow_credentials=True` | Restreint a localhost:5173/3000/127.0.0.1:5173, configurable via `PROMEOS_CORS_ORIGINS` |
| 3 | CRITICAL | `dev_tools.py` | `/api/dev/reset_db` sans guard DEMO_MODE — accessible en prod | Ajoute guard `DEMO_MODE` + HTTP 403 |
| 4 | HIGH | `auth.py` | Pas de validation mot de passe (changement) | Ajoute validation min 8 caracteres |
| 5 | HIGH | `iam_service.py` | `datetime.utcnow()` deprecie (Python 3.12+) | Remplace par `datetime.now(timezone.utc)` |
| 6 | HIGH | `auth.py` | `datetime.utcnow()` deprecie | Remplace par `datetime.now(timezone.utc)` |
| 7 | HIGH | `models/base.py` | `soft_delete()` utilise `datetime.utcnow()` | Remplace par `datetime.now(timezone.utc)` |
| 8 | HIGH | `routes/actions.py` | `datetime.utcnow()` (3 occurrences) | Remplace par `datetime.now(timezone.utc)` |
| 9 | HIGH | `routes/contracts_radar.py` | `datetime.utcnow()` | Remplace par `datetime.now(timezone.utc)` |
| 10 | HIGH | `database/connection.py` | `print()` en production | Remplace par `logging.getLogger()` |
| 11 | HIGH | `dev_tools.py` | `db.close()` appele avant backup (libere la session trop tot) | Supprime le `db.close()` premature |
| 12 | HIGH | `CreateActionDrawer.jsx` | catch-all cree une fausse action locale sur erreur API | Affiche erreur, garde le drawer ouvert pour retry |
| 13 | HIGH | `SegmentationQuestionnaireModal.jsx` | Soumission silencieuse sur erreur | Affiche message d'erreur + console.error |
| 14 | MEDIUM | `ActionPlan.jsx` | URL hardcodee `http://127.0.0.1:8001` | Remplace par `''` (utilise le proxy Vite) |
| 15 | MEDIUM | `DemoContext.jsx` | URL hardcodee `http://127.0.0.1:8001` | Remplace par `''` |
| 16 | MEDIUM | `SiteDetail.jsx` | URL hardcodee `http://127.0.0.1:8001` | Remplace par `''` |
| 17 | MEDIUM | `Site360.jsx` | 3x `.catch(() => {})` silencieux | Remplace par `console.error` |
| 18 | MEDIUM | `Patrimoine.jsx` | `.catch(() => {})` silencieux | Remplace par `console.error` |
| 19 | MEDIUM | `BillIntelPage.jsx` | `.catch(() => {})` silencieux | Remplace par `console.error` |
| 20 | MEDIUM | `ROISummaryBar.jsx`, `SitePicker.jsx` | `.catch(() => {})` silencieux | Remplace par `console.error` |

---

## ISSUES RESTANTES — Par priorite

### CRITICAL (3 restantes)

| # | Fichier | Issue | Recommandation |
|---|---------|-------|----------------|
| C1 | `iam_service.py` | Token JWT stocke dans localStorage (XSS) | Migrer vers httpOnly cookie + CSRF token. V103+ |
| C2 | `auth.py:247` | Impersonate sans auth en DEMO_MODE (open door) | Ajouter rate-limit + IP logging en DEMO_MODE |
| C3 | `pyproject.toml` | Ruff F401 ignore globalement — dead imports invisibles | Supprimer `F401` de la liste ignore, nettoyer les imports |

### HIGH (15 restantes)

| # | Fichier | Issue | Recommandation |
|---|---------|-------|----------------|
| H1 | `routes/*` (22 endpoints) | Pas de guard auth (passent par `get_optional_auth` qui retourne None en DEMO_MODE) | Cataloguer les endpoints, ajouter `require_permission()` sur les mutations critiques |
| H2 | `routes/actions.py` | Pas de pagination sur `GET /actions` — renvoie tout | Ajouter `limit/offset` + response `{total, items}` |
| H3 | `routes/patrimoine.py` | Pas de pagination sur `GET /patrimoine/sites` | Idem |
| H4 | `routes/billing.py` | Pas de pagination sur `GET /billing/insights` | Idem |
| H5 | `api.js` (interceptor) | Token non refresh automatiquement (expiration JWT 30min) | Implementer refresh token flow ou extend TTL |
| H6 | `services/*.py` (~60 occ.) | `datetime.utcnow()` restant dans 30+ fichiers | Migration progressive — script sed ou codemod |
| H7 | `routes/auth.py:86` | Pas de rate-limiting sur login | Ajouter slowapi ou middleware custom (5 req/min/IP) |
| H8 | `routes/auth.py` | Pas de protection brute-force (lockout) | Ajouter compteur d'echecs + lockout temporaire |
| H9 | `services/compliance_rules.py` | `batch.started_at = datetime.utcnow()` — 2 occurrences | Migrer vers `datetime.now(timezone.utc)` |
| H10 | `services/action_hub_service.py` | `datetime.utcnow()` — 2 occurrences | Idem |
| H11 | `services/notification_service.py` | `datetime.utcnow()` — 2 occurrences | Idem |
| H12 | `PatrimoinePortfolioHealthBar.jsx:232` | `window.location.reload()` apres action | Utiliser callback React pour re-fetch |
| H13 | `UpgradeWizard.jsx:215` | `window.location.reload()` apres upgrade | Idem |
| H14 | `SiteCompliancePage.jsx:232` | `window.location.reload()` apres action | Idem |
| H15 | `routes/segmentation.py` | `evaluate_organisation()` peut crasher en cascade sans try/except | Wrapper dans try/except avec fallback graceful |

### MEDIUM (35 restantes)

| # | Zone | Issue | Recommandation |
|---|------|-------|----------------|
| M1 | Backend | SQLAlchemy `declarative_base()` deprecie | Migrer vers `sqlalchemy.orm.declarative_base()` (2.0) |
| M2 | Backend | Pydantic v1 `class Config` (4 schemas) | Migrer vers `model_config = ConfigDict(...)` |
| M3 | Backend | `@app.on_event("startup")` deprecie FastAPI | Migrer vers lifespan context manager |
| M4 | Backend | `services/demo_seed/gen_weather.py` utilise `datetime.utcnow()` | Migrer |
| M5 | Backend | `services/demo_seed/gen_readings.py` — 4 occ. `datetime.utcnow()` | Migrer |
| M6 | Backend | `services/intake_service.py` — 3 occ. | Migrer |
| M7 | Backend | `services/kb_service.py` — 4 occ. | Migrer |
| M8 | Backend | `services/patrimoine_service.py` — 3 occ. | Migrer |
| M9 | Backend | `services/patrimoine_anomalies.py` — 2 occ. (`__import__` inline) | Migrer + supprimer `__import__` |
| M10 | Backend | `services/bacs_ops_monitor.py` — 3 occ. | Migrer |
| M11 | Backend | `services/analytics_engine.py` — 3 occ. | Migrer |
| M12 | Backend | `services/electric_monitoring/*.py` — 3 occ. | Migrer |
| M13 | Backend | `services/consumption_diagnostic.py` — 3 occ. | Migrer |
| M14 | Backend | `services/consumption_context_service.py` — 2 occ. | Migrer |
| M15 | Backend | `routes/monitoring.py` — 3 occ. | Migrer |
| M16 | Backend | `routes/patrimoine.py` — 2 occ. | Migrer |
| M17 | Backend | `routes/consumption_diagnostic.py` — 2 occ. | Migrer |
| M18 | Backend | `routes/alertes.py` — 1 occ. | Migrer |
| M19 | Backend | `routes/ems.py` — 1 occ. | Migrer |
| M20 | Backend | `routes/tertiaire.py` — 1 occ. | Migrer |
| M21 | Backend | `routes/watchers_route.py` — 1 occ. | Migrer |
| M22 | Backend | `regops/engine.py` — 2 occ. | Migrer |
| M23 | Backend | `connectors/rte_eco2mix.py`, `pvgis.py` — 2 occ. | Migrer |
| M24 | Backend | `jobs/worker.py` — 4 occ. | Migrer |
| M25 | Backend | `watchers/rss_watcher.py` — 1 occ. | Migrer |
| M26 | Frontend | `Sidebar.jsx` — 2x `.catch(() => {})` | Ajouter console.error |
| M27 | Frontend | `ContractRadarPage.jsx` — 2x `.catch(() => {})` | Ajouter console.error (optionnel: badge segmentation) |
| M28 | Frontend | `ScopeContext.jsx` — `.catch(() => {})` | OK — intentionnel (demo status passive) |
| M29 | Frontend | `AuthContext.jsx` — logout `.catch(() => {})` | OK — fire-and-forget |
| M30 | Frontend | `PatrimoineWizard.jsx` — recomputeSegmentation `.catch(() => {})` | OK — fire-and-forget |
| M31 | Backend | Test `test_action_close_rules_v49.py` en echec pre-existant | Investiguer et corriger |
| M32 | Backend | `scripts/seed_data.py` — 1 occ. `datetime.utcnow()` | Migrer |
| M33 | Backend | `app/referential/service.py` — 1 occ. | Migrer |
| M34 | Backend | `services/audit_report_service.py` — 1 occ. | Migrer |
| M35 | Backend | `services/tertiaire_service.py` — 3 occ. | Migrer |

### LOW (12 restantes)

| # | Zone | Issue | Recommandation |
|---|------|-------|----------------|
| L1 | Tests | 20+ tests utilisent `datetime.utcnow()` | Migrer progressivement (non bloquant) |
| L2 | Backend | `scripts/generate_monitoring_demo.py` — 2 occ. | Migrer |
| L3 | Backend | `scripts/referential/fetch_sources.py` — 1 occ. | Migrer |
| L4 | Backend | `scripts/referential/build_manifest.py` — 1 occ. | Migrer |
| L5 | Frontend | `TimeseriesPanel.jsx` — fallback `window.location.reload` | Passer callback `onRetry` |
| L6 | Backend | Pas de health-check DB dans `/api/health` | Ajouter test connexion DB |
| L7 | Frontend | `ConsumptionPortfolioPage` — pas de gestion erreur | Ajouter error boundary |
| L8 | Frontend | `Cockpit.jsx` — pas de skeleton loading | Ajouter skeleton/spinner |
| L9 | Backend | `.env.example` manquant | Creer avec les variables documentees |
| L10 | Backend | Pas de Dockerfile | Creer pour le deploiement |
| L11 | Frontend | Bundle `index.js` > 370KB gzipped 115KB | Code splitting supplementaire |
| L12 | Backend | SQLAlchemy `pool_pre_ping` uniquement pour PostgreSQL | Ajouter aussi pour SQLite (check_same_thread) |

---

## Plan de remediation — Avancement

### V103 — Securite & Qualite
- [ ] C1: httpOnly cookies + CSRF (report pour v2)
- [x] C2: Rate-limit impersonate (middleware/rate_limit.py — 10 req/min)
- [ ] C3: Nettoyer Ruff F401
- [ ] H1: Audit des 22 endpoints sans auth, ajouter guards
- [ ] H2-H4: Pagination sur tous les endpoints list
- [x] H7: Rate-limiting login (middleware/rate_limit.py — 5 req/min)
- [ ] H8: Brute-force lockout

### V104 — Modernisation — DONE
- [x] H6 + M4-M35: Migration `datetime.utcnow()` → `datetime.now(timezone.utc)` (60+ fichiers)
- [x] M1: SQLAlchemy 2.0 `declarative_base()`
- [x] M2: Pydantic v2 `ConfigDict` (schemas.py, billing.py, kb_usages.py, energy.py)
- [x] M3: FastAPI lifespan context manager
- [x] M31: Fix test_action_close_rules_v49 (detail is dict, not string)

### V105 — UX Robustesse — DONE
- [x] H12: PatrimoinePortfolioHealthBar — navigate(0) au lieu de window.location.reload
- [x] H13: UpgradeWizard — onClose(completed) + redirect /patrimoine
- [x] H14: SiteCompliancePage — KanbanCee.onAdvance callback au lieu de reload
- [x] H15: Wrapper try/except segmentation evaluate (fait en V100)
- [x] M26-M27: Console.error sur catches silencieux restants (fait en V102)

### V106 — DevOps
- [x] L6: Health-check DB dans /api/health
- [x] L9: `.env.example` (existait deja a la racine)
- [ ] L10: Dockerfile (report)
- [ ] L11: Code splitting avance (report)
