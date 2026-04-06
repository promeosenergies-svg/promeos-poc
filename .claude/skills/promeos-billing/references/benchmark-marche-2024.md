# Benchmark Marché Électricité France — Vision 2024

> Source : "Marché de l'électricité : la bataille est relancée" — Les Echos Études, déc 2024 (137 pages)
> Dernière mise à jour : avril 2026

## 1. Cadre réglementaire — Transitions 2024-2026

### ARENH — Dernière année (2025)

| Paramètre | Valeur |
|---|---|
| Prix | 42 €/MWh (fixe depuis 2011) |
| Volume plafond | 100 TWh/an |
| Demandes 2025 | 135 TWh (107 fournisseurs) |
| Écrêtement 2025 | **26%** |
| Coefficient de bouclage | **0,844** (vs 0,964 avant) |
| Date fin | **31 décembre 2025** |

L'écrêtement = surcoût approvisionnement pour les alternatifs (achat du complément sur marché de gros).

### Valorisation électricité nucléaire EDF (2024)

| Mode de valorisation | % production nucléaire |
|---|---|
| ARENH fournisseurs alternatifs | 31% |
| ARENH réplication (offres marché EDF) | 21% |
| ARENH TRVE | 14% |
| ARENH pertes réseau | 8% |
| **Marché & contrats long terme** | **26%** |

> Seulement 26% de la production nucléaire valorisée aux prix de marché — impact -8,2 Mds€ pour EDF en 2022 (bouclier tarifaire).

### Post-ARENH — Nouveau dispositif (2026-2040)

| Paramètre | Valeur envisagée |
|---|---|
| Durée | 15 ans |
| Production concernée | 100% nucléaire |
| Prix cible consommateur | ~70 €₂₀₂₂/MWh en moyenne |
| Prélèvement État | 50% à partir de 78 €/MWh |
| | 90% à partir de 110 €/MWh |
| Liberté commerciale EDF | Totale (gros, long terme, PPA) |

**Instruments EDF post-ARENH :**
- **CAPN** : 10-15 ans, électro-intensifs, 5 lettres d'intention signées (~10 TWh)
- **Contrats moyen terme** : 4-5 ans, ~60 €/MWh, 3 600 contrats signés (~17 TWh/an)
- **Enchères calendaires Y+4/Y+5** : moy 72 €/MWh (2028), 66 €/MWh (2029)

### Garanties de capacité

| Année | Prix de référence |
|---|---|
| 2021 | ~35 000 €/MW |
| 2022 | ~23 900 €/MW |
| 2023 | **60 000 €/MW** (pic — corrosion sous contrainte nucléaire) |
| 2024 | ~6 200 €/MW |
| 2025 (9e enchère) | **0 €/MW** |

Filières certifiées : nucléaire 48%, hydraulique 17%, interconnexion 10%, gaz 9%, effacement 4%, éolien 4%.

### CEE (5e période 2022-2025)

| Paramètre | Valeur |
|---|---|
| Part électricité dans obligation totale | **27%** |
| Coefficient obligation | 0,478 kWh cumac/kWh (à partir de 2023) |
| Seuil soumission électricité | 100 GWh/an (à partir de 2024) |
| Poids dans tarif bleu | **2,9%** |
| Pénalité max classique | 0,015 €/kWh cumac |
| Pénalité max précarité | 0,02 €/kWh cumac |

## 2. Prix de gros — Historique et tendances

### Prix spot day-ahead (France, moyennes mensuelles)

| Période | Prix €/MWh | Contexte |
|---|---|---|
| 2019 (moy) | ~40-50 | Pré-crise, normalité |
| Avril 2020 | ~15-20 | COVID, demande effondrée |
| Août 2022 | **492** | **Record absolu** — nucléaire + sécheresse + gaz |
| 2023 (moy) | ~80-100 | Normalisation progressive |
| Nov 2024 | **101** | Élevé vs décennie 2010-2020 (jamais >82,5 avant) |

### Contrats calendaires baseload (France, moyennes annuelles €/MWh)

| Année | Y+1 | Y+2 |
|---|---|---|
| 2020 | 45 | 46 |
| 2021 | 95 | 69 |
| 2022 | **365** | **220** |
| 2023 | 168 | 132 |
| Jan-Nov 2024 | **77** | **67** |

> Convergence vers le prix cible post-ARENH (~70 €/MWh). Toujours +50% vs pré-crise.

### Facteurs de volatilité prix

1. Disponibilité nucléaire (corrosion sous contrainte 2022 = -80 TWh)
2. Hydraulicité (sécheresse 2022)
3. Prix du gaz (guerre Ukraine)
4. Prix CO₂ (pic 89 €/t en 2022)
5. Conditions éoliennes et solaires
6. Interconnexions européennes

## 3. Prix de détail — Benchmark B2B et B2C

### TRVE (Tarif Bleu) — Évolution résidentiel TTC

| Date | Variation | Contexte |
|---|---|---|
| Juin 2019 | +7,7% | |
| Fév 2022 | +4,0% | Bouclier tarifaire (sinon +99% selon CRE) |
| Fév 2023 | +15,0% | Plafonnement (CRE recommandait +99%) |
| Août 2023 | +10,0% | |
| Fév 2024 | +0,2% | |
| **Fév 2025** | **~-10%** | Baisse prix de gros |

En 4 ans (2020-2024), le TRVE a augmenté de **48%**.

### Construction TRVE par empilement (CRE)

```
TRVE HT = ARENH
        + Complément fourniture écrêtement (3 mois lissés)
        + Complément fourniture marché (24 mois lissés)
        + Coût capacité au prix de marché
        + Coût capacité lié à l'écrêtement
        + Coûts commerciaux (y compris CEE)
        + Rémunération normale (marge "at-risk" ~2% HT)
        + TURPE (distribution)
        + Rattrapage
```

### Brique énergie TRVE (€/MWh, résidentiel)

| Année | ARENH | Marché lissé | Complément écrêtement |
|---|---|---|---|
| 2019 | 21,4 | 17,6 | 10,0 |
| 2020 | 19,3 | 19,9 | 10,1 |
| 2021 | 19,5 | 18,9 | 10,3 |
| 2022 | 17,5 | 28,8 | **63,9** |
| 2023 | 18,9 | **124,2** | **89,8** |
| 2024 | 18,8 | 91,1 | 13,9 |

### Coûts commerciaux dans le TRVE (€/MWh)

| Année | Coûts commerciaux (incl CEE) | Marge |
|---|---|---|
| 2019 | 11,9 | — |
| 2020 | 13,2 | — |
| 2021 | 12,7 | — |
| 2022 | 12,0 | — |
| 2023 | 13,8 | 4,1 |
| 2024 | **14,3** | **4,1** |

### Prix B2B (Opéra Energie)

- Fin 2023 vs fin 2021 : **+50%**
- Indice base 100 (T4 2020) → pic ~300 (T3 2022) → ~150 (T4 2023)
- Inertie des contrats pluriannuels ralentit la normalisation

### Offres B2C vs TRVE (déc 2024)

- **55 offres sur 67 moins chères que le TRVE**
- Discount max : **-25% à -30%**
- Meilleure offre : Ekwateur (981 €/an TTC pour 4 500 kWh, 6 kVA)
- TRVE : 1 284 €/an TTC
- 85% des fournisseurs proposent au moins une offre verte
- GO quasi-gratuite (0,45 €/MWh) → offre verte = pas de surcoût

### Formules tarifaires B2B (benchmark)

| Type | Description | Cible |
|---|---|---|
| Prix fixe | Sécurité budgétaire, marge fournisseur intégrée | TPE/PME |
| Prix indexé TRVE | Suit le tarif réglementé | Petits pro |
| Prix indexé marché | Base + spread, suit les marchés de gros | PME/ETI |
| Offre à clic | Fenêtres d'achat pendant le contrat | Grands comptes |
| Portfolio | Construction prix selon profil de conso | Grands comptes |
| Accès spot | Indexation directe prix spot | Électro-intensifs |
| CAPN (post-ARENH) | Allocation production nucléaire 10-15 ans | Électro-intensifs |

## 4. Concurrence — Paysage 2024

### Forces en présence

| Catégorie | Exemples | Caractéristique |
|---|---|---|
| Historique national | EDF (27M clients, 224 TWh, ~50% PDM) | TRVE + offres marché |
| Historiques étrangers & Engie | Engie (5,3M), Vattenfall, Iberdrola | Ouverture marché |
| Fournisseurs énergie fossile | TotalEnergies (5,5M, 29 TWh), ENI/Plenitude (1M), Dyneff | Reconversion |
| Indépendants français | Ekwateur, Ohm (249K), Ilek, Elmy, Enercoop (104K) | Start-up |
| Indépendants étrangers | Octopus Energy (200K), Wekiwi, La Belle Energie | Expansion |
| Filiales ELD | Alterna (50+ ELD), Sélia (Séolis), Enalp | Hors zone historique |
| ELD | ES (575K), Séolis (166K), UEM (161K), Sorégies (141K) | Monopole local |

### Parts de marché par segment (T3 2024, en volume)

| Segment | Historiques | Alternatifs | Sites alternatifs |
|---|---|---|---|
| Grands sites non résidentiels | 48% | **52%** | 261 000 |
| Sites moyens non résidentiels | 48% | **52%** | (inclus ci-dessus) |
| Petits sites non résidentiels | 57% | 43% | 1,7M |
| Résidentiels | 72% | 28% | 10,4M |
| **Global** | **57%** | **43%** | — |

**Projection 2030** : 48-52% historiques / 48-52% alternatifs (tendance équilibre).

### Taux de switch

- Résidentiel : ~8-10%/an (France), vs 12% Allemagne, 18% Belgique, 21% Espagne
- Non résidentiel : nettement plus élevé, pics T1 et T4 (échéances contrats)
- TRVE freine le switch résidentiel

### Victimes de la crise 2021-2023

Faillites/retraits : Hydroption, Bulb, Barry, Mega Energie, Ovo Energy, Energies Leclerc, GreenYellow, Planète Oui, Plüm Energie. Écrémage terminé depuis 2024.

### Performances financières 2023 (échantillon)

| Acteur | CA (M€) | EBE (M€) | Résultat net (M€) |
|---|---|---|---|
| ENI Gas & Power France | 2 560 | 42 | **-171** |
| Groupe Sorégies (¹) | 1 911 | **430** | **167** |
| Groupe GEG | 1 060 | 81 | 55 |
| Alterna | 768 | 54 | 38 |
| Ekwateur | 581 | 40 | 22 |
| Primeo Energie | 278 | 36 | 17 |
| Sélia | 226 | 32 | 16 |
| Enercoop | 165 | 25 | 16 |
| Octopus Energy France | 88 | 40 | **-78** |

(¹) Y compris production + distribution + Alterna

## 5. TURPE — Trajectoire

### Évolution TURPE 6 (2021-2024)

| Date | HTB | HTA-BT |
|---|---|---|
| Août 2019 | +2,2% | +3,0% |
| Août 2020 | -1,1% | +2,8% |
| Août 2021 | +1,1% | +0,9% |
| Août 2022 | 0,0% | +2,3% |
| Août 2023 | +6,7% | +6,5% |
| Nov 2024 | +5,0% | +4,8% |

**Total TURPE 6** : HTB +13%, HTA-BT +15%.

### TURPE 7 (à partir du 01/08/2025)

- Hausse attendue : **~10%** dès 2025
- Raison : investissements massifs réseau (ENR, VE, modernisation)
- Enedis : 5,5 Mds€/an en 2027 (vs 4,4 en 2022)
- RTE : 4 Mds€/an en 2027 (doublement)
- Représente **90% des revenus** de RTE et Enedis

## 6. CPPA — Marché émergent

| Indicateur | Valeur |
|---|---|
| Volumes annuels cumulés (depuis 2019) | **4,9 TWh** |
| CPPA signés jan-sept 2024 | **26** |
| Greenfield | 84% |
| Brownfield | 16% |

### Types de CPPA

| Type | Principe | Exemple |
|---|---|---|
| PPA sur site | Installation sur site conso, livraison physique directe | Toitures PV |
| PPA hors site | Installation ailleurs, injection réseau, contrat fourniture | Engie-Suez (PV décharges) |
| PPA virtuel | CfD financier, pas de livraison physique | ZE Energy-Orange (90 GWh/an, 15 ans) |

## 7. Production et mix — Fondamentaux

### Capacité installée (2023)

| Source | GW | % |
|---|---|---|
| Nucléaire | 61,4 | 41% |
| Hydraulique | 25,7 | 17% |
| Éolien | 23,8 | 16% |
| Solaire | 19,4 | 13% |
| Gaz | 13,4 | 9% |
| Charbon & fioul | 4,5 | 3% |
| Bioénergies | 1,5 | 1% |
| **Total** | **149,0** | |

### Production (2023)

- Total : 495 TWh (point bas, nucléaire 279 TWh en 2022 → 320 TWh en 2023 → ~360 TWh 2024)
- Mix : nucléaire 65%, hydraulique 12%, éolien 10%, gaz 6%, solaire 4%
- **92,2% décarbonée**
- Export net 2023 : +50 TWh, 2024 estimé : record ~75 TWh

### Consommation

- 2023 : **439 TWh** (point bas)
- Baisse structurelle : sobriété, efficacité, hivers cléments, destruction demande industrielle
- Rebond attendu (décalé) : électrification usages, VE, data centers, H2
- Cible RTE 2035 : **590-640 TWh**

### PPE 3 — Objectifs capacité

| Source | 2023 | 2030 | 2035 |
|---|---|---|---|
| Nucléaire | 56 réacteurs | — | 57 réacteurs |
| Photovoltaïque | 19 GW | 54-60 GW | 75-100 GW |
| Éolien terrestre | 22 GW | 33-35 GW | 40-45 GW |
| Éolien en mer | 1 GW | 4 GW | 18 GW |
| Hydroélectricité | 26 GW | 26 GW | 29 GW |

## 8. Accise — Historique complet

| Période | Taux particuliers (€/MWh) | Contexte |
|---|---|---|
| Avant 2022 | 22,50 | CSPE pré-bouclier |
| 01/02/2022 – 31/01/2024 | **1,00** | Bouclier tarifaire |
| 01/02/2024 – 31/01/2025 | **21,00** | Sortie progressive |
| 01/02/2025 – 31/07/2025 | 22,50 | Retour pré-crise |
| 01/08/2025 – 31/01/2026 | 25,79 | LFI 2025 |
| Depuis 01/02/2026 | T1=30,85 / T2=26,58 | Par catégorie |

Taux normal 2024 (hors bouclier) : 32,5 €/MWh particuliers, 25,7 €/MWh PME, 22,5 €/MWh hautes puissances.

Exonérations électro-intensifs : 2 / 5 / 7,5 €/MWh. Industries fuites carbone : 1 / 2,5 / 5,5 €/MWh.

## 9. Nouveaux entrants attendus

| Catégorie | Logique | Exemples potentiels |
|---|---|---|
| Fournisseurs énergie fossile | Reconversion obligée | Distributeurs fioul, GPL |
| Producteurs ENR | Valorisation directe via CPPA | Neoen, Voltalia, Valorem |
| Fournisseurs étrangers | 2e marché UE | E.ON, EDP, indépendants UE |
| Constructeurs automobiles | Intégration chaîne VE | Volkswagen (déjà en DE) |
| Sociétés services énergétiques | Offre clé en main | Installateurs PV+batteries+fourniture |

## 10. Implications PROMEOS

### Shadow billing
- Benchmark fourniture B2B : 60-77 €/MWh = zone normale post-ARENH
- > 90 €/MWh = contrat à renégocier
- < 50 €/MWh = vérifier conditions (CAPN, ancien ARENH résiduel)

### Module achat
- Modéliser les 3 instruments post-ARENH (CAPN, moyen terme, enchères)
- Intégrer CPPA dans cascade de prix
- Alerter fin de contrats ARENH résiduels

### Conformité
- TURPE 7 = +10% à intégrer dans les projections budget
- Accise versioning temporel = critique (7 changements en 5 ans)
- CTA : 15% depuis 02/2026 (transition à vérifier)

### Benchmark concurrentiel
- 55/67 offres B2C < TRVE = le TRVE est un plafond
- Taux de switch faible (8-10%) = opportunité rétention/conquête
- 85% offres vertes = standard, pas différenciant
