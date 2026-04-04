# Stratégies d'achat — Matching profil CDC → contrat

Source: backend/services/purchase_service.py (434 lignes) + backend/services/cdc_contract_simulator.py (256 lignes)

## Matching automatique profil → stratégie

| Profil CDC | Caractéristiques | Stratégie recommandée | Justification |
|---|---|---|---|
| baseload_dominant | Facteur charge >0.7, faible variation | Fixe 12 mois | Budget prévisible, pas de gain spot |
| saisonnier_fort | Seasonality index >1.3, variation hiver/été >40% | Indexé EPEX Spot | Bénéficier des prix bas été |
| bureau_classique | HP/HC ~70/30, facteur charge 0.3-0.5 | THS (Heures Solaires) ou Fixe | HC méridiennes si nouveau contrat |
| mixte | Aucun profil dominant | Hybride baseload/pointe | 70% fixe + 30% spot |

## 4 scénarios simulés dans PROMEOS

### Scénario 1: Fixe 12 mois
- Prix: fixe €/MWh sur 12 mois
- Risque: nul (budget certain)
- Score effort: 1/5
- Profil idéal: PME, budget contraint

### Scénario 2: Indexé EPEX Spot
- Prix: EPEX Day-Ahead + spread fournisseur
- Ratios mensuels EPEX: 0.68 (été) à 1.40 (hiver pointe)
- Risque: élevé (P10/P90)
- Score effort: 4/5

### Scénario 3: Mixte baseload/pointe
- Base (70%): prix fixe
- Pointe (30%): indexé spot
- Risque: modéré
- Score effort: 3/5

### Scénario 4: RéFlex Solar (heures solaires)
- Blocs horaires: solaire (11h-14h prix bas), pointe (17h-20h prix élevé)
- Report de consommation vers HC méridiennes
- Gain estimé: 5-15% vs fixe classique
- Score effort: 3/5
- Prérequis: CRE 2026-33 applicable, nouveau contrat

## Backend PROMEOS

- `backend/services/cdc_contract_simulator.py` (256 lignes) — caractérisation CDC + 4 stratégies
- `backend/services/purchase_service.py` (434 lignes) — estimation, scénarios, P10/P90
- `backend/services/purchase_pricing.py` (233 lignes) — prix forward/spot, volatilité
- Routes: POST /api/purchase/estimate/{site_id}, /compute/{site_id}, GET /results/{site_id}
- Modèles: PurchaseAssumptionSet, PurchaseScenarioResult, PurchaseStrategy enum
