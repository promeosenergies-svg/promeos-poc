# Ingestion Report: LEVIERS_MARCHE_2025

**Title:** Etat 2025, Leviers de Marche et Plan de Simplification
**Content Hash:** 9c7e3609b3e1fb51
**Ingested at:** 2026-02-11T19:35:50

## Pipeline Summary

| Step | Count |
|------|-------|
| Sections extracted | 84 |
| Chunks generated | 55 |
| YAML drafts created | 55 |

## Drafts by Type

- **knowledge**: 38
- **rule**: 17

## Drafts by Domain

- **acc**: 29
- **facturation**: 2
- **reglementaire**: 10
- **usages**: 14

## Sections

1. **Autoconsommation Collective en France – État 2025, Leviers de Marché & Plan de Simplification (2026–2030)** (level 1, 7 words)
2. **Executive Summary** (level 2, 173 words)
3. **A) Définition & Cadre Réglementaire ACC (2025)** (level 2, 0 words)
4. **A.1 – Définition et Rôles** (level 3, 153 words)
5. **A.2 – Cadre Réglementaire (Arrêté 21 février 2025, Journal Officiel 5 mars 2025)** (level 3, 0 words)
6. **Critères d’Éligibilité Critère ACC Classique ACC Étendue Remarques Puissance cumulée max (MW) 3 5 (généraliste) / 10 (collectivités) Arrêté 21/02/2025 : seuil 5 MW pour toutes ; 10 MW dérogation EPCI à fiscalité propre Rayon géographique 2 km autour point production 20 km (zones rurales, cas spécifiques) Décret 2024-1023 Participants min/max 2 producteurs OU 1 prod + consommateurs Même Structure ouverte ou fermée Secteurs Tous (résidentiel, tertiaire, agricole, zones d’activités) Idem Intérêt croissant PME/industriels Périmètre réseau Enedis + ELD (entreprises locales distribution) Idem Hors RTE (transport)** (level 3, 0 words)
7. **Obligations Contractuelles Enedis Élément Obligation Modalités Convention Enedis Signature avant démarrage opération Modèle Enedis pré-rempli, 3–6 semaines de traitement Clés de répartition Statique, dynamique ou “par défaut” Modifiables avec préavis 15 jours ouvrés ; par défaut = au prorata consommations Compteurs communicants Obligatoires pour tous participants Linky générant données 30–60 min Déclaration API Transmission PMO + produits + consommateurs via guichet Enedis Depuis 2025 : automatisation accélérée, délai 3 mois max Données temps réel Courbes de charge 15 min (API Data Connect) Enedis transmet via portail SGE ou API tiers Sortie participant Possibilité entrée/sortie avec préavis 30j Formalités simplifiées si pas contrat de long terme** (level 3, 22 words)
8. **A.3 – Points Réglementaires “Painfully Complex” & Risques de Non-Conformité Friction Cause racine Exemple concret Risque Statut juridique PMO Code monétaire (L315-1) exige personne morale, pas de flou sur structure Confusion : peut-on faire PMO = association informelle ? Enedis refuse Rejet dossier, retard 6+ mois Licences fournisseur ACC = acte de fourniture locale ; PMO peut être requalifiée fournisseur d’énergie si dépasse seuils PMO loue espace toit, vend excédent : est-ce fourniture ? Fiscalité appliquée Amende jusqu’à 7 500 €, status légal incertain Accise électricité Accise TICFE = 0 € ACC (depuis 2022), mais confusion factures si facturation interne non claire Client reçoit facture PMO (accise 0) + facture fournisseur (accise complète) pour même électricité Double-imposition, refus client, conflit Clé de répartition Statique mensuelle = simple mais inefficient (pics ignorés) ; dynamique = optimal mais calcul complexe, Enedis lent PMO veut passer clé statique → dynamique : nécessite accord Enedis + préavis 15j + refonte contrats Délai 2–3 mois, perte valeur si production haut varié Données manquantes Compteur défaillant, historique incomplet, consommation estimée → allocation incorrecte Participant entre après démarrage : données rétroactives ? Attribution au pro-rata ou précision réelle ? Litige participant, correction longue Changement fournisseur participant Fournisseur sortant/entrant doit notifier Enedis pour mise à jour contrats Participant quitte pour OA ailleurs : Enedis reçoit demande fournisseur N+1, mais PMO pas au courant → clash Interruption supply 48–72h, churn participant Conformité territoriale Rayon 2 km (ou 20 km dérogation) mesuré géométriquement → GIS complexe Nouveau consommateur à 2.1 km : accepté ou pas ? Quelle preuve ? Rejet tardif, projet à revoir Fiscalité PMO PMO peut être association non lucrative (TVA exonérée) ou SAS (TVA 20%) → choix impacts coûts client Changement statut PMO après montage : révision TVA rétro ? Conflit avec participants, refonte devis** (level 3, 0 words)
9. **A.4 – Matrice Obligations / Acteurs / Données / Pénalités Obligation Texte Responsable Données requises Échéance Sanction non-conformité Automatisation possible Déclaration opération Enedis Code Énergie R315-1 PMO PDL, puissance, clés, participants Avant mise en service Refus mise en service ✓ API Enedis Convention Enedis Décret 2016-711 PMO + GRD Accord mutuel, clés, fournisseur complément 3–6 sem. traitement Suspension opération Partiellement (auto-génération documents) Clés de répartition Code Énergie R315-1 PMO + Enedis validation Calcul (statique/dynamique), tous paramètres Avant démarrage + chaque changement Allocation erronée, litige participant ✓ Moteur calcul déterministe Courbes de charge Enedis Décret RGCC GRD 15 min par PDL Quotidien / mensuel Impossible facturation ✓ API Data Connect Facturation PMO-consommateurs Code Monétaire + CGI PMO KWh alloués × tarif convenu Mensuel ou trimestriel Litige, impayé, sortie participant ✓ Billing automatisé (shadow) Paiements SEPA Norme SEPA PMO (collecte) IBAN, mandat SDD Avant prélèvement Impayé, relance manuelle, coûts ✓ Intégration SEPA api Conformité vis-à-vis fournisseur complément Contrat GRD-F + CU Fournisseur + PMO Accord tarif, conditions Continu Fourniture interrompue ✓ Notifications EDI GRD Déclaration fiscale ACC (si revente) Loi APER 2023 PMO (si applicable) Chiffre affaires, base imposable Annuel (31 mai) Redressement fiscal ✓ Export données comptables** (level 3, 0 words)
10. **B) Marché ACC 2025 : Taille, Dynamique, Économie** (level 2, 0 words)
11. **B.1 – Données de Marché Actualisées (décembre 2024 – juin 2025) Métrique Valeur Tendance Source Opérations actives (juin 2025) 1 111 +144% vs juin 2024 (454) Enedis Open Data, Enogrid 4 5 Opérations (déc. 2024) 698 +129% vs déc. 2023 (305) Enedis 6 Puissance installée (juin 2025) 161 MW +117% yoy (74 MW déc. 2024) Enedis 7 Participants totaux (juin 2025) 10 600+ +26% vs déc. 2024 (8 342) Enedis 8 Producteurs 1 700 ~16% du total Enedis Consommateurs 10 600+ ~84% du total Enedis Puissance moyenne par opération 145 kVA +96% vs 2024 (74 kVA) Enedis Participants moyen par opération 10–12 Stable Enedis Régions dominantes Occitanie (94), AURA (98), Grand Est (81), BFC Croissance équilibrée Enedis, PV Magazine 9** (level 3, 0 words)
12. **B.2 – Segmentation Cas d’Usage Rentables vs Difficiles** (level 3, 0 words)
13. **Cas Rentables (2025)** (level 3, 205 words)
14. **Cas Difficiles (Freins majeurs)** (level 3, 153 words)
15. **B.3 – Unit Economics Type ACC** (level 3, 0 words)
16. **Scénario : Collectivité 400 kWc, 15 participants, 20 ans** (level 3, 186 words)
17. **C) Croissance 2026–2030 : Scénarios & Drivers** (level 2, 0 words)
18. **C.1 – Trois Scénarios Build** (level 3, 0 words)
19. **Scénario 1 : PRUDENT (Croissance 50% annuelle)** (level 3, 85 words)
20. **Scénario 2 : CENTRAL (Croissance 100% annuelle jusqu’2027, 60% après)** (level 3, 108 words)
21. **Scénario 3 : ACCÉLÉRÉ (Croissance 150% annuelle)** (level 3, 127 words)
22. **C.2 – Signaux Faibles à Surveiller (Wildcards) Signal Impact positif ACC Probabilité 2026 Actions PROMEOS Suppression licence fournisseur PMO Reduction friction legal, scaling AMEP +300% Moyen (30–40%) Briefing legal, advoc régulatoire Intégration EU Energy Sharing Directive Cross-border ACC pilotes, mutualisation internationale Faible (10%) Monitor EU legislation, R&D Baisse coûts batteries Stockage intra-ACC standard, taux autoconso +20% Moyen-haut (50–60%) Intégration batterie dans Ops v2 Démocratisation IA clés dynamiques Taux autoconso +5–15%, réduction prix acc attractif Haut (70–80%) MVP clé dynamique T4 2025 Obligation ACC tertiaire (décret renforcé) Doublement opérations collectivités 2027–2028 Moyen (40%) Compliance module “ACC-ready” Crise tarif énergie (prix spot >€150/MWh) Rentabilité ACC x2–3, frénésie investissement Moyen (30–50%) Pricing model flexible spot Saturation réseau distribution local Effacement producti onrequis, ACC devient nécessaire Moyen (30–40%) local Flexible orchestration v2** (level 3, 0 words)
23. **D) Les 10 Leviers Concrets pour Accélérer Croissance ACC (2025–2026)** (level 2, 0 words)
24. **1. Automatisation API Enedis (DataConnect + ACC)** (level 3, 37 words)
25. **2. Template juridique standardisé PMO (par type : association, SAS, SEM)** (level 3, 43 words)
26. **3. Clés de répartition dynamiques (IA prédictive)** (level 3, 42 words)
27. **4. Shadow Billing automatisé + SEPA** (level 3, 36 words)
28. **5. Intégration ERP/GTB clients (API connecteurs)** (level 3, 38 words)
29. **6. Conformité multi-réglementation natif (Décret Tertiaire, BACS, APER, accise)** (level 3, 33 words)
30. **7. Simplification onboarding participant (KYC express + e-signature)** (level 3, 38 words)
31. **8. Agrégation multi-ACC pour PMO portfolio (reporting centralisé)** (level 3, 40 words)
32. **9. Standardisation données comptables (export module OPERAT + BACS)** (level 3, 33 words)
33. **10. Marché de data/flex (API exposée partenaires : agrégateurs, VPP, DR)** (level 3, 44 words)
34. **E) Les 10 Irritants Opérationnels Majeurs & Solutions d’Automatisation # Irritant Cause Exemple Friction Solution Process Solution Tech Gain 1 Montage PMO lourd Choix statut juridique flou + docs custom Collectivité lance ACC, avocat propose 3 structures → débat 2 mois Template bancaire, critères de sélection smart PROMEOS suggère structure basée sur secteur/taille → 1 clic -6 sem 2 Participants tardent inscription Onboarding papier, peur clauses, manque confiance Chef projet relance 10 fois pour mandats signés Flow digital intégré + explications contextuelles PROMEOS : email + lien unique, e-sign Universign, MFA -2 sem 3 Enedis demande revérifications données PDL mal formatés, participants douteux, doublons Enedis refuse dossier, demande recalcul clés → 3 sem attente Validation données Enedis dans PROMEOS avant soumission Checker API Enedis + BDD PDL Enedis en temps réel -3 sem 4 Changement fournisseur participant crée chaos Nouveau fournisseur pas au courant ACC → coupe électricité Participant quitte fournisseur A pour OA ailleurs, confusion contrats Procédure synchronisation Enedis → fournisseurs automatisée PROMEOS notifie Enedis et fournisseurs N+1 en batch -48h risque 5 Clé statique = autoconso sous-optimal Clé 50/50 mais prod 2000 kWh/j de 10–14h, demande pic 18–22h Taux autoconso réel 35% vs potentiel 70% ; client mécontentement Passage clé statique → dynamique PROMEOS moteur IA : propose clé optimale, met à jour auto chaque mois +15–20% autoconso 6 Facturation = cauchemar Excel Ventilation manuelle 12 participants × 30 jours, recalculs Erreur calcul : participant A facturé 2x, doit rembourser Facturation entièrement automatisée PROMEOS shadow billing : calcul jour J, facture 24h après relevé Enedis -15 jours clôture 7 Impayés participants trop fréquents Rappels manuels inefficaces, démotivation PMO 30% participants en retard paiement > 30j, recouvrement coûte €200/an Prélèvement automatique SEPA + escalade smart PROMEOS SEPA intégré + notifications SMS/email smart, astreintes auto Trésorerie +95% vs 70% 8 Entrée/sortie participant lente + coûteuse Changement clés, recalcul contrats, notification Enedis manuelle Participant veut partir : 4 sem délai, coûts réécriture docs Automation contrats, re-calc clé, notification batch Enedis PROMEOS re-deploy clés < 48h, notifications Enedis API batch Churn risk –30% 9 Audit annuel et conformité = panique Dossier éparse : courbes Enedis, factures, contrats, preuves Auditeur demande historique 5 ans, traces décisions clés → racontage Coffre-fort numérique centralisé + audit trail crypto PROMEOS vault : tous documents versionnés, tamponné, queryable -3j audit 10 Communication Enedis lente et formelle Délais 3–6 mois pour validation, feedback > bureaucratique PMO relance 10 fois, Enedis pas au courant changement clés → dossier bloqué Portal standard Enedis (SGE) utilisé mais via API PROMEOS PROMEOS = proxy smart : agrège demandes batch, suit statut real-time -50% délai Enedis** (level 2, 0 words)
35. **F) Design Process + Produit pour Cycle Projet 12–24 mois → 3–6 mois** (level 2, 0 words)
36. **F.1 – Phases Actuelles vs Optimisées Phase Durée Actuelle Durée Optimisée PROMEOS Contribution 1. Diagnostic faisabilité 4–8 sem 1–2 sem Simulateur ACC 5 min (PDL input → résultat TRI auto) 2. Montage PMO (statut + docs) 8–12 sem 2–4 sem Template SaaS (association/SAS/SEM), assistant config, e-doc 3. Recrutement participants 6–12 sem 2–4 sem Portal auto-invitation, KYC express digital, e-sig 4. Valeurs fournisseur complément 2–4 sem 1 sem Connecteur fournisseurs (EDI batch), comparatifs auto 5. Constitution dossier Enedis 4–8 sem 1 sem Checker données Enedis API, génération auto convention, API submit 6. Validation Enedis 4–6 sem 2–3 sem Suivi statut real-time SGE API, escalade auto si > 3 sem 7. Test & démarrage opération 2–4 sem 1 sem Simulation clés, shadow testing, batch Enedis, quick go-live TOTAL 30–54 sem (6–12 mois) 10–20 sem (2.5–5 mois) Réduction 70–80%** (level 3, 0 words)
37. **F.2 – Checkpoints Clés Accélération (PMO/PROMEOS)** (level 3, 204 words)
38. **F.3 – Modèle Economique PROMEOS pour Montage Rapide** (level 3, 117 words)
39. **G) PROMEOS – Intégration Brique ACC dans Cockpit B2B Fournisseur 2.0** (level 2, 0 words)
40. **G.1 – Positionnement “Micro-fournisseur Local Augmenté”** (level 3, 25 words)
41. **Package 1 : ACC Starter (Incubation, 3–6 mois déploiement)** (level 3, 57 words)
42. **Package 2 : ACC Ops (Exploitation courante, 3+ ans)** (level 3, 67 words)
43. **Package 3 : Data & Conformité (Réglementation B2B, toutes organisations)** (level 3, 69 words)
44. **G.2 – Architecture Logicielle (MVP → v1 → v2)** (level 3, 0 words)
45. **MVP (T0–T3 2025, ~10–12 sem dev)** (level 3, 158 words)
46. **V1 (T3–T4 2025, +10 sem dev)** (level 3, 47 words)
47. **V2 (2026, +20 sem dev)** (level 3, 40 words)
48. **G.3 – Roadmap MVP (90 j / 180 j / 12 mois) & Backlog RICE** (level 3, 0 words)
49. **Roadmap Temporelle ```** (level 3, 320 words)
50. ****G.4 – PRD Mini (Problem → Features → Success Metrics)**** (level 3, 0 words)
51. ****Problem**** (level 4, 48 words)
52. ****Users & Jobs-to-be-Done**** (level 4, 81 words)
53. ****Features Clés (MVP)**** (level 4, 132 words)
54. ****Data Model (Schéma Simplifié)**** (level 4, 84 words)
55. **Success Metrics (KPIs) Métrique Target MVP Target V1 Owner Délai montage ACC < 8 sem < 6 sem Prod % dossiers acceptés Enedis (1ère tentative) > 95% 100% Tech Taux autoconsommation (vs clé statique) 60–65% 70–75% (avec clé dynamique) Product Taux de couverture facturation > 95% 100% Ops Impayés (% facturation totale) < 5% < 2% Finance NPS participants > 6/10 > 8/10 UX Temps support P1 (réponse) < 4h < 1h Support Churn opération annuelle < 10% < 5% Growth CAC (coût acquisition client PMO) < €200 < €100 Marketing LTV/CAC ratio > 3x > 5x Finance** (level 3, 0 words)
56. **H) Benchmark Concurrence & Espaces Blancs** (level 2, 0 words)
57. **H.1 – Paysage Concurrentiel (2025)** (level 3, 0 words)
58. **Catégorie 1 : EMS Généralistes (Energy Management Systems) Acteur Positionnement Offre ACC Offre Compliance Limites Différenciation Advizeo (Hager) Dashboard énergie multi-sites Non (aucune) Décret Tertiaire baseline Pas ACC, pas settlement Puissance analyse prédictive Deepki SaaS data énergie buildings Non Tertiaire + BACS Pas ACC, support basique Intelligence données immobilier Datanumia Intelligence énergétique Non Monitoring coûts Pas ACC, pas settlement Billing énergétique mais pas ACC WeSmart Plateforme locale ENR Partiel (ACC consultation) Non ACC limité, pas automatisation UI attrayante, modèle éducatif** (level 3, 14 words)
59. **Catégorie 2 : Plateformes ACC Spécialisées Acteur Positionnement Opérations gérées Segmentation Modèle Limites Différenciation Enogrid/EnoPower Leader ACC opération 200+ opérations Multi-secteur SaaS (€) + services Pas compliance tertiaire, clés statiques Scalabilité opérations, UX EDF – Communitiz Fournisseur + ACC 50–100 opérations Collectivités surtout SaaS captif EDF Verrouillage EDF, pas agnostique Assistance déploiement, crédibilité Enercoop – Elocoop Coopérative citoyenne 30–50 opérations Coopératives/citoyens Modèle équitable Petite taille, peu scaling Mission éthique, gouvernance Sunchain (blockchain) Blockchain ACC <20 opérations Tech-forward Experimental Adoption faible, coûts élevés Transparence blockchain HubWatt Facturation ACC + monitoring 100+ opérations Multi-secteur SaaS + support Pas compliance multi-réglementaire, pas montage ACC Facturation robuste, intégration compta** (level 3, 20 words)
60. **Catégorie 3 : Fournisseurs & Intermédiaires Énergie Acteur Positionnement Modèle ACC Différenciation Limites Urban Solar Fournisseur vert local Intermédiaire (PMO externalisée) Marque réputée, accompagnement Perte autonomie PMO, captivité Ilek Marketplace producteurs–consommateurs Pair-à-pair (pas ACC collectif) Peer-to-peer, flexibilité Pas ACC multi-membres, micro EDF Obligation d’Achat (OA) Rachat surplus PV Non (vs ACC local) Tarifs assurés 20 ans Pas partage local, peu attractive pour ACC** (level 3, 14 words)
61. **H.2 – Matrice Positionnement PROMEOS Compliance & Réglementation (X-axis)** (level 3, 89 words)
62. **H.3 – Trois Différenciateurs PROMEOS** (level 3, 0 words)
63. **1) “Compliance-Driven Energy Communities”** (level 3, 62 words)
64. **2) “End-to-End Automation”** (level 3, 72 words)
65. **3) “Local Value Maximization via AI”** (level 3, 58 words)
66. **I) Réponses aux 5 Questions Guides Obligatoires** (level 2, 0 words)
67. **Q1 : 10 Leviers Concrets Accélération ACC 2025** (level 3, 110 words)
68. **Q2 : 10 Irritants Opérationnels Majeurs (avec solutions)** (level 3, 118 words)
69. **Q3 : Design Process + Produit → 12–24 mois → 3–6 mois** (level 3, 109 words)
70. **Q4 : Modèle Économique PROMEOS** (level 3, 132 words)
71. **Q5 : Évolutions 2026–2030 Changeant la Donne & Préparation Évolution Impact ACC Probabilité Réaction PROMEOS Suppression licence fournisseur PMO < 5 MW +300% AMEP, scalabilité particuliers 30–40% Advoc policy, legal brief, product ready Obligation ACC tertiaire renforcée Doublement opérations collectivités 40% Intégration Décret Tertiaire native Directive UE energy sharing Cross-border ACC pilots, mutualisation 10% Monitor EU lawmaking Baisse batterie ($/kWh → 80–100) 25% opérations + stockage 50–60% Intégration batterie dans Ops v2 IA dynamique standard industrie +5–15% autoconso, attractivité x2 70–80% Clés IA en MVP T1 2026 Saturation réseau local (DER) Effacement production obligatoire 30–40% Flex orchestration capability v2 Crise tarif énergie >€150/MWh Frénésie ACC (3x valeur) 30–50% Pricing model flexible, marketing** (level 3, 47 words)
72. **J) Roadmap Brique ACC PROMEOS – Backlog MVP & Priorisation** (level 2, 0 words)
73. **J.1 – Roadmap 90 j / 180 j / 12 mois (T0 2025 → T3 2025)** (level 3, 172 words)
74. **J.2 – Backlog Détaillé (User Stories)** (level 3, 0 words)
75. **MVP Core (Sprint 1–9, Jan–Mar 2025)** (level 3, 566 words)
76. **T1 Phase Extend (Sprint 10–15, Apr–Jun 2025) US-011 [S] En tant que PMO, j'intègre courbes Enedis via API (Data Connect)** (level 3, 238 words)
77. **J.3 – Priorisation RICE User Story R (Reach) I (Impact) C (Confidence) E (Effort) RICE Score Sprint US-001 (Auth) 100 5 100 5 1000 1–2 US-002 (Participants list) 100 4 100 8 500 2–3 US-003 (Participant signup) 100 4 90 10 360 3–4 US-004 (Participant dashboard) 100 3 90 12 225 4–5 US-005 (CSV import Enedis) 100 4 80 8 400 5–6 US-006 (Settlement calc) 100 5 90 15 300 6–7 US-007 (Billing PDF) 100 4 90 10 360 7–8 US-008 (Payment tracking) 100 3 85 12 212 8–9 US-009 (Wizard ACC) 100 5 85 20 212 6–9 US-010 (Invitations) 100 3 95 5 570 8–9 US-011 (API Data Connect) 100 5 70 15 233 10–12 (T1) US-012 (API ACC Enedis) 100 5 75 12 312 10–12 (T1) US-013 (SEPA) 100 4 70 20 140 12–14 (T1) US-014 (Compliance lite) 30 4 60 15 48 13–15 (T1)** (level 3, 0 words)
78. **K) Annexes & Ressources** (level 2, 0 words)
79. **K.1 – Textes Réglementaires Clés (Referencing)** (level 3, 83 words)
80. **K.2 – Guides Enedis (2025)** (level 3, 46 words)
81. **K.3 – Ressources Marché & Secteur** (level 3, 58 words)
82. **K.4 – Templates Documents (Intégrés PROMEOS MVP)** (level 3, 45 words)
83. **K.5 – KPI Dashboard PMO (Suivi Opérationnel)** (level 3, 223 words)
84. **Executive Summary (Synthèse finale)** (level 2, 513 words)

## Generated Drafts

| ID | Type | Domain | Confidence | Status |
|----|------|--------|------------|--------|
| LEVIERS_MARCHE_2025_0 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_1 | rule | usages | low | draft |
| LEVIERS_MARCHE_2025_2 | rule | usages | low | draft |
| LEVIERS_MARCHE_2025_3 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_4 | rule | usages | low | draft |
| LEVIERS_MARCHE_2025_5 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_6 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_7 | rule | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_8 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_9 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_10 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_11 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_12 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_13 | knowledge | facturation | low | draft |
| LEVIERS_MARCHE_2025_14 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_15 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_16 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_17 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_18 | rule | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_19 | knowledge | facturation | low | draft |
| LEVIERS_MARCHE_2025_20 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_21 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_22 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_23 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_24 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_25 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_26 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_27 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_28 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_29 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_30 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_31 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_32 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_33 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_34 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_35 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_36 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_37 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_38 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_39 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_40 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_41 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_42 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_43 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_44 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_45 | knowledge | reglementaire | low | draft |
| LEVIERS_MARCHE_2025_46 | rule | usages | low | draft |
| LEVIERS_MARCHE_2025_47 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_48 | rule | acc | low | draft |
| LEVIERS_MARCHE_2025_49 | rule | usages | low | draft |
| LEVIERS_MARCHE_2025_50 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_51 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_52 | knowledge | acc | low | draft |
| LEVIERS_MARCHE_2025_53 | knowledge | usages | low | draft |
| LEVIERS_MARCHE_2025_54 | rule | usages | low | draft |

## Next Steps

1. Review drafts in `docs/kb/drafts/LEVIERS_MARCHE_2025/`
2. Upgrade confidence and refine tags/logic for each draft
3. Promote to validated: `python backend/scripts/kb_promote_item.py <file.yaml>`
4. Import to DB: `python backend/scripts/kb_seed_import.py --include-drafts`
5. Rebuild FTS index: `python backend/scripts/kb_build_index.py`
