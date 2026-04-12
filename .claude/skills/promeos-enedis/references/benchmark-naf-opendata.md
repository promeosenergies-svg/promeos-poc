# Benchmark NAF via Open Data Enedis -- Guide d'exploitation

Sources : Doctrine CDC PROMEOS Parties 1.2+4+6.8 + Doctrine experte Parties 4+6

## Pourquoi c'est critique

Les agregats >36 kVA (`conso-sup36`) sont la **seule source publique** croisant forme de courbe de charge x secteur d'activite (NAF) x plage de puissance. C'est la base du benchmark sectoriel PROMEOS pour les sites B2B >36 kVA -- la cible principale du produit.

## Datasets Open Data a integrer

### 1. Agregats >36 kVA (PRIORITE 1)

- **URL** : `data.enedis.fr/explore/dataset/conso-sup36/`
- **Acces** : Public, libre, API ODS
- **Mise a jour** : Trimestrielle (30 jours apres fin de trimestre)
- **Format** : CSV, API REST ODS

**Schema :**

| Champ | Type | Description |
|---|---|---|
| horodate | datetime (30 min) | Horodatage du pas |
| profil | string | Code profil Enedis (ENT1, ENT2...) |
| plage_puissance_souscrite | string | Plage (ex: "36-72 kVA", "72-144 kVA") |
| secteur_activite | string | Secteur derive du code NAF |
| nb_points_soutirage | int | Nombre de PRM dans l'agregat |
| total_energie_soutiree_wh | float | Energie totale soutiree (Wh) |
| courbe_moyenne_w | float | Puissance moyenne par point (W) |

**Secteurs d'activite disponibles** (derives NAF) :
Industrie, Agriculture, Tertiaire, Commerce, Residentiel collectif, Enseignement, Sante, Administration, etc.

**Metriques derivables** :
- Courbe de charge moyenne par profil x puissance x NAF
- Facteur de charge par segment sectoriel
- Saisonnalite par type d'activite
- Ratio jour/nuit, semaine/week-end par secteur
- Thermosensibilite sectorielle (croisement avec meteo)

**PRECAUTION** : Le `nb_points_soutirage` varie (deploiement progressif compteurs communicants). Une hausse apparente peut refleter l'inclusion de nouveaux compteurs, pas une hausse reelle de consommation.

### 2. Agregats <=36 kVA

- **URL** : `data.enedis.fr/explore/dataset/conso-inf36/`
- **Schema** : Identique SAUF pas de dimension NAF (limite structurelle)
- **Usage** : Benchmark C5 petit tertiaire (profil x puissance uniquement)

### 3. Coefficients des profils reglementaires

- **URL** : `opendata.enedis.fr/datasets/coefficients-des-profils/`
- **Mise a jour** : Hebdomadaire
- **Historique** : 5 ans max

**Profils disponibles** :

| Code | Description | Thermosensibilite |
|---|---|---|
| RES1 | Residentiel sans CE | Faible |
| RES2 | Residentiel avec CE | Tres forte |
| PRO1 | Pro standard | Faible-moyenne |
| PRO2 | Pro avec CE | Forte |
| PRO5 | Eclairage public | Anti-solaire |
| ENT1 | Entreprise C4 | Variable |
| ENT2+ | Entreprise C2-C3 | Variable |
| PRD1-4 | Production (PRD3=PV) | Solaire |

**Versions** :
- **Statiques** : coefficients moyens a temperature de reference
- **Dynamiques** : adaptes temps reel via panel mesure (depuis 2018)
- **Indices de confiance** (0-100) : INDIC_DISPERS_POIDS_DYN + INDIC_REPRESENT_PANEL_DYN

### 4. Bilan electrique 15 minutes

- **URL** : `data.enedis.fr/explore/dataset/bilan-electrique/`
- **Variables** : Soutirage RTE, consommation HTA (C1+C2+C3), C4 BT>36, C5 BT<=36, production, temperature
- **Usage** : Contextualisation portefeuille vs. reseau national
- **Mise a jour** : bimensuelle (estimation puis consolide)
- **Historique** : ~10 ans

### 5. Agregats production PV (maille nationale)

- **URL** : `opendata.enedis.fr` (Article 23 decret 2017-486)
- **Acces** : Public
- **Granularite** : 30 min, nationale
- **Mise a jour** : Trimestrielle

**Schema :**

| Champ | Type | Description |
|---|---|---|
| horodate | datetime (30 min) | Horodatage du pas |
| plage_puissance_injection | string | Classe de puissance (ex: 9-36 kW) |
| filiere | string | PV, eolien, hydro, cogeneration, bioenergies |
| nb_producteurs | int | Nombre de producteurs dans l'agregat |
| energie_injectee_wh | float | Energie injectee (Wh) |
| puissance_moyenne_w | float | Puissance moyenne des producteurs communicants (W) |

**Usage PROMEOS** :
- Suivi injection PV moyenne par classe de puissance
- Estimation taux couverture PV vs charge (croisement avec agregats conso)
- Dimensionnement potentiel PV par analogie
- **Attention** : donnees dependantes meteo, croiser avec irradiation (Open-Meteo) pour toute modelisation

### 6. Simulateur de courbes de charge IA (Enedis Open Services)

- **URL** : openservices.enedis.fr (login requis)
- **Acces** : Public experimental
- **Type** : Service web generant des courbes synthetiques realistes a la demande
- **Granularite** : 30 min
- **Usage** : Prototypage d'analyses sur jeux non confidentiels, generation on-demand pour etudes de cas
- **Limites** : Courbes generees (pas de donnees brutes), non contractuelles, non tracables
- **REGLE** : meme precautions que courbes fictives -- JAMAIS pour benchmark ou diagnostic reel

### 7. Observatoire de la transition ecologique

- **URL** : `observatoire.enedis.fr`
- **Acces** : Public
- **Type** : Datavisualisations thematiques (transition energetique, mobilite electrique, EnR)
- **Usage** : Enrichissement contextuel, croisements donnees Enedis + externes

## Architecture backend recommandee

### Service `enedis_benchmarks.py`

```python
# Responsabilites :
# 1. Import periodique des 4 datasets (cron trimestriel)
# 2. Stockage en table dediee (benchmark_enedis_opendata)
# 3. API de comparaison site vs. benchmark NAF
# 4. Calcul du score d'atypie

# Table benchmark_enedis_opendata :
# id, horodate (UTC), profil, plage_puissance, secteur_activite,
# nb_points, total_energie_wh, courbe_moyenne_w, dataset_source,
# trimestre_import

# Endpoints :
# GET /api/benchmarks/naf/{naf_code}?puissance={kva}&periode={...}
#   -> courbe moyenne 30min du segment, metriques derivees
# GET /api/benchmarks/compare/{site_id}
#   -> score d'atypie, ecarts par indicateur, radar chart data
```

### Score d'atypie

```python
# Score normalise 0-100 :
S_atypie = RMSE(CdC_site_normalisee, CdC_benchmark_NAF_normalisee) / sigma_segment * 100

# Normalisation : diviser par P_moy pour comparer les formes, pas les volumes
# sigma_segment : ecart-type intra-segment (a calculer depuis les agregats)

# Interpretation :
# 0-20  : Typique du secteur
# 20-50 : Ecart modere (verifier usages specifiques)
# 50-80 : Atypique (diagnostic recommande)
# 80+   : Tres atypique (anomalie probable ou activite mixte)
```

### Benchmark par indicateur

| Indicateur | Calcul sur agregat | Comparaison site |
|---|---|---|
| Facteur de charge | P_moy_agregat / P_max_agregat | LF_site vs LF_segment |
| Ratio nuit/jour | E_nuit_agregat / E_jour_agregat | R_nj_site vs R_nj_segment |
| Ratio semaine/WE | E_WE_agregat_norm / E_sem_agregat_norm | R_sw_site vs R_sw_segment |
| Baseload relatif | P_5_agregat / P_moy_agregat | Baseload_site vs benchmark |
| Saisonnalite | Variance inter-mensuelle normalisee | Comparaison thermosensibilite |

## Mapping NAF -> Secteur Enedis

PROMEOS dispose de 15 archetypes NAF (732 codes). Le mapping vers les secteurs Enedis Open Data doit etre explicite :

```python
# Mapping a construire et maintenir dans config/
# archetype_promeos -> secteur_enedis_opendata
# ex: "bureau" -> "Tertiaire"
# ex: "commerce_alimentaire" -> "Commerce"
# ex: "hopital" -> "Sante"
# Attention : le mapping n'est pas 1:1, certains archetypes
# PROMEOS sont plus fins que les secteurs Enedis
```

## Dataset 5 : Thermosensibilite par secteur et NAF

- **URL** : `opendata.enedis.fr/datasets/consommation-electrique-par-secteur-dactivite-departement`
- **Acces** : Public
- **Granularite** : Annuelle x Departement x Secteur/NAF
- **Historique** : 2011-2024

**Schema :**

| Champ | Type | Description |
|---|---|---|
| annee | int | Annee (2011-2024) |
| departement | string | Code departement |
| secteur | string | Residentiel / Tertiaire / Industrie / Agriculture |
| code_naf | string | Code NAF 4-5 positions (si entreprises) |
| consommation_totale | float (MWh) | Conso annuelle agregee |
| nombre_sites | int | Nombre sites dans agregat (si >= 10) |
| part_thermosensible | float (%) | Part conso liee usages thermosensibles |
| gradient_thermosensibilite | float (MWh/C) | Surconsommation par degre sous seuil |

**Exploitation** :
- Benchmark : comparer conso entreprise vs moyenne NAF departement
- Scoring : conso/m2 > P75 NAF = opportunite economies
- Gradient eleve (> 100 kWh/C pour tertiaire) = forte dependance chauffage elec = potentiel isolation/PAC

**Limites** : Granularite annuelle uniquement (pas de courbe horaire), agregation departement masque disparites locales.

## Secret statistique -- regles de publication

Les agregats Open Data ne sont publies que si :

- **Residentiel** : nombre sites >= 10
- **Professionnel** : nombre sites >= 10 OU consommation > 50 MWh

En dessous : valeur masquee. Consequences :
- Trous dans datasets a maille fine (IRIS, commune, petit NAF)
- Biais de selection : seuls les segments suffisamment peuples sont visibles
- Pour benchmark PROMEOS : toujours verifier `nb_points > 0` avant comparaison

## Regles non-negociables

1. **Toujours normaliser** avant comparaison (par P_moy ou par surface, jamais en valeurs brutes)
2. **Afficher le nb_points** de l'agregat -- un benchmark sur 5 PRM n'a pas la meme valeur qu'un sur 5000
3. **Disclaimer obligatoire** : "Comparaison basee sur la moyenne du segment [X] Enedis ([N] points). Les ecarts individuels sont typiquement de 20-40%"
4. **Ne JAMAIS comparer** un hopital 24/7 avec un cabinet medical sous le meme NAF
5. **Mettre a jour trimestriellement** -- les agregats evoluent avec le deploiement des compteurs communicants
6. **Secret statistique** : verifier que l'agregat respecte le seuil (>= 10 sites ou > 50 MWh). Sinon donnee non disponible
7. **Biais NAF** : variabilite enorme au sein d'un meme code (boulangerie artisanale vs industrielle). Afficher l'ecart-type ou la distribution, pas seulement la moyenne
