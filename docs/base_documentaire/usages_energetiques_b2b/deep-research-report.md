# Cartographie actionnable des usages et comportements énergétiques des bâtiments B2B en France

## Synthèse exécutive

- La consommation finale d’énergie en France se répartit entre secteurs avec un poids significatif du tertiaire et de l’industrie : en 2024, le tertiaire représente 15 % et l’industrie 18 % de la consommation finale énergétique (tous vecteurs). citeturn32view1  
- Le dispositif **Éco Énergie Tertiaire** (issu du “décret tertiaire”) impose, pour les bâtiments tertiaires assujettis, une trajectoire de réduction de la **consommation d’énergie finale** d’au moins **–40 % en 2030, –50 % en 2040, –60 % en 2050** (référence 2010) et organise la collecte/évaluation via une plateforme numérique. citeturn32view0turn33search0  
- Le **décret BACS** (systèmes d’automatisation et de contrôle des bâtiments) impose, pour les bâtiments équipés de CVC > 290 kW, une échéance **au 1er janvier 2025**, et pour ceux > 70 kW une échéance **au plus tard le 1er janvier 2030** (avec exemption possible si TRI ≥ 10 ans). citeturn20view0turn22view0  
- Les exigences “BACS” structurent directement les besoins data/IA : suivi et analyse **au pas horaire par zone fonctionnelle**, détection de pertes d’efficacité, interopérabilité, et conservation des données **5 ans à l’échelle mensuelle**. citeturn20view1  
- Pour les sites BT ≤ 36 kVA équipés de compteurs communicants, l’activation de la collecte permet typiquement une courbe de charge **au pas 30 min**, pouvant être réduite à **15 min** (voire 10 min selon services), et une “désactivation” ramène à 60 min. citeturn12view2  
- Côté “référentiels de signatures”, entity["company","Enedis","grd france"] publie en open data des **agrégats segmentés de consommation** au pas **1/2h** (≤ 36 kVA et > 36 kVA) incluant des **courbes de charge moyennes** par profils, plages de puissance et (pour > 36 kVA) **secteur d’activité dérivé du code NAF**. citeturn27view0turn29view0turn28search13  
- Dans le tertiaire, les “dérives hors horaires” sont un gisement majeur : sur un panel de bâtiments, entity["organization","Cerema","france"] observe que **> 30 %** de la consommation d’éclairage du tertiaire peut avoir lieu en **période d’inoccupation**, avec des cas de dérives au-delà de niveaux élevés. citeturn18view0  
- Les data centers constituent un archétype électrique critique : le entity["organization","SDES","france statistics energy"] estime pour la France métropolitaine **4 à 6 TWh** en 2023 (incertitude sur “petits” sites), avec une très forte concentration (21 % des sites ≈ 78 % de la conso des grands sites). citeturn34view3  
- Les trajectoires 2026–2035 projettent une forte tension sur certains usages (numérique, IRVE) : entity["organization","RTE","french tso"] indique qu’un scénario table sur un **triplement** de la consommation des data centers d’ici 2035 (23–28 TWh). citeturn34view1  
- En industrie, une lecture “utilités vs procédés” est généralement actionnable pour l’IA : une source ATEE (données Ceren consolidées EDF, année 2007) indique que l’électricité industrielle est dominée par les **moteurs** (ordre de grandeur), et que les **utilités** (ventilation, pompage, air comprimé, froid…) structurent des signatures repérables et pilotables. citeturn37view0  

## Cadre de référence et sources

Le périmètre visé couvre les bâtiments B2B en entity["country","France","metropolitan focus"] (priorité métropole), avec mention des spécificités DROM lorsque les signatures et la saisonnalité changent fortement (notamment la climatisation). Les vecteurs considérés sont l’électricité (prioritaire) et, lorsque nécessaire pour expliquer les profils électriques, les usages thermiques (gaz, réseaux de chaleur, fioul/biomasse) qui déplacent ou réduisent la thermosensibilité électrique.

Le corpus “sources obligatoires” mobilisé ici privilégie :  
- Textes officiels sur entity["organization","Légifrance","official legal portal france"] pour **décret tertiaire** et **BACS**. citeturn32view0turn20view0turn22view0  
- Publications de l’État (écologie.gouv, SDES) et de l’écosystème public (ADEME, Cerema) pour chiffrages et retours terrain. citeturn32view1turn34view3turn18view0turn25search0  
- Données réseau et open data (Enedis) pour structurants “data / signatures”. citeturn27view0turn29view0turn12view2turn12view3  
- Références normalisation et management : entity["organization","ISO","international standardization body"] 50001 (système de management de l’énergie) et corpus France (ecologie.gouv) pour cadrer “processus + mesurage” (utile pour industrialiser des agents IA dans des organisations). citeturn24search1turn24search5  

Points de vigilance méthodologiques (assumés et explicités) :  
- Les “parts par usage” (chauffage vs refroidissement vs spécifiques) varient fortement selon sous-secteur, climat, équipements, et niveau de sous-comptage. Dès qu’un chiffre n’est pas directement sourcé, il est remplacé par une plage, ou transformé en “méthode de mesure” (ce qu’il faut instrumenter pour le connaître sur un site). citeturn9view0turn9view2  
- Les données open (OPERAT, agrégats Enedis) sont puissantes pour construire des priors et des modèles, mais comportent des limites (contrôles de cohérence “larges”, anonymisation, secret des affaires, règles de publication). citeturn9view0turn9view2turn27view1  

Contexte 2026–2030 à intégrer dans les agents IA (drivers structurants) :  
- Trajectoires nationales de consommation électrique plus incertaines mais potentiellement en hausse selon scénarios de décarbonation. citeturn10search0  
- Intensification de la flexibilité et des contraintes prix/réseau, avec montée du pilotage (effacement, IRVE, GTB/BACS). citeturn26view0turn26view1turn20view1  
- Croissance possible des data centers (charge 24/7 et demandes de raccordement fortes). citeturn34view3turn34view1turn34view2  

## Taxonomie opérationnelle des usages

La taxonomie ci-dessous est conçue comme une **ontologie exploitable** (étiquetage, features, règles, recommandations, pilotage). Elle suit les niveaux demandés (Secteur → Sous-secteur → Usages finaux → Pilotabilité/Criticité/Contraintes).

### Ontologie des usages

**Niveau secteur**  
- Tertiaire  
- Industrie  
- Bailleurs sociaux / habitat collectif (parties communes + équipements collectifs +, selon cas, usages individuels agrégés)

**Niveau sous-secteur (exemples prioritaires)**  
- Tertiaire : bureaux, commerce/retail, santé, éducation, hôtellerie, restauration, logistique/entrepôts, administrations, data centers  
- Industrie : process électro-intensifs, process thermiques, froid industriel, air comprimé, vapeur/chaleur, moteurs/entraînements, pompage  
- Habitat collectif : parties communes (éclairage, ascenseurs, ventilation, parkings), chaufferies/production ECS collective, éventuellement IRVE résidentielle collective

**Niveau usages finaux (électricité, et effets multi-énergies)**  
- CVC : chauffage (électrique direct / PAC / groupes via GTB), refroidissement (DRV, groupes froids), ventilation/CTA, pompes/auxiliaires, régulation  
- ECS : production (ballons électriques/thermodynamiques, PAC, échangeurs), bouclage et pompes, appoint  
- Éclairage : intérieur, sécurité (BAES), extérieurs/parkings  
- Usages spécifiques tertiaires : bureautique/IT, salles serveurs, cuisines, blanchisserie, stérilisation, imagerie (selon sites), etc.  
- Froid commercial/industriel : vitrines, chambres froides, surgélation, centrales frigorifiques  
- Mobilité électrique : IRVE (recharge opportuniste, flotte, visiteurs), contraintes réseau et puissance  
- Industrie utilités : air comprimé, pompage, ventilation, refroidissement, moteurs entraînements  
- Industrie procédés : cycles batch/continu, électrolyse, fours, presses, etc. (signature très spécifique)

**Niveau actifs pilotables / non pilotables, criticité, contraintes**  
- Pilotables “souples” (souvent sans impact process direct) : éclairage (hors sécurité), ventilation hors contrainte qualité d’air, consignes CVC en inoccupation, ECS/bouclage (fenêtrage), air comprimé (arrêt hors prod), optimisation pression. citeturn18view0turn37view1  
- Pilotables “contraints” : froid alimentaire (inertie produit), data centers (température/humidité), process industriels (qualité/temps cycle), hôpitaux (santé/sécurité). citeturn34view3turn34view2turn18view0  
- Non pilotables (à court terme) : postes “mission-critical” (IT critique), certains procédés continus, sécurité incendie, contraintes réglementaires. citeturn20view1  

### Dictionnaire usages et signatures électriques

Table conçue pour relier directement “usage → signature → data minimale → levier IA”.

| Usage final | Signature typique à 30 min / 15 min | Drivers dominants | Actifs pilotables | Data minimale pour confirmer |
|---|---|---|---|---|
| Chauffage électrique / PAC | Thermosensibilité marquée (hausse quand T° baisse), parfois “marche/arrêt” matin et week-end | Température extérieure, consignes, inertie, horaires | Consignes, plages horaires, délestage | Courbe de charge, T° extérieure, calendrier, infos système/puissance souscrite citeturn12view3turn12view2 |
| Refroidissement (clim, groupes froids) | Thermosensibilité à la hausse (hausse quand T° monte), pointes diurnes saison chaude | T°, apports solaires, occupation, consignes | Consignes, free-cooling, optimisation horaires | Courbe, T°, calendrier (vacances), états/consignes CVC citeturn18view0turn20view1 |
| Ventilation / CTA | Base load + modulation horaire, parfois constance “24/7” (dérive) | Occupation, qualité d’air | Vitesse variable, arrêt nuit | Courbe, horaires, états GTB (marche/arrêt) citeturn20view1turn18view0 |
| Éclairage tertiaire | Pic en présence + dérives significatives en inoccupation possibles | Occupation, automatismes | Horaires, détecteurs, lux/NO, relamping LED | Courbe + événements horaires; sous-comptage utile | citeturn18view0 |
| BAES / sécurité | Faible mais 24/7, stable | Normes sécurité | Non (sauf optimisation conformité matériels) | Sous-comptage ou estimation (souvent) | citeturn18view0 |
| Bureautique / IT (bureaux) | Base load nuit + montée matin; week-end réduit mais non nul | Occupation, politiques IT | Mise en veille, gestion postes, salles serveurs | Courbe + calendrier + inventaire IT | citeturn18view0 |
| Salle serveurs / mini-DC | Base load élevé constant 24/7 + clim dédiée | IT load, refroidissement | Consignes, confinement, UPS, récupération chaleur | Courbe + T° salle + états clim/UPS | citeturn18view0turn34view3 |
| Froid commercial | Cycles compresseurs, intensité selon ouverture et saison; parfois pointe nuit (dégivrage) | T°, portes, charge produit | Réglages, dégivrage, variation vitesse | Courbe + sous-comptage froid + T° | citeturn18view0 |
| IRVE (site tertiaire / flotte) | “Bosse” fin de journée ou matin; très sensible aux règles de recharge | Comportements, tarifs, pilotage | Smart charging, délestage, planification | Courbe + données borne + calendrier + signaux prix | citeturn26view1 |
| Ascenseurs (bureaux / collectif) | Événements brefs + veille (standby), corrélé occupation | Occupation, réglage veille | Veille, éclairage cabine | Sous-comptage ou signature par pics + veille | citeturn18view0 |
| Air comprimé | Consommation liée à pression/débit, fuites visibles en hors production; “charge à vide” | Production, pression, fuites | Arrêt, baisse pression, chasse aux fuites | Courbe + mesures pression/débit + état compresseurs | citeturn37view1 |
| Pompage (industrie/utilités) | Cycles, corrélé process; parfois nocturne (remplissage) | Process, niveaux | VSD, séquencement | Courbe + capteurs process (niveau, débit) | citeturn37view0 |
| Data center | Base load élevé, stable; peu de week-end; refroidissement corrélé T° | IT demand, refroidissement | Consignes, free cooling, récupération chaleur | Courbe + T° + PUE/IT load + états refroidissement | citeturn34view3turn34view2 |

## Archétypes et signatures de charge

Cette section livre la cartographie “macro → micro” des profils attendus par archétype, et propose des critères de reconnaissance exploitables par agents IA.

### Cartographie détaillée des archétypes

Le tableau ci-dessous est volontairement orienté “diagnostic via courbe + contexte minimal” (MVP) et “pilotage si GTB/IRVE/process” (niveau avancé).

| Archétype | Profil quotidien typique | Hebdo / vacances | Saison | Usages dominants (impact électrique) | Signatures reconnaissables | Data minimale |
|---|---|---|---|---|---|---|
| Bureaux / admin (tertiaire) | Base load nuit + **ramp-up matin**, plateau journée, **ramp-down soir** | Week-end réduit; périodes vacances visibles | Chauffage/clim selon équipements; intersaison sensible réglages | CVC, éclairage, IT; dérives en inoccupation possibles | Surconso nocturne; simultanéité chaud/froid; éclairage en inoccupation | Courbe 30/15 min possible citeturn12view2 + T° ext + calendrier |
| Retail / commerce | Pic heures ouverture; pointe possible fin journée; éclairage fort | Dimanche variable; jours fériés très marqués | Clim saison chaude; chauffage saison froide | Éclairage, CVC, froid (si alimentaire) | Pic stable “horaires + vitrines”; dérives portes ouvertes | Courbe + calendrier jours fériés + T° |
| Santé (hôpital / clinique) | Charge 24/7 élevée; pics jour; base load fort | Week-end peu réduit | CVC + stérilisation/blocs | CVC, ventilation, équipements techniques | Base load très élevé; variabilité limitée; contraintes fortes | Courbe + T° + liste systèmes critiques |
| Éducation (écoles/lycées) | Charge jour forte; **creux vacances scolaires** | Semaine marquée; week-end bas | Chauffage important; ventilation | Chauffage, ventilation, éclairage | “Reduits” chauffage observables; relances matin | Courbe + calendrier vacances + T° citeturn18view0 |
| Hôtellerie | Charge étalée; ECS et blanchisserie; cuisine selon offre | Week-end souvent haut | Clim en été (fort), chauffage en hiver | CVC + ECS + cuisines + parfois froid | Pointe matin (petit-déj/ECS), pointe soir | Courbe + calendrier occupation |
| Restauration (site dédié) | Pic midi et/ou soir; cuisine très marquée | Week-end selon activité | Clim été ; extraction/ventilation | Cuisson, ventilation, froid, ECS | Pointe brève forte; ventilation prolongée | Courbe + horaires service |
| Logistique / entrepôt | Faible base load; éclairage selon occupation; chauffage selon volume | Week-end faible | Chauffage (souvent gaz) → élec plus faible, ventilation | Éclairage, recharge engins, CVC variable | Charge “rectangulaire” (horaires), faible thermosensibilité si gaz | Courbe + calendrier |
| Data center | **Base load très élevé et stable 24/7** | Week-end quasi identique | Refroidissement augmente avec T° | IT + refroidissement | Faible variabilité; corrélation T° sur auxiliaires; UPS test | Courbe + T° + données refroidissement citeturn34view3turn34view2 |
| Industrie “moteurs/utilités” | Base load process + cycles (pompes, ventilation…) | Week-end dépend de production | Saison faible sauf locaux/ventilation | Moteurs, ventilation, pompage, air comprimé, froid | Cycles; charge à vide; fuites; dérives pression | Courbe + états machines; pour air comprimé pression/débit citeturn37view0turn37view1 |
| Industrie électro-intensive | Charge élevée, parfois quasi constante; modulable si effacement | Week-end proche semaine si continu | Peu liée météo | Process (électrolyse, fours…) | Plateaux longs; contraintes fortes; opportunités effacement | Courbe + contraintes process + signaux prix/effacement citeturn26view0 |
| Habitat collectif parties communes | Faible mais 24/7 (éclairage sécu), plus pics (ascenseurs) | Week-end similaire (occupation résidentielle) | Ventilation parking; bouclage ECS si collectif | Éclairage commun, ascenseurs, VMC, pompes | Éclairage permanent anormal; ascenseur veille élevée | Courbe + inventaire équipements; sous-comptage idéal citeturn18view0 |
| Habitat collectif chaufferie/ECS (collectif) | Pompes/bouclage parfois 24/7, pics matin/soir | Week-end similaire | Si chauffage électrique/PAC → thermosensibilité | Pompes, auxiliaires, éventuellement PAC | Temps de marche trop long, bouclage continu | Courbe + T° + états pompes/régulation citeturn18view0 |

### Spécificités DROM utiles pour signatures

Dans certains DROM, la climatisation devient un usage dominant et change complètement le pattern saisonnier (moins “hiver thermosensible”, plus “été thermosensible”). À La Réunion, des études sectorielles tertiaires montrent un poste **climatisation/ventilation** très dominant sur certains segments (ordre de grandeur autour de la moitié dans des cas étudiés). citeturn31search6turn31search8  

### Reconnaissance dans les données

La reconnaissance robuste combine (i) **formes de charge** (shape) et (ii) **drivers exogènes**.

**Signaux “shape” (micro, 15/30 min)**  
- Base load (médiane nuit) et ratio base/peak  
- Pentes de montée/descente (matin/soir)  
- Indice week-end vs semaine  
- Cycles (spectre fréquentiel / autocorrélation) pour froid/air comprimé/process  
- Détection de ruptures (changepoint) et dérives (CUSUM)

**Signaux “drivers” (macro & micro)**  
- Thermosensibilité (via T° extérieure, modèles piecewise) : Enedis fournit une base de données “thermosensibilité” annualisée par secteur/NAF utile comme prior. citeturn12view3  
- Calendrier (jours fériés, vacances scolaires, périodes d’ouverture)  
- Données contractuelles (puissance souscrite, option tarifaire) accessibles via Enedis selon modalités. citeturn17search13turn12view2  

## Leviers de valeur et matrice décision-service

Les leviers sont classés “du plus simple au plus avancé”, et reliés à des services industrialisables (monitoring, anomalies, forecasting, recommandations, pilotage, conformité).

### Leviers par niveau de maturité

**Monitoring et qualité de données (fondation)**  
- Contrôler complétude, trous, doublons, cohérence index/factures, cohérence puissance vs énergie, cohérence sites multi-compteurs.  
- Exploiter les règles Enedis : profondeur historique, pas de temps, et conditions d’accès (consentement, activation). citeturn12view2turn17search13  

**Détection d’anomalies (ROI court, souvent sans CAPEX)**  
- Surconsommations nocturnes / week-end  
- Équipements hors horaires (ventilation, éclairage, clim)  
- Dérives de consignes, simultanéité chaud/froid  
- Dérives air comprimé (fuites 10–20% typiques, charge hors production) citeturn37view1  

**Prévision (portefeuille et site)**  
- Court terme (J+1 / J+7) : optimisation achats, pointe, effacement, pilotage IRVE  
- Moyen terme (M+1) : budget, capacité, contractualisation puissance  
- Pour IRVE : sans pilotage, la recharge “naturelle” peut pousser la pointe vers 19–21h; le pilotage est un enjeu système reconnu par la CRE. citeturn26view1  

**Recommandations efficacité énergétique**  
- Quick wins : horaires, consignes, extinction auto, chasse aux fuites air comprimé, optimisation pression (1 bar ≈ +7% énergie sur compression). citeturn37view1turn25search0  
- CAPEX : GTB/BACS, variation de vitesse, relamping LED, rénovation enveloppe, récupération chaleur (data centers, industrie). citeturn20view1turn34view2turn18view0  

**Pilotage / flexibilité**  
- Implicite (prix) ou explicite (effacement) : RTE définit les pointes hivernales (8–13h et 18–20h) et le rôle de l’effacement pour prévenir délestage. citeturn26view0  
- Pilotage IRVE (smart charging), pilotage CVC via GTB, pilotage air comprimé et froid.

### Matrice décision / service

Table “problème → hypothèse → data à demander → actions”, avec un score ICE (Impact, Confiance, Effort) indicatif sur 10 (plus haut = prioritaire).

| Secteur / archétype | Symptôme observé | Hypothèses prioritaires | Data à demander | Actions no-regret | Actions CAPEX | Pilotage possible | ROI estimatif | Risques | ICE |
|---|---|---|---|---|---|---|---|---|---|
| Bureaux | Base load nuit élevé | IT/serveurs, ventilation ou éclairage en marche, consignes CVC | Courbe 30/15 min, calendrier, T°, états GTB si dispo citeturn12view2turn20view1 | Réglage horaires CVC/éclairage; politiques veille IT | GTB/BACS si absent (obligations) citeturn20view0 | Oui (GTB) | Souvent rapide (mois) si dérive forte | Plaintes confort | 8 |
| Retail | Pic constant après fermeture | Éclairage/vitrines, ventilation, portes | Calendrier, courbe, éventuellement sous-compteurs | Règles fermeture; alerte “après fermeture” | Automatismes éclairage | Oui | Rapide | Sécurité | 7 |
| Éducation | Chauffage actif vacances | Programmation/régulation, relances | Vacances scolaires, courbe, T° | Ajuster réduits / relances citeturn18view0 | Régulation avancée | Possible | Rapide | Confort matin | 7 |
| Data center | Hausse été disproportionnée | Refroidissement inefficace, consignes basses | T°, IT load/PUE, états refroidissement | Ajuster consignes (si SLA), free-cooling | Récupération chaleur (selon débouchés) citeturn34view2 | Partiel | Variable | SLA / risques IT | 6 |
| Industrie air comprimé | Conso stable week-end | Fuites, compresseur non arrêté, pression trop haute | Pression/débit, état compresseurs | Campagne fuites; arrêt hors prod; baisse pression (gain ~7%/bar) citeturn37view1 | VSD, réseau, séchage optimisé | Oui | Souvent élevé | Qualité air process | 8 |
| Habitat collectif PC | Éclairage commun 24/7 | Temporisations mal réglées, détecteurs HS | Inventaire, courbe, visites | Recalibrer détecteurs/minuterie citeturn18view0 | LED + détection | Oui | Rapide | Sécurité | 7 |
| IRVE tertiaire | Pointe 19–21h | Recharge non pilotée | Données bornes, heures connexion, contrat | Smart charging, plafonds puissance | Stockage local / raccordement | Oui | Variable | Satisfaction usagers | 6 |

### Trente règles / alertes prêtes à implémenter

Table “spécification exécutable” (seuils par défaut à calibrer par site via historique).

| ID | Règle (condition) | Données | Seuil par défaut | Gravité |
|---|---|---|---|---|
| A01 | Surconsommation nuit : (P_nuit_médiane > x% de P_jour_médiane) jours ouvrés | Courbe | x=40% | Haute |
| A02 | Week-end anormal : énergie week-end > 80% semaine | Courbe + calendrier | 80% | Moy |
| A03 | Ramp-up trop tôt : montée puissance avant horaire d’ouverture | Courbe + horaires | >1h | Moy |
| A04 | Ramp-down tardif : puissance élevée >2h après fermeture | Courbe + horaires | >2h | Moy |
| A05 | Base load dérive : base_nuit augmente >15% vs baseline 8 semaines | Courbe | +15% | Haute |
| A06 | Pic puissance récurrent > puissance souscrite x 0,95 | Courbe + puissance souscrite | 95% | Haute |
| A07 | “Plateau 24/7” sur un site supposé tertiaire | Courbe + classification | oui/non | Haute |
| A08 | Thermosensibilité inversée (chauffage supposé) | Courbe + T° | corrélation signée | Moy |
| A09 | Clim active en hiver (T° < seuil) + puissance CVC élevée | Courbe + T° | T°<15°C | Moy |
| A10 | Éclairage en inoccupation suspect (si sous-compteur éclairage) | Sous-compteur | >30% conso hors occup. citeturn18view0 | Haute |
| A11 | Ventilation nocturne continue (si GTB état ON) | GTB états | ON>90% nuit | Moy |
| A12 | Simultanéité chaud/froid (chauffage + froid ON) | GTB | chevauchement >1h | Haute |
| A13 | ECS bouclage 24/7 sans abaissement | Pompes/GTB | >22h/j | Moy |
| A14 | Détection “jours fériés” non respectés (profil identique semaine) | Calendrier | distance <ε | Moy |
| A15 | Anomalie “trou” data > 2h | Courbe | >2h | Basse |
| A16 | Valeurs négatives ou spikes irréalistes | Courbe | z-score>6 | Basse |
| A17 | Décalage horaire compteur (DST) | Courbe | pattern | Moy |
| A18 | Énergie journalière incohérente vs facture (écart >10%) | Facture + index | 10% | Haute |
| A19 | IRVE : recharge sur période rouge/peak (si signal) | Prix/alerte | oui/non | Moy citeturn26view1 |
| A20 | IRVE : dépassement site plafond puissance (agrégation) | Courbe + bornes | >x kW | Haute |
| A21 | Air comprimé : débit hors production > seuil | Débit | >10–20% prod citeturn37view1 | Haute |
| A22 | Air comprimé : pression moyenne +1 bar vs cible | Pression | +1 bar | Moy citeturn37view1 |
| A23 | Air comprimé : temps à vide compresseur élevé | État compresseur | >30% | Moy |
| A24 | Froid : cycles trop longs (duty cycle) | Sous-compteur froid | >x% | Moy |
| A25 | Data center : dérive T° consigne “trop basse” | GTB/PUE | <cible | Moy citeturn34view2 |
| A26 | Data center : hausse été > baseline météo prévu | T° + modèle | résidu>3σ | Haute |
| A27 | Ascenseur : veille cabine permanente | Sous-compteur | >x W | Basse citeturn18view0 |
| A28 | Éclairage commun : détecteurs dysfonctionnement (allumé continu) | Sous-compteur | >y h/j | Moy citeturn18view0 |
| A29 | Signature “NV” : nouveau régime horaire détecté (changepoint) | Courbe | changepoint | Moy |
| A30 | Non-conformité BACS potentielle (pas de données horaires par zone) | GTB/data | manquant | Haute citeturn20view1 |

## Blueprint agents IA et kit data

### Architecture fonctionnelle des agents

Schéma texte (interfaces types) :

1) **Ingestion & Qualité** → 2) **Segmentation & Archétypes** → 3) **Baseline & Normalisation** → 4) **Détection anomalies** → 5) **Prévision** → 6) **Recommandations** → 7) **Pilotage** → 8) **Conformité** → 9) **Reporting & Tickets**

Ce blueprint est aligné avec les obligations/attentes réglementaires : collecte et suivi du tertiaire (plateforme, kWh/m²/an, ajustements climatiques), et exigences BACS sur données horaires par zones. citeturn32view0turn32view2turn20view1  

### Tableau des agents IA

| Agent | Objectif | Inputs | Outputs | KPIs | Fréquence | Besoin humain |
|---|---|---|---|---|---|---|
| Ingestion & Qualité | Normaliser multi-compteurs, gérer trous/spikes, contrôler cohérence | Courbes (15/30/60), index, factures, puissance souscrite citeturn12view2 | Dataset “propre”, score qualité | % complétude, taux outliers, écart facture | Quotidien / intraday | Validation exceptions |
| Segmentation & Archétypes | Classer secteur/sous-secteur; clustering shapes | Courbe, calendrier, T°, NAF (si connu) citeturn28search13 | Label archétype + confiance | accuracy/ARI, stabilité clusters | Hebdo | Ajuster mapping métier |
| Baseline & Normalisation | Baseline météo/occupation; référence pour M&V simplifié | Courbe + T° + calendrier | Baseline + résidu | CVRMSE, biais | Quotidien / mensuel | Revue mensuelle |
| Détection anomalies | Règles + ML; scoring gravité/urgence | Résidus baseline + règles 30 alertes | Alertes, causes probables | FP rate, temps détection | Intraday / quotidien | Triage + actions |
| Prévision | J+1/J+7/M+1 avec incertitudes | Courbe hist, T° forecast, calendrier, événements | Forecast + PI | MAPE/Pinball loss | Quotidien | Validation exceptions |
| Recommandations | Mesures + ROI + priorisation | Alertes + inventaire + coûts énergie | Plan d’action | taux adoption, € économisés | Hebdo / mensuel | Décision CAPEX |
| Pilotage | Optimisation sous contraintes (GTB/IRVE/process) | États GTB, consignes, prix, contraintes réseau | Consignes, schedules | kW évités, confort SLA | 5–15 min | Supervision |
| Conformité | Décret tertiaire, BACS, preuves | Données conso, surfaces, catégories, GTB | Dossier, checklists, exports | complétude, non-conformités | Mensuel / annuel | Validation juridique |
| Reporting | Synthèse exécutive, tickets maintenance | Tous outputs | Rapports, tickets | délais traitement, satisfaction | Hebdo | Exploitation |

### Kit data minimum par typologie

| Niveau | Tertiaire | Industrie | Habitat collectif (bailleurs) |
|---|---|---|---|
| MVP | Courbe 30/15 min si possible citeturn12view2, factures, T° ext, calendrier, puissance souscrite | Courbe + factures + calendrier prod (même simple) | Courbe compteur parties communes + factures + inventaire équipements |
| Intermédiaire | Sous-comptage (CVC/éclairage/IT), états GTB (consignes, T°, marche/arrêt) | Sous-comptage utilités (air comprimé, froid, pompage), états machines | Sous-comptage ascenseurs/éclairage/ventilation; ECS collective (pompes, bouclage) citeturn18view0 |
| Avancé | Télémetries équipements CVC, capteurs confort/IAQ, IRVE, PV, prix spot | Pression/débit air comprimé, capteurs process, qualité/production, pas ≤10 min si nécessaire (exigences mesure) citeturn37view1 | GTB si présente, supervision chaufferie, IRVE résidentielle, PV collectif |

### Modèle de features pour ML

Catégories de variables (liste opérationnelle) :  
- **Calendrier** : heure, jour semaine, férié, vacances scolaires, mois, “ouverture” (si dispo).  
- **Statistiques charge** : base_nuit, peak_jour, ratio base/peak, ramp-up slope, ramp-down slope, énergie 24h, énergie ouvrés vs week-end, quantiles, entropie.  
- **Thermosensibilité** : T° ext, DJU, interaction T°×heure, pente change-point. (Les jeux “thermosensibilité” Enedis donnent aussi des agrégats macro utiles.) citeturn12view3  
- **Qualité** : flags trous, outliers, recalage DST.  
- **Événements** : maintenances, plaintes confort, changements horaires.  
- **Actifs** : consignes, états ON/OFF, vitesse variable (si GTB).  
- **IRVE/PV** : sessions, puissance max, énergie, production PV (si mesurée), autoconsommation (net load).  
- **Prix/système** : prix de marché (si accessible), alertes de tension, consignes effacement (si contrat). citeturn26view0turn26view1  

### Méthode de clustering des courbes et limites

Pipeline recommandé (robuste en portefeuille multi-secteurs) :  
- Normalisation par **énergie journalière** + centrage sur base load (sinon les gros sites dominent).  
- Représentation jour-type par (i) vecteur 48 pas (30 min) ou 96 pas (15 min), (ii) features shape (ramp, ratios), (iii) signatures spectrales.  
- Distances : DTW (pour décalages), cosine (shape), ou distances sur features.  
- Clustering : HDBSCAN (détecte outliers) + k-means sur clusters stables.  
- Limites : multi-usages dans un même compteur, sous-comptage absent, changements d’occupation, effets tarifaires; d’où la nécessité d’un agent “Segment & Archetype” avec boucle humaine.

### Cinq cas d’usage “bailleurs sociaux” concrets

1) **Éclairage parties communes** : alerte “allumé permanent” + recommandation recalage temporisations/détecteurs (Cerema souligne la sensibilité aux automatismes et leurs dérives). citeturn18view0  
2) **Ascenseurs** : détection veille excessive (cabine, éclairage) et priorisation retrofit (veille, LED). citeturn18view0  
3) **Ventilation parking / VMC** : détection ventilation 24/7 non justifiée + reprogrammation + suivi du confort/IAQ. citeturn18view0  
4) **ECS collective** : alerte bouclage/pompes trop longues, optimisation plages, suivi des températures (sécurité sanitaire) et consommation auxiliaires. citeturn18view0  
5) **IRVE résidentielle collective** : prévention pointe via pilotage “puissance site” et algorithme équitable (plafond dynamique), en cohérence avec les enjeux système mis en avant par la CRE. citeturn26view1  

### Checklist terrain audit rapide

- **Bureaux / tertiaire généraliste** : horaires réels vs programmations, consignes chauffage/clim, dérives nuit/week-end, éclairage (détecteurs), sous-comptage CVC/éclairage/IT, présence GTB et capacité à produire pas horaire par zone (préparation BACS). citeturn20view1turn18view0  
- **Industrie** : cartographier utilités (air comprimé, froid, pompage), existence mesures pression/débit, stratégie arrêt hors prod, suivi moteurs/utilités (ordre de grandeur moteur dominant), opportunités récupération chaleur. citeturn37view0turn37view1  
- **Habitat collectif** : inventaire communs (BAES/éclairage, ascenseurs), réglages automatismes, ventilation, chaufferie/ECS collective, possibilité de sous-compter par poste. citeturn18view0  

### Schéma de données JSON

```json
{
  "site": {
    "site_id": "string",
    "secteur": "tertiaire|industrie|habitat_collectif",
    "sous_secteur": "string",
    "localisation": {"code_insee": "string", "meteo_station_id": "string"},
    "surfaces": [{"type": "SHON|SU|SHAB|autre", "valeur_m2": 0}],
    "contrat_elec": {"pdl_prm": "string", "puissance_souscrite_kva": 0, "option_tarifaire": "string"}
  },
  "compteurs": [
    {"compteur_id": "string", "type": "principal|sous_compteur", "vecteur": "elec|gaz|chaleur", "usage_associe": "string"}
  ],
  "actifs": [
    {"actif_id": "string", "categorie": "CVC|Eclairage|IRVE|AirComprime|Froid|Process",
     "pilotable": true, "criticite": "confort|securite|process_critique",
     "capteurs": ["etat_onoff", "consigne", "temperature", "debit", "pression"]}
  ],
  "mesures": [
    {"timestamp": "ISO8601", "compteur_id": "string", "pas_minutes": 15, "energie_wh": 0, "puissance_w": 0}
  ],
  "anomalies": [
    {"anomaly_id": "string", "type": "surconso_nuit|simul_chaud_froid|fuite_air_comprime|...",
     "score": 0.0, "debut": "ISO8601", "fin": "ISO8601", "evidence": {"features": {}, "regles": ["A01"]}}
  ],
  "recommandations": [
    {"reco_id": "string", "type": "quick_win|capex|pilotage", "gain_kwh_an": 0, "gain_eur_an": 0,
     "cout_eur": 0, "tri_ans": 0.0, "priorite": "P1|P2|P3", "preuves": ["string"]}
  ]
}
```

## Prochaines étapes pour industrialiser dans une plateforme EMS

Industrialiser la cartographie en plateforme suppose une trajectoire en quatre chantiers, directement alignée sur les obligations et la valeur opérationnelle :

1) **Data backbone** : connecteurs compteurs (activation/collecte courbe de charge), factures, météo, calendrier; dictionnaire “sites/compteurs/usages” et contrôles qualité systématiques. citeturn12view2turn27view1  
2) **Bibliothèque de signatures et baselines** : segmentation par archétypes (portefeuille), puis baselines météo/occupation; publication d’un “score santé énergétique” et d’un backlog d’actions. citeturn12view3turn32view2  
3) **Boucle décisionnelle** : moteur d’anomalies (30 règles + ML), estimation gains/ROI, tickets exploitation; intégration GTB/IRVE pour passer de “détecter” à “piloter”, notamment en vue des exigences BACS (données horaires, détection pertes d’efficacité, archivage). citeturn20view1turn26view1  
4) **Conformité et preuve** : modules dédiés décret tertiaire (déclarations, trajectoires, justificatifs) et BACS (capacité système, horaires par zone, preuves d’inspection/maintenance), avec exports auditables. citeturn32view0turn20view1turn33search1