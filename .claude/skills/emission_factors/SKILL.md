---
name: emission_factors
description: Facteurs d'émission CO2e canoniques France — électricité 0.052 kgCO2e/kWh, gaz 0.227, ADEME V23.6. Wrapper de backend/config/emission_factors.py. À charger pour tout calcul CO₂.
triggers: [CO2, CO₂, emission, kgCO2e, ADEME, facteur emission, bilan carbone, GES, empreinte carbone]
source_of_truth: backend/config/emission_factors.py
last_verified: 2026-04-24
---

# Facteurs d'émission CO₂e — Source of truth

## Quand charger cette skill

- ✅ Tout calcul CO₂ (site, portefeuille, action, bilan)
- ✅ Conversion kWh → kgCO₂e / tCO₂e
- ✅ Vérification d'un facteur d'émission utilisé dans un composant ou un endpoint
- ✅ Comparaison inter-vecteurs (élec vs gaz vs fioul)
- ❌ Ne PAS charger pour : prix du kWh (€/kWh) → `tariff_constants` · coût carbone (CBAM, ETS2) → `regulatory_calendar`

## Constantes canoniques (SoT = `backend/config/emission_factors.py`)

| Vecteur | Facteur | Unité | Source | Année | Méthode |
|---|---|---|---|---|---|
| Électricité réseau France | 0.052 | kgCO₂e/kWh | ADEME Base Empreinte V23.6 | 2024 | Mix moyen annuel, ACV |
| Gaz naturel | 0.227 | kgCO₂e/kWh | ADEME Base Empreinte V23.6 | 2024 | PCI, combustion + amont |
| Fioul domestique | 0.324 | kgCO₂e/kWh | ADEME Base Empreinte V23.6 | 2024 | PCI, combustion + amont |
| Bois bûche | 0.030 | kgCO₂e/kWh | ADEME Base Empreinte V23.6 | 2024 | PCI, combustion |

**Vérification triple-source** (doctrine PROMEOS) :
- Source 1 : ADEME Base Empreinte V23.6 (`base-empreinte.ademe.fr`) → 0.0520
- Source 2 : RTE Bilan Électrique 2024 → 21.7 gCO₂eq/kWh (direct) / 30.2 (ACV)
- Source 3 : ADEME Bilans GES (`bilans-ges.ademe.fr`) → cohérent

**Arbitrage** : 0.052 retenu (ADEME primaire, confirmée x3 sources).

## Exemples d'usage dans les prompts agents

**Backend Python** :
```python
from config.emission_factors import get_emission_factor
factor = get_emission_factor("ELEC")   # 0.052
factor = get_emission_factor("GAZ")    # 0.227
co2e_kg = kwh * factor
```

**Frontend React** : jamais de hardcode. Toujours via `useElecCo2Factor()` du `EmissionFactorsContext` (endpoint `GET /api/config/emission-factors`).

**Agent invocation** : `ems-expert` / `bill-intelligence` / `regulatory-expert` chargent cette skill avant tout output CO₂.

## Anti-patterns (FAIL systématique)

- ❌ **`CO2 = 0.0569`** → c'est le tarif **TURPE 7 HPH en €/kWh**, PAS un facteur CO₂. Confusion historique.
- ❌ **`CO2 = 0.0571`** → valeur ADEME V23.5 obsolète (remplacée par 0.052 en V23.6).
- ❌ **Hardcode frontend** : `const CO2E_FACTOR = 0.052` dans un `.jsx` → violation règle d'or zero business logic in frontend. Utiliser `useElecCo2Factor()`.
- ❌ **Conversion tCO₂ direct** sans passer par `get_emission_factor()` → risque de divergence lors d'une mise à jour ADEME (ex: V24.0).
- ❌ **Confondre scope 1/2/3** : ACV ADEME couvre scopes 1+2+3 amont. Ne pas re-sommer avec scope 3 déjà inclus.

## Coefficient énergie primaire (EP)

- Électricité : coefficient EP = **2.3** (RE2020, Décret n°2021-1004)
- Gaz naturel : coefficient EP = 1.0
- Source : Arrêté 4/08/2021 (RE2020). Réduit de 2.58 → 2.3 depuis 2023.

## Mise à jour

Toute mise à jour (V24.0 ADEME) passe par :
1. Modification `backend/config/emission_factors.py`
2. Bump `last_verified` dans ce SKILL.md
3. Test de non-régression endpoint `GET /api/config/emission-factors`
4. Annonce dans memory `project_emission_factors_update_YYYY_MM.md`

## Références

- Code SoT : [backend/config/emission_factors.py](../../../backend/config/emission_factors.py)
- Endpoint API : `GET /api/config/emission-factors`
- Contexte React : `frontend/src/contexts/EmissionFactorsContext.jsx`
- ADEME Base Empreinte : https://base-empreinte.ademe.fr
- RTE Bilan Électrique : https://bilan-electrique-2024.rte-france.com
- Dernière vérification : 2026-04-24
