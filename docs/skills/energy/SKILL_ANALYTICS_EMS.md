---
name: promeos-analytics-ems
description: >
  Expert analytics énergétique et EMS.
  Signature énergétique, DJU, anomalies ML,
  carpet plot, CUSUM ISO50001, optimisation puissance.
version: 2.0.0
tags: [ems, analytics, dju, signature, anomalie, ml, cusum, carpet-plot]
---

# Analytics Énergétique & EMS -- Expert PROMEOS

## 1. Constantes Physiques (source unique : emission_factors.py)

| Constante | Valeur | Source |
|-----------|--------|--------|
| CO2 électricité | **0.052 kgCO2/kWh** | ADEME Base Empreinte V23.6 |
| CO2 gaz naturel | **0.227 kgCO2/kWh** | ADEME Base Empreinte V23.6 |
| Coef. énergie primaire élec | **1.9** (depuis 01/2026) | RE2020 (ancien: 2.3) |

### Erreurs fréquentes à éviter
- 0.0569 = tarif TURPE 7 BT >36kVA HPH (EUR/kWh), PAS un facteur CO2
- 0.0442 = tarif TURPE 7 HTA HPH (EUR/kWh), PAS un facteur CO2
- Toujours utiliser **0.052** pour les calculs CO2 électricité

## 2. Benchmarks de Référence

### OID (Observatoire de l'Immobilier Durable) 2022
| Type | Benchmark (kWhEF/m²/an) |
|------|------------------------|
| Bureaux | **146** (référence PROMEOS) |
| Commerce | 180-250 |
| Enseignement | 90-130 |
| Hôtellerie | 280-350 |
| Entrepôt | 40-80 |

Source : OPERAT, 600M+ m² déclarés, 25 300 bâtiments

## 3. Méthode DJU (Degrés-Jours Unifiés)

### Méthode COSTIC (préférée PROMEOS)
- DJU chauffage = Sum max(0, Tref - Tjour) avec Tref = 18°C
- DJU refroidissement = Sum max(0, Tjour - Tref) avec Tref = 26°C

### Valeurs de référence par ville
| Ville | Zone | DJU Chauffage |
|-------|------|--------------|
| Paris | H1a | ~2 400 |
| Lyon | H1b | ~2 750 |
| Marseille | H3 | ~1 500 |
| Nice | H3 | ~1 400 |
| Toulouse | H2d | ~1 800 |

### API source : Open-Meteo historical (remplace _mock_dju)
```
GET https://archive-api.open-meteo.com/v1/archive
  ?latitude=48.85&longitude=2.35
  &start_date=2020-01-01&end_date=2020-12-31
  &daily=temperature_2m_max,temperature_2m_min
```

## 4. Signature Énergétique E = a x DJU + b

### Modèle de base (2P)
- E = consommation mesurée (kWh)
- a = sensibilité thermique (kWh/DJU)
- b = consommation de base (kWh) = baseload

### Interprétation
- a élevé -> fort impact météo -> priorité isolation/CVC
- b élevé -> forte consommation de base -> priorité veille/éclairage

### Modèles avancés
- 3P : changement de régime (point de bascule)
- 4P : chauffage ET climatisation
- 5P : deux points de bascule

## 5. Décomposition Consommation

```
Consommation totale
  Baseload (15-40% en tertiaire)
    Serveurs / informatique
    Éclairage permanent
    Équipements en veille
  Usage météo-dépendant (DJU-corrélé)
    CVC chauffage
    CVC climatisation
  Usage occupants (profil hebdomadaire)
    Éclairage fonctionnel
    Bureautique
    Process métier
```

## 6. Anomaly Detection ML

### Pipeline PROMEOS
```python
# Étape 1 : Features
features = [consumption_kwh, hour, day_of_week,
            dju, is_holiday, temperature]

# Étape 2 : Modèles (ensemble)
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
# SHAP pour explicabilité

# Cible : < 0.27 alertes/site/jour (évite la fatigue alertes)
```

### 30 règles anomalies (docs/.claude/skills/references/)
- Dérive progressive : +10% sur 30 jours glissants
- Pics nocturnes : conso > 150% baseline entre 22h-6h
- Sous-performance PV : production < 60% prévision météo
- Baseload anormal : min 7j < 80% baseline historique

## 7. CUSUM ISO 50001

```python
# Cumulative Sum -- détection dérive progressive
S_t = Sum (E_t_mesuré - E_t_référence)
# Si S_t > seuil -> dérive significative -> alerte
```

## 8. Carpet Plot (24h x 365j)

Heatmap 2D :
- Axe X : jours de l'année (1-365)
- Axe Y : heures de la journée (0h-23h)
- Couleur : consommation normalisée (kWh)

Révèle immédiatement : anomalies, patterns saisonniers,
heures de pointe, jours fériés, pannes.

## 9. Optimisation Puissance Souscrite (C4/HTA)

### CMDPS (Coût de Dépassement de Puissance Souscrite)
- Formule : **CMDPS = 12.65 x h** (EUR par kW de dépassement)
- h = nombre d'heures de dépassement mesurées

### Méthode optimisation
1. Analyser CDC 10min sur 12 mois
2. Identifier les dépassements de puissance souscrite
3. Calculer CMDPS annuel réel vs économie de réduction puissance
4. Recommander ajustement si CMDPS > 15% coût abonnement

## 10. Architecture EMS PROMEOS

### Source de vérité unique
-> `consumption_unified_service.py`
-> ZÉRO calcul dans les composants React

### Hiérarchie drill-down
Portfolio -> Site -> Bâtiment -> Compteur -> DeliveryPoint

### KPIs obligatoires par niveau
- kWh/m²/an (énergie finale normalisée surface)
- kWhEP/m²/an (énergie primaire x 1.9)
- kgCO2/m²/an (x 0.052 élec, x 0.227 gaz)
- EUR/m²/an (coût énergétique surfacique)
- Score DJU-corrigé (trajectoire DT)
