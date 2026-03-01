# CHANGELOG

## [Unreleased] — 2026-03-01

### V88 — Quality Gate (P0/P1/P2) — Overlays, Lint Zero, Perf Memoization

**P0 — Overlays (fix/p0-overlays-vague1):**
- `Tooltip.jsx` : migration vers `TooltipPortal` wrapper — corrige le clipping par stacking contexts CSS
- `Modal.jsx` / `Drawer.jsx` : z-index standardise a z-200 (etait z-50/z-[999]/z-[9999])
- `ScopeSwitcher.jsx` : dropdown via `createPortal(…, document.body)` + `position:fixed z-[9990]`

**P1 — Qualite (fix/vague2-p1-quality):**
- `ScopeSummary` : suppression du doublon dans `components/` — source unique dans `layout/ScopeSummary.jsx`
- Tooltips consolides : `TooltipPortal` + `InfoTip` comme composants uniques, anciens `Tooltip`/`InfoTooltip` migres
- `useActivationData` hook : deduplique les fetches d'activation sur 6+ pages (etait copie-colle)
- ESLint 211→0 warnings : `--max-warnings=0` dans `package.json`
  - 170 `no-unused-vars` corriges (imports supprimes, vars prefixes `_`)
  - 40 `react-hooks/exhaustive-deps` resolus (eslint-disable ou useMemo)
  - 1 `no-useless-escape` corrige

**P2 — Perf & Hygiene (fix/vague3-p2-perf):**
- `ui/Badge` partage : remplace les `<span>` inline dans SiteDetail.jsx et Site360.jsx
- Dead code : `Cockpit2MinPage.jsx` supprime (330 lignes, jamais importe) + route `/cockpit-2min`
- Performance memoization :
  - `HeatmapChart.jsx` : `React.memo` + `Map` index (O(1) lookup vs O(n) `.find()` × 168 cellules)
  - `PortfolioPanel.jsx` : `MiniSparkline` + `RankingTable` en `memo`, sort pipeline `useMemo`
  - `ProfileHeatmapTab.jsx` : `HeatmapGrid` + `DailyProfileChart` en `memo`
  - `SignaturePanel.jsx` : prop stability (`setDrillDown` direct au lieu de `(cell) => setDrillDown(cell)`)
- Lazy-load : toutes les routes deja en `React.lazy` + `Suspense` — aucune action requise

**Tests:**
- Frontend : 3 665 passes (105 fichiers de test), 0 regression
- Backend : 2 400+ passes, 0 regression
- ESLint : 0 erreurs, 0 warnings

---

### V84 — Consumption Context V0 + ULTIMATE++ ScheduleEditor + UX Overlays

**Consumption Context V0 (Usages & Horaires):**
- Nouveau service `backend/services/consumption_context_service.py` :
  - `get_consumption_profile()` : heatmap 7x24, profil journee 24 pts, baseload Q10, peak P90, load_factor
  - `get_activity_context()` : SiteOperatingSchedule + archetype NAF + TOUSchedule actif
  - `get_anomalies_and_score()` : orchestration run_diagnostic() + ConsumptionInsight existants
  - `get_full_context()` : agregation complete
  - `compute_behavior_score()` : score 0-100 deterministe (4 penalites transparentes : hors-horaires 40pts, baseload 25pts, derive 20pts, weekend 15pts)
  - `detect_weekend_active()` : comparaison avg kWh weekend vs semaine avec seuils 0.5/0.8
  - `get_portfolio_behavior_summary()` : classement tous sites org par score ascending
- 6 routes `backend/routes/consumption_context.py` (prefixe `/api/consumption-context`) :
  - `GET /site/{id}`, `GET /site/{id}/profile`, `GET /site/{id}/activity`, `GET /site/{id}/anomalies`
  - `POST /site/{id}/diagnose`, `GET /portfolio/summary`
- 20 tests pytest `backend/tests/test_consumption_context.py` (A-E : score, weekend, profile, activity, API)
- Page `/usages-horaires` (ConsumptionContextPage.jsx) : 4 KpiCards + 2 tabs
  - Tab "Profil & Heatmap" (ProfileHeatmapTab.jsx) : HeatmapGrid 7x24, DailyProfileChart, BaseloadCard
  - Tab "Horaires & Anomalies" (HorairesAnomaliesTab.jsx) : ScheduleEditor, ArchetypeCard, ScoreBadge, AnomalyList, WeekendActiveAlert
- 6 fonctions API frontend (`getConsumptionContext`, `getConsumptionProfile`, `getConsumptionActivity`, `getConsumptionAnomalies`, `refreshConsumptionDiagnose`, `suggestSchedule`)
- `toUsagesHoraires()` dans routes.js, route React `/usages-horaires`, entree nav "Usages & Horaires"
- 44 tests vitest source-guard `consumptionContextV0.test.js`

**ULTIMATE++ — ScheduleEditor interactif:**
- `frontend/src/pages/consumption/ScheduleEditor.jsx` : edition inline des horaires (7 jours toggle Set, heure debut/fin, is_24_7, bouton "Suggestion NAF", save → PUT schedule + POST diagnose)
- Rafraichissement de la page via `onSaved` prop → `onRefresh={load}` dans ConsumptionContextPage

**Demo HELIOS canonique (V83):**
- Suppression complete de Groupe Casino : pack `packs.py`, `demo_templates.py`, `seed_casino.py`, `test_seed_casino.py`
- `dev_tools.py` reset_db reseed HELIOS (etait Casino)
- Defaults orchestrator + CLI : `--pack helios`
- Tests mis a jour : `test_demo_seed_packs.py` (TestSeedHeliosPack, 5 sites), `test_demo_manifest.py`, `test_compliance_bundle.py`
- `getAiExecBrief(orgId = null)` : suppression du org_id=1 hardcode
- `DemoScopeUltime.test.js` : heliosMock5 (5 sites), "Groupe HELIOS"

**UX Overlays (fix/ux-overlays):**
- `Tooltip.jsx` : early return si `!text` → pas de span invisible en DOM (zero point noir)
- `TooltipPortal.jsx` : guard dans `show()` callback, `text` ajoute aux deps useCallback
- `InfoTooltip.jsx` : `return null` apres useState si `!text`
- `ScopeSwitcher.jsx` : dropdown via `createPortal(…, document.body)` + `position:fixed z-[9990]` — corrige le clipping par le stacking context `backdrop-blur-md` du header sticky; `dropRef` exclu du outside-click handler

**Tests:**
- Frontend : 3 596 passes (105 fichiers de test), 0 regression
- Backend : 2 400+ passes, 0 regression

---

## [Unreleased] — 2026-02-18

### Quality Gate CI/CD — Front + Back + E2E

**Frontend:**
- Fixed broken ESLint config (`.eslintrc.js` ESM → `.eslintrc.cjs` CJS)
- Removed `|| exit 0` silencing ALL lint failures
- Fixed 7 ESLint errors: missing imports (ConsumptionDiagPage, ConsumptionExplorerPage), children prop (ExplorerChart)
- Added `format:check` script for CI
- ESLint now enforced with `--max-warnings=174` ceiling (ratchet down)

**Backend:**
- Added `pyproject.toml`: Ruff + Mypy + Pytest config
- Added `requirements-dev.txt`: ruff, mypy
- Fixed 6 Ruff errors: missing datetime import (alertes.py), bare except (audit_repo.py, rss_watcher.py), redundant import (consumption_diagnostic.py)
- Ruff: 0 errors (E, F, W, B rules)
- Mypy: 0 errors (280 source files, gradual mode)

**CI/CD:**
- `.github/workflows/quality-gate.yml`: 3-job pipeline (frontend, backend, e2e)
- Deleted 2 empty workflow files (backend-tests.yml, frontend-build.yml)
- `Makefile`: lint, test, typecheck, ci, e2e, dev, install targets

**E2E:**
- `e2e/`: Playwright smoke tests (health, login, dashboard)
- Isolated from frontend workspace (no browser download in unit test runs)

**Pre-commit:**
- Husky + lint-staged: ESLint+Prettier on .jsx, Ruff on .py
- `.husky/pre-commit` + `.lintstagedrc.json`

**Documentation:**
- `docs/quality-gate.md`: full pipeline docs + ratcheting strategy

| Métrique | Avant | Après |
|----------|-------|-------|
| ESLint errors | 7 (hidden) | 0 |
| Ruff errors | 6 | 0 |
| Mypy errors | 100+ | 0 (gradual) |
| CI pipeline | none | 3-job quality gate |
| Pre-commit | none | lint-staged |

---

### QW3-5: Accent Sweep — 90+ corrections across 24 files

**Batch A (8 fichiers, ~50 corrections):**
- ConsommationsUsages.jsx — 13 fixes (données, détecté, Résultats, génération…)
- ConsumptionExplorerPage.jsx — 10 fixes (données, énergie, énergétique, relevés…)
- WatchersPage.jsx — 10 fixes (événements, réglementaire, configuré, synthèses…)
- Patrimoine.jsx — 9 fixes (Conformité, détectée, Données, Décret, détail…)
- Site360.jsx — 7 fixes (Conformité, détectées, Évaluation réglementaire, Données…)
- ImportPage.jsx — 3 fixes (données démo, importées, affectées, relevés, météo…)
- BillIntelPage.jsx — 5 fixes (importée, générez, données démo, Génération, détectées)
- SiteDetail.jsx — 11 fixes (Conformité, Données, Décret, réglementaires, détectée, incohérence…)

**Batch B (8 fichiers, ~28 corrections):**
- AdminAuditLogPage.jsx — 2 fixes (événement, résultat)
- ConnectorsPage.jsx — 2 fixes (configuré, données, Météo-France)
- KBExplorerPage.jsx — 9 fixes (Réglementaire, chargée, données, résultat(s), mot-clé, découvrir, règles, décret, flexibilité)
- PurchaseAssistantPage.jsx — 4 fixes (terminée, détectée, résultat(s), Résultats, étape)
- PurchasePage.jsx — 2 fixes (données, résultats)
- NotificationsPage.jsx — 6 fixes (Conformité, Ignoré, Ignorées, sélectionnée, détecter, Réinitialiser)
- AdminUsersPage.jsx — 2 fixes (Conformité, résultat)
- ConsumptionDiagPage.jsx — 2 fixes (détectés, analysés)

**Batch C (8 fichiers, ~11 corrections):**
- AdminAssignmentsPage.jsx — 2 fixes (Conformité, données)
- CompliancePage.jsx — 3 fixes (Conformité réglementaire, Évaluation, Décret)
- Dashboard.jsx — 3 fixes (enregistré, énergétique, conformité réglementaire)
- StatusPage.jsx — 1 fix (données)
- ConsommationsPage.jsx — 1 fix (données énergie)
- Cockpit2MinPage.jsx — 1 fix (estimées, liées, conformité réglementaire)
- AdminRolesPage.jsx — 2 fixes (Conformité, rôles, système, être, modifiés, périmètre, accès, configuré)

**Guard tests: AccentSweepGuard.test.js — 37 tests source-level**
- 19 describe blocks couvrant les 24 fichiers modifiés
- Regex negatives: aucune régression possible sans casser un test

**Métriques:**

| Métrique | Avant | Après |
|----------|-------|-------|
| Tests | 943 | 986 (+43) |
| Build | 13.54s | 13.81s |
| Régressions | 0 | 0 |
| Fichiers touchés | 24 source + 1 test | |

---

### QW1+QW2: MonitoringPage cleanup + import hygiene

**Fichiers modifies (3 source + 1 test):**

#### MonitoringPage.jsx — 11 accents + 1 perf fix
- `Ecole` → `École`, `Hopital` → `Hôpital` (PROFILE_OPTIONS)
- `Resolu` → `Résolu` (drawer CTA + resolve handler)
- `Resolus` → `Résolus` (filter tab)
- `Resoudre` → `Résoudre` (table action button)
- `Severite` → `Sévérité` (table header)
- `detecter` → `détecter` (empty state)
- `resolution` → `résolution` (toast error)
- `defaut` → `défaut` (archetype fallback label)
- `recommandee` → `recommandée` (drawer empty state)
- Supprime `useMemo(() => mockSites, [])` inutile (constante statique)

#### Patrimoine.jsx — unused import
- Supprime `TrendingUp` (import lucide-react jamais utilise)

#### MonitoringPage.test.js — 8 guard tests
- Bloc `QW1 guard — MonitoringPage accents FR` (8 tests source-level)
- Protege contre regression des accents et du useMemo mort

**Metriques:**

| Metrique | Avant | Apres |
|----------|-------|-------|
| Tests | 935 | 943 (+8) |
| Build | 14.35s | 13.54s |
| Regressions | 0 | 0 |
