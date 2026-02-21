# CHANGELOG

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
