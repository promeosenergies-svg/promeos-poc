# Brique Énergie P1 — Rapport de clôture (2026-05-30)

Sprint P1.S7 — polish transverse + provenance 100 % KPI. Ce rapport
clôture le cycle P1 Énergie (P0.S1a → P1.S7).

## 1. Endpoints livrés (6 endpoints orchestration `/api/energy/*`)

| Endpoint | Sprint | Service backend | KPI cardinaux |
|---|---|---|---|
| `GET /api/energy/synthesis` | P1.S2a | `energy_orchestration.synthesis.build_synthesis` | 10 KPI (consumption_kwh, cost_eur, co2_kg, peak_kw, weighted_price_eur_mwh, data_quality_score, sites_coverage_pct, alerts_open, actions_open, estimated_impact_eur) |
| `GET /api/energy/loadcurve` | P1.S2a | `energy_orchestration.loadcurve.build_loadcurve` | 4 KPI + série temporelle granularité validée |
| `GET /api/energy/week-profile` | P1.S2b | `energy_orchestration.week_profile.build_week_profile` | 4 KPI (highest_day, highest_hour, night_baseload_kw, weekend_consumption_pct) + matrix 7×24 |
| `GET /api/energy/cost-vs-contract` | P1.S2c | `energy_orchestration.cost_vs_contract.build_cost_vs_contract` | 6 KPI + active_contract + price_decomposition[] + scenarios[4] + recommendation |
| `GET /api/energy/market-exposure` | P1.S2d | `energy_orchestration.market_exposure.build_market_exposure` | 8 KPI + top_expensive_hours[] + favorable_hours[] + baseload_comparison + simulation |

Standardisation transverse :
- Schémas Pydantic `EnergyKpi`, `EnergyProvenance`, `EnergyScope`, `EnergyPeriod`, `EnergyErrorPayload`.
- `EnergyProvenance` : `source` + `service` + `formula` + `period` (requis) + `confidence` + `assumptions` (déclarés).
- `EnergyErrorPayload` : `code` + `message` + `hint` + `correlation_id` (UUID v4 ou header X-Correlation-Id / X-Request-Id / X-Trace-Id).

## 2. Vues UI livrées (5 vues principales)

| Route | Sprint | Composant orchestrateur | Composants UI réutilisés |
|---|---|---|---|
| `/monitoring` (synthesis) | P1.S3b | `MonitoringSynthesisStrip` | `KpiCardWithProvenance` ×10 + `NarrativeBanner` + `WarningsBanner` + `ApiErrorState` |
| `/consommations/courbe` | P1.S3a | `LoadCurveTab` | `EnergyFilterBar` + `LoadCurveChart` + `TopPeaksTable` + `KpiCardWithProvenance` ×4 |
| `/usages?tab=semaine-type` | P1.S4 | `WeekProfileTab` | `WeekProfileHeatmap` (7×24 sparse) + `KpiCardWithProvenance` ×4 + `SiteRequiredState` |
| `/consommations/cout-contrat` | P1.S5 | `CostContractTab` | `CostVsContractCard` (4 scénarios) + `PriceDecompositionTable` + `KpiCardWithProvenance` ×6 + `SiteRequiredState` + `EnergyCrossLinks` |
| `/consommations/marche` | P1.S6 | `MarketExposureTab` | `ExposureScoreGauge` + `BaseloadComparisonCard` + `TopExpensiveHoursTable` + `FavorableHoursPanel` + `DisplacementSimulationCard` + `KpiCardWithProvenance` ×8 + `SiteRequiredState` + `EnergyCrossLinks` |

Pattern composant autonome (loading / empty / error / partial) appliqué uniformément sur les 5 vues.

## 3. Tests verts

| Suite | Total | Notes |
|---|---|---|
| Vitest frontend | **1903 / 1903** ✅ (3 skipped pré-existants) | 8 nouvelles suites Énergie P1.S3a→S7 ; pas de régression brique Énergie ni hors brique |
| Pytest source-guards Energy subset | **52 / 52** ✅ | `frontend_no_business_calc` (3) + `energy_orchestration_provenance` (42, dont 17 ajoutés P1.S7) + `cdc_timezone_paris` (3) + `market_price_canonical` (4) |
| Playwright pack final S7 | **7 / 7** ✅ (15.5 s avec auth setup) | 5 routes capturées + provenance vérifiée + fix UX scope vérifié + rail intact |
| Playwright e2e ciblés | **5/5 + 5/5 + 4/4** ✅ | `p1_loadcurve` + `p1_market_exposure` + `p1_week_profile` |

## 4. État provenance KPI

Couverture provenance **100 %** sur les KPI exposés par les 6 endpoints `/api/energy/*` :

- ✅ Chaque `EnergyKpi` exigé par le schéma porte une `EnergyProvenance` requise (`source`/`service`/`formula`/`period`).
- ✅ Champs `confidence` + `assumptions` déclarés sur `EnergyProvenance` (test source-guard `TestProvenanceCoveragePolishP1S7`).
- ✅ Réponse racine de chaque endpoint expose `provenance` obligatoire.
- ✅ Sous-objets non-KPI portent aussi `provenance` : `EnergyPriceComponent`, `EnergyContractScenario`, `EnergyContractSummary`, `EnergyExpensiveHour`, `EnergyFavorableHour`, `EnergyBaseloadComparison`, `EnergyDisplacementSimulation`, `EnergyMarketContext` (12 sous-types vérifiés par source-guard P1.S7).

Couverture provenance **frontend** (testée via `EnergyProvenanceCoverage.test.jsx`) :
- ✅ Les 5 Tabs orchestrateurs importent `KpiCardWithProvenance`.
- ✅ Les composants UI dédiés exposent leur propre tooltip provenance via `data-testid` :
  - `ExposureScoreGauge` → `exposure-score-provenance`
  - `BaseloadComparisonCard` → `baseload-provenance`
  - `TopExpensiveHoursTable` → `top-hour-provenance`
  - `PriceDecompositionTable` → `price-component-provenance`
  - `CostVsContractCard` → `scenario-provenance` (ajouté P1.S7)
  - `DisplacementSimulationCard` → `simulation-provenance` (ajouté P1.S7)
  - `WeekProfileHeatmap` → `heatmap-provenance`

## 5. Dette restante

### Dette technique applicative

| Dette | Statut | Cible | Justification |
|---|---|---|---|
| `confidenceDisplay.js` dans HELPER_WHITELIST | **Justifié P1.S7 — Option B** | P2.1 MonitoringPage split | Utilisé uniquement par `MonitoringPage:1905-1919` (`climateConf` scatter + `qualityConf`). Climate scatter pas couvert par `/api/energy/synthesis`. Modifier MonitoringPage interdit par brief P1.S7. |
| Climate scatter Monitoring hors `energy_orchestration` | **Hors scope P1** | P2.1 endpoint `/api/energy/climate-scatter` | Reste exposé par services legacy Monitoring (r² + n_points). Migration backend reportée. |
| HELPER_WHITELIST applicative à 3 entrées | **Acceptable** | P2.1 → 2 entrées (retrait `confidenceDisplay.js`) | `co2.js` + `scopedAggregates.js` documentés (helpers ADEME V23.6 + agrégats scope FE). |
| MarketPrice legacy table preservée | **Acceptable** | Migration progressive P2 | Brief P1.S7 : « Ne pas dropper MarketPrice legacy ». `mkt_prices` canonique utilisé partout dans `energy_orchestration`. |

### Dette UX

| Dette | Statut |
|---|---|
| Cross-links Énergie → Conformité Décret Tertiaire | **Dette P2** — pas ajouté en P1.S7 ; route `/conformite/tertiaire` existe mais l'angle est plus naturel depuis `/usages` (Pilotage des usages) qui a déjà sa logique métier propre. |
| Cross-link Action V4 depuis `/monitoring` | **Dette P2** — interdit par « ne pas refondre MonitoringPage ». |
| Cross-links Énergie depuis `/consommations/courbe` et `/usages?tab=semaine-type` | **Dette P2** — pas d'action métier directe associée (vues d'analyse seulement). |

### Dette tests

| Dette | Statut |
|---|---|
| `WeekProfileTab` et `CostContractTab` mockent `react-router-dom.Link` via `vi.importActual` | **OK** — pattern test propre. |
| Tests `MonitoringPage.test.js` continuent à tester `computeConfidence` | **OK** — sera nettoyé P2.1 lors du retrait. |

## 6. Recommandation P2

Phase P2 — recommandations issues du polish P1.S7 :

1. **P2.1 MonitoringPage split** (climat scatter backend) — endpoint `/api/energy/climate-scatter` + composant `MonitoringClimateStrip` + retrait `confidenceDisplay.js` de HELPER_WHITELIST.
2. **P2.2 Cross-links transverses étendus** — Énergie → Conformité (depuis `/usages` Décret Tertiaire) + Énergie → Action V4 (depuis `/monitoring` post-split).
3. **P2.3 Migration progressive `MarketPrice` legacy** — purge table + source-guard renforcé sur `mkt_prices` canonique.
4. **P2.4 Source-guard composant FE** — vérifier statiquement que tout composant `frontend/src/ui/energy/*` qui accepte une prop `kpi` ou `provenance` la rend visiblement (sinon raise warning CI).
5. **P2.5 Performance** — audit bundle size brique Énergie (12 nouveaux composants UI + 5 Tabs lazy-loaded) ; vérifier qu'aucune route Énergie ne dépasse 250 kB gzipped.

## 7. Verdict note actuelle / cible

### Note actuelle brique Énergie P1 : **9 / 10**

| Critère | Note | Justification |
|---|---|---|
| Endpoints orchestration livrés | 10 / 10 | 5/5 endpoints livrés + schémas Pydantic + erreurs standardisées |
| Vues UI livrées | 10 / 10 | 5/5 vues principales livrées + pattern uniforme |
| Provenance 100 % KPI | 10 / 10 | 100 % côté backend (source-guard 42 tests) + 100 % côté frontend (tooltips) |
| Doctrine zéro calcul métier FE | 10 / 10 | HELPER_WHITELIST applicative à 3 entrées documentées + source-guards verts |
| Microcopy FR cohérente | 9 / 10 | Variants contextuels homogènes + tests `EnergyMicrocopy.test.jsx` |
| UX scope-site-required | 10 / 10 | Pattern uniforme 3 onglets + tests vitest + Playwright |
| Cross-links transverses | 7 / 10 | Sobre sur 2 vues (Coût & contrat + Marché) ; dette P2 pour Conformité + Action |
| Rail NavRegistry intact | 10 / 10 | 0 nouvelle entrée rail sur 7 sprints |
| Pas de promesse d'économie | 10 / 10 | Warning « Simulation indicative » obligatoire + hardcodé fallback |
| Régression sur sprints précédents | 10 / 10 | Smoke visuel 5 routes verts post-chaque-merge |
| Tests automatisés | 9 / 10 | 1903 vitest + 52 source-guards + Playwright pack final 7/7 |

### Note cible post-P2 : **10 / 10**
- Retrait `confidenceDisplay.js` (P2.1) → HELPER_WHITELIST 2 entrées
- Cross-links Conformité + Action depuis vues clés (P2.2) → 10/10 sur cet axe
- Migration MarketPrice legacy (P2.3) → harmonisation finale schémas

### Verdict global

🟢 **GO clôture P1 Énergie** — La brique Énergie est démontrable, fiable, cohérente et audit-ready. Tous les critères de la DoD P1.S7 sont satisfaits :

- ✅ KPI traçables (provenance 100 %)
- ✅ Microcopy homogène (audit cross-fichiers vitest)
- ✅ États UX propres (loading / empty / error / partial / site-required)
- ✅ Zéro calcul métier frontend (source-guards 52/52)
- ✅ Aucune route/menu inutile (rail intact sur 7 sprints)
- ✅ Aucune promesse d'économie certaine (warnings hardcodés fallback)

La phase P2 peut démarrer en confiance sur la base P1 close.

---

## Annexe — Timeline complète P1 Énergie

| Sprint | PR | Tip refonte-sol2 post-merge | Safety tag |
|---|---|---|---|
| P0.S1a | (pré-cycle) | — | — |
| P0.S1b | (pré-cycle) | — | — |
| P0.S1c | (pré-cycle) | — | — |
| P1.S2a | (pré-cycle) | — | — |
| P1.S2b | (pré-cycle) | — | — |
| P1.S2c | (pré-cycle) | — | — |
| P1.S2d | (pré-cycle) | — | — |
| P1.S3a | (pré-cycle) | — | — |
| P1.S3b | #334 | `a230b61b` | `safety/refonte-sol2-post-p1-s3b-a230b61b` |
| P1.S4 | #335 | `d7522ba6` | `safety/refonte-sol2-post-p1-s4-d7522ba6` |
| P1.S5 | #337 | `96242460` | `safety/refonte-sol2-post-p1-s5-96242460` |
| P1.S6 | #338 | `17955ecc` | `safety/refonte-sol2-post-p1-s6-17955ecc` |
| **P1.S7** | **(en cours)** | **(à venir)** | **(à venir)** |

Rapport généré le 2026-05-30 dans le cadre du sprint P1.S7.
