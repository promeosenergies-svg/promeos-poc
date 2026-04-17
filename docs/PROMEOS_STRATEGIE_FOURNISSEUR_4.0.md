# PROMEOS — Stratégie « Fournisseur 4.0 sans la fourniture »

> **Version** : 2.0 — Avril 2026
> **Statut** : Document stratégique de référence
> **Auteur** : Équipe PROMEOS
> **Dernière mise à jour** : 06/04/2026

---

## Table des matières

1. [Résumé exécutif](#1-résumé-exécutif)
2. [Contexte de marché](#2-contexte-de-marché)
   - 2.1 [Dynamiques structurelles](#21-dynamiques-structurelles)
   - 2.2 [Taille de marché adressable (TAM/SAM/SOM)](#22-taille-de-marché-adressable-tamsam-som)
   - 2.3 [Tendances émergentes](#23-tendances-émergentes)
3. [Cartographie des acteurs](#3-cartographie-des-acteurs)
   - 3.1 [Fournisseur historique](#31-fournisseur-historique)
   - 3.2 [Fournisseur alternatif](#32-fournisseur-alternatif)
   - 3.3 [GRD / GRT](#33-grd--grt)
   - 3.4 [Éditeur SaaS énergie](#34-éditeur-saas-énergie)
   - 3.5 [Courtier en énergie](#35-courtier-en-énergie)
   - 3.6 [Agrégateur de flexibilité](#36-agrégateur-de-flexibilité)
   - 3.7 [Producteur EnR](#37-producteur-enr)
4. [Analyse concurrentielle](#4-analyse-concurrentielle)
   - 4.1 [Matrice fonctionnelle](#41-matrice-fonctionnelle)
   - 4.2 [Positionnement différenciant PROMEOS](#42-positionnement-différenciant-promeos)
5. [Proposition de valeur PROMEOS](#5-proposition-de-valeur-promeos)
   - 5.1 [Vision](#51-vision)
   - 5.2 [Les 5 piliers fonctionnels](#52-les-5-piliers-fonctionnels)
   - 5.3 [Personas cibles](#53-personas-cibles)
6. [Modèle économique](#6-modèle-économique)
   - 6.1 [Pricing](#61-pricing)
   - 6.2 [Unit economics](#62-unit-economics)
7. [Architecture produit](#7-architecture-produit)
   - 7.1 [Stack technique](#71-stack-technique)
   - 7.2 [Modules fonctionnels](#72-modules-fonctionnels)
   - 7.3 [Intégrations](#73-intégrations)
8. [Go-to-market](#8-go-to-market)
   - 8.1 [Segmentation client](#81-segmentation-client)
   - 8.2 [Canal de distribution](#82-canal-de-distribution)
   - 8.3 [Partenariats stratégiques](#83-partenariats-stratégiques)
9. [Roadmap produit](#9-roadmap-produit)
10. [Risques et mitigations](#10-risques-et-mitigations)
11. [Métriques de succès](#11-métriques-de-succès)
12. [Gouvernance et organisation](#12-gouvernance-et-organisation)
13. [Annexes et sources](#13-annexes-et-sources)

---

## 1. Résumé exécutif

### Le constat

Le marché français de l'énergie B2B traverse une transformation structurelle sans précédent. La fin du dispositif ARENH au 31 décembre 2025, la crise énergétique de 2022-2023, la montée en puissance des obligations réglementaires (décret tertiaire, BACS, CSRD) et l'émergence de nouvelles formes de production et de flexibilité créent un environnement où les entreprises multi-sites se retrouvent démunies face à la complexité croissante de leur gestion énergétique.

### Le problème

Les entreprises B2B françaises manquent cruellement d'outils adaptés pour :

- **Comprendre** leurs factures d'énergie (fourniture, acheminement, taxes, contributions — plus de 30 composantes)
- **Piloter** leur stratégie d'achat dans un monde post-ARENH (VNU, CAPN, marchés à terme, CPPA)
- **Respecter** leurs obligations réglementaires croissantes (OPERAT, BACS, audit énergétique, CEE)
- **Optimiser** leur consommation et valoriser leur flexibilité
- **Décider** sur la base de données fiables, explicables et actionnables

### La solution PROMEOS

PROMEOS est le **cockpit énergétique B2B France** qui transforme les données de patrimoine, de consommation, de facturation et de contrats en **décisions lisibles et actionnables** pour les décideurs non experts (DAF, directeurs immobilier, responsables énergie, acheteurs).

Notre positionnement unique : **« Fournisseur 4.0 sans la fourniture »** — offrir toute l'intelligence d'un fournisseur d'énergie de nouvelle génération (analyse, optimisation, conseil, pilotage) sans jamais vendre un seul kWh. Cette indépendance vis-à-vis de la fourniture garantit la neutralité des recommandations et l'alignement total avec les intérêts du client.

### Les 3 différenciants défendables

1. **Bill Intelligence France « explicable »** : décoder chaque facture (fourniture / acheminement / taxes), relier chaque anomalie à sa cause probable, quantifier l'impact € et proposer une action correctrice avec ROI estimé
2. **Purchase Strategy post-ARENH intégrée** : modélisation de l'exposition, scénarios d'achat, simulation budgétaire, lisibilité DAF/achats — avec VNU/CAPN comme contexte natif
3. **Conformité « preuve-ready »** : OPERAT/BACS avec gouvernance, justificatifs, responsables, échéances, plan d'action priorisé et audit trail complet

### Chiffres clés du marché adressable

| Indicateur | Valeur |
|---|---|
| Sites B2B France (électricité) | 5,39 M sites non résidentiels (261 TWh) |
| Cible primaire (C2-C5 multi-sites) | ~100 000 entreprises |
| Dépense énergie annuelle B2B France | ~60 Mds € |
| Taux de pénétration outils dédiés | < 5% |
| SAM PROMEOS | ~500 M € |
| SOM année 3 | ~5 M € |

---

## 2. Contexte de marché

### 2.1 Dynamiques structurelles

Le marché français de l'énergie traverse cinq crises superposées qui redéfinissent les règles du jeu pour les entreprises B2B.

#### Crise 1 : Fin de l'ARENH et nouveau monde des prix

Le dispositif ARENH (Accès Régulé à l'Électricité Nucléaire Historique), qui permettait aux fournisseurs alternatifs d'acheter de l'électricité nucléaire à 42 €/MWh dans la limite de 100 TWh/an, a pris fin le **31 décembre 2025**. Ce dispositif structurant, en place depuis 2011, a été remplacé par de nouveaux mécanismes :

- **VNU (Vente au Nucléaire Universel)** : mécanisme de redistribution de la rente nucléaire d'EDF, qui vise un prix cible post-ARENH d'environ **~70 €₂₀₂₂/MWh**. Le prélèvement État est progressif : **50% au-dessus de 78 €/MWh**, puis **90% au-dessus de 110 €/MWh**, garantissant un encadrement des prix pour les consommateurs tout en assurant la rentabilité du parc nucléaire.
- **CAPN (Contrats d'Allocation de Production Nucléaire)** : contrats long terme (10-15 ans) réservés aux électro-intensifs, assurant une visibilité prix sur la durée.
- **Contrats moyen terme EDF post-ARENH** : les premiers contrats signés post-ARENH se positionnent à environ **~60 €/MWh** sur des durées de 4-5 ans, offrant une référence de prix pour le marché.
- **Enchères calendaires** : les produits Y+4/Y+5 s'échangent à **66-72 €/MWh**, reflétant les anticipations du marché à moyen terme.

**Impact sur les entreprises B2B** : La fin de l'ARENH a provoqué une hausse structurelle des prix de fourniture. Les prix B2B ont connu une hausse de **+50% fin 2023 par rapport à 2021** (source : Opéra Énergie / Les Echos Études décembre 2024). Une normalisation est en cours avec des prix convergeant vers la fourchette **60-77 €/MWh** pour les contrats moyen terme, mais la volatilité reste significativement plus élevée que dans le monde ARENH.

**Volumes ARENH 2025 (dernière année)** :

| Indicateur | Valeur |
|---|---|
| Volume demandé (hors filiales EDF) | 157,6 TWh |
| Volume attribué (consommateurs) | 100 TWh (plafond) |
| Volume pertes réseau | 22,7 TWh |
| Écrêtement | 34,9 TWh |

La transition vers le monde post-ARENH crée un besoin massif d'outils de pilotage pour les entreprises qui doivent désormais naviguer un marché plus complexe, plus volatile et plus cher.

#### Crise 2 : Réglementation croissante

Les obligations réglementaires se multiplient et s'alourdissent pour les entreprises :

**Décret tertiaire (Éco-énergie tertiaire)** :
- Obligation de réduction de la consommation énergétique des bâtiments tertiaires > 1 000 m²
- Objectifs : -40% en 2030, -50% en 2040, -60% en 2050 (par rapport à une année de référence ou à un seuil absolu)
- Déclaration annuelle sur la plateforme OPERAT de l'ADEME
- Sanctions : mise en demeure, publication du non-respect (« name & shame »), amende jusqu'à 7 500 € par site

**Décret BACS (Building Automation and Control Systems)** :
- Obligation d'installer un système d'automatisation et de contrôle pour les bâtiments tertiaires neufs et existants
- Seuil : bâtiments > 290 kW de puissance nominale de chauffage/climatisation
- Échéances : 1er janvier 2025 (bâtiments existants > 290 kW), 2027 (bâtiments > 70 kW)
- Inspections régulières obligatoires

**Audit énergétique** :
- Obligatoire tous les 4 ans pour les grandes entreprises (> 250 salariés ou CA > 50 M€)
- Alternative : certification ISO 50001
- Lien avec les CEE (Certificats d'Économies d'Énergie) pour le financement des actions

**CSRD (Corporate Sustainability Reporting Directive)** :
- Reporting extra-financier élargi incluant la performance énergétique
- Application progressive : 2025 (grandes entreprises cotées), 2026 (grandes non cotées), 2027 (PME cotées)
- Double matérialité : impact de l'énergie sur l'entreprise ET impact de l'entreprise sur le climat

**Obligations solarisation** :
- Obligation d'installation de panneaux photovoltaïques ou de végétalisation sur les toitures des bâtiments commerciaux, industriels et de bureaux
- **Bâtiments existants > 500 m² : obligation applicable dès janvier 2028** (Loi APER n°2023-175)
- Bâtiments neufs > 500 m² : déjà en vigueur (Loi Climat et Résilience)
- Parcs de stationnement > 1 500 m² : obligation progressive depuis juillet 2023

**TURPE 7** :
- Nouveaux tarifs d'utilisation des réseaux publics d'électricité en vigueur depuis le **1er août 2025** (CRE délibération n°2025-78)
- **Hausse d'environ +10%** par rapport au TURPE 6, reflétant les investissements massifs des gestionnaires de réseaux : **Enedis 5,5 Mds€/an** et **RTE 4 Mds€/an** pour moderniser et renforcer les réseaux face à l'électrification des usages, l'intégration des EnR et le développement des véhicules électriques
- Le réseau représente environ 28% de la facture d'un consommateur résidentiel au TRVE

#### Crise 3 : Volatilité des marchés de gros

La crise énergétique de 2022 a révélé la vulnérabilité des entreprises face à la volatilité des prix de gros :

- **Prix spot** : de ~50 €/MWh moyen en 2021 à un pic à 1 000+ €/MWh en août 2022, puis normalisation vers 60-80 €/MWh en 2024-2025
- **Marchés à terme** : les produits calendaires Y+1 à Y+5 offrent une visibilité prix mais avec des primes de risque significatives. En T4 2025, les volumes échangés ont atteint **1 897 TWh** (+20% sur un an), avec un open interest record de 24,1 GW pour Y_2026 (source : Bulletin CRE marchés de gros T4 2025)
- **Liquidité** : la fin de l'ARENH a paradoxalement amélioré la liquidité des marchés à terme, avec des maturités échangées jusqu'à Y+5

**Impact B2B** : Les entreprises doivent désormais développer une véritable stratégie d'achat (timing, durée, indexation, couverture) là où l'ARENH fournissait un prix stable et prévisible.

#### Crise 4 : Transition énergétique et électrification

La PPE3 (Programmation Pluriannuelle de l'Énergie 2026-2035) fixe des objectifs ambitieux qui transforment le paysage énergétique :

- **Consommation électrique** : objectif 1 243 TWh en 2030 (vs 439 TWh en 2023, point bas historique), tiré par l'électrification des transports, de l'industrie et du chauffage
- **Mix électrique 2035** : 48 GW PV, 31 GW éolien terrestre, 15 GW éolien offshore, 380 TWh nucléaire (6 EPR2 en construction)
- **Sortie des fossiles** : -50% gaz et pétrole d'ici 2035
- **Rénovation bâtiment** : 900 000 rénovations performantes par an d'ici 2030
- **Flexibilités** : 6,5 GW de capacités flexibles à développer (stockage, effacement, pilotage de la demande)
- **CEE Période 6** : 1 050 TWhc/an d'obligations, hausse significative

#### Crise 5 : Complexification de la facture

La facture d'électricité d'une entreprise française comporte aujourd'hui plus de **30 composantes** réparties en plusieurs catégories :

| Catégorie | Composantes principales | Part facture résidentiel TRVE |
|---|---|---|
| Fourniture | Prix de l'énergie (fixe/indexé/spot), profil de consommation | ~39% |
| Acheminement (TURPE) | Composante de gestion, comptage, soutirage (fixe + variable), injection | ~28% |
| Taxes et contributions | Accise sur l'électricité (ex-TICFE/CSPE), TVA (20%), CTA | ~33% |

**Détail des taxes et contributions (depuis août 2025)** :

| Composante | Taux 2025-2026 |
|---|---|
| Accise électricité (particuliers) | 29,98 €/MWh |
| Accise électricité (entreprises) | 25,79 €/MWh |
| TVA | 20% sur part fixe et part variable |
| CTA | ~3% de la facture |
| Capacité | Variable selon enchères (0 €/MW en déc 2024) |

Cette complexité rend l'analyse et le contrôle des factures quasi impossible sans outil dédié, d'autant que les erreurs de facturation sont fréquentes (estimations erronées, application de mauvais tarifs TURPE, erreurs de puissance souscrite, doublons de taxes).

### 2.2 Taille de marché adressable (TAM / SAM / SOM)

#### Marché français de l'électricité B2B — Données CRE T4 2025

Le marché français de l'électricité compte **41,1 millions de sites éligibles** pour une consommation annuelle d'environ **414 TWh** (Observatoire CRE T4 2025).

**Répartition détaillée des 40+ millions de sites de consommation** :

| Segment | Sites | Consommation | Profil |
|---|---|---|---|
| Résidentiels | 35,02 M (34,7 M hors ELD) | 146 TWh (142 TWh hors ELD) | Ménages, compteurs ≤ 36 kVA |
| Petits professionnels | 4,84 M (4,8 M hors ELD) | ~40 TWh (~37 TWh hors ELD) | Commerces, artisans, TPE, C5 |
| Sites moyens | 458 K (447 K hors ELD) | ~45 TWh (~43 TWh hors ELD) | PME, C3-C4 |
| Grands sites | 100 K (99 K hors ELD) | ~183 TWh (~182 TWh hors ELD) | Industrie, tertiaire, C1-C2 |
| **Total non résidentiel** | **5,39 M** | **261 TWh** | **Cible B2B** |

**Trajectoire de consommation** : La consommation française d'électricité a atteint un **point bas en 2023 à 439 TWh**. La cible RTE pour 2035 est de **590-640 TWh**, tirée par l'électrification massive des usages (véhicules électriques, pompes à chaleur, hydrogène, industrie). Cette croissance structurelle augmente mécaniquement la taille du marché adressable.

**Dynamique concurrentielle B2B** :

| Segment | Part alternatifs (sites) | Part alternatifs (volume) | Tendance |
|---|---|---|---|
| Résidentiel | 31,8% | 29,5% | Accélération (+556K sites en 2025) |
| Petits pro | ~35% | ~38% | Progression régulière |
| Sites moyens | 52% | 57% | Majorité alternative |
| Grands sites | 51% | 54% | Équilibre |

#### Dimensionnement TAM / SAM / SOM

**TAM (Total Addressable Market)** — Marché total adressable :
- Ensemble des dépenses d'énergie des entreprises françaises
- ~60 Mds € annuels (électricité + gaz + réseaux + taxes)
- Taux de service potentiel : 1-3% = **600 M€ - 1,8 Md€**

**SAM (Serviceable Addressable Market)** — Marché adressable par PROMEOS :
- Cible : entreprises multi-sites (> 3 sites), dépense énergie > 100 K€/an
- Estimation : ~50 000 entreprises
- ARPA cible : 10-50 K€/an
- **SAM : ~500 M€**

**SOM (Serviceable Obtainable Market)** — Marché capturable à 3 ans :
- Objectif : 100-200 clients
- ARPA réalisé : 25-50 K€/an
- **SOM année 3 : ~5 M€ ARR**

#### Marché gaz naturel B2B

Le marché du gaz naturel représente un complément significatif :

| Segment | Sites | Consommation |
|---|---|---|
| Résidentiel | 10,34 M | 94 TWh |
| Non résidentiel distribution | 625 K | 143 TWh |
| Non résidentiel transport | 1 000 | 108 TWh |
| **Total** | **~11 M** | **~348 TWh** |

Les entreprises B2B multi-sites gèrent généralement des contrats d'électricité ET de gaz. PROMEOS couvre nativement les deux énergies.

### 2.3 Tendances émergentes

Cinq tendances de fond transforment le paysage énergétique B2B et créent de nouvelles opportunités pour PROMEOS.

#### 2.3.1 Autoconsommation photovoltaïque

L'autoconsommation photovoltaïque connaît une croissance explosive en France :

- **494 000 installations** en autoconsommation au T1 2024
- **2,6 GWc** de puissance cumulée installée
- **Croissance de +124% en 2023** par rapport à 2022
- L'obligation de solarisation des bâtiments existants > 500 m² dès janvier 2028 constitue un **nouveau driver massif** qui va accélérer encore l'adoption dans le tertiaire et l'industrie

**Impact PROMEOS** : L'autoconsommation complexifie la facture (injection, surplus, autoconsommation, TURPE injection) et crée un besoin de pilotage intégré production/consommation/facturation.

#### 2.3.2 Stockage par batteries et flexibilité

Le marché du stockage stationnaire par batteries connaît une accélération remarquable :

- **701 MW** installés en France en 2023
- **Cible de 3 GW en 2028** (multiplication par 4)
- La PPE3 vise **6,5 GW de capacités flexibles** à l'horizon 2035
- Les modèles d'affaires se diversifient : FCR (réserve primaire), mécanisme de capacité (MÉCAPA), PPA hybrides (PV + stockage), arbitrage prix

**La flexibilité devient un nouveau terrain de jeu** pour les entreprises disposant d'actifs pilotables (batteries, IRVE, process industriels, climatisation tertiaire). PROMEOS intègre l'analyse de flexibilité comme composante native de son cockpit.

#### 2.3.3 CPPA (Corporate Power Purchase Agreements)

Les CPPA se développent rapidement en France :

- **4,9 TWh cumulés** sous contrat CPPA
- **26 CPPA signés en 2024**, un record
- **84% des CPPA sont « greenfield »** (financement de nouvelles installations EnR)
- Les CPPA offrent une visibilité prix sur 10-20 ans et un verdissement vérifiable (Garanties d'Origine traçables)

**Impact PROMEOS** : Les CPPA ajoutent une couche de complexité dans la stratégie d'achat (mix CPPA + marché + couvertures) que seul un cockpit intégré peut piloter efficacement.

#### 2.3.4 Tarification dynamique et signaux prix

L'émergence des tarifs dynamiques (type Tempo étendu, offres spot, demand response) crée de nouvelles opportunités d'optimisation :

- Tarif Tempo : économies potentielles de 20-30% pour les profils adaptés
- Offres spot : exposition directe au marché, forte volatilité
- Demand response / effacement : rémunération pour la réduction de consommation en période de pointe

#### 2.3.5 Données et intelligence artificielle

La disponibilité croissante des données énergétiques (compteurs communicants Linky/Gazpar, API Enedis/GRDF, SGE) et les progrès de l'IA ouvrent de nouvelles possibilités :

- Détection automatique d'anomalies de facturation
- Prévision de consommation et de coûts
- Optimisation automatique des puissances souscrites
- Recommandations personnalisées d'achat
- Classification automatique des sites (benchmark sectoriel)

---

## 3. Cartographie des acteurs

Le marché de l'énergie B2B en France fait intervenir de nombreux acteurs dont les rôles, les intérêts et les chaînes de valeur sont profondément interconnectés.

### 3.1 Fournisseur historique

**Acteurs** : EDF (62% du marché résidentiel en sites+OA), Engie (via ses filiales historiques de distribution), ELD (Entreprises Locales de Distribution — Strasbourg, Grenoble, Metz, etc.)

**Rôle** : Fourniture d'énergie (électricité et/ou gaz) aux tarifs réglementés (TRVE, PRVG) et en offres de marché. Les fournisseurs historiques restent dominants, en particulier sur le segment résidentiel.

**Forces** :
- Base clients massive et inertielle (55,8% du résidentiel au TRVE pour EDF)
- Marque de confiance institutionnelle
- Accès à l'énergie nucléaire (EDF) = avantage coût structurel post-ARENH
- Portails clients développés (EDF Pro, ENGIE BiLL-e)
- Capacité de bundling (fourniture + services + maintenance)

**Faiblesses** :
- Innovation lente (organisation bureaucratique)
- Conflits d'intérêts entre fourniture et conseil (optimiser le client = réduire sa consommation = réduire le chiffre d'affaires)
- Portails orientés fourniture, pas pilotage multi-fournisseurs
- Lock-in client par la fourniture, pas par la valeur

**Relation PROMEOS** : Complémentarité partielle. Les fournisseurs historiques sont des partenaires potentiels (intégration de PROMEOS dans leurs offres de services à valeur ajoutée) mais aussi des concurrents potentiels s'ils développent leurs propres outils de pilotage. La neutralité de PROMEOS (pas de fourniture) est un avantage décisif pour les clients multi-fournisseurs.

### 3.2 Fournisseur alternatif

**Acteurs** : TotalEnergies, Vattenfall, Alpiq, Eni, Iberdrola, Mint Énergie, Ekwateur, Ovo Energy, Plüm, etc.

**Rôle** : Fourniture d'énergie en offres de marché, souvent positionnées sous le TRVE. Les alternatifs gagnent des parts de marché régulièrement.

**Dynamique de marché** (CRE T4 2025) :
- Résidentiel : 31,8% des sites, 29,5% du volume (+556K sites en 2025)
- Non résidentiel : 41% des sites, 53,3% du volume
- 2025 marque un basculement : les alternatifs captent davantage que les historiques OM

**Forces** :
- Agilité commerciale et innovation tarifaire
- Offres compétitives (post-ARENH, accès aux marchés de gros, PPA)
- Offres vertes attractives (72% des offres résidentielles sont vertes)
- Pure players digitaux avec UX soignée

**Faiblesses** :
- Fragilité financière (plusieurs faillites post-crise 2022 : Hydroption, Bulb, etc.)
- Taille limitée sur le segment B2B grands comptes
- Pas d'outils de pilotage multi-fournisseurs
- Turn élevé (clients peu fidèles, sensibles au prix)

**Relation PROMEOS** : Partenariat possible comme canal de distribution (l'alternatif propose PROMEOS à ses clients comme service à valeur ajoutée). PROMEOS renforce la fidélisation des clients de l'alternatif en apportant de l'intelligence au-delà du simple prix.

### 3.3 GRD / GRT

**Acteurs** :
- **GRD** : Enedis (95% du réseau de distribution électrique), GRDF (réseau de distribution gaz), ELD locales
- **GRT** : RTE (réseau de transport électrique), GRTgaz / Teréga (réseau de transport gaz)

**Rôle** : Gestion, exploitation et développement des réseaux de transport et de distribution d'énergie. Tarification de l'acheminement (TURPE, ATRD, ATRT).

**Forces** :
- Monopole naturel régulé
- Données massives (compteurs communicants : 36M Linky, 12M Gazpar)
- APIs ouvertes en développement (SGE Enedis, API GRDF)
- Neutralité vis-à-vis des fournisseurs

**Faiblesses** :
- Pas de vocation commerciale directe
- Investissements lourds à financer (5,5 Mds€/an Enedis, 4 Mds€/an RTE → hausse TURPE 7)
- Données parfois difficiles d'accès (processus d'habilitation, latence)

**Relation PROMEOS** : Source de données critique. PROMEOS consomme les données Enedis (courbes de charge, index, puissances) et GRDF (consommations gaz) via les APIs ouvertes. L'accès à ces données est un actif stratégique.

### 3.4 Éditeur SaaS énergie

**Acteurs** : Ubigreen, Advizeo (Setec), Deepki, Citron, Datanumia (EDF), Energisme, Hxperience (Wizata), Dalkia Analytics (EDF/Veolia)

**Rôle** : Plateformes logicielles de gestion de l'énergie (EMS — Energy Management System), de données extra-financières (ESG), de gestion technique du bâtiment (GTB/GTC).

**Forces** :
- Expertise technique profonde (mesure, IoT, GTB)
- Base clients installée (Ubigreen : +50 000 sites, Deepki : +600 clients)
- Levées de fonds significatives (Deepki : 150 M€, Energisme : introduction en bourse)
- Intégrations hardware/software (capteurs, sous-compteurs)

**Faiblesses** :
- Focus technique (kWh, température, puissance) plus que financier (€, facture, budget)
- Faible couverture de la facture détaillée et de la stratégie d'achat
- Souvent orientés résidentiel/tertiaire, moins industrie
- Pas de neutralité (certains sont filiales de fournisseurs)

**Relation PROMEOS** : Concurrence partielle sur la brique consommation/performance, mais complémentarité forte. Les EMS gèrent le kWh technique ; PROMEOS gère le € décisionnel. Partenariat possible : PROMEOS comme couche « intelligence financière » au-dessus d'un EMS technique.

### 3.5 Courtier en énergie

**Acteurs** : Opéra Énergie, Enoptea (hybride courtier/éditeur), Selectra, Hello Watt, Mega Énergie, JeChange, Comparateur-Energie

**Rôle** : Intermédiation entre les entreprises et les fournisseurs d'énergie. Le courtier aide l'entreprise à trouver la meilleure offre en lançant des appels d'offres auprès de plusieurs fournisseurs.

**Dynamique de marché** (CRE T4 2025) :
- **55 offres B2C sur 67 étaient moins chères que le TRVE** en décembre 2024 (avant baisse TRVE février 2025)
- Discounts courants de **-25% à -30%** par rapport au TRVE
- Le marché post-ARENH ouvre une **fenêtre massive pour le courtage neutre** : la complexification des offres et la disparition du prix de référence ARENH rendent l'intermédiation plus précieuse que jamais
- Au T4 2025, 47 offres restent sous le TRVE malgré la baisse de février 2025

**Forces** :
- Accès à un panel large de fournisseurs
- Expertise marché et négociation
- Modèle économique simple (commission sur le contrat)
- Pas de risque de portage (pas de fourniture)

**Faiblesses** :
- Valeur limitée dans le temps (uniquement au moment du renouvellement)
- Pas de suivi post-signature (facture, consommation, conformité)
- Conflits d'intérêts potentiels (commission versée par le fournisseur)
- Pas d'outil de pilotage continu

**Relation PROMEOS** : Complémentarité forte. Le courtier intervient ponctuellement (au renouvellement) ; PROMEOS intervient en continu (analyse, pilotage, conformité). PROMEOS peut être le « bras armé analytique » du courtier, ou le courtier peut être un canal de distribution pour PROMEOS. La stratégie d'achat PROMEOS peut naturellement alimenter un processus de courtage.

### 3.6 Agrégateur de flexibilité

**Acteurs** : Energy Pool (Schneider), Agregio Solutions (EDF), Flexible Power Solutions (TotalEnergies), Flexcity (Veolia), Smart Grid Energy (Vinci), Enel X, Voltalis, Engie Flex Gen

**Rôle** : Agrégation et valorisation de la flexibilité des consommateurs et producteurs sur les marchés de l'énergie (effacement, réserves, capacité, arbitrage).

**Données de marché clés** :
- **Garanties de capacité 2025** : prix tombé à **0 €/MW** lors de la 9e enchère (décembre 2024), reflétant un excédent de capacité
- **FCR (réserve primaire)** : rémunération d'environ **~152 k€/MW/an**, marché le plus rémunérateur pour les batteries
- **aFRR (réserve secondaire)** : en cours d'ouverture aux batteries, nouveau gisement de revenus
- **NEBEF (Notification d'Échange de Bloc d'Effacement)** : mécanisme d'effacement de consommation valorisé sur les marchés spot

**Principaux agrégateurs** :

| Agrégateur | Groupe | Spécialité |
|---|---|---|
| Agregio Solutions | EDF | Batteries, EnR, industriels |
| Flexible Power Solutions | TotalEnergies | Industriels, multi-énergie |
| Flexcity | Veolia | Bâtiments tertiaires, GTB |
| Smart Grid Energy | Vinci | Infrastructures, IRVE |
| Energy Pool | Schneider | Industriels, grands effacements |

**Forces** :
- Expertise technique pointue (algorithmes d'optimisation, trading)
- Accès aux marchés organisés (EPEX, RTE)
- Relations directes avec les gestionnaires de réseau
- Modèle économique à forte valeur (partage de revenus)

**Faiblesses** :
- Cible limitée (clients avec des actifs flexibles significatifs)
- Complexité technique élevée (barrière à l'entrée pour les clients)
- Pas de couverture de la facture ou de la conformité
- Marchés de capacité à prix nul (2024) = revenus sous pression

**Relation PROMEOS** : Partenariat naturel. PROMEOS identifie le potentiel de flexibilité des clients (analyse des courbes de charge, identification des actifs pilotables, estimation des revenus) et oriente vers l'agrégateur adapté. PROMEOS ne fait PAS de trading ni d'agrégation — il fait le **diagnostic et l'orientation**.

### 3.7 Producteur EnR

**Acteurs** : Neoen, Voltalia, Akuo Energy, Boralex, Total Eren, EDF Renouvelables, Engie Green, Q Energy, Urbasolar (Axpo)

**Rôle** : Développement, construction et exploitation de centrales de production d'énergie renouvelable (photovoltaïque, éolien, biomasse, hydroélectricité).

**Données de marché clés — Photovoltaïque France** :

| Indicateur | Valeur |
|---|---|
| Puissance installée (2024) | ~19 GW |
| Objectif PPE3 2030 | 54-60 GW |
| Objectif PPE3 2035 | 75-100 GW |
| Prix panneaux (mars 2024) | 0,13 €/Wc (effondrement -51% vs 2016) |
| CPPA PV annoncés T1 2024 | 15 contrats (845 GWh/an) |
| Installations autoconsommation | 494 000 (T1 2024), 2,6 GWc |

**Éolien France** :

| Indicateur | Valeur |
|---|---|
| Éolien terrestre installé | ~22 GW |
| Objectif PPE3 2030 | 31 GW |
| Éolien offshore installé | ~1,5 GW |
| Objectif PPE3 2035 | 15 GW offshore |

L'effondrement du prix des panneaux PV (-51% vs 2016 à 0,13 €/Wc en mars 2024) combiné aux obligations de solarisation crée une accélération forte du déploiement. **15 PPA PV ont été annoncés au T1 2024** pour un volume de 845 GWh/an, reflétant l'appétit croissant des entreprises pour un approvisionnement vert à prix garanti.

**Forces** :
- Coûts de production en baisse continue (PV : LCOE ~30-50 €/MWh)
- Soutien réglementaire fort (PPE3, obligations solarisation, complément de rémunération)
- CPPA comme nouveau canal de commercialisation directe
- Verdissement traçable (Garanties d'Origine)

**Faiblesses** :
- Intermittence (besoin de stockage/flexibilité)
- Délais de développement longs (permitting, raccordement)
- Dépendance aux aides publiques pour certains segments
- Pas d'outils de pilotage client

**Relation PROMEOS** : PROMEOS aide les entreprises à évaluer l'opportunité d'un CPPA (simulation économique, comparaison avec les alternatives de marché), à piloter l'autoconsommation (suivi production/consommation/injection) et à intégrer la production EnR dans leur stratégie d'achat globale. Les producteurs EnR sont des partenaires potentiels pour le référencement de leurs offres dans le module Purchase Strategy.

---

## 4. Analyse concurrentielle

### 4.1 Matrice fonctionnelle

La matrice ci-dessous compare les principaux acteurs sur les 5 piliers fonctionnels de PROMEOS.

**Légende** : ✓ = couvert | ⚠️ = partiel | ✗ = non couvert

| Acteur | Type | Facture (Bill Intelligence) | Conformité (OPERAT/BACS) | Achat (Purchase Strategy) | Performance (Consommation) | Flexibilité | Patrimoine multi-sites |
|---|---|---|---|---|---|---|---|
| **PROMEOS** | Cockpit SaaS | ✓ | ✓ | ✓ | ✓ | ⚠️ | ✓ |
| **Ubigreen** | EMS SaaS | ⚠️ | ✓ | ✗ | ✓ | ⚠️ | ✓ |
| **Deepki** | ESG SaaS | ⚠️ | ⚠️ | ✗ | ✓ | ✗ | ✓ |
| **Advizeo** | EMS SaaS | ✗ | ⚠️ | ✗ | ✓ | ✗ | ✓ |
| **Citron** | EMS SaaS | ✗ | ✗ | ✗ | ✓ | ⚠️ | ✓ |
| **Energisme** | Data SaaS | ⚠️ | ✗ | ✗ | ✓ | ✗ | ✓ |
| **Schneider RA+** | Suite Enterprise | ⚠️ | ✗ | ✓ | ✓ | ⚠️ | ✓ |
| **Enoptea** | Hybride SaaS/Service | ⚠️ | ✗ | ⚠️ | ✗ | ✗ | ⚠️ |
| **WattValue** | Audit/Conseil | ✓ | ✗ | ⚠️ | ✗ | ✗ | ✗ |
| **Opéra Énergie** | Courtier | ⚠️ | ✗ | ✓ | ✗ | ✗ | ✗ |
| **Optima Énergie** | Courtier/Conseil | ⚠️ | ✗ | ✓ | ✗ | ✗ | ✗ |
| **EDF Pro** | Portail fournisseur | ✓ | ✗ | ✗ | ⚠️ | ✗ | ⚠️ |
| **ENGIE BiLL-e** | Portail fournisseur | ⚠️ | ✗ | ⚠️ | ⚠️ | ✗ | ⚠️ |
| **Datanumia** | EMS (EDF) | ✗ | ✗ | ✗ | ✓ | ✗ | ⚠️ |
| **Energy Pool** | Agrégateur | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |

**Constats clés** :

1. **Aucun acteur ne couvre les 5 piliers** — PROMEOS est le seul cockpit intégrant facture + conformité + achat + performance + patrimoine
2. **Le trou dans le marché** est à l'intersection facture explicable + achat post-ARENH + conformité preuve-ready
3. **Les EMS** (Ubigreen, Advizeo, Citron) sont forts sur la performance technique (kWh) mais faibles sur la dimension financière (€) et l'achat
4. **Les courtiers** (Opéra, Optima) sont forts sur l'achat ponctuel mais n'offrent aucun suivi continu
5. **Les portails fournisseurs** (EDF Pro, ENGIE BiLL-e) sont limités à leur propre périmètre de fourniture — inutiles pour les clients multi-fournisseurs
6. **Enoptea** représente la menace la plus frontale : approche hybride expert + logiciel couvrant facture, achat et budget, mais sans couverture conformité ni performance énergétique

### 4.2 Positionnement différenciant PROMEOS

PROMEOS se positionne dans un espace unique que nous appelons le **« cockpit décisionnel énergie B2B »** :

```
                    Complexité d'usage
                         ▲
                         │
     EMS techniques      │      Suites enterprise
     (Ubigreen,          │      (Schneider RA+)
      Advizeo)           │
                         │
    ─────────────────────┼──────────────────────► Couverture fonctionnelle
                         │
     Outils simples      │     ★ PROMEOS
     (courtiers,         │     Cockpit décisionnel
      portails)          │     intégré
                         │
```

**Le positionnement « Fournisseur 4.0 sans la fourniture »** signifie :

| Ce que fait un fournisseur 4.0 | PROMEOS le fait | Sans la fourniture |
|---|---|---|
| Analyse de la consommation | ✓ Analytics multi-sites | Pas de vente de kWh |
| Optimisation tarifaire | ✓ Shadow billing, puissance souscrite | Pas de contrat de fourniture |
| Stratégie d'achat | ✓ Scénarios, exposition, budget | Pas de position de marché |
| Conformité réglementaire | ✓ OPERAT, BACS, audit trail | Pas de conflit d'intérêt |
| Conseil et recommandations | ✓ Actions priorisées avec ROI | Indépendance totale |
| Verdissement | ✓ Analyse GO, simulation CPPA | Pas de commercialisation EnR |

**Avantage clé** : l'absence de fourniture garantit la **neutralité des recommandations**. Quand PROMEOS recommande de changer de fournisseur, de modifier sa puissance souscrite ou de signer un CPPA, c'est dans l'intérêt exclusif du client — pas pour générer du chiffre d'affaires de fourniture.

---

## 5. Proposition de valeur PROMEOS

### 5.1 Vision

> **« Donner à chaque entreprise française la maîtrise totale de sa performance énergétique — sans être fournisseur d'énergie. »**

PROMEOS ambitionne de devenir la **plateforme de référence** pour les entreprises B2B françaises qui veulent :

1. **Comprendre** exactement ce qu'elles paient et pourquoi
2. **Optimiser** leurs coûts énergétiques de manière continue
3. **Sécuriser** leur conformité réglementaire
4. **Piloter** leur stratégie d'achat avec des données fiables
5. **Décider** sur la base d'une information claire, explicable et actionnable

### 5.2 Les 5 piliers fonctionnels

#### Pilier 1 : Bill Intelligence — « La facture explicable »

**Problème** : Les factures d'énergie sont opaques, complexes (30+ composantes), souvent erronées, et les entreprises n'ont ni le temps ni l'expertise pour les décrypter.

**Solution PROMEOS** :
- **Shadow billing** : recalcul théorique de chaque facture à partir des données de consommation réelles et des grilles tarifaires en vigueur (TURPE 7, accises, TVA, CTA, capacité)
- **Détection d'anomalies** : identification automatique des écarts entre facture reçue et facture théorique, avec classification de la cause probable (erreur de comptage, mauvais tarif TURPE, erreur de puissance souscrite, taxe manquante, etc.)
- **Explicabilité** : chaque ligne de la facture est décomposée, annotée et reliée à sa source réglementaire
- **Action** : pour chaque anomalie détectée, PROMEOS propose une action correctrice avec estimation du ROI (ex : « réclamation au fournisseur pour erreur TURPE : 3 200 € récupérables »)

**KPIs** :
- Taux de détection d'anomalies : > 95%
- Temps moyen de traitement d'une facture : < 5 secondes
- Montant moyen d'économies identifiées par client : 2-5% de la facture annuelle

#### Pilier 2 : Purchase Strategy — « L'achat piloté »

**Problème** : Dans le monde post-ARENH, les entreprises doivent construire une stratégie d'achat (timing, durée, indexation, mix) sans avoir les outils ni l'expertise d'un trader.

**Solution PROMEOS** :
- **Exposition** : visualisation de l'exposition au marché du portefeuille de contrats (couvert / ouvert / à renouveler)
- **Scénarios d'achat** : simulation de l'impact budgétaire de différentes stratégies (fixe vs indexé vs mix, VNU vs marché, CPPA vs spot)
- **Radar de renouvellement** : alerte anticipée sur les contrats arrivant à échéance, avec fenêtre d'achat optimale
- **Budget prévisionnel** : projection des coûts à 12-36 mois selon différents scénarios de marché
- **Tableau de bord DAF** : vue consolidée des engagements, des risques et des opportunités

**KPIs** :
- Anticipation moyenne des renouvellements : > 6 mois
- Réduction du coût d'achat vs benchmark marché : 3-8%
- Couverture du portefeuille : > 80% des volumes couverts

#### Pilier 3 : Conformité — « La preuve-ready »

**Problème** : Les obligations réglementaires (décret tertiaire, BACS, audit, CSRD) se multiplient et exigent des données structurées, des preuves d'action et un suivi rigoureux — que la plupart des entreprises gèrent encore dans des fichiers Excel.

**Solution PROMEOS** :
- **OPERAT** : préparation et export des déclarations annuelles (consommations par site, année de référence, trajectoire)
- **BACS** : suivi de l'état d'équipement et de conformité de chaque bâtiment
- **Audit trail** : qui a déclaré quoi, quand, avec quelle preuve, quel responsable
- **Plan d'action** : priorisation des actions de réduction (par impact €, par urgence réglementaire, par faisabilité)
- **Gouvernance** : attribution des responsabilités par site, par obligation, avec échéancier et alertes

**KPIs** :
- Taux de conformité OPERAT des sites gérés : > 95%
- Temps de préparation d'une déclaration : réduit de 80%
- Nombre de sites en risque de non-conformité identifié en avance : 100%

#### Pilier 4 : Performance — « La consommation pilotée »

**Problème** : Les entreprises multi-sites manquent de visibilité sur leur consommation réelle, ses tendances et ses anomalies, par site et par usage.

**Solution PROMEOS** :
- **Dashboard multi-sites** : vue consolidée de la consommation (kWh, €, CO₂) par site, par bâtiment, par usage
- **Benchmark** : comparaison inter-sites (kWh/m², €/m², DJU corrigé) et sectoriel
- **Alertes** : détection de dérives de consommation (surconsommation nocturne, week-end, jours fériés)
- **Puissance souscrite** : analyse et recommandation d'optimisation de la puissance souscrite (TURPE)
- **Corrélations** : analyse DJU/consommation, HP/HC, profil de charge

**KPIs** :
- Nombre de sites monitorés : illimité
- Fréquence de rafraîchissement des données : quotidienne (via API Enedis/GRDF)
- Anomalies détectées par site et par an : 5-15 en moyenne

#### Pilier 5 : Patrimoine — « La vue d'ensemble »

**Problème** : Les entreprises multi-sites (multi-entités, multi-fournisseurs, multi-sites, multi-compteurs) n'ont aucune vue unifiée de leur patrimoine énergétique.

**Solution PROMEOS** :
- **Référentiel** : base de données structurée de l'ensemble du patrimoine (entités juridiques, sites, bâtiments, compteurs, contrats)
- **Segmentation** : classification des sites par critères métier (activité, surface, usage, performance)
- **Hiérarchie** : modélisation de l'organisation (groupe → filiale → site → bâtiment → compteur)
- **Scope** : gestion multi-périmètres (DG, direction immobilier, direction achats — chacun voit « son » périmètre)
- **Import/export** : intégration des données depuis des sources multiples (fichiers, API, connecteurs)

**KPIs** :
- Complétude du référentiel : > 90% des champs renseignés
- Temps de setup d'un nouveau client : < 2 jours
- Nombre d'entités/sites gérés : illimité

### 5.3 Personas cibles

PROMEOS s'adresse à 5 personas principaux au sein des entreprises B2B multi-sites :

| Persona | Rôle | Besoin principal | Pilier PROMEOS principal |
|---|---|---|---|
| **DAF / CFO** | Directeur Administratif et Financier | Maîtrise budgétaire, visibilité coûts, réduction des écarts | Bill Intelligence + Purchase Strategy |
| **Directeur Immobilier** | Gestion du parc immobilier | Conformité réglementaire, performance des bâtiments | Conformité + Performance |
| **Responsable Énergie / RSE** | Pilotage énergétique et RSE | Données fiables, reporting, plan d'action | Performance + Conformité |
| **Acheteur Énergie** | Négociation et gestion des contrats | Stratégie d'achat, benchmark, timing | Purchase Strategy |
| **DG / COMEX** | Direction Générale | Vue d'ensemble, alertes critiques, ROI | Cockpit synthétique |

---

## 6. Modèle économique

### 6.1 Pricing

PROMEOS adopte un modèle **SaaS par abonnement** avec une tarification progressive basée sur le nombre de sites et les modules activés.

#### Grille tarifaire indicative

| Plan | Sites | Modules inclus | Prix indicatif |
|---|---|---|---|
| **Starter** | 1-10 sites | Patrimoine + Facture + Performance | 500-1 000 €/mois |
| **Business** | 11-50 sites | Tous les modules | 1 500-3 000 €/mois |
| **Enterprise** | 51-500 sites | Tous les modules + support dédié + API | 3 000-8 000 €/mois |
| **Corporate** | 500+ sites | Sur mesure | Sur devis |

#### Options additionnelles

| Option | Prix indicatif |
|---|---|
| Shadow billing avancé (recalcul automatique) | +20% du plan |
| Module Purchase Strategy (scénarios d'achat) | +30% du plan |
| Module Conformité OPERAT/BACS | +20% du plan |
| Module Flexibilité (diagnostic + orientation) | +15% du plan |
| Connecteur API personnalisé | Sur devis |
| Formation et accompagnement setup | Forfait 2-5 K€ |

#### Modèle de revenus complémentaires

- **Commission de performance** : pourcentage des économies identifiées et réalisées (5-15% des gains sur la facture)
- **Données anonymisées** : benchmark sectoriel (agrégé, anonymisé, opt-in) — revenus marginaux
- **Marketplace partenaires** : référencement de courtiers, agrégateurs, installateurs — commission d'apporteur d'affaires (5-10%)

### 6.2 Unit economics

| Métrique | Cible Année 1 | Cible Année 3 |
|---|---|---|
| ARPA (Average Revenue Per Account) | 15 K€/an | 35 K€/an |
| CAC (Customer Acquisition Cost) | 5-10 K€ | 3-5 K€ |
| LTV (Lifetime Value) | 45-75 K€ | 105-175 K€ |
| LTV/CAC | 5-10x | 20-35x |
| Churn annuel | < 15% | < 10% |
| Payback period | 4-8 mois | 1-2 mois |
| Marge brute SaaS | > 70% | > 80% |
| NDR (Net Dollar Retention) | > 110% | > 120% |

**Hypothèses clés** :
- Rétention forte grâce à la profondeur d'intégration (données patrimoniales, historiques de facturation, conformité)
- Expansion revenue via l'ajout de sites et de modules
- Coût de service marginal décroissant (économies d'échelle sur l'infrastructure et les données réglementaires)

---

## 7. Architecture produit

### 7.1 Stack technique

| Composante | Technologie | Justification |
|---|---|---|
| **Backend** | FastAPI (Python) | Performance, typage, async, écosystème data |
| **Frontend** | React + Vite | Rapidité de développement, écosystème riche |
| **Base de données** | SQLite (POC) → PostgreSQL (prod) | Simplicité POC, robustesse production |
| **Authentification** | JWT + rôles (DG_OWNER, ADMIN, USER) | Standards, stateless, granulaire |
| **API** | REST + OpenAPI 3.0 | Interopérabilité, documentation auto |
| **Export** | PDF (jsPDF natif), CSV, XLSX | Formats métier standards |
| **CI/CD** | GitHub Actions | Automatisation tests + déploiement |
| **Conteneurisation** | Docker + docker-compose | Reproductibilité, déploiement simplifié |
| **Monitoring** | Monitoring light intégré | Santé application, alertes |

### 7.2 Modules fonctionnels

```
┌─────────────────────────────────────────────────────────┐
│                    PROMEOS COCKPIT                        │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │   Bill    │  │ Purchase │  │Conformité│  │  Perf    │ │
│  │ Intelli- │  │ Strategy │  │  OPERAT  │  │ Énergie  │ │
│  │  gence   │  │          │  │  BACS    │  │          │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │       │
│  ┌────┴──────────────┴──────────────┴──────────────┴────┐ │
│  │              PATRIMOINE (Référentiel)                  │ │
│  │     Entités → Sites → Bâtiments → Compteurs           │ │
│  └──────────────────────┬───────────────────────────────┘ │
│                          │                                 │
│  ┌───────────────────────┴──────────────────────────────┐ │
│  │              DONNÉES & INTÉGRATIONS                    │ │
│  │   Enedis API │ GRDF API │ Import CSV │ Connecteurs    │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 7.3 Intégrations

| Source / Cible | Type | Données | Statut |
|---|---|---|---|
| **Enedis (SGE)** | API | Courbes de charge, index, puissances | En développement |
| **GRDF** | API | Consommations gaz, index | Planifié |
| **OPERAT (ADEME)** | Export CSV/API | Déclarations réglementaires | En développement |
| **Fournisseurs** | Import CSV/PDF | Factures, contrats | Opérationnel |
| **ERP clients** | API REST | Référentiel patrimonial, budgets | Planifié |
| **Marchés de gros** | API (EEX/EPEX) | Prix spot, forward, références | Planifié |
| **CRE / data.gouv** | Scraping / API | Tarifs réglementaires, offres | Opérationnel |
| **ADEME Base Empreinte** | Données V23.6 | Facteurs d'émission CO₂ | Intégré |

---

## 8. Go-to-market

### 8.1 Segmentation client

PROMEOS segmente ses clients cibles selon leur taille, leur maturité énergétique et leur douleur principale.

#### Segmentation par taille

| Segment | Profil | Nombre de sites | Dépense énergie | Priorité |
|---|---|---|---|---|
| **PME multi-sites** | Retail, restauration, santé | 5-20 sites | 100 K€ - 1 M€ | Haute |
| **ETI** | Industrie, logistique, tertiaire | 20-100 sites | 1-10 M€ | Très haute |
| **Grands comptes** | Groupes nationaux, bancassurance | 100-1000 sites | 10-100 M€ | Moyenne (cycle long) |
| **Collectivités** | Communes, intercommunalités, départements | 50-500 sites | 500 K€ - 20 M€ | Haute |

#### Segmentation par maturité

| Niveau | Description | Outil actuel | Besoin PROMEOS |
|---|---|---|---|
| **Niveau 0** | Aucune gestion structurée | Excel, rien | Patrimoine + Facture |
| **Niveau 1** | Suivi basique des factures | Excel avancé, ERP | Bill Intelligence |
| **Niveau 2** | Gestion active de l'énergie | EMS partiel | Purchase + Conformité |
| **Niveau 3** | Stratégie énergétique mature | Multi-outils | Cockpit intégré |

#### Segments verticaux prioritaires

1. **Retail / Distribution** : multi-sites homogènes, forte sensibilité coût, conformité tertiaire
2. **Santé / EHPAD** : obligations réglementaires fortes, budgets contraints
3. **Logistique / Entrepôts** : gros consommateurs, potentiel flexibilité (froid, IRVE)
4. **Tertiaire / Bureaux** : décret tertiaire, BACS, OPERAT
5. **Industrie légère** : multi-sites, sensibilité prix, potentiel achat structuré

### 8.2 Canal de distribution

| Canal | Description | Coût d'acquisition | Priorité |
|---|---|---|---|
| **Vente directe** | Prospection, démos, pilotes | Moyen | Phase 1 |
| **Courtiers partenaires** | Opéra, Selectra → recommandation PROMEOS | Faible | Phase 1-2 |
| **Fournisseurs alternatifs** | Bundling avec offre de fourniture | Faible | Phase 2 |
| **Intégrateurs IT** | ESN, cabinets conseil énergie | Moyen | Phase 2-3 |
| **Marketplace** | App stores fournisseurs, places de marché B2B | Variable | Phase 3 |
| **Inbound / Content** | Blog, webinaires, livres blancs | Faible | Continu |

### 8.3 Partenariats stratégiques

**Partenariats prioritaires** :

| Partenaire | Type | Valeur pour PROMEOS | Valeur pour le partenaire |
|---|---|---|---|
| **Courtier énergie** (Opéra, Enoptea) | Canal + données | Acquisition client, accès marché | Outil de pilotage pour ses clients, fidélisation |
| **Fournisseur alternatif** | Canal + intégration | Volume, données contrats | Service à valeur ajoutée, réduction churn |
| **EMS technique** (Ubigreen, Advizeo) | Intégration technique | Données IoT, sous-comptage | Couche intelligence financière |
| **Cabinet conseil énergie** | Canal + expertise | Acquisition, crédibilité sectorielle | Outil logiciel pour ses missions |
| **Expert-comptable / DAF externalisé** | Canal | Accès aux PME multi-sites | Module de suivi des coûts énergie |
| **Agrégateur flexibilité** | Référencement | Offre de valorisation pour les clients | Qualification de leads, données consommation |

---

## 9. Roadmap produit

**État actuel (avril 2026)** : V109 terminé (docker-compose, guide admin, monitoring, loadtest, feedback widget). Sprints V93-V109 complétés couvrant billing, market, actions, flex, tertiaire, notifications, cockpit, QA, E2E, CI. La plateforme dispose d'une base fonctionnelle solide avec 5 endpoints OpenAPI documentés, tests E2E Playwright, CI GitHub Actions, et un mode démo complet avec seed data enrichie (3 sites, pack Helios).

### Phase 1 : Fondation (V93-V109) — ✅ Complété

| Sprint | Thème | Livrable clé |
|---|---|---|
| V93-V98 | Modules métier | Billing, Market, Actions, Flex, Tertiaire, Notifications |
| V99 | Radar contrats | Contract Renewal Radar + Purchase Scenarios |
| V100 | Segmentation | Segmentation Linked Patrimoine |
| V101 | Sprint P0 métier | Achat auditable, conformité, billing prorata, seed data |
| V102 | Cockpit & Cohérence | Compliance history, risque canonique, trace achat, insight→action→ROI |
| V103 | Cockpit exception | Pondération surface, snapshot auto, scoring inline, KPI contrat, PDF export |
| V104 | Vérité Visible | Export canonique, pondération explicable, priorités achat, QA baseline |
| V105 | QA Deep | 234→182 fails, smoke tests, PDF iframe, parity fixture |
| V106 | Robustesse | 182→31 fails, jsPDF natif, E2E journey 8 tests, fixture canonique |
| V107 | Release Readiness | 31→0 fails frontend, Playwright E2E, fixture enrichie 3 sites, PDF durci |
| V108 | Démo Pilote | Scripts demo, CI GitHub Actions, guide cockpit, pitch data, perf audit |
| V109 | Pilote Contrôlé | Docker-compose, guide admin, monitoring light, loadtest, feedback widget |

### Phase 2 : Shadow Billing MVP (V110-V115) — En cours

| Sprint | Thème | Livrable cible |
|---|---|---|
| V110+ | Cockpit World-Class | Rapprochement maquettes cibles, UX premium |
| V111 | Shadow Billing V1 | Recalcul facture théorique élec HTA/BT, TURPE 7 |
| V112 | Détection anomalies | Écarts facture réelle vs théorique, classification |
| V113 | Actions & ROI | Action correctrice par anomalie, estimation ROI |
| V114 | Connecteur Enedis | API SGE, import courbes de charge, automatisation |
| V115 | Dashboard DAF | Vue consolidée dépenses, écarts, top anomalies, projection |

### Phase 3 : Purchase Strategy (V116-V120)

| Sprint | Thème | Livrable cible |
|---|---|---|
| V116 | Modèle contrats | Data model 30+ entités, composantes contractuelles |
| V117 | Exposition portefeuille | Visualisation couvert/ouvert/à renouveler |
| V118 | Scénarios d'achat | Simulation fixe/indexé/VNU/CPPA, impact budget |
| V119 | Radar renouvellement | Alertes anticipées, fenêtres d'achat optimales |
| V120 | Budget prévisionnel | Projection 12-36 mois, scénarios de marché |

### Phase 4 : Conformité & Performance (V121-V126)

| Sprint | Thème | Livrable cible |
|---|---|---|
| V121 | OPERAT avancé | Export structuré, trajectoire, année de référence |
| V122 | BACS | Suivi équipement, conformité, inspections |
| V123 | Audit trail | Preuve-ready, responsabilités, historique complet |
| V124 | Performance avancée | Benchmark inter-sites, DJU, profils de charge |
| V125 | Puissance souscrite | Analyse et recommandation optimisation TURPE |
| V126 | Alertes intelligentes | Dérives consommation, anomalies automatiques |

### Phase 5 : Flexibilité & Partenaires (V127-V132)

| Sprint | Thème | Livrable cible |
|---|---|---|
| V127 | Diagnostic flex | Identification actifs pilotables, potentiel |
| V128 | Simulation revenus | Estimation FCR, capacité, NEBEF, arbitrage |
| V129 | Orientation agrégateur | Matching client-agrégateur, référencement |
| V130 | CPPA cockpit | Simulation CPPA, comparaison alternatives, GO |
| V131 | API partenaires | Connecteurs agrégateurs, courtiers, EMS |
| V132 | Marketplace V1 | Référencement partenaires, commissions |

### Phase 6 : Scale & Enterprise (V133+)

| Sprint | Thème | Livrable cible |
|---|---|---|
| V133 | Multi-tenant | Architecture SaaS multi-clients, isolation données |
| V134 | API publique | Endpoints REST documentés, rate limiting, SDK |
| V135 | SSO / SAML | Intégration annuaires d'entreprise |
| V136 | Gaz naturel V2 | Couverture complète gaz (ATRT, TTS, TICGN) |
| V137 | IA / ML | Prédiction consommation, recommandations automatiques |
| V138 | International V1 | Première extension (Belgique, Luxembourg) |

---

## 10. Risques et mitigations

### Matrice des risques

| # | Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Adoption lente** : les entreprises sont conservatrices et changent d'outil rarement | Élevée | Élevé | Pilotes gratuits, ROI démontré en < 30 jours, wedge « facture » (pain immédiat), onboarding assisté |
| R2 | **Concurrence des fournisseurs** : EDF/ENGIE développent leurs propres outils de pilotage | Moyenne | Élevé | Différenciation par la neutralité (multi-fournisseurs), profondeur fonctionnelle (5 piliers), agilité d'exécution |
| R3 | **Concurrence EMS** : Ubigreen/Deepki ajoutent des modules facture/achat | Moyenne | Moyen | Avance sur le shadow billing France, expertise réglementaire native, focus financier vs technique |
| R4 | **Évolution réglementaire** : changements de tarifs, nouvelles obligations, modifications du TURPE | Certaine | Moyen | Architecture modulaire (tarifs_reglementaires.yaml versionné), veille réglementaire continue (agent SENTINEL-REG), mises à jour rapides |
| R5 | **Accès aux données** : restrictions API Enedis/GRDF, consentement client | Moyenne | Élevé | Multi-source (API + import CSV + connecteurs), accompagnement client pour les mandats, stockage local des données |
| R6 | **Scalabilité technique** : passage de SQLite POC à PostgreSQL production, montée en charge | Faible | Moyen | Architecture modulaire FastAPI, migration planifiée, loadtests dès V109, docker-compose prêt |
| R7 | **Risque commercial** : cycle de vente B2B long (6-12 mois grands comptes) | Élevée | Moyen | Cible PME/ETI (cycle court), pilotes rapides, pricing flexible, partenariats courtiers (vente indirecte) |
| R8 | **Qualité des données** : données de consommation incomplètes, factures mal structurées | Élevée | Moyen | Contrôle de cohérence automatique, enrichissement progressif, tolérance aux données manquantes |
| R9 | **Bus factor technique** : dépendance à un seul développeur principal | Élevée | Critique | Documentation exhaustive (320+ fichiers .md), architecture modulaire et lisible, CI/CD automatisé (GitHub Actions), tests complets (E2E Playwright + unitaires), docker-compose pour reproductibilité |
| R10 | **Coût maintenance réglementaire** : chaque changement de taux = mise à jour code | Certaine | Moyen | Fichier tarifs_reglementaires.yaml versionné et centralisé, agent SENTINEL-REG de veille automatisée, architecture séparant données réglementaires du code métier, alertes proactives sur les changements |
| R11 | **Sécurité des données** : données sensibles (factures, consommation, contrats) | Faible | Critique | Chiffrement, authentification JWT, rôles granulaires, audit trail, conformité RGPD, hébergement France |
| R12 | **Financement** : besoin de trésorerie pour atteindre le seuil de rentabilité | Moyenne | Élevé | Bootstrap initial (coûts contenus), SaaS = revenus récurrents, recherche de financement dès atteinte PMF |

### Matrice probabilité × impact

```
Impact →    Faible       Moyen        Élevé        Critique
            ─────────────────────────────────────────────
Certaine  │            │ R4, R10    │            │           │
Élevée    │            │ R7, R8     │ R1         │ R9        │
Moyenne   │            │ R3         │ R2, R5, R12│           │
Faible    │            │ R6         │            │ R11       │
```

---

## 11. Métriques de succès

### KPIs produit

| Métrique | Définition | Cible M6 | Cible M12 | Cible M24 |
|---|---|---|---|---|
| **Clients actifs** | Nombre de comptes payants | 5-10 | 20-40 | 80-150 |
| **Sites gérés** | Nombre total de sites dans la plateforme | 100-500 | 1 000-5 000 | 10 000+ |
| **ARR** | Annual Recurring Revenue | 75-150 K€ | 500 K€ - 1 M€ | 2-5 M€ |
| **NPS** | Net Promoter Score | > 30 | > 40 | > 50 |
| **DAU/MAU** | Ratio d'engagement quotidien | > 30% | > 35% | > 40% |
| **Time to value** | Temps entre onboarding et première valeur | < 48h | < 24h | < 4h |

### KPIs financiers

| Métrique | Définition | Cible An 1 | Cible An 3 |
|---|---|---|---|
| **MRR** | Monthly Recurring Revenue | 40-80 K€ | 200-400 K€ |
| **Burn rate** | Dépenses mensuelles nettes | < 30 K€ | < 100 K€ |
| **Runway** | Mois de trésorerie restants | > 18 mois | > 24 mois |
| **Marge brute** | (Revenus - COGS) / Revenus | > 70% | > 80% |
| **CAC payback** | Mois pour récupérer le CAC | < 8 mois | < 3 mois |
| **NDR** | Net Dollar Retention | > 110% | > 120% |

### KPIs impact client

| Métrique | Définition | Cible |
|---|---|---|
| **Anomalies détectées** | Nombre d'erreurs de facturation identifiées par client/an | 5-20 |
| **Économies générées** | Montant € économisé grâce à PROMEOS par client/an | 10-50 K€ |
| **Temps gagné** | Heures économisées sur la gestion énergie par mois | 20-40h |
| **Conformité** | % de sites conformes OPERAT/BACS | > 95% |
| **Couverture achat** | % du portefeuille couvert avec stratégie documentée | > 80% |

---

## 12. Gouvernance et organisation

### Organisation cible

```
┌─────────────────────────────────────────┐
│              CEO / Fondateur             │
│         Vision, Stratégie, GTM          │
├──────────┬──────────┬───────────────────┤
│          │          │                   │
│  CTO     │  CPO     │  COO / Sales      │
│  Tech    │  Product │  Opérations       │
│          │          │  Commercial       │
├──────────┼──────────┼───────────────────┤
│ Dev      │ Design   │ Customer Success  │
│ Backend  │ UX/UI    │ Support           │
│ Frontend │ Research │ Partenariats      │
│ DevOps   │ Data     │ Marketing         │
└──────────┴──────────┴───────────────────┘
```

### Équipe phase 1 (bootstrap)

| Rôle | Profil | Priorité |
|---|---|---|
| **Fondateur / CEO** | Vision produit, développement commercial, expertise énergie | En place |
| **Lead Developer** | Fullstack (Python/React), architecture, CI/CD | En place |
| **Expert Énergie / Réglementaire** | Connaissance marché, tarifs, réglementation France | À recruter |
| **Customer Success** | Onboarding, support, feedback client | À recruter (M6) |
| **Commercial B2B** | Prospection ETI/PME multi-sites | À recruter (M6-M12) |

### Principes de gouvernance

1. **Documentation-first** : toute décision, architecture et fonctionnalité est documentée (320+ fichiers .md, ADR, specs, audits)
2. **Feedback-driven** : widget de feedback intégré, boucle courte avec les pilotes
3. **Quality gates** : pre-merge checklist (code-review + simplify), tests automatisés, E2E Playwright
4. **Transparence** : backlog public, roadmap partagée avec les clients pilotes
5. **Agilité** : sprints courts (V93-V109 = 17 sprints en quelques mois), livraison continue

---

## 13. Annexes et sources

### Sources primaires

| Source | Référence | Date | Utilisation |
|---|---|---|---|
| CRE | Observatoire des marchés de détail T4 2025 | Mars 2026 | Données marché (sections 2, 3) |
| CRE | Bulletin des marchés de gros T4 2025 | Mars 2026 | Volumes, liquidité (section 2.1) |
| CRE | Délibération n°2025-78 (TURPE 7) | 2025 | Tarifs acheminement (section 2.1) |
| CRE | Délibération n°2026-33 | 2026 | Régulation marché |
| ADEME | Base Empreinte V23.6 | 2023 | Facteurs d'émission CO₂ |
| ADEME | Plateforme OPERAT | En continu | Décret tertiaire |
| RTE | Bilan prévisionnel 2023, Futurs énergétiques 2050 | 2023-2024 | Trajectoires consommation |
| Gouvernement | PPE3 (2026-2035) | 2025 | Objectifs mix énergétique (section 2.1) |
| Gouvernement | Décret n°2019-771 (décret tertiaire) | 2019 | Obligations tertiaire |
| Gouvernement | Loi n°2025-391 (DDADUE — audit énergétique/SMÉ) | 2025 | Obligations audit >2.75 GWh (11/10/2026) et SMÉ >23.6 GWh (11/10/2027) |
| RTE/Enedis | RM-5-NEBCO-V01 | 2024 | Règles marché NEBEF |

### Études sectorielles

| Source | Titre | Date | Utilisation |
|---|---|---|---|
| Les Echos Études | Marché de l'électricité en France | Décembre 2024 | Prix B2B, concurrence, ARENH (section 2.1) |
| Les Echos Études | Stockage d'électricité | Novembre 2023 | Batteries, flexibilité (section 2.3) |
| Les Echos Études | Photovoltaïque | Mai 2024 | PV, autoconsommation, CPPA (sections 2.3, 3.7) |
| Opéra Énergie | Baromètre prix énergie B2B | 2024 | Prix B2B, évolutions (section 2.1) |

### Données internes PROMEOS

| Document | Localisation | Contenu |
|---|---|---|
| Maquettes cockpit cible | `memory/maquettes_cockpit_cible.md` | UX cible des dashboards |
| Competitive Intelligence | `memory/reference_competitive_intelligence_2026.md` | Benchmark 25 acteurs |
| Modèle contrats | `memory/project_modele_contrats_roadmap.md` | Blueprint data model 30+ entités |
| Business cases flexibilité | `memory/reference_business_cases_flexibilite.md` | 10 verticals |
| Stratégie produit flexibilité | `memory/project_flexibilite_strategie_produit.md` | Architecture 5 briques |
| Corrélations analytics | `memory/project_correlations_analytics.md` | 6 modules analytiques |
| Veille réglementaire | `memory/reference_veille_reglementaire_2025_2026.md` | 12 mécanismes cartographiés |
| Marché B2B fourniture | `memory/reference_marche_b2b_fourniture.md` | Taxonomie contrats |

### Sources enrichies

- **Les Echos Études (décembre 2024)** — Marché de l'électricité en France : prix, tarifs, concurrence, réglementation, ARENH, CPPA, CEE
- **Les Echos Études (novembre 2023)** — Stockage d'électricité : marché batteries stationnaires, drivers, modèles d'affaires, coûts, agrégateurs
- **Les Echos Études (mai 2024)** — Photovoltaïque : installations, autoconsommation, prix panneaux, PPA, obligations solarisation
- **CRE Observatoire T4 2025** — Marchés de détail électricité et gaz naturel au 31/12/2025
- **ADEME Base Empreinte V23.6** — Facteurs d'émission pour le calcul des impacts carbone
- **Décret n°2019-771** — Décret tertiaire (obligations de réduction de consommation)
- **Loi n°2025-391** — Loi DDADUE : audit énergétique obligatoire (>2.75 GWh, 11/10/2026) et SMÉ (>23.6 GWh, 11/10/2027)
- **RM-5-NEBCO-V01** — Règles du mécanisme NEBEF (Notification d'Échange de Bloc d'Effacement)
- **CRE délibération n°2026-33** — Régulation des marchés de l'énergie

### Glossaire

| Terme | Définition |
|---|---|
| ARENH | Accès Régulé à l'Électricité Nucléaire Historique — dispositif (2011-2025) permettant l'achat d'électricité nucléaire à prix régulé |
| ATRD | Accès des Tiers au Réseau de Distribution — tarif d'utilisation du réseau gaz distribution |
| ATRT | Accès des Tiers au Réseau de Transport — tarif d'utilisation du réseau gaz transport |
| BACS | Building Automation and Control Systems — obligation d'automatisation des bâtiments tertiaires |
| CAPN | Contrats d'Allocation de Production Nucléaire — contrats long terme post-ARENH pour électro-intensifs |
| CDE | Courbe De charge — profil de consommation électrique à pas fin (10 min, 30 min, 1h) |
| CEE | Certificats d'Économies d'Énergie — mécanisme d'obligation de réalisation d'économies d'énergie |
| CPPA | Corporate Power Purchase Agreement — contrat d'achat direct d'électricité renouvelable |
| CRE | Commission de Régulation de l'Énergie — autorité de régulation indépendante |
| CSRD | Corporate Sustainability Reporting Directive — directive européenne de reporting extra-financier |
| CTA | Contribution Tarifaire d'Acheminement — taxe finançant les retraites des agents IEG |
| DJU | Degrés-Jours Unifiés — indicateur de rigueur climatique pour normaliser les consommations |
| ELD | Entreprise Locale de Distribution — distributeur d'énergie local (hors Enedis/GRDF) |
| EMS | Energy Management System — système de management de l'énergie |
| EPR | European Pressurized Reactor — réacteur nucléaire de nouvelle génération |
| FCR | Frequency Containment Reserve — réserve primaire de fréquence |
| aFRR | Automatic Frequency Restoration Reserve — réserve secondaire automatique de fréquence |
| GO | Garantie d'Origine — certificat attestant l'origine renouvelable de l'électricité |
| GRD | Gestionnaire de Réseau de Distribution (Enedis, GRDF) |
| GRT | Gestionnaire de Réseau de Transport (RTE, GRTgaz) |
| GTB/GTC | Gestion Technique du Bâtiment / Gestion Technique Centralisée |
| HP/HC | Heures Pleines / Heures Creuses — plages horaires tarifaires |
| IRVE | Infrastructure de Recharge pour Véhicules Électriques |
| LCOE | Levelized Cost of Energy — coût actualisé de l'énergie |
| MÉCAPA | Mécanisme de Capacité — obligation pour les fournisseurs de garantir la sécurité d'approvisionnement |
| NEBEF | Notification d'Échange de Bloc d'Effacement — valorisation de la flexibilité sur le marché spot |
| OPERAT | Observatoire de la Performance Énergétique, de la Rénovation et des Actions du Tertiaire — plateforme ADEME |
| PPE | Programmation Pluriannuelle de l'Énergie — feuille de route énergie de la France |
| PRVG | Prix Repère Vente de Gaz — prix de référence gaz naturel (remplace les TRV gaz) |
| PV | Photovoltaïque |
| SGE | Système de Gestion des Échanges — plateforme de données Enedis |
| TICGN | Taxe Intérieure de Consommation sur le Gaz Naturel |
| TRVE | Tarifs Réglementés de Vente d'Électricité — tarifs fixés par les pouvoirs publics |
| TURPE | Tarif d'Utilisation des Réseaux Publics d'Électricité — tarif d'acheminement |
| VNU | Vente au Nucléaire Universel — mécanisme post-ARENH de redistribution de la rente nucléaire |

---

> **Document vivant** — Ce document est mis à jour à chaque sprint majeur et à chaque évolution significative du marché ou de la réglementation. Dernière mise à jour : 06/04/2026.
>
> **Confidentialité** — Document interne PROMEOS. Ne pas diffuser sans autorisation.
