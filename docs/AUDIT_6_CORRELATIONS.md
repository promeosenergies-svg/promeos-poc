# Audit des 6 Corrélations Analytics — PROMEOS PoC

**Date** : 2026-04-03  
**Périmètre** : `c:\Users\amine\promeos-poc\promeos-poc` (backend + frontend)  
**Méthode** : Exploration exhaustive du codebase (modèles, services, routes, composants, tests, seed)

---

## Verdict global

| # | Corrélation | Statut | Couverture | Verdict |
|---|-------------|--------|------------|---------|
| 1 | Signature DJU × Usage | **IMPLÉMENTÉ** | ~95% | Production-ready |
| 2 | Coût par période tarifaire × Usage | **IMPLÉMENTÉ** | ~95% | Production-ready |
| 3 | Potentiel flexibilité × Usage | **IMPLÉMENTÉ** | ~90% | Production-ready |
| 4 | Optimisation puissance souscrite | **IMPLÉMENTÉ** | ~90% | Production-ready |
| 5 | Stratégie achat × profil CDC | **IMPLÉMENTÉ** | ~95% | Production-ready |
| 6 | Score flex composite portefeuille | **IMPLÉMENTÉ** | ~85% | Fonctionnel, améliorable |

**Les 6 corrélations identifiées dans le rapport de recherche sont déjà implémentées dans le codebase PROMEOS.** Les écarts restants sont mineurs (paramétrage, tests dédiés, intégrations UI secondaires).

---

## 1. Signature DJU × Usage (Thermosensibilité)

### Statut : COMPLET

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Service DJU | `backend/services/weather_dju_service.py` (214 lignes) | Calcul DJU COSTIC base 18°C, API Open-Meteo (archive + prévisions), fallback synthétique en mode démo |
| Service Signature | `backend/services/energy_signature_service.py` (256 lignes) | Modèle E = a·DJU + b, régression linéaire (numpy.polyfit ou OLS manuel), benchmarks par archétype |
| Route API | `GET /api/usages/energy-signature/{site_id}` | Params: `months` (3-36, défaut 12). Retourne : signature (a, b, R²), benchmark, savings_potential, scatter_data, regression_line |
| Tests | `backend/tests/test_energy_signature.py` (85 lignes) | Benchmarks archétypes, régression parfaite/bruitée, intégration DB |
| Tests DJU | `backend/tests/test_weather_dju.py` (100+ lignes) | Calcul DJU chauffage/clim, résolution coordonnées, validation synthétique |

**Benchmarks intégrés** : bureau, hotel, enseignement, entrepot, usine, magasin, commerce, santé, collectivité, copropriété, logement_social

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Panel signature | `frontend/src/pages/consumption/SignaturePanel.jsx` | Heatmap consommation (jour×heure), scatter plot + droite de régression, CTA drill-down |

### Écarts mineurs
- Pas de visualisation brute des DJU dans l'UI (seulement la signature dérivée)
- Signature par usage individuel non exposée (agrégée au niveau site)

---

## 2. Coût par période tarifaire × Usage

### Statut : COMPLET

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Classificateur TURPE 7 | `backend/services/tariff_period_classifier.py` (68 lignes) | 5 classes : HPH, HCH, HPB, HCB, Pointe. Ratios prix (P=1.30, HPH=1.00, HPB=0.78, HCH=0.62, HCB=0.50). Réf. CRE n°2025-78 |
| Service coûts | `backend/services/cost_by_period_service.py` (141 lignes) | Ventilation kWh×€ par usage et période, détection optimisation HP→HC (seuil 70%), simulation décalage 1h (12% capturable), calcul économies |
| Route API | `GET /api/usages/cost-by-period/{site_id}` | Params: `months` (1-36, défaut 12). Retourne : by_period, optimization, hp_pct, ventilation par usage |
| Config prix | `backend/config/default_prices.py` | Élec 0.068 €/kWh, HC 0.055 €/kWh. Cascade : Contrat → Spot 30j → SiteTariffProfile → Fallback |
| Config TURPE | `backend/config/tarif_loader.py` + `tarifs_reglementaires.yaml` | Grilles tarifaires YAML (10 KB) |
| Modèles | `backend/models/tou_schedule.py`, `site_tariff_profile.py`, `tariff_calendar.py` | TOUSchedule (fenêtres HP/HC JSON), saisonnalisation Phase 2 TURPE 7 |

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Panel HP/HC | `frontend/src/pages/consumption/HPHCPanel.jsx` | Ratio HP/HC en barre, badge confiance, nom calendrier, ventilation par usage |
| Card coûts | `frontend/src/components/usages/CostCard.jsx` | Visualisation ventilation coûts par période |
| API client | `frontend/src/services/api/energy.js` (L424-425) | `getCostByPeriod(siteId, months)` |

### Écarts mineurs
- Pas de fichier test dédié `test_cost_by_period.py` (couverture implicite via intégration)
- Période Pointe classifiée mais moins mise en avant dans l'UI

---

## 3. Potentiel flexibilité × Usage

### Statut : COMPLET (architecture riche)

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Scoring flex | `backend/services/flex/flexibility_scoring_engine.py` (220+ lignes) | 15 profils d'usage, classification NEBCO (OUI_NATURELLE, OUI_MULTISITE, PORTFOLIO...), scores pilotabilité 0-1, 7 mécanismes mappés |
| Service NEBCO | `backend/services/flex_nebco_service.py` | kW pilotables par usage, seuil ≥100 kW, revenus 80-200 €/kW/an NEBCO + 45 €/kW/an capacité, ROI BACS (25k€/site) |
| Éligibilité NEBCO | `backend/services/power/nebco_eligibility_engine.py` | Seuil 100 kW, validation compteur (télérelevé vs Linky), complétude données (12+ mois, >50%), 3 types modulation, discipline décalage |
| Assessment | `backend/services/flex_assessment_service.py` | 4 dimensions : technical readiness, data confidence, economic relevance, regulatory alignment (0-100 chacune) |
| Mini flex | `backend/services/flex_mini.py` | Scoring heuristique rapide, top 3 leviers (HVAC, IRVE, FROID) |
| Routes API | `backend/routes/flex.py` | `GET /api/sites/{site_id}/flex/mini`, `GET /api/flex/assessment` |
| Routes scoring | `backend/routes/flex_score.py` | `GET /api/flex/score/sites/{site_id}`, `GET /api/flex/score/usages`, `GET /api/flex/score/prix-signal` |
| Route usages | `backend/routes/usages.py` (L118) | `GET /api/usages/flex-potential/{site_id}` — scoring NEBCO + lien BACS↔Flex |

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Card flex | `frontend/src/components/flex/FlexPotentialCard.jsx` | Score, 4 dimensions en barres, top leviers |
| Card NEBCO | `frontend/src/components/usages/FlexNebcoCard.jsx` | kW par usage, badge éligibilité, revenus (NEBCO low/high + capacité), ROI BACS, checklist Go/No-Go (6 items) |
| Bubble chart | `frontend/src/components/usages/FlexBubbleChart.jsx` | X=disponibilité%, Y=complexité, taille=kW pilotable, couleur=revenu (4 tiers : >20k€ vert, 10-20k€ lime, 5-10k€ ambre, <5k€ gris) |
| API client | `frontend/src/services/api/energy.js` | `getFlexPotential()`, `getFlexPortfolio()` |
| API client | `frontend/src/services/api/actions.js` | `getFlexAssets()`, `getFlexAssessment()`, `getFlexScore()`, `getAllUsagesScores()`, `getPrixSignal()` |

### Écarts mineurs
- Tarifs revenus NEBCO hardcodés (80-200 €/kW/an) — pas d'interface admin pour ajuster
- Ratios IFPEB via `FLEX_BY_USAGE` interne, pas exposé comme modèle formel
- Pas d'analyse de sensibilité ou scénarios "what-if" sur les revenus

---

## 4. Optimisation puissance souscrite

### Statut : COMPLET (~90%)

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Détection pics | `backend/services/power/peak_detection_engine.py` (120 lignes) | Algo sur CDC 15min, CMDPS quadratique (12,65 €/kW), analyse par poste tarifaire (HPH, HCH, HPE, HCE, Pointe), coûts dépassement |
| Optimiseur PS | `backend/services/power/subscribed_power_optimizer.py` (128 lignes) | Optimisation PS par poste, analyse P_max réelle vs PS, règles EIR Enedis (BT≥36kVA, HTA≥100kW), économies annuelles, classification risque (OPTIMAL/REDUIRE/RISQUE_DEPASSEMENT) |
| Profil puissance | `backend/services/power/power_profile_service.py` (136 lignes) | KPI : P_max, P_mean, P_base (P5%), énergie totale, facteur de forme, taux utilisation PS |
| Facteur puissance | `backend/services/power/power_factor_analyzer.py` (140 lignes) | Analyse tan φ / cos φ, seuil TURPE 7 (0.4), pénalités réactif, ventilation par poste |
| Routes API | `backend/routes/power.py` (269 lignes) | `GET /api/power/sites/{id}/profile`, `/contract`, `/peaks`, `/optimize-ps`, `/factor`, `/nebco` |
| Modèles | `backend/models/power.py` (150 lignes) | `PowerReading` (P_active_kw, P_reactive_ind_kvar, periode_tarif), `PowerContract` (ps_par_poste_kva, FTA), segments TURPE 7 (C4, C2) |

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Panel puissance | `frontend/src/components/power/PowerPanel.jsx` (184 lignes) | KPI (P.Max, P.Baseload, utilisation PS, tan φ), PS par poste, pics détectés + coût CMDPS, recommandations optimisation, pénalités facteur puissance |
| API client | `frontend/src/services/api/energy.js` (L452-468) | `getPowerProfile()`, `getPowerContract()`, `getPowerPeaks()`, `getPowerFactor()`, `getPowerOptimizePs()` |

### Écarts mineurs
- CMDPS calculé à la demande, pas historisé en DB (pas de tendance sur 12 mois)
- Granularité TURPE 10min vs mesure 15min (approximation acceptable)
- Workflow EIR (SGE F170) signalé mais pas automatisé

---

## 5. Stratégie achat × profil CDC

### Statut : COMPLET (~95%)

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Simulateur CDC | `backend/services/cdc_contract_simulator.py` (257 lignes) | Caractérisation CDC (baseload_ratio, seasonality_index, hp_ratio), 4 stratégies simulées (Fixe 12m, Indexé EPEX, Mixte baseload/pointe, THS Heures Solaires), ratios mensuels EPEX Spot (0.68-1.40), recommandation automatique par profil |
| Service achat | `backend/services/purchase_service.py` (279 lignes) | Estimation conso annuelle, facteur profil (flat=0.85, peak=1.25), 4 scénarios (Fixe, Indexé, Spot, RéFlex Solar), blocs horaires RéFlex Solar, score effort, report HP→solaire, P10/P90 |
| Pricing marché | `backend/services/purchase_pricing.py` | Prix forward/spot, volatilité P10/P90, contexte marché |
| Routes API | `backend/routes/purchase.py` | `POST /api/purchase/estimate/{site_id}`, `/preferences/{site_id}`, `/compute/{site_id}`, `GET /results/{site_id}`, `POST /accept/{site_id}` |
| Modèles | `backend/models/purchase_models.py` | `PurchaseAssumptionSet`, `PurchaseScenarioResult`, `PurchaseStrategy` enum (FIXE, INDEXE, SPOT, REFLEX_SOLAR) |

**Matching profil → contrat :**
| Profil CDC | Stratégie recommandée |
|------------|----------------------|
| `baseload_dominant` (data center) | Fixe 12 mois |
| `saisonnier_fort` (chaufferie) | Indexé EPEX Spot |
| `bureau_classique` | THS ou Fixe |
| `mixte` | Hybride baseload/pointe |

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Page achat | `frontend/src/pages/PurchasePage.jsx` | Contexte marché, 4 cards scénarios, badges risque, métriques confiance, roll-up portefeuille, tracking renouvelable, workflow RéFlex Solar |
| API client | `frontend/src/services/api/purchase.js` | `getPurchaseEstimate()`, `computePurchaseScenarios()`, `getPurchaseResults()`, `getMarketContext()` |

### Écarts mineurs
- Pas de connecteur API EPEX direct (prix de référence en fallback)
- Pas d'intégration prix forward réels (Platts, TradingView)
- Classification CDC limitée à 4 archétypes (extensible)
- Pas d'empreinte carbone par stratégie

---

## 6. Score flex composite portefeuille

### Statut : IMPLÉMENTÉ (~85%)

### Backend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Agrégation portfolio | `backend/services/flex_nebco_service.py` (L172-214) | `compute_flex_portfolio()` : agrège kW pilotables, compte sites NEBCO-éligibles, revenu mid-point, ROI BACS portfolio, enrichissement bulle via `_enrich_site_for_portfolio()` |
| Score pondéré | `backend/services/flex_score.py` (L178) | `get_portfolio_flex_score()` : batch meters + usage profiles, score pondéré par surface, détail par site |
| Routes API | `backend/routes/flex_score.py` (L177) | `GET /api/flex/score/portfolios/{portfolio_id}` — score agrégé pondéré surface |
| Routes API | `backend/routes/flex.py` (L301) | `GET /api/flex/portfolios/{portfolio_id}/flex-prioritization` — ranking sites |
| Routes API | `backend/routes/usages.py` (L130) | `GET /api/usages/flex-portfolio` — agrège tous les sites du périmètre |

### Frontend

| Composant | Fichier | Description |
|-----------|---------|-------------|
| Summary portefeuille | `frontend/src/components/flex/FlexPortfolioSummary.jsx` | Total sites, total kW, score flex moyen, top 5 sites par flex_score, comptage assets |
| Bubble chart | `frontend/src/components/usages/FlexBubbleChart.jsx` | Visualisation portfolio : disponibilité × complexité × kW × revenu (4 tiers couleur) |
| API client | `frontend/src/services/api/actions.js` | `getFlexPortfolio()`, `getPortfolioFlexScore()` |

### Écarts identifiés
- **Pas de matrice de priorisation** avec quadrants (Quick Wins, Stratégique, Complexe, Low-Impact)
- KPI portfolio calculés dynamiquement, pas persistés (contrairement au niveau site)
- Pondération composite = moyenne surface uniquement (pas de pondération configurable technical/data/economic)
- Pas d'historique du score portfolio dans le temps

---

## Socle de données

### Modèles fondamentaux — Tous en place

| Modèle | Table | Champs clés | Statut |
|--------|-------|-------------|--------|
| `MeterReading` | `meter_reading` | meter_id, timestamp, frequency(MIN_15), value_kwh, is_estimated, quality_score | ✅ 35k records/meter/an |
| `Usage` | `usages` | batiment_id, type(12 enum), surface_m2, data_source(6 enum), pct_of_total, is_significant | ✅ |
| `EnergyContract` | `energy_contracts` | tariff_option(BASE/HP_HC/CU/MU/LU), subscribed_power_kva, prix par classe, indexation | ✅ |
| `EnergyInvoice` | `energy_invoices` | period_start/end, total_eur, energy_kwh + lignes détaillées (period_code) | ✅ |
| `TOUSchedule` | `tou_schedules` | windows_json (HP/HC), saisonnalisation, prix par classe | ✅ |
| `PowerReading` | `power_reading` | P_active_kw, P_reactive_ind_kvar, periode_tarif | ✅ |
| `PowerContract` | `power_contract` | ps_par_poste_kva, FTA, meter type | ✅ |
| `Site` | `sites` | type(10 enum), surface_m2, lat/lon, code_postal, NAF, tertiaire_area_m2 | ✅ |
| `Batiment` | `batiments` | surface_m2, annee_construction, cvc_power_kw | ✅ |
| `DeliveryPoint` | `delivery_points` | PRM/PCE, tariff_segment(C5/C4/C3), puissance_souscrite_kva, reprog HC | ✅ |

### Hiérarchie données

```
Site (1:N)
  ├─ DeliveryPoint (PRM/PCE)
  │   └─ Contracts (1:N via ContractDeliveryPoint)
  ├─ Meter
  │   ├─ MeterReading (15min, horaire, journalier, mensuel)
  │   ├─ PowerReading (CDC 30min)
  │   ├─ PowerContract (paramètres tarifaires par poste)
  │   ├─ TOUSchedule (fenêtres HP/HC)
  │   └─ Usage (via usage_id FK)
  ├─ Batiment
  │   └─ Usage (1:N classifications énergie)
  ├─ EnergyContract
  │   └─ EnergyInvoice (1:N)
  │       └─ EnergyInvoiceLine (1:N, period_code)
  └─ TertiaireEfa (conformité réglementaire)
```

### Lacunes données mineures

| Lacune | Impact | Workaround existant |
|--------|--------|---------------------|
| Pas de flag GTB/BACS dédié dans `Site` | Corrélation 6 (complexité) | Via `BacsComplianceRule` ou `TertiaireEfa` |
| Occupation (nombre_employes) sparse | Corrélation 2 (activité) | Archétype par TypeSite |
| Operating schedule non formalisé | Corrélation profil CDC | Heuristique par TypeSite dans seed |
| period_code non matérialisé dans MeterReading | Performance requêtes HP/HC | Classificateur à la volée (acceptable) |

---

## Matrice couverture rapport recherche vs implémentation

| Élément du rapport | Attendu | Trouvé dans le codebase | Écart |
|--------------------|---------|-------------------------|-------|
| Régression E = a·DJU + b | OUI | `energy_signature_service.py` | Aucun |
| API `/sites/{id}/signature-dju` | OUI | `GET /api/usages/energy-signature/{site_id}` | Nom différent, fonctionnel |
| DJU base 18°C Météo-France | OUI | Open-Meteo + COSTIC 18°C | Source météo différente (Open-Meteo vs Météo-France), équivalent |
| Ventilation HP/HC/Pointe × usage | OUI | `cost_by_period_service.py` + `tariff_period_classifier.py` | Complet |
| API `/portfolio/{id}/cost-by-period` | OUI | `GET /api/usages/cost-by-period/{site_id}` | Par site, pas par portfolio (agrégeable) |
| Simulation décalage chauffage | OUI | Détection seuil 70% + simulation 12% capturable | Simplifié mais fonctionnel |
| Ratios IFPEB par usage | OUI | `flexibility_scoring_engine.py` (15 usages) | Plus riche que prévu |
| Seuil NEBEF ≥100 kW | OUI | `nebco_eligibility_engine.py` | Complet + 3 types modulation |
| API `/sites/{id}/flex-potential` | OUI | `GET /api/usages/flex-potential/{site_id}` | Exact match |
| Valorisation 80-100 €/kW·an | OUI | 80-200 €/kW·an NEBCO + 45 capacité | Plus détaillé |
| Graphique bulle portfolio | OUI | `FlexBubbleChart.jsx` (4 axes + couleur) | Implémenté |
| CMDPS TURPE 7 | OUI | `peak_detection_engine.py` (12,65 €/kW) | Complet |
| API `/sites/{id}/peak-opt` | OUI | `GET /api/power/sites/{id}/optimize-ps` | Nom différent, fonctionnel |
| Facteur de charge, base-peak | OUI | `cdc_contract_simulator.py` + `purchase_service.py` | Complet |
| 4 stratégies achat | OUI | Fixe, Indexé, Spot, RéFlex Solar (THS) | 4/4 + RéFlex Solar bonus |
| Score composite portefeuille | OUI | `flex_score.py` + `FlexPortfolioSummary.jsx` | Pondéré surface, améliorable |

---

## Recommandations d'amélioration

### Priorité haute (quick wins)

1. **Test dédié `test_cost_by_period.py`** — Couvrir les scénarios de ventilation HP/HC et optimisation décalage
2. **Endpoint portfolio cost-by-period** — Agréger `/cost-by-period` au niveau portefeuille (aujourd'hui site uniquement)
3. **Historisation CMDPS** — Persister les calculs CMDPS mensuels pour afficher la tendance 12 mois

### Priorité moyenne (valeur ajoutée)

4. **Interface admin tarifs flex** — Rendre paramétrables NEBCO_REVENUE_LOW/HIGH (80-200) et CAPACITY_REVENUE (45)
5. **Matrice quadrants portfolio** — Ajouter overlay "Quick Wins / Stratégique / Complexe / Low-Impact" sur le bubble chart
6. **Pondération configurable** — Permettre technical/data/economic weighting dans le score portfolio (pas seulement surface)

### Priorité basse (perfectionnement)

7. **Connecteur EPEX Spot** — Intégrer prix réels Day-Ahead pour la stratégie achat
8. **Flag BACS dans Site** — Ajouter `is_bacs_equipped: bool` pour simplifier le scoring complexité
9. **Matérialisation period_code** — Pré-calculer le code période dans MeterReading pour performance

---

## Conclusion

**Le rapport de recherche identifiait 6 corrélations "manquantes" — l'audit révèle qu'elles sont toutes implémentées dans le codebase PROMEOS**, souvent avec une richesse supérieure aux spécifications du rapport :

- **Signature DJU** : benchmarks par archétype, savings_potential, scatter plot
- **Coûts HP/HC** : classification TURPE 7 conforme CRE, simulation décalage
- **Flex NEBCO** : 15 profils d'usage (vs "quelques ratios IFPEB"), ROI BACS, checklist Go/No-Go
- **Puissance souscrite** : 6 endpoints dédiés, facteur puissance réactif en bonus
- **Achat CDC** : RéFlex Solar (stratégie innovante non prévue dans le rapport)
- **Portfolio flex** : bubble chart 4 axes + couleur revenu, déjà opérationnel

Les 9 recommandations ci-dessus sont des améliorations incrémentales, pas des développements structurels. **La roadmap P0-P2 du rapport est de facto déjà réalisée.**
