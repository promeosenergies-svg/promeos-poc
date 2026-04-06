---
name: promeos-flexibilite-acc
description: >
  Expert flexibilité énergétique et autoconsommation collective.
  NEBCO, effacement, marchés capacité, ACC France,
  clés de répartition, gouvernance PMO.
version: 2.0.0
tags: [flexibilite, nebco, acc, effacement, capacite, autoconsommation]
---

# Flexibilité & Autoconsommation Collective -- Expert PROMEOS

## 1. NEBCO (remplace NEBEF depuis 01/09/2025)

### Principe
- Notification d'Échanges de Blocs de Consommation
- Approuvé CRE délib. 2025-199 du 31/07/2025
- Référence : RM-5-NEBCO-V01
- Seuil : **100 kW par pas de contrôle** (hors zéro)
- Marchés éligibles : capacité, mFRR, aFRR, services système

### Actifs flexibles éligibles
- CVC (chauffage/clim) bâtiments tertiaires
- Réfrigération industrielle
- IRVE (bornes recharge EV)
- Batteries BESS
- Process industriels décalables

### Valorisation NEBCO (revenus complémentaires)
- Marché capacité 2026 : **~5 400 EUR/MW** (prix moyen, historiquement bas)
- mFRR (réserve tertiaire) : ~200-500 EUR/MWh activé
- Peak shaving : réduction CMDPS
- Spot : valorisation au prix EPEX du moment de l'effacement

## 2. Taxonomie complète des mécanismes de flexibilité

| Mécanisme | Activation | Rémunération | Seuil | Opérateur |
|-----------|-----------|-------------|-------|-----------|
| FCR | Auto, <30s | Capacité ~10-20 EUR/MW/h | 1 MW (pool possible) | RTE enchères hebdo |
| aFRR | Auto, <5min | Capacité + énergie | 1 MW | RTE (PICASSO) |
| mFRR | Manuel, <15min | Capacité + énergie | 1 MW | RTE (MARI) |
| NEBCO | Notification J-1 ou infrajournalier | Énergie EUR/MWh spot | **100 kW** | RTE, via agrégateur |
| AOFD | Contractuel | Capacité EUR/MW/an | Variable par lot | RTE |
| Interruptibilité | Signal RTE, <5s | Prime ~30-50k EUR/MW/an | 50 MW | RTE contrat direct |
| Capacité (certificats) | PP1/PP2 hiver | Certificats MW | Tout fournisseur | RTE enchères |
| Flex locale Enedis | Contractuel saisonnier | EUR/MW/an | 100 kW | Enedis |

## 3. Autoconsommation Collective (ACC)

### Cadre réglementaire
- Rayon max : 2 km (arrêté 21/02/2025 : extensions 5 MW -> 10 MW)
- Acteur principal : PMO (Personne Morale Organisatrice)
- Déclaration : via SGE Enedis (F131 convention ACC)

### Modes de répartition
| Mode | Description | Optimal pour |
|------|-------------|-------------|
| Statique | % fixe par participant | Simplicité |
| Dynamique défaut | Prorata conso 15min (Enedis) | Maximise TAc |
| Dynamique personnalisée | Règles métier PROMEOS | Contrôle total |

### KPIs ACC
- **TAc** : Taux d'autoconsommation collective = prod_injectée_allouée / prod_totale
- **TAp** : Taux d'autoproduction = conso_allouée / conso_totale_participant
- Surplus : production non allouée -> vente réseau

### Architecture PMO dans PROMEOS
```
PMO (PROMEOS)
  Données 15min Enedis (prod/conso participants)
  Prévisions PV (météo Open-Meteo + PVGIS)
  Calcul clé répartition dynamique
  Shadow billing participants
  Génération factures ACC automatisées
  Rapport CRE/Enedis
```

## 4. Prix Spot Négatifs -- Stratégie

Contexte 2025 (RTE Bilan Électrique) : 513h de prix négatifs
-> Opportunité : stocker, produire, décaler consommation
-> PROMEOS : alertes temps réel + recommandations

Stratégie recommandée :
1. Monitorer EPEX SPOT J-1 (via RTE éCO2mix API)
2. Alerter si prix < 0 EUR/MWh -> déclencher flexibilité
3. Tracer les événements dans le plan d'action

## 5. Optimisation HP/HC avec Heures Solaires

Depuis CRE délib. 2026-33 (04/02/2026) :
- HC méridiennes 11h-14h ouvertes pour nouveaux clients
- Signal prix : production PV maximale = prix bas
- Stratégie : décaler charge vers 11h-14h

### 6 blocs horaires saisonnalisés
| Bloc | Hiver | Été |
|------|-------|-----|
| Matin | 6h-11h | 6h-11h |
| Midi (solaire) | 11h-14h | 11h-14h |
| Soir | 14h-22h | 14h-22h |

## 6. Flex Score PROMEOS

Évaluation du potentiel de flexibilité d'un site :
- CVC modulable (kW / % total)
- Process décalables (kW / durée max)
- Stockage disponible (kWh)
- Contraintes confort / process
- Score : 0-100, seuil 40 pour éligibilité NEBCO
