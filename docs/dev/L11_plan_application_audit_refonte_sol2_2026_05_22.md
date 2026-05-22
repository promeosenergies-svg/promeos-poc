---
title: "Plan d'application audit → claude/refonte-sol2 — feuille de route 6 mois"
date: 2026-05-22
status: DRAFT
origin: "Mémoire Claude Code (~/.claude/projects/.../memory/project_plan_application_audit_refonte_sol2_2026_05_22.md)"
audience: "Direction PROMEOS, Yannick, agents dev (architect-helios, implementer, regulatory-expert)"
companion: L10_audit_manques_promeos_2026_05_22.md
---

> **Note de portage repo** : ce document provient de la mémoire Claude Code (session 22/05/2026). Il applique l'audit méta des 5 backlogs CLOSED (cf **L10_audit_manques_promeos_2026_05_22.md**) à la branche `claude/refonte-sol2`. Matrice 114 features × état réel code + plan séquencé V0→V3 sur 6 mois (~130-185 j/h) avec 25+ branches `claude/*` recommandées. Les liens internes vers d'autres documents mémoire ne sont pas accessibles depuis le repo — voir `~/.claude/projects/-Users-amine-projects-promeos-poc/memory/` sur le Mac d'origine.

---

---
name: plan-d-application-audit-manques-promeos-sur-claude-refonte-sol2-feuille-de-route-6-mois
description: "Application opérationnelle de l'audit méta des 5 backlogs CLOSED ([reference_audit_manques_promeos_2026_05_22.md](reference_audit_manques_promeos_2026_05_22.md)) à la branche **claude/refonte-sol2** (V4 base PROMEOS). Matrice 114 features × état réel code (✅ présent / 🟡 partiel / 🔴 manquant / ⭐ innovation). Plan séquencé V0→V3 sur 6 mois (~190-280 j/h) avec branches `claude/*` dédiées, PR draft pattern, DoD par sprint. Cible : combler les 5 patches urgents + 3 différenciants commerciaux + industrialisation + 4 innovations cardinales."
metadata: 
  node_type: memory
  type: project
  date: 2026-05-22
  originSessionId: ca630fd5-f0d8-4fa4-965c-c9c89d321aff
---

<!-- markdownlint-disable MD060 MD032 MD022 MD058 MD049 -->
# Plan d'application audit → refonte-sol2

**Source audit** : [reference_audit_manques_promeos_2026_05_22.md](reference_audit_manques_promeos_2026_05_22.md) (114 features, 5 backlogs CLOSED, 27 apports Drive, ~84 items KB).
**Branche cible** : `claude/refonte-sol2` (tip `ade3d0a0`, V4 base, gelée main).
**Méthode** : 1 sprint = 1 branche `claude/<thème>-<YYYY-MM-DD>` forkée refonte-sol2 + PR draft immédiate + DoD binaire avant merge.

## 1. Synthèse écarts code refonte-sol2 vs audit

### Maturité par pillar (cumul fichiers services backend)

| Pillar | Services backend | KB items | Pages FE Sol2 | Verdict |
|---|---|---|---|---|
| **Bill** | **28** (billing/) + 4 (bill_intelligence/) | 8 (facturation) | BillIntelPage, BillingPage | 🟢 **plus mature** |
| **Pilotage/Flex** | 15 (pilotage/) + 9 (flex/) + 3 (capacity/) | 7 (flex) + 11 (usages) | Cockpit×4, CockpitPilotage, CockpitStrategique | 🟢 mature |
| **RegOps** | 11 (compliance/) + 8 (bacs/) + 8 (tertiaire/) + 3 (operat/) + 1 (aper/) + 1 (cee/) + 2 (cbam/) + 5 (audit/) | 9 (reglementaire) | Compliance×2, Conformite, Aper | 🟢 mature |
| **Achat** | 11 (purchase/) + 7 (contract/) | (cross-facturation) | (cross-Cockpit) | 🟡 mature mais sans agent dédié |
| **EMS** | 9 (ems/) + 5 (consumption/) | (cross-usages) | Consommations×2 | 🟡 plomberie OK, analytics partiels |
| **ACC** | **0** (gap !) | 4 (acc) | (?) | 🔴 **gap cardinal** |

### Matrice 114 features × état refonte-sol2 (résumé)

| Statut | Nombre | % | Exemples |
|---|---|---|---|
| ✅ **Présent / quasi-complet** | ~38 | 33 % | bacs_engine, billing_canonical_service, operat_export_service, purchase_pricing, energy_signature_service, action_plan_engine |
| 🟡 **Partiel** (legacy à enrichir) | ~32 | 28 % | S6 signature (manque R² + outliers + IC), S10 plan d'action (engine existe, calibrage économies% manquant), M5 catalogue HP/HC (présent dans recommendation_engine, fourchettes économies absentes), C11 chaudière (axes partiels), parser contrat (présent mais pour contrats pas factures) |
| 🔴 **Manquant** (greenfield) | ~38 | 33 % | M1 base load, M6 brief PDF conformité, B5 parser facture, R1 auto-déclaration OPERAT, R26 Capacity Forecaster, P0 12 archétypes restants, R21 traçabilité NOR, R25 ARENH Post-2025 Manager |
| ⭐ **Innovation** (concept neuf) | ~6 | 5 % | A16 Marketplace Matching producteur↔consommateur, A17 CEO Mini-Fournisseur, A18 PMO Automation smart contracts, A19 IA Pricing Agents, A20 pivot EMS→marketplace, P15 orchestrateur flex IA temps réel + V2G |

## 2. 4 catégories d'écarts — actionnables

### 2.A 🔴 5 PATCHES RÉGLEMENTAIRES URGENTS (1-2 sem cumulé, effet 1/2/2026)

| ID | Patch | Fichier(s) impacté(s) | Branche dédiée |
|---|---|---|---|
| **R17** | JOE 6/9/2025 — GNL 0,238 énergie primaire + RNB Building + attestations OPERAT migrées | `backend/config/emission_factors.py` + `models.Building` + `operat_export_service.py` | `claude/reg-patch-joe-2025-06-09` |
| **R22** | Arrêté CEE P6 ECOR2532411A — taux contrôle 25/50/100 % 2026-2028 | `backend/regops/rules/cee_p6.py` + `cee_service.py` | `claude/reg-patch-cee-p6-2026` |
| **R23** | Arrêté accises 2026 CPPE2600972A — élec 25,19 / 20,92 €/MWh | `backend/config/tarifs_reglementaires.yaml` (section accises) | `claude/reg-patch-accises-2026-02-01` |
| **B18** | TRVE CRE 2026-06 — CTA 21,93 % → 15 % au 1/2/2026 | `tarifs_reglementaires.yaml` (CTA) + `billing_canonical_service.py` | `claude/bill-patch-cta-15pct-2026-02-01` |
| **R24** | Audit seuils APER (canon 500/100 m² vs code potentiel 10000/1500) | `backend/regops/rules/aper.py` | `claude/reg-audit-aper-thresholds` |

### 2.B 🎯 3 DIFFÉRENCIANTS COMMERCIAUX CARDINAUX (10-14 sem cumulé)

| ID | Feature | État refonte-sol2 | Effort | Pourquoi cardinal |
|---|---|---|---|---|
| **M6/R0** | Module export PDF "Brief Conformité Site" auto-généré | 🔴 absent | 3-4 sem | livrable client tangible · différenciant vs Alter Watt (statique) + Bamboo (pas conformité) |
| **B5** | Parser PDF facture multi-fournisseur (EDF / Engie / Total / alternatifs) | 🔴 absent (contract_pdf_parser ≠ facture) | 6-8 sem | entrée du wedge facture — sans parser PROMEOS reste théorique |
| **S10** | Plan d'action priorisé € + délai par levier | 🟡 partiel (action_plan_engine.py existe) | 2-3 sem | calibrage économies % chiffrées Yele/Bamboo manquant — passage descriptif → actionnable |

### 2.C 🛠 AMÉLIORATIONS LEGACY (services partiels à enrichir, ~10-15 sem)

| ID | Feature | Service existant | Gap à combler |
|---|---|---|---|
| **S6** | Signature énergétique exposée gaz + élec vs DJU | `energy_signature_service.py` | Régression + R² + outliers + IC + fenêtre 24 mois (Apport #3 EMS) |
| **M5** | Catalogue 7 leviers HP/HC | `recommendation_engine.py` | Fourchettes économies % verbatim (Apport #7 META cours GTB) |
| **C11** | Diagnostic chaudière 6 axes | partiel via reco engine | Catalogue axes + heuristiques chiffrées (-1°C=-7 %, chaleur fatale +5-15 %) |
| **M4** | Décomposition HP/HC/Pointe + comparaison M-1 vs M | `tariff_periods_service.py` | Comparaison M-1 vs M + alerte > 5 % + segments C1-C5 (Apport #12) |
| **S14** | Profils NAF + matching tarif | `naf_resolver.py` + `usage_service.py` | Matrice NAF × tarif optimal + 6 calendriers alternatifs (Endesa Optimización) |
| **R2** | Trajectoire DT pluriannuelle | `operat_trajectory.py` | Comparateur Crelat vs Cabs + courbes 2030/2040/2050 chiffrées |
| **A1** | Parser contrat fournisseur — détection clauses risque | `contract_pdf_parser.py` (existe) | Extension détection break clause / take-or-pay / indexation cachée |
| **B7** | Audit anomalies R01-R20 | `bill_intelligence/` (folder) | Vérifier implémentation effective vs spec agent + tests couverture |

### 2.D ⭐ 6 INNOVATIONS CARDINALES (Vision Yannick + CCdC Brique 4, ~30-50 sem)

| ID | Innovation | Source | Décision doctrine |
|---|---|---|---|
| **A20** | Pivot EMS → Marketplace de l'énergie | Idées Yannick (A1 Achat) | **⚠ ARBITRAGE CARDINAL** — refonte doctrine v1.3 ? |
| **A16** | Marketplace Matching producteur↔consommateur local | Vision Yannick | si A20 statué OK : socle V3 |
| **A17** | CEO Mini-Fournisseur — dashboard interne entreprise | Vision Yannick | différenciant patrimoine PV multi-sites |
| **P15** | Orchestrateur flex IA temps réel + clés ACC dynamiques | CCdC Brique 4 (Apport P1) | cardinal Pilotage V1 H1 2025 (selon CCdC) |
| **A19/P9** | IA Pricing Agents — tarification dynamique offre/demande | Vision Yannick phase 2 | extension Flex Advisory |
| **P13** | V2X (Vehicle to Grid / Building) — IRVE bidirectionnel ISO 15118-2 | Étude Endesa EnergyLab (Apport #5 EMS) | obligation 01/2026 — anticiper |

### 2.E 📦 ITEMS KB MANQUANTS (cumul ~50 priorisés sur ~84)

Groupes prioritaires :
- 11 archétypes restants HELIOS/MERIDIAN (Pilotage P0)
- 7 items LEGAL-* sources canoniques NOR
- 4 items E-FACTURE-* (calendrier, Factur-X, PA-Peppol, données obligatoires)
- 5 items TURPE-7-HTB-*
- 5 items BILL-PARSER-*
- 7 items ARENH/VNU/CAPN/MECAPA
- 4 fournisseurs flex/concurrents (Bamboo, Volterres, Wattwin, Advizeo)

## 3. Plan d'action séquencé sur refonte-sol2 — 6 mois

### Sprint **V0** — Patches urgents + Arbitrages doctrinaux (J+1 → J+15, ~10-15 j/h)

**Branches** : `claude/reg-patch-joe-2025-06-09` · `claude/reg-patch-cee-p6-2026` · `claude/reg-patch-accises-2026-02-01` · `claude/bill-patch-cta-15pct-2026-02-01` · `claude/reg-audit-aper-thresholds` · `claude/reg-traceability-nor`

**Livrables** :
1. ✅ 5 patches réglementaires appliqués + 7 items KB LEGAL-* créés
2. ✅ R21 traçabilité légale : `.claude/legal_sources.json` + commentaires NOR dans rules
3. ✅ 4 arbitrages cardinaux statués (P18 pricing, P17 numérotation, A20 EMS→marketplace, Q10 hub MOE)
4. ✅ Source-guards CI : rule sans NOR rejetée

**DoD V0** : 5/5 patches mergés sur refonte-sol2 · 4/4 arbitrages tranchés par user · 0 régression baseline tests (BE ≥ 843, FE ≥ 3 783) · doc `legal_sources.json` documentée.

**Risque mitigé** : non-conformité légale post 1/2/2026 (accises + CTA).

---

### Sprint **V1** — 3 différenciants commerciaux cardinaux (J+16 → J+60, ~30-40 j/h)

**Branches** : `claude/ems-base-load-m1` · `claude/regops-brief-pdf-m6` · `claude/bill-parser-facture-b5` · `claude/ems-plan-action-priorise-s10`

**Livrables** :

1. **M1 base load detection + quantification €** (3-5 j) :
   - `backend/services/ems/base_load_service.py` (P75-P100 monotone + quantif €/sem)
   - endpoint `/api/ems/site/{id}/base_load`
   - carte Cockpit Pilotage
   - KPI cardinal CFO

2. **M6/R0 export PDF Brief Conformité auto-généré** (3-4 sem) :
   - `backend/services/regops/brief_export_service.py`
   - template HTML + WeasyPrint
   - endpoint `/api/regops/site/{id}/brief.pdf`
   - 5-7 sections format Alter Watt + neutralité PROMEOS (0 CTA commercial)

3. **B5 parser facture multi-fournisseur** (6-8 sem) :
   - stack pdfplumber + regex + Claude Sonnet (4-shot prompt)
   - 17 golden tests anonymisés RGPD (corpus folder Drive `1RaexzcB_*`)
   - classifier pré-LLM (3 templates EDF + Engie + Total)
   - validation cross-check (somme HT + TVA réconciliation + PDL format)
   - `backend/services/billing/invoice_parser.py`

4. **S10 plan d'action priorisé €+délai par levier** (2-3 sem) :
   - extension `action_plan_engine.py` existante
   - calibrage économies % verbatim Apport #7 META cours GTB
   - calcul gain € + payback par levier + classement ROI
   - matériel commercial unique vs ENDESA descriptif

**DoD V1** : 4/4 features mergées sur refonte-sol2 · 3 démos prospects validées · 0 régression tests · brief PDF auto pour ≥3 sites HELIOS/MERIDIAN · parser facture passe les 17 golden tests · plan d'action priorisé déployé sur Site360.

**Gain commercial attendu** : passage de "PROMEOS théorique" à "PROMEOS opérationnel" sur le wedge facture+conformité.

---

### Sprint **V2** — Industrialisation + KB items + Forecaster (J+61 → J+120, ~50-70 j/h)

**Branches** : `claude/regops-operat-auto-r1` · `claude/regops-dt-trajectoire-r2` · `claude/regops-capacity-forecaster-r26` · `claude/ems-carpet-plot-s8` · `claude/ems-cusum-c14` · `claude/pilotage-archetypes-12-restants` · `claude/bill-cee-bat-th-116-c21` · `claude/ems-flex-intensity-s12` · `claude/ems-gtb-connectors-s13` · `claude/regops-bacs-audit-trame-c20`

**Livrables** :

1. **R1 Auto-déclaration OPERAT** (2-3 sem) — pré-remplissage 90 % depuis patrimoine + CSV export DEET conforme Annexe I + IIU + multi-occupation
2. **R2 Trajectoire DT** (1-2 sem) — Crelat vs Cabs comparateur + courbes 2030/2040/2050
3. **R26 Capacity Forecaster PP1/PP2** (2-3 sem) — cardinal P1 SENTINEL-REG 1/11/2026 · alerte RTE J-1 (9h30/19h)
4. **S8 Carpet plot 24h × 365j** (5-8 j) — visualisation cardinale spec ems-expert non implémentée
5. **C14 CUSUM ISO 50001** (5-8 j) — détection dérive long terme
6. **P0 12 archétypes HELIOS/MERIDIAN restants** (4 sem) — commerce, magasin, école, université, hôpital, EHPAD, hôtel, restauration_collective, datacenter, industrie_légère, logistique, copropriété
7. **C21/B12 Calcul CEE BAT-TH-116** (1-2 sem) — formule officielle ATEE/Gimelec/ADEME + coefficients zones H1/H2/H3 + table 24 montants unitaires
8. **S12 Flex Intensity KPIs** (5-8 j) — €/MW/an + Payback + Activation Rate calibré Yele 286 k€/MW + Bamboo 12-51 k€/MW
9. **S13 Connecteurs GTB Modbus/M-Bus/BACnet** (4-6 sem) — ordre M-Bus → Modbus → BACnet/IP → KNX → LonWorks
10. **C20 Trame audit BACS 3 phases** (1-2 sem) — modèle Alterwave Air France

**DoD V2** : 10/10 features mergées · 15 archétypes complets (3 existants + 12 nouveaux) · ~30 KB items créés cumul (LEGAL-* + ARCHETYPE-* + BAT-TH-116-* + TURPE-7-HTB-* + BILL-PARSER-*) · couverture tests +30 % · 5 démos clients pilotes.

---

### Sprint **V3** — Innovations cardinales (J+121 → J+180, ~40-60 j/h selon arbitrages)

**Pré-requis** : arbitrages V0 statués (A20 pivot EMS→marketplace en particulier).

**Branches** : `claude/pilotage-orchestrator-flex-ia-p15` · `claude/achat-arenh-post-2025-a0` · `claude/regops-cre-signal-tracker-r27` · `claude/achat-comparateur-offres-a7` · `claude/regops-bacs-auto-diag-c16-c17` · `claude/achat-marketplace-ppa-a10`

**Livrables** :

1. **P15 Orchestrateur flex IA temps réel + clés ACC dynamiques** (6-10 sem) — CCdC Brique 4 V1 H1 2025 · arbitrage profit-maximizing vs équité solidaire + heuristique vs PL
2. **A0/R25 ARENH Post-2025 Manager** (2-3 sem) — bascule VNU/CAPN clients 31/12/2025
3. **R27 CRE Signal Tracker** (2 sem) — webhook EPEX + RTE PP1/PP2 + écrêtement ARENH + agent SENTINEL-REG actif
4. **A7 Comparateur offres fournisseurs B2B** (3-4 sem) — agrégation EDF/Engie/Total/Alterna/Octopus + transparence prix
5. **C16/C17 Auto-diagnostic classe BACS + Matrice points GTB par levier** (3-4 sem) — différenciant fort vs ENDESA + Bamboo
6. **(si A20 statué) A10 Marketplace ENR PPA** (4-6 sem) — agrégateur PPA Corporate inspiré Volterres (partenariat possible avec 500 MW partenaires Sun'r/Eiffage)

**Innovations Phase 2 (réservées V4+)** :
- A16 Marketplace Matching producteur↔consommateur local (vision Yannick)
- A17 CEO Mini-Fournisseur dashboard interne
- A18 PMO Automatisée smart contracts ACC
- A19 IA Pricing Agents — tarification dynamique
- P12 BESS gestion + arbitrage spot/EcoWatt
- P13 V2X (Vehicle to Grid / Building) ISO 15118-2

**DoD V3** : 6/6 features mergées · arbitrage A20 doctrinal acté · partenariats Volterres + agrégateurs RTE initiés · battlecards 4 concurrents produits · démo investisseur seed pitch-ready.

---

## 4. KPI / DoD globaux du plan 6 mois

| KPI | Cible | Mesure |
|---|---|---|
| Patches réglementaires appliqués | 5/5 | conformité 1/2/2026 |
| Différenciants commerciaux livrés | 3/3 | M1 + M6 + B5 + S10 en production |
| Items KB créés | ≥ 50 cumulés | depuis ~39 actuels → ≥ 90 |
| Archétypes HELIOS/MERIDIAN | 15/15 | 3 actuels + 12 nouveaux |
| Source-guards CI ajoutés | ≥ 20 | NOR + lifecycle + parser facture |
| Baseline tests BE | ≥ 843 → ≥ 1500 | +75-80 % coverage |
| Baseline tests FE | ≥ 3 783 → ≥ 5 500 | +45 % |
| Branches `claude/*` créées | ≥ 25 | 1 par sprint feature |
| PRs draft mergées sur refonte-sol2 | ≥ 25 | atomic commits |
| Arbitrages doctrinaux statués | 12/12 | 4 cardinaux V0 + 8 V1-V3 |
| Démos prospects validées | ≥ 8 | 3 V1 + 5 V2 |

## 5. Risques + mitigations

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| **Patches non appliqués post 1/2/2026** | 🔴 haute si V0 retardé | non-conformité légale immédiate | V0 prioritaire absolu (1-2 sem max) |
| **A20 arbitrage doctrinal bloqué** | 🟡 moyenne | bloque V3 innovations | Statuer V0 — si bloqué, scinder V3 (sans A20) |
| **B5 parser facture sous-estimé** | 🟡 moyenne | retarde V1 | 17 golden tests anonymisés en parallèle dès J+1 |
| **Incohérence pricing P18 non résolu** | 🔴 haute | bloque GTM commercial | Décision user obligatoire V0 |
| **Drive corpus factures pas exploitable RGPD** | 🟡 moyenne | bloque B5 | anonymisation script automatique (regex names/IBAN/PDL kept) |
| **Concurrent Bamboo/Volterres pivote** | 🟡 moyenne | menace marché flex/PPA | Battlecards V3 + partenariat Volterres dès J+30 |
| **Tests baseline régression refonte-sol2** | 🟡 moyenne | bloque merge | Source-guards CI + pre-merge workflow |
| **Dette `acc` services = 0** | 🟡 moyenne | gap PMO ACC | Sprint dédié V2 si A18 priorisée |

## 6. Branches `claude/*` recommandées (récap cumul)

```
V0 (5 + 1) :
  claude/reg-patch-joe-2025-06-09
  claude/reg-patch-cee-p6-2026
  claude/reg-patch-accises-2026-02-01
  claude/bill-patch-cta-15pct-2026-02-01
  claude/reg-audit-aper-thresholds
  claude/reg-traceability-nor

V1 (4) :
  claude/ems-base-load-m1
  claude/regops-brief-pdf-m6
  claude/bill-parser-facture-b5
  claude/ems-plan-action-priorise-s10

V2 (10) :
  claude/regops-operat-auto-r1
  claude/regops-dt-trajectoire-r2
  claude/regops-capacity-forecaster-r26
  claude/ems-carpet-plot-s8
  claude/ems-cusum-c14
  claude/pilotage-archetypes-12-restants
  claude/bill-cee-bat-th-116-c21
  claude/ems-flex-intensity-s12
  claude/ems-gtb-connectors-s13
  claude/regops-bacs-audit-trame-c20

V3 (6) :
  claude/pilotage-orchestrator-flex-ia-p15
  claude/achat-arenh-post-2025-a0
  claude/regops-cre-signal-tracker-r27
  claude/achat-comparateur-offres-a7
  claude/regops-bacs-auto-diag-c16-c17
  claude/achat-marketplace-ppa-a10
```

Pattern : 1 sprint = 1 branche `claude/<thème>-<id>` forkée refonte-sol2 + PR draft immédiate base `claude/refonte-sol2` + DoD binaire avant merge + atomic commits (cf [feedback_commit_push_immediately.md](feedback_commit_push_immediately.md)).

## 7. Calendrier estimé (6 mois)

| Sprint | Démarrage estimé | Durée | Volume cumulé |
|---|---|---|---|
| **V0** | 23/05/2026 | 2 sem | ~10-15 j/h |
| **V1** | 06/06/2026 | 6 sem | ~30-40 j/h |
| **V2** | 18/07/2026 | 8 sem | ~50-70 j/h |
| **V3** | 12/09/2026 | 8 sem | ~40-60 j/h |
| **Total** | 23/05 → 07/11/2026 | **24 sem** | **~130-185 j/h** |

À noter : `feat/m2-5-frontend-v4` sprint frontend en cours (clos 18/05 selon memory) doit être mergé avant V1 pour ne pas bloquer.

## 8. Cross-références

- **Audit méta** : [reference_audit_manques_promeos_2026_05_22.md](reference_audit_manques_promeos_2026_05_22.md)
- **5 backlogs CLOSED** : EMS · RegOps · Bill · Achat · Pilotage/Flex+Usages
- **Doctrine cardinale v1.3** : [project_promeos_vision_consolidee_v1_3_2026_05_08.md](project_promeos_vision_consolidee_v1_3_2026_05_08.md)
- **Patrimoine matrice v1** : [reference_patrimoine_parametrage_matrice_v1_2026_05_03.md](reference_patrimoine_parametrage_matrice_v1_2026_05_03.md) (~310 champs Phase A.0 verrouillée)
- **PR ouvertes** : #284 kb-hygiene-p1 (status: validated 39 items) · #281 KB veille S20

## 9. Statut

- ✅ Plan rédigé 22/05/2026 fin journée 2
- ⏳ V0 à démarrer (5 patches + 4 arbitrages)
- ⏳ Décisions user à statuer **avant V1** : 4 arbitrages cardinaux (P18, P17, A20, Q10)
- 🔁 Itération attendue user (validation plan + ajustements priorités)
