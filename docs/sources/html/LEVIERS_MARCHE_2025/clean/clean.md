État 2025, Leviers de Marché & Plan de Simplification (2026–2030) 

# 

# Autoconsommation Collective en France – État 2025, Leviers de Marché & Plan de Simplification (2026–2030) 

Dossier Stratégique & Feuille de Route PROMEOS 

## Executive Summary 

L’autoconsommation collective (ACC) en France connaît une croissance historique : 1 111 opérations actives et 161 MW en juin 2025, soit +144% en un an . Le cadre réglementaire s’assouplit (arrêté 21 février 2025 : seuils portés à 5–10 MW, périmètre géographique étendu, délais administratifs réduits), créant une fenêtre d’opportunité stratégique pour PROMEOS de se positionner comme “micro-fournisseur local augmenté”. 1 

Situation clé : 
- Marché: 1 700 producteurs, 10 600+ consommateurs, puissance moyenne 145 kVA/opération 2 
- Secteurs dominants : collectivités, bailleurs sociaux, parcs d’activités, particuliers (AMEP) 
- Freins opérationnels majeurs : montage PMO lourd (12–24 mois), manque d’automatisation (Excel + ressaisies), facturation manuelle, communication Enedis complexe 
- Leviers: APIs Enedis DataConnect/ACC, standardisation juridique, clés de répartition dynamiques, pilotage temps réel 

PROMEOS doit combiner trois briques (Data & Conformité, ACC Starter, ACC Ops) pour devenir l’unique plateforme intégrant réglementation multi-énergie + gestion ACC clé-en-main + cockpit d’exploitation automatisé . Gain attendu : réduction temps montage ACC de 12–24 mois à 3–6 mois , scaling de 10 → 100+ opérations sans effort supplémentaire. 

## A) Définition & Cadre Réglementaire ACC (2025) 

### A.1 – Définition et Rôles 

ACC (Autoconsommation Collective) : Opération où au moins deux entités juridiques distinctes partagent l’électricité produite localement par un ou plusieurs producteurs, sans transiter par le réseau public. Les consommateurs reçoivent l’électricité localement valorisée, réduisant leur facture de fournisseur pour cette part. 3 

ACC Étendue : Variante pour projets patrimoniaux (collectivités, bailleurs sociaux, organismes publics) avec seuils augmentés. 

Rôles clés : 
- PMO (Personne Morale Organisatrice) : Structure juridique (association, SAS, SARL, etc.) qui regroupe participants et gère l’opération. Rôles : signature convention Enedis, gestion clés de répartition, facturation, conformité 
- Producteur(s) : Propriétaire(s) installation PV (ou autres EnR), raccordée au réseau public 
- Consommateur(s) : Entités (particuliers, entreprises, collectivités) participant au partage 
- GRD (Enedis) : Mesure production/conso 24h/24, calcule allocation officielle, met à disposition données 
- Fournisseur(s) de complément : Fournit électricité au-delà du partage local, collecte TURPE spécifique 
- Agrégateur/RE (Responsable d’Équilibre) : Gère équilibre pour producteur si > certains seuils 

### A.2 – Cadre Réglementaire (Arrêté 21 février 2025, Journal Officiel 5 mars 2025) 

### Critères d’Éligibilité Critère ACC Classique ACC Étendue Remarques Puissance cumulée max (MW) 3 5 (généraliste) / 10 (collectivités) Arrêté 21/02/2025 : seuil 5 MW pour toutes ; 10 MW dérogation EPCI à fiscalité propre Rayon géographique 2 km autour point production 20 km (zones rurales, cas spécifiques) Décret 2024-1023 Participants min/max 2 producteurs OU 1 prod + consommateurs Même Structure ouverte ou fermée Secteurs Tous (résidentiel, tertiaire, agricole, zones d’activités) Idem Intérêt croissant PME/industriels Périmètre réseau Enedis + ELD (entreprises locales distribution) Idem Hors RTE (transport) 

### Obligations Contractuelles Enedis Élément Obligation Modalités Convention Enedis Signature avant démarrage opération Modèle Enedis pré-rempli, 3–6 semaines de traitement Clés de répartition Statique, dynamique ou “par défaut” Modifiables avec préavis 15 jours ouvrés ; par défaut = au prorata consommations Compteurs communicants Obligatoires pour tous participants Linky générant données 30–60 min Déclaration API Transmission PMO + produits + consommateurs via guichet Enedis Depuis 2025 : automatisation accélérée, délai 3 mois max Données temps réel Courbes de charge 15 min (API Data Connect) Enedis transmet via portail SGE ou API tiers Sortie participant Possibilité entrée/sortie avec préavis 30j Formalités simplifiées si pas contrat de long terme 

Actualisation 2025: Décret du 21 février 2025 a supprimé obligation convention PMO-consommateurs pour ACC < 100 kW (simplification clé pour petits projets). 

### A.3 – Points Réglementaires “Painfully Complex” & Risques de Non-Conformité Friction Cause racine Exemple concret Risque Statut juridique PMO Code monétaire (L315-1) exige personne morale, pas de flou sur structure Confusion : peut-on faire PMO = association informelle ? Enedis refuse Rejet dossier, retard 6+ mois Licences fournisseur ACC = acte de fourniture locale ; PMO peut être requalifiée fournisseur d’énergie si dépasse seuils PMO loue espace toit, vend excédent : est-ce fourniture ? Fiscalité appliquée Amende jusqu’à 7 500 €, status légal incertain Accise électricité Accise TICFE = 0 € ACC (depuis 2022), mais confusion factures si facturation interne non claire Client reçoit facture PMO (accise 0) + facture fournisseur (accise complète) pour même électricité Double-imposition, refus client, conflit Clé de répartition Statique mensuelle = simple mais inefficient (pics ignorés) ; dynamique = optimal mais calcul complexe, Enedis lent PMO veut passer clé statique → dynamique : nécessite accord Enedis + préavis 15j + refonte contrats Délai 2–3 mois, perte valeur si production haut varié Données manquantes Compteur défaillant, historique incomplet, consommation estimée → allocation incorrecte Participant entre après démarrage : données rétroactives ? Attribution au pro-rata ou précision réelle ? Litige participant, correction longue Changement fournisseur participant Fournisseur sortant/entrant doit notifier Enedis pour mise à jour contrats Participant quitte pour OA ailleurs : Enedis reçoit demande fournisseur N+1, mais PMO pas au courant → clash Interruption supply 48–72h, churn participant Conformité territoriale Rayon 2 km (ou 20 km dérogation) mesuré géométriquement → GIS complexe Nouveau consommateur à 2.1 km : accepté ou pas ? Quelle preuve ? Rejet tardif, projet à revoir Fiscalité PMO PMO peut être association non lucrative (TVA exonérée) ou SAS (TVA 20%) → choix impacts coûts client Changement statut PMO après montage : révision TVA rétro ? Conflit avec participants, refonte devis 

### A.4 – Matrice Obligations / Acteurs / Données / Pénalités Obligation Texte Responsable Données requises Échéance Sanction non-conformité Automatisation possible Déclaration opération Enedis Code Énergie R315-1 PMO PDL, puissance, clés, participants Avant mise en service Refus mise en service ✓ API Enedis Convention Enedis Décret 2016-711 PMO + GRD Accord mutuel, clés, fournisseur complément 3–6 sem. traitement Suspension opération Partiellement (auto-génération documents) Clés de répartition Code Énergie R315-1 PMO + Enedis validation Calcul (statique/dynamique), tous paramètres Avant démarrage + chaque changement Allocation erronée, litige participant ✓ Moteur calcul déterministe Courbes de charge Enedis Décret RGCC GRD 15 min par PDL Quotidien / mensuel Impossible facturation ✓ API Data Connect Facturation PMO-consommateurs Code Monétaire + CGI PMO KWh alloués × tarif convenu Mensuel ou trimestriel Litige, impayé, sortie participant ✓ Billing automatisé (shadow) Paiements SEPA Norme SEPA PMO (collecte) IBAN, mandat SDD Avant prélèvement Impayé, relance manuelle, coûts ✓ Intégration SEPA api Conformité vis-à-vis fournisseur complément Contrat GRD-F + CU Fournisseur + PMO Accord tarif, conditions Continu Fourniture interrompue ✓ Notifications EDI GRD Déclaration fiscale ACC (si revente) Loi APER 2023 PMO (si applicable) Chiffre affaires, base imposable Annuel (31 mai) Redressement fiscal ✓ Export données comptables 

## B) Marché ACC 2025 : Taille, Dynamique, Économie 

### B.1 – Données de Marché Actualisées (décembre 2024 – juin 2025) Métrique Valeur Tendance Source Opérations actives (juin 2025) 1 111 +144% vs juin 2024 (454) Enedis Open Data, Enogrid 4 5 Opérations (déc. 2024) 698 +129% vs déc. 2023 (305) Enedis 6 Puissance installée (juin 2025) 161 MW +117% yoy (74 MW déc. 2024) Enedis 7 Participants totaux (juin 2025) 10 600+ +26% vs déc. 2024 (8 342) Enedis 8 Producteurs 1 700 ~16% du total Enedis Consommateurs 10 600+ ~84% du total Enedis Puissance moyenne par opération 145 kVA +96% vs 2024 (74 kVA) Enedis Participants moyen par opération 10–12 Stable Enedis Régions dominantes Occitanie (94), AURA (98), Grand Est (81), BFC Croissance équilibrée Enedis, PV Magazine 9 

### B.2 – Segmentation Cas d’Usage Rentables vs Difficiles 

### Cas Rentables (2025) 

1) Collectivités + écoles/équipements publics 
- Profil : 5–20 bâtiments publics, puissance 200–500 kWc 
- Économie : 15–30% réduction facture électricité locale 
- Drivers : obligation décret Tertiaire (-40% 2030), aide région, maturité PMO 
- Exemple : Mairie + 5 écoles, 300 kWc PV, 15 participants = ~50 kWh/j partagé 
- TRI typique : 6–8 ans ; NPV+ après subventions ; sensible aux prix marché 

2) Bailleurs sociaux + copropriétés résidentielles 
- Profil : Copro > 200 logements, PV toiture + parking, 150–600 kWc 
- Économie : 8–15% réduction charges communes, copropriétaires satisfaits 
- Drivers : obligation solarisation parkings (loi APER 2023), économies visibles, engagement RSE 
- Exemple : 300 logts, 400 kWc toiture + 200 kWc parking = 150 kWh/j local 
- TRI typique : 8–12 ans (ROI construction); motivation de copropriété > financière 

3) Zones d’activités / PME mutualisées 
- Profil : Parc de 5–50 PME, puissance 500 kWc–3 MW 
- Économie : 10–25% réduction coûts énergie (usage complémentaire bureau/atelier) 
- Drivers : prix marché volatil post-ARENH (fin 2025), réduction prix négatifs, sécurisation tarif 15–20 ans 
- Exemple : 20 PME 50 kWh/j usage moyen, 800 kWc PV partagé = 60% autoconso 
- TRI typique : 5–7 ans (profils entreprises sensibles ROI court) 

### Cas Difficiles (Freins majeurs) 

1) Petit résidentiel (< 5 unités, < 100 kWc) 
- Obstacle : Coûts juridiques/administratifs (PMO, contrats) > bénéfice annuel (~€200–500/participant) 
- Mitigation : AMEP (Association pour Mutualisation Énergie Proximité) ; modèle don surplus ; automatisation complète 
- Statut 2025 : Croissance AMEP (15+ actives, 30 en projet), mais scalabilité limitée sans plateforme SaaS 

2) Projets dispersés géographiquement (> 2 km, pas dérogation 20 km) 
- Obstacle : Rayon 2 km = ~40 000 m² cercle ; zones rurales/périurbaines < dense 
- Mitigation : Arrêté 21/02/2025 : dérogation 20 km pour zones rurales, cas spécifiques 
- Statut 2025 : Dérogation applicable mais dossier lourd, CRE contrôle strict 

3) Intermittence sévère (PV seul, pas complémentarité charge) 
- Obstacle : Taux autoconso bas (~30%) si pic production ≠ pic demande 
- Mitigation : Stockage (batteries 50–100 kWh), pilotage charge (bornes VE, chauffage), flexibilité 
- Statut 2025 : Techniquement possible mais CAPEX +€80–150k ; ROI 12–15 ans 

### B.3 – Unit Economics Type ACC 

### Scénario : Collectivité 400 kWc, 15 participants, 20 ans 

CAPEX (Investissement PV) 
- Installation PV 400 kWc : €300–350/kWc = €120–140k TTC 
- Moins aide État/région (30–50%) = €60–98k net 
- PMO (structure juridique + constitution docs) : €2–5k 
- Total CAPEX initial : €62–103k 

OPEX annuel (Gestion PMO) 
- Frais administratifs (Enedis, comptable, assurance) : €3–8k/an 
- Suivi clés, facturation manuelle (si pas automata) : €2–4k/an 
- Maintenance PV : ~€5k/an (0.4% puissance) 
- Total OPEX sans automation : €10–17k/an 

Avec PROMEOS ACC Ops (Automation) 
- Abonnement SaaS : €200–500/mois (~€3–6k/an) 
- Support/onboarding : €1–2k/an 
- Total OPEX automation : €4–8k/an (net gain vs manual : €2–9k/an) 

Revenus (Économies Participants) 
- Partage local typique : 60–75% production autoconsommée = 240–300 kWh/j 
- Tarif PPE 2025 moyen (complément) : ~€70–90/MWh (post-AOS) 
- Tarif ACC interne : 15–20% moins cher = ~€60–75/MWh 
- Gain par kWh : €10–20/MWh = €2.4–6k/an (pour 240 kWh/j) 
- Total économie porteurs : €40–90k sur 20 ans (avant amortissement PV) 

TRI / NPV (avec subventions 40–50%) 
- TRI brut : 8–12% (très bon pour infrastructure locale) 
- Payback : 7–10 ans (acceptable collectivités) 
- NPV 8% taux d’actualisation : €30–60k positif 

## C) Croissance 2026–2030 : Scénarios & Drivers 

### C.1 – Trois Scénarios Build 

### Scénario 1 : PRUDENT (Croissance 50% annuelle) 

Hypothèses : 
- Réglementation inchangée, automatisation lente (Excel + paperasse persistent) 
- Seuils puissance 5 MW max (pas extension 10 MW généralisée) 
- Pas d’intégration massive data Enedis 
- Adoption par collectivités seulement (60% marché) 

Projections 2030: 
- Opérations : ~5 000 (vs 1 100 en 2025) 
- Puissance : ~750 MW (vs 161 MW 2025) 
- Participants : ~50 000 (vs 10 600 en 2025) 
- Coûts PMO : rester hauts (18–24 mois de montage moyen) 
- Taux churn participants : 15–20%/an (friction administrative) 

### Scénario 2 : CENTRAL (Croissance 100% annuelle jusqu’2027, 60% après) 

Hypothèses : 
- Accélération simplification réglementaire (automatisation API Enedis, templates juridiques) 
- Arrêté 21/02/2025 pleinement implémenté + 10 MW collectivités standardisé 
- Émergence 3–4 plateformes SaaS dominantes (EnoPower, EDF Communitiz, PROMEOS, …) 
- Adoption diversifiée : collectivités 40%, bailleurs 25%, PME 20%, particuliers (AMEP) 15% 
- PV raccordé France : 50+ GW (vs 24 GW fin 2024) 

Projections 2030: 
- Opérations : ~12 000 (vs 1 100 en 2025) 
- Puissance : ~1 800 MW (vs 161 MW 2025) 
- Participants : ~120 000 (vs 10 600 en 2025) 
- Coûts PMO : réduire à 3–6 mois avec automation 
- Taux churn : 5–10%/an (confiance + UX améliorée) 

### Scénario 3 : ACCÉLÉRÉ (Croissance 150% annuelle) 

Hypothèses : 
- Réforme majeure : suppression licence fournisseur pour PMO < 5 MW (demande SER/Enerplan) 
- Directive UE energy sharing transposée (Allemagne modèle) 
- Clés de répartition dynamiques pilotées IA standard (accroît attractivité + 5–10% autoconso supplémentaire) 
- Stockage distribué (batteries, IRVE) intégré opérations (25% opérations + stockage 2030) 
- PV raccordé + autoconso collective = modèle dominant tertiaire/résidentiel 
- Électrification chauffage (PAC) + VE crée profils demande favorables ACC (lissage demande) 

Projections 2030: 
- Opérations : ~25 000 (vs 1 100 en 2025) 
- Puissance : ~3 500–4 000 MW (vs 161 MW 2025) 
- Participants : ~250 000 (vs 10 600 en 2025) 
- % PV France en ACC : 40–50% (vs ~6% 2025) 
- Modèle économique stabilisé (prix marché spot + primes flexibilité) 

### C.2 – Signaux Faibles à Surveiller (Wildcards) Signal Impact positif ACC Probabilité 2026 Actions PROMEOS Suppression licence fournisseur PMO Reduction friction legal, scaling AMEP +300% Moyen (30–40%) Briefing legal, advoc régulatoire Intégration EU Energy Sharing Directive Cross-border ACC pilotes, mutualisation internationale Faible (10%) Monitor EU legislation, R&D Baisse coûts batteries Stockage intra-ACC standard, taux autoconso +20% Moyen-haut (50–60%) Intégration batterie dans Ops v2 Démocratisation IA clés dynamiques Taux autoconso +5–15%, réduction prix acc attractif Haut (70–80%) MVP clé dynamique T4 2025 Obligation ACC tertiaire (décret renforcé) Doublement opérations collectivités 2027–2028 Moyen (40%) Compliance module “ACC-ready” Crise tarif énergie (prix spot >€150/MWh) Rentabilité ACC x2–3, frénésie investissement Moyen (30–50%) Pricing model flexible spot Saturation réseau distribution local Effacement producti onrequis, ACC devient nécessaire Moyen (30–40%) local Flexible orchestration v2 

## D) Les 10 Leviers Concrets pour Accélérer Croissance ACC (2025–2026) 

### 1. Automatisation API Enedis (DataConnect + ACC) 
- Action : Intégration native PROMEOS avec courbes de charge 15 min (Data Connect) + déclaration opération (API ACC) 
- Gain : Zéro ressaisie données, facturation générée automatiquement 
- Impact time-to-market : –3 mois montage, settlement fiabilisé 

### 2. Template juridique standardisé PMO (par type : association, SAS, SEM) 
- Action : Banque de modèles pré-remplis Enedis + statuts + contrats (gérés par avocats, intégrés PROMEOS) 
- Gain : Montage juridique < 1 mois vs 2–4 mois aujourd’hui 
- Impact : Scalabilité 10x (1 avocat peut valider 50 opérations/an vs 5 aujourd’hui) 

### 3. Clés de répartition dynamiques (IA prédictive) 
- Action : Moteur IA qui ajuste clés basé sur prévisions météo + historique (non-linéaire, ex: 60% toit/40% partic dynamique) 
- Gain : +5–15% autoconsommation vs clés statiques, meilleure rentabilité pour tous 
- Impact : Attractivité produit +30%, réduction prix négatifs producteur 

### 4. Shadow Billing automatisé + SEPA 
- Action : Facturation internalisée PMO (PROMEOS génère factures internes + mandats SEPA prélèvement direct) 
- Gain : Zéro factures manuelles, recouvrement trésorerie 95%+ vs 70% manuellement 
- Impact : OPEX PMO –€5–8k/an, satisfaction participant +40% 

### 5. Intégration ERP/GTB clients (API connecteurs) 
- Action : Connecteurs natifs comptabilité (Sage, SAP, Excel) + GTB (pour données consommation) 
- Gain : Zéro saisie en double en comptabilité, données temps réel pour optimisation 
- Impact : Onboarding client simplifiée, churn risque réduit 30% 

### 6. Conformité multi-réglementation natif (Décret Tertiaire, BACS, APER, accise) 
- Action : Module “Compliance ACC” intégré PROMEOS : suivi obligation, alertes automatiques, preuve générée 
- Gain : Sécurité légale PMO, audit trail complet 
- Impact : Réduction litiges 50%, confiance bailleurs/collectivités +40% 

### 7. Simplification onboarding participant (KYC express + e-signature) 
- Action : Flow digital < 5 min : KYC, mandats paiement, statuts, signature e (Universign, Docusign) 
- Gain : Entrée/sortie participant < 48h vs 2–3 semaines 
- Impact : Dynamique opération fluide, retenues réduits, scalabilité participants ×3 

### 8. Agrégation multi-ACC pour PMO portfolio (reporting centralisé) 
- Action : Cockpit group pour PMO gérant 5–50 opérations ACC : KPIs consolidated, gestion clés batch, reporting unique 
- Gain : Mutualisation expertise, gestion coûts OPEX < €2k/an par opération 
- Impact : Business model PMO-as-a-service viable (revenus €1–3k/opération/an) 

### 9. Standardisation données comptables (export module OPERAT + BACS) 
- Action : Export CSV/XML prêt audit, compatible OPERAT (décret Tertiaire), BACS (conformité GTB) 
- Gain : Audit annuel < 1 jour, zéro reformatage données 
- Impact : Coûts comptable –30%, conformité garantie 

### 10. Marché de data/flex (API exposée partenaires : agrégateurs, VPP, DR) 
- Action : PROMEOS expose API flex : surplus production disponible, capacité effacement (bornes EV, chaufage) → agrégateurs can consommer 
- Gain : Valorisation additionnel €500–2000/an par opération, réduction prix négatifs producteur 
- Impact : Revenue stream additionnel pour PMO (partage), attractivité producteur +25% 

## E) Les 10 Irritants Opérationnels Majeurs & Solutions d’Automatisation # Irritant Cause Exemple Friction Solution Process Solution Tech Gain 1 Montage PMO lourd Choix statut juridique flou + docs custom Collectivité lance ACC, avocat propose 3 structures → débat 2 mois Template bancaire, critères de sélection smart PROMEOS suggère structure basée sur secteur/taille → 1 clic -6 sem 2 Participants tardent inscription Onboarding papier, peur clauses, manque confiance Chef projet relance 10 fois pour mandats signés Flow digital intégré + explications contextuelles PROMEOS : email + lien unique, e-sign Universign, MFA -2 sem 3 Enedis demande revérifications données PDL mal formatés, participants douteux, doublons Enedis refuse dossier, demande recalcul clés → 3 sem attente Validation données Enedis dans PROMEOS avant soumission Checker API Enedis + BDD PDL Enedis en temps réel -3 sem 4 Changement fournisseur participant crée chaos Nouveau fournisseur pas au courant ACC → coupe électricité Participant quitte fournisseur A pour OA ailleurs, confusion contrats Procédure synchronisation Enedis → fournisseurs automatisée PROMEOS notifie Enedis et fournisseurs N+1 en batch -48h risque 5 Clé statique = autoconso sous-optimal Clé 50/50 mais prod 2000 kWh/j de 10–14h, demande pic 18–22h Taux autoconso réel 35% vs potentiel 70% ; client mécontentement Passage clé statique → dynamique PROMEOS moteur IA : propose clé optimale, met à jour auto chaque mois +15–20% autoconso 6 Facturation = cauchemar Excel Ventilation manuelle 12 participants × 30 jours, recalculs Erreur calcul : participant A facturé 2x, doit rembourser Facturation entièrement automatisée PROMEOS shadow billing : calcul jour J, facture 24h après relevé Enedis -15 jours clôture 7 Impayés participants trop fréquents Rappels manuels inefficaces, démotivation PMO 30% participants en retard paiement > 30j, recouvrement coûte €200/an Prélèvement automatique SEPA + escalade smart PROMEOS SEPA intégré + notifications SMS/email smart, astreintes auto Trésorerie +95% vs 70% 8 Entrée/sortie participant lente + coûteuse Changement clés, recalcul contrats, notification Enedis manuelle Participant veut partir : 4 sem délai, coûts réécriture docs Automation contrats, re-calc clé, notification batch Enedis PROMEOS re-deploy clés < 48h, notifications Enedis API batch Churn risk –30% 9 Audit annuel et conformité = panique Dossier éparse : courbes Enedis, factures, contrats, preuves Auditeur demande historique 5 ans, traces décisions clés → racontage Coffre-fort numérique centralisé + audit trail crypto PROMEOS vault : tous documents versionnés, tamponné, queryable -3j audit 10 Communication Enedis lente et formelle Délais 3–6 mois pour validation, feedback > bureaucratique PMO relance 10 fois, Enedis pas au courant changement clés → dossier bloqué Portal standard Enedis (SGE) utilisé mais via API PROMEOS PROMEOS = proxy smart : agrège demandes batch, suit statut real-time -50% délai Enedis 

## F) Design Process + Produit pour Cycle Projet 12–24 mois → 3–6 mois 

### F.1 – Phases Actuelles vs Optimisées Phase Durée Actuelle Durée Optimisée PROMEOS Contribution 1. Diagnostic faisabilité 4–8 sem 1–2 sem Simulateur ACC 5 min (PDL input → résultat TRI auto) 2. Montage PMO (statut + docs) 8–12 sem 2–4 sem Template SaaS (association/SAS/SEM), assistant config, e-doc 3. Recrutement participants 6–12 sem 2–4 sem Portal auto-invitation, KYC express digital, e-sig 4. Valeurs fournisseur complément 2–4 sem 1 sem Connecteur fournisseurs (EDI batch), comparatifs auto 5. Constitution dossier Enedis 4–8 sem 1 sem Checker données Enedis API, génération auto convention, API submit 6. Validation Enedis 4–6 sem 2–3 sem Suivi statut real-time SGE API, escalade auto si > 3 sem 7. Test & démarrage opération 2–4 sem 1 sem Simulation clés, shadow testing, batch Enedis, quick go-live TOTAL 30–54 sem (6–12 mois) 10–20 sem (2.5–5 mois) Réduction 70–80% 

### F.2 – Checkpoints Clés Accélération (PMO/PROMEOS) 

Semaine 0–1 : Diagnostic ACC (5 min simulator → TRI, économies prévisionnelles) 
- PDL input → calcul profil complémentarité → scoring faisabilité 
- Output : “Accessible ACC ?” + recommandations structure 

Semaine 1–2 : Montage PMO (wizard 30 min) 
- Choix statut (algo suggestion), remplissage données 
- Auto-génération : statuts, contrats, mandats, formulaires URSSAF/cadastre 

Semaine 2–3 : Recrutement participants (flow digital) 
- PROMEOS envoie mail unique par participant, lien inscription portal 
- KYC express (ID, IBAN), consentement, e-signature documents 
- Tracking taux signature real-time (target > 80% sem 2) 

Semaine 3–4 : Validation données + Enedis (checker smart) 
- PROMEOS valide PDL Enedis (API query), détecte doublons, qualité données 
- Auto-génération convention Enedis + clés initiales 
- Submit API Enedis (guichet) → tracking statut SGE 

Semaine 4–6 : Négociation fournisseur (batch RFQ) 
- PROMEOS connecte 2–3 fournisseurs complément, RFQ auto 
- Comparative tarif, conditions → PMO choisit 
- Contrat pré-signé en EDI 

Semaine 6–8 : Validation Enedis + tests opération 
- Enedis finalise convention (cible 3 sem max, PROMEOS escalade si +) 
- Go-live : test shadow billing 1–2 cycles, puis démarrage officiel 

Semaine 8–10 : Go-live & onboarding participants 
- Participants reçoivent 1ère facture ACC 
- Support PROMEOS (chat, wiki intégré) pour questions 

### F.3 – Modèle Economique PROMEOS pour Montage Rapide 

Pricing Modules : Module Modèle Exemple Prix Use Case ACC Starter (montage) Setup fee one-time €300–800 / opération PMO nouvelle, <100 kW ACC Ops (expl. 3 ans) SaaS /mois €150–400/mois Suivi temps réel, facturation Data & Compliance (multi-régl) SaaS modular €500–2000/mois (portfolio multi-sites) Collectivités, bailleurs, tertiaire Flex Broker (API agg) %revenue 5–10% surplus vendu Pour PROMEOS monetizing flex 

Exemple revenu PROMEOS : 100 opérations ACC montées 2025 (scénario central) 
- Starter fee : 100 × €500 = €50k one-time 
- Ops SaaS annuel : 100 × €250/mois × 12 = €300k/an (année 1–3 post-go-live) 
- Data module (20% portfolios): 20 × €1000/mois × 12 = €240k/an 
- Total revenu année 1 (post-ramp) : ~€290k (base 100 ops) 

## G) PROMEOS – Intégration Brique ACC dans Cockpit B2B Fournisseur 2.0 

### G.1 – Positionnement “Micro-fournisseur Local Augmenté” 

Vision : PROMEOS = unique plateforme qui combine fournisseur local digital (ACC ops) + conformité multi-énergie (tertiaire) + orchestrateur flexibilité . 

Trois Packages Progressifs : 

### Package 1 : ACC Starter (Incubation, 3–6 mois déploiement) 
- Clients : PMO + collectivités/bailleurs pour 1ère ACC 
- Features MVP : 
- Wizard configuration ACC (participants, clés, docs) 
- Auto-génération convention Enedis + contrats 
- API submit Enedis (guichet) 
- Portal participants (consultation simple) 
- Tarif : €300–600 setup + €100/mois portal 
- Success metrics : Temps montage < 6 sem, 100% dossier accepté Enedis 

### Package 2 : ACC Ops (Exploitation courante, 3+ ans) 
- Clients : PMO opérant ACC, particuliers consommateurs/producteurs 
- Features MVP : 
- API Enedis Data Connect (courbes 15 min) 
- Calcul répartition automatisé (clés statique/dynamique) 
- Shadow billing (factures + export SEPA) 
- Dashboard participants (production, conso, économies) 
- Journal transactions + alertes 
- Tarif : €150–400/mois (PMO manager), €0 (participants consumers) 
- Success metrics : Taux autoconso ≥ 60%, impayés < 5%, NPS > 7/10 

### Package 3 : Data & Conformité (Réglementation B2B, toutes organisations) 
- Clients : Collectivités, bailleurs, tertiaire multi-sites (avec/sans ACC) 
- Features MVP : 
- Import Enedis + GTB (données conso multi-site) 
- Dashboard conformité Décret Tertiaire (-40% 2030), BACS, APER 
- Alerts automatiques (dérive, échéances) 
- Rapports OPERAT, CO₂, émissions 
- Recommandations sobriété/investissement (PV, acc, stockage) 
- Tarif : €400–2000/mois (échelle nombre sites + energy) 
- Success metrics : % conformité 100%, audit time –50%, recos adoption > 30% 

### G.2 – Architecture Logicielle (MVP → v1 → v2) 

### MVP (T0–T3 2025, ~10–12 sem dev) 

Modules : 
- PMO Workspace (gestion gouvernance) 
- Inscription PMO, profil, documents (statuts, convention Enedis) 
- Liste participants + rôles (producteur/consommateur/trésorier) 
- Gestion clés de répartition (statique par défaut, éditable) 
- Data & Monitoring (import + KPI) 
- Intégration CSV Enedis (courbes export manuel → automation API T1 2026) 
- Calcul ratios : TAc (taux autoconsommation), TAp (taux autoproduction) 
- Graphs temps réel (prod/conso/surplus) + alertes anomalies 
- Settlement & Billing (ventilation + facturation) 
- Calcul mensuel parts énergétiques (clés × courbes) 
- Génération factures internes (PDF exportés) 
- Suivi paiements manuels (checklist + email relance simple) 
- Participant Portal (vue consommateur/producteur) 
- Login simple, affichage conso locale + économies 
- PDF facture téléchargeable 
- FAQ intégré 

Tech Stack (Recommandation): 
- Frontend : React/Vue.js (PWA, responsive mobile) 
- Backend : Node.js/Python FastAPI (API-first) 
- Data : PostgreSQL (données transactionnelles) + TimescaleDB (séries temporelles) 
- Auth : OAuth2 (Keycloak), e-sign (Universign API) 
- Infra : K8s managed (GCP/AWS/OVH French) 

### V1 (T3–T4 2025, +10 sem dev) 

Ajouts clés : 
- API Enedis Data Connect (branchement officiel, pas CSV manuel) 
- API ACC Enedis (déclaration + suivi statut opération) 
- Clés de répartition dynamiques (v1.0 : règles simples météo) 
- SEPA intégration (mandats SDD, prélèvements) 
- Module Data & Conformité beta (Décret Tertiaire lite) 

### V2 (2026, +20 sem dev) 

Intelligence & Scalabilité : 
- Clés dynamiques IA avancées (prédiction demande + flexibilité) 
- Intégration GTB (capteurs température, équipements) 
- Orchestrateur flexibilité (pilotage IRVE, batteries, chaufage) 
- Agrégation multi-ACC (pour PMO portfolio) 
- Marketplace flex (vente surplus à agrégateurs VPP) 

### G.3 – Roadmap MVP (90 j / 180 j / 12 mois) & Backlog RICE 

### Roadmap Temporelle ``` 

T0 (Jan–Mar 2025) – MVP Core Foundation 
├─ Sprint 1–3 : Auth, PMO workspace, data model 
├─ Sprint 4–6 : Participant portal, settlement calc 
└─ Sprint 7–9 : Test UAT, go-live beta (10 opérations pilotes) 

T1 (Apr–Jun 2025) – API Enedis + Compliance Lite 
├─ Integration Enedis Data Connect (courbes temps réel) 
├─ API ACC Enedis (déclaration automatisée) 
├─ Décret Tertiaire monitoring (bêta) 
└─ First 20 paying customers 

T2 (Jul–Sep 2025) – Clés dynamiques + SEPA 
├─ Moteur clés dynamiques v1.0 (règles MBA) 
├─ SEPA mandate + prélèvements auto 
├─ Data & Conformité v1.0 (full module) 
└─ 50+ opérations actives 

T3 (Oct–Dec 2025) – Scaling + Intelligence 
├─ Agrégation multi-ACC (portfolio PMO) 
├─ Clés dynamiques IA (prédiction ML) 
├─ Intégration GTB (capteurs IoT) 
└─ 100+ opérations, 10+ bailleurs/collectivités engagées #### **Backlog Priorisé (MoSCoW + RICE)**

| User Story | Module | MoSCoW | RICE Score | Statut T0 |
|-----------|--------|--------|-----------|-----------|
| En tant que PMO, je crée opération ACC en 15 min avec wizard | ACC Starter | **M** | 95 | Sprint 1–2 |
| En tant que participant, je vois ma facture + économies | Portal | **M** | 90 | Sprint 3–4 |
| En tant que PMO, j'automatise la facturation SEPA | Billing | **M** | 85 | Sprint 4–6 |
| En tant qu'admin, j'importe courbes Enedis automatiquement | Data & Mon | **M** | 80 | Sprint 6–9 (API T1) |
| En tant que PMO, j'optimise clés de répartition avec IA | Settlement | **S** | 75 | T1 2026 |
| En tant qu'energy manager, je piloter multi-sites + ACC | Compliance | **S** | 70 | T1 2025 beta |
| En tant qu'agrégateur, j'accède aux surplus via API | Flex Broker | **C** | 55 | T2 2026 |
| En tant que client data, j'exporte compliance rapports | Data & Mon | **C** | 50 | T2 2025 |

### **G.4 – PRD Mini (Problem → Features → Success Metrics)**

#### **Problem**

- 12–24 mois pour monter opération ACC (flou statut PMO, docs customs, Enedis communication lent)
- Exploitation manuelle 80% (Excel, facturation, clés statiques, impayés)
- Conformité multi-énergie (Tertiaire, BACS, APER, accise) = nébuleuse, risque audit
- Aucune solution intègre "montage + opération + conformité" de A à Z

#### **Users & Jobs-to-be-Done**

| User | Job-to-be-Done |
|------|---|
| **PMO (rôle structure)** | Créer opération légalement, gérer participants, encaisser paiements, rester conforme |
| **Collectivité/baillet responsable** | Déployer ACC énergie local rapidement, sécuriser budget électricité 5–20 ans |
| **Participant consommateur** | Acheter électricité locale moins chère, voir impact économie, payer facilement |
| **Participant producteur** | Vendre production localement sans marché spot volatilité, maximiser valorisation |
| **Energy manager multi-sites** | Piloter conformité tertiaire, intégrer ACC, tracker KPI énergies, auditer facilement |

#### **Features Clés (MVP)**

1. **Wizard ACC** (5 features)
 - Choix statut PMO smart (algo suggère basé secteur)
 - Remplissage données participants (PDL, puissance, coordonnées)
 - Configuration clé répartition (statique par défaut, explication dynamique)
 - Auto-génération docs juridiques (statuts, contrats, mandats)
 - Submit API Enedis + tracking dossier

2. **Portal Participants** (3 features)
 - Vue personnalisée (conso/prod locale, économies, facture)
 - E-signature documents (onboarding < 5 min)
 - Paiement SEPA (opt-in prélèvement)

3. **Settlement Automatisé** (4 features)
 - Calcul répartition mensuel (clés × courbes Enedis)
 - Facturation interne (PDF, export comptable)
 - Alerts impayés + escalade (SMS, email)
 - Dashboard PMO (KPI, journal transactions)

4. **Data & Conformité** (4 features)
 - Import Enedis multi-sites (API Data Connect)
 - Conformité Décret Tertiaire (tracker objectives, alerts)
 - Conformité BACS (status GTB, checkpoints)
 - Export rapports (OPERAT, CO₂, audit)

#### **Data Model (Schéma Simplifié)**

```sql
-- PMO
Table PMO (id, name, type[association|SAS|SARL|SEM], siren, iban, status[created|validated|live])

-- Opération ACC
Table Operation_ACC (id, pmo_id, name, start_date, puissance_kWc, radius_km, status[montage|live|inactive])

-- Participants (producteurs + consommateurs)
Table Participant (id, operation_id, type[producer|consumer], pdl, siret, iban, role[member|trésorier|ref])

-- Courbes Enedis (import 15 min)
Table MeasurementCurve (participant_id, timestamp, kWh_produced, kWh_consumed)

-- Clés de répartition
Table Allocation_Rule (operation_id, participant_producer_id, participant_consumer_id, ratio[0–100], effective_date)

-- Factures internes
Table Invoice_Internal (id, pmo_id, consumer_id, month, kwh_local, tarif, total_eur, status[draft|sent|paid], due_date)

-- Paiements SEPA
Table Payment_SEPA (id, invoice_id, mandate_id, status[pending|collected|failed], collected_date) 

### Success Metrics (KPIs) Métrique Target MVP Target V1 Owner Délai montage ACC < 8 sem < 6 sem Prod % dossiers acceptés Enedis (1ère tentative) > 95% 100% Tech Taux autoconsommation (vs clé statique) 60–65% 70–75% (avec clé dynamique) Product Taux de couverture facturation > 95% 100% Ops Impayés (% facturation totale) < 5% < 2% Finance NPS participants > 6/10 > 8/10 UX Temps support P1 (réponse) < 4h < 1h Support Churn opération annuelle < 10% < 5% Growth CAC (coût acquisition client PMO) < €200 < €100 Marketing LTV/CAC ratio > 3x > 5x Finance 

## H) Benchmark Concurrence & Espaces Blancs 

### H.1 – Paysage Concurrentiel (2025) 

### Catégorie 1 : EMS Généralistes (Energy Management Systems) Acteur Positionnement Offre ACC Offre Compliance Limites Différenciation Advizeo (Hager) Dashboard énergie multi-sites Non (aucune) Décret Tertiaire baseline Pas ACC, pas settlement Puissance analyse prédictive Deepki SaaS data énergie buildings Non Tertiaire + BACS Pas ACC, support basique Intelligence données immobilier Datanumia Intelligence énergétique Non Monitoring coûts Pas ACC, pas settlement Billing énergétique mais pas ACC WeSmart Plateforme locale ENR Partiel (ACC consultation) Non ACC limité, pas automatisation UI attrayante, modèle éducatif 

Verdict : Aucun EMS n’offre ACC opérationnelle + facturation ; marché blanc à PROMEOS. 

### Catégorie 2 : Plateformes ACC Spécialisées Acteur Positionnement Opérations gérées Segmentation Modèle Limites Différenciation Enogrid/EnoPower Leader ACC opération 200+ opérations Multi-secteur SaaS (€) + services Pas compliance tertiaire, clés statiques Scalabilité opérations, UX EDF – Communitiz Fournisseur + ACC 50–100 opérations Collectivités surtout SaaS captif EDF Verrouillage EDF, pas agnostique Assistance déploiement, crédibilité Enercoop – Elocoop Coopérative citoyenne 30–50 opérations Coopératives/citoyens Modèle équitable Petite taille, peu scaling Mission éthique, gouvernance Sunchain (blockchain) Blockchain ACC <20 opérations Tech-forward Experimental Adoption faible, coûts élevés Transparence blockchain HubWatt Facturation ACC + monitoring 100+ opérations Multi-secteur SaaS + support Pas compliance multi-réglementaire, pas montage ACC Facturation robuste, intégration compta 

Verdict : Enogrid/EnoPower = leader ACC, mais pas compliance tertiaire (Data & Conformité). Ouverture pour PROMEOS « double compétence ». 

### Catégorie 3 : Fournisseurs & Intermédiaires Énergie Acteur Positionnement Modèle ACC Différenciation Limites Urban Solar Fournisseur vert local Intermédiaire (PMO externalisée) Marque réputée, accompagnement Perte autonomie PMO, captivité Ilek Marketplace producteurs–consommateurs Pair-à-pair (pas ACC collectif) Peer-to-peer, flexibilité Pas ACC multi-membres, micro EDF Obligation d’Achat (OA) Rachat surplus PV Non (vs ACC local) Tarifs assurés 20 ans Pas partage local, peu attractive pour ACC 

Verdict : Modèles captifs ou pair-à-pair ; pas ACC clé en main + compliance. 

### H.2 – Matrice Positionnement PROMEOS Compliance & Réglementation (X-axis)
 Faible ←────────────────────────────────→ Fort

 ╔════════════════════════════════════════════════════════╗
 ║ ║
 Fort ║ ║
 ║ ╔─────────────────────────────────────╗ ║
 ║ │ PROMEOS │ ║
 ║ │ (Data & Compliance + ACC + Ops) │ ║
 ║ │ Holistique, Automatisé, Intelligent ║
 ║ ╚─────────────────────────────────────╝ ║
 ACC ║ ║
 Ops ║ ╔─────────────────────┐ ║
 Gestion ║ │ Enogrid/EnoPower │ ║
 ║ │ Spécialisé ACC │ Advizeo/Deepki ║
 ║ │ mais pas compliance │ (EMS compliance) ║
 ║ └─────────────────────┘ ║
 ║ ║
 Faible║ ║
 ╚════════════════════════════════════════════════════════╝
 Faible Fort 

PROMEOS = unique en cadran supérieur droit (compliance fort + ACC ops fort) 

### H.3 – Trois Différenciateurs PROMEOS 

### 1) “Compliance-Driven Energy Communities” 
- What : PROMEOS is 1st platform integrating natively regulatory compliance (Décret Tertiaire, BACS, APER, accise) into ACC operation 
- Why it matters : Clients manage energy compliance + local sharing in same portal → risk mitigation + time savings (separate tools cost 2x, time 3x) 
- Competitor gap : Enogrid/Communitiz = zero compliance; Deepki/Advizeo = zero ACC → PROMEOS fills gap 

### 2) “End-to-End Automation” 
- What : PROMEOS automates entire lifecycle : legal setup (wizard) → Enedis API integration (zero manual data entry) → monthly billing (SEPA direct) → compliance reporting (PDF one-click) 
- Why it matters : Reduce ACC project cycle from 12–24 mo to 3–6 mo; scale 10 → 100+ operations without linear cost increase 
- Competitor gap : Most solutions still manual (Excel, email, phone); PROMEOS = factory for ACC, competitors are artisans 

### 3) “Local Value Maximization via AI” 
- What : Dynamic allocation keys + flex orchestration (IRVE, heat, storage) powered by ML → maximize autoconsumption % + minimize negative pricing exposure 
- Why it matters : Producer confidence +, consumer savings +, project ROI ×1.5–2.0 vs static keys 
- Competitor gap : No competitor offers this; future-proof differentiator (becomes essential as % renewables → 50%+) 

## I) Réponses aux 5 Questions Guides Obligatoires 

### Q1 : 10 Leviers Concrets Accélération ACC 2025 
- Automatisation API Enedis (DataConnect + ACC) : –3 mois montage, zéro ressaisie 
- Template PMO standardisé : montage juridique < 1 mois vs 2–4 mois 
- Clés dynamiques IA : +5–15% autoconso, attractivité +30% 
- Shadow billing + SEPA auto : OPEX PMO –€5–8k/an, recouvrement 95%+ 
- Intégration ERP/GTB : zéro double-saisie, optimisation data temps réel 
- Conformité multi-réglementation native : audit trail complet, risque litige –50% 
- Onboarding participant digital : KYC express < 5 min, churn –30% 
- Agrégation multi-ACC : gestion coûts OPEX < €2k/opération/an 
- Standardisation données comptables : audit < 1 jour vs 3–5 jours 
- Marché flex/data : revenue additionnelle €500–2000/opération/an pour PMO 

### Q2 : 10 Irritants Opérationnels Majeurs (avec solutions) 
- Montage PMO lourd → Template + algo sélection structure → –6 sem 
- Inscription participants tardive → Flow digital e-sig → –2 sem 
- Enedis revérifications données → Validation API préalable → –3 sem 
- Changement fournisseur chaos → Notification batch API → –48h risque 
- Clé statique sous-optimal → IA dynamique monthly → +15–20% autoconso 
- Facturation Excel cauchemar → Shadow billing auto → –15 jours clôture 
- Impayés trop fréquents → SEPA escalade smart → trésorerie +95% 
- Entrée/sortie participant lent → Automation contrats → churn –30% 
- Audit annuel panique → Vault numérique crypto + trail → –3 jours audit 
- Enedis lent & bureaucratique → API proxy smart batch → –50% délai Enedis 

### Q3 : Design Process + Produit → 12–24 mois → 3–6 mois 

Phases optimisées (10–20 sem vs 30–54 sem) : 
- Diagnostic auto (1–2 sem vs 4–8) : simulator 5 min 
- Montage PMO (2–4 sem vs 8–12) : template SaaS wizard 
- Recrutement (2–4 sem vs 6–12) : portal auto-invite + e-sig 
- Fournisseur (1 sem vs 2–4) : connecteur RFQ batch 
- Dossier Enedis (1 sem vs 4–8) : checker API + auto-generation 
- Validation Enedis (2–3 sem vs 4–6) : suivi SGE real-time + escalade 
- Tests & démarrage (1 sem vs 2–4) : shadow testing 1 cycle 

Checkpoints clés : Simulator diagnosis S0, PMO wizard S1–2, participant signup S2–3, Enedis submit S4, fournisseur locked S5, go-live S8–10. 

### Q4 : Modèle Économique PROMEOS 

Trois flux revenus : Stream Tarif Volume 2025 Volume 2030 Central Revenu 2030 ACC Starter (setup) €300–600 / opération 100 opérations 1 000 opérations €300–600k/an ACC Ops (SaaS expl) €150–400/mois PMO 100 ops × 12 mo 1 000 ops × 12 mo €1.8–4.8M/an Data & Compliance €400–2000/mois portfolio 20 clients (multi-site) 200 clients €960M–4.8M/an Flex Broker (API%) 5–10% surplus revenue €0 (beta 2026) €500k/an avg portfolio €5–50M/an (if 1000 ops) 

Blended ARPU (Annual Revenue Per User) : 
- Micro-PMO (< 100 kW) : €600/year 
- SME-PMO (100 kW–1 MW) : €2000–5000/year 
- Portfolio (multi-site) : €5000–20k/year 

Path to profitability : 
- Year 0 (2025) : –€500k (dev + go-to-market) 
- Year 1 (2026) : break-even (100 opérations × avg €3k) 
- Year 2+ (2027+) : €2–5M net profit (200–300 opérations, scale compliance) 

### Q5 : Évolutions 2026–2030 Changeant la Donne & Préparation Évolution Impact ACC Probabilité Réaction PROMEOS Suppression licence fournisseur PMO < 5 MW +300% AMEP, scalabilité particuliers 30–40% Advoc policy, legal brief, product ready Obligation ACC tertiaire renforcée Doublement opérations collectivités 40% Intégration Décret Tertiaire native Directive UE energy sharing Cross-border ACC pilots, mutualisation 10% Monitor EU lawmaking Baisse batterie ($/kWh → 80–100) 25% opérations + stockage 50–60% Intégration batterie dans Ops v2 IA dynamique standard industrie +5–15% autoconso, attractivité x2 70–80% Clés IA en MVP T1 2026 Saturation réseau local (DER) Effacement production obligatoire 30–40% Flex orchestration capability v2 Crise tarif énergie >€150/MWh Frénésie ACC (3x valeur) 30–50% Pricing model flexible, marketing 

Préparation PROMEOS (2025–2026) : 
- Intégrer clés IA dès MVP (vs concurrent attente v2–v3) 
- Préparer module batterie + IRVE (pour cas 50% opérations 2028+) 
- Plaider simplification réglementaire (FNCCR, Enerplan, SER) 
- Investir en R&D flex orchestration (orchestrateur local demand-response) 
- Monitorer directive UE, legal watch 

## J) Roadmap Brique ACC PROMEOS – Backlog MVP & Priorisation 

### J.1 – Roadmap 90 j / 180 j / 12 mois (T0 2025 → T3 2025) 

T0 : 90 jours (Jan–Mar 2025) – Fondation MVP 
- ✓ Auth & user management (SSO compatible) 
- ✓ PMO workspace (gestion profil, docs storage) 
- ✓ Participant portal (inscription, portal consultation) 
- ✓ Settlement calc (import CSV Enedis → répartition) 
- ✓ Billing draft (génération factures PDF) 
- ✓ Beta launch 5–10 opérations pilots (collectivités amies) 

T0–T1 : 180 jours (Jan–Jun 2025) – API Enedis + Compliance Lite 
- ✓ API Enedis Data Connect (branchement courbes 15 min) 
- ✓ API ACC Enedis (déclaration opération + suivi statut) 
- ✓ Décret Tertiaire monitoring (tableau bord baseline) 
- ✓ SEPA mandate + prélèvement auto (premiers clients paying) 
- ✓ First 20 paying customers (Starter + Ops) 

T0–T3 : 12 mois (Jan–Dec 2025) – Scale + Intelligence 
- ✓ Clés dynamiques v1.0 (règles ML simples basées météo + historique) 
- ✓ Data & Conformité v1.0 (full Décret Tertiaire, BACS alert, APER tracker) 
- ✓ Agrégation multi-ACC (portfolio PMO) 
- ✓ 100+ opérations actives, 1000+ participants 
- ✓ 10+ bailleurs/collectivités engagés (Data & Compliance) 

### J.2 – Backlog Détaillé (User Stories) 

### MVP Core (Sprint 1–9, Jan–Mar 2025) 

Sprint 1–2 : Auth & PMO Workspace US-001 [M] En tant que PMO, je m'inscris et crée mon profil
 Acceptance Criteria:
 - Inscription email + password (ou SSO)
 - Remplissage infos PMO (SIREN, type structure, adresse)
 - Upload statuts + documents constitutifs
 - Validation email
 - Redirection vers PMO dashboard

US-002 [M] En tant que PMO, je gère liste participants
 AC:
 - Ajouter participant (one-by-one ou CSV import)
 - Éditer coordonnées participant
 - Supprimer participant (soft delete)
 - Exporter liste PDF (pour validation Enedis)
 - Suivre statut signature/KYC (% completeness) 

Sprint 3–4 : Participant Portal US-003 [M] En tant que participant, je m'inscris à opération ACC
 AC:
 - Lien unique reçu par email (génération code)
 - Form inscription simple (PDL, IBAN, coordonnées)
 - Consent documents (checkbox statuts, convention Enedis, contrat membre)
 - E-signature Universign (via API)
 - Confirmation + accès portal participant

US-004 [M] En tant que participant, je consulte mes données
 AC:
 - Dashboard synthétique : % énergie locale consommée ce mois-ci
 - Estimé économie (€) vs facture normale
 - Facture PDF téléchargeable (détail allocation)
 - Graph historique 3 derniers mois
 - FAQ contextel embedded 

Sprint 4–6 : Settlement & Billing US-005 [M] En tant que PMO, j'importe courbes Enedis
 AC:
 - Upload CSV Enedis (format Export Data, 30 min ou 60 min pas)
 - Parse & validation colonne (timestamp, PDL, kWh)
 - Storage BD TimescaleDB
 - Alert si PDL missing ou format invalide
 - (T1 2026 : API Data Connect automated)

US-006 [M] En tant que système, je calcule répartition mensuelle
 AC:
 - Récupère courbes import + clé répartition (statique default)
 - Calcul pour chaque consommateur : somme kWh alloués période
 - Valide : total kWh alloués ≤ production + imports (conservation énergie)
 - Stocke résultat allocation table
 - Génère report CSV "allocation_[mois].csv"

US-007 [M] En tant que PMO, je génère factures
 AC:
 - Lance "Générer factures [mois]"
 - Système récupère allocations + tarif convenu
 - Calcul montant HT par participant : kWh × tarif
 - Ajout TVA 20% (si PMO non-exonérée)
 - Génération PDF facture (template standard)
 - Envoi email participant + storage (vault)
 - Mark status "sent" (suivi)

US-008 [M] En tant que PMO, je suivi paiements
 AC:
 - Dashboard "Paiements" listant toutes factures + statut (draft/sent/paid/overdue)
 - Marquer facture comme payée (checkbox manual)
 - Envoyer relance email participant (templated)
 - Export list overdue (list participants relance)
 - KPI : % paid factures, days overdue 

Sprint 7–9 : Wizard ACC + Go-Live US-009 [M] En tant que PMO, je crée opération ACC via wizard
 AC:
 - Step 1 : Infos opération (nom, type PMO, secteur)
 - Step 2 : Ajouter producteurs (PDL, puissance kWc, iban)
 - Step 3 : Ajouter consommateurs (PDL, type [particulier|entreprise|public], usage MW-h estimé)
 - Step 4 : Configurer clé répartition (default pro-rata ou manual % par participant)
 - Step 5 : Sélectionner fournisseur complément (list hardcoded T0, connecteur T1)
 - Step 6 : Review & générer docs (convention Enedis pré-complétée, statuts, contrat)
 - Step 7 : Submit dossier (validation avant)
 - Output : status "submitted to Enedis", tracking ID, expected validation 3–6 sem

US-010 [M] En tant que PMO, j'envoie invitations participants
 AC:
 - Dans portal, bouton "Invite participants"
 - Système génère email unique par participant (avec link + code)
 - Participant reçoit email → click link → signup flow US-003
 - PMO voit statut signature (% of list)
 - Email reminder auto après 1 sem si unsigned 

### T1 Phase Extend (Sprint 10–15, Apr–Jun 2025) US-011 [S] En tant que PMO, j'intègre courbes Enedis via API (Data Connect)
 AC:
 - Authentification Enedis (OAuth2 client cred)
 - Subscription à endpoints "participants" (prod + conso)
 - Récupe courbes 15 min auto (scheduled daily 2 AM)
 - Stockage BD + alert si fetch fail
 - Dashboard : "Données Enedis à jour : [timestamp]"

US-012 [S] En tant que PMO, je déclare opération via API Enedis
 AC:
 - Submit dossier opération ACC (US-009) lance API call
 - Body : PMO data, participants list, clés, convention
 - Récep response Enedis : request ID + status "en attente validation"
 - Polling status quotidien (via API)
 - Alert PMO si status change (ex: "validée" ou "demande info supplémentaire")

US-013 [S] En tant que PMO, je mets en place SEPA
 AC:
 - Section "Paiements SEPA" dans PMO workspace
 - Générer mandats SDD (texte standard + code mandat)
 - Participant signe mandat (e-sig, ou print+post)
 - Mandat stocké encrypted vault
 - Test prélèvement € (crédit sample, reversible)
 - Prélèvements auto chaque mois (batch, post-facturation)
 - Dashboard "Prélèvements" : list mandates, % collectés, failures + retry logic

US-014 [S] En tant que energy manager, je suivi conformité Décret Tertiaire (bêta)
 AC:
 - Import site tertiaire (surface m², année référence, type [bureaux|école|etc])
 - Baseline : 2010–2019 conso (upload historique ou estimation)
 - Trajectory compute : (conso 2025 climate-corrigée) vs (baseline × (100–40)%)
 - Dashboard : % atteinte objectif 2030
 - Alert si risque dépassement
 - Export report (simple pour T0)
 - (T1 : intégration full OPERAT API) 

### J.3 – Priorisation RICE User Story R (Reach) I (Impact) C (Confidence) E (Effort) RICE Score Sprint US-001 (Auth) 100 5 100 5 1000 1–2 US-002 (Participants list) 100 4 100 8 500 2–3 US-003 (Participant signup) 100 4 90 10 360 3–4 US-004 (Participant dashboard) 100 3 90 12 225 4–5 US-005 (CSV import Enedis) 100 4 80 8 400 5–6 US-006 (Settlement calc) 100 5 90 15 300 6–7 US-007 (Billing PDF) 100 4 90 10 360 7–8 US-008 (Payment tracking) 100 3 85 12 212 8–9 US-009 (Wizard ACC) 100 5 85 20 212 6–9 US-010 (Invitations) 100 3 95 5 570 8–9 US-011 (API Data Connect) 100 5 70 15 233 10–12 (T1) US-012 (API ACC Enedis) 100 5 75 12 312 10–12 (T1) US-013 (SEPA) 100 4 70 20 140 12–14 (T1) US-014 (Compliance lite) 30 4 60 15 48 13–15 (T1) 

## K) Annexes & Ressources 

### K.1 – Textes Réglementaires Clés (Referencing) 
- Code de l’énergie (Articles L315-1 à L315-3, R315-1 à R341-7) : définitions ACC, cadre PMO, clés répartition, modalités Enedis 
- Décret n°2016-711 (Autoconsommation individuelle & collective) : régime juridique 
- Arrêté 21 février 2025 (Journal Officiel 5 mars 2025) : seuils 5–10 MW, périmètre 20 km dérogation 
- Décret n°2024-1023 (13 novembre 2024) : modalités traitement Enedis pre-deployment 
- Loi APER 2023 (Accélération Production ENR) : obligation solarisation parkings, frameworks 
- Directive UE 2019/944 (Electricity Market Directive) : background energy sharing concept 

### K.2 – Guides Enedis (2025) 
- Note externe Enedis-OPE-CF_06E (Modalités traitement demandes ACC – phase amont) 
- Note externe Enedis-OPE-CF_07E (Modalités mise en œuvre opération ACC – phase opérationnelle) 
- Modèle Convention Enedis PMO-GRD (standard template) 
- Data Connect – Modèle Contrat (accès données) 
- Guide Pédagogique ACC (Enedis + EDF) 

### K.3 – Ressources Marché & Secteur 
- Enerplan / SER : baromètre ACC annuel, positionnement réglementaire 
- FNCCR : appuis collectivités, montage ACC, bases données 
- ADEME : aides financières, guides économie, plateforme OPERAT 
- RTE : bilans électriques, prévisions consommation 2030, scenarios mix 
- CRE : tarifs achat, appels d’offres, décisions régulatoires 
- PV Magazine / Les Échos : actualité secteur, analyses marché 

### K.4 – Templates Documents (Intégrés PROMEOS MVP) 
- Statuts PMO (association SAS SARL SEM) – 3 variantes 
- Convention Enedis PMO – pré-complétée template 
- Contrat interne participant – droits/devoirs 
- Mandat SEPA – format standard CBI 
- Facture interne ACC – format compliant TVA 
- Rapport clés répartition – audit trail 

### K.5 – KPI Dashboard PMO (Suivi Opérationnel) 

┌────────────────────────────────────────────────────────┐ │ PROMEOS PMO Dashboard – Opération ACC [Nom] │ ├────────────────────────────────────────────────────────┤ │ 📊 ÉNERGIE LOCAL │ │ ├─ Production j [kwh] : 480 kWh │ │ ├─ Consommation j [kwh] : 350 kWh │ │ ├─ Autoconso % : 72% (très bon!) │ │ ├─ Surplus injecté : 130 kWh (pour vente/stockage) │ │ │ │ 💰 FINANCE │ │ ├─ Factures mois [N] : 12 (tous sent) │ │ ├─ Encaissements : 10/12 (83%) │ │ ├─ Retards : 1 participant (relance auto en cours) │ │ ├─ Cash position : €2,450 (trésorerie PMO) │ │ │ │ 👥 PARTICIPANTS │ │ ├─ Actifs : 15/15 │ │ ├─ Documents signés : 15/15 (100%) │ │ ├─ Mandats SEPA : 12/15 (80%, 3 en cours) │ │ │ │ 📋 CONFORMITÉ │ │ ├─ Convention Enedis : ✓ signée (05-mar-2025) │ │ ├─ Statut opération : ✓ Live │ │ ├─ Données Enedis : ✓ à jour (02-jan 14:30) │ │ ├─ Audit trail : ✓ 100% documenté │ │ │ │ ⚠️ ALERTES │ │ ├─ Participant X en retard 35j (relance email sent) │ │ ├─ Demande sortie participant Y (processus en cours) │ │ ├─ Pas de données Linky 2 heures (check Enedis) │ │ │ │ [📥 Import Enedis] [💾 Backup] [📤 Export] [⚙️ Config] │ └────────────────────────────────────────────────────────┘ — 

## Executive Summary (Synthèse finale) 

PROMEOS , en intégrant trois briques modulaires (Data & Conformité, ACC Starter, ACC Ops) , devient l’unique plateforme holistique adressant le marché ACC en explosion (+144% opérations/an, 161 MW 2025). 

Défis résolus : 
- Montage ACC lourd (12–24 mois) → 3–6 mois via automation API + templates 
- Exploitation manuelle (80% Excel) → 100% digital shadow billing + SEPA 
- Conformité fragmentée (multi-réglementations) → cockpit unique Tertiaire + BACS + APER + accise 
- Clés statiques sous-optimales → IA dynamique +5–15% autoconso 

Avantage compétitif : 
- Enogrid/EnoPower = leader ACC pur ; absent sur compliance tertiaire 
- Deepki/Advizeo = leaders compliance ; absent sur ACC opération 
- PROMEOS seul combine les deux → valeur client 3–5× supérieure 

Scénario Central 2030 : 
- 1 200 opérations gérées, 120 000+ participants, 1 800 MW 
- Revenu PROMEOS : €2–5M net profit (SaaS scaling + flex monetization) 
- Impact marché : standardisation juridique/opérationnelle, scaling collectivités/bailleurs, démocratisation AMEP (particuliers) 

Prochaines étapes (T0 2025) : 
1. Valider MVP 10–12 sem (User Testing + Beta 5–10 opérations) 
2. Finaliser roadmap API Enedis (Q1 2025 négociations) 
3. Securiser 3–5 « anchor customers » (collectivité/bailleur pour pilots) 
4. Levée seed financing (€800k–1.2M) pour dev scale + go-to-market 

Dates sources utilisées : 5 décembre 2024 – 30 décembre 2025 (données Enedis, Enogrid, TECSOL, EDF OA, CRE, Enedis guides 2025, arrêtés législatifs jusqu’à février 2025). 

10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 

⁂ 
- https://enogrid.com/croissance-record-de-lautoconsommation-collective-en-2025/ ↩︎ 
- https://enogrid.com/croissance-record-de-lautoconsommation-collective-en-2025/ ↩︎ 
- https://www.enedis.fr/media/2069/download ↩︎ 
- https://enogrid.com/croissance-record-de-lautoconsommation-collective-en-2025/ ↩︎ 
- https://enogrid.com/autoconsommation-collective-decembre-2024/ ↩︎ 
- https://enogrid.com/autoconsommation-collective-decembre-2024/ ↩︎ 
- https://enogrid.com/croissance-record-de-lautoconsommation-collective-en-2025/ ↩︎ 
- https://enogrid.com/croissance-record-de-lautoconsommation-collective-en-2025/ ↩︎ 
- https://www.pv-magazine.fr/2025/01/13/autoconsommation-collective-le-nombre-doperations-actives-double-en-un-an-seulement-et-atteint-74-mw/ ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1lBtWOWrphJWbg7S_YtjW94q35HXVfor6/cbc5a5fe-89e0-4089-98f3-eb3b0cc6e142/Plan-de-MVP-et-Offre-PROMEOS-Micro-fournisseur-local-augmente.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1j_N_5fswFsyr83tshdBCH85xHdY68HGp/4276431a-acfd-4bdc-8015-f93377a7e353/Les-Echos-Stockage-delectricite.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/14_hZ7KEgKXrb9EZvlEuCnWr1vMqP3m4s/5e0a1929-0cec-4cd7-95a6-261f3b12ab09/Les-Echos-Marche-de-lelectricite-la-bataille-est-relancee.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1Ht6JkKn-jF2zcrUZjjNl1tbBjARaZoKr/77b504f5-56db-4bac-8e92-53c0055d3c59/Les-Echos-Le-marche-des-data-centers.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1XCfazetekY-wv6g9o1ZOFNuZv7ny67Ed/f65e719d-c4d3-4af2-851d-d6afd6cf26d6/Les-Echos-Le-nouvel-age-dor-du-marche-du-photovoltaique.pdf ↩︎ 
- https://terresolaire.com/Blog/rentabilite-photovoltaique/tarif-cre-photovoltaique-2025/ ↩︎ 
- https://www.edf.fr/sites/default/files/contrib/entreprise/cgv-tarifs-reglementes/2020/enedis-for-cf_02e_annexe_1bis.pdf ↩︎ 
- https://wesmart.com/es/blog/autoconsommation-collective-france-2025 ↩︎ 
- https://zendure.fr/blogs/news/evolution-prix-rachat-edf-photovoltaique-guide-2026 ↩︎ 
- https://www.enedis.fr/media/2127/download ↩︎ 
- https://www.cre.fr/actualites/toute-lactualite/la-cre-publie-les-nouveaux-tarifs-et-primes-relatifs-aux-installations-photovoltaiques-implantees-sur-batiment-hangar-ou-ombriere-dune-puissance-crete-installee-inferieure-ou-egale-a-500-kw.html ↩︎ 
- https://www.enedis.fr/media/1924/download ↩︎ 
- https://www.gossement-avocats.com/blog/autoconsommation-collective-publication-de-larrete-du-21-fevrier-2025-modifiant-les-criteres-dune-operation-dautoconsommation-collective-etendue-et-prevoyant-une-nouvelle/ ↩︎ 
- https://www.cre.fr/actualites/toute-lactualite/la-cre-publie-les-nouveaux-tarifs-et-primes-pour-les-installations-photovoltaiques-implantees-sur-batiment-hangar-ou-ombriere-dune-puissance-crete-installee-inferieure-ou-egale-a-500-kwc.html ↩︎ 
- https://www.enedis.fr/acceder-aux-donnees-fournies-par-enedis ↩︎ 
- https://www.idex.fr/le-blog/la-fin-du-s21-opportunite-ou-menace-pour-vos-projets-solaires ↩︎ 
- https://help-center.meteocontrol.com/en/vcom-cloud/latest/vcom-enedis-api-1 ↩︎ 
- https://www.journal-photovoltaique.org/les-actus/seuils-de-puissance-augmentes-pour-lautoconsommation-collective/ ↩︎ 
- https://www.les-energies-renouvelables.eu/conseils/photovoltaique/tarif-rachat-electricite-photovoltaique/ ↩︎ 
- https://rencontres-france-hydro-electricite.fr/wp-content/uploads/2024/06/Sunflow-ACC-FHE-.pdf ↩︎ 
- https://www.apem-energie.fr/%F0%9F%9A%A8-nouvelle-evolution-pour-lautoconsommation-collective-en-france-%F0%9F%9A%A8/ ↩︎ 
- https://www.cre.fr/actualites/toute-lactualite/la-cre-procede-a-des-evolutions-techniques-sur-la-methode-de-fixation-des-tarifs-reglementes-de-vente-delectricite-en-vue-du-prochain-mouvement-fevrier-2026-1.html ↩︎ 
- https://blog-gestion-de-projet.com/capex-opex-projet/ ↩︎ 
- https://www.oecd.org/content/dam/oecd/fr/publications/reports/2009/01/overcoming-barriers-to-administrative-simplification-strategies_g1gha83f/9789264060630-fr.pdf ↩︎ 
- https://www.enedis.fr/media/2070/download ↩︎ 
- https://www.softyflow.io/guide-capex-opex/ ↩︎ 
- https://coherence-energies.fr/services/etude-mise-en-place-et-suivi-doperation-dautoconsommation-collective-acc/ ↩︎ 
- https://www.enedis.fr/media/1886/download ↩︎ 
- https://www.cost-house.com/post/c-est-quoi-opex-capex-p-l-cashout ↩︎ 
- https://hubwatt.fr/autoconsommation-collective-tout-savoir-sur-la-reglementation-actuelle/ ↩︎ 
- https://www.enedis.fr/media/4770/download ↩︎ 
- https://www.youtube.com/watch?v=rVXj8xJgrWk ↩︎ 
- https://enogrid.com/faq-autoconsommation-collective/ ↩︎ 
- https://www.enedis.fr/media/1881/download ↩︎ 
- https://adherents.energie-partagee.org/wp-content/uploads/2024/02/guide-acc-citoyenne-fevrier-2024-1.pdf ↩︎ 
- https://www.chemins-publics.org/articles/simplification-et-reforme-administrative-de-lambition-consensuelle-a-une-rupture-dans-lapproche-et-les-methodes ↩︎ 
- https://www.urbanisme-puca.gouv.fr/IMG/pdf/rapport_final_vf.pdf ↩︎ 
- https://www.enedis.fr/sites/default/files/documents/pdf/autoconsommation-collective-guide-pedagogique.pdf ↩︎ 
- https://www.enedis.fr/comment-monter-un-projet-dautoconsommation-collective ↩︎ 
- https://adherents.energie-partagee.org/wp-content/uploads/2023/11/note-acc-information.pdf ↩︎ 
- Analyse-experte-Obligations-reglementaires-module-Data-Conformite-multi-energie-France-B2B.pdf ↩︎ 
- https://solairepv.fr/wp-content/uploads/SolairePVEnFranceV3.1.pdf ↩︎ 
- https://www.fnccr.asso.fr/article/dernier-appel-a-projets-destine-a-toutes-les-collectivites-francaises/ ↩︎ 
- https://hubwatt.fr/vente-delectricite-en-autoconsommation-collective/ ↩︎ 
- https://actu.xpair.com/actualites/le-photovoltaique-va-representer-80-de-la-croissance-mondiale-des-capacites-enr-d-ici-a-2030 ↩︎ 
- https://enogrid.com/la-reglementation-sur-lautoconsommation-collective-evolue-en-2025/ ↩︎ 
- https://www.afg.asso.fr/app/uploads/2025/09/PS-facturation-e_SLIDES.pdf ↩︎ 
- https://www.mordorintelligence.com/fr/industry-reports/solar-photovoltaic-market ↩︎ 
- https://www.fnccr.asso.fr/article/projet-dextension-du-perimetre-de-lautoconsommation-collective/ ↩︎ 
- https://data.megalis.bretagne.bzh/OpenData/213500069/Deliberation/2025/790602/54cf47b4dbd49e2f216c6af796f2f7b33dc87f69131d2d028532d0f88815c43a.pdf ↩︎ 
- https://www.les-energies-renouvelables.eu/conseils/photovoltaique/les-chiffres-essentiels-du-photovoltaique/ ↩︎ 
- TECSOL-Formation-PV-ACC-06-2025.pdf ↩︎ 
- https://www.fnccr.asso.fr ↩︎ 
- https://www.edf-oa.fr/sites/oa/files/2025-08/autoconsommation-collective-guide-pedagogique_vdef.pdf ↩︎ 
- https://www.france-renouvelables.fr/wp-content/uploads/2025/10/OBSERVATOIRE_systeme_EnR_2025_VF.pdf ↩︎ 
- https://programme-cee-actee.fr/wp-content/uploads/2025/10/Guide_solarisation-V2.pdf ↩︎ 
- https://entreprises-collectivites.engie.fr/wp-content/uploads/2024/08/Autoconsommation-collective-Comprendre-sa-facture.pdf ↩︎ 
- https://www.civisol.fr/blog/188/perspectives-marche-solaire-europeen.html ↩︎ 
- https://www.auvergnerhonealpes-ee.fr/api/fileadmin/mediatheque_Cdr/Documents/Commande_publique_durable/Synthese_webinaire_achats_durables_electricite_renouvelable_21nov25.pdf ↩︎ 
- https://ressources.opentalent.fr/space/FAQ/2492227/Sp+cial+collectivit+s+territoriales ↩︎ 
- https://www.lechodusolaire.fr/photovoltaique-quel-avenir-en-france/ ↩︎ 
- https://www.seine-et-marne.gouv.fr/contenu/telechargement/66557/548706/file/Table%20ronde%20n%C2%B02_4_Gwennyn%20Yardin_SDESM.pdf``` ↩︎ 
- Plan-de-MVP-et-Offre-PROMEOS-Micro-fournisseur-local-augmente.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1UJOz5hSHG5r50Rr-ct61Dg8G61b5miJL/66b57442-5ab5-46ba-9e32-fb56c7d97afb/Brique-1-Data-Conformite-_-Un-Systeme-Expert-Proactif-Pas-un-Cockpit-Passif.pdf ↩︎ 
- https://ppl-ai-file-upload.s3.amazonaws.com/connectors/google_drive/1-dt7B1rcORxQA26oRLWkRxrv7l-5pdtP/ad0cab5c-e0b7-43ae-b29b-085ed048de9d/Reglementations-energetiques-_-donnees-a-surveiller-et-formules-de-calcul.pdf ↩︎