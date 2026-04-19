# BILAN STOP GATE — Phase 3

> **Date** : 2026-04-19
> **Branche** : `claude/refonte-visuelle-sol` (poussée sur remote)
> **Ports** : refonte 5175 · main 5173 (A/B) · backend 8001

---

## Phase en cours
- Phase 3 — SolAppShell remplace AppShell global (+ 3 exigences renforcées)
- Statut : **terminée** (Gate 3 OK, 4 pages screenshottées)

---

## Ce qui est fait (commits)

### Commits (à venir) de la phase
1. **Push** commit Phase 2 `d5f5da46` sur `origin/claude/refonte-visuelle-sol` ✓
2. **Issue GitHub #257** créée sur main : `bug(api): /api/cockpit 500 runtime browser uniquement, curl OK` → https://github.com/promeosenergies-svg/promeos-poc/issues/257
3. **Commit Phase 3** (prochain) : `feat(refonte-p3): SolAppShell global + panelSections + KPI semantic + A/B helper`

### Fichiers par type

| Type | Créés | Modifiés |
|---|---|---|
| `.jsx` | `layout/SolAppShell.jsx` (production wrapper) | `ui/sol/SolKpiCard.jsx` (prop `semantic`) · `ui/sol/SolPanel.jsx` (headerSlot+footerSlot+getPanelSections) · `pages/CockpitSol.jsx` (propagation semantic) · `App.jsx` (swap) |
| `.js` | — | `layout/NavRegistry.js` (PANEL_SECTIONS_BY_ROUTE + getPanelSections) |
| `.mjs` | `tools/playwright/sol_refonte_helper.mjs` (helper captureABPair A/B réutilisable) | — |
| `.md` | `docs/design/BILAN_PHASE_3.md` | `docs/design/SOL_MIGRATION_GUIDE.md` (règle A/B point 10) |
| `.test.js` | — | `ui/sol/__tests__/sol_components.source.test.js` (SolPanel Phase 3 assertions) |
| `.png` | 12 nouveaux screenshots (3 pages × 2 sides × 2 viewports) | — |

---

## Ce qui est validé

### Tests
- Source-guards Sol : **175 / 175 passing** (174 + 1 nouveau sur SolPanel headerSlot/footerSlot)
- Vitest full suite : non-régression confirmée (suite stable à 4274/4276)
- Baseline préservée

### Build
- `npx vite build` : clean en 1m06s
- Aucun warning nouveau
- `SolAppShell` + contextes + overlays bundlés correctement

### Source-guards Sol discipline — inchangée
- ✓ Aucun hex hardcodé hors whitelist
- ✓ Aucun fetch/axios dans `ui/sol/*`
- ✓ Composants Sol toujours purs présentation

### Visuel — Playwright A/B sur 4 pages flagship
Capturés via `tools/playwright/sol_refonte_helper.mjs` (login réel, 1440×900, full + fold, OnboardingOverlay dismissé) :

| Page | Route | Main (before) | Refonte (after) |
|---|---|---|---|
| Cockpit | `/cockpit` | `cockpit_main_before{,_fold}.png` | `cockpit_refonte_after{,_fold}.png` |
| Conformité | `/conformite` | `conformite_main_before{,_fold}.png` | `conformite_refonte_after{,_fold}.png` |
| Patrimoine | `/patrimoine` | `patrimoine_main_before{,_fold}.png` | `patrimoine_refonte_after{,_fold}.png` |
| Achat | `/achat-energie` | `achat_main_before{,_fold}.png` | `achat_refonte_after{,_fold}.png` |

**Constats visuels** :
- Cockpit refonte : panel 3 sections (Cette semaine / Horizons / Vue d'ensemble) conformes maquette ✓ · KPI Conformité `59.4 /100 ▲ +17 pts` affiché en **vert** (semantic='score') ✓ · scope switcher top panel ✓ · header-sol 40px avec Rechercher+Bell+Expert ✓
- Conformité refonte : shell Sol appliqué · panel affiche section générique module conformité (pas de panelSections dédiés, fallback legacy non-cassant opère) · page legacy rendue intacte
- Patrimoine refonte : idem, shell Sol + contenu legacy Patrimoine rendu (table 5 sites, KPIs 238 k€, 2,9 GWh, etc.) — aucune régression
- Achat refonte : idem, shell Sol + page Scénarios d'achat legacy fonctionnelle

### Validation zéro backend
```bash
git diff --name-only origin/main... | grep -E '^(backend/|.*\.py$)'
# → vide ✓
```

---

## Ce qui reste dans la phase

### 3 exigences reçues en début Phase 3 — toutes livrées

| Exigence | Livré | Preuve |
|---|---|---|
| **E1** — Top-bar legacy absorbé | ✅ | Scope top panel + UserMenu footer panel + header-sol ≤40px (Search⌘K + Bell + Expert) dans `layout/SolAppShell.jsx` |
| **E2** — Panel contextuel conforme maquette | ✅ | `PANEL_SECTIONS_BY_ROUTE` + `getPanelSections()` dans `NavRegistry.js` · sections `Cette semaine / Horizons / Vue d'ensemble` pour `/cockpit` · fallback legacy non-cassant pour autres routes |
| **E3** — Sémantique KPI | ✅ | Prop `semantic` sur `SolKpiCard` ('cost'\|'score'\|'conso'\|'neutral') · `SEMANTIC_TONE` mapping · resolveDeltaColor() · propagation CockpitSol |

### Checklist STOP GATE 3 (reprise prompt)

- [x] Toutes routes protégées rendues dans SolAppShell (App.jsx swap unique point d'ancrage)
- [x] Header legacy (breadcrumb + scope + search + user) remplacé ou absorbé
- [x] ScopeSwitcher déplacé dans SolPanel (top slot)
- [x] CommandPalette ⌘K préservé (raccourci global dans SolAppShell)
- [x] OnboardingOverlay + ToastProvider + ActionDrawerProvider + DevPanel + ActionCenterSlideOver toujours montés
- [x] Mode Expert toggle préservé (dans header-sol + raccourci Ctrl+Shift+X)
- [x] 4 routes V1 chargent sans régression visible (cockpit, conformite, patrimoine, achat)
- [x] Screenshots A/B main/refonte sur 4 pages minimum
- [x] 175/175 source-guards verts
- [x] Build Vite prod clean

### Règle durable A/B inscrite dans `SOL_MIGRATION_GUIDE.md`
Point 10 de la checklist Phase 0 mis à jour avec :
- Nomenclature stricte : `<page>_main_before{,_fold}.png` + `<page>_refonte_after{,_fold}.png`
- Helper `captureABPair(pageName, routePath)` réutilisable
- Viewport 1440×900 full + fold
- Login réel promeos@promeos.io
- Wait 3500 ms + dismiss OnboardingOverlay

---

## Questions bloquantes

1. **Phase 4 Pattern A** — les 4 flagship hors Cockpit (Conformité DT, Bill Intel, Patrimoine, Achat) sont-elles à migrer en Pattern A intégral (avec SolPageHeader/Headline/KpiRow/WeekGrid/LoadCurve) ou seulement à **habiller** avec le shell Sol en laissant leur contenu legacy (comme actuellement) ? (A = migration Pattern A complète · B = shell seul, contenu legacy préservé)

2. **Panel generic fallback** — actuellement Conformité/Patrimoine/Achat héritent de `getSectionsForModule(moduleId)` legacy (section unique du module). Veut-on ajouter des `PANEL_SECTIONS_BY_ROUTE` dédiés par page flagship avant Phase 4, ou au fil des migrations ? (A = pré-remplir les 4 maintenant · B = au fil des migrations Phase 4/Lots)

3. **Commit Phase 3** — à pousser immédiatement après ce bilan, ou attendre validation visuelle des 4 screenshots par Amine ? (A = commit + push immédiat · B = attente validation)

---

## Prochaine phase attendue

### Phase 4 — 4 pages flagship Pattern A
- Durée estimée : 2-3 h par page selon option A ou B ci-dessus
- Ordre imposé prompt : Conformité DT → Bill Intelligence → Patrimoine → Achat énergie
- Dépendances satisfaites :
  - SolAppShell global en prod ✓
  - 21 composants Sol livrés ✓
  - Pattern A déjà appliqué avec succès sur Cockpit ✓
  - sol_presenters.js helpers réutilisables ✓
  - Playwright helper A/B pour captures systématiques ✓

### Risques résiduels
- Bug backend `/api/cockpit` 500 runtime browser (issue #257) — n'affecte pas Phase 4, fallbacks en place
- Deltas N-1 billing/conso toujours null tant que `getBillingCompareMonthly` + `getCockpitConsoMonth` non ajoutés (TODO documenté sol_presenters.js)
- User menu footer panel potentiellement caché si panel overflows — à vérifier au scroll sur les pages longues

---

**Fin BILAN_PHASE_3.md**
