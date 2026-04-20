# Heritage debt audit — branche refonte Lot 6

> **Date de création** : 2026-04-19 (fin Phase 5 Lot 6)
> **Mise à jour** : 2026-04-20 — les 2 debts recensées sont **RÉSOLUES** (commit `4effc2f2`). Branche passe 185/185 files · 4670/4682 tests · 0 régression.

## ✅ Debt 1 résolue — `formatGuard.test.js · C. Source guard .toFixed()`

**Statut** : ✅ RÉSOLU (2026-04-20, commit `4effc2f2`)

**Assertion originale** : `moins de 40 fichiers avec .toFixed() (baseline avant migration complète)` · **Reçu avant fix** : `45 fichiers` · **Reçu après fix** : `35 fichiers` ✓.

**Fix** : migration batch de 10 fichiers easy-win `.toFixed()` → `fmtNum` / `fmtPct` (helpers `frontend/src/utils/format.js`, FR-aware, null-safe) :

|#|Fichier|Transformation|
|---|---|---|
|1|`src/pages/AchatSol.jsx`|`.toFixed(1)` → `fmtNum(v, 1)`|
|2|`src/pages/CommandCenterSol.jsx`|`.toFixed(1).replace('.', ',')` → `fmtNum(v, 1)`|
|3|`src/pages/PatrimoineSol.jsx`|`Math.abs(gap).toFixed(0)` → `fmtNum(..., 0)`|
|4|`src/pages/CockpitRefonte.jsx`|`(delta*100).toFixed(1)` → `fmtNum(delta*100, 1)`|
|5|`src/pages/AperPage.jsx`|`(ratio*100).toFixed(0)+'%'` → `fmtPct(ratio, true, 0)`|
|6|`src/pages/admin/CxDashboardPage.jsx`|`v.toFixed(1)` → `fmtNum(v, 1)`|
|7|`src/pages/achat/sol_presenters.js`|`Math.abs(trend).toFixed(1)` → `fmtNum(..., 1)`|
|8|`src/pages/cockpit/CockpitHeaderSignals.jsx`|`prixSignal.valeur?.toFixed(0)` → `fmtNum(..., 0)`|
|9|`src/components/MeterBreakdownChart.jsx`|`(percent*100).toFixed(0)%` → `fmtPct(percent, true, 0)`|
|10|`src/components/ScoreBreakdownPanel.jsx`|`contribution.toFixed(1)` → `fmtNum(..., 1)`|

**Bénéfices collatéraux** : localisation FR automatique (virgule décimale, NNBSP séparateur milliers), null/NaN safety via `_safe` guard interne, discipline Sol (pages Lot 6 exemplaires du pattern).

**Reste à migrer (backlog Lot 7+ refonte complète)** — 5 fichiers SKIP initial, 29 occurrences cumulées :

- ✅ `cockpit/MarketWidget.jsx` (6 occ) — **refonte Lot 7 livrée 2026-04-20** : `fmtNum` wiré, guards `data-testid` préservés, 20/20 tests verts.
- ✅ `purchase/MarketContextBanner.jsx` (6 occ) — **refonte Lot 7 livrée 2026-04-20** : rebuild in-place sur tokens Sol (`--sol-succes/calme/attention`), `fmtNum` sur trend + spot, `MarketContextCompact` conservé, 35/35 tests verts.
- ✅ `analytics/EnergySignatureCard.jsx` (6 occ) — **refonte Lot 7 livrée 2026-04-20** : `fmtNum` wiré sur R²/baseload/pentes/thermosens, pas de régression sur Site360.
- ✅ `analytics/LoadProfileCard.jsx` (6 occ) — **refonte Lot 7 livrée 2026-04-20** : `fmtNum` wiré sur 5 KPI tiles + tooltip + peak, pas de régression sur Site360.
- ⏳ `Site360.jsx` (5 occ, 2200 L hybride) — **reste backlog** : refonte Sol partielle (seul l'onglet Résumé via `Site360Sol.jsx` 251 L), 8 onglets legacy à refondre. Migration `.toFixed()` laissée en place pour absorption dans le sprint Site360 dédié.

**Baseline formatGuard durcie** : `< 40 fichiers` → **`< 35 fichiers`** ; `< 120 occurrences` → **`< 80 occurrences`**. État actuel : 32 fichiers · 63 occurrences. Prochain palier cible : `< 30 fichiers` après refonte Site360 + sweep restant.

## ✅ Debt 2 résolue — `glossaryExplain` entry overflow

**Statut** : ✅ RÉSOLU (2026-04-20, commit `4effc2f2`)

**Assertion** : entry `pipeline_applicability_frameworks` (`src/ui/glossary.js:834`) ajoutée Phase 5.4 faisait 310 chars (seuil 300 imposé par test guard).

**Fix** : raccourcie à 230 chars en préservant l'essentiel métier (seuils DT/BACS/APER + origine backend dérivée).

- **Avant** (310 chars) : _"Règles réglementaires applicables par site : Décret Tertiaire (surfaces ≥ 1 000 m²) · BACS (bâtiments tertiaires neufs ou CVC > 290 kW) · APER (parkings ≥ 1 500 m² ou toitures industrielles ≥ 500 m²). Booléens calculés backend à partir des attributs patrimoine (surface, puissance CVC, parking)."_
- **Après** (230 chars) : _"Règles applicables par site : Décret Tertiaire (≥ 1 000 m²) · BACS (CVC > 290 kW) · APER (parkings ≥ 1 500 m² ou toitures ≥ 500 m²). Booléens backend dérivés du patrimoine (surface, puissance CVC, parking)."_

## Heritage debt notable, NON-bloquant Phase 5

### Build heap OOM (Vitest + Vite build)

**Observation** : `npx vitest run` sans `NODE_OPTIONS=--max-old-space-size=6144` saturé le heap V8 (~1.4 GB OOM) sur les 68 fichiers de test du repo, triggered par le worker pool threads.

**Workaround retenu** (Phase 4 + Phase 5) : préfixer `NODE_OPTIONS=--max-old-space-size=6144` pour les runs full-repo. `6144` suffit, `8192` avait timeout sur RAM physique 8 GB saturée.

**Cause racine hypothèse invalidée** (circular barrel `ui/sol/index.js`) : documentée Phase 4 dans `docs/audit/build_heap_diagnostic_lot6.md`. Cause réelle suspectée = composants legacy très volumineux (MonitoringPage.jsx 3134 LOC, PatrimoinePage.jsx 2284 LOC, Site360Page.jsx 2200 LOC) chargés simultanément par Vitest transform. Fix proposé = splitting pages legacy en composants distincts, hors scope Lot 6.

**Priorité** : P3 — workaround heap suffisant, pas bloquant tests CI.
