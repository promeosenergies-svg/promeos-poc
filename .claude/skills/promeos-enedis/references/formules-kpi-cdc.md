# Formules & KPI Courbes de Charge -- Reference Claude Code

Sources : Doctrine CDC PROMEOS Parties 6-7-12 + Doctrine experte exploitation CDC Parties 6-7

## Indicateurs fondamentaux

```python
# Energie sur un pas (Wh)
E_pas_wh = P_moyenne_W * dt_heures  # dt=0.5 pour 30min, dt=1/6 pour 10min

# Puissance moyenne sur une periode (kW)
P_moy_kw = sum(E_pas_kwh) / duree_periode_h

# Puissance appelee maximale (kW)
P_max = max(P_pas)

# Percentiles de charge (kW)
P_95 = np.percentile(P_pas, 95)  # pointe representative
P_5  = np.percentile(P_pas, 5)   # baseload representatif

# Duree d'utilisation a pleine puissance (h/an)
H_util = E_annuelle_kwh / P_souscrite_kw

# Facteur de charge (sans unite, 0-1)
LF = P_moy / P_max

# Ratio base/pointe (sans unite)
R_bp = P_5 / P_95

# Ratio nuit/jour (sans unite)
R_nj = sum(E_22h_6h) / sum(E_6h_22h)

# Ratio semaine/week-end (normalise)
R_sw = (sum(E_WE) / 2) / (sum(E_sem) / 5)

# Coefficient de simultaneite (multi-sites)
K_simul = P_max_agregee / sum(P_max_individuelles)

# Intensite des pics (sans unite)
I_pic = (P_max - P_moy) / P_moy

# Variabilite intra-journaliere
V_intra = std(P_horaire_jour_type) / mean(P_horaire_jour_type)

# Variabilite inter-journaliere
V_inter = std(E_journaliere) / mean(E_journaliere)
```

## Baseload (talon de consommation)

```python
# Definition : puissance minimale appelee en permanence
# Calcul recommande :
baseload = np.percentile(P_nuit_weekend_ferie, 5)
# Alternative : moyenne 2h-5h du matin, jours WE hors vacances

# Interpretation :
# baseload/P_moy > 0.6 -> fort potentiel economie hors occupation
# C'est le PREMIER indicateur de gaspillage a montrer dans PROMEOS
```

## Thermosensibilite -- Signature energetique

```python
# Modele fondamental (regression lineaire)
# E_jour = a * DJU_jour + b
# a (kWh/DJU) = coefficient de thermosensibilite (pente)
# b (kWh/jour) = consommation independante de la temperature (baseload)
# DJU base 18C, methode COSTIC pour PROMEOS

# Modele 3P (3 parametres) :
# E = b                       si T > T_break
# E = a * (T_break - T) + b  si T < T_break

# Modele 4P : ajoute pente climatisation (sites climatises)
# Modele 5P : ajoute zone morte (plage sans dependance)

# Part thermosensible (%)
part_thermo = (E_totale - b * N_jours) / E_totale * 100

# Consommation specifique normalisee DJU (kWhEF/m2/an)
conso_spec_norm = (E_annuelle / DJU_reel) * DJU_reference / surface

# PIEGE : site chauffe au gaz -> CdC electrique non thermosensible
# mais le site EST thermosensible (le gaz compense)
```

## Scores composites PROMEOS

```python
# Score de gaspillage potentiel (0-100)
S_gaspillage = w1*(R_nj/R_nj_ref_NAF) + w2*(R_sw/R_sw_ref_NAF) + w3*(baseload/P_moy)
# 100 = fort potentiel de gaspillage

# Score d'atypie (0-100)
S_atypie = RMSE(CdC_site_norm, CdC_benchmark_NAF_norm) / sigma_segment * 100

# Score de flexibilite (0-100)
S_flex = f(LF, V_intra, part_deplacable, reactivite_CVC)

# Score de sensibilite tarifaire (0-100)
S_tarif = f(part_HP, depassements, cos_phi, structure_puissance)

# Score de pertinence PV (0-100)
S_PV = f(taux_recouvrement_conso_prod, surface_toiture, orientation)

# Score de pertinence stockage (0-100)
S_stock = f(delta_HP_HC, pics_courts, arbitrage_spot)
```

## Autoconsommation

```python
# Taux d'autoconsommation (%)
TAC = sum(min(P_conso, P_prod) * dt) / sum(P_prod * dt) * 100

# Taux d'autoproduction (%)
TAP = sum(min(P_conso, P_prod) * dt) / sum(P_conso * dt) * 100

# Surplus injectable (kWh)
surplus = sum(max(0, P_prod - P_conso) * dt)
```

## Puissance reactive et tan phi

```python
# Pour C2-C4 avec acces courbes reactives
tan_phi = Q / P  # reactive / active

# Si tan_phi > 0.4 : penalites TURPE reactive excedentaire
# Analyser la courbe de tan_phi par heure pour dimensionner compensation
```

## CMDPS (depassements)

```python
# Composante de depassement de puissance souscrite
# Calcul sur Pmax 10 min (C4/HTA)
CMDPS = 12.65 * sum(max(0, P_10min - P_souscrite))  # en euros
```

## Arrondi Linky -- precision critique

```python
# Les compteurs Linky transmettent les puissances ARRONDIES A L'ENTIER (kW)
# Sur pas 30 min : perte de 0.5 kWh par arrondi
# Sur 1 an : erreur cumulee de quelques kWh/jour (significatif pour petits consommateurs)
# REGLE : traiter les donnees Linky comme int, considerer incertitude +/- 0.5 kW
# Pour comparaisons fines, privilegier les index (non arrondis) sur les courbes
```

## Optimisation puissance souscrite

```python
# Objectif : trouver P_souscrite minimale evitant les penalites CMDPS
# Methode : simulation iterative sur historique 12 mois

# Pour chaque palier P_test :
#   depassements = sum(max(0, P_10min - P_test)) pour tous les pas
#   cout_cmdps = 12.65 * depassements  # euros
#   cout_abonnement = f(P_test)  # grille TURPE
#   cout_total = cout_abonnement + cout_cmdps
# P_optimal = argmin(cout_total)

# Indicateur : surcout actuel = cout_total(P_actuelle) - cout_total(P_optimal)
# Attention : prendre en compte previsions futures (croissance charge, meteo)
# et duree engagement contractuel

# Courbe de duree de charge (monotone) :
# Tri decroissant des puissances sur 1 an
# Visualise la repartition temporelle de la puissance appelee
# Croisement monotone x paliers tarifaires = seuil optimal P_souscrite
```

## Shadow billing -- simulation de factures

```python
# Reconstitution de facture theorique a partir de la courbe + tarifs
# Facture_contrat_X = Abonnement + sum(P(t) * dt * tarif(t)) pour chaque pas t

# Etapes :
# 1. Mapper chaque pas a sa classe tarifaire (HP, HC, Pointe, etc.)
# 2. Appliquer le prix unitaire (c€/kWh) de chaque classe
# 3. Calculer composante puissance (P_souscrite * prix_kW_annuel / 12)
# 4. Ajouter taxes (CTA, CSPE/accise, TVA) selon ParameterStore

# Comparaison multi-contrats :
# Pour chaque structure tarifaire candidate (Base, HP/HC, Tempo, indexe spot) :
#   facture_simulee = shadow_bill(courbe, grille_tarifaire)
# Recommandation = contrat avec min(facture_simulee)

# Ecart facture reelle vs shadow = detection anomalies facturation
# (erreur index, mauvais profil applique, puissance incorrecte)
```

## Correlation prix spot / courbe de charge

```python
# Pour clients sur offre indexee marche :
# Cout moyen pondere = sum(P(t) * prix_spot(t) * dt) / sum(P(t) * dt)
# Compare au prix spot moyen simple = mean(prix_spot)
# Si cout_pondere > prix_moyen : le client consomme aux mauvaises heures
# Si cout_pondere < prix_moyen : profil favorable (consomme en heures creuses spot)

# Indicateur de sensibilite spot :
# correlation(P_horaire, prix_spot_horaire)
# Positive = consomme quand c'est cher (defavorable)
# Negative = consomme quand c'est pas cher (favorable, ou flexible)

# 513 heures de prix negatifs en 2025
# Sites flexibles peuvent en profiter (charge batteries, ECS, process decalable)
```

## Detection d'anomalies -- pipeline recommande

```python
# 1. Pre-filtre : seuils physiques
#    P < 0 (soutirage), P > 2 * P_souscrite

# 2. Modele contextuel :
#    LOF ou IsolationForest entraine sur 3 derniers mois
#    Par cluster de jours (LV ouvre, samedi, dimanche/ferie)

# 3. Post-filtre : suppression alertes redondantes, agregation par episode

# 4. Explicabilite : SHAP values

# 5. Feedback loop : user marque "faux positif" -> reentrainement

# Target : < 0.27 alertes pertinentes / site / jour
# Taux faux positifs < 20%
```

## Forecasting

| Horizon | Modeles | MAPE typique | Usage |
|---|---|---|---|
| J+1 a J+7 | ARIMA, Prophet, XGBoost, LSTM | 5-15% | Achat spot, position |
| M+1 a M+12 | Regression DJU + tendance + saisonnalite | 10-25% | Budget, trajectoire DT |

## Normalisation pour comparaison inter-sites

| Methode | Formule | Usage |
|---|---|---|
| Par surface | kWh/m2/an ou W/m2 | Benchmark ADEME/OPERAT |
| Par DJU | kWh/DJU | Isoler thermosensibilite |
| Par occupation | kWh/ETP | Sites tertiaires |
| Facteur de charge | P_moy/P_max (0-1) | Comparaison forme courbe |

## IPE -- Indicateur de Performance Energetique

```python
# kWh par unite d'activite -- benchmark sectoriel
IPE_batiment = E_annuelle_kwh / surface_m2          # kWh/m2/an
IPE_industrie = E_periode_kwh / tonnes_produites     # kWh/tonne
IPE_hotel = E_periode_kwh / nuitees                  # kWh/nuitee
IPE_commerce = E_periode_kwh / CA_euros              # kWh/euro CA

# Derive IPE : si IPE augmente a activite constante
# -> inefficacite croissante (vieillissement equip, dereglage parametres)
# Regression lineaire IPE mensuel sur 12-24 mois : pente > 0 = derive
```

## M&V IPMVP -- Validation impact travaux

```python
# Measurement & Verification (protocole IPMVP)
# 1. Baseline : modele predictif entraine sur periode pre-travaux
#    E_baseline = f(DJU, jour_semaine, heure, activite)
# 2. Post-travaux : predire ce qu'aurait ete conso sans travaux
# 3. Economies = E_predite_post - E_reelle_post

# IMPERATIF : ajuster pour variables externes (temperature, activite)
# Comparaison pre/post DOIT etre ajustee DJU pour isoler effet travaux
# Sinon un hiver doux simule une economie qui n'existe pas

# Change Point Detection pour identifier date rupture :
# Algorithmes : PELT, Binary Segmentation, CUSUM, Bayesian CPD
```

## Estimation potentiel flexibilite

```python
# Par usage pilotable :
# | Usage        | P typique | Pilotable | Duree max effacement | Impact confort |
# | CVC          | 20-50 kW  | Oui       | 1-2h (inertie therm) | Faible <2C     |
# | ECS          | 5-15 kW   | Oui       | 4h (reserve tampon)  | Nul            |
# | Eclairage    | 2-5 kW    | Non       | -                    | Critique       |
# | Process      | 10-100 kW | Partiel   | 30min                | Modere         |
# | IRVE         | 7-22 kW   | Oui       | 2-4h (V2G/V1G)      | Faible         |

# Potentiel effacement total :
flex_total_kwh = sum(P_pilotable_i * duree_max_i for i in usages_pilotables)

# Valorisation :
# - Effacement pointe : kWh * (prix_pointe - prix_base)
# - Mecanisme capacite : euros/MW disponible
# - Mecanisme ajustement (agregateur) : euros/MWh active
# - Seuil NEBCO : 100 kW par pas 10 min
```

## Clustering de profils

```python
# Objectif : regrouper sites par forme de courbe (independamment du volume)
# Features : LF, R_nj, R_sw, gradient_thermo, coef_saisonnier, V_intra
# Methodes : K-Means, DBSCAN, Hierarchical
# Distance : euclidienne ou DTW (Dynamic Time Warping) entre courbes

# Clusters typiques tertiaire :
# Cluster 1 "Bureaux" : pic LV jour, faible WE, thermosensible
# Cluster 2 "Commerce" : pic apres-midi/soir, WE actif, peu thermo
# Cluster 3 "Sante"   : continu 24/7, faible variabilite
# Cluster 4 "Enseignement" : pic semaine, effondrement vacances

# Prerequis B2B : resultats explicables (pas de "cluster 7" sans label)
# Normaliser par P_moy avant clustering pour comparer formes, pas volumes
```

## NILM -- Non-Intrusive Load Monitoring

```python
# ATTENTION : precision moderee (50-80%), NE PAS vendre comme fonctionnalite
# Utiliser comme PRE-DIAGNOSTIC avant audit physique

# Methodes disponibles :
# 1. Analyse spectrale (FFT) : cycles on/off reguliers (frigo ~1/h)
# 2. Edge detection : transitions brutales (allumage/extinction)
# 3. Clustering motifs : patterns recurrents (pic 19h = cuisson)
# 4. ML (HMM, LSTM) : desagregation multi-equipements

# Heuristiques metier PROMEOS (preferer a NILM pur) :
# - Baseload 2h-5h = veilles + serveurs + froid
# - Surplus jour vs nuit = CVC + eclairage
# - Correlation DJU = chauffage electrique
# - Pics reguliers = process, ascenseurs, ventilation

# Necessite historique > 6 mois pour fiabilite
# Ne remplace PAS le sous-comptage physique pour audit precis
```

## Analyse temporelle avancee

```python
# Decomposition saisonnalite (STL, X-13-ARIMA) :
# Serie = Tendance + Saisonnalite + Residu

# Profils types :
# - Residentiel France : pic janvier (chauffage), creux aout (vacances)
# - Industrie : plus lisse, creux aout si arret maintenance
# - Tertiaire bureaux : saisonnalite + effondrement vacances scolaires

# Segmentation temporelle :
# | Periode          | Plages         | Jours      | Usage reference   |
# | Heures ouvrees   | 8h-18h         | Lun-Ven    | Activite maximale |
# | Heures non ouv.  | 18h-8h         | Lun-Ven    | Veilles, securite |
# | Week-end          | 0h-24h         | Sam-Dim    | Reduit ou nul     |
# | Nuit profonde     | 2h-6h          | Tous jours | Baseload pur      |

# Ratio ouvre/non-ouvre :
# Tertiaire bureaux attendu : 5-10
# Si ratio < 2 : consommation anormale hors heures (gaspillage probable)

# Calendrier francais : integrer workalendar.europe.France
# pour jours feries + vacances scolaires (impact significatif enseignement)
```

## Gestion fuseau horaire -- regles

```python
# Stockage : UTC (timezone-aware)
from datetime import datetime, timezone
ts = datetime.now(timezone.utc)

# Calcul : UTC
# Affichage : Europe/Paris
# Agregation journaliere : minuit a minuit CET/CEST

# Changements d'heure :
# Passage ete (dernier dim mars, 2h->3h) : 46 pas de 30min
# Passage hiver (dernier dim oct, 3h->2h) : 50 pas de 30min
# Solution : pd.date_range(tz='Europe/Paris', freq='30min')

# Impact sur calculs :
# - Conso journaliere : un jour de changement != 24h (23h ou 25h)
# - Moyennes horaires : exclure jours changement ou corriger ponderation
# - Modeles predictifs : feature engineering pour capturer effet
```
