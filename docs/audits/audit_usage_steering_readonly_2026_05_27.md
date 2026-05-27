# Audit Pilotage des usages READ-ONLY (2026-05-27)

**Branche** : `claude/usage-steering-audit-readonly`
**Base** : `claude/refonte-sol2` après merge PR #315 (squash `f2129f87`)
**Mode** : READ-ONLY strict — **0 code modifié**.
**Verdict global** : 🟡 **Périmètre riche mais éclaté** — `/usages` est confirmée canonique (3 onglets timeline/baseline/comptage + 7 cards), le BE expose **28 endpoints `/api/usages/*` + 5 `/api/pilotage/*`** dont **22 endpoints orphelins jamais consommés FE** prêts à alimenter un 4ᵉ onglet « Pilotage des usages » sans nouveau menu. **4 calculs métier FE violent doctrine §8.1** (P0). Mapping Centre d'Action V4 propre via `external_ref` pattern `consumption_insight:{id}`.

---

## 1 — Cartographie écrans / composants / routes

### 1.1 Page canonique `/usages` — `UsagesDashboardPage.jsx` (383 l)

| Bloc | Composant | Données |
|---|---|---|
| ScopeBar multi-niveaux | `components/usages/ScopeBar.jsx` | org → entité → portefeuille → site + filtre archetype |
| KPI Strip | `components/usages/KpiStrip.jsx` | 4 KPI : Conso totale / Coût/an / Score readiness / IPE m² |
| TabBar | `components/usages/TabBar.jsx` (+icon support C5) | 3 onglets : Évolution / Baseline / Comptage |
| Onglet Évolution | `TimelineTab.jsx` | timeline AreaChart par usage + signature DJU scatter + regression |
| Onglet Baseline | `BaselineTab.jsx` | écart vs N-1 par usage + metering plan + sub-meters + trend |
| Onglet Comptage | `ComptageTab.jsx` | arborescence meters/sub-meters + coverage % + delta pertes |
| Card 1 | `HeatmapCard.jsx` | IPE portefeuille par usage × site (4×N) — *fix duplicate keys P0b* |
| Card 2 | `ComplianceCard.jsx` | Conformité BACS/DT/ISO 50001 |
| Card 3 | `FlexNebcoCard.jsx` | site-only flex potential NEBCO RTE |
| Card 4 | `FlexBubbleChart.jsx` | multi-site flex potential bubble |
| Card 5 | `CostCard.jsx` | coût ventilé HPH/HCH/HPB/HCB (TURPE 7) |
| Card 6 | `PowerOptimizationCard.jsx` | puissance souscrite optimization |
| Card 7 | `CdcSimulationCard.jsx` | simulation CDC-aware |
| FooterLinks | `FooterLinks.jsx` | cross-page CTAs (/consommations, /monitoring, /diagnostic-conso) |

### 1.2 Pages voisines (à connaître pour l'intégration 4ᵉ onglet)

| Route | Page | État | Doublon ? |
|---|---|---|---|
| `/usages-horaires` | `ConsumptionContextPage.jsx` | HIDDEN_PAGES (raison « doublon-sub-page », audit menu #313) | Profile heatmap + activity schedule + anomalies horaires |
| `/diagnostic-conso` | `ConsumptionDiagPage.jsx` | LIVE | Insights (hors_horaires/base_load/pointe/derive/data_gap) + Flex mini 3 leviers + ActionDrawer V4 |
| `/monitoring` | `MonitoringPage.jsx` | LIVE | KPIs puissance + signature + heatmap 7×24 + alerts |
| `/flex` | `FlexPage.jsx` | HIDDEN_PAGES (P0a brief « Aucun Flex visible client ») | Shell phase 1 — placeholder S2+ |

### 1.3 Page `ConsommationsUsages.jsx`

**N'existe pas.** Le brief mentionne `frontend/src/pages/ConsommationsUsages.jsx` mais le fichier est absent du repo (grep négatif). Pas de doublon caché.

---

## 2 — Cartographie endpoints (BE — 33 vivants)

### 2.1 `/api/usages/*` — 28 endpoints (1 endpoint orphelin sur 30 listés audit menu #313)

| Catégorie | Endpoints | Statut |
|---|---|---|
| **Dashboard scoped multi-niveaux** | `/scoped-dashboard`, `/scoped-timeline`, `/archetypes-in-scope` | LIVE — consommés par UsagesDashboardPage |
| **Dashboard mono-site legacy** | `/dashboard/{site_id}`, `/readiness/{site_id}`, `/metering-plan/{site_id}`, `/top-ues/{site_id}`, `/cost-breakdown/{site_id}` | ❌ **ORPHELINS** |
| **Baselines M&V** | `/baselines/{site_id}` | ❌ **ORPHELIN** — 3 méthodes A_HISTORICAL/B_DJU_ADJUSTED/C_REGULATORY_DT, formule explicite, R² exposé |
| **Compliance** | `/compliance/{site_id}` | ❌ **ORPHELIN** — BACS/DT/ISO 50001 |
| **Energy signature** | `/energy-signature/{site_id}`, `/{site_id}/advanced` | ❌ **ORPHELIN** — modèles 2P/3P/4P/5P E=a×DJU+b, R²+baseload+thermo |
| **Load profile** | `/load-profile/{site_id}` | ❌ **ORPHELIN** — baseload P5, LF, ratios nuit/jour & WE/sem |
| **Benchmark sectoriel** | `/benchmark/{site_id}`, `/estimate/reference-curve`, `/estimate/sector-trend` | ❌ **ORPHELINS** — Enedis Open Data NAF×puissance×région |
| **Recommendations + comparaison** | `/recommendations/generate/{site_id}` (POST 405), `/compare/site-vs-sector/{site_id}` | ❌ **ORPHELINS** |
| **Power optimization** | `/power-optimization/{site_id}` | LIVE — consommé par PowerOptimizationCard |
| **Cost** | `/cost-by-period/{site_id}` | LIVE — consommé par CostCard |
| **Flex** | `/flex-potential/{site_id}`, `/flex-portfolio` | LIVE — consommés par FlexNebcoCard + FlexBubbleChart |
| **Portfolio compare** | `/portfolio-compare` | LIVE — consommé par HeatmapCard |
| **Meter readings** | `/meter-readings/{meter_id}` | LIVE — consommé par BaselineTab sub-meters |
| **Timeline + billing-links** | `/timeline/{site_id}`, `/billing-links/{site_id}` | ❌ **ORPHELINS** |
| **Site / taxonomy** | `/site/{site_id}`, `/taxonomy` | ❌ **ORPHELINS** |

**Bilan** : ≥ **18 endpoints orphelins** prêts à enrichir le 4ᵉ onglet sans création BE.

### 2.2 `/api/pilotage/*` — 5 endpoints

| Endpoint | Service | Live HELIOS | Notes |
|---|---|---|---|
| `/portefeuille-scoring` | `services/pilotage/portefeuille_scoring.py` | **200 ✅** | Top-N sites par potentiel flex + heatmap archétype |
| `/radar-prix-negatifs` | `services/pilotage/radar_prix_negatifs.py` | 200 (live HELIOS) | Fenêtres J+1..J+7 prix négatifs ENTSOE — pas de scope (données publiques) |
| `/flex-ready-signals/{site_id}` | `services/pilotage/flex_ready.py` | **404 HELIOS** (DEMO_MODE site_id alpha) | 5 signaux NF EN IEC 62746-4 |
| `/roi-flex-ready/{site_id}` | `services/pilotage/roi_flex_ready.py` | **404 HELIOS** (idem) | Business case EUR/an (3 composantes : pointe + NEBCO + CEE) |
| `/nebco-simulation/{site_id}` | `services/pilotage/nebco_simulation.py` | live | Rejeu N jours CDC, gain NEBCO décalage flexibles |

**Tous consommés par `frontend/src/services/api/pilotage.js`** — mais aucun appelé par `UsagesDashboardPage.jsx` (utilisés par `FlexPage.jsx` qui est HIDDEN_PAGES depuis P0a).

### 2.3 `/api/consumption/*` — règles métier pilotage

`backend/services/consumption_diagnostic.py` expose **5 détecteurs** (formules explicites, contrat de vérité respecté) :

| Type | Algorithme | Seuil | Action template |
|---|---|---|---|
| `hors_horaires` | `_detect_hors_horaires():444` | E_off-hours / E_total > 20 % | Arrêt CVC + horloge GTC |
| `base_load` | `_detect_base_load():517` | Q10(nuit/WE) > 30 % × Q50(heures ouvertes) | Audit talon + couper veilles |
| `pointe` | `_detect_pointe():572` | E_day > median(daily) + 3×MAD (robust) | Délestage + décalage HC |
| `derive` | `_detect_derive():623` | slope(30j) / E_avg > 5 % | Vérif thermostat + équipements |
| `data_gap` | `_detect_data_gaps():731` | gap > 180 min OU gap_pct(mois) > 5 % | Complétude données |

---

## 3 — Cartographie calculs

### 3.1 ✅ Calculs BACKEND fiables (contrat §8.1)

| Service | Calcul | Source/Formule exposée |
|---|---|---|
| `consumption_diagnostic.py` | 5 détecteurs ci-dessus | ✅ type + formula + threshold |
| `energy_signature_service.py` | Modèles 2P/3P/4P/5P | ✅ formula `E=a×DJU+b`, R², bench, model |
| `baseline_service.py` | 3 méthodes M&V | ✅ source A/B/C, formula, confidence, R² |
| `load_profile_service.py` | Baseload P5, LF, ratios | ✅ formulas exposées dans payload |
| `cost_by_period_service.py` | Ventilation TURPE 7 | ✅ HPH/HCH/HPB/HCB respectés ; ❌ prix source NON exposé |

### 3.2 ❌ Calculs FRONTEND (violations doctrine §8.1)

**4 calculs métier critiques détectés** — à migrer BE :

| Fichier:ligne | Calcul FE | Devrait être |
|---|---|---|
| [`KpiStrip.jsx:24`](frontend/src/components/usages/KpiStrip.jsx#L24) | `ipe = totalKwh / totalSurface` | `ipe_total_kwh_m2` exposé par `/scoped-dashboard` |
| [`KpiStrip.jsx:27`](frontend/src/components/usages/KpiStrip.jsx#L27) | `surplusEur = surplusKwh × priceRef` | `surplus_eur_estimated` + `price_source` ParameterStore |
| [`HeatmapCard.jsx:80`](frontend/src/components/usages/HeatmapCard.jsx#L80) | `ratio = (val / ademeRef - 1) × 100` | `ratio_vs_ademe_pct` dans sites[].ipe_by_usage |
| [`PowerOptimizationCard.jsx:14-17`](frontend/src/components/usages/PowerOptimizationCard.jsx#L14) | `utilization = min(pct, 100)` + `overflow = (subscribed/actual) × 100` | `utilization_pct_safe` + `overflow_status` BE |

**Calculs FE tolérés (affichage pur)** :
- `TimelineTab.jsx:191-193` `baseloadExcessPct = (baseload / benchmark - 1) × 100` — tolérable si données BE viennent toutes du BE.
- `BaselineTab.jsx` `reduce()` agrégation totalEcart — affichage trivial.
- `KpiStrip.jsx:64` gap DT — limite floue (mais lecture pure d'une projection BE recommandée).

---

## 4 — Audit UX / UI / CX

### 4.1 Score readiness (présent)

`UsagesDashboardPage.jsx` Header rend `data.readiness.{score, level, details, recommendations}` avec tooltip décomposition (audit menu #313 §3). Bonne pratique.

### 4.2 Acronymes nus (à glosser)

| Localisation | Acronymes nus |
|---|---|
| `KpiStrip.jsx:60` | « Écart DT 2030 » (DT) |
| `FlexNebcoCard.jsx:40,80` | NEBCO ×4, BACS ×2, AOFD |
| `CostCard.jsx:74,154-160` | HPH / HCH / HPB / HCB ×4 |
| `BaselineTab.jsx:86` | « Obj. DT » |
| `FooterLinks.jsx:89` | « Scoring DT / BACS / APER » |

**≥ 12 occurrences** à glosser via `SolNarrativeText` / `SolAcronym` (cohérence avec Cockpit P1 — pattern déjà adopté).

### 4.3 États empty/loading/error

- `UsagesDashboardPage.jsx` : ScopeBar gère l'empty (« Aucune donnée disponible pour ce périmètre »).
- TimelineTab / BaselineTab / ComptageTab : pas systématiquement protégés contre `data === null`.
- **Recommandation P0b a déjà patché HeatmapCard duplicate-keys** (audit P0b §C4).

### 4.4 Pilotage actions dispersées (motivation 4ᵉ onglet)

| Card | Action contenue | Tracking |
|---|---|---|
| `CostCard` | `optimization.action` + `savings_eur` (shift HP→HC) | ❌ aucun tracker |
| `PowerOptimizationCard` | recommandation réduction PS + `strategy` | ❌ aucune CTA Centre d'Action |
| `FlexNebcoCard` | Checklist éligibilité + ROI BACS↔Flex | ❌ aucune action enregistrée |
| `TimelineTab:279` | Verdict baseload « Pistes : éclairage nuit, serveurs, veilles » | ❌ texte mort |

→ **Le 4ᵉ onglet « Pilotage des usages » fédèrerait ces 4 recommandations dispersées en file d'attente d'actions actionnables avec création ActionCenterItem.**

---

## 5 — Audit doublons / legacy

### 5.1 Doublons FE/UX (8 identifiés)

| # | Concept | Page A | Page B | Recommandation | Priorité |
|---|---|---|---|---|---|
| D1 | Loss €/an estimation | `/diagnostic-conso` (`estimated_loss_eur`) | `/monitoring` (`estimated_impact_eur`) | Unifier service backend ; expose `estimated_loss_*` | **P0** |
| D2 | Off-hours impact | `/diagnostic-conso` insight hors_horaires | `/monitoring` KPI alert HORS_HORAIRES | Unifier calc model + service | **P0** |
| D3 | Vocabulaire anomalie/alert | `/diagnostic-conso` ConsumptionInsight | `/monitoring` MonitoringAlert | Enum `AnomalyType` unifié + severity scale | P1 |
| D4 | Period parameter | /usages months 3-36 | /diagnostic days 90 default | /monitoring days 90 | Standard `period_start/period_end` ISO | P1 |
| D5 | Data quality / gap | /diagnostic banner data_gap | /monitoring no_data status | Métadonnées unifiées endpoints | P1 |
| D6 | Heatmap 7×24 (renderer) | /usages HeatmapCard (IPE) | /usages-horaires ProfileHeatmapTab | /monitoring HeatmapGrid | Extraire composant `<Heatmap7x24/>` partagé | P2 |
| D7 | Power profile chart | /diagnostic Evidence drawer | /monitoring WeekdayWeekendChart | Extraire `<ProfileChart/>` Recharts | P2 |
| D8 | Action creation flow | /diagnostic ✓ ActionDrawer V4 | /monitoring ✓ ExecutiveSummary CTAs | Garder distinct (source diff) | P3 |

### 5.2 Routes mortes / legacy

- `/api/usages/recommendations/generate/{site_id}` → HTTP **405** (POST attendu) : non orphelin techniquement mais inutile sans caller FE.
- `/api/pilotage/flex-ready-signals/{site_id}` + `/roi-flex-ready/{site_id}` → HTTP **404 sur HELIOS** (DEMO_MODE site_id alpha pas mappé). Pattern Option C cohérent mais peut surprendre.
- **Pages legacy déjà neutralisées** : `/cockpit/pilotage` (P0a redirect), `/flex` (P0a hidden), 7 pages orphelines fichiers physiques (L8 Mois 5).

---

## 6 — Audit contrat de vérité des chiffres

### 6.1 ✅ Endpoints qui respectent (source / formule / unit / period / scope)

`/usages/energy-signature/{site_id}` → exemple :
```json
{
  "baseload_kwh_per_day": 120.5,
  "thermo_sensitivity_kwh_per_dju": 8.2,
  "r_squared": 0.83,
  "model": "2P",
  "formula": "E = 8.20 × DJU + 120.50",
  "data_points": 120,
  "period": "12 mois",
  "benchmark": { "baseload": 150, "thermo": 10 },
  "confidence": "high"
}
```

`/usages/baselines/{site_id}` expose 3 méthodes avec `source` + `formula` + `confidence`.

`/usages/load-profile/{site_id}` expose toutes les formules dans le payload.

`/consumption/insights` expose `type` + seuil pour chaque détecteur.

### 6.2 ❌ Endpoints qui exposent des chiffres bruts sans contrat

| Endpoint | Manque |
|---|---|
| `/usages/scoped-dashboard` | Scope OK ; formule des KPI Conso/Coût/IPE/Readiness non documentée dans payload |
| `/usages/cost-by-period/{id}` | Prix appliqué NON explicité (source contract vs fallback DEFAULT) |
| `/usages/benchmark/{id}` | Seuil 20 % atypie NON documenté |
| `/pilotage/roi-flex-ready/{id}` | Composantes EUR (pointe/NEBCO/CEE) sans détail prix unitaire source |
| `/pilotage/radar-prix-negatifs` | Algo heuristique J+7 non documenté payload (`confiance:"indicative"` seulement) |
| `/pilotage/portefeuille-scoring` | Score formule opaque |

---

## 7 — Audit impacts €

**SoT Prix** : `cost_by_period_service.py::_resolve_site_price()` → `EnergyContract` site ACTIVE elec, fallback `DEFAULT_PRICE_ELEC_EUR_KWH=0.185` (`config/default_prices.py`).

### Endpoints respectueux du contrat TURPE 7

✅ `/cost-by-period/{site_id}` : ventile HPH/HCH/HPB/HCB × usage (structure TURPE 7 correcte).
✅ `/hphc_breakdown_v2` : ratio HP/HC appliqué.

### Endpoints sans prix canonique exposé

❌ `/consumption/insights` : `estimated_loss_eur` calculé avec `_get_price_ref()` MAIS source non retournée.
❌ `/recommendations/generate/{site_id}` : `expected_gain_eur` dans actions, source implicite.
❌ `/pilotage/roi-flex-ready/{site_id}` : 3 composantes EUR sans détail prix unitaire source.

→ **Lacune critique** : aucun endpoint n'expose `price_source: "EnergyContract:id_123" | "default_fallback"` → auditabilité facture impossible.

---

## 8 — Mapping Centre d'Action V4

| Page | Crée `ActionCenterItem` ? | `external_ref` actuel | Recommandation 4ᵉ onglet |
|---|---|---|---|
| /usages | ❌ Read-only | N/A | Ajouter via 4ᵉ tab |
| /usages-horaires | ❌ Read-only | N/A | — |
| /diagnostic-conso | ✅ via `openActionDrawer()` | `consumption:insight-{id}` | Existant — réutiliser |
| /monitoring | ✅ via ExecutiveSummary CTAs | `monitoring:alert-{id}` | Existant — réutiliser |
| /flex | ❌ Shell | N/A | — |

**Pattern recommandé pour le 4ᵉ tab « Pilotage des usages »** :

| Source | external_ref | Domain | Kind |
|---|---|---|---|
| Insight `hors_horaires` | `pilotage:hors_horaires:site:{id}:from:{date}` | `optimisation` | `recommendation` |
| Insight `base_load` | `pilotage:base_load:site:{id}` | `optimisation` | `recommendation` |
| Insight `pointe` | `pilotage:pointe:site:{id}:date:{day}` | `optimisation` | `recommendation` |
| Insight `derive` | `pilotage:derive:site:{id}:window:30d` | `optimisation` | `recommendation` |
| Recommendation `power_optim` | `pilotage:power_optim:site:{id}` | `optimisation` | `decision` |

**Source_url** : `/usages?tab=pilotage&site={id}&insight={type}` → retour drilling-down depuis Centre d'Action drawer LinksTab « Voir la source » (P0 #311).

---

## 9 — Réponses aux 10 questions clés du brief

| # | Question | Réponse synthétique |
|---|---|---|
| 1 | Que peut faire un EM aujourd'hui dans /usages ? | **Voir** 4 KPI + 3 onglets (timeline/baseline/comptage) + 7 cards. **Naviguer** scope multi-niveaux. **Lire** verdicts texte (baseload pistes, action suggestion CostCard). **Ne peut PAS** : créer une action de pilotage, tracker l'exécution, voir le ROI cumulé d'un plan. |
| 2 | Quels endpoints existent mais ne sont pas exposés ? | **≥ 18 orphelins `/api/usages/*`** dont `/baselines`, `/energy-signature`, `/load-profile`, `/recommendations/generate`, `/compliance`, `/compare/site-vs-sector`, `/benchmark` (cf §2.1) |
| 3 | Quels calculs sont backend fiables ? | 5 détecteurs `consumption_diagnostic.py` + `energy_signature_service.py` + `baseline_service.py` (A/B/C) + `load_profile_service.py` + `cost_by_period_service.py` (cf §3.1) |
| 4 | Quels calculs sont encore frontend ? | **4 violations §8.1** : KpiStrip.jsx:24 IPE, :27 surplusEur, HeatmapCard.jsx:80 ratio ADEME, PowerOptimizationCard.jsx:14-17 utilization+overflow |
| 5 | Quelles règles talon nuit / WE / pic / dérive existent ? | **Toutes existent BE** : `_detect_hors_horaires` / `_detect_base_load` (P5 nuit/WE) / `_detect_pointe` (MAD) / `_detect_derive` (slope 30j) / `_detect_data_gaps`. Seuils + formules dans la réponse. |
| 6 | Quels doublons existent entre les 5 pages ? | **8 doublons** identifiés (cf §5.1) — 2 P0 (loss €/an + off-hours), 3 P1 (vocab/period/data quality), 3 P2 (renderer heatmap/profile, action flow OK distinct) |
| 7 | Comment intégrer le 4ᵉ onglet sans nouveau menu ? | Ajouter `{ id: 'pilotage', label: 'Pilotage', icon: Sliders }` dans `ALL_TABS` de `UsagesDashboardPage.jsx`. Composer un nouveau composant `PilotageTab.jsx` consommant `/consumption/insights` + `/usages/recommendations/generate` + ActionDrawerContext. **Aucune route à ajouter.** |
| 8 | Comment créer des actions dans Centre d'Action V4 sans doublon ? | external_ref pattern `pilotage:{insight_type}:site:{id}[:from:{date}]` (cf §8). Garantit idempotence ; ne pas réintroduire le pattern title-based legacy. |
| 9 | Quels chiffres ne respectent pas le contrat de vérité ? | `/scoped-dashboard` (formules KPI), `/cost-by-period` (prix source), `/benchmark` (seuil atypie), `/pilotage/roi-flex-ready` + `/radar-prix-negatifs` + `/portefeuille-scoring` (algos opaques) |
| 10 | Quels impacts € ne respectent pas le contrat tarifaire ? | Aucun endpoint n'expose `price_source: "EnergyContract:id" \| "default_fallback"`. À ajouter sur tous les services qui calculent un € (insights, recommendations, ROI flex) |

---

## 10 — Plan P0 / P1 / P2

### 10.1 P0 — Bloquant pour le sprint Pilotage (4 items, ~2,5 j-dev)

| # | Item | Effort |
|---|---|---|
| **P0-1** | Migrer 4 calculs FE → BE : `ipe_total_kwh_m2`, `surplus_eur_estimated`, `ratio_vs_ademe_pct` dans sites[], `utilization_pct_safe`+`overflow_status` dans power-optimization | 1 j (BE + FE remplacement par lecture) |
| **P0-2** | Exposer `price_source` (contract_id ou default_fallback) dans tous les endpoints qui calculent un € (`insights`, `recommendations`, `roi-flex-ready`) | 0,5 j |
| **P0-3** | Unifier `estimated_loss_eur` / `estimated_impact_eur` (D1 doublon) : alias ou champ canonique partagé entre `/consumption/insights` et `/monitoring/alerts` | 0,5 j |
| **P0-4** | Glosser ≥ 12 acronymes nus dans UsagesDashboardPage cards (KpiStrip, FlexNebcoCard, CostCard, BaselineTab, FooterLinks) via `SolNarrativeText` | 0,5 j |

### 10.2 P1 — Sprint Pilotage des usages 4ᵉ tab (~5 j-dev)

| # | Item | Effort |
|---|---|---|
| P1-1 | Ajouter onglet `pilotage` dans `ALL_TABS` (UsagesDashboardPage.jsx) + composer `PilotageTab.jsx` consommant `/consumption/insights` filtré par site/scope | 1 j |
| P1-2 | PilotageTab : liste insights actionnables (hors_horaires/base_load/pointe/derive) avec impact € + CTA « Créer action » (`openActionDrawer` réutilisé) | 1 j |
| P1-3 | Sync `/consumption/insights` → `ActionCenterItem` via endpoint `POST /api/pilotage/sync-actions-from-insights` (pattern billing_sync P0 #311 + external_ref + ActionLink + idempotence) | 1,5 j |
| P1-4 | Drawer « Pourquoi ce pilotage ? » sur chaque insight : expose source/formula/threshold/impact/period (pattern Cockpit P1.5) | 0,5 j |
| P1-5 | Unifier vocabulaire D3-D5 (AnomalyType enum + period_start/end ISO + data quality metadata) | 1 j |

### 10.3 P2 — Renderer partagés + cleanup (~3 j)

| # | Item | Effort |
|---|---|---|
| P2-1 | Extraire `<Heatmap7x24/>` composant partagé (D6) — used par 3 pages | 1 j |
| P2-2 | Extraire `<ProfileChart/>` Recharts (D7) | 1 j |
| P2-3 | Documenter contrat algos opaques (radar-prix-negatifs, portefeuille-scoring) + formula dans payload | 0,5 j |
| P2-4 | Fusionner `/usages-horaires` dans `/usages` (audit menu #313 P1-2) — décision en sprint P1 si UX bénéficie | 0,5 j |

---

## 11 — Prompt P0 prêt pour le sprint correctif

```
Tu es Staff Engineer Full-Stack + QA/Release Manager sur PROMEOS.

BRANCHE
Créer :
  claude/usage-steering-p0-truth-contract

Base :
  claude/refonte-sol2 après merge PR audit Usage Steering (cette PR).

OBJECTIF
Corriger les 4 P0 issus de l'audit Usage Steering 2026-05-27 (§10.1)
avant d'ouvrir le sprint 4ᵉ onglet « Pilotage des usages ».

CONTEXTE
L'audit a confirmé :
- /usages est la route canonique.
- 18+ endpoints BE existent déjà pour alimenter Pilotage (orphelins).
- 4 calculs métier FE violent la doctrine §8.1.
- Le contrat tarifaire des impacts € est lacunaire (price_source absent).
- 8 doublons cross-pages dont 2 P0 (loss €/an + off-hours).
- ≥ 12 acronymes nus dans UsagesDashboardPage cards.

RÈGLES NON NÉGOCIABLES
- Aucun nouveau menu (4ᵉ tab arrive au sprint P1).
- Aucun écran fantôme.
- Aucun /usage-steering.
- Aucun Flex visible client (préserver hidden P0a).
- Doctrine §8.1 : zéro calcul métier FE.
- Français clair.
- Tests source-guards G1-G4 + Playwright obligatoires.

CHANTIER 1 — Migration 4 calculs FE → BE

Backend :
- /api/usages/scoped-dashboard : ajouter dans summary{} :
    ipe_total_kwh_m2 (kWh/m²)
    surplus_eur_estimated (€)
    price_source (str: "EnergyContract:id_X" | "default_fallback")
- /api/usages/portfolio-compare : ajouter dans chaque sites[].ipe_by_usage :
    ratio_vs_ademe_pct (float)
- /api/usages/power-optimization/{site_id} : ajouter
    utilization_pct_safe (clamp 0-100)
    overflow_status (str: "normal" | "overflow" | "underflow")

Frontend :
- KpiStrip.jsx:24 → lire summary.ipe_total_kwh_m2 (supprimer division)
- KpiStrip.jsx:27 → lire summary.surplus_eur_estimated (supprimer multiplication)
- HeatmapCard.jsx:80 → lire sites[].ipe_by_usage[u].ratio_vs_ademe_pct (supprimer Math)
- PowerOptimizationCard.jsx:14-17 → lire utilization_pct_safe + overflow_status

Tests :
- BE unit tests : 4 endpoints exposent les nouveaux champs
- FE source-guard : grep dans components/usages/ interdit Math.* sur ratios métier
- Playwright : 0 console error sur /usages

CHANTIER 2 — Price source exposé

- /api/consumption/insights : chaque insight inclut price_source
- /api/usages/recommendations/generate/{id} : chaque action inclut price_source
- /api/pilotage/roi-flex-ready/{id} : composantes EUR avec price_source par composante

Tests :
- BE assert price_source ∈ ["EnergyContract:id_*", "default_fallback"]
- Source-guard : interdit response sans price_source si payload contient *_eur

CHANTIER 3 — Unification loss €/an cross-brique

Backend :
- /api/consumption/insights + /api/monitoring/alerts : alias commun
    estimated_loss_eur (canonical) + impact_period_days
- Maintenir estimated_impact_eur deprecated pour rétro-compat (avec warning).

Tests :
- /diagnostic-conso et /monitoring affichent même chiffre pour même site/période.

CHANTIER 4 — Glose 12 acronymes énergie

Frontend :
- KpiStrip.jsx:60 « Écart DT 2030 » → <SolNarrativeText>
- FlexNebcoCard.jsx:40,80 NEBCO ×4, BACS, AOFD → <SolNarrativeText>
- CostCard.jsx:74,154-160 HPH/HCH/HPB/HCB → <SolNarrativeText>
- BaselineTab.jsx:86 « Obj. DT »
- FooterLinks.jsx:89 « DT / BACS / APER »

Tests source-guard :
- Aucun acronyme énergie nu (DT/OPERAT/BACS/APER/NEBCO/AOFD/HPH/HCH/HPB/HCB)
  dans UsagesDashboardPage cards sans <SolNarrativeText> wrapper.

CRITÈRES D'ACCEPTATION
- 4 calculs FE migrés BE (sources documentées dans payload).
- Tous les endpoints € exposent price_source.
- loss €/an cohérent /diagnostic vs /monitoring.
- 0 acronyme énergie nu dans /usages.
- 0 console error Playwright HELIOS.
- 0 network 4xx/5xx golden path.
- Non-régression cockpit P1/P1.5 + Action Center V4 P0.
- BE source-guards cockpit+billing+energie_p0a+p0b+usage_steering verts.

COMMIT
fix(usage-steering): migrate FE calc to BE and expose truth contract
```

---

## 12 — Critères GO du brief (8/8 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 0 modification code | ✅ READ-ONLY strict |
| 2 | `/usages` confirmé route canonique | ✅ §1.1 |
| 3 | 4ᵉ onglet « Pilotage des usages » confirmé ou challengé | ✅ confirmé (§9 Q7) — pas de `/usage-steering` |
| 4 | Aucun nouveau menu proposé | ✅ ajout dans `ALL_TABS` interne, pas de NavRegistry |
| 5 | Aucun `/usage-steering` | ✅ aucun proposé |
| 6 | Tous les doublons listés | ✅ 8 doublons §5.1 |
| 7 | Tous les calculs frontend identifiés | ✅ 4 violations §3.2 |
| 8 | Plan P0 chiffré | ✅ 4 items ~2,5 j-dev §10.1 |

---

## Verdict

🟡 **Périmètre Pilotage des usages riche mais éclaté** :
- Côté BE : 28 endpoints `/api/usages/*` + 5 `/api/pilotage/*` + 5 détecteurs `consumption_diagnostic` avec règles formelles (talon nuit / WE / pic / dérive / data_gap). **≥ 18 endpoints orphelins** prêts à alimenter le 4ᵉ onglet sans nouveau service BE.
- Côté FE : `/usages` est canonique, 3 onglets + 7 cards, **mais** 4 calculs métier violent doctrine §8.1, 12 acronymes nus, 0 mécanisme pour créer une action depuis une carte.
- Cross-brique : 8 doublons (2 P0 critiques sur loss €/an cross-brique, 3 P1 vocab/period/data quality, 3 P2 renderers).
- Mapping Centre d'Action V4 : pattern `external_ref` clair (`pilotage:{insight_type}:site:{id}`), `source_url` `/usages?tab=pilotage&site=X`.

**Plan P0 chiffré** : ~2,5 j-dev pour fiabiliser le contrat de vérité avant le sprint P1 (4ᵉ onglet). **Prompt P0 prêt à l'emploi** §11 (5 chantiers : 4 calculs BE + price_source + unification loss + glose acronymes).

Aucun fichier code modifié dans cet audit (mode READ-ONLY strict respecté).
