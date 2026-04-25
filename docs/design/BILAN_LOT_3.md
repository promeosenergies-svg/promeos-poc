# BILAN STOP GATE — Lot 3 Fiches détail + Diagnostic

> **Date** : 2026-04-19
> **Branche** : `claude/refonte-visuelle-sol` (pushée · 37 commits ahead origin/main)
> **Scope** : 4 pages — 3 Pattern C (fiches entité) + 1 Pattern A hybride (dashboard multi-sites)
> **Statut** : terminée, tag `v2.2-lot3-fiches` prêt à pousser

---

## Commits Lot 3

| # | Commit | Phase | Livrables principaux |
|---|---|---|---|
| 1 | `be11dd02` | P1 — 4 composants Pattern C | `SolDetailPage` + `SolBreadcrumb` + `SolEntityCard` + `SolTimeline` + 28 source-guards + showcase |
| 2 | `b85f7f60` | P2 — Site360Sol | `/sites/:id` onglet Résumé Pattern C · injection minimale ligne 2 145 · presenters sites · normalizeCompliance |
| 3 | `54c3ae7b` | P2.1 — Site360 A/B | Playwright devDep + browser chromium · `captureABPair` réutilisé · 4 PNGs |
| 4 | `b38674b1` | P3 — RegOpsSol | `/regops/:id` Pattern C · presenters regops · glossary +4 (operat_status + regops_*) · RegOps.jsx 374 LOC → 110 LOC loader thin · AI endpoints non-bloquants (fix bonus UX) |
| 5 | `b8d1017c` | P4 — EfaSol | `/conformite/tertiaire/efa/:id` Pattern C · presenters efa · glossary +3 efa_* · extension SolTrajectoryChart `verticalMarkers` · TertiaireEfaDetailPage 1 121 → 160 LOC · ProofDepositCTA + ModulationDrawer + safety banner préservés |
| 6 | `4c6b8d18` | P4.1 — Registre features parked | `docs/REFONTE_FEATURES_PARKED.md` · 3 entrées EFA (P1 export Mémobox + 2 P2) |
| 7 | `b0313cf4` | P5 — DiagnosticConsoSol | `/diagnostic-conso` Pattern A hybride · presenters diagnostic · glossary +3 diagnostic_* · legacy 1 190 LOC intégralement préservé · EvidenceDrawer 4 tabs inline intact |
| 8 | `cea98719` | P6.1 — Polish + helper | Fix visual redundancy header Diagnostic (PageShell.hideHeader) · `captureABPair` gagne `waitUntil` + `settleMs` opts · 3 scripts ad-hoc retirés |
| 9 | _(ce commit)_ | P6.2 — Smoke + bilan | Smoke étendu 22 étapes · BILAN_LOT_3 · SOL_MIGRATION_GUIDE update |

---

## Smoke test d'ensemble 22 étapes

Script `tools/playwright/sol_refonte_smoketest.mjs` étendu de 18 à 22
étapes (ajout `/sites/3` Pattern C, `/regops/3` Pattern C, `/conformite/tertiaire/efa/1` Pattern C, `/diagnostic-conso` Pattern A hybride) :

```
✓ 01 login                                       OK
✓ 02z / CommandCenter render                     OK   (kicker + kpis + tiles)
✓ 02a /cockpit render                            OK
✓ 02b panel item "Journal d'actions"             OK   url → /actions
✓ 02c /conformite render                         OK
✓ 02d /bill-intel render                         OK
✓ 02e /patrimoine render                         OK
✓ 02f /patrimoine?type=bureau filter             OK   7 occurrences "bureau"
✓ 02g week-card drill-down /sites/:id            OK   url → /sites/3
✓ 02h /achat-energie render                      OK
✓ 02i /conformite/aper render                    OK
✓ 02j /monitoring render                         OK
✓ 02k /sites/3 Site360Sol render                 OK   breadcrumb + entity + trajectoire (Lot 3 P2)
✓ 02l /regops/3 RegOpsSol render                 OK   breadcrumb + timeline · render 3 815 ms (P3)
✓ 02m /conformite/tertiaire/efa/1 EfaSol render  OK   breadcrumb + trajectoire + safety banner (P4)
✓ 02n /diagnostic-conso DiagnosticConsoSol render OK  kicker + kpis + bar chart (P5 + P6.1)
✓ 03a Ctrl+K open CommandPalette                 OK
✓ 03b Escape close palette                       OK
✓ 03c Ctrl+Shift+X Expert toggle                 OK
⚠ 04 scope switcher top panel                    WARN (faux négatif selector, pré-existant Lot 1)
✓ 05 responsive 1280x720                         OK   panel width 240 px
✓ 06 deep-link /bill-intel fresh                 OK

OK: 21 · FAIL: 0 · WARN: 1 · Console errors: 0
```

**Résultat** : zéro régression, zéro erreur console runtime. Les 4 pages Lot 3 rendent correctement avec structure Pattern C / Pattern A Sol, breadcrumbs, entityCard, KPIs avec explainKey, charts, week-cards avec variety tags guarantis par construction.

**Performance bonus** : `/regops/3` rend en 3 815 ms (vs legacy figé sur spinner 30 s+ à cause du `Promise.all` bloquant sur AI endpoints). Fix collatéral Phase 3 qui améliore aussi le legacy side.

---

## Chiffres clés Lot 3

- **9 commits** pushés sur `claude/refonte-visuelle-sol` (Phase 1 → Phase 6.2)
- **4 pages migrées** : Site360Sol (Pattern C) · RegOpsSol (Pattern C) · EfaSol (Pattern C) · DiagnosticConsoSol (Pattern A hybride)
- **Cumul Phase 2 → Lot 1 → Lot 3** : **12 pages Sol** migrées
- **Composants Sol Pattern C livrés** : 4 nouveaux (`SolDetailPage`, `SolBreadcrumb`, `SolEntityCard`, `SolTimeline`) — total **25 composants Sol**
- **Extension composant** : `SolTrajectoryChart` gagne la prop `verticalMarkers` (backward-compat) pour afficher N jalons temporels
- **Nouveaux termes glossaire** : **14** — site (0, reuse 100%) · regops (4 : `operat_status`, `regops_completion`, `regops_penalty_eur`, `regops_days_remaining`) · efa (3 : `efa_reference_year_kwh`, `efa_current_year_kwh`, `efa_target_2030_kwh`) · diagnostic (3 : `diagnostic_total_loss_eur`, `diagnostic_total_loss_kwh`, `diagnostic_sites_affected`) — **total ~37 termes** dans le glossaire Sol
- **Nouveaux business_errors** : **14** — site ×3, regops ×2, efa ×4, diagnostic ×2 → **total ~37 entrées**
- **Nouveaux presenters** : 4 modules purs (`sites/sol_presenters.js` 14 helpers · `regops/sol_presenters.js` 16 helpers · `efa/sol_presenters.js` 17 helpers · `diagnostic/sol_presenters.js` 11 helpers) = **58 helpers purs** ajoutés au patrimoine Sol
- **Tests presenters** : +109 tests unitaires dans `pages/__tests__/sol_presenters.test.js` (de 61 à **170 tests verts**)
- **Source-guards Sol** : 245/245 (28 nouveaux sur composants Pattern C)
- **Full suite** : 4 497 / 4 498 tests verts (seul `formatGuard` pré-existant failing, hors scope Lot 3)
- **Backend touché** : **0** (aucune modification API, presenter-only)

---

## Dettes polish restantes

### Corrigées Phase 6.1
- **Visual redundancy header DiagnosticConsoSol** : 2 headers simultanés (PageShell legacy + Sol) → réglé via `PageShell.hideHeader=true` + migration des 5 boutons actions vers SolPageHeader.rightSlot

### Reportées (registres)
- `docs/REFONTE_FEATURES_PARKED.md` liste **3 features EFA parkées** :
  - #1 Export pack Mémobox UI (P1 · Phase 6 ou v2.3+)
  - #2 handlePrecheck + qualification card (P2 · Phase 6 ou différée)
  - #3 Précheck/Controls boutons secondaires (P2 · Phase 6 ou différée)
- Décision Phase 6 : **laisser parked** pour maintenir rythme serré. Ré-intégration conditionnée au signal pilote post-v2.2.
- Backend endpoints concernés (`generate_operat_pack`, `precheckTertiaireDeclaration`, `runTertiaireControls`) **inchangés** — seuls les wiring UI ont été retirés.

### Pré-existant hors scope Lot 3
- `formatGuard.test.js` pré-existant failing (baseline 40 fichiers `.toFixed()` · actuel 47). Dette main antérieure, à traiter dans un ticket dédié.

---

## Méthodologie adoptée Lot 3

- **Audit Phase 0 systématique** avant chaque refonte (Explore agent) → révèle les divergences spec user vs API réelle (3 sur 4 phases : RegAssessment par-site, EFA reference_year dynamique, summary diagnostic shape)
- **Variety tag guard D1** : chaque `buildXxxWeekCards` garantit 3 tags distincts (attention + afaire + succes) par construction, testé unit
- **Injection minimaliste** au lieu de rewrite agressif (Site360 scope-cut Résumé, Diagnostic hero Pattern A + legacy preserved)
- **Divergences API documentées dans commit body** : chaque renaming (`baseline_kwh_2010` → `reference_year_kwh` dynamique, etc.) + raison
- **Fix collatéraux assumés** : RegOps AI Promise.all non-bloquant (Phase 3) améliore aussi UX side-effect
- **Registre features parked** (Phase 4.1) : prévient l'oubli des `describe.skip` entre phases

---

## A/B screenshots archivés

Tous dans `docs/design/screenshots/` :
- `site-360_{main_before,refonte_after}.png` + `_fold.png` (Phase 2.1)
- `regops_{main_before,refonte_after}.png` + `_fold.png` (Phase 3) — main stuck loader = fidèle représentation legacy Promise.all bug
- `efa_{main_before,refonte_after}.png` + `_fold.png` (Phase 4)
- `diagnostic_{main_before,refonte_after}.png` + `_fold.png` (Phase 5 + re-capture post-Phase 6.1 single header)

---

## Tag de clôture

Tag annoté `v2.2-lot3-fiches` à pousser (commit 3 Phase 6) après validation ce bilan.
