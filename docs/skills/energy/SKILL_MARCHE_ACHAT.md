---
name: promeos-marche-achat
description: >
  Expert marché énergie B2B France post-ARENH.
  Stratégies d'achat, contrats, fournisseurs, pricing,
  flexibilité, NEBCO, PPA, couverture spot/forward.
version: 2.0.0
tags: [market, achat, energie, b2b, post-arenh, spot, forward, ppa]
---

# Marché & Achat Énergie B2B France -- Expert PROMEOS

## 1. Structure du Marché Français post-ARENH

### Acteurs du marché
| Acteur | Rôle | Exemples |
|--------|------|----------|
| Producteur | Génère kWh (nucléaire, ENR, thermique) | EDF, Engie, TotalEnergies, CNR |
| Fournisseur | Achète en gros, vend au détail B2B/B2C | EDF Entreprises, Engie Pro, Alpiq |
| RE (Responsable d'Équilibre) | Garantit équilibre injection=soutirage | Chaque fournisseur ou délégué |
| Agrégateur | Valorise flexibilité (effacement, ENR) | Voltalis, Energy Pool, Enel X |
| Courtier | Intermédiation AO, pas de fourniture | Selectra, Opera Energie, CWape |
| GRD/GRT | Réseau distribution/transport | Enedis, RTE, GRDF, Teréga |

### Fournisseurs validés PROMEOS (30 fournisseurs CRE)
- Historiques : EDF, Engie, EDF collectivités
- Alternatifs : TotalEnergies, Vattenfall, Eni, Proxelia,
  Alpiq, Axpo, Ekwateur, Urban Solar, ...

### Types de contrats B2B
| Type | Description | Risque client |
|------|-------------|--------------|
| Tarif fixe | Prix bloqué sur durée | Faible |
| Indexé SPOT | Suit le marché day-ahead | Élevé |
| Indexé forward | Suit les cotations terme | Moyen |
| SPOT pur | 100% prix J-1 EPEX | Très élevé |
| PPA | Contrat direct producteur (10-15 ans) | Faible long terme |
| TUNNEL | Prix entre plancher/plafond | Modéré |
| C3 | Forfait avec ajustement | Modéré |

### Segments tarifaires TURPE
- HP/HC (Heures Pleines / Creuses)
- HPH/HCH/HPB/HCB (Heures Pointe/Pleine/Base Hiver/Été)
- Pointe (heures de pointe système -- jours RTE)
- Heures Solaires (méridiennes 11h-14h, CRE délib. 2026-33 du 04/02/2026)

## 2. Stratégies d'Achat PROMEOS (4 stratégies)

### Stratégie 1 -- Tarif Fixe Sécurisé
Couverture totale, zéro exposition marché.
Adapté aux : PME, collectivités, budget annuel contraint.
Effort score : 1/5 | Risque : minimal

### Stratégie 2 -- Indexé Forward + Couverture
Achat progressif sur courbes forward 6-24 mois.
Adapté aux : ETI avec DAF, volume > 500 MWh/an.
Effort score : 3/5 | Risque : modéré

### Stratégie 3 -- Tarif Heures Solaires
Maximise l'autoconsommation sur la plage 11h-14h.
6 blocs horaires (été/hiver x matin/midi/soir).
Adapté aux : sites avec PV ou usage décalable.
Effort score : 4/5 | Risque : modéré si consommation stable

### Stratégie 4 -- SPOT + NEBCO
Exposition marché temps réel + valorisation flexibilité.
Adapté aux : sites industriels > 100 kW flexibles.
Effort score : 5/5 | Risque : élevé sans pilotage actif

## 3. Analyse Prix Spot 2025 (RTE Bilan Électrique 2025)

| Indicateur | Valeur 2025 | Valeur 2024 | Signal |
|-----------|-------------|-------------|--------|
| Heures prix négatifs | **513h** | 352h | autoconsommation/stockage |
| Heures >= 100 EUR/MWh | **1 807h** | 1 382h | couverture obligatoire |
| Volatilité | Très élevée | Élevée | pilotage actif rentable |

## 4. Post-ARENH / VNU (depuis 01/01/2026)

- ARENH (42 EUR/MWh, 100 TWh/an) terminé 31/12/2025
- VNU : EDF vend au marché, redistribue si prix > 78 EUR/MWh
- CAPN (Contrats d'Allocation de Production Nucléaire) :
  long terme EDF, 10-15 ans, éligibles >= 7 GWh/an
- En avril 2026 : VNU dormant (prix ~60 EUR/MWh < seuil)

## 5. Mécanisme de Capacité 2026

| Paramètre | Valeur |
|-----------|--------|
| Prix moyen 2026 (6 premières enchères) | **~5 400 EUR/MW** |
| Enchère décembre 2025 pour 2026 | ~99 EUR/MW (quasi-nul) |
| Plafond réglementaire | 60 000 EUR/MW |
| Contexte | Excellente disponibilité nucléaire, ENR en hausse |

-> Les prix de capacité 2026 sont historiquement bas. Ne pas utiliser
les anciennes estimations à ~50 000 EUR/MW (valeurs crise 2022).

## 6. Levier Commercial PROMEOS

### Wedge principal : "Audit conformité gratuit 48h"
- Démo : calcul score DT + risque financier en 2 minutes
- Urgence : deadline 11/10/2026 Audit Énergétique
- ROI type : détection 2 anomalies facture = 2.5k EUR/mois récupérés

### Pricing PROMEOS
| Plan | Prix | Cible |
|------|------|-------|
| Starter | 400-800 EUR/mois | ETI 10-30 sites |
| Growth | 800-2000 EUR/mois | ETI 30-150 sites |
| Enterprise | Custom | Groupe 150-500 sites |

## 7. Compétiteurs à surveiller
- Deepki : ESG immobilier, pas de billing/achat
- Spacewell/Dexma : EMS généraliste, pas France-fit
- Energisme : data platform, pas d'achat
- Trinergy : le plus proche, mais France-fit limité (6-12 mois derrière)
- advizeo/WattValue : service humain, pas SaaS pur
