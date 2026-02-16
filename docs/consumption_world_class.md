# Consommations World-Class (Sprint V10)

## Vue d'ensemble

Sprint V10 ajoute 4 modules avances pour l'analyse des consommations electriques et gaz :

| Module | Description | Route API |
|--------|-------------|-----------|
| **Tunnel** | Enveloppe quantile P10-P90 par creneau horaire | `GET /api/consumption/tunnel` |
| **Objectifs** | CRUD objectifs/budgets + progression + prevision | `CRUD /api/consumption/targets` |
| **HP/HC** | Grilles tarifaires versionnees + ratio HP/HC | `CRUD /api/consumption/tou_schedules` |
| **Gaz** | Resume conso gaz, base ete, sensibilite meteo (beta) | `GET /api/consumption/gas/summary` |

## Architecture

### Backend

#### Nouveaux modeles

- **ConsumptionTarget** (`consumption_targets`) : objectifs mensuels/annuels par site avec kWh, EUR, CO2e
- **TOUSchedule** (`tou_schedules`) : grilles HP/HC versionnees avec dates d'effet et fenetres JSON

#### Nouveaux services

| Service | Fichier | Responsabilite |
|---------|---------|----------------|
| tunnel_service | `services/tunnel_service.py` | Calcul envelope P10-P90, score outside, confiance |
| targets_service | `services/targets_service.py` | CRUD targets + progression/forecast |
| tou_service | `services/tou_service.py` | CRUD TOU schedules + ratio HP/HC |

#### Endpoints (sur `/api/consumption`)

| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/tunnel` | Enveloppe P10-P90 pour un site |
| GET | `/targets` | Liste objectifs par site/annee |
| POST | `/targets` | Creer un objectif (upsert) |
| PATCH | `/targets/{id}` | Modifier un objectif |
| DELETE | `/targets/{id}` | Supprimer un objectif |
| GET | `/targets/progression` | Progression vs objectif avec forecast |
| GET | `/tou_schedules` | Liste grilles HP/HC |
| GET | `/tou_schedules/active` | Grille active a une date |
| POST | `/tou_schedules` | Creer version grille |
| PATCH | `/tou_schedules/{id}` | Modifier grille |
| DELETE | `/tou_schedules/{id}` | Desactiver grille |
| GET | `/hp_hc` | Ratio HP/HC avec couts ventiles |
| GET | `/gas/summary` | Resume conso gaz |

### Frontend

#### Page : ConsumptionExplorerPage (`/consumption-explorer`)

4 onglets :

1. **Tunnel** : AreaChart P10-P90, selecteur jour-type (semaine/weekend), KPI cards (releves, % hors bande)
2. **Objectifs** : BarChart objectif vs reel, formulaire d'ajout, table CRUD, banniere alerte (on_track/at_risk/over_budget)
3. **HP/HC** : barre de ratio, KPI grid (HP/HC/Total en kWh + EUR), table plages horaires
4. **Gaz (beta)** : BarChart conso journaliere, KPI cards (total, moyenne, base ete)

#### API (17 fonctions dans api.js)

```javascript
getConsumptionTunnel(siteId, days, energyType)
getConsumptionTargets(siteId, energyType, year)
createConsumptionTarget(data)
patchConsumptionTarget(id, data)
deleteConsumptionTarget(id)
getTargetsProgression(siteId, energyType, year)
getTOUSchedules(siteId, meterId, activeOnly)
getActiveTOUSchedule(siteId, meterId, refDate)
createTOUSchedule(data)
patchTOUSchedule(id, data)
deleteTOUSchedule(id)
getHPHCRatio(siteId, meterId, days)
getGasSummary(siteId, days)
```

## Confiance (Confidence Gating)

Chaque module retourne un niveau de confiance :

| Niveau | Condition | Badge |
|--------|-----------|-------|
| **high** | ratio >= 0.8 et readings >= 500 | Vert |
| **medium** | ratio >= 0.5 et readings >= 200 | Ambre |
| **low** | sinon | Rouge |

## Tests

- **Backend** : 51 tests dans `test_consumption_v10.py`
  - TestTunnelService (6), TestTunnelEndpoint (3)
  - TestTargetsService (8), TestTargetsEndpoint (6)
  - TestTOUService (8), TestTOUEndpoint (6)
  - TestGasSummary (3), TestConfidenceGating (3)
  - TestEdgeCases (7)
- **Frontend** : 6 tests (smoke + API contract validation)
- **Total suite** : 931 backend, 6 frontend

## Format TOU Schedule (JSON)

```json
{
  "windows": [
    {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP", "price_eur_kwh": 0.18},
    {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC", "price_eur_kwh": 0.13},
    {"day_types": ["weekend", "holiday"], "start": "00:00", "end": "24:00", "period": "HC", "price_eur_kwh": 0.13}
  ]
}
```

## References externes

- CRE TURPE 7 : grille tarifaire officielle
- Enedis SGE : portail donnees compteurs elec
- GRDF API : donnees compteurs gaz
