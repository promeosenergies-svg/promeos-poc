# Heritage debt audit — branche refonte Lot 6

> **Date de création** : 2026-04-19 (fin Phase 5 Lot 6)
> **Origine** : test suite complète `npx vitest run` révèle 1 failure pré-existant hors scope Phase 5

## Régression unique restante

### `src/__tests__/formatGuard.test.js · C. Source guard .toFixed()` — baseline dépassée

**Assertion** : `moins de 40 fichiers avec .toFixed() (baseline avant migration complète)` · **Reçu** : `45 fichiers` (expected < 40).

**Pré-existant** : confirmé via `git stash` en fin de Phase 5 (stash du WIP Phase 5, run test → même 45 violations). **N'est pas introduit par** les commits Phase 5.

**Cause** : le test impose un plafond décroissant (`.toFixed() < 40 fichiers`, `< 120 occurrences`) pour forcer la migration progressive vers `fmtNumber` / `fmtPercent` / `fmtEuro` (helpers `frontend/src/ui/format.js`). La baseline a été fixée lors d'un sprint antérieur, mais la migration effective de `.toFixed()` a dérivé de 40 → 45 fichiers au fil des développements (Pilotage, Billing, Achat entre autres).

**Hors scope Lot 6** : aucun fichier des paths Phase 5 (`compliance-pipeline/` + `CompliancePipelineSol.jsx` + `CompliancePipelinePage.jsx`) n'utilise `.toFixed()`. Le fix consiste à migrer les 45 fichiers vers les helpers `fmtXxx` puis durcir la baseline à `< 30` → `< 20` → `< 10`, ce qui dépasse le scope refonte Sol.

**Priorité** : P3 hygiène — à planifier dans un sprint "migration formatters" dédié (~1-2 h de sweep mécanique + un commit par batch de 10 fichiers pour review incrémentale).

**Doc de référence** : `frontend/src/ui/format.js` + convention `fmtNumber(value, { digits })` / `fmtPercent(value, { digits })` / `fmtEuro(value)` (voir `docs/audit/format-migration-plan.md` si existe ou à créer).

## Heritage debt notable, NON-bloquant Phase 5

### Build heap OOM (Vitest + Vite build)

**Observation** : `npx vitest run` sans `NODE_OPTIONS=--max-old-space-size=6144` saturé le heap V8 (~1.4 GB OOM) sur les 68 fichiers de test du repo, triggered par le worker pool threads.

**Workaround retenu** (Phase 4 + Phase 5) : préfixer `NODE_OPTIONS=--max-old-space-size=6144` pour les runs full-repo. `6144` suffit, `8192` avait timeout sur RAM physique 8 GB saturée.

**Cause racine hypothèse invalidée** (circular barrel `ui/sol/index.js`) : documentée Phase 4 dans `docs/audit/build_heap_diagnostic_lot6.md`. Cause réelle suspectée = composants legacy très volumineux (MonitoringPage.jsx 3134 LOC, PatrimoinePage.jsx 2284 LOC, Site360Page.jsx 2200 LOC) chargés simultanément par Vitest transform. Fix proposé = splitting pages legacy en composants distincts, hors scope Lot 6.

**Priorité** : P3 — workaround heap suffisant, pas bloquant tests CI.
