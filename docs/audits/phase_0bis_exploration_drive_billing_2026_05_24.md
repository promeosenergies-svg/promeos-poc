# Phase 0-bis — Exploration documentaire profonde Bill Intelligence

> **Date** : 2026-05-24
> **Branche cible (futur code)** : `claude/refonte-sol2`
> **Mode** : analyse READ-ONLY uniquement — aucune correction produite à ce stade.
> **Périmètre** : Bill Intelligence / Factures B2B France — électricité (TURPE, accise, CTA) + gaz (ATRD, ATRT, accise) + capacité + CEE + TVA + régularisations.
> **Référence amont** : [audit_brique_bill_intelligence_deep_readonly_2026_05_23.md](audit_brique_bill_intelligence_deep_readonly_2026_05_23.md) (verdict 7/10 — 3 P0 ouverts).

## Sommaire

1. [Méthode](#1-méthode)
2. [Sources hiérarchisées](#2-sources-hiérarchisées)
3. [Corpus Drive analysé](#3-corpus-drive-analysé)
4. [Skills PROMEOS lus](#4-skills-promeos-lus-base-de-vérité-interne)
5. [Sources officielles web](#5-sources-officielles-web)
6. [Matrice des règles de facture (60+ règles)](#6-matrice-des-règles-de-facture)
7. [Impact PROMEOS — gaps P0 / P1 / P2 par règle](#7-impact-promeos--gaps-par-règle)
8. [Hypothèses internes vs règles officielles](#8-hypothèses-internes-vs-règles-officielles)
9. [Recommandations pour le sprint Bill Intelligence P1](#9-recommandations-pour-le-sprint-bill-intelligence-p1)

---

## 1. Méthode

3 agents READ-ONLY parallèles + lectures ciblées + cross-skills :

| Agent | Périmètre | Output |
|---|---|---|
| **A — PDFs CRE/Enedis locaux** | 17 PDFs CRE (`docs/base_documentaire/CRE/`) + 10 PDFs Enedis (`docs/base_documentaire/enedis/`) déjà présents dans `promeos-audit-main/` | Verbatim TURPE 7 (CRE 2025-40 + 2025-77), ATRT 8 (2025-270), ATRD 7 ELD (2026-15), CTA (2026-14), CART-P (2026-44), GRDF non péréqué (2026-48), minoration VNU 2026 (2026-52) |
| **B — Skills installées** | 8 skills `.claude/skills/` (promeos-billing, bill-intelligence-fr, promeos-enedis, promeos-energy-market, energy-contracts-b2b, cee-p6, energy-autoconsommation, promeos-regulatory) | 7 règles déjà encodées + 5 partielles + 5 manquantes |
| **C — Google Drive deep search** | 30+ keywords (facture, TURPE, ATRD, ATRT, CTA, accise, CSPE, CEE, capacité, PRM, PCE, Gazpar, etc.) sur 7 dossiers Drive | 80+ hits, 5 nouveaux dossiers identifiés (factures réelles, EE Flashes, APIs SGE, exports contrats, formations) |

**Pourquoi pas WebFetch massif** : les PDFs CRE locaux SONT les sources officielles (délibérations publiées au format PDF par la CRE). Le verbatim extrait par l'agent A est suffisant pour anchor chaque règle ; les URLs canoniques sont citées en §5 pour traçabilité.

**Pourquoi pas de modification code** : doctrine "aucun prompt de correction produit avant cette phase" (cf. brief). La matrice §6 et les gaps §7 sont des **données d'entrée** pour un futur sprint Bill Intelligence P1.

---

## 2. Sources hiérarchisées

| Couleur | Tier | Exemples | Usage |
|---|---|---|---|
| 🟦 | **Officielle** | CRE délibérations, JO/Légifrance, Enedis SGE guides, GRDF tarifs, ADEME | **Source de vérité** pour tout code de règle tarifaire |
| 🟩 | **Interne PROMEOS** | Templates Energisme intégrés au repo, fixtures factures réelles, skills installés | Schéma de données + golden set de test |
| 🟨 | **Cabinet / éditeur** | EuropEnergies (EE) Flashes, Advizeo, Energisme catalogue, N'Gage | Inspiration / benchmark, **jamais source de règle tarifaire seule** |
| 🟪 | **Concurrent** | Bamboo, ENGIE ViGi-e, Endesa, Deepki, Citron | Battle card UX, jamais data |

**Règle de non-régression** : aucune règle tarifaire commit-ée ne peut citer une source 🟨 ou 🟪 sans recroisement 🟦. Cf. discipline `bill-intelligence-fr` §1 (routage tarifaire runtime obligatoire).

---

## 3. Corpus Drive analysé

### 3.1 Dossiers Drive parcourus

Memory `reference-promeos-drive` (compte `promeos.energies@gmail.com`) liste 7 dossiers déjà connus. L'agent C en a découvert **5 nouveaux** qu'il faut ajouter à la memory :

| Dossier | ID | Contenu (résumé) | Status memory |
|---|---|---|---|
| Lancement PROMEOS | `1JWsj0eT9Zp4fWWi4Ipc4jqdsYJqxRz6u` | Briques 1-4, Vision, MVP, réglementations | ✅ connu |
| MVP_v0 | `1vwz-r7A1PY4OjeAReigBHv6itUryrOlE` | Simulateur ACC, sheet MVP | ✅ connu |
| BACS | `1GU7OJADsfp1ZOpG_jMzpPHw1es_heBHW` | Guide BACS, NF 52120-1, Air France | ✅ connu |
| Corpus réglementaire | `1Kqns6VQT3zRu8fjc8kj_JDoBuPQrQZrQ` | OPERAT, JO décrets, plaquettes | ✅ connu |
| **Factures réelles** | `1RaexzcB_tsjoCaPG90Jb7W4gRtxASaoW` | ~30 PDFs EDF/Engie/TotalEnergies/Endesa/Soregie/SME/PEF | 🆕 **à ajouter memory** |
| **EE Flashes (EuropEnergies)** | `1tNpm6LdZM1psEj-vMqczEtgwBEZsvcH1` | ~30 newsletters daily/mensuelles marché | 🆕 **à ajouter memory** |
| **Réglementaire récent** | `1ACMBf-AHy1mvDY0npchDTvBkDB38FJTw` | TURPE 7 brochures, TRVE 2026, JO 28/01/2026, ATRD7, ATRT8 | 🆕 **à ajouter memory** |
| **APIs Enedis SGE** | `1hKMCrOsIzZn4E4IANHaIecxSkBMQe5-k` | Mesures/Point/Affaires v0 (2026-05), MappingR6X, Homologations V25.6→V26.2 | 🆕 **à ajouter memory** |
| **Templates intégration** | `1G9RqstpMOG9tleAMz-egUxh2yPC7veGX` | Schéma canonique factures Elec + Gaz + requête Enedis/GRDF (Energisme) | 🆕 **à ajouter memory** |

### 3.2 Top documents 🟦 officiels — billing

| Document | fileId | Énergie | Brique | Verbatim clé extrait |
|---|---|---|---|---|
| **`brochure-tarifaire-turpe-7 (1).pdf`** (CRE délib 2025-78) | `1z9hLgaYVVDY64lDa3wCx2Yaya3XT-FG1` | Élec | TURPE 7 | `CS = b₁·P₁ + Σ bᵢ·(Pᵢ–Pᵢ₋₁) + Σ cᵢ·Eᵢ` ; `CMDPS HTA = Σ 0,04·bᵢ·√Σ(ΔP²)` ; `CMDPS BT>36 = 12,41 €·h` ; plafonds 30% facture & 25× tarif PS suppl. ; CER `tg φ max 0,40 = 2,44 c€/kVAr.h` ; CACS 4 045,96 €/cellule/an + 1 103,68/1 655,52 €/km ; CG HTA 499,80 €/an ; CC HTA 376,39 €/an ; CACNC socle 6,48 € + maj 4,14 €/bimestre |
| **`250204_2025-40_TURPE_7_HTA-BT.pdf`** (CRE délib 2025-40) | local | Élec | TURPE 7 | Formule évolution annuelle `Z = IPC + X + k` ; X = −0,35 % ; k ∈ [−3%, +3%] ; entrée en vigueur 01/08/2025 ; durée 4 ans (2025-2028) ; revenu autorisé moyen 18 143 M€/an ; CRCP solde fin TURPE 6 = +3 548 M€ |
| **`250313_2025-77_Post-CSE_TURPE_7_HTB.pdf`** | `1JLk7E8DyK_BxnGv0vP2Rig05nyMcftF3` | Élec HTB | TURPE 7 HTB | Tarifs HTB1/HTB2/HTB3 — clients industriels haut de gamme (hors MVP P1) |
| **`260204_2026-33_Modif_TURPE_7_HTB_HTA_BT.pdf`** (CRE 2026-33) | local | Élec | TURPE 7 réforme HC | Réforme heures creuses méridiennes 11h-14h (creux solaire) — déploiement automne 2025 → fin 2027 — 28M PDL BT + 0,5M HTA concernés |
| **`251216_2025-270_ATRT8.pdf`** (CRE délib 2025-270) | local | Gaz | ATRT 8 transport | Tarif transport gaz GRTgaz/Teréga ; entrée 01/01/2025 ; durée 4 ans ; trajectoire IPC + X (−0,24%) + k (±3%) ; péréquation nationale sauf Corse/Guadeloupe |
| **`240215_2024-40_ATRD7_Post_CSE.pdf`** | `1e4EHr68HW_v-jt3bm7hFaquYTOnm8kKl` | Gaz | ATRD 7 distribution | 294 k chars — grilles ATRD7 T1/T2/T3/T4 + TP (abonnement + débit-prix). **À parser via subagent** avant tout code |
| **`260220_2026-15_ATRD7_ELD.pdf`** (CRE 2026-15) | local | Gaz | ATRD 7 ELD | Tarif ELD (Entreprises Locales Distribution) — synchrone calendrier national |
| **`260128_2026-28_maj_tarifaire_ATRT8_1er_avril_2026.pdf`** | local | Gaz | ATRT 8 maj | Mise à jour annuelle ATRT 8 au 01/04/2026 |
| **`260115_2026-14_Arrete_CTA.pdf`** (arrêté ministériel CTA) | local | Élec + Gaz | CTA | CTA = 15% × part fixe TURPE depuis 02/2026 (historique : 27,04% avant 08/2021, 21,93% avant 02/2026) ; CTA HTB2 = 10,11% |
| **`260210_2026-44_CART-P.pdf`** (CRE 2026-44) | local | Élec | CART-P production | Contrat Accès Réseau Transport Production (producteurs) — hors scope facture client B2B classique |
| **`260210_2026-48_Tarif_non_pereque_GRDF.pdf`** | local | Gaz | ATRD 7 non péréqué | Tarif GRDF zones non péréquées (Corse, DOM) |
| **`260210_2026-43_Parametrage_PL_26-27.pdf`** | local | Élec | Capacité | Paramétrage Plafond Long terme (mécanisme capacité 2026-2027) |
| **`260226_2026-52_Tarif_unitaire_minoration_du_vnu_2026.pdf`** | local | Élec | VNU (post-ARENH) | Minoration tarif unitaire VNU 2026 — directement lié à l'anomalie R19 PROMEOS (VNU dormant) |
| **`260226_2026-54_PI_2026_RTE.pdf`** | local | Élec | Pertes injection | Coefficient pertes RTE 2026 |
| **`260226_2026-49_Coefficients_A.pdf`** | local | Élec | TURPE/Tarification | Coefficients A (lissage CRCP) |
| **`260312_2026-61_Avis_arrete_prix_negatifs.pdf`** | local | Élec | Marché spot | Avis CRE prix négatifs (513h en 2025) |
| **`260312_2026-62_Avis_Flexibilites_reseau.pdf`** | local | Élec | Flexibilité | Avis CRE flexibilités réseau |
| **`260312_2026-63_Terme_tarifaire_stockage_2026.pdf`** | local | Élec | Stockage | Terme tarifaire stockage 2026 |
| **`260327_2026-67_Approbation_Accord_Injection_THT.pdf`** | local | Élec | Injection THT | Hors MVP P1 |

### 3.3 Top documents Enedis 🟦 — référentiel facturation

| Document | fileId / chemin local | Brique | Verbatim clé |
|---|---|---|---|
| **`Enedis_Flux F15_Relevé résiduel TURPE7_principes_facturation_fournisseurs.pdf`** | `1Y1R82ZMtAxjVrWFI3jxgMRfNx3Y1fRtI` | F15 / CACNC | 6 cas codés (F5/F6/F1/F2 + cessation + annulation) avec valeurs exactes : ASCS-E = 6,48 € ; ASCS-R = −6,48 € ; ASCS-F-U = 2,12 € prorata ; ASCA = 4,14 € ; balises XML `<Date_Dernier_Releve_Reel>`, `<Motif_Exemption_Releve_Residuel>` |
| **`Enedis.SGE.GUI.0561.API.Mesures_v0.pdf`** (mai 2026) | `11-UvtRn6a5-BYbZyHk3yukkkh-Sq1H6U` | Ingestion mesures | API officielle B2B post-DataConnect — schémas index, courbe charge |
| **`Enedis.SGE.GUI.0562.API.Point_v0.pdf`** | `127iLI3XeOsaB4kNCgF8Y_9upZrJvivy-` | Référentiel PRM | Métadonnées PRM : segment C1-C5, code FTA, puissance souscrite active |
| **`Enedis.SGE.GUI.0560.API.Affaires_v0.pdf`** | `1Q2KSbnf7p0Nifs7usMjO-ho1DMNuD9LB` | Demandes Enedis | Mise en service, changement puissance souscrite, etc. |
| **`Enedis.SGE.CAR.0549.MappingFluxR6X_v1.0.0.xlsx`** | `1-kJwYHJdqMucElMBbKz-CE4nKyv7Y0Ug` | Mapping R6X → API | Référence pivot ingestion |
| **`Enedis.SGE.AX.0355.Annexe ListeDeValeurs_v4.6.0.pdf`** | `1WOo1B-ItFBGhA7dF3SOm5C_jYfQO6P-p` | Référentiel Enedis | Toutes les valeurs codées : code FTA, segments C1-C5, options tarifaires, types compteurs |
| **`Enedis SGE GUI 0300 Flux C15_v5.1.3.pdf`** | local | Flux C15 | Référentiel flux C15 (changement contrat) |
| `Enedis Homologation Session type 1_SGE V26.2_C2C4_V0.pdf` + V25.6/V25.9 | local | Homologation SGE | Specs versionnées API — utiliser V26.2 (la plus récente) |
| `20260319 - Reprog. HC - planning stabilisé phase 2 - V1.pdf` | local | Réforme HC | Planning Enedis reprogrammation heures creuses |
| `2026 02 19 CR ad-hoc CSF HPHC v1.pdf` | local | CSF HPHC | Concertation système fournisseur HP/HC |

### 3.4 Templates 🟩 schéma de facture (Energisme intégré)

| Document | fileId | Énergie | Idée |
|---|---|---|---|
| **`Template intégration de factures Elec.xlsx`** (Energisme) | `1O49L8hr3fvbaWv1bNN4UPEwmRnAJshlS` | Élec | **80+ champs canoniques FR/EN** : `invoice.elec_cost_cc/cg/fixed_charge_cs/variable_charge_cs/cmdps`, `elec_power_supply_*` (HPSH/HCSH/HPSB/HCSB/pointe), `elec_price_tax_cspe/tc/td`, `cost_obligation_eec` (CEE), `cost_tax_cta` |
| **`Template intégration de factures GAZ.xlsx`** | `1mXtwiTe133WJWuUNIvQ4z4YSQg5dBp9l` | Gaz | Champs : `gas_contract_rate_option`, `gas_cost_distribution`, `gas_cost_transport`, `gas_cost_excess_cj` (dépassement CJ), `gas_cost_tcs`, `gas_cost_tax_ticgn`, `consumption_invoiced`, `gas_ref_pce` |
| **`Template requête Enedis GRDF.xlsx`** | `1pY-5P0oN72k1lGVKy1jbJeyDGObgO4Ba` | Mixte | Formulaire demandes consentement PRM/PCE |

### 3.5 Golden set OCR 🟩 — factures réelles (~30 PDFs)

Dossier Drive `1RaexzcB_tsjoCaPG90Jb7W4gRtxASaoW` (à intégrer memory) — couverture multi-fournisseurs :

| Fournisseur | Énergie | Exemples |
|---|---|---|
| EDF | Élec | `Facture_EDF_10226229166.pdf`, `eDF_Facture_20250329_080531.pdf` |
| Engie | Élec | `ENGIE_05.25.pdf`, `été_2025_engie.pdf`, `facture-2025-12-21_engie.pdf` |
| TotalEnergies | Élec | `TOTAL_ENERGIES.pdf` + variants |
| Endesa | Gaz | `Gaz_-_2025_08_Facture_ENDESA.pdf`, `Endesa-Offre_Eco_Gaz-36_mois.pdf` (×3) |
| Soregie (ELD) | Élec | `Facture_soregie_.pdf` |
| SME (ELD) | Élec | `SME197861_08-2025.PDF` |
| PEF / autres | Mixte | `F1305571725.pdf`, `facture_R24181344.pdf`, `1002539004FP*.pdf` |
| Régularisation annuelle | Élec | `Facture-Annuelle.pdf` |

**Usage Bill Intelligence P1** : créer `backend/tests/fixtures/bills/` avec au moins **1 fixture par fournisseur × énergie** pour parser OCR + assertions shadow billing.

### 3.6 Document RTE 🟦 — anatomie facture HTB

**`202508_Comprendre votre facture.pdf`** (`1VicefCfsDsbnRVja7Ux0VO7vRdftD339`) — derrière ce titre pédagogique se cache la **spec officielle RTE** d'une facture HTB :
- Layout exact d'une facture HTB
- PLIC (Pertes en Ligne et Inducteur de Charge)
- Puissances souscrites par plage (HPTE / HPSH / HCSH / HPSB / HCSB)
- Mécanisme **`hausse après baisse (HB)`** — logique de régularisation rétroactive
- tg φ, Psmax/Pdim, code EIC
- Taux CTA HTB2 = 10,11 %
- ASCS Linky / F15

**À lire impérativement** avant tout code shadow billing HTB.

---

## 4. Skills PROMEOS lus (base de vérité interne)

Synthèse couverture skills (corpus 2000+ lignes) — détail dans rapport agent B :

### 4.1 Règles bien couvertes (5)

| # | Règle | Skill | Status | Constante / Référence |
|---|---|---|---|---|
| 1 | **TURPE 7 — soutirage** (€c/kWh par période) | `promeos-billing` p.151-162 | ✅ implémenté | `tarifs_reglementaires.yaml`, `tariff_period_classifier.py` |
| 2 | **TURPE 7 — gestion / comptage / dépassement (CMDPS)** | `promeos-billing` p.163-180 | ✅ implémenté | CMDPS = 12,65 €·h (vs CRE = 12,41 €·h — **divergence à valider**) |
| 3 | **Accise électricité versioning temporel** | `promeos-billing` p.138-149 | ✅ implémenté | T1 = 30,85 €/MWh (ménages), T2 = 26,58 €/MWh (PME/pro) depuis 01/02/2026 |
| 4 | **CTA versioning** (15% part fixe depuis 02/2026) | `promeos-billing` p.122, 287 + anomalie R009 | ✅ implémenté | Constantes versionnées YAML |
| 5 | **TVA 5,5% / 20%** (abonnement + CTA vs reste) | `promeos-billing` p.256-259 + anomalie R007 | ✅ implémenté | CGI art. 278-0 bis |

### 4.2 Règles partielles (5)

| # | Règle | Lacune | Action |
|---|---|---|---|
| 1 | **Gaz ATRD/ATRT grilles détaillées** | Montants globaux uniquement (16,39 €/MWh accise gaz), pas de grille par classe ATRD/ATRT comme TURPE 7 | Acquérir grilles GRDF/Teréga depuis `240215_2024-40_ATRD7_Post_CSE.pdf` |
| 2 | **CEE P5 → P6 transition** | P5 implicite ~5 €/MWh en `billing_shadow_v2.py`, **P6 (2026-2030) non intégrée** | Attendre stabilisation marché P6 fin 2026 |
| 3 | **Capacité — répercussion client** | Obligation détaillée (PP1 10-15 j, prix ~20-40 k€/MW), pas de formule €/MWh fine par classe puissance | Délibération CRE 2026-43 (`Parametrage_PL_26-27`) à exploiter |
| 4 | **ACC-TURPE** (autoconsommation collective) | Exonération composante variable décrite p.42-44 `energy-autoconsommation`, pas d'intégration shadow billing | Doc CRE `plaquette_consoprod_TURPE7-VF.pdf` |
| 5 | **CEE constante prix** `CEE_PRIX_MWHC_CUMAC_EUR` | Valeur 8,50 €/MWh documentée SKILL.md p.44, **n'existe pas en `constants.py`** | TODO canonisation tracking EPIC |

### 4.3 Règles manquantes (5)

| # | Règle | Source canonique requise |
|---|---|---|
| 1 | **Gaz ATRD/ATRT grilles complètes** par classe abonnement/débit-prix | CRE délibérations + brochures GRDF/Teréga |
| 2 | **CEE P6 catalogue exhaustif fiches BAT** (~200+) | Arrêté CEE P6 DGEC 2026 |
| 3 | **Formule DPE tertiaire** (transposition EPBD recast) | À attendre 2026-2027 |
| 4 | **Scoring conformité — applicabilité contextuelle dynamique** | Doctrine interne PROMEOS à formaliser |
| 5 | **Commission courtier pass-through** en contrat | Pas de format standard de marché — usage interne |

---

## 5. Sources officielles web

**Méthode** : les PDFs CRE locaux ETANT les sources officielles publiées (délibérations CRE numérotées + arrêtés JORF), les URLs ci-dessous sont fournis pour traçabilité et recroisement futur. **Aucune règle commit-ée ne peut citer une source 🟨 sans recroisement avec une de ces URLs**.

| Source | Type | URL canonique | Périmètre |
|---|---|---|---|
| **CRE** | Délibérations tarifaires | https://www.cre.fr/documents/Deliberations | TURPE 6/7, ATRT 7/8, ATRD 6/7, CART-P, CTA, capacité |
| **Légifrance** | Codes + arrêtés | https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000023983208 (Code énergie) ; CGI art. 278-0 bis | TURPE base légale L.341-2, TVA, accises |
| **Enedis** | Documentation SGE / DataConnect / Mesures | https://www.enedis.fr/documentation ; https://datahub.enedis.fr/ | Référentiel PRM, flux F15/C15/R6X, API v0 |
| **GRDF** | Documentation tarifaire | https://www.grdf.fr/fournisseurs/regulation | ATRD 7, tarif non péréqué |
| **GRTgaz / Teréga** | Documentation transport | https://www.grtgaz.com/ ; https://www.terega.fr/ | ATRT 8, débit normalisé |
| **Énergie-Info** | Médiateur national énergie | https://www.energie-info.fr/ | Litiges facture, droits client B2C / B2B |
| **impots.gouv.fr** + **BOFiP** | Fiscalité | https://bofip.impots.gouv.fr/ | TVA 5,5% (abo + CTA), TVA 20% (énergie + taxes) |
| **Douanes** (DGDDI) | Accises | https://www.douane.gouv.fr/dossier/taxes-energies | Accise élec (TICFE renommée), accise gaz (TICGN) |
| **RTE** | Tarification HTB + capacité + flexibilités | https://www.services-rte.com/ | TURPE 7 HTB, mécanisme capacité, EcoWatt |
| **Ministère Économie / BO arrêtés** | CTA + capacité + ARENH/VNU | https://www.economie.gouv.fr/ | Arrêtés CTA, paramétrage capacité |

---

## 6. Matrice des règles de facture

**Lecture matrice** : chaque ligne = 1 règle facture identifiée, sourcée, prête à devenir un test backend / un anomaly detector / un champ schema. Priorité = priorité d'intégration code Bill Intelligence P1.

### 6.1 Électricité — Fourniture (énergie)

| Doc | Source | Brique | Règle extraite | Champs nécessaires | Formule | Périodicité | Unité | Test attendu | Priorité |
|---|---|---|---|---|---|---|---|---|---|
| Templates Energisme | 🟩 | Fourniture | Composante énergie par plage (HPSH/HCSH/HPSB/HCSB/PTE) | `elec_power_supply_hpsh/hcsh/hpsb/hcsb/pte`, `unit_price_eur_per_kwh`, `consumption_kwh` | `cost = consumption_kwh × unit_price_eur_per_kwh` par plage | Mensuel | €/kWh | `assert ∑(plage.cost) == invoice.energie.cost_ht` | **P0** |
| Contrats B2B (skills) | 🟦 + 🟩 | Fourniture | Prix indexé (formule contractuelle : ARENH, spot M+1, Cal Y+1, EPEX SPOT) | `indexation_formula`, `spread_eur_mwh`, `index_value` | `prix_unitaire = index + spread` (recalcul par mois) | Mensuel | €/MWh | Recalc shadow vs facture, écart ≤ 0,1% | **P0** |
| CRE 2026-52 minoration VNU | 🟦 | Fourniture post-ARENH | Minoration tarif unitaire VNU 2026 (lié anomalie R19 dormant) | `vnu_volume_mwh`, `vnu_unit_price_eur_per_mwh`, `vnu_minoration_pct` | Tarif officiel CRE 2026-52 (à parser) | Annuel | €/MWh | Anomalie R19 doit avoir `actual_value` non NULL | **P0** |
| EE Flashes (inspiration) | 🟨 | Fourniture | Prix négatifs (513h en 2025, 1807h ≥100€/MWh) | `spot_price_eur_mwh`, `is_negative_price_hour` | Croiser EPEX SPOT day-ahead | Horaire | €/MWh | Flag si conso pendant prix négatif → opportunité valorisation | P2 |

### 6.2 Électricité — Acheminement (TURPE 7)

| Doc | Source | Règle | Champs | Formule | Périodicité | Unité | Test | Priorité |
|---|---|---|---|---|---|---|---|---|
| **CRE délib 2025-78 (brochure TURPE 7)** | 🟦 | **Composante Soutirage CS** | `b_coef` (par option/plage), `c_coef` (par plage), `puissance_souscrite_kw`, `consommation_kwh`, `plage_horaire` | `CS = b₁·P₁ + Σ bᵢ·(Pᵢ–Pᵢ₋₁) + Σ cᵢ·Eᵢ` | Annuel (révision 01/08) | €/an | Recalc shadow ≈ facture (tolérance 0,1€) | **P0** |
| CRE 2025-78 | 🟦 | **Composante Gestion CG** | `segment` (HTA/BT≤36/BT>36), `puissance_kw` | HTA : 499,80 €/an • BT>36 : 249,84 €/an • BT≤36 : 18 €/an | Annuel | €/an | Constante par segment | **P0** |
| CRE 2025-78 | 🟦 | **Composante Comptage CC** | `segment`, `type_compteur` (LINKY_C5, HISTORIQUE_C4, C3, C2) | HTA : 376,39 €/an • BT>36 : 283,27 €/an • BT≤36 : 22 €/an | Annuel | €/an | Constante par segment + type | **P0** |
| CRE 2025-78 | 🟦 | **CMDPS HTA** (dépassement) | `puissance_souscrite_kw`, `puissance_atteinte_max_kw`, `duree_depassement_h` | `CMDPS_HTA = Σ 0,04·bᵢ·√Σ(ΔP²)` | Mensuel | € | Test edge case dépassement 2h × 50 kW | **P0** |
| CRE 2025-78 | 🟦 | **CMDPS BT>36 kVA** | `puissance_souscrite_kva`, `puissance_atteinte_kva`, `duree_depassement_h` | `CMDPS = 12,41 €·h` (vs 12,65 actuellement en `tarifs_reglementaires.yaml` — **divergence**) | Mensuel | € | ⚠️ valider source CRE vs constante PROMEOS | **P0** |
| CRE 2025-78 | 🟦 | **CER** (énergie réactive) | `tg_phi`, `kvar_h_facturable` | tg φ max 0,40 = 2,44 c€/kVAr.h (HTA uniquement TURPE 7) | Mensuel | c€/kVAr.h | Test si tg φ > 0,40 → CER facturée | **P1** |
| CRE 2025-78 | 🟦 | **CACS** (raccordement) | `nb_cellules`, `nb_km_ligne` | 4 045,96 €/cellule/an + 1 103,68 / 1 655,52 €/km | Annuel | €/an | Forfaitaire — pas anomalie facture régulière | P2 |
| CRE 2025-78 | 🟦 | **CACNC** (composante additionnelle non communicant) | `type_compteur=HISTORIQUE`, `non_communication_index` | Socle 6,48 € + maj 4,14 €/bimestre si non-communication | Bimestriel | € | Anomalie : compteur non-Linky post 01/08/2025 sans CACNC | **P0** |
| CRE 2025-77 | 🟦 | **CT Composante Transformation BT→HTA** | `transformation_active`, `puissance_kw` | 10,54 €/kW/an | Annuel | €/kW/an | Edge case clients avec transfo dédiée | P2 |
| CRE 2025-40 | 🟦 | **Formule évolution annuelle** | `IPC`, `X=-0,35%`, `k ∈ [-3%, +3%]` (apurement CRCP) | `Z = IPC + X + k` | Annuel (01/08) | % | Sanity check : grille 01/08/N+1 vs N respecte ±5% max | **P1** |
| CRE 2026-33 | 🟦 | **Réforme HC méridiennes 11h-14h** | `plage_horaire`, `date_facture` | Déploiement progressif automne 2025 → fin 2027 | Migration | n/a | Anomalie : facture post-déploiement avec ancienne plage | P1 |

### 6.3 Électricité — Taxes / contributions

| Doc | Source | Règle | Champs | Formule | Périodicité | Unité | Test | Priorité |
|---|---|---|---|---|---|---|---|---|
| Arrêté CTA 2026-14 | 🟦 | **CTA = 15% × part fixe TURPE** (depuis 02/2026) | `tarif_part_fixe_turpe`, `cta_rate_pct=15` | `CTA = part_fixe × 15%` | Mensuel | € | Anomalie R009 si CTA ≠ 15% post 02/2026 | **P0** |
| Skill `promeos-billing` (5 régimes) | 🟦 (versioning) | **Accise électricité — versioning temporel strict** | `date_consommation` (PAS date_facture), `accise_rate_eur_per_mwh`, `client_type` (T1 ménages / T2 PME-pro) | T1 = 30,85 €/MWh, T2 = 26,58 €/MWh depuis 01/02/2026 | Mensuel | €/MWh | Anomalie R014 si accise ≠ taux en vigueur à la date de conso | **P0** |
| CGI art. 278-0 bis | 🟦 | **TVA 5,5%** sur abonnement + CTA + accise | `line_type` ∈ {ABONNEMENT, CTA, ACCISE}, `tva_rate=5.5` | `tva = ht × 5,5%` | Mensuel | €/% | Anomalie R003 si TVA ≠ 5,5 sur ces lignes | **P0** |
| CGI art. 278-0 bis | 🟦 | **TVA 20%** sur énergie + autres taxes | `line_type` ∈ {ENERGY, NETWORK, TAX_OTHER}, `tva_rate=20` | `tva = ht × 20%` | Mensuel | €/% | Anomalie R003 si TVA ≠ 20 | **P0** |
| TURPE 7 + arrêté CTA | 🟦 | Sommes TVA = total TVA facture | `∑(line.tva_amount)`, `invoice.total_tva` | `∑ = total` (tolérance 0,02€) | Par facture | € | Anomalie R018 | **P0** |
| Marché capacité (CRE 2026-43) | 🟦 + 🟨 | **Composante capacité** | `capacity_certif_mwh`, `pp1_hours_consumed_kwh`, `capacity_price_eur_per_mw` | `capacity_cost = pp1_kwh × certif_price` | Annuel | €/MWh | Test : présent si client > seuil | **P1** |
| Skill `cee-p6` | 🟦 + 🟩 | **CEE pass-through P5** (~5 €/MWh implicite) | `cee_pass_through` (bool), `cee_amount_eur` | Si pass-through : `cost = conso_mwh × ~5€/MWh` | Mensuel | €/MWh | Anomalie : CEE absent si contrat pass-through actif | **P1** |

### 6.4 Gaz — Fourniture + acheminement

| Doc | Source | Règle | Champs | Formule | Périodicité | Unité | Test | Priorité |
|---|---|---|---|---|---|---|---|---|
| Templates Energisme GAZ | 🟩 | **Composante fourniture gaz** | `gas_unit_price_eur_per_kwh`, `consumption_kwh_pcs`, `pci_pcs_coefficient` | `cost = conso_kwh_pcs × prix` | Mensuel | €/kWh PCS | Conversion m³ → kWh PCS via coefficient | **P0** |
| ATRD 7 (`240215_2024-40_ATRD7_Post_CSE.pdf`) | 🟦 | **Composante distribution ATRD 7 — option tarifaire (T1/T2/T3/T4/TP)** | `atrd_option` enum, `abonnement_annuel`, `prix_proportionnel_eur_kwh`, `cjn_mwh_per_day` (CJN) | Tableau ATRD 7 GRDF par option | Annuel (01/07) | €/an + €/kWh | Recalc shadow par option | **P0** |
| ATRT 8 (CRE 2025-270) | 🟦 | **Composante transport ATRT 8** | `atrt_zone_code` (TRF/TRD/TRS), `souscription_kwh_j`, `conso_kwh_mois` | `cost = souscription × jours + conso × tarif` | Mensuel | €/an + €/kWh | Recalc shadow + dépassement CJ | **P1** |
| ATRD 7 + ATRT 8 | 🟦 | **CTA gaz** (Contribution Tarifaire d'Acheminement) | `cta_rate_pct`, `acheminement_part_fixe` | `CTA = acheminement_fixe × taux` | Mensuel | €/% | Anomalie si absent | **P0** |
| TICGN (Douanes) | 🟦 | **Accise gaz TICGN** | `consommation_kwh`, `ticgn_rate_eur_per_mwh=16,39` (10,73 base + 5,66 ZNI) depuis 02/2026 | `accise_gaz = conso_mwh × 16,39` | Mensuel | €/MWh | Anomalie : taux ≠ 16,39 post 02/2026 | **P0** |
| CGI art. 278-0 bis | 🟦 | **TVA gaz** : 5,5% abonnement / 20% énergie+accise | idem élec | idem | Mensuel | % | Anomalie R003 | **P0** |
| ATRD 7 | 🟦 | **Dépassement CJN gaz** (débit normalisé) | `cjn_souscrit_mwh_j`, `cjn_atteint_mwh_j`, `tarif_depassement_eur_kwh` | Pénalité tarif × surplus | Mensuel | € | Anomalie R19 équivalent gaz | **P1** |

### 6.5 Régularisations / avoirs / mécanismes spéciaux

| Doc | Source | Règle | Champs | Formule | Périodicité | Unité | Test | Priorité |
|---|---|---|---|---|---|---|---|---|
| Flux F15 Enedis | 🟦 | **CACNC ASCS** (Active Substitution Compteur Smart) | `ascs_eur`, `motif_flag` ∈ {F5/F6/F1/F2/cessation/annulation} | 6 cas codés : `ASCS-E=+6,48`, `ASCS-R=−6,48`, `ASCS-F-U=+2,12 prorata`, `ASCA=4,14` | Bimestriel | € | Test : parser F15 + assert 1 cas appliqué | **P1** |
| Templates Energisme | 🟩 | **Avoirs / notes de crédit** | `invoice_type=CREDIT_NOTE`, `original_invoice_id`, `amount_eur < 0` | `total_ttc < 0` ou `total_ttc = 0` | Ad hoc | € | Anomalie R016 (TTC=0) : INFO seulement | **P1** |
| Templates Energisme | 🟩 | **Régularisation annuelle** | `invoice_type=REGULARIZATION`, `period_start/end` (annuel), `previous_estimated_kwh`, `actual_kwh` | Différence (réel - estimé) × prix | Annuel | € | Test : période > 35j → R014 INFO | **P1** |
| RTE `202508_Comprendre votre facture.pdf` | 🟦 | **Hausse Après Baisse (HB) HTB** | `tarif_avant`, `tarif_apres`, `volume_concerné` | Mécanisme HTB de régularisation rétroactive lors d'un changement tarif | Ad hoc | € | Test edge case HTB | **P2** |
| Skills `promeos-enedis` | 🟦 | **Index relevé vs estimé** (consommation) | `index_releve`, `index_estime`, `pdl`, `date_releve` | Anomalie si écart > 10% | Mensuel | kWh | Anomalie R022 (à créer) | **P1** |

### 6.6 Erreurs détectables transverses (anomalies)

| # | Anomalie | Source règle | Conditions détection | Sévérité | Priorité |
|---|---|---|---|---|---|
| **R001** | Somme composantes vs total HT | Universel | `∑(comp.amount_ht) ≠ invoice.total_ht` (tolérance 0,02€) | ERROR | P0 |
| **R002** | TTC = HT + TVA | Universel | `total_ht + total_tva ≠ total_ttc` | ERROR | P0 |
| **R003** | TVA taux correct par composante | CGI 278-0 bis | Abo/CTA/accise → 5,5% ; reste → 20% | ERROR | P0 |
| **R004** | TVA montant = base × taux | Universel | `amount_ht × tva_rate ≠ tva_amount` | WARNING | P0 |
| **R005** | Quantité × prix = montant | Universel | `qty × unit_price ≠ amount_ht` (±0,02€) | WARNING | P0 |
| **R007** | Composantes obligatoires présentes | Législation | Élec : accise + CTA présentes. Gaz : idem | WARNING | P0 |
| **R009** | Composante opaque (type=autre) | Logique | `component_type == 'autre'` | INFO | P1 |
| **R010** | Doublon composante | Logique | Même (type, label) apparaît 2× | WARNING | P0 |
| **R011** | Conso composantes vs conso globale | Logique | `∑(conso_comp) ≠ conso_kwh_total` | WARNING | P1 |
| **R012** | Base accise vs conso | Législation | `accise.qty_kwh ≠ conso_kwh_facturée` | WARNING | P0 |
| **R013** | Prix unitaire plage crédible | Marché | `unit_price` ∉ [0,01 ; 1,00] €/kWh | WARNING | P1 |
| **R014** | Période > 35 jours | Logique | Facture couvre > 1 mois | INFO | P1 |
| **R015** | Facture sans composante | Logique | `len(components) == 0` | CRITICAL | P0 |
| **R017** | PDL/PCE manquant | Opérationnel | Pas d'identifiant point livraison | INFO | P1 |
| **R018** | Somme TVA vs total TVA | Universel | `∑(comp.tva_amount) ≠ invoice.total_tva` | ERROR | P0 |
| **R019** | **Pénalité / dépassement puissance** | Opérationnel | `max(P_consommée) > P_souscrite` OU `has_penalty=true` | WARNING | P0 |
| **R020** | Montant total élevé | Seuil interne | `total_ttc > 50 000 €` | INFO | P2 |
| **R022** | **Index relevé vs estimé (>10%)** | Logique | écart > 10% | WARNING | P1 (à créer) |
| **R023** | **Tarif obsolète post-révision** | CRE | `version_turpe=TURPE_6` et `date_facture > 2025-07-31` | CRITICAL | P0 (à créer) |
| **R024** | **Non-Linky sans CACNC** | CRE 2025-78 | `type_compteur=HISTORIQUE` + `date >= 2025-08-01` + pas CACNC 6,48€ | WARNING | P0 (à créer) |
| **R025** | **Soutirage hors grille TURPE 7** | CRE 2025-78 | `unit_price_kwh` < min ou > max grille | WARNING | P1 (à créer) |
| **R026** | **CTA gaz absent** | Arrêté CTA | Facture gaz sans ligne CTA | WARNING | P1 (à créer) |
| **R027** | **Régularisation sans préavis** | Code énergie | Régul > 12 mois antérieurs sans préavis | WARNING | P2 (à créer) |

---

## 7. Impact PROMEOS — gaps par règle

Croisement matrice ↔ audit Bill Intel (`audit_brique_bill_intelligence_deep_readonly_2026_05_23.md`).

### 7.1 P0 — bloquants avant tout sprint additionnel

| Règle / domaine | Modèle existant | Champ existant | Route existante | Test existant | Gap | Impact UX DAF | Preuve attendue | Action Centre d'Action |
|---|---|---|---|---|---|---|---|---|
| **CMDPS = 12,41 vs 12,65 (divergence CRE vs PROMEOS)** | ✅ `tarifs_reglementaires.yaml` | ✅ `CMDPS_COEFFICIENT` | ✅ recalc shadow | ⚠️ test sur 12,65 | ❌ Vérifier source CRE puis aligner | KPI dépassement faussé | Délibération CRE 2025-78 + arrêté annuel | Anomalie R019 mauvais montant |
| **TURPE 6 → TURPE 7** versioning | ✅ champ `version_turpe` | ✅ existe | ⚠️ vérifier propagation | ⚠️ tests | ⚠️ Anomalie R023 à créer | Score conformité erroné si facture post 01/08/2025 avec TURPE 6 | Délibération CRE 2025-40 | Action "Migrer facture TURPE 7" |
| **CACNC non-Linky** (6,48 €/bimestre) | ❌ pas de modèle dédié | ❌ pas de champ | ❌ pas de route | ❌ pas de test | ❌ Anomalie R024 à créer | DAF ne voit pas que client paye CACNC évitable | Flux F15 Enedis (6 cas codés) | Action "Demander pose Linky" |
| **Accise élec versioning** (taux à date conso) | ✅ skill `promeos-billing` | ✅ `tarifs_reglementaires.yaml` | ✅ recalc | ⚠️ tests historique | ✅ couvert | KPI loss correct | YAML versionné | R014 INFO seulement |
| **CTA versioning (15% post 02/2026)** | ✅ skill | ✅ YAML | ✅ R009 | ✅ tests | ✅ couvert | n/a | n/a | n/a |
| **TVA 5,5% / 20% par ligne** | ✅ champ `tva_rate` ligne | ✅ R003/R007 | ✅ détecteur | ⚠️ tests par ligne | ⚠️ valider R003 sur tous types ligne | KPI fiscal | CGI 278-0 bis | Action "Demander avoir rectificatif" |
| **R001/R002/R018** arithmétique base | ⚠️ partiellement (`bill_anomaly.py` Phase 5.1) | ⚠️ pas tous codes | ⚠️ pas détecteur dédié | ⚠️ partiel | ⚠️ Compléter R01-R20 backend | KPI cohérence | n/a (universel) | Anomalie ERROR bloquante |
| **Anomalie sans `actual_value`** (audit Bill Intel P0 §3) | ✅ `BillAnomaly.actual_value` | ⚠️ nullable | ✅ `POST /audit/{id}` | ❌ pas de test rejet | ❌ Ajouter CHECK ou assertion runtime | KPI VNU dormant = 0 € faux | Détecteur peuple toujours | Anomalie incomplète refusée |
| **FK Evidence formelle anomalie** (audit Bill Intel P0 §3) | ❌ pas de `BillAnomalyEvidence` | ❌ `details_json` semi-structuré | ❌ pas d'endpoint download | ❌ rien | ❌ Créer table dédiée + endpoint (pattern Evidence V4 conformité C6 P1) | DAF ne peut pas opposer la preuve | À créer | Anomalie sans preuve = pas opposable |
| **Sync anomalie → ActionCenterItem** (audit Bill Intel P1 §7.5) | ⚠️ `BillingInsight.recommended_actions_json` | ⚠️ JSON pas FK | ❌ pas d'endpoint sync | ❌ rien | ❌ Créer `POST /api/billing/sync-actions-from-anomalies` (similaire conformité C1) | Boucle non fermée — DAF doit créer manuellement | n/a (pattern conformité P1) | Bouton "Créer les actions billing" |

### 7.2 P1 — durcissement après P0

| Règle / domaine | Gap | Source canonique | Action |
|---|---|---|---|
| **Grilles ATRD 7 par option (T1/T2/T3/T4/TP)** | Pas en YAML | `240215_2024-40_ATRD7_Post_CSE.pdf` (294 k chars, à parser via subagent) | Ajouter grilles + recalc gaz |
| **Grilles ATRT 8** | Pas en YAML | CRE 2025-270 | Idem |
| **CEE pass-through P5 (~5 €/MWh)** | Implicite billing_shadow_v2 | Skill cee-p6 + arrêté DGEC | Formaliser composante |
| **Composante capacité** | Pas de modèle | CRE 2026-43 | Ajouter champ `capacity_amount_eur` |
| **Anomalie R023** : tarif obsolète post-révision | À créer | CRE délibérations dates | Détecteur date_facture vs version_turpe |
| **Anomalie R024** : non-Linky sans CACNC | À créer | CRE 2025-78 + flux F15 | Détecteur compteur + ASCS |
| **Anomalie R022** : index relevé vs estimé (>10%) | À créer | Code énergie | Détecteur Enedis CDC |
| **Régularisation annuelle parsing** | Partiel | Templates Energisme + factures golden set | Parser dédié `invoice_type=REGULARIZATION` |
| **Avoirs (notes de crédit)** | Partiel | Templates + factures réelles | `total_ttc<0` = avoir, lien FK `original_invoice_id` |
| **Réforme HC méridiennes 11h-14h** | Pas pris en compte | CRE 2026-33 + Enedis reprog HC | Détecter facture post-déploiement avec ancienne plage |
| **ACC-TURPE (autoconsommation collective)** | Pas en shadow billing | CRE plaquette TURPE 7 ACC | Coefficient réduction conso locale |
| **TICGN ZNI** (5,66 €/MWh) | Globalement OK | Douanes | Vérifier modulation zone non interconnectée |

### 7.3 P2 — confort / opportunité

| Règle / domaine | Source | Note |
|---|---|---|
| **HTB facture (RTE)** | `202508_Comprendre votre facture.pdf` | Petite cohorte clients PROMEOS — bas effort, gain faible |
| **Hausse Après Baisse (HB)** | RTE HTB | Edge case rare, garder en backlog |
| **CER énergie réactive HTA** | CRE 2025-78 | Détection tg φ > 0,40, opportunité conseil |
| **CACS raccordement** | CRE 2025-78 | Forfaitaire, pas anomalie facture régulière |
| **CART-P production** | CRE 2026-44 | Hors B2B classique (producteurs uniquement) |
| **Marché de gros / prix négatifs** | EE Flashes + EPEX SPOT | Opportunité valorisation flexibilité (513h en 2025) |
| **Catalogue CEE P6 fiches BAT** | DGEC | Attendre arrêté |
| **DPE tertiaire** | Transposition EPBD 2026-2027 | Attendre |

---

## 8. Hypothèses internes vs règles officielles

**Séparation stricte** — règle non-négociable PROMEOS : aucune source 🟨 ou 🟪 ne peut servir seule à coder une règle tarifaire.

| Sujet | Source officielle 🟦 à utiliser | Source interne / commerciale ⚠️ à ne PAS commit |
|---|---|---|
| TURPE 7 HTA/BT coefs bᵢ/cᵢ, CG, CC, CMDPS | `brochure-tarifaire-turpe-7 (1).pdf` (CRE 2025-78) | EE Flashes daily — ordres de grandeur seulement |
| ATRD 7 gaz distribution | `240215_2024-40_ATRD7_Post_CSE.pdf` | EE-N285-mai2026 (résumé marché) |
| Accise élec/gaz 2026 | `joe_20260128_0023_0021.pdf` (JO 28/01/2026) à parser | Doc interne ChatGPT (cite 0,079 kgCO₂/kWh erroné) |
| CACNC F15 valeurs (6,48 € / 4,14 €) | `Enedis_Flux F15_...pdf` | — |
| Schéma facture parser | Templates Energisme + TURPE 7 + RTE | — |
| Code FTA / segments C5 | `Enedis.SGE.AX.0355.Annexe_ListeDeValeurs_v4.6.0.pdf` | — |
| Facteurs CO₂ (élec 0,052 / gaz 0,227) | Skill PROMEOS `emission_factors` (ADEME V23.6) | **PAS** le doc interne ChatGPT |
| Mécanisme capacité prix | ❌ pas trouvé en officiel Drive — wget direct RTE/CRE 2026-43 | EE Flashes — ordres de grandeur |
| CEE BAT-TH-XXX | `BAT-TH-116_FC.pdf` (fiche officielle) | calculcee.fr commercial |
| Logique billing N'Gage / Bamboo / Energisme | — | catalogues 🟪 — inspiration UX uniquement |

### Risque qualité identifié

- **1 doc interne PROMEOS** (`Réglementations énergétiques — données à surveiller...`) = synthèse ChatGPT citant `calculcee.fr` (source commerciale) avec **facteurs CO₂ erronés (0,079 kgCO₂/kWh élec vs 0,052 canonique)**. **Action** : isoler / archiver ; toute reprise = bug data quality.
- **Doublons brochure TURPE 7** (1) et (2) — diff à faire avant import (probable maj 1er semestre 2026).
- **Plusieurs factures dupliquées** dans dossier `1RaexzcB...` (suffixes `_Adg3mQ8.pdf` / `_ISIdzLh.pdf`) — dedup avant création fixtures.

---

## 9. Recommandations pour le sprint Bill Intelligence P1

**À NE PAS faire dans ce sprint (corrections code)** — doctrine "aucun prompt de correction produit avant cette phase".

**À faire dans le sprint Bill Intelligence P1 qui suivra** :

### 9.1 Acquisition documentaire (J0)

1. **Importer dans le repo PROMEOS** (versionné, hash SHA-256) :
   - `brochure-tarifaire-turpe-7.pdf` → `docs/base_documentaire/billing/turpe7/`
   - `Templates intégration Elec.xlsx` + `Templates intégration Gaz.xlsx` → `docs/base_documentaire/billing/schemas/`
   - 30 PDFs factures réelles → `backend/tests/fixtures/bills/` (1 par fournisseur × énergie min)
2. **Mettre à jour memory `reference-promeos-drive`** avec les 5 nouveaux dossiers IDs (§3.1).
3. **Parser via subagent** les 2 gros docs (`240215_2024-40_ATRD7_Post_CSE.pdf` 294 k + `260114_2026-06_TRVE_2026.pdf` 83 k) — extraction grilles complètes.

### 9.2 Implémentation P0 (3 chantiers)

**C1 — Durcissement anomalies (audit Bill Intel P0 §3)**
- `BillAnomaly.actual_value` : assertion runtime + plan migration `NOT NULL` après scan DB
- Créer table `BillAnomalyEvidence(anomaly_id FK, file_url, hash, mime_type, timestamp)` (pattern Evidence V4 conformité C6)
- Créer endpoint `GET /api/billing/anomalies/{id}/evidence/{ev_id}/download` (pattern conformité C6)
- Endpoint `POST /api/billing/audit-all` : fix HTTP 500 sans JWT → retour FR `NO_ORG_CONTEXT` (pattern conformité P1)

**C2 — Sync anomalie → ActionCenterItem** (pattern conformité C1)
- `POST /api/billing/sync-actions-from-anomalies` : pour chaque `BillAnomaly` ouverte → 1 `ActionCenterItem(kind=BILLING_DISPUTE, domain=BILLING)`
- Idempotent par signature `(org_id, anomaly_id)`
- Bouton UI `/bill-intel` header : *"Créer les actions de litige facture"* (pattern conformité C2)

**C3 — TURPE 7 versioning fort**
- Anomalie R023 : `version_turpe=TURPE_6` post-2025-08-01 → CRITICAL
- Anomalie R024 : non-Linky sans CACNC (6,48 €/bimestre)
- Anomalie R025 : `unit_price_kwh` hors grille TURPE 7 (par option + segment)
- Aligner constante CMDPS sur source CRE 2025-78 (12,41 €·h) avec rationale

### 9.3 Implémentation P1 (gaz + CEE)

- Importer grilles ATRD 7 + ATRT 8 dans `tarifs_reglementaires.yaml`
- Parser flux F15 Enedis (6 cas codés CACNC)
- Composante CEE pass-through P5 (~5 €/MWh) formalisée
- Détecteur régularisation annuelle + avoirs (avec FK `original_invoice_id`)
- Composante capacité (`capacity_amount_eur` champ + détecteur)

### 9.4 Audit final post-P1 (méthode `feedback-audit-sprint-visuel-fonctionnel`)

- 5 curls : `/api/billing/audit/{id}` avec / sans JWT, `/audit-all` avec JWT, anomalies, download evidence
- Playwright golden path : `/bill-intel` → click "Créer actions" → toast FR → `/centre-action` → vérif action créée
- 0 console error / 0 network 4xx-5xx sur parcours
- Verdict GO/NO GO consigné dans `docs/audits/audit_postfix_bill_intelligence_p1_<date>.md`

### 9.5 Non-objectifs explicites (out of scope P1)

- ❌ HTB (RTE) — cohorte trop petite, P2
- ❌ CART-P (production) — hors B2B classique
- ❌ DPE tertiaire — attendre transposition EPBD
- ❌ ACC-TURPE — sprint dédié autoconsommation collective
- ❌ Blockchain / smart contracts traçabilité (Brique 4 future)
- ❌ Toute modification doctrinale du modèle Contrat V2 (Cadre + Annexe)

---

## 10. Notes méthodologiques

**Périmètre couvert** : 7 dossiers Drive + 17 PDFs CRE + 10 PDFs Enedis + 8 skills (~2000 lignes). Bon recouvrement des 6 lots de mots-clés A→F. 80+ hits Drive analysés.

**Documents au contenu utile mais titre trompeur** (à retenir pour explorations futures) :
- `202508_Comprendre votre facture.pdf` → spec officielle RTE facture HTB
- `Enedis_Flux F15_Relevé résiduel TURPE7...pdf` → 6 cas codés CACNC
- `Template intégration de factures Elec/GAZ.xlsx` → schéma DB canonique 80 champs
- `Enedis.SGE.AX.0355.Annexe ListeDeValeurs_v4.6.0.pdf` → toutes valeurs codées Enedis
- `240215_2024-40_ATRD7_Post_CSE.pdf` → 294 k chars, doc gaz le plus riche

**Gaps documentaires identifiés** (à acquérir hors Drive en P1) :
- Mécanisme capacité — RTE direct + CRE 2026-43
- Catalogue prestations Enedis €
- CSPE/Accise gaz 2026 — JO à parser pour grille TICGN
- CEE valeurs €/MWhc P5/P6 — pas de doc tarifaire dans Drive
- ATRT 8 brochure tarifaire détaillée (seul le post-CSE est présent)

**Mode READ-ONLY respecté** : aucune écriture, aucun déplacement, aucune suppression Drive ; aucune modification code backend / frontend. Ce document est une **donnée d'entrée** pour le sprint Bill Intelligence P1 qui suivra une validation explicite du user.

---

*Phase 0-bis clôturée le 2026-05-24 — branche d'analyse uniquement. Méthode : 3 agents Explore parallèles (PDFs locaux + skills installées + Drive deep search) + cross-references avec audit `audit_brique_bill_intelligence_deep_readonly_2026_05_23.md`. Sources hiérarchisées 🟦/🟩/🟨/🟪. Référence skills : `promeos-billing`, `bill-intelligence-fr`, `promeos-enedis`, `promeos-energy-market`, `energy-contracts-b2b`, `cee-p6`, `energy-autoconsommation`, `promeos-regulatory`.*
