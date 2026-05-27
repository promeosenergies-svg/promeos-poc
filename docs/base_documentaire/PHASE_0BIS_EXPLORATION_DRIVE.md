# Phase 0-bis — Exploration documentaire Google Drive profonde (PROMEOS)

> Date : 2026-05-23
> Cadre : Audit produit brique « Conformité conditionnelle multi-énergie » PROMEOS
> Périmètre : Google Drive `promeos.energies@gmail.com`

**Périmètre analysé** : 60+ documents Drive parcourus, dont ~40 lus partiellement ou intégralement (≈ 1,4 Mo de texte extrait). Cinq dossiers ciblés (BACS, Décret Tertiaire, Lancement PROMEOS, MVP_v0, EMS_PROMEOS) + corpus réglementaire `1Kqns6VQT3zRu8fjc8kj_JDoBuPQrQZrQ` + recherches plein texte sur 20+ mots-clés (OPERAT, BACS, GTB, APER, CEE, ISO 50001, BEGES, exemption, modulation, RICE, playbook, connecteur, partenaire, attestation, preuve, parking, ombrière, photovoltaïque…). Triple analyse parallèle par 3 subagents pour rester en deçà de la limite de contexte.

Sources hiérarchisées par fiabilité :

- 🟦 **Officielle** (OPERAT/ADEME, Cerema, JORF, DHUP, Énergie-Info).
- 🟩 **Interne PROMEOS** (briques 1-4, simulateur, MVP, fiches produit, notes).
- 🟨 **Cabinet / éditeur** (Alter Watt, Advizeo, Energisme, Citron, Siemens).
- 🟪 **Commerciale / concurrent** (Enogrid, ENGIE ViGi-e, Endesa, Bamboo, Bpifrance).

---

## Corpus documentaire Google Drive analysé

| Document | Type | Contenu utile | Règle / idée extraite | Impact PROMEOS | Priorité | À intégrer ? |
|---|---|---|---|---|---|---|
| 🟩 **Brique 1 – Data & Conformité** (Lancement PROMEOS) | Vision produit | Système expert proactif, alertes contextualisées, P1/P2/P3, leads partenaires | Tagging opportunités P1/P2/P3 + carnet d'actions V2 + benchmark typologie + ROI estimé chaque action | Définit toute la promesse Conformité conditionnelle | Critique | OUI |
| 🟩 **Brique 2 – ACC Starter** | CdC fonctionnel | 4 types clés (statique/dyn défaut/dyn simple/full dyn), wizard 10 étapes, cercle 2 km, CACSI stockage, signature DocuSign, PVGIS | Règle gating ACC : 2 km / 5 MW / 36 kVA / 3 kW / dérogation 20 km EPCI / préavis 2 mois Enedis | Roadmap Brique 2 directe | Critique | OUI |
| 🟩 **Brique 3 – Architecture** | Cartographie modules | 13 modules (PMO-as-a-service, multi-site, clés dyn, facturation, IA prévision, GTB pilotage, stockage virtuel, smart contracts, OPERAT auto, alarmes, cockpit multi-acteurs) | Catalogue d'APIs Enedis ACC/Data Connect + IoT/GTB + onduleurs + marché spot + SEPA | Vision cible PROMEOS Ops | Haute | OUI (référence) |
| 🟩 **Brique 4 – Flexibilité, Stockage, TR** | CdC stratégique | 4 scénarios pricing (A abonnement+success, B kWh, C licence, D freemium), 5 catégories charges pilotables, smart contracts, Flex_score | Garde-fous bloquants 2 km/36 kVA + override humain + PWA mobile + explicabilité IA "on a coupé X parce que prix haut" | Future Brique 4 | Moyenne | OUI à terme |
| 🟩 **Analyse experte – Obligations multi-énergie** | Référence interne | Carte Obligations_Unitaires (texte/périmètre/exigence/data/échéance/calcul/sanction/RICE/owner/statut), connecteurs RICE | Identifiant Unique Bâtimentaire (IUB), Solarization gap (m² & kWc), BACS score 0-100, format YAML alertes | Squelette du module Conformité | Critique | OUI |
| 🟩 **Réglementations énergétiques – données & formules** | Référence interne | DEET/BACS/RE2020/BEGES/audit/ISO 50001 avec seuils, formules ajustement DJU, modulations, classes A/B/C/D, kWh/m² cibles | Dictionnaire calc verbatim : Conso ajustée, Bbio, Cep, ICénergie, ICconstruction, DH, ratios BEGES | Référence de calcul | Critique | OUI |
| 🟩 **Simulateur ACC & Conformité v0** | Spec MVP cockpit | 3 écrans (portefeuille / scénarios PV-GTB-ACC / plan actions), 4 questions clés client, schéma tables RT_*/BACS_*/CR_*/APER_* | Statut tertiaire feux : Rouge >-10%, Orange -10/-30%, Vert >-30% | Modèle data immédiatement codable | Critique | OUI |
| 🟩 **Vision MVP & Cas d'usage v0** (Sheet) | Schéma de données | Tables Inputs_site, Resultats_PV, Reg_Tertiaire, Reg_BACS, Reg_APER, Packs P1/P2/P3, Setup paliers 1-5/6-20/21-100 | Pack 1 Essentiel 1 200 €/an + 200 €/site ; Pack 2 OPERAT 2 000 + 250 ; Pack 3 Travaux 4 000 + 400 + 2 % success fee CAPEX | Source de vérité pricing actuel | Critique | OUI (déjà partiellement) |
| 🟩 **Plan de MVP & Offre PROMEOS** | Stratégie commerciale | Différenciation vs Advizeo/Deepki (compliance) vs Enogrid/Communitiz/Elocoop (ACC) — PROMEOS = les deux | "Fin ARENH 2026 + TURPE7 +10 %" comme accroche commerciale, roadmap 10/50/150 ACC | Pitch + positionnement | Haute | OUI (com) |
| 🟩 **MVP PROMEOS** (Sheet 1,3 Mo) | Scoring portefeuille | Mapping NAF→segment_PROMEOS + 3 scénarios prix (Bas/Base/Haut) + Tertiaire_status/BACS_status/APER_status_previsionnel par client gaz | Logique de scoring conformité "Assujetti probable / Possiblement / Peu probable" déjà formalisée | Pré-qualification commerciale automatisée | Haute | OUI |
| 🟩 **Fiche Produit Stratégique EMS NG** (≈100 k) | Vision multi-énergie | Pricing modulaire ~200 €/site/mois base, +50 IA, +100 ACC, license marque blanche ~50 k€/an, cas chiffrés (commune 5 000 hab, bailleur 10 résidences, usine 5 000 m²) | Compat OpenEMS / Modbus / MQTT / OCPP / REST, perf <3 s, uptime 99,9 %, mode hors-ligne edge | Roadmap technique | Haute | OUI (R&D) |
| 🟩 **Onboarding EMS** | Micro-copy UX | "Étape 2 sur 5", "Sauvegarder et continuer plus tard", vidéos <30 s, mise en service <15 min, zéro Excel | "Comment souhaitez-vous partager l'énergie produite ?", "Votre tableau de bord affiche votre conformité légale automatiquement" | Bibliothèque micro-copy | Haute | OUI |
| 🟩 **Idées Yannick 20250414** (≈88 k) | Étude conception | Architecture API-first, anomalies (panneau encrassé -10 %), comparatif Energisme/Deepki/Citron/Enogrid, BEMServer open-source | Référence Brooklyn TransActive Grid, Lyon Confluence, Volterres / Sunchain | Vivier d'idées | Moyenne | OUI (sélectif) |
| 🟩 **Réflexion EMS complémentaire** | Brainstorm | Distinction PMO opérée vs PMO juridique, intégration PVGIS/PVsyst/Archelios en amont | "EMS = opérateur, pas l'entité juridique" → modèle service géré pour collectivités | Modèle business neuf | Moyenne | OUI (eval) |
| 🟩 **EMS_SGO_2025 / Synthèse produit EMS** | Synthèse | 6 principes (ouverte/modulaire/TR/IA/réglementaire/communautaire/cockpit multi-sites) | Smart contracts traçabilité, mutualisation batteries multi-sites | Vision multi-énergie | Moyenne | OUI (cadrage) |
| 🟩 **Note stratégique Promeos 042025 (SGO²)** | Stratégie cible | Plateforme Génération+Gestion offres : leads solaire + scénarios + EMS + ACI/ACC/revente | Cible B2B2C (installateurs / BE / énergéticiens) avec API compat Archelios/PVsyst/Enerbee | Canal indirect | Moyenne | OUI (sélectif) |
| 🟩 **Rapport ACC photovoltaïque** (≈141 k) | Étude marché | 698 ops ACC actives fin 2024 (~74 MW), doublement annuel, AURA 98 + Occitanie 94 + Grand Est 81, 8 inspirations internationales | Italie prime ~110 €/MWh, SonnenCommunity, Piclo Flex, Brooklyn LO3, Tibber, Power Ledger | Inspiration UX/stratégie | Moyenne | OUI (sélectif) |
| 🟩 **Recommandations stratégiques EMS-NG (ACC PV B2B)** | Stratégie GTM | Time-to-market par segment (PME 1-3 mois, collectivités 6-12, industriels 9-18), killer features | Forfaits "EMS-NG Compliance 990 €/an", "Communauté Solaire 200 €/mois", "Reporting as a Service 500 €/an/bât" | Packages alternatifs | Haute | OUI |
| 🟩 **Étude autoconsommation PV (éligibilité ADEME)** | Subventions | Aide ADEME jusqu'à 80 % études, plafond 100 k€ accompagnement + 50 k€ diag, prestataire RGE | Champs exacts dossier AGIR ADEME (SIRET, surface, kWh/an, TRI 20/30 ans, %autoconso/autoprod) | Quick win commercial | Haute | OUI (différenciateur) |
| 🟩 **Cartographie B2B (ACC/ACI/Réseau classique)** | Étude segments | Problématiques par segment (collectivités/industriels/bailleurs/PME/agriculteurs/tertiaire) + opportunités tech | Limite agrivoltaïsme 40 % parcelle + FEADER, challenges CUBE/BBCA/ISO 50001 | Segmentation produit | Moyenne | OUI (sélectif) |
| 🟦 **Guide utilisateur OPERAT V1.1** (Sept 2025, 124 k) | Officiel ADEME | Parcours UI, EFA, IUB, import CSV par nom colonne, kWh PCI, zones climatiques H1A/H1B/…, mandats | Schéma data EFA + matrice droits + format CSV 1:1 OPERAT | Interopérabilité OPERAT | Critique | OUI |
| 🟦 **Documentation attestation & objectifs OPERAT** (Sept 2025) | Note méthodo | Formules verbatim **Cabs 2030 = CVC(n)+USE(n)** ; **Cabs = Σ(CVCi·Si)/ΣSi** ; **Crelat 2030 = Cref × (Cabs2030(n)/Cabs2030(ref)) × (1−0,4)** ; primo-assujetti vs EFA liée ; 3 types attestations ; **1er juillet 2026 = attestations à l'échéance** ; arrêté 1er août 2025 = pleine restitution | Algo de calcul Crelat/Cabs en local avant validation OPERAT | Critique | OUI |
| 🟦 **OPERAT – Récap versions V9.0** | Changelog officiel | V9 : ferm. multi-EFA, validation rattachement, **identifiant RNB**, export CSV ; V10 (nov 2025) : modulation par IHM, **connecteur GRDF**, alertes fiabilité | Brancher RNB (rnb.beta.gouv.fr), préparer connecteur GRDF | Haute | OUI |
| 🟦 **Remplissage OPERAT 2021-2024** | Statistiques | 2024 = 146 786 EFA / 447 Mm² / 59,4 TWh ; 2023 = 184 809 / 551 / 75,1 ; 2022 = 194 980 / 578 / 84,2 ; 2021 = 220 121 / 644 / 99,3 | Benchmark national à afficher dans le cockpit | Moyenne | OUI (UI) |
| 🟦 **Cerema DEET Mode d'emploi** (162 k) | Guide officiel | Notation EET (feuille grise → 3 feuilles vertes), valeurs étalons CVC*/USE* par sous-catégorie kWh/m².an, scénarios horaires, **fausse déclaration = art. 441-1 CP**, modulation dossier technique | Moteur simulation notation + alertes anti-fausse-déclaration | Critique | OUI |
| 🟦 **Plaquette EET 5 pages (DGEC)** | Plaquette officielle | Exemptions : construction provisoire, lieux culte, défense/sécurité civile ; sanctions **1 500 € (PP) / 7 500 € (PM)** ; **30/09/2027** = déclaration modulation 1ère décennie ; vérification fin 2031 | Calendrier réglementaire UI + amende prévisionnelle | Haute | OUI |
| 🟦 **EET 10 étapes** | Checklist DGEC | Périmètre 1 000 m², mutualisation, données (SHON/SUB/GLA + factures 2010-2020 + sous-comptage + IUB), dossier technique modulation | Wizard onboarding 10 étapes côté UI | Moyenne | OUI |
| 🟦 **EET Accompagnement commerces** | FAQ ADEME | Liens FAQ commerce : SCU, A13, QA8, DC5, E2, O8 (locaux non exploités, changement propriétaire, copropriétés, parkings) | Bibliothèque cas particuliers commerce intégrée | Moyenne | OUI (FAQ) |
| 🟦 **Guide BACS Janvier 2026 (DHUP)** (51 k) | Officiel V2 | Décret 2023-259 ; échéances **existants >290 kW : 1er janv 2025** ; **existants 70-290 kW : 1er janv 2030** ; **neufs >70 kW : régime neuf applicable** ; pas horaire par zone fonctionnelle ; conservation données 5 ans ; classes C/B/A éligibles ; **CEE BAT-TH-116 → classe A ou B** ; inspection périodique R. 175-5-1, 1ère avant 1er janv 2025 ; rapport conservé **10 ans** | Module BACS : profil puissance/classe/plan comptage/agenda inspection | Critique | OUI |
| 🟦 **Guide BACS Mai 2023 (DHUP V1)** | Officiel | Formule **TRI = S/Σ(Génergie·Cénergie), S = I − A, Génergie = G·ΣCi,j/2** ; signaux EcoWatt orange/rouge + EcoGaz | Calculateur TRI exact + signaux EcoWatt/EcoGaz | Haute | OUI |
| 🟨 **Advizeo Guide BACS 2025** | Plaquette | Suivi zone fonctionnelle pas horaire ; **arrêté 30 août 2024 modifie BAT-TH-116** : baisse forfaits 5-30 %, prolongation jusqu'au 1er janv 2030 ; **vA62-6 dès 01/01/2025** | Mise à jour montants CEE | Moyenne | OUI |
| 🟦 **Air France – Diag BACS CMH (Allonzo)** (62 k) | Rapport diag réel | Modèle complet de **Rapport Diag BACS** : analyse existant, plan comptage, scénarios technico-éco, justif exclusions ; tableau par lot 1-7 avec classe actuelle → C/B/A | Template export PDF "Diag BACS" + arbre décision par lot | Critique | OUI |
| 🟦 **Classes GTB (NF EN 15232 / ISO 52120-1)** | Extrait normatif | Lots 1-7 × fonctions 1.1-7.5 × classes A/B/C/D | Référentiel d'audit GTB complet | Critique | OUI (référentiel) |
| 🟦 **NF EN 52120-1 mars 2022** (175 k) | Norme officielle | Méthode attribution classe par projet, exclusion fonctions <5 %, exemple galerie marchande | Base normative scoring BACS | Haute | OUI (citer) |
| 🟨 **Manuel Siemens GTB** (180 k) | Manuel fournisseur | Fonctions BA/GTB par chapitre, asservissement chaud-froid, optimisation start/stop, gestion présence, refroid nocturne | Bibliothèque recommandations techniques | Moyenne | OUI (sélectif) |
| 🟨 **Alter Watt – Décret BACS** | Fiche cabinet | Règle puissance = max(chauffage, climatisation), somme si plusieurs ; **exonération TRI > 10 ans valable lot par lot** ; pas de sanction propre (rattaché tertiaire) | Calculateur exonération TRI lot par lot | Haute | OUI |
| 🟨 **Alter Watt – Décret tertiaire** | Fiche cabinet | EFA = SIRET + site + activité ; année réf 2010-2022 ; mutualisation = moyenne pondérée objectifs EFA | Modèle de mutualisation parc | Moyenne | OUI |
| 🟦 **Plaquette tertiaire_privé on vous aide** (ADEME 2023) | Plaquette financements | **Diag Perf'Immo Bpifrance 3-15 k€ HT** ; **Booster Entreprises EET 70 % ingénierie** ; fiches CEE BAT-TH-116, BAT-TH-127, BAT-EQ-127, BAT-EN-103, BAT-EQ-124 | Catalogue CEE/aides intégré | Haute | OUI |
| 🟦 **BAT-TH-116 (fiche CEE officielle)** | Réglementaire CEE | Conditions classe **B ou A** NF EN 15232-1 ; matrice **secteur × usage × énergie × zone (H1=1,1; H2=0,9; H3=0,6)** ; durée vie 15 ans ; coef actualisation 11,563 ; coût équipement 3-10 €/m² | Calculateur CEE prêt à coder (Bureaux H1 comb. = 320×1,1×S, etc.) | Critique | OUI |
| 🟦 **JO 06/09/2025 – Arrêté 1er août 2025 (ATDL2430864A)** | JORF officiel | Supprime modèle d'attestation papier VII-1, **ajoute GNL (facteur GES 0,238)**, période transitoire jusqu'au 1er juillet 2026 | Mettre à jour table énergies + workflow attestation | Haute | OUI |
| 🟦 **JO 08/04/2023 – Décret 2023-259 (TREL2232678D)** | JORF officiel BACS | Abaisse seuil **290 → 70 kW** ; **bâtiments existants 70-290 kW : échéance 1er janv 2030** ; bâtiments neufs >70 kW : régime neuf applicable ; inspection R. 175-5-1 ; rapport conservé 10 ans | Calendrier BACS + module inspection | Critique | OUI |
| 🟦 **JO 11/03/2023 – LOI 2023-175 (APER)** (240 k) | JORF officiel | Accélération EnR + zones d'accélération PLU/SCOT + **ombrières PV parkings ≥ 1 500 m² (art. 40)** + agrivoltaïsme + communautés énergétiques | Détection parkings >1 500 m² + simulateur loyer/autoconso | Critique | OUI |
| 🟦 **JO 25/07/2019 – Décret 2019-771 (LOGL1909871D)** | JORF tertiaire fondateur | Art. R. 131-38-44 : champ ≥ 1 000 m², modulations (a/b/c), OPERAT, 30 sept, sanctions 1 500/7 500 €, mise en demeure 3 mois | Référentiel juridique fondateur (mapping articles → champs UI) | Haute | OUI |
| 🟪 **Brochure Solaire FAS** | Plaquette pédago | AO CRE 2 000 MW/an sol + 900 MW toitures/ombrières ; LCOE 58,86-84,65 €/MWh ; cycle projet 12-24 mois post-lauréat ; PLU "Npv/AUpv" | Module APER/PV (PLU, AO CRE, types valorisation) | Moyenne | OUI (sélectif) |
| 🟨 **Livre Blanc Décret Tertiaire 2025 (Energisme)** | Synthèse éditeur | Art. 606/605 Code Civil (répartition bailleur/locataire), JORF 24/04/2022 mutualisation, **amende 7 500 €/bât/an + 150 €/m² au-delà de 2 000 m²** | Module CGU/contrat bail + calculateur amende prévisionnelle | Moyenne | OUI |
| 🟪 **ENGIE ViGi-e** | Concurrent direct | 3 leviers (conso/horaire/contrat) ; cas client **56 agences bancaires, -23 % conso, 51 793 €/an économisé** (IPMVP, spot 57,74 €/MWh × 897 MWh) | Granularité financière temps réel à atteindre | Haute | OUI (benchmarking) |
| 🟦 **JO 18/12/2025 – Arrêté 15/12/2025 (CEE PAC BAR-TH-171/172)** | JORF | Modifie fiches CEE PAC résidentiel (BAR-TH) | Pertinence faible tertiaire | Faible | Non (sauf module bailleur résidentiel) |
| 🟨 **Diag Air France lots 1-7** | Modèle rapport | Justif exclusion équipements (ex. ECS classe D mais aucune action car risque sanitaire) | Logique exemptions documentées | Critique | OUI |

---

## Découvertes documentaires actionnables

| Découverte | Source | Module impacté | Action produit | Action tech | Test attendu | Priorité |
|---|---|---|---|---|---|---|
| **Formules verbatim OPERAT Cabs/Crelat** | 🟦 Doc Attestation & Objectifs (Sept 2025) | Conformité DEET | Afficher la trajectoire et la **prévision avant validation OPERAT** | Implémenter `Cabs = Σ(CVCi·Si)/ΣSi` + `Crelat = Cref × (Cabs(n)/Cabs(ref)) × 0,6` ; gérer EFA liée (moyenne pondérée) et primo-assujetti | Comparer Crelat calculé vs Crelat restitué par OPERAT après validation (delta ≤ 1 %) | Critique |
| **Identifiant RNB (rnb.beta.gouv.fr)** | 🟦 OPERAT V9 | Modèle Site | Ajouter champ `IUB_code` + bouton "Proposer RNB" | Connecteur API RNB + auto-proposition + saisie manuelle | Test E2E : un site avec lat/lng renvoie ≥ 1 RNB candidat | Haute |
| **Arrêté 1er août 2025 — ajout GNL + suppression modèle papier** | 🟦 JO 06/09/2025 | Référentiel énergies | Ajouter "GNL" coef GES 0,238 + retirer modèle attestation papier (VII-1) | Migration table `energy_type` + suppression PDF papier UI | Régression : déclaration GNL accepte coef officiel | Haute |
| **Connecteur GRDF (OPERAT V10)** | 🟦 OPERAT V9 | Connecteurs ingestion | Préparer onglet "Données gaz GRDF" | Spec API GRDF (équivalent Data Connect Enedis) + OAuth + ingestion mensuelle | Récupération conso gaz site test sur 12 mois rolling | Haute |
| **Sanctions amende DEET = 7 500 €/bât/an + 150 €/m² au-delà de 2 000 m²** | 🟨 Livre Blanc Energisme | Cockpit Conformité | Widget "Amende prévisionnelle" sur fiche site | Fonction `amende_prev = 7500 + max(0, (surface_m2-2000)*150)` | Test unitaire : 5 000 m² → 7 500 + 3 000×150 = 457 500 € | Haute |
| **Anti-fausse-déclaration (art. 441-1 CP)** | 🟦 Cerema DEET | Validation formulaire OPERAT | Warning UI si indicateur intensité d'usage hors plage étalon Cerema | Règle YAML `ALERTE_ETALON_DEPASSE` + lien article 441-1 CP | Test : 5000 h/an sur sous-cat 2400h → alerte rouge | Haute |
| **Calculateur TRI BACS lot par lot (exonération partielle)** | 🟦 Guide BACS DHUP / 🟨 Alter Watt | Module BACS | Wizard "Exonération BACS" par lot CVC | `TRI = S / Σ(G_énergie × C_énergie)`, `S = I − A`, `G_énergie = G·ΣCi,j/2` ; flag par lot | Test : 3 lots dont 1 avec TRI 12 ans → 1 lot exonéré, 2 lots assujettis | Critique |
| **Inspection BACS R. 175-5-1 — agenda 2 à 5 ans, rapport 10 ans** | 🟦 Guide BACS Jan 2026 | Module BACS | Agenda inspection avec rappels mailing + stockage rapports 10 ans | Modèle `BacsInspection { date_planned, date_done, report_url, periodicity }` | Test : alerte 90 j avant échéance, 30 j, 7 j | Critique |
| **Matrice CEE BAT-TH-116 (secteur × usage × énergie × zone)** | 🟦 BAT-TH-116 officielle | Module CEE | Calculateur primes CEE intégré dans recommandations | Tableau pivot 6 secteurs × 4 usages × 2 énergies × 3 zones (H1=1,1; H2=0,9; H3=0,6) + durée 15 ans + coef 11,563 | Test : 1 000 m² bureaux H1 comb. CH+ECS = 330×1,1×1000 = 363 000 kWhc | Critique |
| **Mise à jour BAT-TH-116 vA62-6 (01/01/2025)** | 🟨 Advizeo guide BACS | Module CEE | Mettre à jour montants forfaitaires baisse 5-30 %, prolongation jusqu'au 01/01/2030 | Versionner barème CEE par date d'arrêté | Régression : montant pré-2025 ≠ post-2025 | Haute |
| **Cycle de vie loi APER : parkings ≥ 1 500 m² → 50 % ombrières PV** | 🟦 JO LOI 2023-175 art. 40 | Module APER | Détection parkings + alerte échéance + simulateur loyer/autoconso | Table `Reg_APER { surface_parking_m2, surface_couverte_PV_m2, couverture_%, date_limite (≥10k→2026-07-01, 1,5-10k→2028-07-01), sanction_potentielle_€/an }` | Test : parking 12 000 m² → APER 2026, couverture 5 000 m² → conformité 41 % rouge | Critique |
| **Sanction APER 20 000 €/an (1,5-10k) et 40 000 €/an (≥10k)** | 🟩 Analyse experte | Module APER | Widget sanction prévisionnelle | `if non_conforme_apres_date_limite → annual_fine` | Régression annuelle sur portefeuille | Haute |
| **Exemptions APER (ABF, ENV, économique, ENR alternative, mutualisation, suppression parking)** | 🟩 Analyse experte + JO 2024-1023 | Module APER | Workflow "Demande exemption APER" + checklist + dossier preuve | Modèle `AperException { type, justification_url, status, decision_date }` | Test : exemption ABF acceptée bloque alerte sanction | Haute |
| **Cocktail amende DEET 1 500 € PP / 7 500 € PM + name & shame** | 🟦 Plaquette DGEC 5 pages | Cockpit Conformité | Widget badge "exposition name & shame" | Bool `risk_name_and_shame = (RT_atteinte_2030 = FAUX AND modulation_dossier IS NULL)` | Régression : un site sans modulation et sans atteinte → exposé | Haute |
| **Mutualisation parc DEET (moyenne pondérée surfaces)** | 🟨 Alter Watt | Module DEET | Switch portefeuille "Mutualiser objectifs" | `Obj_global = Σ(Obj_i × S_i) / Σ S_i` | Comparaison portefeuille mutualisé vs non | Haute |
| **3 statuts tertiaire feu (Rouge >-10 %, Orange -10/-30 %, Vert >-30 %)** | 🟩 Simulateur ACC v0 | Cockpit | Pastille couleur sur liste sites | Fonction `status_tertiaire(reduction_%)` retourne enum | Test unitaire 3 cas (8 %, 20 %, 45 %) | Haute |
| **Schéma data v0 prêt à coder (Inputs_site, Reg_Tertiaire, Reg_BACS, CR_*)** | 🟩 Simulateur ACC + Vision MVP | Modèle de données | Migration SQL pour table Reg_Tertiaire/Reg_BACS/Reg_APER + vue Cockpit_Reglementaire | Voir colonnes verbatim dans bilan agent A § fichier 5 | Tests fixtures sur 4 sites du Vision MVP (S001-S004) | Critique |
| **Phrase de synthèse auto `CR_Message_synthese`** | 🟩 Simulateur ACC v0 | Cockpit | Générer pour chaque site une phrase lisible "Site X : encore 210 MWh/an pour 2030, aucun projet GTB lancé." | Function `generate_message(site)` combine RT+BACS+PV | QA copy review natif FR | Haute |
| **Cockpit MVP 3 écrans (portefeuille / scénarios / plan d'actions)** | 🟩 Simulateur ACC v0 | UI Cockpit | Maquetter et coder les 3 écrans | Routes `/portfolio`, `/site/:id/scenarios`, `/site/:id/actions` | Test E2E parcours bailleur 20 sites | Critique |
| **Packs P1/P2/P3 (Essentiel / Conformité OPERAT / Conformité+Travaux)** | 🟩 Vision MVP Sheet | Billing | Implémenter 3 paliers (1-5/6-20/21-100) avec setup + base + variable + success fee | Modèle `BillingPlan { pack, palier, setup_€, base_€/an, variable_€/site/an, success_fee_% }` | Calcul automatique CA 20 sites Pack 2 = 2 000 + 250×20 + setup 7 500 = 14 500 €/an | Haute |
| **Wizard onboarding <15 min avec micro-copy verbatim** | 🟩 Onboarding EMS + Brique 2 | UX | Réécrire onboarding ACC, ajout site, déclaration Tertiaire | Composants `WizardStep`, barre "Étape X sur N", "Sauvegarder & continuer plus tard", vidéos <30s | Test : utilisateur novice atteint étape 5 en <15 min | Haute |
| **Forfait "Reporting as a Service 500 €/an/bâtiment"** | 🟩 Reco strat EMS-NG | Billing | Pack additionnel "OPERAT-as-a-Service" pour clients hors pack 2/3 | Add-on `reporting_aas: bool` au modèle Client | Test pricing 30 bâtiments → 15 000 €/an récurrent | Moyenne |
| **Pré-remplissage dossier AGIR ADEME** | 🟩 Étude ACC ADEME | Module Subventions | Générer auto les 3 blocs (Description / Contexte / Objectifs ≤1300 car.) + données chiffrées | Mapper `Site` → AGIR fields | Export PDF prêt à upload sur agir.ademe.fr | Haute |
| **Catalogue d'aides : Diag Perf'Immo 3-15 k€, Booster EET 70 %, Fonds Chaleur, Prêt Vert Bpifrance** | 🟦 Plaquette tertiaire on vous aide | Module Subventions | Page "Aides disponibles" filtrée par site/segment | Table `Aide { nom, montant, plafond, conditions, lien }` | QA contenu | Moyenne |
| **API Enedis ACC : synchronisation auto clés de répartition mensuelles** | 🟩 Brique 3 + Brique 2 | Connecteur ACC | Job mensuel + interface "Clé envoyée à Enedis" | Cron + appel API Enedis ACC + log + reconciliation avec CRM Enedis | Test sandbox Enedis | Critique |
| **API Enedis Data Connect (consentement, OAuth2, 15-min)** | 🟩 Brique 3 | Connecteur conso | Wizard "Importer mes données Enedis" | OAuth + récupération PDL + 12 mois historique | Test E2E sur compte test Enedis | Critique |
| **Connecteurs IoT/GTB (MQTT, BACnet, Modbus, OCPP, DALI)** | 🟩 Brique 4 + Fiche EMS NG | Connecteurs terrain | Plan de comptage par site | Driver MQTT + BACnet/IP + Modbus TCP + OCPP 1.6 | Lab sur 3 sites pilotes | Moyenne |
| **Garde-fous bloquants 2 km / 36 kVA / CACSI / périmètre ACC** | 🟩 Brique 4 + Brique 2 | Orchestrateur ACC | Avant toute commande, valider règles | Hook `before_command(asset, action)` | Tests réglementaires automatisés | Critique |
| **PMO opérée (service géré, sans personnalité juridique)** | 🟩 Réflexion EMS comp. | Offre service | Nouveau pack "PMO Managed" | Modèle `Operator { client_id, role: 'pmo_managed' }` | Pilote 1 collectivité | Moyenne |
| **API marque blanche / multi-tenant** | 🟩 Fiche Stratégique EMS NG | Architecture | Mode `WhiteLabel { logo_url, primary_color, domain }` | Multi-tenancy + branding dynamique | Test 2 tenants distincts | Moyenne |
| **Calculateur exonération BACS TRI > 10 ans** | 🟦 Guide BACS + 🟨 Alter Watt | Module BACS | Wizard exonération + génération dossier | Voir formules TRI ci-dessus + génération PDF | Test : dossier signé + déposé en preuve | Haute |
| **Plan de comptage BACS par zone fonctionnelle, pas horaire, 5 ans archivage** | 🟦 Guide BACS Jan 2026 | Module BACS | Plan de comptage interactif + carte zones | Storage hot 13 mois + warm 5 ans | Test conformité audit | Haute |
| **Référentiel NF EN 15232 / ISO 52120-1 (lots 1-7 × fonctions 1.1-7.5 × classes A/B/C/D)** | 🟦 NF EN 52120-1 + Classes GTB + Diag Air France | Module BACS | Score classe BACS automatique par bâtiment | Table référentiel + algo attribution classe | Test sur Diag Air France (cohérence préco) | Critique |
| **Template export "Diag BACS"** | 🟦 Diag Air France CMH | Module BACS | Bouton "Générer Diag BACS PDF" sur site | Template Jinja/Puppeteer PDF | Comparaison visuelle vs modèle Air France | Critique |
| **Recommandations techniques Siemens (asservissement chaud-froid, optimisation start/stop, FDD, déstratification)** | 🟨 Siemens manuel | Recommandations | Bibliothèque de patterns avec ROI estimé | Catalogue `Recommandation { code, titre, prereqs_lot, gain_estime_%, capex_estime_€ }` | Cohérence vs manuel | Moyenne |
| **EcoWatt / EcoGaz signaux orange/rouge** | 🟦 Guide BACS 2023 | Module Flex/Conformité | Mode "sobriété hivernale" auto activé sur signal | Connecteur API EcoWatt RTE + EcoGaz GRTgaz | Régression : déclenchement test orange | Moyenne |
| **Calcul climat-corrigé via DJU + ajustement chauffage/refroid séparé** | 🟦 Cerema DEET + Réglementations énergétiques | Algo conso ajustée | Workflow saisie sépare CH / refroid / autres pour ajustement DJU | `Conso_ajustee = Conso + Adj_chauffage + Adj_refroid` ; DJU vs moy 2001-2020 | Régression vs calculateur OPERAT | Critique |
| **Calendrier réglementaire UI (countdowns)** | 🟦 Cerema + Guide BACS + JO APER | Cockpit | Bandeau "Prochaines échéances" sur dashboard | Component `RegCountdown { date, label, status }` × 8 dates clés (voir liste agent B) | Test : 30/09 → "J-30 OPERAT" | Critique |
| **8 dates pivots à coder dans le calendrier** | 🟦 Multi-sources | Cockpit | 30/09 N (OPERAT), 01/01/2025 (BACS existants >290 kW + 1ère inspection), 01/07/2026 (attestations OPERAT + APER >10k), 30/09/2027 (modulation DEET 1ère décennie), 01/07/2028 (APER 1,5-10k), **01/01/2030 (BACS existants 70-290 kW + BAT-TH-116 fin)**, 31/12/2031 (vérification décennie 1) | Table `KeyDate { date, label, regulation, impact }` | Régression visuelle | Critique |
| **Scoring NAF→segment_PROMEOS + Tertiaire/BACS/APER_status_previsionnel** | 🟩 MVP PROMEOS Sheet | Pré-qualification commerciale | Endpoint "Évaluer prospect" depuis SIRET seul | Mapping NAF (68.20A, 47.11D, 86.10Z, 85.31Z, 25.11Z…) + règles | Test : SIRET bailleur → "Assujetti probable + BACS probable + APER fort potentiel" | Haute |
| **Modèle Reg_APER manquant dans v0** | 🟩 Simulateur ACC v0 + Analyse experte | Modèle data | Ajouter table dédiée + calcul date_limite + sanction | Voir colonnes ci-dessus | Migration alembic + fixtures parking 1500 m² et 12 000 m² | Critique |
| **Préavis 2 mois Enedis pour changement périmètre ACC** | 🟩 Brique 2 | Workflow ACC | Validation gel 60 jours avant date_effective | Trigger UI + email rappel J-60 | Test : ajout participant → impossible avant J+60 | Haute |
| **Flex score / Autonomy score / Resilience score** | 🟩 Brique 4 | Scoring | Trois nouveaux scores complémentaires au conformité | `flex_score = sum(asset.power if pilotable)` ; `autonomy_score = max_hours_off_grid` | Tests unitaires | Moyenne |
| **Explicabilité IA : "On a coupé X parce que prix haut"** | 🟩 Brique 4 | UX Flex | Justification systématique pour chaque action automatique | Champ `decision_reason` log | Audit UX | Moyenne |
| **Mode override + fallback local si IoT KO** | 🟩 Brique 4 | Sécurité Flex | Bouton "Reprendre la main" + edge fail-safe | Heartbeat + bascule mode dégradé | Test perte connexion 5 min | Moyenne |
| **CACSI autorise désormais le stockage (≤ 36 kVA)** | 🟩 Brique 2 | Module batterie | Re-router clients CACSI vers offre stockage | Décision tree `if cacsi and souscrite≤36kVA → propose stockage` | Doc commercial mis à jour | Moyenne |
| **Comparatif concurrentiel 13 acteurs (Advizeo/Deepki/Citron/Energisme/Enogrid/Communitiz/Elocoop/Sunchain/Eficia/Metron/BEMServer/Bamboo/Schneider)** | 🟩 Plan MVP + Idées Yannick + Reco strat | Stratégie produit | Positionnement clair "compliance + ACC" | Doc battle card | Validation comm | Moyenne |
| **Cas chiffré "Résidence Soleil" (600 MWh/an, 84 k€, 200 kWc → -26 k€/an)** | 🟩 Simulateur ACC v0 | Démo commerciale | Démo embarquée dans onboarding | Données fixtures S001-S004 | QA visuel cohérent | Haute |
| **Fenêtre commerciale "fin ARENH 2026 + TURPE7 +10 %"** | 🟩 Plan MVP | Marketing | Bandeau cockpit + page d'atterrissage | Copy verbatim | Validation com | Moyenne |
| **Smart contracts traçabilité (Sunchain / Volterres / Brooklyn LO3)** | 🟩 Idées Yannick + Rapport ACC | Roadmap V3 | Mode "blockchain-ready" même non activé | Hash + signature des décisions + Merkle tree | À planifier (V3) | Faible |
| **Mode "Cockpit CEO"** | 🟩 Fiche Stratégique EMS NG | Profils utilisateurs | Vue exec : VAN/TRI 10 ans, scenarios CO₂ ESG | Profil `executive` avec dashboard distinct | Pilote 1 direction client | Moyenne |
| **Mode hors-ligne / edge device** | 🟩 Fiche Produit EMS NG | Architecture | Mode dégradé local en cas de perte cloud | Cache + sync différée | Test 24h offline | Faible |
| **Widget public RSE "X % renouvelable, Y t CO₂ évitées"** | 🟩 Vision EMS NG + Onboarding | Communication | Embeddable iframe public | Endpoint `/widgets/co2-live?client_id=...` | Test embed sur site externe | Moyenne |
| **Agents IA spécialisés (facture / autoconso / surplus / maintenance)** | 🟩 Fiche Stratégique + Idées Yannick | Roadmap IA | Activation modulaire par agent | Service `Agent { type, config, enabled }` | Mode sandbox simu | Faible |
| **Détection anomalies maintenance prédictive (panneau encrassé -10 %)** | 🟩 Idées Yannick | Module ACC Ops | Alerte "Perte de rendement détectée" | Modèle de comparaison vs jumeau numérique | Lab sur 1 site PV | Moyenne |
| **Mutualisation batteries multi-sites** | 🟩 Synthèse EMS / Idées Yannick | Module Flex/Stockage | Agrégateur de capacité virtuel intra-portefeuille | Service "virtual battery pool" | Lab 2 sites | Faible |
| **Mécanisme opt-out HLM (loi APER 2023)** | 🟩 Rapport ACC | Module ACC bailleur | Workflow d'invitation locataires + recueil refus | Modèle `TenantConsent { status, opt_in_date, opt_out_date }` | Test bail social pilote | Moyenne |
| **Agrivoltaïsme (max 40 % parcelle, FEADER)** | 🟩 Carto B2B | Vertical agrico (futur) | Évaluer si segment d'expansion | Document de cadrage | Décision GO/NO-GO | Faible |
| **Verticales d'amorçage : ACC vs Compliance DEET** | 🟩 Reco strat | Stratégie GTM | Choisir une des 2 comme cheval de Troie | Documentation positionnement | Décision board | Critique |

---

## Notes méthodologiques & points d'attention

**Documents au titre peu parlant mais au contenu utile** (souvent confirmé) :

- `Idées Yannick 20250414` : 88 k caractères d'étude de conception détaillée (sans le titre on passe à côté).
- `Documentation attestation et objectifs.pdf` (sept 2025) : contient les **formules officielles OPERAT** rarement publiées ailleurs.
- `Onboarding EMS.docx` : **mine d'or de micro-copy** UX prête à reprendre.
- `joe_20230408_0084_0013.pdf` : décret 2023-259 BACS qui abaisse 290→70 kW.
- `joe_20250906_0207_0061.pdf` : arrêté pivot 2025 (ajout GNL, suppression modèle papier).
- `Air France – CMH – Diag BACS_v2.pdf` : **gabarit complet** de rapport BACS à reproduire.
- `BAT-TH-116_FC_*.pdf` : matrice complète des primes CEE prête à intégrer.
- `Étude autoconsommation photovoltaïque - Conditions d'éligibilité ADEME.pdf` : champs exacts AGIR pour subvention 80 %.

**Documents commerciaux / formations utiles pour micro-copy** :

- `Onboarding EMS.docx`, `ENGIE___ViGi_e.pdf` (granularité financière), `advizeo - Schéma économique Partenaires.pdf` (modèles commission).

**Sources réglementaires à recroiser web/Légifrance avant tout commit de règle code** :

- Décret 2019-771 + arrêtés "valeurs absolues" successifs (notamment 1er août 2025).
- Décret 2020-887 + 2023-259 (BACS).
- LOI 2023-175 art. 40 + décret 2024-1023 (APER).
- Arrêté CEE BAT-TH-116 vA62-6 (à compter du 01/01/2025).

**Sources hypothèse produit interne** (à challenger) :

- Brique 4 (scénarios pricing A/B/C/D), Note SGO² (positionnement B2B2C), Idées Yannick (Energy Bots blockchain), Rapport ACC inspirations internationales — utiles comme inspiration mais ne sont pas validés clients.

**Documents stockés sur disque par les agents** (relecture ciblée possible) :

- `/Users/amine/.claude/projects/-Users-amine/984626c3-b87d-40a2-93af-a4bec0cf36e0/tool-results/*.txt` (5 gros docs PROMEOS).
- `/tmp/promeos_audit/doc_*.md` (agent A).
- `/tmp/fps_emsng_part2.txt`, `/tmp/idees_yannick.txt`, `/tmp/rapport_acc.txt`, `/tmp/reco_strat.txt`, `/tmp/carto_b2b.txt` (agent C).
