---
name: promeos-ppa-long-terme
description: >
  Expert PPA et stratégies achat long terme.
  Power Purchase Agreements, CAPN, contrats forward,
  couverture 2030, gestion du risque prix.
version: 1.0.0
tags: [ppa, long-terme, forward, couverture, risque, capn]
---

# PPA & Contrats Long Terme — Expert PROMEOS

## 1. Contexte Post-ARENH

### Avant (jusqu'au 31/12/2025) — ARENH
- Prix nucléaire garanti : 42 €/MWh (puis 46,2 €/MWh)
- Volume alloué aux fournisseurs alternatifs
- Offre de couverture accessible à tous

### Après (depuis 01/01/2026) — VNU
- VNU (Versement Nucléaire Universel) : redistribution
  des revenus nucléaires à tous les fournisseurs
- Seuils : 50% au-dessus de 78 €/MWh, 90% au-dessus de ~110 €/MWh
- Prix de marché = référence (EPEX SPOT + marchés terme)
- Volatilité accrue : besoin de couverture stratégique

## 2. Types de Contrats Long Terme

### PPA (Power Purchase Agreement)
```
Acheteur B2B ←→ Producteur ENR (PV, éolien)
  Durée : 5-20 ans
  Prix : fixe ou indexé (€/MWh)
  Volume : profilé ou "pay as produced"
  Garanties d'Origine : incluses
```

**Types de PPA**
| Type | Description | Avantage |
|------|-------------|---------|
| PPA physique | Livraison sur réseau, compensation | Prix stable |
| PPA financier (CfD) | Contrat différence, pas de livraison | Flexibilité |
| PPA corporate | Direct producteur → entreprise | Image RSE |
| PPA agrégé | Pool d'acheteurs | Volume accessible PME |

**Seuil d'accès** : généralement > 2 GWh/an
PROMEOS cible ETI avec plusieurs sites = volumes agrégeables

### CAPN (Contrats d'Accès à la Production Nucléaire)
- Offre EDF post-ARENH pour grands clients
- Prix lié aux coûts de production nucléaire
- Volume garanti sur 5-15 ans
- Éligibilité : > 5 GWh/an par site

### Contrats Forward (Terme)
- Achat sur marchés à terme (ICE, EEX)
- Horizons : M+1, Q+1, Y+1 jusqu'à Y+3
- Via trader ou fournisseur avec desk trading

## 3. Gestion du Risque Prix

### Exposition sans couverture
```
Coût énergie = f(prix_spot_EPEX)
Volatilité 2025 : prix entre -500 et +3000 €/MWh
→ Budget énergie imprévisible = inacceptable pour DAF
```

### Stratégie de couverture recommandée PROMEOS

**Profil "prudent" (DAF averse au risque)**
- 80% couverture fixe (PPA ou forward Y+1)
- 20% spot (optimisation opportuniste)
- Révision annuelle

**Profil "équilibré" (ETI avec équipe énergie)**
- 50% couverture terme (Y+1 / Y+2)
- 30% couverture rolling (M+3 à M+6)
- 20% spot avec limites de stop-loss

**Profil "optimiseur" (Energy Manager expert)**
- Couverture progressive sur 24 mois
- Intégration signaux NEBCO
- Prix négatifs : déclenchement flexibilité

## 4. Module Achat PROMEOS — 4 Stratégies

```python
STRATEGIES = {
    "FIXE": {
        "description": "Tarif fixe sécurisé",
        "effort_score": 1,
        "risque": "minimal",
        "adapte": ["PME", "budget_contraint"]
    },
    "FORWARD": {
        "description": "Indexé forward + couverture progressive",
        "effort_score": 3,
        "risque": "modéré",
        "adapte": ["ETI", "DAF_actif", "> 500 MWh/an"]
    },
    "SOLAIRE": {
        "description": "Heures Solaires 11h-14h + PV",
        "effort_score": 4,
        "risque": "modéré",
        "adapte": ["sites_pv", "usage_décalable"]
    },
    "SPOT_NEBCO": {
        "description": "SPOT + valorisation flexibilité NEBCO",
        "effort_score": 5,
        "risque": "élevé",
        "adapte": ["industriels", "> 100 kW_flexible"]
    }
}
```

## 5. Assistant Achat PROMEOS (8 étapes)

```
Étape 1 : Profil de consommation (courbe de charge)
Étape 2 : Analyse exposition prix actuelle
Étape 3 : Appétit au risque (questionnaire DAF)
Étape 4 : Simulation 4 stratégies (coût × risque)
Étape 5 : Recommandation personnalisée
Étape 6 : Sélection fournisseurs (30 CRE validés)
Étape 7 : RFQ automatisée (Request for Quotation)
Étape 8 : Comparaison offres + aide à la décision
```

## 6. Critères PPA pour ETI

### Quand recommander un PPA
- Consommation agrégée > 5 GWh/an
- Engagement RSE/CSRD documenté
- Direction prête pour engagement 5-15 ans
- Profil de consommation stable

### Calcul attractivité PPA
```python
# Prix PPA vs prix marché forward
spread = prix_marche_Y5 - prix_ppa
valeur_actualisee = sum(spread * volume_annuel / (1+taux)**n for n in range(duree))
# Si VAN > 0 → PPA attractif
```

### Risques PPA à documenter
- Risque volume (si conso change)
- Risque contrepartie (producteur fait défaut)
- Risque réseau (disponibilité injection)
- Risque réglementaire (changement règles GO)
