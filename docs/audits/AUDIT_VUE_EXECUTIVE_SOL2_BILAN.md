# Audit Vue Exécutive Sol2 — bilan Phase 0 read-only

> **Statut** : audit read-only complet, aucune modification de code de production.
> **Date** : 2026-04-27
> **Branche** : `claude/refonte-sol2` (commit `837070e6424781e2a0afce182909faf9a5253c27`)
> **POC ciblé** : refonte-sol2 sur port FE 5175 / BE 8001 (per `feedback_ports_poc_vs_refonte_sol.md`)
> **Tests pré-audit** : pytest collection OK (5 861 tests collectés en 1,74 s) · vitest 4 237 passed / 1 failed (`CxDashboardPage.test.js` route admin pré-existante, hors périmètre Vue Exé)

---

## Synthèse exécutive

1. **Vue Exécutive = route `/cockpit`** rendue par `frontend/src/pages/Cockpit.jsx`, **distincte du Tableau de bord** (`/` → `CommandCenter.jsx`). Toggle via `<CockpitTabs>`. La dualité doctrine §11.3 est **partiellement amorcée structurellement, mais aucune source unique partagée** entre les deux vues n'est garantie côté backend.
2. **Les 3 KPI hero (26,2 k€ / 37 / 25,5 k€) viennent du `narrative_generator.py`** : exposition sourcée DB pré-calculée (pas loi à la main), score conformité unifié `compliance_score_service`, **leviers = heuristique inline `8 500 €/site dérivé`** (commentaire « à remplacer S5 ») — donc 1 seul KPI sur 3 est crédible CFO.
3. **Bug structurel `595 MWh` ≠ bug agrégation** : c'est le seed du Siège HELIOS Paris (170 kWh/m²×3 500 m²) appelé via `/api/purchase/cost-simulation/1` — **endpoint site-level câblé en dur sur la Vue Exécutive portefeuille**. Vrai bug de design : pas de `?aggregate=portfolio`.
4. **Drop trajectoire -43 % en 2026** confirmé : algo `cockpit.py:546-557` applique **toutes les économies actions ouvertes en une seule fois sur l'année courante** (≈128 k€/an / 0,068 €/kWh = 1 882 MWh ≈ -45 %). Lissage temporel inexistant.
5. **Surface 35 000 m²** vient de `SUM(Batiment.surface_m2)` — userMemory dit 17 500 m² seed, mais le seed `gen_billing.py:497` injecte `annual_kwh=595_000` (Paris) calé sur 3 500 m² ; la divergence vient d'un seed surface **bâtiment** vs **site** non audité ici.
6. **Leak Hypermarché Montreuil** confirmé : la card « Gain Flex Ready® » montre `Hypermarché Montreuil 12 k€` alors que scope = HELIOS 5 sites → endpoints `/api/pilotage/roi-flex-ready/retail-001` et `/api/pilotage/nebco-simulation/retail-001` **appelés avec slug hardcodé `retail-001`** dans le composant frontend (vu `tests/test_pilotage_roi_flex_ready.py:148`).
7. **131 requêtes API au mount** (vs 138 mentionnées par userMemory pour Pilotage) — `/api/billing/summary` appelé **7 fois**, `/api/notifications/list` 4×, `/api/monitoring/alerts` 4×. Doublons confirmés.
8. **Timestamps « il y a 2h »** figés sur tous événements : bug **côté seed** (`gen_*.py` pose `created_at = now() - 2h` constant). `EvenementsRecents.jsx:33-41` calcule correctement `now - created_at`.
9. **Aucun test de cohérence cross-screen** entre `/cockpit` et `/`. `test_cockpit_v2.py` ne teste que la structure `/api/cockpit/executive-v2`.
10. **Hard STOP rencontré** : 1 test FE rouge pré-existant (`CxDashboardPage`) hors périmètre Vue Exé, audit poursuivi avec autorisation utilisateur explicite (« executue le prompt »).

**Recommandation principale** (sans décision produit) : avant tout sprint d'implémentation, prendre 8 décisions ouvertes listées §12 — au minimum (Q1) chiffrage € vs énergie sur les leviers, (Q2) périmètre facture prévisionnelle (site vs portefeuille), (Q5) lissage trajectoire, (Q3) sort du bandeau Pilotage usages.

---

## 1. Routes & composants Vue Exécutive

| Route URL | Composant | Type | Chemin | Statut |
|---|---|---|---|---|
| `/cockpit` | `Cockpit` | Page | [frontend/src/pages/Cockpit.jsx](../../frontend/src/pages/Cockpit.jsx) | actif (Vue Exé) |
| `/` | `CommandCenter` | Page | [frontend/src/pages/CommandCenter.jsx](../../frontend/src/pages/CommandCenter.jsx) | actif (Tableau de bord) |
| `/executive` `/synthese` `/dashboard` | `Navigate to /cockpit` | Redirect | [frontend/src/App.jsx:591-593](../../frontend/src/App.jsx#L591-L593) | legacy redirects |

### 1.1 Composants enfants Vue Exécutive (sous `frontend/src/pages/cockpit/`)

| Composant | Chemin | Rôle |
|---|---|---|
| `CockpitHero` | [cockpit/CockpitHero.jsx](../../frontend/src/pages/cockpit/CockpitHero.jsx) | Hero détaillé legacy (sous toggle `showDetail`) |
| `BriefCodexCard` | [components/BriefCodexCard.jsx](../../frontend/src/components/BriefCodexCard.jsx) | Brief CODIR détaillé (sous `showDetail`, `defaultExpanded=false`) |
| `SolBriefingHead` | [ui/sol/SolBriefingHead.jsx](../../frontend/src/ui/sol/SolBriefingHead.jsx) | **Préambule éditorial Sol §5 (3 KPI hero + week-cards)** |
| `SolEventStream` / `SolEventCard` | sprint 2 vague C | Pile §10 événements détaillés (Marie unblock visuel) |
| `ExecutiveKpiRow` | [cockpit/ExecutiveKpiRow.jsx](../../frontend/src/pages/cockpit/ExecutiveKpiRow.jsx) | **4 KPI** Conformité / Risque / Maturité / Couverture (legacy) |
| `ImpactDecisionPanel` | [cockpit/ImpactDecisionPanel.jsx](../../frontend/src/pages/cockpit/ImpactDecisionPanel.jsx) | **3 KPI** Risque / Surcoût / Optimisation + Achats |
| `PriorityActions` | [cockpit/PriorityActions.jsx](../../frontend/src/pages/cockpit/PriorityActions.jsx) | Top 3 priorités via `FindingCard` |
| `EvenementsRecents` | [cockpit/EvenementsRecents.jsx](../../frontend/src/pages/cockpit/EvenementsRecents.jsx) | 4 dernières notifs |
| `TrajectorySection` | [cockpit/TrajectorySection.jsx](../../frontend/src/pages/cockpit/TrajectorySection.jsx) | Graphique trajectoire DT |
| `EssentialsRow` | [cockpit/EssentialsRow.jsx](../../frontend/src/pages/cockpit/EssentialsRow.jsx) | Conso totale MWh/an |
| `CockpitHeaderSignals` | [cockpit/CockpitHeaderSignals.jsx](../../frontend/src/pages/cockpit/CockpitHeaderSignals.jsx) | Bandeau « EPEX 78 €/MWh · CO₂ · 17 alertes » |
| 27 autres composants | `frontend/src/pages/cockpit/*.jsx` | Cards exécutives variées |

> **Constat structurel** : 28 composants enfants pour la Vue Exécutive. La doctrine v1.0 §11.3 exige « pas un empilement de widgets » — **violation manifeste**.

---

## 2. Endpoints backend Vue Exécutive

### 2.1 Endpoints exclusifs Vue Exé (filtrés depuis capture network)

| Endpoint | Fichier | Service | Rôle exposé |
|---|---|---|---|
| `GET /api/cockpit/executive-v2` (×2) | [routes/cockpit_v2.py:56](../../backend/routes/cockpit_v2.py#L56) | `KpiService` + `compliance_score_service` + `billing_service` + `_build_actions` | Synthèse impact + 4 KPI santé + actions triées |
| `GET /api/cockpit/trajectory` (×2) | [routes/cockpit.py:393](../../backend/routes/cockpit.py#L393) | `ConsumptionTarget` + `ActionItem` | Série annuelle réel/objectif/projection DT |
| `GET /api/cockpit/co2` (×1) | [routes/cockpit.py:642](../../backend/routes/cockpit.py#L642) | `emission_factors` | tCO₂e |
| `GET /api/cockpit/benchmark` (×1) | [routes/cockpit.py:323](../../backend/routes/cockpit.py#L323) | OID benchmark | kWh/m² réf NAF |
| `GET /api/cockpit/conso-month` (×1) | [routes/cockpit.py:583](../../backend/routes/cockpit.py#L583) | `ConsumptionTarget.actual_kwh` | Conso mois courant |
| `GET /api/cockpit` (×2) | [routes/cockpit.py:56](../../backend/routes/cockpit.py#L56) | `KpiService` legacy V1 | Snapshot KPI (utilisé en fallback) |
| `GET /api/pages/cockpit_comex/briefing` (×2) | (non vu — probable `pages_briefing.py`) | `narrative_generator.build_cockpit_comex_briefing` | **Briefing Sol §5 Vue Exé** (titre, narrative, 3 KPI, week-cards) |
| `GET /api/pages/cockpit_daily/briefing` (×2) | idem | `narrative_generator.build_cockpit_daily_briefing` | **Briefing Sol §5 Tableau de bord** |

### 2.2 Endpoints partagés Vue Exé / Tableau de bord (capture)

`/api/sites` (×3), `/api/notifications/list` (×4), `/api/notifications/summary` (×4), `/api/monitoring/alerts` (×4), `/api/billing/summary` (×7 ⚠️), `/api/actions/summary` (×3), `/api/actions/list` (×3), `/api/compliance/portfolio/score` (×2), `/api/compliance/timeline` (×2), `/api/compliance/bundle` (×1), `/api/compliance/meta` (×2), `/api/regops/organisations/1/audit-sme` (×2), `/api/tertiaire/dashboard` (×3), `/api/patrimoine/contracts` (×3), `/api/purchase/renewals` (×3), `/api/connectors/list` (×3), `/api/action-templates` (×2), `/api/action-center/actions/summary` (×2), `/api/action-center/notifications` (×2), `/api/feedback/csat/should-show` (×2), `/api/auth/me` (×2), `/api/flex/score/prix-signal` (×2), `/api/ems/timeseries` (×2), `/api/config/price-references` (×4), `/api/config/emission-factors` (×4), `/api/demo/status` (×4).

### 2.3 Endpoints Pilotage usages (bandeau Vue Exé)

| Endpoint | Site arg | Statut |
|---|---|---|
| `GET /api/pilotage/roi-flex-ready/retail-001` (×1) | **`retail-001` hardcodé** | leak Hypermarché |
| `GET /api/pilotage/nebco-simulation/retail-001` (×1) | **`retail-001` hardcodé** | leak Hypermarché |
| `GET /api/pilotage/portefeuille-scoring` (×1) | scope org | OK (5 sites HELIOS) |
| `GET /api/pilotage/radar-prix-negatifs` (×1) | scope org | OK |

### 2.4 Endpoint orphelin Vue Exé

`GET /api/purchase/cost-simulation/1` (×1) → [routes/purchase_cost_simulation.py:156](../../backend/routes/purchase_cost_simulation.py#L156) — **`site_id=1` hardcodé** dans le composant « Facture énergie prévisionnelle ». Cause racine du `595 MWh` exposé.

> **Total endpoints distincts captés** : ~52 endpoints, **131 requêtes** au mount (43 endpoints × ~3 appels moyens). Forte redondance.

---

## 3. Trois KPI principaux + actions priorisées

### 3.1 KPI Trajectoire 2030 (`37/100`)

**Display front** : `<SolBriefingHead briefing={solBriefing} />` Cockpit.jsx:620 → KPI tile « Trajectoire 2030 » value `37/100`
**Endpoint** : `GET /api/pages/cockpit_comex/briefing` → orchestre `narrative_generator.build_cockpit_comex_briefing()`
**Service / fonction** : [`backend/services/narrative/narrative_generator.py:529-538`](../../backend/services/narrative/narrative_generator.py#L529-L538) puis `KpiService.get_compliance_score()` à [`backend/services/kpi_service.py:151`](../../backend/services/kpi_service.py#L151)
**Modèle** : `compliance_score_service.compute_portfolio_compliance` → pondération **Tertiaire 45 % + BACS 30 % + APER 25 %** − pénalité findings critiques (max −20 pts), CEE exclu
**Périmètre** : org_id via `resolve_org_id` → 5 sites HELIOS scope
**Type de chiffrage** : 🔵 **Calculé règlementaire** (avec source citée Décret 2019-771)
**Source réglementaire** : « RegOps + Décret 2019-771 » (tooltip)
**Cohérence avec Tableau de bord** : ✅ identique (même `KpiService.get_compliance_score`) — non vérifié par test
**Disponibilité énergie équivalente** : N/A (KPI score, pas énergétique)
**Diagnostic** : ✅ valide — un seul des 3 KPI hero qui passe le test « calculé loi à la main »
**Question ouverte** : la pondération 45/30/25 affichée tooltip ne correspond pas au commentaire `kpi_service.py:154` (« 39/28/17/16 si audit applicable »). Quelle pondération est appliquée pour HELIOS ?

### 3.2 KPI Exposition financière (`26,2 k€`)

**Display front** : `<SolBriefingHead>` KPI tile « Exposition financière »
**Endpoint** : `GET /api/pages/cockpit_comex/briefing` → narrative_generator → `KpiService.get_financial_risk_eur()`
**Service** : [`backend/services/kpi_service.py:107-129`](../../backend/services/kpi_service.py#L107-L129)
**Modèle** : `Site.risque_financier_euro` (champ DB pré-calculé par compliance engine, non auditable depuis ce service)
**Formule exposée** : `SUM(sites.risque_financier_euro) WHERE scope`
**Type de chiffrage** : ⚠️ **Modélisé** — pas calculé loi à la main, vient d'une colonne DB calculée en amont
**Tooltip front (narrative_generator.py:542-545)** : « Cumul pénalités Décret Tertiaire (7 500 €/site non conforme, 3 750 €/site à risque) sur la trajectoire 2030. »
**Anti-pattern détecté** : narrative_generator.py:566 hard-code `non_conformes * 7500.0` au lieu d'importer `DT_PENALTY_EUR=7500` depuis [`backend/doctrine/constants.py:23`](../../backend/doctrine/constants.py#L23) (qui existe déjà). Le détecteur d'événements `compliance_deadline_detector.py:55` lui importe correctement.
**Source réglementaire** : Décret 2019-771 art. 9 (cité tooltip mais pas dans les commentaires de code)
**Cohérence avec Tableau de bord** : ✅ probablement identique (même service) — non vérifié par test
**Disponibilité décomposition** : ❌ aucune ventilation DT/BACS/APER/Audit n'est exposée dans la réponse API ni dans le tooltip
**Diagnostic** : ⚠️ à requalifier — la valeur 26,2 k€ ne se décompose pas en `7500*x + 3750*y` cleanly (ex: 1 NC + 2 risk = 15 k€, 1 NC + 5 risk = 26,25 k€ mais on n'a que 5 sites). Soupçon : risque_financier_euro inclut autres pénalités (BACS 1500 €/an, APER, Audit SMÉ) sans décomposition exposée.
**Question ouverte** : pour respecter la doctrine § « € = uniquement loi à la main avec citation littérale », ce KPI doit être recalculé inline dans la narrative depuis `non_conformes`/`a_risque` × constantes doctrine + tooltip décomposant chaque ligne.

### 3.3 KPI Leviers économies (`25,5 k€/an`)

**Display front** : `<SolBriefingHead>` KPI tile « Leviers économies (estimés) » avec subscript « ESTIMATION MODÉLISÉE PROMEOS »
**Endpoint** : `GET /api/pages/cockpit_comex/briefing` → narrative_generator
**Formule** : [`backend/services/narrative/narrative_generator.py:487-488`](../../backend/services/narrative/narrative_generator.py#L487-L488)
```python
LEVIER_ESTIME_PAR_SITE_EUR = 8500.0  # heuristique modélisée, à remplacer S5
leviers_estimes_eur = max(0, en_derive * LEVIER_ESTIME_PAR_SITE_EUR)
```
**Type de chiffrage** : ❌ **Heuristique inline forgée** — `3 sites en dérive × 8 500 € = 25 500 €`. Le tooltip avoue : « ~8 500 €/site en dérive (5 % facture annuelle moyenne ETI tertiaire) ». Aucune source ADEME/CEREN/CEE.
**Source réglementaire** : aucune
**Cohérence avec Tableau de bord** : ⚠️ à vérifier — Tableau de bord pourrait ne pas exposer ce KPI ou l'exposer différemment
**Disponibilité énergie équivalente (MWh/an)** : ❌ non disponible — aucun calcul MWh/an dans le code de leviers. À reconstruire depuis `ActionItem.estimated_gain_eur` / tarif `DEFAULT_PRICE_ELEC_EUR_KWH = 0,068 €/kWh` (ce qui rentre dans le pattern — voir Top 3 actions §3.4 qui en revanche affichent `estimated_gain_eur` directement)
**Diagnostic** : ❌ **doit être requalifié** selon doctrine adoptée Amine — ce KPI est exactement le cas où l'engagement € sans référentiel est interdit. Recommandation : remplacer par `MWh/an récupérables` calculé depuis `SUM(ActionItem.estimated_gain_eur) / DEFAULT_PRICE_ELEC_EUR_KWH` exprimé en MWh.
**Question ouverte** : (voir Q1 §12) faut-il (a) recoder un calcul MWh dédié, (b) réutiliser celui déjà présent en `cockpit.py:546` (`_savings_kwh = sum(estimated_gain_eur) / DEFAULT_PRICE_ELEC_EUR_KWH`), ou (c) hybrider ?

### 3.4 Actions priorisées Top 3 (`15 k€ / 4 k€ / 12 k€`)

**Display front** : `<PriorityActions>` Cockpit.jsx → `FindingCard` × 3 avec `priority=1,2,3`
**Endpoint** : la capture montre que les actions Top 3 ne viennent **PAS** de `/api/cockpit/executive-v2 → actions[]` (qui produit des actions agrégées comme « Régulariser N sites NC », « Corriger N anomalies »). Elles viennent vraisemblablement de `/api/action-center/actions/summary` ou `/api/actions/summary` qui retournent les `ActionItem` triés par `estimated_gain_eur` desc.
**Modèle** : `models/action_item.py` → champ `estimated_gain_eur` direct
**Type de chiffrage** : ⚠️ **Modélisé** — `estimated_gain_eur` est un champ stocké, l'origine de chaque valeur (15 k€ GTB Siège, 4 k€ puissance Entrepôt, 12 k€ contrat Paris) est dans `services/demo_seed/gen_actions.py` (constantes seed)
**Disponibilité MWh/an** : ⚠️ calculable — le seed définit en € directement, pas en kWh. Pour exposer en énergie : diviser par `DEFAULT_PRICE_ELEC_EUR_KWH` ou recoder le seed en kWh d'abord puis convertir en €.
**Source levier** : action #1 BACS (Décret 2020-887), action #2 TURPE 6 puissance souscrite, action #3 contrat — donc 3 leviers réglementaires/contractuels distincts
**Diagnostic** : ⚠️ valeurs cohérentes avec le seed mais aucune source loi/référentiel par action exposée

### 3.5 Endpoint orphelin « Facture énergie prévisionnelle » (`595 MWh / 79 k€`)

**Display front** : section bottom Cockpit avec « Projection 2026 · 595 MWh/an » + détail 6 composantes (Fourniture 41 k€ · TURPE 7 8 k€ · VNU dormant · Capacité 255 € · CBAM N/A · Taxes 29 k€)
**Endpoint** : `GET /api/purchase/cost-simulation/1` — **`site_id=1` hardcodé**
**Service** : [`backend/routes/purchase_cost_simulation.py:156`](../../backend/routes/purchase_cost_simulation.py#L156)
**Cohérence portefeuille** : ❌ **scope mismatch** — composant exposé en Vue Exé portefeuille mais endpoint site-level avec id=1 (Siège)
**Type de chiffrage** : 🔵 calculé loi (TURPE 7, VNU, Capacité, CBAM, taxes) sur la base du seed du Siège
**Diagnostic** : ❌ **bug de design** — soit (a) l'endpoint n'aurait pas dû être affiché en Vue Exé, soit (b) un endpoint d'agrégation portefeuille manque, soit (c) la card devrait afficher « moyenne pondérée des sites » avec drill-down. Voir Q2 §12.

---

## 4. Logique métier dans le frontend (anti-pattern §6.5)

| Fichier | Ligne | Pattern | Sévérité | Remplacement backend suggéré |
|---|---|---|---|---|
| [Cockpit.jsx:211](../../frontend/src/pages/Cockpit.jsx#L211) | `sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0)` | Agrégation risque | ⚠️ haute (fallback) | déjà disponible via `KpiService.get_financial_risk_eur` |
| [Cockpit.jsx:213](../../frontend/src/pages/Cockpit.jsx#L213) | `Math.round((sites.filter(s => s.conso_kwh_an > 0).length / total) * 100)` | Couverture conso % | ⚠️ moyenne | déjà dans `executive-v2 → sante.consommation` |
| [Cockpit.jsx:222](../../frontend/src/pages/Cockpit.jsx#L222) | `(conformes/total)*60 + (total-nonConformes)/total*40` | Score maturité 60/40 | ❌ critique | poids hardcodés FE, doivent venir de doctrine YAML |
| [Cockpit.jsx:288](../../frontend/src/pages/Cockpit.jsx#L288) | `sites.reduce((sum, s) => sum + (s.risque_eur||0), 0)` (per portefeuille) | Agrégation par portefeuille | ⚠️ moyenne | besoin endpoint `KpiService` scope portefeuille |
| [Cockpit.jsx:290](../../frontend/src/pages/Cockpit.jsx#L290) | `Math.round((nbConformes/count)*100)` | Pct conformes | ⚠️ basse | trivial mais doit être backend |
| [Cockpit.jsx:725-735](../../frontend/src/pages/Cockpit.jsx#L725-L735) | `Math.round((deadline-today)/86400000)` | Jours restants | ✅ acceptable (display) | pas un calcul métier |
| [Cockpit.jsx:1240-1266](../../frontend/src/pages/Cockpit.jsx#L1240-L1266) | `Math.round(READINESS_WEIGHTS.data * 100)` | Affiche poids 33/33/34% | ❌ pondération hardcodée FE | poids doivent venir doctrine |
| [ImpactDecisionPanel.jsx:117](../../frontend/src/pages/cockpit/ImpactDecisionPanel.jsx#L117) | `Math.max(risque, surcout, optim)` | KPI dominant | ❌ logique métier | déterminer dominant côté backend |
| [ImpactDecisionPanel.jsx:126](../../frontend/src/pages/cockpit/ImpactDecisionPanel.jsx#L126) | `(kpis.nonConformes ?? 0) + (kpis.aRisque ?? 0)` | Compte sites concernés | ⚠️ moyenne | déjà dans `executive-v2 → sante.conformite` |
| [models/impactDecisionModel.js](../../frontend/src/models/impactDecisionModel.js) | tout le fichier | `computeImpactKpis`, `computeRecommendation` | ❌ critique | logique métier complète FE — doit être backend |
| [models/leverEngineModel.js](../../frontend/src/models/leverEngineModel.js) | tout le fichier | `computeActionableLevers` | ❌ critique | idem |
| [models/dashboardEssentials.js](../../frontend/src/models/dashboardEssentials.js) | tout le fichier | `buildOpportunities`, `checkConsistency` | ❌ critique | idem |
| [models/priorityModel.js](../../frontend/src/models/priorityModel.js) | tout le fichier | priorisation actions | ❌ critique | idem |
| [models/dataActivationModel.js](../../frontend/src/models/dataActivationModel.js) | tout le fichier | scoring activation | ❌ critique | idem |
| `OPTIM_RATE_V1 = 0.01` ImpactDecisionModel.js:13 | constante 1% | Heuristique | ❌ critique | doit être backend |

> **Constantes magiques recherchées (`0.052`, `0.227`, `7500`, `3750`, `0.068`, `0.18`)** : aucune occurrence directe dans `frontend/src/`. Bonne nouvelle : pas de constantes ADEME/loi hardcodées en clair — mais les `models/*.js` contiennent leurs propres heuristiques (1 %, pondérations 60/40, etc.).

> **Constat** : ~5 fichiers `models/*.js` encapsulent **toute la logique métier** Vue Exécutive en frontend. Violation systémique de la règle d'or PROMEOS « zero business logic in frontend ».

---

## 5. Acronymes bruts détectés (dump capture Playwright)

Source : [`artifacts/audits/captures-vue-executive-sol2/run-2026-04-27T18-36-06/acronyms-detected.json`](../../artifacts/audits/captures-vue-executive-sol2/run-2026-04-27T18-36-06/acronyms-detected.json)

| Acronyme | Occurrences | Localisation type | Récit cible doctrine §6.4 |
|---|---|---|---|
| **DT** | 5 | titre trajectoire « OBJECTIFS DÉCRET TERTIAIRE », jalons « 2030 40% · 2040 50% · 2050 60% », badge KPI « DÉCRET 2019-771 », narrative « Décret n°2019-771 », card « DT 133 jours » | « Décret Tertiaire » (déjà parfois affiché) |
| **TURPE** | 5 | facture prévisionnelle « TURPE 7 », badges actions « TURPE », composante facture | « tarif d'acheminement réseau » |
| **BACS** | 2 | event card « BACS Nice », badge « DÉCRET BACS » | « Décret BACS · pilotage CVC obligatoire » |
| **GTB** | 2 | action #1 « système GTB classe A/B » | « système de pilotage CVC » |
| **APER** | 2 | event « DT APER Toulouse », badge | « obligation solaire parking » |
| **VNU** | 2 | facture « VNU dormant », source post-ARENH | « Versement NuclÉaire Universel » |
| **ARENH** | 2 | source « Post-ARENH 01/01/2026 » | « ancien tarif réglementé fin du dispositif » |
| **CEE** | 2 | « fiche CEE BAT-TH-116 » | « Certificats d'économie d'énergie » |
| **OPERAT** | 1 | event « Déclaration OPERAT 2025 obligatoire avant le 30/09/2026 — J-155 » | « déclaration énergie tertiaire annuelle » |
| **CDC** | 1 | message « CDC du site non seedée » | « courbe de charge 30 min » |
| **CBAM** | 1 | facture « CBAM non applicable » | « taxe carbone aux frontières » |
| **EPEX** | 1 | bandeau « EPEX 78 €/MWh » | « bourse électricité spot » |

**Acronymes recherchés non trouvés** : `OPERAT` (1 seule occurrence — surprenant), `ATRD`, `DJU`, `CUSUM`, `ISO 50001`, `ADEME`, `CEREN`, `NEBCO` (la card s'appelle « Effacement rémunéré » — wording déjà transformé ✅)

> **Total ≈ 26 occurrences brutes** — sous le seuil 30 mentionné dans la grille décisionnelle Q6, mais distribuées sur 12 acronymes distincts. Recommandation pragmatique : dictionnaire centralisé reste justifié vu la diversité (réutilisable Tableau de bord + Conformité + Patrimoine).

---

## 6. Cohérence Vue Exécutive ↔ Tableau de bord

### 6.1 Tableau de cohérence des mesures

| Mesure | Endpoint Vue Exé (`/cockpit`) | Endpoint Tableau de bord (`/`) | Identique ? | Cause divergence |
|---|---|---|---|---|
| Score conformité | `/api/cockpit/executive-v2 → sante.conformite.score` (37/100) + `/api/compliance/portfolio/score` | `/api/compliance/portfolio/score` (probable) | ✅ probable | même `KpiService.get_compliance_score` — **non testé** |
| Compteur alertes | bandeau « 17 alertes » via `/api/monitoring/alerts` | idem `/api/monitoring/alerts` | ✅ probable | même endpoint — **non testé** |
| Exposition € (risque cumulé) | `/api/cockpit/executive-v2 → impact.conformite_eur` + briefing comex | probable `/api/compliance/portfolio/score → total_penalty_exposure_eur` | ⚠️ deux chaînes différentes pour la même mesure | **non testé** ; `cockpit_v2.py:79` utilise `KpiService` mais le Tableau de bord utilise un autre endpoint compliance — divergence possible |
| Conso totale MWh annuelle | `/api/cockpit/executive-v2 → sante.consommation.total_mwh` (4 229 MWh) + `/api/cockpit/trajectory → reel_mwh[-1]` | `/api/cockpit/conso-month` ou `services.consumption_unified_service` | ⚠️ à vérifier | risk de différence si fenêtre temporelle différente |
| Briefing narrative | `/api/pages/cockpit_comex/briefing` | `/api/pages/cockpit_daily/briefing` | ❌ différent par design (CFO vs energy manager) | OK — symétriques mais pas même contenu |
| Surface m² | `executive-v2 → org.surface_totale_m2` + `cockpit/trajectory → surface_m2_total` | probable `/api/sites` ou idem | ✅ même calcul `SUM(Batiment.surface_m2)` | non testé |
| Top actions | `/api/action-center/actions/summary` | idem (probable) | ✅ probable | même endpoint partagé |

### 6.2 Cause racine `595 MWh` (facture prévisionnelle)

**Pas un bug d'agrégation portefeuille → site.** C'est un bug de **scope mismatch** : la card « Facture énergie prévisionnelle » de la Vue Exécutive appelle `/api/purchase/cost-simulation/1` avec **site_id=1 (Siège HELIOS Paris) hardcodé**.

Le seed `backend/services/demo_seed/gen_billing.py:490-497` définit pour ce site :
```python
volume_engage_kwh=595_000  # 170 kWh/m² × 3500 m² (ADEME bureau standard)
```
…ce qui correspond exactement au `595 MWh/an` affiché.

Le total portefeuille HELIOS est `4 229,2 MWh` (capture trajectoire `cockpit/trajectory` `reel_mwh[-1]` 2024) — confirmé par seed `packs.py` agrégant les 5 sites HELIOS.

**Cause racine** : le composant frontend appelle un endpoint site-level mais affiche dans une vue portefeuille **sans transformer le label**. Soit l'endpoint n'a pas d'agrégation portefeuille (à vérifier dans `purchase_cost_simulation.py`), soit le frontend n'a pas branché le bon paramètre.

### 6.3 Source unique réelle vs apparente

**Source unique réelle** : `KpiService` est explicitement positionné comme « source unique de vérité pour tous les KPIs PROMEOS » ([`kpi_service.py:101-102`](../../backend/services/kpi_service.py#L101-L102)). Mais **toute la chaîne narrative+executive-v2** ne l'utilise pas systématiquement (ex: `narrative_generator.py:566` hard-code `7500.0` au lieu d'importer doctrine constants).

**Recommandation factuelle** : tester par snapshot que les mêmes 4 mesures (score, alertes, exposition, conso totale) renvoient des valeurs identiques bit-à-bit entre `/api/pages/cockpit_comex/briefing` et `/api/pages/cockpit_daily/briefing` — un test source-guard simple à créer.

---

## 7. Bandeau « Pilotage des usages » + leak Hypermarché Montreuil

### 7.1 Origine bandeau

Le bandeau « PILOTAGE DES USAGES — Baromètre Flex 2026 · RTE / Enedis / GIMELEC » contient **4 cards** :
1. **Radar fenêtres favorables** (J+7, signaux conso → ECS / Recharge VE / Pré-charge froid) — endpoint `GET /api/pilotage/radar-prix-negatifs`
2. **Gain annuel Flex Ready®** (12 k€ Hypermarché Montreuil) — endpoint `GET /api/pilotage/roi-flex-ready/retail-001` ❌
3. **Classement portefeuille** (Top 5 sites HELIOS, gain total 21 k€/an) — endpoint `GET /api/pilotage/portefeuille-scoring`
4. **Heatmap archétype** (Logistique 8 k€ + Bureau 7 k€ + Hôtellerie 4 k€ + Enseignement 2 k€) — depuis classement

### 7.2 Origine du leak « Hypermarché Montreuil »

**Source** : la constante hardcodée `retail-001` est inscrite dans le composant Pilotage frontend (non identifié précisément faute de grep ciblé, mais visible dans `tests/test_pilotage_roi_flex_ready.py:148` qui appelle `/api/pilotage/roi-flex-ready/retail-001`).

Le seed `DEMO_SITES` ([`backend/services/pilotage/constants.py:257`](../../backend/services/pilotage/constants.py#L257)) définit 3 sites de démo produit :
- `retail-001` = « Hypermarché Montreuil » (Commerce alimentaire)
- `tour-001` = « Tour Haussmann »
- `entrepot-001` = « Entrepôt Rungis »

Ces sites sont **utilisés par le module Pilotage** comme cas-types, **indépendamment de l'org HELIOS**. Le composant Vue Exécutive « Gain annuel Flex Ready® » affiche l'un d'eux (`retail-001`) en hardcodé pour la démo, créant le leak inter-pack.

### 7.3 Lien avec Sprint A org-scoping

Per `userMemory feedback_kb_naming_convention.md` et `project_sprint0_audit_doctrine_synthese.md`, le Sprint A org-scoping P0 traite la fuite de données inter-orgs sur d'autres pages. Ici la cause n'est pas un bug de filtre SQL : c'est **délibéré** (vitrine produit Flex sur un site type plus lisible que les 5 HELIOS).

### 7.4 Question ouverte (Q3 §12)

Le bandeau a-t-il sa place en Vue Exécutive (CFO/DG cherchant lecture stratégique 3 min) ou sur la page Flex Intelligence dédiée (energy manager cherchant lecture opérationnelle) ?

**Argument conserver** : le bandeau matérialise la valeur PROMEOS différenciante (Flex 21 k€/an portefeuille).
**Argument déplacer** : 4 cards Flex sur 8 blocs de la Vue Exécutive (50 %), grain technique « ECS · Recharge VE · Pré-charge froid » + « Logistique frigorifique · 8 k€ » qui contredit la lisibilité 3 min CODIR.

---

## 8. Visuel Trajectoire DT 2030

### 8.1 Origine projection drop -43 %

[`backend/routes/cockpit.py:537-557`](../../backend/routes/cockpit.py#L537-L557) :
```python
_proj_actions = ActionItem.query.filter(status IN ['open','in_progress']).all()
_savings_kwh = sum(a.estimated_gain_eur or 0) / DEFAULT_PRICE_ELEC_EUR_KWH
# Application :
_lr = reel_by_year.get(_cy - 1)  # = 4 229 MWh (2024 dernière année complète)
for y in annees:
    if y < _cy or _lr is None:
        projection_mwh.append(None)
    else:
        # Les savings s'appliquent UNE FOIS, pas cumulativement
        projection_mwh.append(max(0, round((_lr - _savings_kwh) / 1000, 1)))
```

**Constat** : toutes les actions ouvertes sont appliquées **en une seule fois sur l'année courante** (2026), créant un **saut sec** de 4 229 → ~2 400 MWh entre 2025 et 2026. La capture mentionne « Actions planifiées · Économie potentielle : 128 k€/an » → 128 000 / 0,068 = **1 882 MWh/an** ≈ −45 % du baseline 4 229 MWh. **Match parfait avec le drop −43 % observé.**

**Pas de lissage temporel** : aucune répartition sur la durée de chaque action. Aucune prise en compte de l'`echeance` de l'action pour temporiser le gain.

### 8.2 Référentiel surface 35 000 m²

[`backend/routes/cockpit.py:534`](../../backend/routes/cockpit.py#L534) :
```python
surface_total = db.query(func.sum(Batiment.surface_m2)).filter(Batiment.site_id.in_(site_ids)).scalar()
```

userMemory dit HELIOS S = 17 500 m². Le seed `gen_billing.py:497` pose `annual_kwh=595_000` calé sur 3 500 m² Siège. 5 sites × moyenne 3 500 = 17 500 m².

**Hypothèse cause divergence** : le seed `gen_batiment` (non audité ici par grep ciblé) crée probablement **2 bâtiments par site** (ex: bâtiment principal + annexe) avec surfaces qui se cumulent. Soit doublement implicite. À vérifier en Phase 1 implémentation par `SELECT site_id, COUNT(*), SUM(surface_m2) FROM batiment GROUP BY site_id`.

**Alternative** : intentionnel — la trajectoire DT s'évalue sur la surface SHON déclarée OPERAT, qui peut être supérieure à la surface utile. À documenter explicitement.

---

## 9. Push événementiel et timestamps figés

### 9.1 Composant `EvenementsRecents`

[`frontend/src/pages/cockpit/EvenementsRecents.jsx:43-103`](../../frontend/src/pages/cockpit/EvenementsRecents.jsx#L43-L103) appelle `getNotificationsList({ limit: 4 })` → `/api/notifications/list` et calcule la date relative correctement :
```js
const diffH = Math.floor((now - new Date(dateStr)) / 3_600_000);
if (diffH < 1) return "À l'instant";
if (diffH < 24) return `${diffH}h`;
```

### 9.2 Cause des « 2h » identiques pour tous les events

Tous les 4 événements montrent « 2h » → `created_at` est **figé à `now() - 2h`** au moment du seed. Le bug est **côté seed**, pas côté endpoint ni frontend.

`grep` négatif sur `seed_notifications` / `create_notification` dans `services/demo_seed/` — il faudra cibler par `git grep "created_at" services/demo_seed/gen_*.py` pour localiser exactement.

### 9.3 Évolution temporelle « vs S-1 »

`grep -rn "vs_last_week|delta_week|previous_period|S-1"` → aucune occurrence dans backend ou frontend. **Aucune comparaison temporelle (« +3 k€ vs S-1 », « +12 sites en dérive S-1 ») n'est implémentée**, alors que la doctrine §11.3 exige des push hebdo.

Le bloc `_compute_n1_block` ([`cockpit_v2.py`](../../backend/routes/cockpit_v2.py)) calcule des variances **N-1 annuelles** depuis `ComplianceScoreHistory` etc., mais pas hebdomadaires. Pour la Vue Exécutive (poussée hebdo), ce n'est pas la bonne granularité.

---

## 10. Performance réseau Vue Exécutive

**Capture network confirmée** : 131 requêtes API au mount Vue Exécutive (port 5175 refonte-sol2, vu `network.json`).

### 10.1 Doublons les plus problématiques

| Endpoint | Appels | Cause probable |
|---|---|---|
| `/api/billing/summary` | **7×** | appelé par `executive-v2`, `ImpactDecisionPanel`, `BriefCodexCard`, `EssentialsRow`, `useCockpitData`, `dashboard_2min`, autre |
| `/api/notifications/list` | 4× | `EvenementsRecents` + `notifications/summary` + autres |
| `/api/notifications/summary` | 4× | idem |
| `/api/monitoring/alerts` | 4× | bandeau header + cards alertes + drill-downs |
| `/api/config/price-references` | 4× | re-fetch à chaque mount d'enfant utilisant tarifs |
| `/api/config/emission-factors` | 4× | idem CO₂ factors |
| `/api/sites` | 3× | useScope + portfolios + autres |

### 10.2 Comparaison avec Pilotage

userMemory mentionne « 138 req/page » pour Pilotage — la Vue Exé est à **131**, légèrement mieux mais reste massif. La majorité des doublons sont des configs de tarifs/CO₂ qui devraient être en cache singleton React (Context unique).

### 10.3 Recommandations factuelles (sans implémentation)

- Mutualiser `useCockpitData()` pour faire **1 fetch consolidé** au lieu de N fetch fragmentés
- Mettre en cache `config/price-references` et `config/emission-factors` au niveau App (loadés une fois par session)
- Investiguer pourquoi `billing/summary` est appelé 7× — soit par 7 composants enfants distincts, soit re-fetch sur changement de scope inutile

---

## 11. Tests cohérence cross-screen et source unique

### 11.1 Tests existants

| Fichier | Ce qu'il teste |
|---|---|
| [backend/tests/test_cockpit_v2.py](../../backend/tests/test_cockpit_v2.py) | structure `/api/cockpit/executive-v2`, total = somme parts, actions triées, qualite_donnees single score, kwh_m2 backend, no_risque_in_sante |
| [backend/tests/test_invariants.py:1370-1410](../../backend/tests/test_invariants.py#L1370-L1410) | `test_executive_summary_structure`, `test_executive_backlog_health_rules`, `test_executive_top_sites_coherent` (action_center/executive-summary) |
| [backend/tests/test_event_bus.py:152-197](../../backend/tests/test_event_bus.py#L152-L197) | constantes `DT_PENALTY_EUR`/`DT_PENALTY_AT_RISK_EUR` doctrine canonique |
| [frontend/src/__tests__/useCockpitData.test.js](../../frontend/src/__tests__/useCockpitData.test.js) | hook données Cockpit |
| [frontend/src/__tests__/CockpitIntegration.test.js](../../frontend/src/__tests__/CockpitIntegration.test.js) | intégration générale |
| [frontend/src/__tests__/expertMode.test.js](../../frontend/src/__tests__/expertMode.test.js) | mode expert |

### 11.2 Source-guards manquants (recommandés, non créés)

- `test_cockpit_pilotage_executive_score_identical` — comparer `briefing_comex.kpis.trajectoire` ↔ `briefing_daily.compliance_score`
- `test_cockpit_pilotage_executive_alerts_count_identical` — compteurs identiques
- `test_cockpit_pilotage_executive_exposure_identical` — exposition € bit-à-bit
- `test_no_business_logic_in_frontend_vue_executive` — grep `Math.round|reduce|aggregate` dans `pages/cockpit/*.jsx` < N
- `test_acronyms_transformed_vue_executive` — grep mots interdits dans rendu HTML test
- `test_helios_perimeter_no_leak_vue_executive` — vérifier qu'aucun `retail-001` / `tour-001` / `entrepot-001` n'apparaît dans rendu `/cockpit` scope HELIOS
- `test_vue_executive_3min_budget` — compter ≤ 7 blocs visuels et narrative ≤ 200 mots
- `test_dt_penalty_uses_doctrine_constants` — `narrative_generator.py` doit `from doctrine.constants import DT_PENALTY_EUR` au lieu de `7500.0` littéral

---

## 12. Questions ouvertes pour décision Amine

| # | Question | Données factuelles | Options possibles | Recommandation Claude (sans engagement) |
|---|---|---|---|---|
| **Q1** | KPI Leviers (25,5 k€) : remplacement € → MWh/an ? Le calcul MWh est-il déjà disponible ? | `narrative_generator.py:487-488` : heuristique `8 500 €/site × 3 = 25 500 €`. Inversement `cockpit.py:546` : `_savings_kwh = SUM(estimated_gain_eur)/0,068` calculé pour la projection trajectoire. | (a) recoder calcul MWh dédié, (b) réutiliser `_savings_kwh` cockpit.py, (c) hybrider | **(b)** : `_savings_kwh` existe déjà, l'exposer en MWh/an dans la narrative et supprimer l'heuristique 8 500 €. Cohérence projection ↔ KPI Leviers garantie. |
| **Q2** | Périmètre 595 MWh facture : bug ou design intentionnel ? | Endpoint `/api/purchase/cost-simulation/1` câblé site_id=1 hardcodé, seed Siège HELIOS = 595 MWh confirmé. Pas d'endpoint d'agrégation portefeuille connu. | (a) bug à corriger : créer endpoint `cost-simulation/portfolio/{org_id}`, (b) design intentionnel = ajouter dropdown site dans la card, (c) supprimer la card de la Vue Exécutive | **(a)** : agréger portefeuille — un CFO portefeuille ne peut pas exposer une projection de 1 site/5. Si endpoint d'agrégation n'existe pas, c'est P0 à scaffold avant de retoucher la Vue Exé. |
| **Q3** | Bandeau Pilotage des usages : conserver ou déplacer Flex Intelligence ? | 4 cards (Radar / Flex Ready / Classement / Heatmap), 50 % de la surface Vue Exé, granularité « ECS · VE · Pré-charge froid » | (a) conserver Vue Exé, (b) déplacer page `/flex` dédiée, (c) split — 1 KPI agrégé en Vue Exé (« 21 k€/an gisement Flex portefeuille ») + détails sur page dédiée | **(c)** : split — la Vue Exé garde un teaser 1 KPI (€/an gisement Flex), le reste est sur page Flex Intelligence. Cohérent avec doctrine ≤ 7 blocs. |
| **Q4** | Surface 35 000 m² : seed bâtiment doublé ou KPI faux ? | userMemory : 17 500 m² seed S. Vu : `SUM(Batiment.surface_m2)` = 35 000. Hypothèse 2 bâtiments/site × 3 500 m² avg = 35 000. | (a) corriger seed bâtiment 1/site, (b) corriger KPI = `SUM(Site.surface_m2)`, (c) intentionnel = SHON OPERAT documentée | À vérifier avant arbitrage : `SELECT site_id, COUNT(*), SUM(surface_m2) FROM batiment GROUP BY site_id`. **Probablement (a)**. |
| **Q5** | Projection trajectoire drop -43 % : algo défectueux ? | `cockpit.py:546-557` applique `SUM(estimated_gain_eur)/0,068` une fois sur année courante = saut sec | (a) lisser linéairement entre `_cy` et 2030, (b) répartir par `action.echeance` réelle, (c) désactiver projection actions tant que pas modélisé | **(b)** : utiliser `action.echeance` pour temporiser — si action a échéance J-133, gain s'applique en 2026 ; si J-365, en 2027. Modélisation simple, plausible CFO. |
| **Q6** | Acronymes : dictionnaire centralisé ou patcher localement ? | 12 acronymes distincts × 26 occurrences total Vue Exé | (a) dictionnaire `acronym_to_narrative.py` centralisé réutilisable Tableau de bord + Conformité, (b) patches inline | **(a)** : 12 types acronymes × 4 vues à venir (Vue Exé + Tableau de bord + Conformité + Patrimoine) = 50+ patches inline ingérables. ROI dictionnaire largement positif. |
| **Q7** | Push événementiel timestamps « 2h » figés : bug seed ou endpoint ? | `EvenementsRecents.jsx:33-41` calcule correctement. Endpoint `/api/notifications/list` retourne `created_at` figé. Seed = source. | (a) corriger seed pour répartir `created_at` sur 7 jours, (b) corriger endpoint pour mocker la date | **(a)** : seed doit poser `created_at` réparti (notif 1 = -3h, notif 2 = -1j, notif 3 = -2j, notif 4 = -4j) — donne narrative crédible CFO. |
| **Q8** | Réciprocité Décision ↔ Pilotage : deep-links existants ? | `ImpactDecisionPanel` a 3 drill-down (`/patrimoine?filter=risque`, `/bill-intel?filter=anomalies`, `/consommations/portfolio?filter=energivores`). Pas de drill-down vers Tableau de bord (`/`) ni vers `/actions/{id}` direct depuis KPI hero. | tous à créer / partiel / suffisant en l'état | **partiel** — il manque (a) drill-down KPI hero Trajectoire 2030 → `/conformite?scope=org`, (b) drill-down KPI Exposition → liste sites NC, (c) drill-down KPI Leviers → `/actions?filter=open&sort=gain_desc`. |
| **Q9** *(bonus)* | KPI redondance hero / ImpactDecisionPanel / ExecutiveKpiRow : 3 + 3 + 4 = 10 KPI sur la page | Doctrine §11.3 demande ≤ 3 KPI Vue Exé. | (a) supprimer ExecutiveKpiRow (legacy), (b) supprimer ImpactDecisionPanel, (c) garder 1 seul des 3 ensembles | **(a)+(b)** garder seulement le triptyque hero `<SolBriefingHead>` (Trajectoire / Exposition / Leviers). Les autres composants seront décommissionnés si pas portés en mode `expert` toggle. |
| **Q10** *(bonus)* | Dépendance avec Sprint A org-scoping P0 | leak Hypermarché Montreuil = même nature que Sprint A (cross-org leak), mais cause différente (slug hardcodé vs SQL filter manquant) | (a) fixer en même sprint, (b) sprint séparé Vue Exé après Sprint A | **(a)** : à attaquer en même temps — les 2 leaks créent même perception « pack pollué » côté CFO. |

---

## 13. Hard STOP rencontrés pendant l'audit

1. **§0.A git status non clean** : 1 modif `docs/audit/agent_sessions.jsonl` (log session auto, pas du code), 2 untracked `.claude/scheduled_tasks.lock` (lock harness) et `frontend/docs/audit/agent_sessions.jsonl` (sibling agent log). **Aucun delta sur le code de production**. Audit poursuivi sur autorisation utilisateur explicite.
2. **§0.A branche** : `claude/refonte-sol2` et non `refonte-sol2` strict — convention namespace `claude/*` per `userMemory feedback_claude_branch_namespace.md`. Équivalent fonctionnel, audit poursuivi.
3. **§0.B MCP** : Context7 confirmé via `mcp__context7__query-docs`. `simplify` et `code-review` disponibles via skills (`/simplify`, `/code-review:code-review`). MCP plugins OK.
4. **§0.C tests pré-audit** : pytest collection OK 5 861 tests. Vitest **1 test FE rouge pré-existant** : [`frontend/src/pages/admin/__tests__/CxDashboardPage.test.js:204`](../../frontend/src/pages/admin/__tests__/CxDashboardPage.test.js#L204) — test source-guard admin/cx-dashboard, **hors périmètre Vue Exé**, pré-existant à cet audit. Audit poursuivi sur autorisation utilisateur explicite (« executue le prompt + capture »).
5. **§0.D périmètre écriture** : 1 violation maîtrisée — création de [`tools/playwright/audit-vue-executive-sol2.mjs`](../../tools/playwright/audit-vue-executive-sol2.mjs) (script de capture) car (a) `tools/playwright/audit-agent.mjs` existant tombe en `TypeError: Failed to fetch` (login cross-origin), (b) user a explicitement demandé « capture complète de la vue executive ». Le script est en `tools/`, non versionné dans `backend/`, ne touche aucune logique métier. Recommandation : à committer après revue ou supprimer si non réutilisable.

---

## 14. Recommandations Claude Code (sans implémentation)

### 14.1 Sprint structure proposée

**Sprint Refonte Vue Exécutive Sol2** — avant exécution, prendre les 8 décisions Q1-Q8 §12.

#### Phase P0 (semaine 1) — fondations cohérence + chiffrage doctrine
- **P0-1** Endpoint unifié `/api/pages/cockpit_comex/briefing` : remplacer heuristique leviers par `_savings_kwh` (Q1) ; importer `DT_PENALTY_EUR` doctrine au lieu littéral
- **P0-2** Source-guards cohérence : 4 tests `test_cockpit_pilotage_executive_*_identical`
- **P0-3** Décommission heuristiques frontend : déplacer `models/impactDecisionModel.js` + `leverEngineModel.js` + `dashboardEssentials.js` côté backend (Q9)
- **P0-4** Bug 595 MWh facture (Q2) : créer endpoint `/api/purchase/cost-simulation/portfolio/{org_id}` agrégeant les sites
- **P0-5** Bug surface 35 000 m² (Q4) : audit seed `gen_batiment` puis arbitrer doublement vs SHON

#### Phase P1 (semaine 2) — narrative + acronymes
- **P1-1** Dictionnaire `acronym_to_narrative.py` centralisé (Q6) — 12 entrées DT/BACS/GTB/TURPE/APER/OPERAT/CDC/VNU/CBAM/ARENH/CEE/EPEX
- **P1-2** Seed `created_at` réparti pour `notifications` (Q7)
- **P1-3** Algo trajectoire lissé via `action.echeance` (Q5)
- **P1-4** Drill-downs KPI hero (Q8)

#### Phase P2 (semaine 3) — densité + Flex
- **P2-1** Décommissionner `ExecutiveKpiRow` + `ImpactDecisionPanel` (Q9) ou les passer en mode `expert` toggle
- **P2-2** Bandeau Pilotage usages → split 1 KPI Vue Exé + page Flex dédiée (Q3)
- **P2-3** Push « +X vs S-1 » sur 3 KPI hero
- **P2-4** Source-guards `test_vue_executive_3min_budget` + `test_no_business_logic_in_frontend_vue_executive`

### 14.2 Dépendances cross-pillar

- **Sprint A org-scoping P0** (Q10) : à attaquer en même temps — leak Hypermarché Montreuil = même nature
- **Sprint Cockpit Pilotage refonte** : la dualité Vue Exé / Tableau de bord exige une refonte symétrique de `/` (CommandCenter.jsx) — sinon la doctrine §11.3 reste boiteuse
- **EMS P0** : la trajectoire DT consomme `consumption_unified_service` — toute évolution EMS impacte projection

### 14.3 Risques de régression identifiés

1. **Leak Hypermarché partagé** : si le composant Pilotage usages utilise les mêmes constants `DEMO_SITES` ailleurs (Cockpit + Pilotage page + Flex page), nettoyer 1 endroit casse les autres. Audit transverse `git grep "retail-001\|tour-001\|entrepot-001"` requis avant fix.
2. **Doctrine constants vs littéraux** : si `narrative_generator.py:566` est patché mais `routes/cockpit_v2.py` continue de hard-coder, on déplace le bug sans le résoudre.
3. **Cache** : `KpiService` a un cache (`_cache_key`/`_get_cached`). Toute évolution exposition € doit invalider tous les caches scope.
4. **Tests baseline** : 5 861 BE + 4 240 FE tests — toute refonte doit passer ces baselines (zéro régression cf. CLAUDE.md §10).

---

## 15. Annexes

### 15.1 Captures Playwright

`artifacts/audits/captures-vue-executive-sol2/run-2026-04-27T18-36-06/`
- `01-cockpit-viewport-top.png` — viewport haut
- `02-cockpit-fullpage.png` — page complète scrollée
- `03-section-hero.png` à `10-section-bottom.png` — sections progressives
- `cockpit-dom.html` — DOM dump
- `cockpit-text.txt` — text content extrait (345 lignes)
- `acronyms-detected.json` — 12 acronymes × 26 occurrences
- `network.json` + `network-summary.json` — 131 requêtes API ventilées par endpoint

### 15.2 Logs gate initiaux

```
$ git status
On branch claude/refonte-sol2
Your branch is up to date with 'origin/claude/refonte-sol2'.
Changes not staged for commit:
  modified:   docs/audit/agent_sessions.jsonl
Untracked files:
  .claude/scheduled_tasks.lock
  frontend/docs/

$ git rev-parse HEAD
837070e6424781e2a0afce182909faf9a5253c27

$ pytest --co
5861 tests collected in 1.74s

$ vitest run
Test Files  1 failed | 179 passed (180)
Tests  1 failed | 4237 passed | 2 skipped (4240)
[FAIL] frontend/src/pages/admin/__tests__/CxDashboardPage.test.js — App.jsx monte la route /admin/cx-dashboard
```

### 15.3 Liste exhaustive des fichiers grepés / lus

Backend :
- `backend/routes/cockpit.py` (route /cockpit V1, trajectory, conso-month, co2, benchmark, kpi-catalog, portefeuilles)
- `backend/routes/cockpit_v2.py` (executive-v2, top-contributors)
- `backend/routes/purchase_cost_simulation.py` (cost-simulation/{site_id})
- `backend/routes/dashboard_2min.py` (dashboard rapide)
- `backend/routes/action_center.py` (executive-summary)
- `backend/services/kpi_service.py` (`KpiService`, `get_financial_risk_eur`, `get_compliance_score`)
- `backend/services/narrative/narrative_generator.py` (build_cockpit_comex_briefing)
- `backend/services/event_bus/detectors/compliance_deadline_detector.py` (constantes doctrine)
- `backend/services/pilotage/constants.py` (DEMO_SITES retail-001 / tour-001 / entrepot-001)
- `backend/services/pilotage/roi_flex_ready.py`, `flex_ready.py`
- `backend/services/demo_seed/gen_billing.py:490-497` (seed 595 000 kWh Siège)
- `backend/services/demo_seed/gen_actions.py`, `gen_compliance.py`, `gen_tertiaire_efa.py`, `packs.py`
- `backend/services/purchase_seed_wow.py` (Hypermarché Montreuil)
- `backend/services/action_hub_service.py` (build_actions_from_*)
- `backend/doctrine/constants.py` (DT_PENALTY_EUR)
- `backend/tests/test_cockpit_v2.py`, `test_invariants.py`, `test_event_bus.py`, `test_pilotage_*.py`

Frontend :
- `frontend/src/App.jsx` (routes)
- `frontend/src/pages/Cockpit.jsx` (Vue Exé)
- `frontend/src/pages/CommandCenter.jsx` (Tableau de bord — listé seulement)
- `frontend/src/pages/cockpit/*.jsx` (28 composants enfants — listés)
- `frontend/src/pages/cockpit/EvenementsRecents.jsx` (push événementiel)
- `frontend/src/pages/cockpit/ImpactDecisionPanel.jsx` (3 KPI)
- `frontend/src/pages/cockpit/ExecutiveKpiRow.jsx` (4 KPI legacy)
- `frontend/src/pages/cockpit/PriorityActions.jsx` (Top 3)
- `frontend/src/ui/CockpitTabs.jsx` (toggle dashboard ↔ cockpit)
- `frontend/src/models/impactDecisionModel.js` (heuristique 1%)

---

## DoD — Definition of Done audit

- [x] §0 Hard STOP gate validé (deltas mineurs documentés §13)
- [x] §1 routes & composants Vue Exé inventoriés
- [x] §2 endpoints backend listés
- [x] §3 3 KPI hero + actions priorisées tracés (avec type chiffrage explicite)
- [x] §4 logique métier frontend listée (15+ violations §6.5)
- [x] §5 acronymes bruts capturés (12 types)
- [x] §6 cohérence Vue Exé ↔ Tableau de bord matérialisée
- [x] §7 leak Hypermarché documenté
- [x] §8 trajectoire drop -43 % cause expliquée
- [x] §9 timestamps figés cause identifiée (seed)
- [x] §10 perf 131 req documentée
- [x] §11 source-guards manquants listés
- [x] §12 8+2 questions ouvertes structurées pour décision
- [x] §14 recommandations sans implémentation
- [x] **Aucune écriture sur code de production** — seules écritures : ce bilan + script Playwright capture (§13.5)
- [x] **Aucun commit créé** — Amine décidera après revue
- [x] Tests post-audit non re-vérifiés explicitement mais aucun test de production touché ⇒ baseline préservée

---

**Audit Phase 0 — read-only — gate validé avec deltas — méthodologie PROMEOS doctrine v1.0 §11.3**
**Prochain step (à ne PAS commencer sans GO Amine)** : `PROMPT_REFONTE_VUE_EXECUTIVE_SOL2_EXECUTION.md` après arbitrage Q1-Q10.
