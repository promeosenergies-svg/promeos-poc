# Achat Energie V1 — Sprint 8

## Resume

Module de simulation de scenarios d'achat energie (Fixe / Indexe / Spot) avec risk score, bandes P10-P90, recommandation automatique et integration au Dashboard 2min.

## Modeles (3 tables)

| Table | Description |
|-------|-------------|
| `purchase_assumption_sets` | Hypotheses de simulation par site (volume, profil, horizon) |
| `purchase_preferences` | Preferences utilisateur (tolerance risque, priorite budget, offre verte) |
| `purchase_scenario_results` | Resultats persistes (prix, cout, risk score, P10/P90, recommandation) |

### Enums

- `PurchaseStrategy`: fixe, indexe, spot
- `PurchaseRecoStatus`: draft, accepted, rejected

## Service (4 fonctions)

**Fichier**: `backend/services/purchase_service.py`

| Fonction | Description |
|----------|-------------|
| `estimate_consumption(db, site_id)` | Estime la conso annuelle (MeterReading > Invoice > default 500k) |
| `compute_profile_factor(db, site_id)` | Calcule le facteur de profil (24/7=0.85, bureau=1.25, default=1.0) |
| `compute_scenarios(db, site_id, ...)` | Genere 3 scenarios avec prix, risk, bandes P10-P90 |
| `recommend_scenario(scenarios, ...)` | Score composite + filtre risque → recommandation |

### Logique de prix

- **Fixe**: ref_price x 1.05, risk=15, P10=P90=fixe
- **Indexe**: ref_price x 0.95, risk=45, P10=85%, P90=120%
- **Spot**: ref_price x 0.88 x profile_factor, risk=75, P10=70%, P90=145%

Le prix de reference est resolu via `get_reference_price()` de billing_service (contrat > tarif > default).

### Recommandation

Score = (1-budget_priority) x (100-risk) + budget_priority x savings_normalized

Filtres:
- `risk_tolerance=low` → exclut risk > 50
- `green_preference` → +5 pts pour indexe

## Endpoints (9 routes)

**Prefix**: `/api/purchase`

| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/estimate/{site_id}` | Estimation conso + profil |
| GET | `/assumptions/{site_id}` | Hypotheses existantes ou defaults |
| PUT | `/assumptions/{site_id}` | Creer/mettre a jour hypotheses |
| GET | `/preferences` | Preferences (org_id optionnel) |
| PUT | `/preferences` | Creer/mettre a jour preferences |
| POST | `/compute/{site_id}` | Calculer scenarios + recommander + persister |
| GET | `/results/{site_id}` | Derniers resultats persistes |
| PATCH | `/results/{id}/accept` | Accepter une recommandation |
| POST | `/seed-demo` | Seed demo data (2 sites x 3 scenarios) |

## Frontend

**Page**: `PurchasePage.jsx` (`/achat-energie`)

4 sections:
1. Selection site + estimation conso
2. Hypotheses editables (volume, horizon, energie)
3. Preferences (risque, budget, vert)
4. Resultats: 3 cartes (Fixe/Indexe/Spot) avec prix, risk gauge, P10-P90, badge "Recommande", bouton "Accepter"

**Sidebar**: Achat Energie dans la section Analyse (apres Bill Intelligence)

## Dashboard 2min

Nouveau bloc `achat` dans la reponse GET `/api/dashboard/2min`:
```json
{
  "achat": {
    "total_scenarios": 6,
    "recommendation": {
      "strategy": "indexe",
      "price_eur_per_kwh": 0.171,
      "total_annual_eur": 102600,
      "risk_score": 45,
      "savings_vs_current_pct": 5.0,
      "reco_status": "draft"
    }
  }
}
```

Affiche dans Cockpit2MinPage si `data.achat` est present.

## Seed demo

**Fichier**: `backend/services/purchase_seed.py`

Cree pour 2 sites:
- Site A: elec, 600k kWh/an, profil pointe (1.25), indexe recommande
- Site B: gaz, 300k kWh/an, profil plat (0.85), fixe recommande
- 1 PurchasePreference (medium, budget_priority=0.6)

## Tests

**Fichier**: `backend/tests/test_purchase.py` — 13 tests

- TestModels (3): creation assumption_set, preference, scenario_result
- TestPurchaseService (4): estimation invoice, fallback, 3 strategies, recommend low_risk
- TestPurchaseAPI (6): estimate endpoint, assumptions CRUD, preferences CRUD, compute+results, accept, seed-demo

---

# Achat Energie V1.1 — Sprint 8.1

## Resume

Extension operationnelle du module Achat Energie avec 5 capacites: roll-up portefeuille multi-site, alertes de renouvellement contrat, historique des runs de calcul, actions d'achat standardisees, et integration cockpit enrichie.

## Modifications modeles

### EnergyContract (+2 colonnes)

| Colonne | Type | Description |
|---------|------|-------------|
| `notice_period_days` | Integer, default=90 | Preavis de resiliation en jours |
| `auto_renew` | Boolean, default=False | Reconduction tacite |

### PurchaseScenarioResult (+3 colonnes)

| Colonne | Type | Description |
|---------|------|-------------|
| `run_id` | String(36), index | UUID unique du run de calcul |
| `batch_id` | String(36), index | UUID du batch portfolio (multi-site) |
| `inputs_hash` | String(64) | SHA-256 des hypotheses pour comparaison inter-runs |

## Service — nouvelles fonctions

**Fichier**: `backend/services/purchase_service.py` (+3 fonctions)

| Fonction | Description |
|----------|-------------|
| `get_org_site_ids(db, org_id)` | Resout Organisation → EntiteJuridique → Portefeuille → Site (actifs) |
| `compute_inputs_hash(...)` | SHA-256 des parametres d'entree pour comparaison |
| `aggregate_portfolio_results(results_by_site)` | Agregation ponderee par volume (cout, risque, economies) |

## Purchase Actions Engine (nouveau)

**Fichier**: `backend/services/purchase_actions_engine.py`

Actions ephemeres, calculees, non persistees (pattern identique a `action_plan_engine.py`).

| Type | Priorite | Condition |
|------|----------|-----------|
| `renewal_urgent` | 100 | Preavis ≤ 30j |
| `renewal_soon` | 70 | Preavis 30-60j |
| `renewal_plan` | 40 | Preavis 60-90j |
| `strategy_switch` | 60 | Scenario recommande DRAFT avec savings > 5% |
| `accept_reco` | 50 | Scenario recommande DRAFT en attente de validation |

## Endpoints V1.1 (+5 nouveaux, 2 modifies)

**Prefix**: `/api/purchase`

| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/renewals` | Contrats expirant avec urgence color-coded (red/orange/yellow/gray) |
| GET | `/actions` | Actions d'achat ephemeres triees par priorite |
| POST | `/compute?org_id=X&scope=org` | Roll-up portefeuille: compute tous sites d'une org |
| GET | `/results?org_id=X` | Resultats agreges portefeuille |
| GET | `/history/{site_id}` | Historique des runs de calcul groupes par run_id |
| POST | `/compute/{site_id}` | **Modifie**: +run_id, +inputs_hash, preserve historique |
| GET | `/results/{site_id}` | **Modifie**: filtre par latest run_id |

### Changement important: preservation historique

V1.1 ne supprime plus les anciens resultats lors d'un recalcul. Chaque `POST /compute/{site_id}` genere un nouveau `run_id`, permettant la comparaison inter-runs via `GET /history/{site_id}`.

## Dashboard 2min enrichi

Nouveaux champs dans la reponse `achat`:

```json
{
  "achat": {
    "gain_potentiel_eur": 5130.0,
    "prochain_renouvellement": {
      "end_date": "2026-03-28",
      "site_id": 1,
      "site_nom": "Site A",
      "supplier_name": "EDF Entreprises",
      "days_remaining": 45
    }
  }
}
```

## Frontend V1.1

### PurchasePage.jsx — systeme d'onglets (4 tabs)

1. **Simulation** (existant V1): 4 sections originales
2. **Portefeuille**: calcul multi-site, KPI agreges, tableau par site
3. **Echeances**: contrats expirant avec badges urgence (red/orange/yellow)
4. **Historique**: timeline des runs passes, detail par clic

### Cockpit2MinPage.jsx

Ajout sous le bloc achat: gain potentiel EUR + prochain renouvellement (site + date + jours restants).

### api.js (+5 fonctions)

| Fonction | Route |
|----------|-------|
| `computePortfolio(orgId)` | POST /purchase/compute |
| `getPortfolioResults(orgId)` | GET /purchase/results |
| `getPurchaseRenewals(orgId)` | GET /purchase/renewals |
| `getPurchaseHistory(siteId)` | GET /purchase/history/{siteId} |
| `getPurchaseActions(orgId)` | GET /purchase/actions |

## Seed demo V1.1

Ajout de 2 contrats:
- **Contrat 1**: Site A, elec, EDF Entreprises, expiry 45j, notice=60j, auto_renew=False
- **Contrat 2**: Site B, gaz, Engie Pro, expiry 180j, notice=90j, auto_renew=True

## Tests V1.1 (+12 tests)

**Fichier**: `backend/tests/test_purchase.py` — total: 25 tests (13 V1 + 12 V1.1)

- TestV11Models (3): contract notice_period, contract defaults, scenario run_fields
- TestV11API (9): renewals, history, history_empty, actions, portfolio_compute, portfolio_results, dashboard_2min_v11_fields, compute_preserves_history, seed_demo_v11
