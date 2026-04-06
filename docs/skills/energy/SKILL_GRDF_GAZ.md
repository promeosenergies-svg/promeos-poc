---
name: promeos-grdf-gaz
description: >
  Expert GRDF, API ADICT REST, facturation gaz B2B,
  ATRD7, biométhane, gaz vert, accise gaz (ex-TICGN).
version: 1.0.0
tags: [grdf, gaz, adict, atrd7, biomethan, facturation, pcj]
---

# GRDF & Gaz — Expert PROMEOS

## 1. Architecture Réseau Gaz France

### GRDs (Gestionnaires Réseau Distribution)
- **GRDF** : principal GRD, ~11 000 communes
- **ELD locaux** : Gaz de Bordeaux, Régie Strasbourg, etc.
- **GRTgaz / Teréga** : transport (HTB gaz)

### Segments de clientèle
| Segment | Consommation annuelle | Compteur |
|---------|----------------------|---------|
| T1 | < 6 MWh | Standard |
| T2 | 6-300 MWh | Télé-relève mensuelle |
| T3 | 300-5 000 MWh | Télé-relève quotidienne |
| T4 | > 5 000 MWh | Horaire |

## 2. API GRDF ADICT REST

### Qu'est-ce que c'est ?
API REST de GRDF pour accéder aux données de comptage
des clients gaz avec leur consentement.

### Authentification
- OAuth2 Client Credentials Flow
- Consentement client obligatoire (durée : 1 an)
- Portail officiel : **https://sites.grdf.fr/web/portail-api-grdf-adict**
- Token valide 4h (client_id + client_secret)

> **CORRECTION** : L'URL "api.grdf.fr" est FAUSSE.
> Le portail réel est `sites.grdf.fr/web/portail-api-grdf-adict`.

### Endpoints principaux
```
GET /donnees/pce/{pce}/mesures
  → Index et consommations journalières

GET /donnees/pce/{pce}/informations
  → Données contractuelles (PCE, option, puissance)

GET /donnees/pce/{pce}/droits-acces
  → Statut du consentement client
```

### Paramètres clés
- `pce` : Point de Comptage et d'Estimation (équivalent PRM élec)
- `date_debut` / `date_fin` : période (max 3 ans)
- `unite` : MWh ou m³ (PCS local pour conversion)

### Conversion m³ → kWh
```python
# PCS (Pouvoir Calorifique Supérieur) variable selon région
# Valeur indicative : 1 m³ ≈ 11.6 kWh (PCS moyen France)
# GRDF fournit le PCS exact par zone et mois
kWh = volume_m3 * pcs_local
```

## 3. Facturation Gaz B2B

### Structure d'une facture gaz

```
FACTURE GAZ B2B
├── Fourniture (prix fournisseur)
│   ├── Terme fixe (abonnement)
│   └── Terme variable (€/MWh × conso)
├── ATRD7 (Acheminement Transport Distribution Gaz)
│   ├── Terme fixe (abonnement capacité)
│   └── Terme variable (€/MWh × conso)
├── Accise gaz (ex-TICGN)
│   ├── Taux normal : 10.73 €/MWh (base, depuis 01/02/2026)
│   └── Composante ZNI : 5.66 €/MWh (Zones Non Interconnectées)
│   └── ⚠️ TOTAL EFFECTIF : 16.39 €/MWh (arrêté 27/01/2026)
├── CTA gaz (si applicable)
└── TVA 20%
```

> **CORRECTION ACCISE GAZ** : Le taux de 10.73 €/MWh est la composante
> "accise normale" seule. Depuis le 01/02/2026 (arrêté du 27/01/2026,
> Légifrance), le taux total effectif incluant la composante ZNI est
> **16.39 €/MWh**. Utiliser 10.73 seul entraîne un sous-calcul de ~35%.

### ATRD7 (depuis 01/07/2024, durée 4 ans → 30/06/2028)
- Tarif d'acheminement réseau gaz GRDF
- Structuré en : terme capacité (fixe) + terme usage (variable)
- Délibération CRE du 02/02/2024

### CO₂ Gaz
- **0.227 kgCO₂e/kWh** (ADEME Base Empreinte V23.6)
- PCI, combustion + amont
- Source unique : `backend/config/emission_factors.py`
- Corrélation avec DJU chauffage (pour signature énergétique)

## 4. Biométhane & Gaz Vert

### Contexte
- Objectif officiel PPE3 : **~15% de gaz renouvelable en 2030** (44 TWh injectés)
- Biométhane injecté dans le réseau GRDF
- Garanties d'Origine (GO) gaz vert

> **CORRECTION** : Le chiffre "20% en 2030" est une ambition de la
> filière (France Gaz, SER) — PAS un objectif réglementaire.
> L'objectif officiel PPE3 est ~15% (44 TWh), à comparer aux ~4%
> actuels (2025).

### Types de contrats gaz vert
| Type | Description | Prime |
|------|-------------|-------|
| Gaz vert 100% | GO vérifiées, traçabilité | +5-15 €/MWh |
| Mix gaz + biogaz | % de GO | +2-8 €/MWh |
| Gaz fossile standard | Sans GO | Prix marché |

### Dans PROMEOS
- Afficher le % de gaz vert dans le contrat fournisseur
- Calculer CO₂ évité (0.227 × % fossile uniquement)
- Badge "Gaz Vert" dans Site360

## 5. Consommation Gaz & DJU

### Corrélation forte chauffage/DJU
```python
# Signature énergétique gaz
conso_gaz = a_gaz * DJU + b_gaz
# a_gaz : sensibilité thermique (kWh/DJU)
# b_gaz : usage process/ECS (indépendant météo)
```

### Anomalies gaz typiques
- Fuite réseau interne : conso nuit > 20% journalière
- Chaudière déréglée : DJU-corrigé +15% vs baseline
- Compteur défaillant : index incohérents entre relevés

## 6. Architecture Backend PROMEOS pour le Gaz

> **NOTE** : Le module GRDF est **en cours de conception** (MODULE FUTUR).
> Seul le connecteur Enedis (`backend/data_ingestion/enedis/`) existe
> aujourd'hui. L'architecture ci-dessous est la cible.

```
backend/
├── data_ingestion/
│   ├── enedis/          # ✅ EXISTANT — connecteur SGE/DataConnect
│   └── grdf/            # 🔜 FUTUR — connecteur ADICT
│       ├── adict_client.py      # Client REST OAuth2 GRDF
│       ├── parsers/
│       │   ├── mesures_parser.py  # Index + CDC → ConsumptionReading
│       │   └── contrat_parser.py  # PCE → données contractuelles
│       └── bridge.py             # → Meter unifié (vecteur GAZ)
```

### Modèle de données (existant)
```python
class ConsumptionReading(Base):
    energy_type = "GAZ"  # vs "ELECTRICITE" — enum TypeCompteur
    unit = "kWh"         # Toujours kWh (converti depuis m³)
    source = "GRDF_ADICT"  # Futur — aujourd'hui import CSV
    pce = Column(String)   # Identifiant point de comptage
```
