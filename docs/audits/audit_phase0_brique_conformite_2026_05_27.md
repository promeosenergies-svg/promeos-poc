# Audit Phase 0 — Brique Conformité conditionnelle multi-énergie (2026-05-27)

**Branche** : `claude/conformite-audit-readonly-phase0`
**Base** : `claude/refonte-sol2` après merge chaîne #321→#322→#323 (clôture brique Énergie)
**Mode** : **READ-ONLY strict** (uniquement ce document — 0 modification de code applicatif)
**Mandat user** : audit read-only, pas de code immédiat, pas de complexification UX, priorité **simplicité métier + preuves + actions**.

---

## Verdict global

🟢 **Brique Conformité majeure déjà en production — pas de chantier urgent, mais 4 axes d'amélioration ciblés.**

La brique est **plus mature qu'attendu** : ~25 audits cumulés sur mai 2026, 1 hub unique conforme doctrine §6.2, 70+ endpoints API, 6 pages FE lazy-loaded, 6 onglets ConformitePage, scoring V2 multi-cadres (DT 45 % + BACS 30 % + APER 25 %), 9 source-guards backend, 9 KB items YAML canoniques. Les 5 divergences P0 OPERAT identifiées le 2026-05-27 sont **3 résolues + 2 à clarifier** (séparation OPERAT vs ADEME/RE2020 incomplète).

**Pas de sprint « big bang »**. À faire : 4 sprints incrémentaux ciblés, priorisés par valeur client (simplicité + preuves + actions), avec validation Légifrance avant tout commit code.

---

## 1 — État des lieux (Phase 0 read-only)

### 1.1 Sources doctrinales mobilisées

| Source | Contenu mobilisé |
|---|---|
| Skill `regops_constants` ([`.claude/skills/regops_constants/SKILL.md`](.claude/skills/regops_constants/SKILL.md)) | Seuils canoniques BACS/APER/Audit SMÉ/CSRD, jalons DT -40/-50/-60 %, scoring V2, sanctions. Mis à jour 2026-04-24. |
| Skill `regulatory_calendar` | Deadlines 2026-2050 (OPERAT, Audit SMÉ 11/10/2026, ISO 50001 11/10/2027, Capacité 11/2026, CBAM). |
| Mémoire [[promeos-brique-conformite]] | Phase 0-bis Drive 23/05/2026 (46 docs analysés). 5 divergences P0 OPERAT identifiées 2026-05-27 + Annexe II Cabs récupérée (217 p.). |
| Mémoire [[promeos-bacs-seuils-canonical]] | Décret n°2025-1343 (26/12/2025) : 70 kW reporté 2027 → **2030**. 8 fichiers corrigés 2026-05-25. |
| Doctrine PROMEOS « zéro issue » | Pas de fallback silencieux, source/formule/unité/période/confiance par chiffre, FR exclusif, idempotence actions. |

### 1.2 Backend — RegOps : architecture mature

**Structure `backend/regops/`** :
- [engine.py](backend/regops/engine.py) (409 l) — **SoT scoring + cascade findings** (remplace `scoring.py` deprecated)
- `rules/` — 1 fichier par cadre : `tertiaire_operat.py`, `bacs.py`, `aper.py`, `dpe_tertiaire.py`, `cee_p6.py`
- `services/` — `cascade_recompute_service.py`, `operat_cabs_service.py`
- `config/regs.yaml` — pondérations + 15 catégories DEET Cabs (confirmées présentes)
- `priority_scoring.py`, `completeness.py`, `data_quality.py`, `versioning.py`, `schemas.py`, `operat_zones.py`

**Services Conformité** :
- [compliance_score_service.py](backend/services/compliance_score_service.py) — SoT scoring affiché (`compute_site_compliance_score`, `sync_site_unified_score`, `get_framework_label_fr`, `compute_portfolio_compliance`, `_v2_score_*` par cadre).
- [operat_trajectory.py](backend/services/operat_trajectory.py) — Trajectoires DT 2030/2040/2050. Bornes 2000-2060.
- [tertiaire_modulation_service.py](backend/services/tertiaire_modulation_service.py) — Calcul TRI modulation.
- [bacs_engine.py](backend/services/bacs_engine.py), `bacs_regulatory_engine.py`, `bacs_alerts.py`, `bacs_compliance_gate.py`, `bacs_ops_monitor.py` — 5 services BACS dédiés.
- [energy_intensity_service.py](backend/services/energy_intensity_service.py) — Coefficients EP (1.9 ELEC, 1.0 GAS).
- [compliance_engine.py](backend/services/compliance_engine.py) — Legacy `100 - risk_score` (backward compat, non affiché).
- `compliance_coordinator.py` — Orchestration cascade.

**Endpoints API (70+, regroupés)** :

| Prefix | Endpoints | Rôle |
|---|---|---|
| `/api/compliance/` | meta, summary, sites, bundle, recompute-rules, sites/{id}/summary, sites/{id}/score, portfolio/score, findings (list+patch), batches, sites/{id}/cee/dossier, mv/summary | Hub conformité + findings + CEE/M&V |
| `/api/regops/` | site/{id}, recompute, score_explain, data_quality/*, organisations/{orgId}/audit-sme, audit-deadline-status, bacs/site/{id}, bacs/asset, bacs/exemption | Évaluation per-site + Audit SMÉ + BACS expert |
| `/api/tertiaire/` | dashboard, efa/*, export-pack, issues, proofs/catalog | OPERAT/DEET workflows |
| `/api/operat/` | export, export/preview, export-manifests | Export OPERAT CSV |
| `/api/watchers/` | list, {name}/run, events | Veille réglementaire |

**Modèles data** : `ComplianceFinding`, `ComplianceScoreHistory`, `ComplianceRunBatch`, `RegAssessment`, `BacsAsset`, `BacsAssessment`, `BacsInspection`, `AuditEnergetique`, `OperatExportManifest`.

### 1.3 Frontend — Hub unique conforme doctrine §6.2

- **Sidebar Conformité** : 1 seul item parent `/conformite` (ShieldCheck, « DT, BACS, APER, Audit SMÉ — score & obligations »).
- **HIDDEN_PAGES** : `/conformite/tertiaire`, `/conformite/aper` (deep-link ⌘K, pas dans sidebar publique).
- **ROUTE_MODULE_MAP** : 13 routes mappées vers module `conformite`.
- **Pages** (toutes lazy-loaded) :
  - `ConformitePage.jsx` — hub principal V101, 4 tabs (Obligations, Données & Qualité, Exécution, Preuves) + scope filtering.
  - `SiteCompliancePage.jsx` — fiche conformité site.
  - `CompliancePipelinePage.jsx` — pipeline RegOps (hidden, audience expert).
  - `pages/tertiaire/` — `TertiaireDashboardPage`, `TertiaireWizardPage`, `TertiaireEfaDetailPage`, `TertiaireAnomaliesPage`.
  - `AperPage.jsx` — Loi APER, éligibilité + timeline.
- **Composants** :
  - `components/conformite/` (10) : `AuditSmeCard`, `ComplianceScoreHeader`, `ComplianceSummaryBanner`, `ConformiteSyntheseCompacte` (P2-A simplification 2026-05-25), `DtProgressMultiSite`, `FindingAuditDrawer`, `ModulationDrawer`, `MutualisationSection`.
  - `components/compliance/RegulatoryTimeline.jsx` — frise deadlines.
  - `pages/conformite-tabs/` — `ObligationsTab`, `DonneesTab`, `ExecutionTab`, `PreuvesTab`, `GuidedModeBandeau`, `NextBestActionCard`.
- **Service FE** : `services/api/conformite.js` — 70+ endpoints catégorisés (RegOps, Audit SMÉ, Compliance, Findings, Portfolio, CEE/M&V, Tertiaire, OPERAT export, BACS expert, Watchers, Regulatory).

### 1.4 KB Regulatory — état canonique vs drafts

**Items canoniques** (`docs/kb/items/reglementaire/`, **9 YAML**) :
| Item | Cadre | Statut |
|---|---|---|
| `DT-METHODE-CALCUL.yaml` | DT Crelat/Cabs/EFA | Canonique |
| `DT-SCOPE-1000M2.yaml` | DT scope | Canonique |
| `BACS-290KW.yaml` | BACS Tier 1 (2025) | Canonique |
| `BACS-70KW-DEADLINE-2030.yaml` | BACS Tier 2 (2030) | Canonique ✅ corrigé décret 2025-1343 |
| `BACS-OBJECTIF-100K-2030.yaml` | BACS policy | Info |
| `APER-SOLARISATION-PARKINGS.yaml` | APER (Loi 2023-175) | Canonique |
| `CSRD-VOLET-ENERGIE.yaml` | CSRD ESRS E1 | Canonique |
| `DPE-TERTIAIRE.yaml` | DPE (décret 2024-1040) | Canonique |
| `CAPACITE-MECANISME-RTE-2026.yaml` | Capacité (futur) | Draft |

**Drafts auto-ingérés Drive** (`docs/kb/drafts/`, ~5850 lignes YAML) :
| Dossier | Fichiers | Lignes |
|---|---|---|
| `BACS_COMPLET` | 69 | 2 625 |
| `DT_OPERAT_2026` | 27 | 1 011 |
| `FLEX_EFFACEMENT` | 47 | 1 504 |
| `ACC_FRANCE` | 61 | ~2 000 |
| `BACS_SEUILS`, `LOI_APER`, `ARRETE_ACC_2025`, `DT_SYNTHESE`, `LEVIERS`, `MARCHE`, `POST_ARENH`, `STOCKAGE`, `VEILLE` | … | … |

**Status** : items = SoT pour API. Drafts = en attente de validation/canonisation. Goulot principal : **BACS_COMPLET (2 625 l)** et **DT_OPERAT_2026 (1 011 l)** à ingérer en `backend/regops/rules/*.py` ou `backend/regops/config/`.

### 1.5 ADR & doctrine produit

| ADR | Sujet | État |
|---|---|---|
| ADR-020 | Scoring OPERAT migration `s_ce_m2` | Accepted |
| ADR-D-04 | BACS puissance CVC cascade | Accepted |
| ADR-024 | Moteur d'assujettissement | Accepted |

Méthodologie scoring : [`docs/methodologie/conformite-regops.md`](docs/methodologie/conformite-regops.md) (2026-04-26). Doctrine source : `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.3.

### 1.6 Tests existants

**Source-guards backend (9 fichiers conformité)** :
- `test_conformite_source_guards.py` — pondérations DT/BACS/APER (0.45/0.30/0.25)
- `test_operat_aper_enums_no_string_literal_source_guards.py`
- `test_operat_cabs_no_hardcoded_values_source_guards.py`
- `test_compliance_score_v2_adaptive_source_guards.py`
- `test_applicability_engine_source_guards.py`
- `test_cascade_recompute_no_direct_field_modification_source_guards.py`
- `test_regulatory_sources_yaml_consistency_with_constants_source_guards.py`
- `test_regulatory_sources_yaml_structure_source_guards.py`
- `test_phase81_lot_regops_source_guards.py`

**Frontend** : `NavRegistry.test.js` (hub unique 1 item), `ConformitePage.test.js`, `components/conformite/__tests__/`.

### 1.7 Audits déjà produits (~25 fichiers couvrant conformité)

Audits majeurs récents :
- `audit_brique_conformite_deep_readonly_2026_05_23.md` — **verdict GO P0** (DT+BACS+APER+SMÉ).
- `audit_postfix_hotfix_conformite_framework_labels_2026_05_24.md` — fix labels framework.
- `audit_postfix_cleanup_sidebar_conformite_2026_05_24.md` — IS11 + filtre org sidebar.
- `audit_postfix_conformite_p2a_visual_functional_simplification_2026_05_25.md` — UX simplification P2a (ConformiteSyntheseCompacte).
- `AUDIT_OPERAT_L2_ZONES_CLIMATIQUES_2026_05_03.md` — zones climatiques.
- `AUDIT_OPERAT_VA_EXTRACTION_LIVRABLE_FINAL_2026_05_03.md` — extraction VA.

**Phase 0-bis Drive** : livrée 23/05 dans `/Users/amine/projects/promeos-audit-main/docs/base_documentaire/PHASE_0BIS_EXPLORATION_DRIVE.md` (700 l, 46 docs analysés, 136 découvertes actionnables). **Non rapatriée dans `promeos-poc`** — à rapatrier pour prochain sprint.

---

## 2 — Cross-check 5 divergences P0 OPERAT (mémoire 2026-05-27)

| # | Divergence mémoire | Vérification code 2026-05-27 | Statut |
|---|---|---|---|
| D1 | CO2 élec **OPERAT 0,064** ≠ ADEME 0,052 codé dans `emission_factors.py:25` | [`backend/config/emission_factors.py:33`](backend/config/emission_factors.py#L33) — seule constante `kgco2e_per_kwh: 0.052` (ADEME V23.6). **PAS** de constante `EMISSION_FACTORS_OPERAT` séparée. | ⚠️ **À clarifier** |
| D2 | EP élec **OPERAT 2,3** ≠ RE2020 1,9 codé dans `energy_intensity_service.py:30` | [`backend/services/energy_intensity_service.py:30`](backend/services/energy_intensity_service.py#L30) — seule constante `EP_COEFFICIENTS = {ELECTRICITY: 1.9}` (RE2020). **PAS** de constante `EP_OPERAT` séparée. | ⚠️ **À clarifier** |
| D3 | 15 catégories DEET sans valeurs Cabs dans `regs.yaml:24-39` | [`backend/regops/config/regs.yaml`](backend/regops/config/regs.yaml) — 15 catégories présentes avec valeurs CVC/USE par zone (Explore agent confirme). Annexe II Cabs ingérée partiellement via `backend/config/operat_annexe_ii_coeff_dju.json`. | ✅ **Résolue (partielle)** |
| D4 | Plage année référence 2000-2060 dans `operat_trajectory.py:86-87` au lieu de 2010-2022 + butoir 30/09/2027 | [`backend/services/operat_trajectory.py:86-87`](backend/services/operat_trajectory.py#L86-L87) — bornes 2000-2060 toujours en place. **Pas de butoir 30/09/2027** explicite. Pas de fallback « 1ère année pleine OPERAT » audit confirmable sans relecture complète du service. | ⚠️ **Probablement non résolue** |
| D5 | TRI agrégé global dans `tertiaire_modulation_service.py:127-131` au lieu de par typologie 30/15/10 | Explore agent confirme **TRI agrégé global** toujours en place (1 TRI moyen pour tout le portefeuille). | ❌ **Non résolue** |

### Précisions sur la divergence D1/D2 (OPERAT vs ADEME/RE2020)

La mémoire 2026-05-27 recommandait explicitement de **créer des constantes séparées** `EMISSION_FACTORS_OPERAT` et `EP_OPERAT`. Ces constantes **n'existent pas** dans le code actuel. Conséquence : tout calcul de scoring OPERAT/DEET qui utilise les constantes `EMISSION_FACTORS["ELEC"]` (0,052) ou `EP_COEFFICIENTS[ELECTRICITY]` (1,9) **risque de différer du calcul réglementaire OPERAT** (qui exige respectivement 0,064 et 2,3).

**À faire avant tout fix** : (1) recroiser Légifrance/OPERAT pour confirmer les vraies valeurs réglementaires 0,064 et 2,3 (NOR ATDL2430864A consolidé 01/08/2025), (2) identifier les chemins de code qui consomment ces constantes pour scoring OPERAT vs CSRD/Bilan GES. Ce n'est pas trivial : 0,052 ADEME reste correct pour CSRD/Bilan GES, mais **mauvais pour calcul OPERAT** si OPERAT mandate 0,064.

### Précisions sur D4 et D5

- D4 : la plage 2000-2060 est trop large par rapport au texte canonique DEET qui borne l'année référence à 2010-2022. **Risque** : un utilisateur peut saisir année 2005 comme référence → l'API accepte mais la donnée n'est pas conforme OPERAT.
- D5 : le calcul TRI agrégé global donne un seul TRI pour tout le portefeuille. Le texte DEET prévoit une logique par typologie (30 ans pour travaux structuraux, 15 ans CVC, 10 ans GTB). Sans cette segmentation, le test de disproportion économique est faussé.

---

## 3 — Gaps identifiés (priorisés par valeur client)

### 3.1 P0 — Conformité réglementaire OPERAT/DEET (corriger avant 1ᵉʳ juillet 2026)

**Origine** : mémoire 2026-05-27 + cross-check ci-dessus.

| # | Gap | Sprint estimé | Risque produit |
|---|---|---|---|
| P0-1 | D5 TRI par typologie (30/15/10) au lieu de agrégé global | 2 j BE + tests | Test disproportion économique faussé → modulation OPERAT mal calibrée. |
| P0-2 | D4 plage année référence 2010-2022 + butoir 30/09/2027 + fallback « 1ère année pleine OPERAT » | 1,5 j BE + tests | Saisie utilisateur hors plage acceptée silencieusement → donnée non conforme. |
| P0-3 | D1+D2 séparation constantes OPERAT (0,064 CO2 + 2,3 EP) vs ADEME/RE2020 si l'écart est confirmé Légifrance | 1 j BE + 0,5 j cross-check Légifrance | Calcul scoring DT/OPERAT divergeant du calcul réglementaire. |
| P0-4 | Rapatrier `PHASE_0BIS_EXPLORATION_DRIVE.md` depuis `promeos-audit-main` dans `promeos-poc/docs/base_documentaire/` | 0,5 j | Doc de référence absente du repo → contexte perdu pour futurs sprints. |

**Sprint P0 total** : ~5 j/h. Pré-requis : Légifrance check pour D1/D2/D4.

### 3.2 P1 — Simplicité métier (priorité user : « simplicité métier »)

**Origine** : audit ConformitePage 4 tabs + 6 sous-composants + NextBestAction. Mature, mais lourd pour PME.

| # | Gap | Sprint estimé | Valeur client |
|---|---|---|---|
| P1-1 | Audit UX **ConformitePage** : mesurer cognitive load des 4 tabs + 6 sous-composants. Identifier ce qui peut basculer en mode expert (`expertOnly` ou drawer). Objectif : 3 tabs visibles par défaut (Obligations / Données / Preuves), Exécution en drawer NextBestAction. | 2 j (audit + propal réorg) | Réduit le bruit pour PME 1-10 sites (pack Control Lite 6,9 k€). |
| P1-2 | **« Prochaine action prioritaire » mode 1-clic** : NextBestActionCard déjà existant mais à vérifier qu'il propose 1 seule action top-priority par site, créable en 1 clic dans Centre d'Action V4 (idempotente via `external_ref`). | 1 j BE (audit du flow) + 1 j FE | Aligne sur le pattern Pilotage des usages (#318-#322) — boucle conformité → action. |
| P1-3 | **Banner unifié 3 états** (vert/orange/rouge) sur fiche site : `ComplianceSummaryBanner` existe déjà, mais audit visuel à faire pour cohérence avec `ConformiteSyntheseCompacte` (P2-A 25/05). | 0,5 j audit | Évite la double info contradictoire entre composants. |

**Sprint P1 total** : ~4,5 j/h.

### 3.3 P2 — Preuves & actions (priorité user : « preuves + actions »)

**Origine** : `PreuvesTab.jsx` existe, `getTertiaireEfaProofs`, `linkTertiaireProof`, `createOperatProofTemplates` exposés en API. À auditer pour complétude.

| # | Gap | Sprint estimé | Valeur client |
|---|---|---|---|
| P2-1 | Audit complétude **PreuvesTab** : par site, lister les preuves attendues (OPERAT déclaration, attestation BACS, devis ombrière APER, rapport audit énergétique) + statut « manquante / brouillon / validée / déposée ». Idempotence sur upload. | 2 j BE + 2 j FE | Cœur de la promesse « prouver » Vision Consolidée v1.3 (5e verbe cardinal). |
| P2-2 | **Connecteur OPERAT export** : `exportOperatCsv` existe + `OperatExportManifest`. Vérifier que le manifest contient `source/formula_ref/period/confidence` par ligne exportée (truth contract granulaire). | 1 j BE | Pré-requis dépôt OPERAT 2026 sans faute. |
| P2-3 | **Idempotence actions conformité** : auditer `recompute-rules`, `createBacsAsset`, `createCeeDossier` pour s'assurer qu'une re-exécution ne dédoublonne pas. Pattern existant : `external_ref UNIQUE PARTIAL` (V4 #320 brûle d'idempotence Pilotage). | 1 j BE | Évite « action créée 2 fois » silencieuse. |

**Sprint P2 total** : ~6 j/h.

### 3.4 P3 — Hygiène + ingestion drafts

| # | Gap | Sprint estimé | Valeur |
|---|---|---|---|
| P3-1 | Ingestion **DT_OPERAT_2026** (1 011 l drafts) dans `backend/regops/config/` ou `rules/tertiaire_operat.py` après validation Légifrance. | 3 j (extraction pdfplumber + cross-check + tests) | Référentiel Cabs complet (Annexe II) consolidé. |
| P3-2 | Ingestion **BACS_COMPLET** (2 625 l drafts) : formules TRI, classes NF EN 15232, inspections. | 5 j | Sub-score BACS V2 fiabilisé. |
| P3-3 | Suppression du legacy `backend/services/compliance_engine.py` (`100 - risk_score`) ou clarification de son rôle (backward compat ? logging ? à supprimer en cutover L8 Mois 5). | 0,5 j audit + 1 j fix | Évite confusion 2 SoT scoring. |
| P3-4 | Canonisation `CAPACITE-MECANISME-RTE-2026.yaml` (passe de draft à canonique) après validation CRE. | 0,5 j | Préparation deadline 11/2026. |

**Sprint P3 total** : ~10 j/h.

---

## 4 — Plan sprints recommandé (incrémental, ~26 j/h total)

| Sprint | Priorité | Contenu | Effort | Pré-requis |
|---|---|---|---|---|
| **S1** | P0 conformité OPERAT/DEET | D5 TRI typologie + D4 année référence + D1/D2 séparation OPERAT vs ADEME (si Légifrance confirme) + rapatriement PHASE_0BIS | 5 j/h | Cross-check Légifrance D1/D2/D4 (0,5 j) |
| **S2** | P1 simplicité métier | Audit UX ConformitePage + réorg tabs + NextBestAction 1-clic + banner unifié | 4,5 j/h | S1 mergé |
| **S3** | P2 preuves & actions | PreuvesTab complétude + OperatExportManifest truth contract granulaire + idempotence actions | 6 j/h | S2 mergé |
| **S4** | P3 ingestion + cleanup | DT_OPERAT_2026 ingestion + BACS_COMPLET ingestion + cleanup compliance_engine legacy + CAPACITE-MECANISME canonisation | 10 j/h | S3 mergé |
| **Total** | | | **~26 j/h** | |

**Cadence** : 1 sprint = 1 PR (pattern brique Énergie #316-#323 : ~5 j/h moyenne par sprint). 4 PRs étalées sur 4-5 semaines avec audits postfix entre chaque.

---

## 5 — Critères d'acceptation transverses brique (à valider en fin de S4)

| # | Critère | Méthode validation |
|---|---|---|
| 1 | Hub unique préservé (1 item sidebar `/conformite`) | NavRegistry test + source-guard |
| 2 | 0 silo public DT/BACS/APER | NavRegistry test + grep |
| 3 | 5 divergences P0 OPERAT résolues | Cross-check Légifrance + tests endpoint |
| 4 | Boucle conformité → Centre d'Action V4 → preuves opérationnelle | Playwright golden path 3 étapes |
| 5 | Truth contract `{unit, source, formula_ref, period, confidence}` granulaire sur OperatExportManifest | Test endpoint + source-guard |
| 6 | Idempotence actions conformité (recompute, BACS asset, CEE dossier) | Tests pytest |
| 7 | 0 calcul métier FE conformité | Source-guard scoring V2 (existe déjà) |
| 8 | Score brique Énergie/Conformité > 95/100 (cohérent score brique Énergie #322 : 97) | Audit clôture brique Conformité |

---

## 6 — Décisions clés / non-décisions

1. **Pas de big bang refactor** : la brique est mature, ~25 audits cumulés, 9 source-guards. On itère incrémentalement.
2. **Pas de complexification UX** : objectif user explicite. À l'inverse, S2 simplifie (4 tabs → 3 + drawer).
3. **Cross-check Légifrance obligatoire avant tout fix code** : règle déjà encodée dans la mémoire `promeos-brique-conformite`. Les divergences D1/D2 ne doivent PAS être fixées « à l'aveugle » — vérifier que OPERAT mandate 0,064 et 2,3 dans le texte officiel consolidé NOR ATDL2430864A.
4. **PHASE_0BIS reste dans `promeos-audit-main`** pour l'instant — à rapatrier en S1 (P0-4) si validé utile. Alternative : rester read-only dans le repo d'audit et y faire évoluer la doc, le repo `poc` n'embarque que les artefacts validés.
5. **BACS_COMPLET / DT_OPERAT_2026 ingestion reportée S4** : 7 j/h cumulés, risque haut sans validation Légifrance préalable. Ne pas l'enchaîner sur les sprints simplicité/preuves qui sont prioritaires user.
6. **0 nouveau menu / 0 nouveau silo** : doctrine §6.2 et user explicite. Toute évolution UX passe par chips internes `/conformite?regulation=dt|bacs|aper|audit-sme`.
7. **Pas d'idée de « brique APER seule »** : APER reste sous-cadre du module Conformité (déjà acté dans NavRegistry, ROUTE_MODULE_MAP, HIDDEN_PAGES). Pas de remise en cause.

---

## 7 — Dette identifiée (non bloquante S1-S4)

| # | Item | Origine | Statut |
|---|---|---|---|
| 1 | Annexe II Cabs complète (217 p. NOR ATDL2430864A) — extraction pdfplumber/camelot ciblée section III, schéma cible `backend/regops/cabs_referentiel_2030.yaml` | Mémoire 2026-05-27 | S4 P3-1 (3-5 j) |
| 2 | Audit ISO 50001 (>23,6 GWh, deadline 11/10/2027) — pas de YAML canonique dans `docs/kb/items/reglementaire/` | Skill `regops_constants` vs KB items | À ajouter en S1 ou S4 (0,5 j YAML) |
| 3 | Followup `tarifs_sot_consolidation.md` ouvert (Phase 3B pricing bloqué) | `docs/audit/followups/` | Indépendant brique Conformité |
| 4 | Followup `co2_frontend_cleanup.md` ouvert | `docs/audit/followups/` | Indépendant brique Conformité |

---

## Verdict

🟢 **Démarrage brique Conformité validé en mode incrémental**.

La brique est **mature et stable** (~25 audits cumulés, hub unique respecté, 70+ endpoints, 6 pages, 9 source-guards). Pas de chantier urgent ni de big bang refactor à faire.

**4 sprints incrémentaux** recommandés sur ~26 j/h :
- **S1 (P0, 5 j)** : conformité OPERAT/DEET (D5 TRI typologie + D4 année référence + D1/D2 séparation OPERAT vs ADEME après cross-check Légifrance + rapatriement PHASE_0BIS).
- **S2 (P1, 4,5 j)** : simplicité métier (réorg tabs ConformitePage + NextBestAction 1-clic).
- **S3 (P2, 6 j)** : preuves & actions (PreuvesTab complétude + OperatExportManifest truth contract granulaire + idempotence).
- **S4 (P3, 10 j)** : ingestion drafts (DT_OPERAT_2026 + BACS_COMPLET) + cleanup legacy.

**Critères d'acceptation transverses** : hub unique préservé, 0 silo, 5 P0 OPERAT résolues, boucle conformité → Action → preuves opérationnelle, truth contract granulaire, idempotence, 0 calcul FE, score brique > 95/100.

**Prochaine étape** : valider ce plan, puis ouvrir S1 (sprint conformité OPERAT/DEET) avec **cross-check Légifrance préalable** sur les divergences D1/D2/D4 (règle non négociable héritée mémoire `promeos-brique-conformite`).
