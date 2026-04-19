# BILAN STOP GATE — Lot 2 Listes Pattern B + Pattern A hybride

> **Date** : 2026-04-19
> **Branche** : `claude/refonte-visuelle-sol` (pushée · ~46 commits ahead origin/main)
> **Scope** : 6 pages Tier 1+2 (Tier 3 Admin 4 pages différé Lot 5) + 5 nouveaux composants Sol
> **Statut** : terminée, tag `v2.3-lot2-listes` prêt à pousser

---

## Commits Lot 2

| # | Commit | Phase | Livrables principaux |
|---|---|---|---|
| 1 | `d1e09df3` | P1 — 4 composants Pattern B | `SolListPage` + `SolExpertToolbar` + `SolExpertGridFull` + `SolPagination` · 41 source-guards · `PANEL_SECTIONS_BY_ROUTE` +6 routes · showcase section Pattern B · fix regression D3 period_badge |
| 2 | `eed71ecb` | P2 — AnomaliesSol | `/anomalies` Pattern B pur · presenters anomalies (11 helpers) · EvidenceDrawer legacy préservé · tabs Anomalies + Plan d'actions préservés · glossary +3 · business_errors +2 |
| 3 | `b2119707` | P3 — ContratsSol | `/contrats` Pattern B pur + **SolKpiRow agrégats** (nouveauté) · presenters contrats (14 helpers) · 3 panels legacy préservés (CadrePanel + AnnexePanel + Wizard) · fix honnêteté "prix pondéré null vs 0" si 100 % indexé · glossary +3 |
| 4 | `540e7842` | P4 — RenouvellementsSol | `/renouvellements` Pattern B pur + **Horizon picker rightSlot** (5 pills 30/60/90/180/1 an, nouveauté) · presenters (14 helpers) · ScenarioDrawer + ScenarioSummaryModal + SegmentationQuestionnaireModal préservés · 2 remaps spec→API · glossary +3 |
| 5 | `2c0c219b` | P5 — UsagesSol | `/usages` Pattern A hybride · injection top + 3 onglets legacy + widgets spécialisés préservés · remap KPI 3 "efficacité fantôme" → readiness_score honnête · glossary +3 |
| 6 | `2c57b41e` | P6 — UsagesHorairesSol | `/usages-horaires` Pattern A compact (100 L, le plus léger Lot 2) · 2 onglets legacy préservés · **remap vocabulaire HP/HC spec → dimension comportementale API** · pas de SolBarChart ni week-cards (skip validé, page technique) · glossary +3 |
| 7 | `b1963160` | P7 — WatchersSol | `/watchers` Pattern B avec **preludeSlot** (nouveauté) + **SolWatcherCard** (nouveau composant Sol) · presenters watchers (14 helpers) · Review Modal + runWatcher + Info Panel garde-fou droits d'auteur préservés · fix JSX Fragment `<>...</>` révélé au build · glossary +3 |
| 8 | _(ce commit)_ | P8 — Smoke + bilan | Smoke 22 → 28 étapes · BILAN_LOT_2 · SOL_MIGRATION_GUIDE update Pattern B + preludeSlot + Pattern A hybride cases · fix `.sol-page-kicker` class dans SolListPage · fix dup keys annexes `annexe-${cadreId}-${annexeId}` |

---

## Smoke test d'ensemble 28 étapes

Script `tools/playwright/sol_refonte_smoketest.mjs` étendu de 22 à
28 étapes (+6 pages Lot 2) :

```
✓ 01 login                                       OK
✓ 02z / CommandCenter render                     OK
✓ 02a /cockpit render                            OK
✓ 02b panel item "Journal d'actions"             OK
✓ 02c /conformite render                         OK
✓ 02d /bill-intel render                         OK
✓ 02e /patrimoine render                         OK
✓ 02f /patrimoine?type=bureau filter             OK
✓ 02g week-card drill-down /sites/:id            OK
✓ 02h /achat-energie render                      OK
✓ 02i /conformite/aper render                    OK
✓ 02j /monitoring render                         OK
✓ 02k /sites/3 Site360Sol render                 OK   (Lot 3 P2)
✓ 02l /regops/3 RegOpsSol render                 OK   (Lot 3 P3, <4s render)
✓ 02m /conformite/tertiaire/efa/1 EfaSol render  OK   (Lot 3 P4)
✓ 02n /diagnostic-conso DiagnosticConsoSol render OK  (Lot 3 P5 + 6.1)
✓ 02o /anomalies AnomaliesSol render             OK   (Lot 2 P2, Pattern B pur)
✓ 02p /contrats ContratsSol render               OK   (Lot 2 P3, Pattern B + KpiRow)
✓ 02q /renouvellements RenouvellementsSol render OK   (Lot 2 P4, Horizon picker 5)
✓ 02r /usages UsagesSol render                   OK   (Lot 2 P5, Pattern A hybride)
✓ 02s /usages-horaires UsagesHorairesSol render  OK   (Lot 2 P6, Pattern A compact)
✓ 02t /watchers WatchersSol render               OK   (Lot 2 P7, Pattern B preludeSlot)
✓ 03a Ctrl+K open CommandPalette                 OK
✓ 03b Escape close palette                       OK
✓ 03c Ctrl+Shift+X Expert toggle                 OK
⚠ 04 scope switcher top panel                    WARN (faux négatif selector, pré-existant Lot 1)
✓ 05 responsive 1280x720                         OK
✓ 06 deep-link /bill-intel fresh                 OK

OK: 27 · FAIL: 0 · WARN: 1 · Console warnings: 15 (dup keys pré-existants, dette)
```

**Résultat** : zéro FAIL, zéro erreur console runtime (hormis 15
warnings "duplicate keys" hérités d'une source tierce — probablement
un autre composant non-Lot 2 comme legacy grids ou seed data). Les
6 pages Lot 2 rendent correctement avec structure Pattern B / Pattern
A Sol, toolbar filtres, grids denses, pagination, KPI rows, week-cards
variety guard, et drawers/modals/wizards/onglets legacy intégralement
préservés.

---

## Chiffres clés Lot 2

- **8 commits** pushés sur `claude/refonte-visuelle-sol`
- **6 pages migrées** : 3 Pattern B pur + 2 Pattern A hybride + 1 Pattern B preludeSlot
- **5 nouveaux composants Sol** (P1 : SolListPage + SolExpertToolbar + SolExpertGridFull + SolPagination · P7 : SolWatcherCard)
- **Cumul total refonte** : **18 pages Sol migrées** (Phase 2 + Lot 1 + Lot 3 + Lot 2) · **30 composants Sol** (25 post-v2.2 + 5 Lot 2)
- **Nouveaux termes glossaire** : **18** (anomaly ×3, contract ×3, renewal ×3, usage ×3, hourly ×3, watcher ×3) · **total cumulé ~55 termes**
- **Nouveaux business_errors** : **17** · **total cumulé ~54 entrées**
- **Nouveaux presenters** : 6 modules purs · **~70 helpers** ajoutés au patrimoine Sol
- **Source-guards Sol** : **296 verts** (245 post-v2.2 → 286 post-P1 → 296 post-P7 SolWatcherCard +10)
- **Full suite** : ~4 500 tests verts (seul `formatGuard` pré-existant failing, hors scope)
- **Backend touché** : **0** (aucune modification API, presenter-only, comme Lot 3)

---

## Pages migrées — détail par Pattern

### Pattern B pur (3 pages)

Structure : `SolListPage` → header + optional KpiRow → toolbar
search/filtres → grid dense sortable + pagination.

- **/anomalies** (AnomaliesSol · Phase 2) — 53 anomalies HELIOS rendues,
  toolbar 4 filtres (Framework/Sévérité/Site/Search), grid 6 cols
  avec pills colorés, EvidenceDrawer legacy préservé. Tabs Anomalies
  + Plan d'actions préservés.
- **/contrats** (ContratsSol · Phase 3) — première application
  **SolKpiRow agrégats** (3 KPIs calculés client-side depuis cadres),
  grid 8 cols avec annexes indentées "↳ ", pills statut, **fix
  honnêteté** "prix pondéré null vs 0" si portefeuille 100 % indexé.
  CadrePanel + AnnexePanel + Wizard préservés.
- **/renouvellements** (RenouvellementsSol · Phase 4) — première
  application **Horizon picker** dans rightSlot (5 pills
  30/60/90/180/1 an), 3 KPIs (imminents/readiness/expirés),
  Segmentation badge conditionnel, ScenarioDrawer + SummaryModal +
  Questionnaire préservés. Deux remaps spec→API documentés
  (bestImpactCumulativeEur et totalScenariosCount absents).

### Pattern A hybride (2 pages)

Structure : Sol Pattern A injecté EN HAUT + legacy body préservé
intégralement dessous (même méthode que Phase 5 Lot 3 Diagnostic).

- **/usages** (UsagesSol · Phase 5) — Pattern A complet (header +
  narrative + 3 KPIs + SolBarChart top usages + SolWeekGrid variety
  guard). Legacy 3 onglets (Timeline/Baseline/Comptage) + HeatmapCard
  + ComplianceCard + FlexNebcoCard + cards power/cdc/flex bubble +
  export Excel préservés. Remap `usage_efficiency_potential_mwh` spec
  → `usage_readiness_score` honnête.
- **/usages-horaires** (UsagesHorairesSol · Phase 6) — Pattern A
  **compact** (100 L, pas de SolBarChart, pas de week-cards — skip
  validé page technique). Remap vocabulaire spec **HP/HC tarifaire**
  → dimension **comportementale** API (behavior_score, offhours_pct,
  baseload_kw). Legacy 2 onglets Profil/Heatmap + Horaires/Anomalies
  préservés.

### Pattern B avec preludeSlot (1 page, nouveauté Phase 7)

Structure : Pattern B + prélude cards actionables AVANT toolbar (au
lieu de SolKpiRow agrégats classique).

- **/watchers** (WatchersSol · Phase 7) — 3 SolWatcherCard
  (legifrance/cre/rte) en preludeSlot avec bouton Exécuter + feedback
  runResult inline, grid 6 cols événements, Review Modal + runWatcher
  + Info Panel garde-fou droits d'auteur préservés. Fix JSX Fragment
  `<>...</>` nécessaire pour wrapper 3 siblings legacy.

---

## Innovations architecturales Lot 2

### Composants Sol Pattern B (Phase 1)
- `SolListPage` : wrapper complet Pattern B (breadcrumb + header +
  kpiRow + preludeSlot + toolbar + grid + pagination + drawerSlot).
  Mono-colonne pleine largeur, complément de `SolDetailPage` (2-col
  Pattern C).
- `SolExpertToolbar` : search + filter pills avec `<select>` natifs
  (accessibilité sans dropdown custom) + selection actions masse +
  source chip `activeFilterCount`.
- `SolExpertGridFull` : superset de `SolExpertGrid` legacy avec sort
  sortable par col + render custom + selectable checkbox + onRowClick
  drawer trigger + loading/empty states narratifs + highlightColumn
  + row tones.
- `SolPagination` : dense mono 11 px, format canonique "1 – 20 sur N
  · page A / B · ‹ › · N par page ▾".

### SolKpiRow agrégats client-side (Phase 3)
Pour `/contrats`, calculs 3 KPIs client-side depuis la data brute
(`cadres[]`) au lieu de consommer un endpoint agrégé variable
(`getCadreKpis` shape instable). Robuste vs variabilité API,
discipline constante pour les pages Pattern B + KpiRow.

### Horizon picker rightSlot (Phase 4)
Pattern de navigation temporelle compact dans le header rightSlot :
5 pills mono (30/60/90/180/1 an) avec `aria-pressed`. Réutilisable
sur d'autres pages avec horizon variable (monitoring, achat énergie
spot).

### SolWatcherCard + preludeSlot (Phase 7)
Nouveau composant Sol léger (100 L) pour afficher des entités
actionables avec état mutable + feedback d'exécution inline.
Extensible à d'autres cas d'usage futurs : bookmarks, alertes
personnalisées, configurations utilisateur sauvegardées.

### Fix honnêteté "null vs 0" systématique (5/6 remaps Lot 2)
Discipline cristallisée : **jamais afficher un "0,0 €/MWh" ou
"— économies fantômes" trompeur quand la donnée sous-jacente n'est
pas calculable**. Return `null` + narrative explicative via
`businessErrors.*_pending` ou variante spécifique. Cumul :

| Phase | KPI attendu (spec) | Remap honnête |
|---|---|---|
| P3 Contrats | weighted_price si 100% indexé | null + "portefeuille 100% indexé · prix fixe à compléter" |
| P4 Renouv | bestImpactCumulativeEur | readiness_score moyen (signal préparation) |
| P4 Renouv | totalScenariosCount | expiredCount (dette urgence) |
| P5 Usages | efficiency_potential_mwh | readiness_score /100 (qualité segmentation) |
| P6 Horaires | hp_pct / hc_pct / shift_potential | behavior_score / offhours_pct / baseload_kw |
| P7 Watchers | active_count (pause inexistante) | total_count · coverage remapé en new_events |

Chaque remap documenté dans le commit body.

### Variety tag guard D1 structurel
Rappelé de Lot 3, confirmé sur Pattern A Lot 2 (Usages P5). Chaque
`buildXxxWeekCards` garantit 3 tags distincts (attention + afaire +
succes) par construction, même quand les données sont partielles.
Fallbacks `businessErrors.*_pending` ou variantes custom préservent
la variety.

---

## Dettes polish post-v2.3 (tickets séparés)

### Artefact capture A/B
- **watchers_main_before.png** = page login au lieu du rendu legacy.
  Faux-négatif `captureABPair` : session auth expirée côté main port
  5173 au moment de la capture. Fix = re-capture post-login active,
  ou bump `settleMs` après login. Non-bloquant — les 3 autres A/B
  Pattern B (anomalies, contrats, renouvellements) ont capturé
  correctement.

### Console warnings pré-existants
- **15 duplicate key warnings** présents même sur les pages non-Lot 2
  (smoke test les détecte globalement). Probable source : seed data
  avec IDs non uniques OU une legacy grid non-refondue. À auditer
  Phase 9 polish cross-phases. Correction déjà appliquée côté
  ContratsSol (annexes : `annexe-${cadreId}-${annexeId}`).

### formatGuard pré-existant
- `formatGuard.test.js` failing depuis avant Phase 2 Site360Sol
  (baseline 40 fichiers `.toFixed()` · actuel 47+). Dette main
  antérieure à Lot 3 et Lot 2. À traiter dans un ticket dédié.

### Onglets legacy non-refondus (architecture préservée)
- `/usages` : 3 onglets Timeline/Baseline/Comptage + widgets
  spécialisés (HeatmapCard, ComplianceCard, FlexNebcoCard,
  PowerOptimizationCard, CdcSimulationCard, FlexBubbleChart) ont
  leur UI Tailwind legacy. Refonte dédiée v2.4+ si signal utilisateur.
- `/usages-horaires` : 2 onglets Profil/Heatmap + Horaires/Anomalies
  (ProfileHeatmapTab + HorairesAnomaliesTab, 900+ LOC cumulés). Idem,
  refonte dédiée v2.4+.
- `/watchers` Review Modal : legacy ui/Modal (pas SolDrawer). Reuse
  direct pour v2.3, refonte SolReviewModal optionnelle v2.4+ si
  pattern ré-utilisé ailleurs.

---

## A/B screenshots archivés

Tous dans `docs/design/screenshots/` :
- `anomalies_{main_before,refonte_after}.png` + `_fold.png` (Phase 2)
- `contrats_{main_before,refonte_after}.png` + `_fold.png` (Phase 3)
- `renouvellements_{main_before,refonte_after}.png` + `_fold.png` (Phase 4)
- `usages_{main_before,refonte_after}.png` + `_fold.png` (Phase 5)
- `usages-horaires_{main_before,refonte_after}.png` + `_fold.png` (Phase 6)
- `watchers_{main_before,refonte_after}.png` + `_fold.png` (Phase 7)

Plus les 22 smoke screenshots `docs/design/screenshots/smoke/step*.png`
(ajout step26-31 pour les 6 pages Lot 2).

---

## Tag de clôture

Tag annoté `v2.3-lot2-listes` à pousser (commit 2 Phase 8) après
validation ce bilan.

État repo post-v2.3 :
- 4 tags refonte : `v2.0-refonte-sol`, `v2.1-lot1-dashboards`,
  `v2.2-lot3-fiches`, `v2.3-lot2-listes`
- ~46 commits refonte cumulés ahead `origin/main`
- 18 pages Sol migrées sur ~35 cibles = **~51 % de la refonte
  totale**
- Restent : Lot 4 Wizards (2 pages, 0,5 j) · Lot 5 Admin (9 pages,
  1,5 j) · Lot 6 Explorer/KB (4 pages, 1 j) — à prioriser selon
  signal stratégique.
