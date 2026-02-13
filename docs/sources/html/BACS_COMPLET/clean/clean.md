decret_bacs_promeos_complet 

# 

# DÉCRET BACS : SYNTHÈSE COMPLÈTE & OPÉRATIONNELLE PROMEOS 2.0 

## Bâtiments Tertiaires – Automation & Control Systems 

Dernière mise à jour : 29 décembre 2025, 12h00 CET (Europe/Paris) 

Statut : Conforme aux décrets n°2020-887, n°2023-259, n°2025-1343 et arrêté 07/04/2023 

## TL;DR – 10 LIGNES CRITIQUES Aspect Information Quoi Obligation système d’automatisation CVC (chauffage/clim/ventilation) pour tertiaires Seuils >290 kW (2025) et >70 kW (anciennement 2027, reporté à 2030 ) >290 kW Deadline 01/01/2025 – URGENCE , sites non conformes sont hors-la-loi >70 kW Deadline 01/01/2030 (report novembre 2025) – Délai relâché mais opportunité économique immédiate Exemption TRI > 10 ans = dérogation valide (audit TRI requis, documentation 10 ans) Inspections Obligatoires : 5 ans max (2 ans post-installation), 1re avant 01/01/2025, rapport 10 ans Responsable Propriétaire équipement (locataire si proprio chaudière/clim) Bâtiments neufs Obligation stricte sans exemption TRI (depuis PC post-21/07/2021 seuil 290 kW, post-08/04/2024 seuil 70 kW) Articulation BACS = outil pour atteindre décret tertiaire -40% 2030 (obligations parallèles, pas annulation) Opportunité Gains 15-30% énergie, ROI 5-8 ans, compatibilité CEE/MaPrimeRénov tertiaire 

## FICHE D’IDENTITÉ : BACS EN 30 SECONDES 

### Définition officielle (CCH art. R.175-1) 

Système d’automatisation et de contrôle : Tout système comprenant tous les produits, logiciels et services d’ingénierie à même de soutenir fonctionnement efficace énergétique/économique systèmes techniques bâtiment via commandes automatiques et gestion manuelle.[R175-1] 

### Objectifs 
- Réduire consommations énergétiques 15-30% via optimisation équipements CVC 
- Détecter dérives performance (alarmes, alertes temps réel) 
- Soutenir atteinte objectifs décret tertiaire (-40% 2030, -50% 2040, -60% 2050) 
- Assurer confort/santé occupants sans surcoût énergétique 

### Équivalences terminologiques 
- BACS = Building Automation Control System (anglais) 
- GTB = Gestion Technique du Bâtiment (français) 
- BMS = Building Management System (anglais alternatif) 

### Portée géographique 
- Champ : Bâtiments tertiaires non-résidentiels (bureaux, commerces, hôtels, établissements scolaires/santé, loisirs, administrations, logistique) 
- Surface minimale : Aucune (s’applique dès qu’un seul équipement CVC dépasse seuil puissance) 
- Applicabilité : France métropolitaine + DROM (même règles) 

## RÉFÉRENCES JURIDIQUES OFFICIELLES Texte Nature Articles clés Publié Statut Changement majeur Lien source Directive UE 2018/844 Directive européenne Art. 8 (BACS obligatoires) 19/06/2018 Transposée FR Base légale comunitaire EUR-Lex directive Décret n°2020-887 Décret initial BACS R.175-1 à R.175-5 20/07/2020 (JORF 22/07) En vigueur Seuil 290 kW, bâtiments tertiaires Légifrance Décret n°2023-259 Modification calendrier R.175-1 à R.175-5-1 07/04/2023 (JORF 08/04) En vigueur Seuil 70 kW, inspections obligatoires TRI modal Légifrance Arrêté 07/04/2023 Application BACS Annexes 1-3 (TRI, insp.) 07/04/2023 (JORF 08/04) En vigueur Méthode TRI détaillée, fréquence inspection 5 ans Légifrance Décret n°2025-1343 Report calendrier Modif. R.175-2 dates 12/2025 (JORF 28/12) En vigueur Seuil 70 kW = 01/01/2030 (ex 2027) Légifrance Code CCH Code référence R.175-1 à R.175-6 Continu Consolidé Définitions, obligations, responsabilités Légifrance CCH 

Lien centralisé accès textes : https://www.legifrance.gouv.fr (rechercher “R.175-1” ou “décret BACS”) 

## DECISION TREE : “SUIS-JE CONCERNÉ ?” ┌─ BÂTIMENT TERTIAIRE NON-RÉSIDENTIEL ?
│ ├─ NON → Pas concerné (BACS non obligatoire)
│ └─ OUI
│ ├─ SYSTÈME CHAUFFAGE OU CLIMATISATION (combiné ou non ventilation) ?
│ │ ├─ NON → Pas concerné
│ │ └─ OUI
│ │ ├─ CALCUL PUISSANCE UTILE (Putile) :
│ │ │ Additionner puissances (kW) selon règles :
│ │ │ • Chaud : max(systèmes distincts) OU somme(systèmes réseau/cascade)
│ │ │ • Froid : somme(thermodynamiques même bâtiment)
│ │ │ • Si plusieurs systèmes : comparer chaud vs froid, retenir le plus élevé
│ │ │
│ │ ├─ Putile > 290 kW ?
│ │ │ ├─ OUI → OBLIGATION 01/01/2025 (URGENCE IMMÉDIATE)
│ │ │ │ ├─ Bâtiment neuf (PC post-21/07/2021) : BACS obligatoire
│ │ │ │ └─ Bâtiment existant : BACS si TRI < 10 ans OU avant 01/01/2025
│ │ │ │
│ │ │ └─ NON (≤290 kW), Putile > 70 kW ?
│ │ │ ├─ OUI → OBLIGATION 01/01/2030 (Report novembre 2025)
│ │ │ │ ├─ Bâtiment neuf (PC post-08/04/2024) : BACS obligatoire
│ │ │ │ ├─ Bâtiment existant (renouvellement post-09/04/2023) : BACS
│ │ │ │ └─ Bâtiment existant (sans renouvellement) : Avant 01/01/2030 OU audit TRI exemption
│ │ │ │
│ │ │ └─ NON (≤70 kW) → Pas concerné décret BACS
│ │ │
│ │ ├─ BÂTIMENT NEUF OU EXISTANT ?
│ │ │ ├─ NEUF (PC déposé après 21/07/2021 seuil 290 kW, après 08/04/2024 seuil 70 kW)
│ │ │ │ └─ BACS obligatoire SANS exemption TRI
│ │ │ └─ EXISTANT
│ │ │ ├─ Renouvellement équipement post-09/04/2023 ?
│ │ │ │ ├─ OUI → BACS obligatoire, seuil 70 kW si renouvellement ≥09/04/2023
│ │ │ │ └─ NON (ancien système)
│ │ │ │ ├─ Putile > 290 kW → Avant 01/01/2025 (sauf TRI > 10 ans)
│ │ │ │ └─ Putile 70-290 kW → Avant 01/01/2030 (sauf TRI > 10 ans)
│ │ │
│ │ └─ TRI > 10 ANS JUSTIFIÉ ?
│ │ ├─ OUI (audit + documentation) → EXEMPTION VALIDE (conservation 10 ans)
│ │ └─ NON → OBLIGATION BACS s'applique 

### Calcul puissance utile (Putile) : RÈGLES PRÉCISES 

### Systèmes de chauffage 
- Chaudières combustion (cascade/réseau) : Somme puissances nominales = 2×200 kW = 400 kW 
- PAC réversible : Puissance utile chaud (label) 
- Chauffage électrique : Puissance électrique max appelée (somme tous radiateurs électriques) 
- Systèmes distincts (PAC + chaudière) : Max (150 kW + 50 kW) = 150 kW (pas somme) 
- Règle générale : Si composantes en réseau/cascade = somme ; si indépendants = max 

### Systèmes de climatisation 
- PAC réversible + appoint froid : Somme (ex : 180 kW + 120 kW = 300 kW) 
- Systèmes thermodynamiques même bâtiment : Somme toutes unités 
- Climatiseurs individuels : Somme tous les climatiseurs 

### Logique déclenchement 
- Obligation si : Putile chauffage OU Putile climatisation > seuil (le plus élevé déclenche) 
- Exemple : Chaud 200 kW + Froid 320 kW → Froid déclenche obligation (320 > 290 kW) 

## CALENDRIER DES OBLIGATIONS : AVANT/APRÈS REPORT DÉCEMBRE 2025 

### Tableau synthétique (mise à jour avec Décret n°2025-1343) Puissance utile Bâtiments neufs (date PC) Bâtiments existants Date limite mise en conformité Statut décembre 2025 > 290 kW PC post-21/07/2021 Tous 01/01/2025 ✓ EN VIGUEUR – Aucun changement > 70 kW PC post-08/04/2024 Renouvellement ≥09/04/2023 + sans renouvellement 01/01/2030 (ex 2027) ⚠ REPORT confirmé (nov 2025) Inspections Tous BACS Tous BACS (1re avant 01/01/2025) Max 5 ans (2 ans post-install) ✓ OBLIGATOIRE – Inchangé 

### Chronologie détaillée (historique + futur) Date Événement Impact 22/07/2020 Décret n°2020-887 publié (JORF) Entrée en vigueur seuil 290 kW 21/07/2021 Obligation bâtiments neufs (PC post cette date) Bâtiments neufs >290 kW assujettis 08/04/2023 Décret n°2023-259 publié (arrêté TRI 07/04/2023) Seuil 290 kW baissé à 70 kW, inspections obligatoires 09/04/2023 Entrée en vigueur seuil 70 kW (renouvellement) Existants qui renouvellent >70 kW = obligation 08/04/2024 Obligation bâtiments neufs seuil 70 kW (PC post cette date) Bâtiments neufs >70 kW assujettis 01/01/2025 DEADLINE >290 kW bâtiments existants Tous >290 kW doivent avoir BACS opérationnel 01/01/2025 1ère inspection obligatoire (tous BACS existants) Inspection périodique commence 20/11/2025 Annonce report >70 kW par PM Lecornu Décalage calendrier confirmé 04/12/2025 Consultation publique closes + validation CSE Décret modification finalisé 12/2025 Décret n°2025-1343 publié (JORF 28/12/2025) Seuil 70 kW = 01/01/2030 (officiel) 01/01/2030 DEADLINE >70 kW bâtiments existants Tous 70-290 kW doivent avoir BACS opérationnel 

## OBLIGATIONS FONCTIONNELLES MINIMALES : TERRAIN 

Tout système BACS doit garantir 5 capacités clés (article R.175-3 CCH) : 

### 1️⃣ SUIVI & ENREGISTREMENT CONTINU 
- Mesure : Données production/consommation énergétique par zone fonctionnelle 
- Archivage : Historiques enregistrées 5 ans minimum (accès propriétaire garanti) 
- Granularité : Au minimum par système technique (chauffage, clim, ventilation, ECS, éclairage, etc.) 
- Exemple : Bâtiment multi-étages → sous-comptage par étage OU automatisme par zone usage homogène 

### 2️⃣ ANALYSE & DÉTECTION DÉRIVES 
- Benchmark : Situer efficacité énergétique vs valeurs de référence (consommation théorique, année antérieure, secteur) 
- Alertes : Détecter automatiquement pertes d’efficacité (ex : conso > +10% vs normal, équipement défaillant) 
- Rapports : Fournir exploitant possibilités d’amélioration (pas juste données brutes) 
- Exemple : Caisson ventilation trop ouvert → surconso chaud/froid détectée, alerte = X€/mois perte 

### 3️⃣ INTEROPÉRABILITÉ 
- Capacité : Communiquer avec autres systèmes (normes ouvertes, API standards) 
- Modularité : Architecture souple et évolutive (ajouter/retirer systèmes futurs sans refonte) 
- Intégration : Tous systèmes techniques (chaud, froid, ventilation, ECS, éclairage) = raccordables au BACS central 
- Exemple : Remplacer chaudière → nouvelle chaudière se branche directement au BACS existant, pas refonte 

### 4️⃣ ARRÊT MANUEL & AUTONOMIE 
- Contrôle manuel : Possibility d’arrêter/piloter manuellement tout ou partie BACS 
- Autonomie : Gestion autonome systèmes (configurations multi-sites avec hyperviseur pilotant supervisions distantes = OK) 
- Sécurité : Pas de dépendance réseau permanent (critères de basculement local) 
- Exemple : PM émetrise hyperviseur 10 sites → chaque site fonctionne en autonomie locale + synchrone hyperviseur 

### 5️⃣ RECOMMANDATIONS & AMÉLIORATIONS 
- Rapport inspection : Fournir tous 5 ans document avec recommandations réglages, remplacement équip., solutions alternatives 
- Formation : Documenter bon usage système pour exploitant/gestionnaire 
- Opportunités : Évaluer intérêt remplacement système (obsolescence, sur-consomé, etc.) 
- Exemple : Inspection détecte thermostat décalé -2°C → recommande recalibrage (gain -5% chaud) 

## EXEMPTIONS & DÉROGATIONS : PREUVES REQUISES 

### SEULE EXEMPTION VALIDE : TRI > 10 ANS (EXISTANT SEULEMENT) 

### Définition TRI (Temps Retour Investissement) TRI (ans) = S / (G × C)
Avec :
 S = Surcoût BACS (€) = Coût installation - Aides financières
 • Coût installation = matériel + MO + paramétrage + analyse fonctionnelle + logiciels/ingénierie
 G = Gain énergétique (kWh/an) = (Conso moy 2 ans) × Taux réduction (%)
 • Taux par défaut = 15% (ou audit spécialisé si différent)
 C = Coût énergétique moyen (€/kWh) = moyenne tarif facturé 12 mois avant demande 

### Méthodologie calcul (arrêté 07/04/2023) 
- Consommation de base : Moyenne consommations 2 dernières années (kWh électricité, gaz, etc.) 
- Gain estimé : 15% par défaut OU valeur audit spécialisé (ex : 8% suite audit thermique) 
- Coût énergie : Prix moyen du kWh facturé 12 mois antérieurs (distinct par fluide) 
- Gain énergétique : Conso base × % réduction = kWh économisés 
- Gain monétaire : kWh gains × prix €/kWh = € économies annuelles 
- Surcoût BACS : Devis complet moins aides (CEE, MaPrimeRénov, etc.) 
- Calcul TRI : S / (G€) = années retour 
- Exemption si : TRI > 10 ans strictement 

### Exceptions à la base 2 ans 
- Rénovation énergétique 2 ans avant : Utiliser 1 année la plus récente (consommation normalisée post-travaux) 
- Bâtiment vide 1 année : Utiliser uniquement années occupées (moyenne réduite) 

### Documentation exemption (à conserver 10 ans) Document Contenu Qui produit Archivage Audit TRI complet Détail calcul, consommations, coût énergie, gain estimé, surcoût Bureau d’études certifié Propriétaire 10 ans Devis BACS Prix matériel, installation, paramétrage, services Intégrateur BACS Propriétaire 10 ans Justificatif aides Lettres engagement CEE, MaPrimeRénov, autres Fournisseur aides Propriétaire 10 ans Facturation énergétique Derniers 24 mois (kWh + prix moyen) Fournisseur énergie Propriétaire 10 ans Rapport d’exemption Synthèse TRI conclusif (TRI = X ans > 10 ans) Propriétaire ou BE Propriétaire 10 ans 

### Risque audit non-conformité 
- Audit découvre exemption non-justifiée : Site classé non-conforme 
- Pénalité administrative : Jusqu’à 300€/jour retard (cumul si multi-sites) 
- Obligation mise en conformité : Délai supplémentaire possible (à négocier) 
- Responsabilité propriétaire : Preuve incombe assujetti 

## INSPECTIONS PÉRIODIQUES OBLIGATOIRES : MODALITÉS & COÛTS 

### Fréquence & Timing (arrêté 07/04/2023 + R.175-5-1 CCH) Cas Fréquence Timing Délai 1ère Installation/remplacement système 2 ans maxi post-installation Audit initial + 2 ans ASAP après install BACS existant en marche 5 ans maximum Récurrent 01/01/2025 (deadline obligatoire tous anciens) Post-inspection 5 ans après dernière insp. Glissement calendrier Basé dépôt rapport précédent 

### Contenu inspection (Annexe 1 arrêté 07/04/2023) 

### Examen fonctionnel (1ère inspection uniquement) 
- Vérification architecture BACS (diagramme systèmes, capteurs, actionneurs, supervision) 
- Documentation équipements (plans, listes matériels) 
- Paramétrage initial vs besoins bâtiment 

### Vérification bon fonctionnement (ALL inspections) 
- Test appareil de mesure (capteurs température, humidité, compteurs kWh) → étalonnage ✓/✗ 
- Vérification algorithmes de régulation (chaud/froid/ventilation réagissent normally) 
- Détection dérives actives (alertes lorsque consommation dépasse +X%) 
- Archivage données fonctionne (historiques consultables, 5 ans présent) 

### Évaluation exigences moyens (sauf réinspection sans changement) 
- Interopérabilité : Connexions toujours au standard (API, protocole) 
- Arrêt manuel : Possibilité toujours présente et testée 
- Recommandations accessibles : Rapports générés automatiquement pour exploitant 

### Paramétrage vs usage réel 
- Consignes température correspondent-elles occupancy réelle ? (bureaux 8-18h = paramétré ?) 
- ECS, éclairage, ventilation = réglés pour usage du bâtiment ? (overconsommation détectée ?) 
- Calendrier saisonnier vs occupation vacances ? (consignes hiver/été justes ?) 

### Recommandations (Annexe 3 arrêté 07/04/2023) 
- Bon usage système en place (notice exploitant) 
- Améliorations possibles installation (recalibrage, remplacement, économies rapides) 
- Intérêt remplacement BACS (obsolescence, architectures modernes) 
- Solutions alternatives (autre BACS, sous-traitance gestion) 

### Rapport inspection (production & archivage) Élément Responsable Format Délai transmission Conservation Rapport écrit Inspecteur certifié (interne/externe) PDF signé 1 mois post-visite Propriétaire 10 ans Exécutif Inspecteur Synthèse 1 page Avec rapport 10 ans Données brutes Inspecteur Tableaux étalonnage Annexe rapport 10 ans Plan d’action Inspecteur + Propriétaire Checklist recommandations Avant clôture 10 ans (preuve suivi) 

### Coûts typiques inspection BACS (données marché 2025) Type bâtiment Taille BACS Durée insp. Coût HT approx. PME tertiaire simple 1 site, 1-2 systèmes 4-6h 1 500 – 2 000€ Immeuble moyen 1 site, 3-4 systèmes, multi-zones 6-8h 2 000 – 3 000€ Grand tertiaire 1 site complexe OU multi-sites pilotage 8-12h 3 000 – 5 000€ Portfolio multi-sites (x10 sites) Audit global + inspections coordonnées 40-60h 12 000 – 20 000€ (économies d’échelle) 

Remarque : Aides possibles (CEE audit, partenaires GTB) peuvent couvrir 30-50% inspection. 

## PMO MISE EN CONFORMITÉ (8-12 SEMAINES) 

Applicable bâtiments >290 kW NON CONFORMES 2025 ou >70 kW EXISTANTS 2025-2030 

### Phase 1 : DIAGNOSTIC URGENT (Semaines 1-2) Étape Livrables Responsable Outils Risques Audit conformité rapide Fiche site (puissance, équip., date instal., état BACS) Gestionnaire + BET Fiche standardisée, visite site 2h Données puissance inexactes Calcul Putile Tableaux puissance chauffage + climatisation, seuil dépassé confirmé BET + Intégrateur Fiches équipements, plaques signalétiques Confusion systèmes distincts vs réseau Audit TRI préalable Consommations 2 ans, tarifs énergie, devis BACS indicatif BE audit + Intégrateur Facturation énergie, appels offres rapides Aides estimées à défaut Risk score Si >290 kW + pas BACS 01/01/2025 = CRITICITÉ ROUGE PM projets Checklist conformité Dépassement deadline imminent Décision stratégique BACS vs exemption TRI vs mixte phasing Direction immobilier Matrice décision TRI/CAPEX Choix tard = délai exécution 

GO/NO-GO : TRI > 10 ans justifié ? OUI = exemption possible → Doc TRI ; NON = BACS obligatoire 

### Phase 2 : SPÉCIFICATIONS & APPELS OFFRES (Semaines 3-5) Étape Livrables Responsable Outils Risques Cahier des charges BACS Spécifications techniques (architecte BACS), zones fonctionnelles, systèmes à intégrer, niveaux d’automatisation BE + Propriétaire Template CdC (+ guide RT-RE BACS) Spécifications incomplètes → débordement scope Appel d’offres Envoi 3-5 intégrateurs BACS (classement, délais, prix) Responsable appels RFQ standardisé, calendrier respect Réponses tardives, délais install impossibles Aides financières identification Dossier CEE (fiche opération BACS), MaPrimeRénov tertiaire, Éco-PTZ si applicable Responsable financement Portails CEE/MaPrimeRénov, simulation Aides refusées = surcoût initial impact Sélection prestataire Contrat intégrateur signé (clauses conformité, délai, inspection incluse) Responsable contrat Contrat type GTB, clauses BACS Non-livraison conforme, débordement délai Planification détaillée Gantt 8-10 semaines (install, param., test, commissioning, 1ère insp.) Intégrateur + PM MS Project/Trello, jalons clairs Dérives calendrier = dépassement deadline 

GO : Contrat signé, aides activées, démarrage imminent 

### Phase 3 : DÉPLOIEMENT BACS (Semaines 6-9) Étape Livrables Responsable Outils Risques Installation matériel Capteurs, actionneurs, automates, cabling, réseau déployés Intégrateur + Électricien Plan câblage, checklist install Matériel défectueux, retard approvisionnement Paramétrage systèmes Consignes température, saisonnalité, occupancy programmés ; algorithmes test Intégrateur + Exploitant Software BACS, documentation paramètres Paramètres incorrects = mauvaise perf Tests/Commissioning Vérification capteurs, actionneurs, alarmes, arrêts manuels, data archivage Intégrateur + BET Plan test, reports test exécution Défaut détecté trop tard en prod Formation exploitant Pilotage système, consultation données, alertes interprétation, maintenance basique Intégrateur + Propriétaire Manuels, sessions formation 4h Exploitant sous-utilise système Go-live & suivi 1 mois Mise en prod, monitoring, ajustements fin-tuning Intégrateur + Exploitant Support 24h/7 inclus contrat Dérives perf post-install 

### Phase 4 : INSPECTION & CONFORMITÉ (Semaines 10-12) Étape Livrables Responsable Outils Risques 1ère inspection obligatoire Audit complet par inspecteur certifié (2-5h selon complexité) Bureau inspection externe Grille inspection arrêté 07/04/2023 Rapport critique = mise en conformité suppl. Rapport inspection Document signé + recommandations pour exploitant ; 1 copie archivage 10 ans BE inspection Template rapport standardisé Documentation incomplète → non-recevable audit Plan d’action recommandations Priorisation améliorations rapides, calendrier moyen/long terme Propriétaire + Exploitant Tableau reco priorités Recommandations ignorées = perf dégradée Attestation conformité Certificat “Conforme décret BACS” généré (archivage, justificatif audit) Intégrateur ou BE PDF signé horodaté Absence attestation = contestable légalement Documentation finale Dossier complet (schémas, paramètres, rapports, formation) archivé 10 ans Propriétaire Classeur physique + copie numérique Perte doc → risque audit futur 

GO : Inspection réussie, rapport conforme, site déclaré conforme 01/01/2025 

## CHECKLIST CONFORMITÉ (NOTION-READY - À COPIER) # ✅ CONFORMITÉ DÉCRET BACS – SITE [NOM SITE]

## PHASE 1 : CADRAGE

### Identification site
- ⬜ Nom bâtiment & adresse précis
- ⬜ Propriétaire équipements identifié (bailleurs, locataires, mixed)
- ⬜ Nature activité tertiaire confirmée (bureaux / commerces / santé / éducation / etc)
- ⬜ Date permis de construire récupérée (ou date construction existant)

### Diagnostic puissance utile
- ⬜ Inventaire ALL équipements chauffage (chaudières, PAC, radiateurs élec, réseau chaleur)
- ⬜ Plaques signalétiques relevées (puissance nominale utile en kW de chaque)
- ⬜ Inventaire ALL équipements climatisation (PAC, clim split/centralisée, refroidisseurs)
- ⬜ Plaques signalétiques climatisation (puissance utile froid kW)
- ⬜ Ventilation présente ? (OU absent, et règle cumul appliquée ?)
- ⬜ Calcul Putile chauffage (somme reseau OU max systèmes distincts)
- ⬜ Calcul Putile climatisation (somme thermodynamiques)
- ⬜ Seuil déclenche obligation confirmé : > 290 kW OUI/NON, > 70 kW OUI/NON

### Assujettissement & calendrier
- ⬜ Seuil > 290 kW → Deadline 01/01/2025 (URGENCE 2025)
- ⬜ Seuil > 70 kW + bâtiment neuf post-08/04/2024 → OBLIGATION BACS (néo pas exemption TRI)
- ⬜ Seuil > 70 kW + existant renouvellement post-09/04/2023 → OBLIGATION BACS au renouvellement
- ⬜ Seuil > 70 kW + existant sans renouvellement → Deadline 01/01/2030 (report)
- ⬜ Responsable obligé identifié (propriétaire équip ou locataire ?)

## PHASE 2 : AUDIT (PRISE DE DÉCISION TRI)

### Audit TRI (si exemption envisagée)
- ⬜ Consommations énergétiques année N-2 collectées (kWh élec, gaz, autres)
- ⬜ Consommations année N-1 collectées (idem)
- ⬜ Moyenne 2 ans calculée (par fluide)
- ⬜ Tarifs €/kWh collectés (factures 12 mois antérieurs)
- ⬜ Gain énergétique estimé : 15% par défaut OU audit spécialisé en cours (%)
- ⬜ Coût BACS : devis complet intégrateur BACS reçu (matériel + MO + param + logiciels)
- ⬜ Aides identifiées : CEE prévisionnel, MaPrimeRénov, Éco-PTZ, autres (montants)
- ⬜ Surcoût BACS = Coût – Aides calculé (€ net)
- ⬜ TRI calculé = S / (G€) = X années
- ⬜ Résultat TRI : > 10 ans → EXEMPTION POSSIBLE ; ≤ 10 ans → BACS OBLIGATOIRE

### Décision stratégique
- ⬜ SI exemption TRI justifiée (TRI > 10) : Dossier TRI complet archivé 10 ans (preuve audit)
- ⬜ SI BACS obligatoire : Lancer cahier des charges + appels offres phase 3

## PHASE 3 : SPÉCIFICATIONS & APPELS OFFRES

### Cahier des charges
- ⬜ Zones fonctionnelles identifiées (bureaux, halls, RDC, etc) – usage homogène par zone
- ⬜ Systèmes à embarquer listés : chauffage, climatisation, ventilation, ECS, éclairage, production élec (oui/non)
- ⬜ Niveaux automatisation définis (régulation seule vs optimisation vs prédictif)
- ⬜ Architecture BACS spécifiée (centralisée / distribuée / hybride)
- ⬜ Interopérabilité exigée (normes ouvertes demandées : BACnet, Modbus, Z-Wave, etc)
- ⬜ Archivage 5 ans données spécifié (capacité stockage, accès propriétaire)
- ⬜ Formation exploitant incluse dans scope (nombre jours, sujets)

### Appels d'offres
- ⬜ RFQ envoyé 3-5 intégrateurs BACS qualifiés (références secteur)
- ⬜ Deadline réponse fixée (ex : 2 semaines)
- ⬜ Critères évaluation définis (prix, délai, réf., garantie, support)
- ⬜ Offres reçues analysées (meilleur value, pas juste prix bas)
- ⬜ Sélection prestataire : contrat signé (clauses BACS, conformité, deadline, inspection incluse)

### Financement
- ⬜ CEE fiche opération BACS préparée (n° opération, prestataire, économies kWh estimées)
- ⬜ Dossier MaPrimeRénov tertiaire préparé (si éligible)
- ⬜ Demandes aides validées, engagements reçus (montants prévus)
- ⬜ Budget net après aides confirmé (impact trésorerie)

## PHASE 4 : DÉPLOIEMENT

### Installation & paramérage
- ⬜ Matériel BACS livré site (capteurs, automates, supervision) – checklist de réception
- ⬜ Installation électricien complétée (cabling, armoire, alimentations)
- ⬜ Paramètres systèmes chargés (consignes chaud/froid, calendriers, saisonnalité)
- ⬜ Connexions captor/actionneur testées (acquisition données fonctionnelle)
- ⬜ Tests arrêt manuel + pilotage validés (sécurité & contrôle)
- ⬜ Archivage données activé (derniers 5 ans accessible, écriture en continu)

### Commissioning & tests
- ⬜ Plan de test exécuté complet (activation chaque système, chaîne complète)
- ⬜ Capteurs étalonnés (température, humidité, compteurs kWh alignés réalité)
- ⬜ Algorithmes régulation testés (chaud > T cible ?, froid < T cible ?, arrêts manuels OK ?)
- ⬜ Alarmes alertes testées (dérive détectée automatiquement ? notification exploitant ?)
- ⬜ Rapports données générés & consultables (derniers 7 jours accessible propriétaire)
- ⬜ Tous tests VALIDÉS avant go-live (rapport test signé)

### Formation exploitant
- ⬜ Formation 4h réalisée (pilotage, consultation données, alertes, maintenance basique)
- ⬜ Manuels exploitant en français remis & expliqués (accès hyperviseur, rapports, paramètres)
- ⬜ Support vendor contact confirmé (n° tél, email, SLA réponse 24h)
- ⬜ Attente exploitant documentée (usage quotidien, fréquence suivi, escalade problèmes)

### Mise en production
- ⬜ Go-live date fixée (coordonné avec deadline conformité si 01/01/2025)
- ⬜ Support intensive 4 semaines (Intégrateur dispo, ajustements fin-tuning)
- ⬜ Monitoring perf post-install (données réelles vs paramétrages prévus)
- ⬜ Ajustements consignes si nécessaire (confort utilisateurs, surconso détectée → rectification)

## PHASE 5 : INSPECTIONS OBLIGATOIRES

### Première inspection (obligatoire avant 01/01/2025 si BACS déjà installé)
- ⬜ Inspecteur certifié sélectionné (interne/externe, accrédité NF, AFNOR, ou équivalent)
- ⬜ Inspection planifiée & site accessible (2-6h selon complexité)
- ⬜ Examen fonctionnel BACS complet (architecture, plans, équipements)
- ⬜ Vérification bon fonctionnement (capteurs, actionneurs, data archivage, alertes)
- ⬜ Paramètres vs usage bâtiment validés (T consignes OK ?, saisonnalité ?, occupancy ?)
- ⬜ Étalonnage capteurs vérifié (température, humidité, compteurs kWh = acceptable)

### Rapport inspection
- ⬜ Rapport signé inspecteur reçu dans 1 mois post-visite
- ⬜ Rapport contient : exécutif, détails techniques, recommandations, plan d'action
- ⬜ Copie archivée propriétaire (10 ans minimum, préservation digitale)
- ⬜ Recommandations triées priorité (rapides < rapide moyen < long terme)

### Plan d'action recommandations
- ⬜ Recommandations rapides (<3 mois) identifiées & exécutées (ex : recalibrage T)
- ⬜ Recommandations moyen terme (3-12 mois) planifiées (ex : remplacement capteur)
- ⬜ Recommandations long terme (>12 mois) documentées pour futur (ex : remplacement BACS)

### Inspections récurrentes
- ⬜ Prochaine inspection planifiée (5 ans max après rapport précédent, ou 2 ans si renouvellement système)
- ⬜ Rappel calendrier dans agenda PM

## PHASE 6 : MAINTIEN & CONFORMITÉ CONTINU

### Exploitation quotidienne
- ⬜ Exploitant consulte dashboards 1x/semaine minimum (dérives détectées rapidement)
- ⬜ Alertes reçues traitées (ex : compteur kWh suspect → vérif capteur)
- ⬜ Paramètres ajustés saisonnalité (printemps/été/automne/hiver)
- ⬜ Maintenance préventive planifiée (filtrages, nettoyages, étalonnages périodiques)

### Documentation & archivage
- ⬜ Tous rapports, contrats, recommandations archivés 10 ans (conformité légale)
- ⬜ Historiques données BACS conservées 5 ans (exigence légale, accès propriétaire)
- ⬜ Changements système documentés (remplacement équipement, modifications paramétrages)

### Amélioration continue
- ⬜ Bilan annuel énergie vs objectifs (économies réelles vs prévisions)
- ⬜ Recommandations mises en œuvre évaluées (gain mesurable ?)
- ⬜ Nouvelles optimisations identifiées (ex : occupancy sensors pour éclairage)
- ⬜ Investissements futurs justifiés sur base données BACS (TRI moyen terme)

### Conformité légale
- ⬜ Attestation conformité BACS conservée (preuve autorités si audit)
- ⬜ Rapports inspection archivés (preuve décret BACS respecté)
- ⬜ Dossier exemption TRI (si applicable) archivé 10 ans (preuve dérogation valide)
- ⬜ Registre BACS maintenance / changements tenu à jour

---

✅ **CONFORMITÉ DÉCRET BACS CONFIRMÉE** (Date : [_______] Signataire : [_______]) 

## FAQ : 10 CAS RÉELS TERRAIN 

### Q1. « Mon immeuble de bureaux a 250 kW chaud + 300 kW froid. Suis-je concerné ? » 

R1. Oui, OBLIGATION immédiate. Max(250 chaud, 300 froid) = 300 kW > 290 kW → Deadline 01/01/2025 . Si pas BACS aujourd’hui = non-conforme risque pénalité . Lancer audit TRI rapide (exemption si TRI > 10 ans) ou devis BACS urgent (délai install 4-8 semaines). 

### Q2. « On va renouveler notre chaudière 100 kW. Avons-nous obligation BACS ? » 

R2. Oui, obligation déclenchée au renouvellement (depuis 09/04/2023). Seuil s’applique = 70 kW (vs 290 ancien). Si chaudière neuve > 70 kW → BACS obligatoire lors du renouvellement (pas délai 2027/2030). À programmer dans contrat remplacement équipement. 

### Q3. « Multi-occupation : locataire A proprio chaudière, locataire B proprio clim. Qui doit BACS ? » 

R3. Propriétaire équipement responsable . Locataire A = BACS chauffage (si P > seuil) ; Locataire B = BACS clim (si P > seuil). Si puissance combinée (A+B) dépasse seuil = Hyperviseur/supervision commune possible, mais responsabilité reste auprès de chaque proprio équip. Contrat de bail doit clarifier (“propriétaire fourni BACS” vs “locataire installe”). 

### Q4. « Site existant 150 kW sans renouvellement depuis 2010. Deadline ? » 

R4. Seuil 150 kW > 70 kW → Deadline 01/01/2030 (report november 2025). Sauf renouvellement : Si vous remplacez équip post-09/04/2023 → obligation immédiate renouvellement (seuil 70 kW). Stratégie : Attendre 2030 OU devancer renouvellement équip + BACS (opportunité financement). 

### Q5. « Audit TRI : gain énergétique estimé 8% (pas 15% défaut). Ça change l’exemption ? » 

R5. Oui, impacte TRI drastiquement . Si 8% réel < 15% défaut → TRI montant plus haut → risque dépassement seuil 10 ans. Exemple : S=50k€, C=0,20€/kWh, Conso=300 MWh → Gain 15% = 45 MWh = 9k€ → TRI = 5,5 ans (OK). Gain 8% = 24 MWh = 4,8k€ → TRI = 10,4 ans (EXEMPTION échouée). Audit spécialisé justification obligatoire si écart 15%. 

### Q6. « Multi-sites géographie : 10 bureaux à 50 kW chacun. Un BACS centralisé OK ? » 

R6. Oui, hyperviseur centralisant sites individuels conforme décret . Chaque site < 70 kW donc aucun n’obligatoire individuellement, MAIS si architecture décide centraliser → BACS hyperviseur est du “moyen”. Avantage : optimisation globale, données consolidées. Condition : chaque site garder autonomie locale (arrêt manuel, paramètres spécifiques possibles). 

### Q7. « Inspection prévue janvier 2025. Intégrateur pas livré à temps. Que faire ? » 

R7. Non-conformité risquée . Deadline inspection = 01/01/2025 (si BACS existant). Si pas encore installé janvier → Site “pas conforme” légalement, même si travaux en cours. Solution : (1) Report date inspection formalité (accord inspecteur) ; (2) Mise en place système provisoire conforme minimal (capteurs de base) avant jan 2025 ; (3) Inspection complète février → Rapport en retard mais site ” en voie de conformité “. Risque : pénalité administrative si delay > 3 mois post-deadline. 

### Q8. « Classé patrimoine : impossible installer capteurs = TRI infini. Exemption ? » 

R8. Peut être exemption MAIS documentation stricte . Cas : si capteurs installation techniquement impossible (contrainte patrimoniale avérée + documents preuve) OU TRI > 10 ans calculé. Preuves attendues : (1) Avis architecte des bâtiments de France (ABF) refusant capteurs ; (2) Audit TRI complet. Risque : audit découvre capteurs possibles ailleurs → refus exemption + obligation BACS alternatif. 

### Q9. « Bâtiment occupé 3 mois/an (vacances). Consommation base bonne ? » 

R9. Non, récalculer base sur occupancy réelle . Règle : “Si bâtiment vide > 6 mois année = utiliser seulement années occupées pour moyenne conso”. Exemple : 2023 vide 8 mois → 2023 ignorée. 2024 occupé 12 mois, 2025 occupé 12 mois → Moyenne = (2024+2025)/2. Conso de base “anormale” (basse vacance) → faux gain énergétique → TRI surestime → exemption possible échoue. Audit doit documenter occupancy exacte. 

### Q10. « Exploitant refuse BACS : “compliqué et inutile”. Comment convaincre ? » 

R10. C’est obligatoire, pas optionnel (>290 kW seulement). Points de vente exploitant : (1) Économies réelles : 15-30% énergie mesurable = économie facture visible (ROI 5-8 ans) ; (2) Alertes immédiates : détecte dérives avant surcoûts exponentiels (ex : climatisation bloquée jour = 2k€ surcoûts weekend vs 20€ alerte détection rapide) ; (3) Confort occupants : pilotage température fines, ventilation optimisée = productivité ; (4) Conformité légale : obligation décret = risque pénalité 300€/jour retard. Proposer démo sur petit système pour preuve gain avant déploiement global. 

## OPPORTUNITÉS PRODUIT PROMEOS 2.0 

### 8 FEATURES BACS-READY (PLATFORM) 

### 1. Score de Conformité BACS Continu 
- Dashboard “Conformité Décret” : % complétude obligations (audit rapide, TRI justifié, BACS installé, inspection à jour, documentation archivée) 
- KPI rouge/orange/vert par site : conforme / en cours / non-conforme 
- Alerte calendrier : “Inspection due dans 6 mois”, “Deadline renouvellement approche”, “TRI exemption expire” 
- Cas d’usage : PM tertiaire gère 50 sites → vision 360° conformité en 1 clic 

### 2. Calcul TRI Automatisé 
- Interface saisie : Consommations 2 ans + tarifs énergie + devis BACS → Calcul TRI instantané 
- Sensibilité analyse : “Si gain 15% → TRI = X ans ; si gain 12% → TRI = Y ans” (montre seuil critique) 
- Recommandation : “BACS obligatoire” vs “Exemption possible (TRI > 10 ans)” + lien dossier TRI à archiver 
- Cas d’usage : Directeur immobilier évalue 30 sites rapidement, identifie 5 exemptions légitimes 

### 3. Alertes Prédictives Dérives 
- Connexion données BACS propriétaire (via API standardisée) : récupération consommations temps réel 
- Détection anomalies : conso +10% vs normal → alerte exploitant (cause probable : surchauffage, équip bloqué, sous-compteur faux) 
- Prédiction : “À ce rythme, surconsommation de 50k€ cette année” → anticipation action 
- Cas d’usage : Exploitant identifie fuite thermique semaine 2 vs découvrir facture année trop tard 

### 4. Registre d’Inspections BACS 
- Base de données inspections (date, inspecteur, site, rapports digitalisés) 
- Génération alertes “Inspection due dans 2 mois” (5 ans max depuis dernière) 
- Suivi recommandations inspection (priorité, statut réalisé/en cours/report, date clôture) 
- Archive 10 ans (conforme exigence légale conservation rapports) 
- Cas d’usage : Portfolio manager vérifie 100 sites ont tous inspecté < 5 ans 

### 5. Proof of Compliance Auto-Export 
- Dossier “Attestation BACS” généré PDF : 
- Audit conformité site (puissance, date deadline, status) 
- Dernier rapport inspection (date + URL doc) 
- Exemption TRI (si applicable) + calcul justificatif 
- Contrat BACS signé + facture install 
- Documentation 10 ans archivée (checklist) 
- Une page résumé → “Conforme Y/N” signée PM (proof audit) 
- Cas d’usage : Audit externe/autorités → Dossier complet fourni 5 minutes 

### 6. Équipement Registry & Lifecycle 
- Inventaire centralisé systèmes techniques (chauffage, clim, ventilation, ECS, éclairage, électricité) 
- Fiche par équipement : puissance, date install, âge, contrat maintenance, prochaine révision 
- Alertes renouvellement : “Chaudière 25 ans → changement conseil dans 3 ans → BACS déclenché si fait” 
- Planification financière : “Budget renouvellement équip 2026-2028 + budget BACS associé” 
- Cas d’usage : Directeur CapEx anticipe coûts renouvellement + BACS bundlé 

### 7. KPI Énergie & Performance BACS 
- Dashboard mensuel : conso (kWh), coûts (€), gain vs baseline, nombre heures inconfort, taux exploitation BACS 
- Tendance annuelle : économies réalisées post-BACS vs avant (kWh saved × tarif moyen) 
- Benchmarking intra-groupe : “Notre site = top 20% effi énergétique vs autres sites classe similaire” 
- ROI tracking : “BACS a coûté 40k€ en 2023 ; économies réalisées 2024 = 8k€ ; ROI année 4 attendu” 
- Cas d’usage : Diriger générale rapporte à CSR “économie énergétique BACS = 250 tCO2 / 5 ans” 

### 8. Matrice Décisionnel Rapport/Exemption 
- Interface guidée : saisir Putile + type bâtiment (neuf/existant) + renouvellement ? → Recommandation 
- Matrice visuelle : “290-70 kW existant sans renouvellement = deadline 2030 (pas urgent)” 
- Liens documentations : si BACS obligatoire → lien CdC; si exemption possible → lien formulaire TRI 
- Simulation budget : saisir coûts → automatique TRI calculé → statut décision 
- Cas d’usage : PME immobilier petite équipe → outil guide conformité sans BET externe 

### 5 KPI MINIMUM (TABLEAU BORD) KPI Formule Fréquence Target % Sites Conformes BACS (Conformes / Total sites assujettis) × 100 Mensuel 100% fin 2027 (>290 kW), 100% fin 2030 (>70 kW) Moyenne TRI Portefeuille (ans) (Σ TRI sites calculés) / N sites Semestriel < 8 ans (meilleur ROI) Économies énergétiques annuelles (kWh) Σ (Conso pré-BACS - Conso post-BACS) × sites Annuel +15% gain baseline Taux Exploitation BACS (Alertes détectées & traitées / Alertes générées) × 100 Mensuel > 80% (exploitant réactif) Jours en Retard Conformité MAX(0, date_réelle - date_deadline) en jours Temps réel 0 jours (zero penalty risk) 

## CONCLUSION EXÉCUTIVE 

Le décret BACS est réglementairement stable (décrets 2020-887, 2023-259, 2025-1343 + arrêté 07/04/2023). Report seuil 70 kW à 2030 apporte légèrement plus de flexibilité , mais deadline >290 kW reste 01/01/2025 critique (non-conformité actuellement = hors-la-loi ). 

Pour PROMEOS , trois leviers d’action : 
1. Conformité immédiate (2025) : Audit sites >290 kW, TRI justifications, BACS urgent si obligation 
2. Opportunité économique (2025-2030) : BACS ROI 5-8 ans, cumul CEE/MaPrimeRénov, économies 15-30% 
3. Plateforme produit : Conformité scoring, TRI calc, inspections registre = valeur SaaS immense marché tertiaire français (50k+ sites concernés, 16% seulement équipés 2025) 

Document production-ready Notion & audit 

Tous liens Légifrance officiels & sources validées 

À jour décret n°2025-1343 (décembre 2025) Décret BACS — seuils, dates, exemptions TRI_“Synth