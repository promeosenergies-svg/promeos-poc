---
title: "Audit des manques PROMEOS — synthèse session 22/05/2026"
date: 2026-05-22
status: DRAFT
origin: "Mémoire Claude Code (~/.claude/projects/.../memory/reference_audit_manques_promeos_2026_05_22.md)"
audience: "Direction PROMEOS, Yannick (co-fondateur), agents dev"
companion: L11_plan_application_audit_refonte_sol2_2026_05_22.md
---

> **Note de portage repo** : ce document provient de la mémoire Claude Code (session 22/05/2026). Les liens internes `[reference_X.md](reference_X.md)` et `[project_X.md](project_X.md)` pointent vers la mémoire privée locale Mac (non synchronisée Git). Pour la version complète avec liens fonctionnels, voir `~/.claude/projects/-Users-amine-projects-promeos-poc/memory/` sur le Mac d'origine. La synthèse opérationnelle se trouve dans le document compagnon **L11_plan_application_audit_refonte_sol2_2026_05_22.md**.

---

---
name: audit-des-manques-promeos-synth-se-session-22-05-2026-5-backlogs-closed
description: "Audit final des éléments, données, code, KB items, doctrine, sources légales, partenariats et arbitrages MANQUANTS pour développer et améliorer PROMEOS. Synthèse des 5 backlogs CLOSED de la session 22/05/2026 (EMS v1.4 · RegOps v1.4 · Bill v1.1 · Achat v1.1 · Pilotage/Flex+Usages v1.1) = **108 features cumulées, ~360-500 j/h estimé, 27 apports ingérés via Drive crawl complet**. Top 10 actions priorisées + 12 arbitrages doctrinaux à statuer."
metadata: 
  node_type: memory
  type: reference
  date: 2026-05-22
  originSessionId: ca630fd5-f0d8-4fa4-965c-c9c89d321aff
---

<!-- markdownlint-disable MD060 MD032 MD022 MD058 MD049 -->
# Audit des manques PROMEOS — synthèse session 22/05/2026

## 1. Synthèse cumulée 5 backlogs CLOSED

| Pillar | Backlog | Features | Volume | Apports | Items KB cumulés |
|---|---|---|---|---|---|
| **EMS** | v1.4 CLOSED | 30 (M0-M6, S6-S16, C11-C22) | ~60-91 j/h | 15 + 2 archives | ~15 |
| **RegOps** | v1.4 CLOSED | 27 (R0-R27) | ~95-135 j/h | 7 (#16-#22) | ~32 |
| **Bill** | v1.1 CLOSED | 19 (B0-B19) | ~75-105 j/h | 3 (B1-B3) | ~15 |
| **Achat** | v1.1 CLOSED | 20 (A0-A20) | ~70-100 j/h | 2 (A1-A2) | ~10 |
| **Pilotage/Flex+Usages** | v1.1 CLOSED | 18 (P0-P18) | ~60-100 j/h | 1 (P1) | ~12 |
| **TOTAL** | | **114 features** | **~360-530 j/h** | **27 apports** | **~84 items KB** |

État cardinal : la session a documenté **~1,5-2 ans de travail** sur 5 pillars. Toutes les features cross-pillar listées + 27 apports Drive ingérés + ~84 items KB inventoriés.

## 2. Manques cardinaux par catégorie

### 2.1 DATA & CORPUS manquants

| Manque | Backlog source | Volume estimé | Impact |
|---|---|---|---|
| **~25 PDFs factures samples** corpus parser (anonymisation RGPD requise) | Bill B3/B5 | 25 PDFs × 1h anonymisation = 25h | 🔴 bloque B5 parser |
| **17 golden tests parser facture** à constituer (EDF×4, Engie×2, Total×2, autres×5, anomalies×3, OCR×2) | Bill B3/B5 | 17 × 2h = 34h | 🔴 bloque B5 validation |
| **12 archétypes HELIOS/MERIDIAN restants** (3 documentés sur 15) | Pilotage P0 | 12 × 4h = 48h | 🔴 bloque pivot Usage cross-pillar |
| **Corpus contrats fourniture samples** (EDF Pro, Engie Pro, Total Pro, etc.) | Achat A1 parser | 10-20 contrats à collecter | 🟡 retarde A1 audit clauses |
| **Catalogue producteurs ENR partenaires** (Volterres a 500 MW, PROMEOS = 0) | Achat A10 PPA | partenariat Volterres à structurer | 🟡 bloque A10 marketplace |
| **Données portefeuille clients réels** (MVP perimeter_raw mentionne ~150 sites — accès à confirmer) | Achat A20 + Bill B5 | étape commerciale | 🔴 socle MVP réel |
| **DJU corpus 24 mois alignés CDC** (template EMS2 fournit 2 mois insuffisants) | EMS S6 Apport #3 | continuité historique météo + Enedis | 🔴 bloque S6 robuste |
| **Benchmarks OID/CEREN par archétype NAF** | Pilotage P11 | abonnement ou open data | 🟡 bloque benchmark portefeuille |
| **Forward EEX Cal-N + Spot EPEX historiques** | Achat A8 scenarios | open data ou abonnement EEX | 🟡 bloque A8 stratégies |

### 2.2 CODE — services à développer

| Service à créer | Pillar | Effort | Priorité |
|---|---|---|---|
| **Parser PDF facture multi-fournisseur** (pdfplumber + regex + Claude Sonnet + golden tests) | Bill B5 | 6-8 sem | 🔴 cardinal différenciant |
| **Module export PDF Brief Conformité** (livrable client auto-actualisé) | RegOps R0/EMS M6 | 3-4 sem | 🔴 cardinal différenciant |
| **Auto-déclaration OPERAT** (pré-remplissage 90 % depuis patrimoine) | RegOps R1 | 2-3 sem | 🔴 différenciant fort |
| **Trajectoire DT pluriannuelle** (Crelat/Cabs/modulation) | RegOps R2 | 1-2 sem | 🟡 |
| **Base load detection + quantif €** (KPI cardinal CFO) | EMS M1 | 3-5 j | 🔴 V1 EMS |
| **Carpet plot 24h × 365j** | EMS S8 / Pilotage P1 | 5-8 j | 🔴 spec ems-expert non implémentée |
| **CUSUM ISO 50001** | EMS C14 / Pilotage P5 | 5-8 j | 🟡 |
| **Flex Intensity KPIs** (€/MW/an + Payback + Activation Rate) | EMS S12 / Pilotage P2 | 5-8 j | 🔴 calibré Yele/Bamboo |
| **Connecteurs GTB** (Modbus/M-Bus/BACnet/KNX/LonWorks) | EMS S13 / Pilotage P3 | 4-6 sem | 🟡 ordre M-Bus→Modbus→BACnet→KNX→LonWorks |
| **Capacity Forecaster PP1/PP2** | RegOps R26 / Pilotage P6 | 2-3 sem | 🔴 P1 SENTINEL-REG 1/11/2026 |
| **Calcul TRI exemption BACS** | RegOps R6/EMS C19 | 1-2 sem | 🟡 différenciant audit |
| **Calcul CEE BAT-TH-116** (formule officielle ATEE/ADEME) | Bill B12/EMS C21 | 1-2 sem | 🟡 monétisation gisements |
| **Orchestrateur flex IA temps réel + clés ACC dynamiques** | Pilotage P15 | 6-10 sem | 🔴 CCdC Brique 4 cardinal |
| **Forecasting 7j/30j conso + flex** | Pilotage P10 | 3-4 sem | 🟡 |
| **Alertes anomalies temps réel <5min** (baseline+IQR) | Pilotage P16 | 2-3 sem | 🔴 |

### 2.3 CODE — patches urgents (réglementaires)

| Patch | Source | Effet | Priorité |
|---|---|---|---|
| **R17 patch JOE 6/9/2025** : GNL 0,238 + RNB Building + attestations OPERAT migrées | NOR ATDL2430864A | immédiate (transitoire 1/7/2026) | 🔴 URGENT |
| **R22 patch arrêté CEE P6 ECOR2532411A** : taux contrôle 25/50/100 % 2026-2028 | JOE 18/12/2025 | 1/1/2026 | 🔴 URGENT |
| **R23 patch arrêté accises CPPE2600972A** : élec ménages 25,19 / PME-HP 20,92 €/MWh | JOE 28/1/2026 | **effet 1/2/2026** | 🔴 URGENT |
| **B18 patch CTA 21,93 % → 15 %** | TRVE CRE 2026-06 | effet 1/2/2026 | 🔴 URGENT |
| **R24 audit seuils APER** : canon 500/100 m² vs code potentiel 10000/1500 | loi 2023-175 art. L.111-6 | conformité légale stricte | 🔴 URGENT |
| **R21 traçabilité code↔NOR** : `.claude/legal_sources.json` + commentaires NOR dans rules | différenciant audit | 1-2 sem | 🟡 |

### 2.4 KB items à créer (cumul ~84 items mais 30+ priorisés)

Groupes prioritaires :
- **11 archétypes restants HELIOS/MERIDIAN** (Pilotage P0) — commerce, magasin, école, université, hôpital, EHPAD, hôtel, restauration_collective, datacenter, industrie_légère, logistique
- **7 items LEGAL-* sources canoniques NOR** : LEGAL-DECRET-2019-771-DT · LEGAL-DECRET-2023-259-BACS · LEGAL-DECRET-2025-1343-BACS-REPORT · LEGAL-LOI-2023-175-APER · LEGAL-ARRETE-2025-CEE-P6 · LEGAL-ARRETE-2026-ACCISES · LEGAL-CRE-AGREMENT-FOURNISSEUR
- **4 items E-FACTURE-*** : CALENDRIER · FORMAT-FACTUR-X · PA-PEPPOL · DONNEES-OBLIGATOIRES
- **5 items TURPE-7-HTB-*** : PERIMETRE · COMPOSANTES · COEFFICIENTS · INJECTION-SURCHARGE · LEGAL-CRE-2025-77
- **5 items BILL-PARSER-*** : EDF-STRUCTURE V1/V2/V3 · ENGIE-STRUCTURE · TOTAL-STRUCTURE · CHAMPS-FIABILITE-MATRIX · GOLDEN-TESTS-V1
- **6 axes chaudière C11** (Apport #7 META cours GTB)
- **7 leviers HP/HC M5** (économies % chiffrées Apport #7)
- **5 items ARENH/VNU/CAPN/MECAPA** (post-ARENH cardinal)

### 2.5 Battlecards concurrents à produire

| Concurrent | Source apport | Position | Action |
|---|---|---|---|
| **Bamboo Energy** (Espagne SaaS, 400 MW EU) | EMS Apport #8 | concurrent direct Flex | ⚠ battlecard PROMEOS vs Bamboo |
| **Volterres** (marketplace PPA, 500 MW) | Achat Apport A2 | concurrent direct A10 PPA | battlecard + partenariat possible |
| **Wattwin** (SaaS engineering, 170k projets) | Achat Apport A2 | concurrent EMS engineer | battlecard threat assessment |
| **Advizeo** (SaaS GTB BACS) | RegOps Apport #17 | concurrent tactique BACS | battlecard exploiter 6 faiblesses |
| **ENDESA** (méthode Griffine + GNV) | EMS Apport #1+#11+#22 | partenaire/concurrent | différenciants neutralité PROMEOS |
| **Alter Watt** (fiches vulgarisation) | RegOps Apport #10 | modèle format livrable | différenciation auto-actualisé |
| **Endesa Efficience MOE/audit** | RegOps Apport #15 | hors doctrine v1.3 | arbitrage Q10 |

### 2.6 Sources légales — 3 écarts détectés code↔NOR (RegOps Apport #20)

1. **APER thresholds** : canon 500 m² parking / 100 m² toiture vs config code potentiellement 10000/1500 m²
2. **Décret Tertiaire deadlines** : confusion possible 2026-07-01 (attestation) vs 2031-12-31 (vérification finale)
3. **Traçabilité NOR absente** dans tout le code RegOps (`.claude/legal_sources.json` à créer)

### 2.7 Partenariats à structurer

| Acteur | Type | Action |
|---|---|---|
| **Volterres** (Sun'r / Eiffage) | Marketplace PPA producteurs ENR | Contact (V. Vivalda PPA, A. Bouanani DG) — partenariat plug PROMEOS↔marketplace |
| **Tilt Energy + Flexcity Veolia** | Agrégateurs RTE Tier 1 | Cf [reference_aggregateurs_rte_shortlist_partenariat_2026](reference_aggregateurs_rte_shortlist_partenariat_2026.md) — modèle 60-70/30-40/5-15 |
| **CLEEE** (Wesley Janssen) | Association 80 membres B2B 85 TWh | AO T&L fin 2026 pour 2029-2030 — qualification éligibilité PROMEOS clients |
| **Enedis DSO** | Gap monétisation flex locales 5-10 GW | Opportunité cardinale — segment blanc (Apport #6 Yele) |
| **ADEME** | Validation méthodologie audit + reconnaissance | Crédibilité institutionnelle |
| **Météo-France** | Source DJU canonique (vs rp5.ru actuel) | Q6 arbitrage RegOps |
| **Bamboo Energy** | Concurrent flex non existential | Synergie possible (API↔orchestration PROMEOS) — non urgent |

### 2.8 Outils techniques / stack

| Outil | Statut | Manque |
|---|---|---|
| **pymupdf** (extraction PDF) | absent env local | bloque pipeline `kb_ingest_pdf.py` — installer + verifier |
| **Météo-France API** vs rp5.ru | rp5.ru actuel non officiel | Q6 source DJU canonique |
| **Anthropic Claude Sonnet** | dispo agent + SDK | OK pour parser facture B5 (~0,03 $/100 PDFs) |
| **Stack BESS / V2G ISO 15118-2** | hors scope MVP | extension Pilotage P12-P13 |
| **Webhooks RTE EcoWatt/Tempo + EPEX** | non branché | R27/P7 — automatisation veille |
| **pdfplumber/PyPDF2** | à installer | B5 parser facture |
| **ParameterStore marché** (EEX/EPEX forward+spot) | partiel via `tarifs_reglementaires.yaml` | A8 scenarios + B5 calibrage |

### 2.9 Incohérences internes PROMEOS détectées (à clarifier)

| Conflit | Détails | Décision attendue |
|---|---|---|
| **Pricing model** | MVP RegOps Apport #19 = ratio **2 % du budget énergie** vs Vision MVP v0 Pilotage P1 = **packs P1=1200 / P2=2000 / P3=4000 €/client + 2 % success fee CAPEX** | P18 arbitrage doctrinal cardinal |
| **Numérotation pillars** | Doctrine v1.3 = 6 pillars (EMS/RegOps/Bill/Achat/Flex/CX) vs CCdC interne = 6 briques (1=Data/Conformité, 2=ACC Starter, 3=ACC Ops, 4=Flex, 5=Achat, 6=CX) | P17 arbitrage doctrinal cardinal |
| **Position EMS** | Doctrine v1.3 = "tour de contrôle" passive vs vision Yannick = orchestration marketplace décentralisée | A20 arbitrage doctrinal cardinal |
| **Statut juridique** | "pas courtier, pas fournisseur" vs sourcing CLEEE / marketplace PPA = nécessite ORIAS ou SCE ? | A6 + A10 arbitrages |

### 2.10 RH / Expertise externe nécessaire

- **Juriste énergie B2B** : valider 5 points "À VALIDER PAR JURISTE" du cadre revenue-share (cf `reference_legal_revenue_share_b2b_2026`)
- **Expert TURPE 7 HTB** : décision B19 couverture segments industriels (5000-8000 sites)
- **Data scientist forecasting** : P10 modèle 7j/30j (Prophet vs Claude vs autres)
- **Designer UX Cockpit** : MVP packs P1/P2/P3 nécessitent interfaces par persona

## 3. Top 10 actions priorisées (3 mois)

| # | Action | Pillar | Effort | Différenciant |
|---|---|---|---|---|
| **1** | 🔴 Patches réglementaires URGENTS (R17 GNL + R23 accises + B18 CTA 15 % + R22 CEE P6 + R24 APER) | RegOps + Bill | 1 sem cumulé | conformité légale stricte effet 1/2/2026 |
| **2** | Statuer 4 arbitrages doctrinaux cardinaux (P18 pricing, P17 numérotation, A20 EMS→marketplace, Q10 hub MOE) | Doctrine | 1-2 j décision user | aligne doctrine v1.3 avec réalité |
| **3** | M1 base load detection + quantif € + M6 brief PDF conformité auto-généré | EMS + RegOps | 3-4 sem | **2 différenciants commerciaux cardinaux** |
| **4** | B5 parser facture multi-fournisseur (stack pdfplumber + regex + Claude Sonnet + 17 golden tests) | Bill | 6-8 sem | **différenciant majeur wedge facture** |
| **5** | Constituer 12 archétypes HELIOS/MERIDIAN restants + 4 étude B2B (Pilotage P0) | Pilotage Usages | 48h ingénieur + benchmarks | pivot Usage cross-pillar opérationnel |
| **6** | R26/P6 Capacity Forecaster PP1/PP2 (cardinal P1 SENTINEL-REG 1/11/2026) | RegOps + Flex | 2-3 sem | obligation légale + valorisation effacement |
| **7** | R1 Auto-déclaration OPERAT + R2 Trajectoire DT pluriannuelle | RegOps | 4-5 sem | différenciant fort vs Alter Watt/Advizeo |
| **8** | A0/R25 ARENH Post-2025 Manager (bascule VNU/CAPN clients) | Achat + RegOps | 2-3 sem | conseil cardinal 31/12/2025 |
| **9** | R21 traçabilité code↔NOR (`.claude/legal_sources.json` + commentaires) + 5 patches NOR cités | RegOps | 1-2 sem | différenciant audit légal continu |
| **10** | P15 Orchestrateur flex IA temps réel V1 (mono-site, heuristiques) | Pilotage | 6-10 sem | CCdC Brique 4 V1 H1 2025 |

## 4. 12 arbitrages doctrinaux à statuer (récap)

| ID | Sujet | Backlog | Impact |
|---|---|---|---|
| **A20** | EMS → orchestration Marketplace (vision Yannick) | Achat | 🔴 cardinal doctrinal |
| **P17** | Numérotation 6 briques interne vs 6 pillars v1.3 | Pilotage | 🔴 cardinal doctrinal |
| **P18** | Pricing packs P1/P2/P3 vs ratio 2 % budget | Pilotage | 🔴 cardinal commercial |
| **Q10** | Hub MOE/audit/ESCO socle ou hors doctrine | RegOps | 🟡 |
| **Q4** | EnergyContract étendre 5 plages × été/hiver | EMS | 🟡 data model |
| **Q6** | Source DJU canonique (Météo-France / ADEME / rp5.ru) | RegOps | 🟡 |
| **Q7** | Multi-stacking flex MECAPA+aFRR+mFRR+spot | EMS | 🟡 |
| **Q11** | Calendrier HP/HC CLEEE option ou défaut post 1/04/2028 | EMS | 🟡 |
| **B6** | Workflow reclaim : PROMEOS génère ou propose template ? | Bill | 🟡 |
| **B14** | CBAM socle ou extension Industrie Y3+ | Bill | 🟡 |
| **A6** | Sourcing collectif CLEEE : orchestration ou apporteur d'affaires (ORIAS) ? | Achat | 🟡 juridique |
| **A10** | Marketplace PPA : facilitation neutre vs courtage ? | Achat | 🟡 juridique |

## 5. Recommandations roadmap 3 mois

### Sprint 1 (J+1 → J+15) — Patches légaux + arbitrages
- Patches urgents R17/R22/R23/B18/R24 (effets 1/2/2026)
- Statuer 4 arbitrages cardinaux (P17/P18/A20/Q10)
- R21 traçabilité légale code↔NOR
- Promouvoir 7 items LEGAL-* dans KB

### Sprint 2 (J+16 → J+45) — V1 EMS + RegOps cardinal
- M1 base load + M6 brief PDF + R1 auto-déclaration OPERAT
- R2 Trajectoire DT + R26/P6 Capacity Forecaster
- Constituer 12 archétypes HELIOS/MERIDIAN

### Sprint 3 (J+46 → J+90) — Parser facture + Flex orchestrateur
- B5 parser facture (stack complète + 17 golden tests)
- P15 orchestrateur flex IA V1 mono-site
- A0/R25 ARENH Post-2025 Manager
- Battlecards Volterres + Bamboo + Advizeo

## 6. Notes cardinales

1. **Pas de greenfield** : les 4 pillars couverts (EMS/RegOps/Bill/Achat/Flex) sont déjà MATURES côté code (>80 services backend cumulés). Le travail = enrichissement + différenciation + patches, **pas réécriture**.
2. **3 différenciants commerciaux cardinaux** identifiés : (a) M6 brief PDF conformité auto · (b) B5 parser facture multi-fournisseur · (c) S10/R0 plan d'action priorisé €+délai. Ces 3 features positionnent PROMEOS au-dessus de tous les concurrents identifiés (Bamboo, Volterres, Wattwin, Advizeo, ENDESA, Alter Watt).
3. **Wedge cardinal v1.3 confirmé** : facture + conformité + consommation. Les apports Drive valident la doctrine — pas d'évolution majeure requise sauf si A20/P17/P18 statués.
4. **Risque réglementaire principal** : 5 patches urgents non appliqués → non-conformité légale immédiate post 1/2/2026 (accises + CTA + GNL + APER + CEE).
5. **Risque commercial principal** : MVP pricing en suspens (P18) → pas de proposition commerciale chiffrée stable possible jusqu'à arbitrage.

## 7. Cross-références (5 backlogs CLOSED)

- [🔒 EMS v1.4 CLOSED](project_ems_pillar_backlog_2026_05_22.md)
- [🔒 RegOps v1.4 CLOSED](project_regops_pillar_backlog_2026_05_22.md)
- [🔒 Bill v1.1 CLOSED](project_bill_pillar_backlog_2026_05_22.md)
- [🔒 Achat v1.1 CLOSED](project_achat_pillar_backlog_2026_05_22.md)
- [🔒 Pilotage/Flex+Usages v1.1 CLOSED](project_pilotage_flex_usages_backlog_2026_05_22.md)
- [Doctrine cardinale v1.3](project_promeos_vision_consolidee_v1_3_2026_05_08.md)
- [Méthodologie ENDESA (reverse-engineer)](reference_methodologie_endesa_analyse_site_industriel.md)
