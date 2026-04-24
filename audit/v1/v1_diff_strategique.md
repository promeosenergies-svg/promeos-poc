# V1.D — Diff stratégique MAIN vs REFONTE SOL

**Date**: 2026-04-24

## 1. Contexte branches

- **Commits ahead/behind** : `origin/main` = 0, `origin/claude/refonte-visuelle-sol` = **119 commits ahead**
- **Divergence** : 2026-04-18 14:30:14 (premier commit refonte)
- **Dernier commit refonte** : 2026-04-24 07:28:14
- **Durée totale** : **5.7 jours** — effort très concentré (~21 commits/jour)
- **Auteurs** : Amine Ben Amara 118 commits (99.2%) · promeosenergies-svg 1 (0.8%)

**Monoauteur, structuré par phases.**

## 2. 119 commits groupés par thème

### A. Navigation / Routing / Panel / Rail (11)
Deep-links, registry, permission mapping, legacy redirects. Exemples : `feat(nav): vague 1 deep-links`, `refactor(nav): rename PANEL_SECTIONS → PANEL_DEEP_LINKS`, `feat(sol-panel): locked badge`, `feat(nav): add 6 missing admin items`, `fix(nav): map /conformite/aper-legacy + anti-drift invariant`.

### B. Accessibilité / A11y (5)
WCAG, keyboard nav, contrast, skip links, focus rings. Exemples : `fix(a11y): P0 locked items accessibility + WCAG contrast`, `fix(a11y): add focus-visible rings`, `feat(a11y): keyboard nav Up/Down/Home/End`, `fix(a11y): P1 Escape + hit area + live region + skip link mobile`.

### C. Refonte visuelle / Design System (3)
Palette Sol, typo, CSS tokens. Exemples : `feat(refonte-visuelle): initial Sol aesthetic applied globally` (8d1e873e), `esprit maquette V2 raw`, `charts repeints palette Sol`.

### D. Composants fondateurs Sol — Phases 0→5 (8)
- P0 : audit read-only
- P1 : 8 composants Sol patterns V2 raw
- P2 : CockpitSol + 3 modes + presenters purs + fallbacks
- P3 : SolAppShell global + panelSections + KPI semantic
- P4 : propagation Conformite/BillIntel/Patrimoine
- P5 : charts repeints palette Sol

### E. Lots 1–3 : Pages par pattern (~35 commits)
**Lot 1 Pattern A (dashboards narratifs)** : CommandCenterSol, AperSol, MonitoringSol
**Lot 2 Pattern B (listes drillables)** : 4 composants + AnomaliesSol, ContratsSol, RenouvellementsSol, UsagesSol, UsagesHorairesSol, WatchersSol
**Lot 3 Pattern C (fiches détail)** : 4 composants + Site360Sol, RegOpsSol, EfaSol, DiagnosticConsoSol

### F. Lot 6 Conformité Tertiaire (4)
ConformiteTertiaireSol hero Pattern A, conformite_presenters (10 helpers), source-guards TDD.

### G. Phase 4 & 5 Conformité Pipeline (10)
Source-guards TDD + pipeline_presenters (44 vitest tests) + CompliancePipelineSol Pattern B + glossary +5 + business_errors +3.

### H. Tests & qualité (6)
Nav invariance guard, dynamic invariants, Python 3.11 compat (78 failures fixed), source-guards EnergySignatureCard/LoadProfileCard.

### I. CI / Polish (15)
prettier --write 67 files, ruff format, wait-on 30→60s, e2e smoke fixes, axios timeout 15s, NBSP FR, redirect path login preserved, site-compliance score /100, -9 LOC simplify.

### J. Audits & docs (15)
12 bilans + 11 audits + screenshots 160+.

### K. Data / YAML / Backend (2)
ATRD7 GRDF grille 1/07/2026 (Z=+5,87%), biométhane + stockage + coef A + composition prix repère gaz.

## 3. Diff de fichiers

**Total** : **412 fichiers** (318 ajoutés A + 94 modifiés M)
**Lignes** : **+35 636 / -2 950** = **+32 686 net**

### Top 15 fichiers par LOC

| Fichier | Type | Insert | Suppr | Net |
|---------|------|--------|-------|-----|
| `frontend/src/pages/__tests__/sol_presenters.test.js` | A | 1470 | 0 | +1470 |
| `frontend/src/index.css` | M | 1003 | 6 | +997 |
| `frontend/src/ui/sol/__tests__/sol_components.source.test.js` | A | 960 | 0 | +960 |
| `frontend/src/pages/CockpitSol.jsx` | A | 608 | 0 | +608 |
| `frontend/src/layout/SolAppShell.jsx` | A | 608 | 0 | +608 |
| `frontend/src/i18n/business_errors.js` | A | 605 | 0 | +605 |
| `frontend/src/pages/SolShowcase.jsx` | A | 544 | 0 | +544 |
| `frontend/src/pages/Contrats.jsx` | M | 582 | 0 | +582 |
| `frontend/src/pages/CompliancePipelinePage.jsx` | M | 486 | 0 | +486 |
| `frontend/src/pages/RegOps.jsx` | M | 446 | 0 | +446 |
| `docs/design/SOL_MIGRATION_GUIDE.md` | A | 387 | 0 | +387 |
| `frontend/src/pages/WatchersPage.jsx` | M | 356 | 0 | +356 |
| `frontend/src/ui/sol/SolExpertGridFull.jsx` | A | 291 | 0 | +291 |
| `frontend/src/layout/NavRegistry.js` | M | 210 | 0 | +210 |
| `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` | M | 224 | 1082 | **-858** |

### Répartition par domaine

- **Frontend pages Sol** : ~6 000 LOC (15 pages × 200-600)
- **Frontend UI Sol** : ~5 500 LOC (30+ composants × 20-400)
- **Tests frontend** : ~2 500 LOC (sol_presenters, component tests, nav tests)
- **CSS / tokens** : ~1 100 LOC (index.css + tokens.css)
- **Docs / bilans / audits** : ~3 000 LOC (12 docs, 70+ screenshots)
- **Backend tests** : ~500 LOC (2 new source-guards + Python 3.11 compat)
- **YAML config** : ~100 LOC (ATRD7 + biométhane)
- **Backend code** : **minimal ~250 LOC** (tests + tweaks mineurs)

### Fichiers critiques (CLAUDE.md) touchés ?

| Fichier | Modifié ? |
|---------|-----------|
| `backend/regops/scoring.py` | ✓ NON |
| `backend/services/consumption_unified_service.py` | ✓ NON |
| `backend/config/emission_factors.py` | ✓ NON |
| `backend/config/tarifs_reglementaires.yaml` | ⚠ OUI (+100 LOC ATRD7/biométhane, **zéro logique**) |
| `backend/utils/naf_resolver.py` | ✓ NON |
| `backend/services/demo_seed/orchestrator.py` | ✓ NON |
| `backend/services/compliance_score_service.py` | ✓ NON |

**Verdict** : Aucune logique métier backend touchée. Seul YAML tarifaire mis à jour (données, zéro logique).

## 4. Zoom nav / layout / theme

### Layout
- `AppShell.jsx` (legacy) : **NON modifié**
- `SolAppShell.jsx` : **NOUVEAU +608 LOC** (rail + panel + timerail footer)
- `Breadcrumb.jsx` : légère maj (support SolBreadcrumb)
- `NavRegistry.js` : **+210 LOC** (routes mapping + deep-links + legacy redirects)
- `permissionMap.js` : **NOUVEAU +52 LOC** (PERMISSION_KEY_MAP)

### Routing (App.jsx)
**+144 LOC** : routes redirects + lazy-load Sol + legacy fallbacks
- `/` → CommandCenterSol
- `/cockpit` → CockpitSol
- `/conformite` → ConformiteSol
- `/patrimoine` → PatrimoineSol
- `/achat-energie` → AchatSol
- `/monitoring` → MonitoringSol
- Tous legacies accessibles via `-legacy`

### Tokens / Theming
- `index.css` : **+1003 LOC** (import `ui/sol/tokens.css` + overrides Tailwind massifs + palette slate/warm + Fraunces/Inter/FiraCode)
- `ui/sol/tokens.css` : **NOUVEAU +82 LOC** (custom properties `--sol-bg-canvas`, `--sol-ink-900`, `--sol-accent-warm`)

### Composants UI Sol ajoutés (30+)
Header/Voice · Data display · Hero/Narrative · Charts · Navigation · Pattern C/B · Overlays · Primitives.

### Détection structurelle
- ✓ Composants ajoutés : 30+
- ✓ Composants renommés : aucun (legacy/new coexistent)
- ✓ Composants supprimés : aucun (backward compat)
- ✓ Pages ajoutées : 20+ (`*Sol.jsx`)
- ✓ Routes restructurées : mineures (legacy redirects)

## 5. Pages métier migrées (21/21)

| Module | Legacy | Sol | Status |
|--------|--------|-----|--------|
| Cockpit | `/cockpit-legacy` | `/cockpit` (CockpitSol) | ✓ Migré |
| Patrimoine | `/patrimoine-legacy` | `/patrimoine` (PatrimoineSol) | ✓ |
| Conformité DT | `/conformite-legacy` | `/conformite` (ConformiteSol) | ✓ |
| Conformité Tertiaire | (legacy) | ConformiteTertiaireSol | ✓ Nouveau Pattern A |
| APER | `/conformite/aper-legacy` | `/conformite/aper` (AperSol) | ✓ |
| Diag Consom | (legacy) | DiagnosticConsoSol | ✓ Pattern A |
| Usages | (legacy) | `/usages` (UsagesSol) | ✓ Pattern A |
| Usages Horaires | (legacy) | `/usages-horaires` (UsagesHorairesSol) | ✓ |
| Anomalies | (legacy) | `/anomalies` (AnomaliesSol) | ✓ Pattern B |
| Contrats | (legacy) | `/contrats` (ContratsSol) | ✓ Pattern B |
| Renouvellements | (legacy) | `/renouvellements` (RenouvellementsSol) | ✓ Pattern B |
| Achat | `/achat-energie-legacy` | `/achat-energie` (AchatSol) | ✓ Pattern A |
| Billing | `/billing` | BillIntelSol | ✓ Pattern A |
| Monitoring | `/monitoring-legacy` | `/monitoring` (MonitoringSol) | ✓ Pattern A |
| Compliance Pipeline | (legacy) | CompliancePipelineSol | ✓ Pattern B |
| KB Explorer | (legacy) | KBExplorerSol | ✓ Pattern B |
| CommandCenter | `/home-legacy` | `/` (CommandCenterSol) | ✓ Pattern A |
| RegOps | (legacy) | `/regops` (RegOpsSol) | ✓ Pattern C |
| EFA | (legacy) | `/efa` (EfaSol) | ✓ Pattern C |
| Site360 | (legacy) | `/site360` (Site360Sol) | ✓ Pattern C |
| Watchers | (legacy) | `/watchers` (WatchersSol) | ✓ Pattern B |
| Segmentation | (legacy) | SegmentationSol | ✓ Pattern A |

**Couverture 21/21**. **Risque régression** : moyen (besoin e2e exhaustif).

## 6. Tests impactés (38 fichiers)

### Frontend vitest
- `sol_presenters.test.js` : **+1470 LOC** (44 units)
- `sol_components.source.test.js` : **+960 LOC** (source guards 30+ composants)
- `SolPanel.focus_rings.test.js` (+53), `.keyboard.test.js` (+74), `.locked.test.js` (+100), `.permissions.test.js` (+73), `.tracker.test.js` (+119)
- `layout/__tests__/` : 7 nouveaux (`admin_routes_coverage`, `permissionMap`, `route_module_map_invariant`, `skip_link`, deep-links gates)

### Backend pytest
- `test_no_compliance_logic_in_frontend_conformite.py` : **NEW +126 LOC**
- `test_no_compliance_logic_in_frontend_pipeline.py` : **NEW +142 LOC**
- `test_migration_mac.py` : +78 fixes (Python 3.11)
- 20+ autres : fixtures tweaks

### Estimation
- Tests nouveaux : ~2 500 LOC
- Tests cassés probables : ~15 (Python 3.11, fixed commit `11795c3f`)
- Tests supprimés : 0
- **Couverture nette AUGMENTE significativement**

## 7. Docs & seed modifiés

### 12 docs + 160+ screenshots A/B (~3 000 LOC)
- `docs/design/SOL_MIGRATION_GUIDE.md` (387 LOC, 6 patterns A/B/C)
- `docs/design/SOL_WIREFRAME_SPEC.md` (403 LOC)
- `docs/design/BILAN_LOT_1/2/3.md` (135/267/122 LOC)
- `docs/design/BILAN_PHASE_2/3/4.5/5.md` (162/138/175/160 LOC)
- `docs/BACKEND_TODO_REFONTE.md` (296 LOC)
- `docs/REFONTE_FEATURES_PARKED.md` (45 LOC)
- `docs/audit/*.md` (1500 LOC, 11 audits)
- Screenshots : 160+ PNG, ~30 MB, 22 pages × 2 versions × 2 folds + 31 smoke

### Seed
`backend/services/demo_seed/**` : **NON modifié** ✓. Seed HELIOS/MERIDIAN compatibles.

## 8. Risques de merge

| Zone | Risque | Likelihood | Mitigation |
|------|--------|-----------|-----------|
| `App.jsx` routing | MOYEN | 5/10 | Merge en dernier, après vérif routes main |
| `index.css` 1003 LOC | MOYEN | 6/10 | Cherry-pick refonte CSS après main CSS |
| `NavRegistry.js` +210 | FAIBLE | 3/10 | Merge direct OK |
| `tarifs_reglementaires.yaml` +100 | FAIBLE | 2/10 | Orthogonal |

### Divergences structurelles (non-conflits mais risques logiques)
- `CompliancePipelinePage.jsx` +486 LOC (perte possible si main modifie)
- `RegOps.jsx` +446 LOC
- `Contrats.jsx` +582 LOC

**Verdict** : **3-5 conflits texte** attendus, tous résolubles.

## 9. Analyse qualitative commits

### 10 commits divergence (2026-04-18)
Démarrage **architecturé** : audit P0 read-only → composants P1-P2 → propagation P3-P5.

### 20 commits récents (2026-04-24)
**Stabilisation** : A11y hardening P0/P1, nav anti-drift, polish, analytics instrumentation. Aucun revert majeur.

### Métrique de maturité

| Signal | Score |
|--------|-------|
| Audits P0→P5 | ✓✓✓ |
| Tests TDD source-guards | ✓✓✓ |
| A11y P0/P1 fixes | ✓✓✓ |
| Reverts (1 annulé) | ✓ |
| Smoke tests 28+ étapes | ✓✓✓ |
| Code polish | ✓✓ |
| Docs (12 bilans) | ✓✓✓ |

**Verdict** : Refonte **mature, en phase de hardening final** (pas expérimental, pas WIP).

## 10. Verdict préliminaire

### Ampleur
**MASSIVE** — 119 commits · 35K+ LOC · 412 fichiers · 21/21 pages.

### Zone d'impact
**Visuel + Navigation + Structure** :
- Visuel : palette Sol, Fraunces, 30 composants UI
- Nav : SolAppShell rail+panel, deep-links, permissions
- Structure : 6 patterns A/B/C, presenters purs
- Backend : **0 logique métier** (zéro risque SoT)

### Risques régression
1. A/B routes : 20+ `-legacy` + nouvelles → collisions lazy-load
2. CSS cascade : 1K+ override peut affecter composants legacy
3. Test suite : 2500 LOC nouveaux mais tests legacy peut-être oubliés
4. Découverte pages : 21 pages ; risque silencieux
5. A11y P2 non audité WCAG complet

### Recommandation préliminaire
**MERGER AVEC CONDITIONS FORTES** :
1. E2E exhaustif (28+ smoke steps rejouées post-merge)
2. Audit WCAG AA complet
3. Merge staging → develop → 2-3 jours → main
4. Rollback prêt (`-legacy` routes conservées 4+ semaines)

**Non-régressif backend** + **modérément risqué frontend UX** (pages multiples, design nouveau).
**Refonte = stabilisée, pas expérimentale.**

## Commandes validation rapide

```bash
# Aucune logique métier critique changée
git diff origin/main...origin/claude/refonte-visuelle-sol -- \
  backend/services/scoring.py \
  backend/config/emission_factors.py \
  backend/services/compliance_score_service.py

# App.jsx routing
git diff origin/main...origin/claude/refonte-visuelle-sol -- frontend/src/App.jsx | head -200

# Pages migrées
git diff --name-only origin/main...origin/claude/refonte-visuelle-sol | grep "Sol\.jsx$" | wc -l

# Dry-run merge
git merge --no-commit --no-ff origin/claude/refonte-visuelle-sol
git merge --abort
```
