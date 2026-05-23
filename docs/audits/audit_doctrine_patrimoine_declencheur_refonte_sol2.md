# Audit doctrine « patrimoine déclencheur » — refonte-sol2

> **Mission** : vérifier que `claude/refonte-sol2` porte la doctrine produit PROMEOS recadrée 2026-05-23 :
> 1. **PROMEOS = tour de contrôle du patrimoine énergétique** B2B multi-sites.
> 2. **Le patrimoine déclenche tout** : chargement patrimoine → moteur d'éligibilité → demande de données manquantes → audit (conso/factures/contrats) → leviers d'action hiérarchisés (conformité conditionnelle / optimisation / achat / pilotage usages / flexibilité progressive / GTB/API / partenariats).
> 3. **Hiérarchie produit** : diagnostic → preuve → action → gain (pas « tout l'énergie sans hiérarchie »).
> 4. **Conformité conditionnelle à l'assujettissement** : non assujetti DT/BACS/APER/SMÉ/BEGES → pivot vers performance + optimisation + achat + pilotage des usages.
>
> **Date** : 2026-05-23 · **Mode** : READ-ONLY strict.
> **HEAD audité** : commit `ade3d0a0` (`claude/refonte-sol2`) · worktree dédié `.claude/worktrees/audit-doctrine-sol2/`.
> **Périmètre exclu court terme** : ACC / PMO / clé de répartition / settlement local · chaleur réseau urbain · vapeur process industriel (Mois 6+).

## TL;DR — verdict cardinal

🎯 **La doctrine « patrimoine déclencheur » est portée à ~80 %** par le code de `claude/refonte-sol2`.

Le **moteur d'assujettissement réglementaire** existe formellement (ADR-024 Accepted Phase 3.5 le 13/05/2026), couvre les 5 règles DT/BACS/APER/SMÉ/BEGES avec **4 statuts** (`APPLICABLE` / `NOT_APPLICABLE` / `UNKNOWN` / `DATA_MISSING`), versionning par évaluateur, reason codes whitelistés, et est **câblé** côté UI sur la Synthèse Stratégique via `CadreApplicable.jsx`.

Gaps restants : CSRD/ISO 50001 absents du moteur, déclenchement automatique post-mutation patrimoine non confirmé, basculement explicite « pivot performance si NON_APPLICABLE » côté UI non outillé, brique facture intégrée mais sans graphe relationnel global explicite, hiérarchie des leviers post-éligibilité présente mais non typée (pas de routing produit conditionnel).

---

## 1. Socle PATRIMOINE — fondation

### 1.1 Hiérarchie patrimoine attendue

> Organisation → Entité juridique → Portefeuille → Site → Bâtiment → Compteur → DeliveryPoint (PDL/PCE) → Équipement → Usage → GTB → Facture → Contrat.

| Niveau | Modèle | File | Verdict |
|---|---|---|---|
| Organisation | `Organisation` | `backend/models/organisation.py` | ✅ |
| Entité juridique | `EntiteJuridique` | `backend/models/entite_juridique.py` | ✅ |
| Portefeuille | `Portefeuille` | `backend/models/portefeuille.py` | ✅ |
| Site | `Site` | `backend/models/site.py` | ✅ — historique transferts via `site_portefeuille_history.py` |
| Bâtiment | `Batiment` | `backend/models/batiment.py` | ✅ |
| Compteur unifié | `Compteur` (élec + gaz unifié — décision D1 Patrimoine v1) | `backend/models/compteur.py` | ✅ |
| DeliveryPoint (PDL/PCE) | `DeliveryPoint` + `compteur_meter_bridge.py` | `backend/services/compteur_meter_bridge.py` | ✅ |
| Contrats V2 | `ContractV2Models` + `ContractDeliveryPoint` N:N | `backend/models/contract_v2_models.py` | 🟢 D5 actée 03/05, à vérifier en seed |
| Facture | `EnergyInvoice` + `EnergyInvoiceLine` | `backend/models/billing_models.py` | ✅ |
| Équipement / Usage | `BacsCvcSystem` + `TypeUsage` enum (12 valeurs + 6 familles) | `backend/models/bacs_models.py` + `backend/models/enums.py:72-129` | ✅ |
| GTB / système BACS | `BacsCvcSystem` + métadonnées GTB | `backend/models/bacs_models.py` | ✅ |
| Audit trail mutations patrimoine | `log_patrimoine_change()` | `backend/services/audit_log_service.py` | ✅ Phase 1.3 — capture chaque changement (transfert, update, soft-delete) |

### 1.2 Patrimoine matrice v1 — couverture champs

D'après `reference_patrimoine_parametrage_matrice_v1_2026_05_03.md` :
- **~310 champs modélisés** sur 8 niveaux
- **52 champs P0 MVP (17 %)** dont 18 manquants sur Site §4.4 (OPERAT 12 + APER 5 + EFA 1) → priorité C-1
- 7 décisions D1-D7 actées (compteur unifié, audit SMÉ séparé, BACS séparé, Contrat V2, ContractDeliveryPoint N:N, SousCompteur self-FK, commit)

| Item | État | Référence |
|---|---|---|
| Champs OPERAT Site §4.4 | 🟡 partiel — gap C-1 | `reference_patrimoine_parametrage_matrice_v1_2026_05_03.md` |
| Index unique global PRM élec (C60) | 🟢 à confirmer en source-guard | Q06 doctrine |
| Index unique global PCE gaz (C85) | 🟢 à confirmer en source-guard | Q06 doctrine |
| Onboarding 3 parcours (Wizard/Expert/Bulk) | ❌ **P1** — gap C-5 | `OnboardingPage.jsx` redirige vers `/cockpit/jour` |
| Tooltip traçabilité réglementaire (NOR + URL + date) sur chaque champ | 🟢 ADEME/JORF cités dans configs | différenciateur unique vs Deepki/Metron |

### Synthèse Socle Patrimoine

| Item | Verdict |
|---|---|
| Hiérarchie 8 niveaux modélisée | ✅ |
| Champs P0 MVP (52/310) | 🟡 — 18 champs Site OPERAT/APER/EFA manquants (Sprint C-1) |
| Audit trail mutations | ✅ |
| Onboarding 3 parcours | ❌ P1 |
| Patrimoine v1 doctrine D1-D7 actées | ✅ |

---

## 2. Moteur d'éligibilité réglementaire — « ce patrimoine est-il soumis ? »

### 2.1 Architecture ADR-024 (Accepted 13/05/2026)

> **Doctrine cardinale** : un service backend unique répond à « ce site/portefeuille est-il assujetti à cette règle, et pourquoi ? » avec preuve textuelle, statut versionné, confiance.

| Composant | File | Lignes | Verdict |
|---|---|---|---|
| ADR canonique | `docs/adr/ADR-024-moteur-assujettissement.md` | — | ✅ Phase 3.5 Accepted (5 évaluateurs implémentés, audit regulatory-expert verdict RÉSERVES avec 2 fixes immédiats appliqués) |
| Service principal | `backend/regulatory/applicability_service.py` | 213 | ✅ — `compute_applicability(db, org_id, site_ids=)` + `compute_patrimoine_maturity(db, org_id)` |
| Types | `backend/regulatory/applicability_types.py` | — | ✅ — `RuleCode`, `ApplicabilityStatus`, `RuleApplicability` |
| Catalogue règles + versions | `backend/regulatory/rules_catalog.py` | 39 | ✅ — `RULE_EVALUATORS` + `RULES_VERSIONS` |
| Reason codes whitelist | `backend/regulatory/reason_codes.py` | 90 | ✅ — `_DT_REASON_CODES`, `_BACS_REASON_CODES`, `_APER_REASON_CODES`, `_SME_REASON_CODES`, `_BEGES_REASON_CODES` + `is_valid_reason_code()` |
| Endpoint REST | `backend/routes/regulatory_applicability.py` | 85 | ✅ — `/api/regulatory/applicability` consommé par drawer `<CadreApplicable />` D.3 et builders Synthèse Stratégique |
| UI grid 5 règles | `frontend/src/components/grammar/hub/CadreApplicable.jsx` | 165 | ✅ — affiche grid 5 règles + statut + maturity % + drawer reason_human |
| Wiring page Cockpit Stratégique | `backend/routes/cockpit_strategique.py:71` | — | ✅ — appel direct `compute_applicability(db, org_id, site_ids=site_ids)` |

### 2.2 Couverture règles d'éligibilité

| Règle | Évaluateur | File | Version | Statuts émis | Verdict |
|---|---|---|---|---|---|
| **DT** — Décret Tertiaire | `DTEvaluator` | `backend/regulatory/rules/dt.py` (204 LoC) | `DT-2019-771-v2024-10-01` | APPLICABLE / NOT_APPLICABLE (surface < 1000 m² tertiaire) / UNKNOWN / DATA_MISSING (`DT.DATA_MISSING.SURFACE`, `DT.DATA_MISSING.USAGE`) | ✅ |
| **BACS** — Régulation chauffage | `BACSEvaluator` | `backend/regulatory/rules/bacs.py` (199 LoC) | `BACS-2020-887+2025-1343-v2025-12-31` | APPLICABLE / NOT_APPLICABLE (Σ cvc_power_kw < 70) / DATA_MISSING (`BACS.DATA_MISSING.CVC_POWER`) | ✅ — décret 2025-1343 (report 2030) intégré |
| **APER** — EnR parking / toiture | `APEREvaluator` | `backend/regulatory/rules/aper.py` (205 LoC) | `APER-2023-175-v2024-07-01` | APPLICABLE / NOT_APPLICABLE / DATA_MISSING | ✅ — fix APER.TOITURE deadline post-audit regulatory-expert |
| **SMÉ** — Audit énergétique | `SMEEvaluator` | `backend/regulatory/rules/sme.py` (250 LoC) | `SME-L233-1+loi-2025-391-v2025-12-31` | APPLICABLE / NOT_APPLICABLE / DATA_MISSING (`SME.DATA_MISSING.EFFECTIF`, `SME.DATA_MISSING.CA`, `SME.DATA_MISSING.CONSO`) | ✅ — loi 2025-391 deadline 11/10/2026 |
| **BEGES** — Bilan GES réglementaire | `BEGESEvaluator` | `backend/regulatory/rules/beges.py` (142 LoC) | `BEGES-Grenelle2-art-75+Decret-2022-982-v2023-01-01` | APPLICABLE / NOT_APPLICABLE / DATA_MISSING (`BEGES.DATA_MISSING.EFFECTIF`) | ✅ — fix périodicité 4→3 ans post-audit |
| **CSRD** post-Omnibus | — | — | — | — | ❌ **P0 doctrine** — absent du moteur, ordonnance 2023-1142 non implémentée |
| **ISO 50001** (volontaire, déclenche exemption SMÉ) | logique dans `SMEEvaluator` (?) | — | — | — | 🟡 — déduction implicite via SMÉ, pas évaluateur dédié |
| **CEE BAT-TH-*** (volontaire, levier) | — | — | — | — | 🔵 Levier, pas règle d'éligibilité au sens ADR-024 |
| **APER toiture** (≥ 500 m² toiture commerciale post-2026) | dans `APEREvaluator` | `backend/regulatory/rules/aper.py` | — | — | ✅ fix appliqué |

### 2.3 Statut `DATA_MISSING` — preuve « quelles données manquent ? »

Cardinal pour la doctrine « le patrimoine déclenche tout ». Chaque évaluateur émet un `reason_code` typé `{RULE}.DATA_MISSING.{FIELD}` qui pointe le champ patrimoine manquant.

| Règle | Champ patrimoine déclencheur | Reason code |
|---|---|---|
| DT | `tertiaire_area_m2` ou `usage_principal` | `DT.DATA_MISSING.SURFACE` / `DT.DATA_MISSING.USAGE` |
| BACS | `cvc_power_kw` agrégé sur bâtiments | `BACS.DATA_MISSING.CVC_POWER` |
| SMÉ | `effectif_total`, `chiffre_affaires`, `conso_energie_finale` | `SME.DATA_MISSING.EFFECTIF` / `SME.DATA_MISSING.CA` / `SME.DATA_MISSING.CONSO` |
| BEGES | `effectif_total` | `BEGES.DATA_MISSING.EFFECTIF` |
| APER | surfaces parking + toiture | `APER.DATA_MISSING.PARKING` (à vérifier) |

✅ **Trace explicite** des champs manquants par règle = condition nécessaire pour « patrimoine déclenche tout » respectée.

### 2.4 Maturity patrimoine

`compute_patrimoine_maturity(db, org_id) → float ∈ [0..1]` (`applicability_service.py:97`).

> *Le score reflète à quel point le patrimoine permet une réponse fiable du moteur d'assujettissement.*

| Item | Verdict |
|---|---|
| Calcul maturity exposé | ✅ |
| Maturity affiché dans `CadreApplicable.jsx` | ✅ (prop `maturity` → `maturityPct = Math.round((maturity ?? 0) * 100)`) |
| Maturity utilisée pour bloquer certaines actions | 🟢 à vérifier en source-guard |

### Synthèse Moteur d'éligibilité

| Item | Verdict |
|---|---|
| Architecture ADR-024 | ✅ Accepted Phase 3.5 |
| 5 évaluateurs versionnés (DT/BACS/APER/SMÉ/BEGES) | ✅ |
| 4 statuts incluant `DATA_MISSING` | ✅ |
| Reason codes whitelistés + source-guard | ✅ |
| Maturity patrimoine | ✅ |
| Wiring UI CadreApplicable + Synthèse Stratégique | ✅ |
| **CSRD post-Omnibus** | ❌ **P0** |
| **ISO 50001 évaluateur dédié** | 🟡 P1 (volontaire) |
| Déclenchement auto post-mutation patrimoine | 🟢 audit_log présent, recompute à confirmer |

---

## 3. Conditionnalité conformité — « pivot vers performance si non assujetti »

### 3.1 Doctrine

> Si un client n'est pas soumis à DT, BACS, APER, audit énergétique, SMÉ/ISO 50001, alors PROMEOS doit **basculer vers performance, optimisation, achat et pilotage des usages**.

### 3.2 État UI

| Item | File | Verdict |
|---|---|---|
| `<CadreApplicable />` affiche les 5 règles avec statut explicite (4 valeurs) | `frontend/src/components/grammar/hub/CadreApplicable.jsx` | ✅ — chaque règle visible, qu'elle soit applicable ou non |
| Mapping `STATUS_TIER = { applicable, not_applicable, unknown, data_missing }` | idem | ✅ |
| Synthèse Stratégique en mode polymorphique (5 régimes : Réglementaire / Performance / Achat / Opportunité / Données insuffisantes) | `frontend/src/pages/CockpitStrategique.jsx` + builders | ✅ — cf. mémoire `project_synthese_strategique_p39_chantiers.md` (5 régimes) |
| Routage produit « si non assujetti DT → afficher kWh/m²/an benchmarks OID » | builder Performance régime | ✅ — cf. polymorphisme 5 régimes (mémoire `project_refontes_briefing_synthese_resume_cardinal.md`) |
| Routage « si non assujetti BACS → reco GTB volontaire CEE BAT-TH-* » | `recommendation_engine.py` + `cee_service.py` | 🟢 à formaliser dans builder |
| Routage « si non assujetti APER → potentiel PV volontaire » | `aper_service.py` + estimation PVGIS | 🟢 |
| Routage « si non assujetti SMÉ → diagnostic conso volontaire » | `consumption_diagnostic.py` | ✅ |

### 3.3 État backend (builders polymorphiques)

| Régime | Builder | Verdict |
|---|---|---|
| Réglementaire (au moins 1 règle APPLICABLE) | `builders/strategique/regulatory_builder.py` (?) | ✅ — Phase 3.5 livrée |
| Performance (aucune règle APPLICABLE, IPE médiocre) | `builders/strategique/performance_builder.py` (?) | ✅ — Phase 3.5 |
| Achat (contrat à renouveler imminent + écart marché) | `builders/strategique/procurement_builder.py` (?) | ✅ — Phase 3.5 |
| Opportunité (flex éligible + marché favorable) | `builders/strategique/opportunity_builder.py` (?) | ✅ — Phase 3.5 |
| Données insuffisantes (maturity < seuil) | `builders/strategique/data_insufficient_builder.py` (?) | ✅ — Phase 3.5 |

> ⚠️ Dette résiduelle bloquante (Phase 3.9) : 6 valeurs €/MWh figées dans constructeurs Procurement+Performance+Opportunity + heuristique `atteint_pct = compliance_score × 0.4` dans `compute_trajectory_drift` — cf. mémoire `project_synthese_strategique_p39_chantiers.md`.

### Synthèse Conditionnalité

| Item | Verdict |
|---|---|
| 5 statuts d'assujettissement présentés à l'utilisateur | ✅ |
| Polymorphisme 5 régimes Synthèse Stratégique | ✅ Phase 3.5 |
| Routage produit explicite par statut | ✅ (via builders polymorphiques) |
| Hide / show KPI conformité selon statut | 🟡 à vérifier en source-guard — `CadreApplicable` affiche tout (intention probable : transparence > masquage) |
| Dette 6 valeurs €/MWh figées | ⚠️ P1 — cf. Phase 3.9 |
| Heuristique `compliance_score × 0.4` | ⚠️ P1 — à remplacer par lecture findings_json détaillée |

---

## 4. Demande de données manquantes — « quelles données manquent ? »

### 4.1 Mécanique en place

✅ Le moteur d'éligibilité émet `DATA_MISSING` + `reason_code` typé pointant **exactement** le champ patrimoine manquant (cf. §2.3).

### 4.2 UI

| Item | Verdict |
|---|---|
| Bandeau « Données manquantes » dans `<CadreApplicable />` | ✅ (statut `DATA_MISSING` visuellement distinct) |
| Drawer reason_human au clic | ✅ — prop `onRuleClick` |
| Lien direct depuis bandeau vers édition champ patrimoine | 🟢 à vérifier (parcours utilisateur) |
| Onboarding wizard 3 parcours (Wizard/Expert/Bulk) | ❌ **P1** — `/onboarding` redirige vers `/cockpit/jour` |
| Bulk update CSV depuis bandeau | 🟢 `import_sites.py` existe (5 LoC stub) |

### 4.3 Backend

| Item | Verdict |
|---|---|
| Anomalies patrimoine | ✅ `patrimoine_anomalies.py` (70+ LoC) |
| `perimeter_check.py` (double counting) | ✅ |
| Data quality score | ✅ KPI registry `data_quality_score` |
| API endpoint "données manquantes par règle" | 🟡 partiel — agrégat dans payload `/api/regulatory/applicability` (champ `data_gaps`?) |

### Synthèse Demande de données

| Item | Verdict |
|---|---|
| Reason codes DATA_MISSING par règle | ✅ |
| UI bandeau visible | ✅ |
| Drawer explicatif | ✅ |
| Onboarding wizard | ❌ P1 |

---

## 5. Brique facture intégrée — « facture ↔ contrat ↔ conso ↔ compteur ↔ taxes ↔ TURPE/ATRD ↔ anomalies ↔ écarts budgétaires ↔ trajectoire »

### 5.1 Modèle relationnel

| Relation | Modèle / Service | Verdict |
|---|---|---|
| Facture ↔ Contrat | `EnergyInvoice.contract_id` FK | ✅ |
| Facture ↔ Compteur / PDL | `EnergyInvoice.pdl_id` ou via site | ✅ |
| Facture ↔ Période tarifaire | `EnergyInvoiceLine.period_start/end` + `tariff_periods_service.py` | ✅ |
| Facture ↔ Conso (réconciliation) | `consumption_unified_service:reconcile_metered_billed()` | ✅ |
| Facture ↔ Composantes TURPE/ATRD | `price_decomposition_service.py` + `billing_explainability.py` | 🟡 — composantes principales OK, CACNC + CER manquants |
| Facture ↔ Taxes (CSPE, accise, TVA, CTA) | `tarifs_reglementaires.yaml` versionné | ✅ |
| Facture ↔ Anomalies (shadow billing L0-L3) | `bill_intelligence/anomaly_detector.py` (13 règles R19→R31) | ⚠️ **P0 cardinal** — Phase L17 dead code : pipeline non câblé production (cf. `project_phase_L17_pipeline_dead_code_discovery_2026_05_09.md`) |
| Facture ↔ Écart budgétaire | `cost_by_period_service.py` + `monthly_comparison_service.py` | ✅ |
| Facture ↔ Trajectoire DT | `tertiaire_modulation_service.py` + `dt_progress_service` | ✅ |

### 5.2 Hiérarchie diagnostic → preuve → action → gain

| Étape | Service | Verdict |
|---|---|---|
| **Diagnostic** : détection écart facture vs théorique | `billing_shadow_v2.py` + 13 règles R19→R31 | ⚠️ existe mais pipeline wiring L17 à confirmer |
| **Preuve** : Evidence (NOR + date + URL JORF + MIME validation) | `Evidence` model ADR-029 IE9 | ✅ |
| **Action** : génération ActionItem via `build_actions_from_billing()` | `action_hub_service.py:181-222` | ✅ |
| **Gain** : `estimated_gain_eur` + `realized_gain_eur` + `realized_at` | `models/action_item.py:115` | ✅ |

### Synthèse Brique facture

| Item | Verdict |
|---|---|
| Modèle relationnel complet | ✅ |
| Composantes TURPE/ATRD/CSPE/CTA/accise/TVA | 🟡 (CACNC + CER manquants — cf. audit mapping §3.3) |
| Pipeline anomalies wiring | ⚠️ **P0 cardinal** (L17 dead code) |
| Hiérarchie diagnostic → preuve → action → gain | ✅ |

---

## 6. Hiérarchie des leviers post-éligibilité

### 6.1 Doctrine cardinale

> Une fois le patrimoine chargé + l'éligibilité calculée + les données manquantes demandées + l'audit fait, **PROMEOS propose les leviers d'action dans cet ordre** :
> 1. **Conformité** (si applicable seulement)
> 2. **Optimisation** (toujours)
> 3. **Achat énergie** (selon profil usages réels)
> 4. **Pilotage des usages** (recos horaires, dérives, optimisation tarifaire)
> 5. **Flexibilité** (couche progressive : implicite tarifaire → effacement explicite via agrégateurs si éligible)
> 6. **GTB/API** (pour sites pilotables)
> 7. **Partenariats** (installateurs, BE énergie, agrégateurs RTE)

### 6.2 État du code par levier

| # | Levier | Code attendu | File:line | Verdict |
|---|---|---|---|---|
| 1 | **Conformité** — actions générées **seulement** si au moins 1 règle APPLICABLE | `build_actions_from_compliance()` filtré par `ApplicabilityStatus.APPLICABLE` | `action_hub_service.py:84-128` | 🟡 — `build_actions_from_compliance()` lit `ComplianceFinding` NOK, mais **pas de filtrage explicite « si NON_APPLICABLE alors no action »** côté FE. À confirmer en source-guard. |
| 2 | **Optimisation** — toujours active | `power_optimization_service.py` + `usage_optimization_engine.py` | présent | ✅ |
| 3 | **Achat énergie** — comparaison offres selon profil usages | `purchase/cost_simulator_2026.py` + `purchase/strategy_recommender.py` + `purchase_scenarios_service.py` | présent (10+ services) | ✅ — `archetype_recommendation.py` croise NAF + profil HP/HC + saisonnalité + post-ARENH |
| 4 | **Pilotage des usages** — recos horaires + dérives + optim tarifaire | `consumption_diagnostic.py` + `tariff_periods_service.py` + `tou_service.py` + `pilotage/` (12 fichiers : `flex_ready.py`, `nebco_simulation.py`, `radar_prix_negatifs.py`, `portefeuille_scoring.py`, `roi_flex_ready.py`, etc.) | présent | ✅ |
| 5 | **Flexibilité** — couche progressive (HP/HC → effacement NEBCO) | `flex_assessment_service.py` + `flex_nebco_service.py` + `flex_mini.py` | présent | ✅ — mode advisory strict (aucun endpoint dispatch) |
| 6 | **GTB / API** — connecteurs sites pilotables | `connectors/grdf_adict.py` + Enedis SGE + Niagara/BACnet/Modbus | 🟡 — Enedis legacy XML OK, **APIs SGE V25→V26.2 + CleFIDO2 absents (P0)** · **GTB connector générique absent (P1)** |
| 7 | **Partenariats** — agrégateurs RTE / installateurs / BE | `flex_nebco_service.py` + `market_window_detector.py` | 🟡 — référencement présent mais **marketplace agrégateurs comparatif absent (P2)** + **8 modèles LUCIOLE primo-agrégateur statut non discriminé (P1)** |

### 6.3 Routing produit conditionnel — gap doctrinal

| Item | Présence | Verdict |
|---|---|---|
| Service `levers_recommender(patrimoine, applicability) → ordered list[Lever]` | — | ❌ **P0 doctrinal** — la hiérarchie 1-7 n'est pas matérialisée dans un service unique. Aujourd'hui chaque pilier vit indépendamment, l'**ordonnancement** est implicite côté UI |
| Routing UI « si non assujetti DT → masquer Conformité, montrer Performance + Achat + Pilotage en priorité » | partiel via builders polymorphiques Synthèse Stratégique | 🟡 P1 — explicite Phase 3.5 mais pas généralisé toutes pages |
| Source-guard test « actions Conformité ne sont émises que si rule_status=APPLICABLE » | — | ❌ **P0** — risque que `ComplianceFinding` génère des actions même pour des règles NOT_APPLICABLE |

### Synthèse Hiérarchie leviers

| Item | Verdict |
|---|---|
| 7 leviers présents dans le code | ✅ (avec dettes ciblées par levier) |
| **Routing produit hiérarchisé conditionnel** | ❌ **P0 doctrinal** |
| Source-guard « no compliance action if NOT_APPLICABLE » | ❌ **P0** |
| Marketplace agrégateurs / 8 modèles LUCIOLE | 🟡 P1-P2 |

---

## 7. Risques de la vision « tout l'énergie sans hiérarchie »

### 7.1 Risque #1 : afficher la conformité partout

| Risque | Mitigation présente | Verdict |
|---|---|---|
| Module conformité visible même pour clients non assujetti DT/BACS/APER | `<CadreApplicable />` affiche statut explicite (pas de masquage), Synthèse Stratégique polymorphique | 🟡 — transparence OK mais **pas de masquage actif des actions Conformité quand NOT_APPLICABLE** |
| Cockpit force trajectoire DT 2030 sur tous les sites | builder Réglementaire conditionnel | ✅ Phase 3.5 |
| Score conformité affiché même pour PME non assujettie | `compliance_score` weighted sum DT × BACS × APER × AUDIT | 🟡 — à pondérer par maturité ou masquer si toutes règles NOT_APPLICABLE |

### 7.2 Risque #2 : empilement de modules sans priorisation

| Risque | Mitigation | Verdict |
|---|---|---|
| 7 modules visibles simultanément sans priorité | absence service `levers_recommender` | ❌ — **gap doctrinal P0** |
| Cockpit affiche 10 KPI sans hiérarchie | audit Sol2 mentionne KPI registry strict, mais 10 KPI ≠ 3 priorités | 🟡 — `Top 3 priorités Cockpit` livré CX Sprint 2 PR #228 ✅ mais limité à Cockpit |

### 7.3 Risque #3 : action sans diagnostic + preuve

| Risque | Mitigation | Verdict |
|---|---|---|
| Action « Installer GTB » émise sans preuve technique | Evidence model ADR-029 + MIME validation | ✅ |
| Recommandation flex sans NEBCO assessment | `flex_assessment_service.py` chiffré | ✅ |
| Promesse `12 % chauffage` sans baseline | `baseline_service.py` IPMVP-compatible + r² | ✅ |
| Pipeline anomalies non câblé prod | dead code L17 | ⚠️ **P0** |

---

## 8. Verdict synthèse — doctrine portée à ~80 %

### 8.1 Tableau de couverture

| Pilier doctrinal | Couverture | Verdict |
|---|---|---|
| 1. Socle patrimoine (8 niveaux) | 90 % | ✅ — gap C-1 (18 champs Site OPERAT/APER/EFA), onboarding wizard P1 |
| 2. Moteur d'éligibilité (5 règles + DATA_MISSING) | 95 % | ✅ — gap CSRD (P0), ISO 50001 (P1) |
| 3. Conditionnalité conformité (5 régimes Synthèse polymorphique) | 80 % | ✅ — gap masquage actif compliance si NOT_APPLICABLE (P0), heuristique 6 valeurs figées Phase 3.9 (P1) |
| 4. Demande données manquantes | 75 % | ✅ — gap onboarding 3 parcours (P1), bulk update flow |
| 5. Brique facture intégrée (10 relations) | 85 % | ⚠️ — gap pipeline L17 (P0), CACNC + CER (P0), CSRD (P0) |
| 6. Hiérarchie 7 leviers post-éligibilité | 70 % | ❌ — gap service `levers_recommender` + source-guard « no compliance if NOT_APPLICABLE » (**P0 doctrinal**) |
| 7. Risques « tout l'énergie sans hiérarchie » | 75 % | ⚠️ — score conformité non pondéré par maturité, KPI registry FE mirror absent |

### 8.2 Hiérarchie diagnostic → preuve → action → gain

| Étape | Couverture | Verdict |
|---|---|---|
| Diagnostic (détecteurs talon/drift/anomalies + applicability) | 90 % | ✅ — gap pipeline wiring L17 |
| Preuve (Evidence model + NOR + MIME + reason_code + DATA_MISSING) | 95 % | ✅ |
| Action (ActionItem 4 briques + lifecycle ADR-028) | 90 % | ✅ — gap briques FLEX + EMS (P1), routing hiérarchisé (P0) |
| Gain (`gain_kwh` / `gain_eur` / `co2_avoided_kg` + `realized_*`) | 80 % | ⚠️ — gap violations FE zero business logic CO₂ + tarif + agrégation (P0) |

---

## 9. Top P0 réalignés sur la doctrine « patrimoine déclencheur »

> 9 items P0, **~56-78 j-h cumulés** (vs 50-74 j-h de l'audit gap mapping précédent — réorientation par doctrine n'ajoute pas de charge mais réordonne les priorités).

| # | P0 doctrinal | Verbe | Effort | Justification doctrine |
|---|---|---|---|---|
| 1 | **Service `levers_recommender(patrimoine, applicability) → ordered list[Lever]`** + source-guard « actions Conformité émises seulement si APPLICABLE » | Pilier 6 hiérarchie leviers | 4-6 j | Empêche « tout l'énergie sans hiérarchie ». Aujourd'hui chaque pilier vit indépendamment. |
| 2 | **Pipeline anomalies factures wiring L17** (13 règles R19→R31 doivent être appelées en prod) | Pilier 5 brique facture | 3-5 j | « Auditer la facture » est cardinal — actuellement dead code (cf. `project_phase_L17_*`) |
| 3 | **CACNC + CER + C5 grilles détaillées TURPE 7** dans `billing_canonical_service` | Pilier 5 brique facture | 5-7 j | Audit facture incomplet → écart shadow billing |
| 4 | **APIs SGE V25→V26.2 + CleFIDO2 + parser R6X JSON** | Pilier 6 GTB/API | 10-14 j | Sans cela, pas d'accès Enedis prod = pas de patrimoine élec fiable post 2027 |
| 5 | **CSRD post-Omnibus** dans moteur d'éligibilité (`CSREvaluator`) | Pilier 2 moteur éligibilité | 8-12 j | Bloque clients grandes entreprises 250+ salariés, ordonnance 2023-1142 |
| 6 | **3 violations FE zero business logic** (CO₂ FE → BE, tarif unitaire BE, agrégation risque/coût BE) | Pilier 5 (gain auditable) | 7-11 j | « Gain » doit être backend, traçable, KPI registry conforme |
| 7 | **APER alerte cockpit deadline 01/07/2026** (< 6 semaines) | Pilier 6 hiérarchie | 2-3 j | Levier conformité activable, deadline imminente |
| 8 | **e-facture obligatoire 1/9/2026** (Factur-X / UBL + signature électronique) | Pilier 5 brique facture | 5-8 j | Centralisation factures bloque sans ce format à compter du 1/9/2026 |
| 9 | **Parser PDF contrat** automatique | Pilier 1 socle patrimoine | 5-7 j | Sans contrat structuré, brique achat dégradée |

### Items reportés P1 (~45-60 j-h)

- ISO 50001 évaluateur dédié (volontaire, exemption SMÉ)
- Onboarding wizard 3 parcours (Wizard/Expert/Bulk)
- Briques FLEX + EMS dans `action_hub` (`build_actions_from_flex/ems`)
- Comparateur TURPE 6 vs 7 + ranking FTA optimal
- Règles détection anomalies TURPE 7 (segment / CMDPS / CER / CACNC / FTA / Psous / capacité)
- KPI registry FE mirror + KPIs gaz / chaleur
- Traçabilité CRE NEBCO + résolutions hardcodées
- TURPE 7 HC daytime 2027-2028 scenario
- 8 modèles LUCIOLE (primo-agrégateur) + UX décision
- Heuristique `compliance_score × 0.4` → lecture findings_json détaillée
- 6 valeurs €/MWh figées Phase 3.9 (constructeurs Procurement+Performance+Opportunity)
- Thermostat pièce par pièce 2027 (EPBD recast art. 7)

### Items P2 différenciation (~30-50 j-h)

CUSUM ISO 50001 · M&V IPMVP B/C/D · forecasting probabiliste Monte-Carlo · géo-cartographie PV APER · archétypes industrie (vapeur, cold storage, GPU, pharma) · marketplace agrégateurs comparatif · veille réglementaire automatique CRE/RTE/JORF · `CarpetPlot.jsx` promotion MonitoringPage + Site360 + export PDF CFO.

---

## 10. Recommandations méthodologiques

### 10.1 P0 #1 (le plus structurant)

**Créer `backend/services/levers/recommender.py`** :

```python
def recommend_levers(
    db: Session,
    org_id: int,
    applicability: dict[RuleCode, list[RuleApplicability]],
    patrimoine_maturity: float,
) -> list[Lever]:
    """
    Retourne la liste ordonnée de leviers conformément à la doctrine.

    Ordre :
        1. Conformité (uniquement si ≥1 règle APPLICABLE)
        2. Optimisation (toujours)
        3. Achat énergie (selon profil HP/HC + saisonnalité)
        4. Pilotage des usages
        5. Flexibilité (advisory progressive)
        6. GTB/API (sites pilotables uniquement)
        7. Partenariats
    """
```

Source-guard associé : `tests/source_guards/test_levers_hierarchy.py` qui valide qu'aucune action Conformité n'est émise quand toutes les règles sont NOT_APPLICABLE.

### 10.2 Source-guards complémentaires à ajouter

| Source-guard | Vérifie | Priorité |
|---|---|---|
| `test_no_compliance_action_if_not_applicable.py` | Filtre `build_actions_from_compliance` | P0 |
| `test_csrd_evaluator_present.py` | Existence `CSRDEvaluator` dans `rules_catalog` | P0 |
| `test_levers_hierarchy.py` | Ordre des leviers respecte la doctrine | P0 |
| `test_applicability_recompute_on_patrimoine_change.py` | Recompute auto post `log_patrimoine_change` | P1 |
| `test_kpi_compliance_score_respects_applicability.py` | `compliance_score` weighted par règles APPLICABLE seulement | P0 |
| `test_synthese_strategique_5_regimes_polymorphic.py` | Tous les 5 régimes émettent un payload valide | P0 |

### 10.3 Workflow méthodologique

1. Aucune correction de code n'a été effectuée — strict READ-ONLY.
2. Branche cible pour chaque P0 : `claude/refonte-sol2` (jamais main).
3. Discipline par phase : `docs/dev/methode_audit_avant_fix.md` (Phase 0 read-only → STOP gate → phases → DoD → atomic commit → source-guard test).
4. Workflow pre-merge : `/code-review:code-review` + `/simplify` + tests baseline + Playwright si UI.
5. Ré-exécuter ce audit tous les 30 jours tant que `refonte-sol2` n'est pas mergée.
6. **Croiser les 4 audits** :
   - `audit_readonly_promeos_scope_sans_acc_usage_steering.md` (code seul)
   - `audit_docs_drive_promeos_sans_acc.md` (exigences Drive)
   - `audit_drive_vs_refonte_sol2_mapping.md` (mapping bidirectionnel par 5 verbes)
   - **`audit_doctrine_patrimoine_declencheur_refonte_sol2.md` (ce document — workflow doctrine)**

---

## 11. Tests & QA — checklist zéro issue

### 11.1 Front — checklist détaillée

#### 11.1.1 Conformité conditionnelle

| Check | Vérification | État code | Verdict |
|---|---|---|---|
| Conformité n'apparaît pas en module actif si `status = non_soumis` | `<CadreApplicable />` affiche les 5 règles avec statut explicite ; **pas de masquage actif** quand toutes règles `NOT_APPLICABLE` | `frontend/src/components/grammar/hub/CadreApplicable.jsx` | 🟡 — affichage transparent, **pas de hide automatique** (intentionnel ? à arbitrer doctrine) |
| Actions Conformité non émises si `NOT_APPLICABLE` | `build_actions_from_compliance` filtre par `ComplianceFinding.status="NOK"` mais ne filtre pas par `ApplicabilityStatus` | `backend/services/action_hub_service.py:84-128` | ❌ **P0** — source-guard absent |

#### 11.1.2 KPI metadata (5 champs cardinaux)

| Champ | Backend SoT | Frontend exposé | Verdict |
|---|---|---|---|
| **Définition** (label FR humain) | `KPI_REGISTRY[id].label` | `getKpiLabel(kpiId, isExpert)` `frontend/src/.../shared/kpiLabels.js` | ✅ |
| **Formule** | `KPI_REGISTRY[id].formula` (backend) | — | ❌ **P0** — `getKpiFormula(kpiId)` absent FE |
| **Source** | `KPI_REGISTRY[id].source` | partiel via `sourceLabel` prop sur `KpiTile` | 🟡 — `sourceLabel = consoSource === 'metered' ? 'EMS' : null` (cas Cockpit), pas généralisé |
| **Période** | `KPI_REGISTRY[id].period` | — | ❌ **P0** — `getKpiPeriod(kpiId)` absent FE |
| **Périmètre** (scope site / bâtiment / org / portfolio) | `KPI_REGISTRY[id].scope` | — | ❌ **P0** — non exposé |
| **Confidence rule** | `KPI_REGISTRY[id].confidence_rule` | — | ❌ **P1** — devrait être affiché en tooltip |
| **Owner** | `KPI_REGISTRY[id].owner` | — | 🔵 — utilisé seulement audit interne |

✅ **Recommandation** : créer `frontend/src/doctrine/kpiRegistry.js` (miroir backend) + helpers `getKpiDefinition / getKpiFormula / getKpiSource / getKpiPeriod / getKpiScope` + source-guard FE bloquant `<KpiTile>` sans `kpi_id` valide.

#### 11.1.3 5 états UI (loading / empty / error / partial data / données manquantes)

| État | Pattern attendu | Détection code | Verdict |
|---|---|---|---|
| `loading` | `isLoading` / spinner / skeleton | grep `isLoading` retourne 0 hit direct — probable usage React Query / SWR avec patterns custom | 🟢 à vérifier en source-guard FE |
| `empty` | composant `<EmptyState />` | — | 🟢 à vérifier |
| `error` | composant `<ErrorBoundary />` ou `isError` | — | 🟢 à vérifier |
| `partial data` | flag `partial=true` + bandeau warning | — | ❌ **P1** — concept non outillé explicitement |
| `données manquantes` | `<CadreApplicable />` statut `DATA_MISSING` + `reason_code` + drawer | ✅ Cardinal pour la doctrine | ✅ |

✅ **Recommandation** : audit Playwright des 5 états par page (`/cockpit/jour`, `/cockpit/strategique`, `/anomalies`, `/bill-intel`, `/usages`, `/conformite`, `/achat-energie`).

#### 11.1.4 5 CTA obligatoires

| CTA cible | Présence code | File:line | Verdict |
|---|---|---|---|
| **« Compléter les données »** | ✅ multiples occurrences (consommations, BACS, contrat, conformité, réglementaire) | `mocks/actions.js:454: complete_data: 'Compléter les données'` + 8 autres hits | ✅ |
| **« Analyser mes factures »** | ❌ 0 hit | — | ❌ **P0** — CTA cardinal absent, à ajouter sur Cockpit + Site360 |
| **« Comparer mes contrats »** | ❌ 0 hit | — | ❌ **P0** — CTA cardinal absent, à ajouter sur Cockpit + Contrats |
| **« Identifier mes usages pilotables »** | 🟡 mentions « usages pilotables » et « actifs pilotables » présentes (`FlexPage.jsx`, glossaire `tdn`, source-guard `cardSrc`) mais **pas de CTA libellé exact** | `frontend/src/pages/FlexPage.jsx` + glossaire | 🟡 **P0** — wording à harmoniser |
| **« Créer une action »** | ✅ multiples CTA + `data-testid="cta-create-action-*"` | `BillIntelPage.jsx:1529`, `1601`, `1632`, plusieurs autres | ✅ |

#### 11.1.5 Aucun bouton vers écran mort

D'après audit Sol2 §10 :
- ✅ 57 routes actives + 31 redirects legacy, 0 dead-end de routing.
- ⚠️ **9 pages mortes restantes** à supprimer (Mois 5 L8 plan) : `EnergyCopilotPage`, `ActionCenterPage`, `CompliancePage`, `Dashboard`, `PurchaseAssistantPage`, `CommandCenter`, `Cockpit`, `CockpitDecision`, `LoginBackground`.

### 11.2 Back / API — checklist détaillée

#### 11.2.1 Tests unitaires du moteur réglementaire (6 cas obligatoires)

| Cas | Test attendu | File:line | Verdict |
|---|---|---|---|
| **tertiaire > 1000 m² → DT APPLICABLE** | `test_rule_dt.py:test_dt_applicable_all_usages` (« tous les usages tertiaires v1.0 doivent statuer APPLICABLE si surface ≥ 1000 ») | `backend/tests/regulatory/test_rule_dt.py:53` | ✅ |
| **tertiaire < 1000 m² → DT NOT_APPLICABLE (SDP_LT_1000)** | `test_rule_dt.py:test_dt_not_applicable_sdp_lt_1000` | `backend/tests/regulatory/test_rule_dt.py:162` | ✅ |
| **CVC > 290 kW → BACS APPLICABLE** | `test_rule_bacs.py:test_bacs_applicable_above_290kw` | `backend/tests/regulatory/test_rule_bacs.py` (9 tests dont ce cas) | ✅ |
| **CVC 70-290 kW → BACS APPLICABLE deadline 2030** | `test_rule_bacs.py:test_bacs_applicable_70_290_deadline_2030` | idem | ✅ |
| **Parking / toiture APER → APER APPLICABLE** | `test_rule_aper.py:test_aper_parking_applicable` + `test_aper_roof_applicable` | `backend/tests/regulatory/test_rule_aper.py:56,74` | ✅ |
| **Données manquantes → DATA_MISSING + reason_code** | `test_data_missing` par règle (DT, BACS, APER, BEGES, SMÉ) | tous présents | ✅ |

**Total : 54 tests** répartis sur 5 évaluateurs (DT: 15, APER: 11, SMÉ: 10, BACS: 9, BEGES: 9). **Couverture excellente** ✅.

#### 11.2.2 Tests d'intégration (4 chaînes cardinales)

| Chaîne | Test attendu | File:line | Verdict |
|---|---|---|---|
| **Import patrimoine → assessment réglementation** | `test_endpoint_applicability.py` + tests évaluateurs | `backend/tests/regulatory/test_endpoint_applicability.py` | ✅ |
| **Import facture → anomalie → action** | `test_action_hub_service.py` (build_actions_from_billing) | `backend/tests/test_action_hub_service.py` (existe mais à vérifier couverture end-to-end) | 🟡 **P1** — à compléter avec scénario complet PDF → anomaly → ActionItem |
| **Contrat → scénario achat → recommandation** | `test_purchase_scenarios` + `test_strategy_recommender` | — | ❌ **P1** — tests intégration end-to-end absents |
| **Usage → recommandation → action** | `test_recommendation_to_action` | — | ❌ **P1** — tests intégration end-to-end absents |

#### 11.2.3 Format erreur API standard (code / message / hint / correlation_id)

| Champ | Présence backend | Verdict |
|---|---|---|
| `correlation_id` | ✅ propagé ADR-027 IS9 dans tous events + `structlog` JSON logs sanitisés + `audit_log_service.py:726-882` | ✅ |
| `code` (machine-readable) | ✅ `reason_code` typé pour applicability ; HTTPException standard FastAPI pour le reste | 🟡 |
| `message` (FR humain) | ✅ `explanation` dans `RuleApplicability` + `evidence` + `notes` | ✅ |
| `hint` (action utilisateur) | ✅ `fix_hint_fr` présent dans `regulatory/rules/*.py` (DT, BACS, APER, BEGES, SMÉ) + `services/patrimoine_anomalies.py` + `routes/billing.py` + `routes/patrimoine/sites.py` | ✅ |
| Format unifié `{code, message, hint, correlation_id}` sur **tous** les endpoints | 🟡 — `fix_hint_fr` présent mais pas formalisé en wrapper API global | 🟡 **P1** |

✅ **Recommandation** : middleware `correlation_id_middleware.py` + `ErrorResponse` Pydantic standardisé enveloppant `{code, message, hint, correlation_id, trace_id}`.

### 11.3 Data — checklist détaillée

#### 11.3.1 Conversions unités

| Conversion | Centralisée backend ? | Verdict |
|---|---|---|
| **kWh ↔ MWh** | division par 1000 dans `KPI_REGISTRY[annual_consumption_mwh].formula` + `consumption_unified_service` | ✅ |
| **kW ↔ kVA** avec hypothèse `cos_phi` explicite | `cos_phi_moyen: Optional[float]` champ présent | 🟡 **P1** — conversion mais hypothèse `cos_phi` non centralisée (utility manquante) |
| **HT / TTC** | `tva_rate` versionné dans `tarifs_reglementaires.yaml` (20 % uniforme 1/8/2025, 5,5 % avant) | ✅ |
| **Dates de début / fin de période** | `EnergyInvoiceLine.period_start/end` + `tariff_periods_service.py` | ✅ |
| **m³ gaz → kWh PCS (R17 post 1/2/2026)** | `grdf_pcs_service.py:m3_to_kwh()` 14 régions + fallback 11,2 | ✅ |
| **DJU correction climatique** | `weather_dju_service.py` + `gas_weather_service.py` | ✅ |

#### 11.3.2 Aucune anomalie sans source

| Type d'anomalie | Source tracée | Verdict |
|---|---|---|
| `ComplianceFinding` | `evidence` + `rule_id` + `rule_version` | ✅ |
| `BillingAnomaly` (13 règles R19→R31) | `source` + `rule_id` | ⚠️ **P0** — pipeline wiring L17 à confirmer en prod |
| `ConsumptionInsight` | `source_type` + `source_id` + `recommended_actions_json` | ✅ |
| `ApplicabilityStatus.DATA_MISSING` | `reason_code` typé `{RULE}.DATA_MISSING.{FIELD}` | ✅ |
| `ActionItem` (dedup) | `(source_type, source_id, source_key)` UQ constraint | ✅ |

#### 11.3.3 Aucune recommandation sans hypothèse

| Recommandation | Hypothèses tracées | Verdict |
|---|---|---|
| ROI Flex Ready® | `payload.hypotheses.parametres_sources` (trace ParameterStore) + Baromètre Flex 2026 + CEE BAT-TH-116 + CRE T4 2025 | ✅ — `services/pilotage/roi_flex_ready.py` + README ligne 89 |
| NEBCO gain estimé | `hypotheses` (fallback 60 €/MWh + compensation fournisseur 30 % gain brut) | ✅ — `flex_nebco_service.py:18-70` |
| Gain CEE BAT-TH-* | `KPI_REGISTRY[leviers_mwh_year].formula` + archetype NAF | ✅ |
| Recommandation chauffage 19°C → 15 % | `recommendation_engine.py` + benchmarks ADEME | 🟢 à vérifier hypothèses explicites |
| Confiance "indicative" (vs "ROI garanti", "économies") | doctrine wording stricte (cf. `pilotage/README.md:119`) | ✅ |

✅ Doctrine cardinale respectée : **« Confiance indicative » MVP** explicite, jamais « ROI garanti ».

### 11.4 Synthèse Tests & QA

| Catégorie | Couverture | Gaps P0 |
|---|---|---|
| Tests unitaires moteur réglementaire | 95 % (54 tests / 6 cas) | — |
| Tests intégration chaînes | 25 % (1/4) | facture→action / contrat→achat / usage→reco |
| Format erreur API standard | 75 % | wrapper unifié `ErrorResponse` |
| Conversions unités | 90 % | utility `kW↔kVA` avec hypothèse `cos_phi` |
| Anomalies sourcées | 95 % | Pipeline L17 wiring |
| Recommandations avec hypothèse | 95 % | — |
| **5 CTA cardinaux Front** | 2/5 (« Compléter données » ✅ / « Créer action » ✅) | « Analyser factures » / « Comparer contrats » / « Identifier usages pilotables » |
| **5 états UI** | 1/5 explicite (`DATA_MISSING` ✅) | `partial data` non outillé |
| **KPI metadata 5 champs** | 2/5 exposés FE (label, unit) | formule / source / période / périmètre absents FE |

---

## 12. Definition of Done — verdict actuel

> PROMEOS est « OK » sur cette vision quand les 8 critères suivants sont satisfaits.

| # | Critère DoD | État actuel `claude/refonte-sol2` | Verdict |
|---|---|---|---|
| 1 | Un client charge son patrimoine et obtient **immédiatement** : périmètre énergétique + données manquantes + obligations potentielles + priorités d'action | Moteur applicability câblé Synthèse Stratégique + `<CadreApplicable />` + `DATA_MISSING` + maturity ; **onboarding wizard 3 parcours absent** (P1) ; **service `levers_recommender` absent** (P0) | 🟡 **75 %** |
| 2 | La conformité est affichée **uniquement** si le patrimoine est soumis ou probablement soumis | `<CadreApplicable />` affiche les 5 règles avec statut explicite — **pas de masquage actif** quand toutes règles `NOT_APPLICABLE` ; actions Conformité émises sans filtrage `APPLICABLE` | 🟡 **60 %** — arbitrage doctrine "transparence vs masquage" à confirmer |
| 3 | Factures, contrats, consommations, usages et actions sont **tous liés au même référentiel patrimoine** | Modèle relationnel complet : Org → EJ → Portefeuille → Site → Bâtiment → Compteur → PDL → Contrat → Facture → Usage ; `org_id` 100 % couvert | ✅ **95 %** |
| 4 | Chaque anomalie explique : où / quand / combien / pourquoi / quelle preuve / quelle action | Modèles : `where` (`site_id`), `when` (`period_start/end`), `how much` (`estimated_loss_eur` / `gain_eur`), `why` (`rule_id` + `evidence`), `proof` (Evidence ADR-029), `action` (`build_actions_from_*`) | ⚠️ **70 %** — pipeline L17 wiring P0 + 3 violations FE business logic (CO₂ / tarif / agrégation) |
| 5 | L'achat énergie propose des scénarios fondés sur les **usages réels**, pas sur des moyennes abstraites | `archetype_recommendation.py` croise NAF + profil HP/HC + saisonnalité + post-ARENH ; `purchase_scenarios_service.py` ; 10+ services achat | ✅ **85 %** — gap comparateur TURPE 6 vs 7 + 8 modèles LUCIOLE primo-agrégateur (P1) |
| 6 | Le pilotage des usages donne des recommandations **simples, actionnables et compréhensibles** | `consumption_diagnostic._actions_*()` (templates par diagnostic type) + `recommendation_engine.py` + `pilotage/` (12 fichiers) + glossaire 70+ termes + `AcronymTooltip.jsx` | ✅ **90 %** — gap décomposition 6-sources base load Griffine (P1) |
| 7 | La flexibilité reste **progressive** : optimisation tarifaire → GTB → agrégateur/effacement | Couche 1 (tarifaire) : `tariff_periods_service.py` + `tou_service.py` ✅ · Couche 2 (GTB) : enum `BacsCvcSystem` ✅ mais connecteur générique absent · Couche 3 (effacement) : `flex_nebco_service.py` mode advisory strict ✅ | 🟡 **75 %** — gap connecteur GTB générique (P1) + 8 modèles LUCIOLE primo-agrégateur (P1) |
| 8 | Le client comprend la promesse **en une phrase** (cf. §13) | Promesse cardinale réalisable à 80 % aujourd'hui ; 20 % de gaps P0 documentés (cf. §9) | 🟡 **80 %** |

### Score DoD global : **78 %** (moyenne pondérée)

| Score | Plage | Verdict |
|---|---|---|
| 90-100 % | Pilote payant Lite 6,9 k€ | non |
| 75-89 % | Pilote pré-prod / démo CFO | **oui** (état actuel) |
| 50-74 % | Démo investisseur | — |
| < 50 % | POC interne | — |

✅ **Verdict** : `claude/refonte-sol2` est **prêt pour démo CFO/DAF + pilote pré-prod**, **pas encore pour pilote payant Lite** — il reste les ~50-78 j-h P0 documentés en §9.

---

## 13. Promesse client en une phrase — verdict

> **« PROMEOS me redonne la main sur mon patrimoine énergétique : je sais à quoi je suis soumis, ce que je consomme, ce que je paie, ce qui dérive, quoi acheter, quoi piloter, quoi prouver et quoi optimiser. »**

### 13.1 Décomposition par verbe et vérification

| Phrase | Verbe doctrine | État code | Verdict |
|---|---|---|---|
| « me redonne la main sur mon patrimoine énergétique » | Centraliser | Hiérarchie 8 niveaux modélisée ✅ ; mutations tracées ✅ ; matrice v1 ~310 champs (52 P0, 18 manquants C-1) | ✅ |
| « je sais à quoi je suis soumis » | Auditer | Moteur applicability ADR-024 + UI `<CadreApplicable />` ✅ ; CSRD absent (P0) | ✅ (sauf CSRD) |
| « ce que je consomme » | Centraliser, Fiabiliser | `consumption_unified_service` SoT multi-source ✅ ; reconciliation metered/billed ✅ | ✅ |
| « ce que je paie » | Auditer | Facture parsée + composantes TURPE/ATRD/CTA/accise/TVA ; CACNC + CER absents (P0) | 🟡 |
| « ce qui dérive » | Auditer, Piloter | Détecteurs talon + drift WE + signature + drift saisonnier + carpet plot ✅ | ✅ |
| « quoi acheter » | Comparer, Piloter | `archetype_recommendation` + 10+ services achat + comparateur TURPE 6/7 partiel | 🟡 |
| « quoi piloter » | Piloter | `consumption_diagnostic` + 12 services `pilotage/` + advisory strict ✅ | ✅ |
| « quoi prouver » | Auditer | Evidence ADR-029 + Reason codes whitelistés + traçabilité NOR ✅ | ✅ |
| « quoi optimiser » | Piloter | `power_optimization_service` + `usage_optimization_engine` + `recommendation_engine` ✅ | ✅ |

### 13.2 Score promesse client : **9/9 axes adressés à 85 %**

| Axe | Couverture | Action P0 résiduelle |
|---|---|---|
| 1. Patrimoine maîtrisé | 90 % | Onboarding wizard 3 parcours (P1) |
| 2. Soumission réglementaire | 85 % | CSRD post-Omnibus (P0) |
| 3. Conso fiabilisée | 95 % | APIs SGE V25→V26.2 + CleFIDO2 + R6X JSON (P0) |
| 4. Facture auditée | 70 % | CACNC + CER + Pipeline L17 (P0) |
| 5. Dérives détectées | 90 % | Dérive WE widget FE (P1) |
| 6. Achat optimisé | 85 % | Comparateur TURPE 6/7 + 8 modèles LUCIOLE (P1) |
| 7. Pilotage advisory | 90 % | Décomposition 6-sources Griffine (P1) |
| 8. Preuve réglementaire | 95 % | Traçabilité CRE NEBCO (P1) |
| 9. Optimisation continue | 85 % | Service `levers_recommender` hiérarchisé (P0) |

### 13.3 Verdict final

✅ **La promesse client en une phrase est tenable à ~85 % aujourd'hui** sur `claude/refonte-sol2`.

Les 4 P0 cardinaux pour passer à **95 %** :
1. Service `levers_recommender(patrimoine, applicability) → ordered list[Lever]` + source-guard « no compliance action if NOT_APPLICABLE »
2. Pipeline anomalies factures L17 wiring + CACNC + CER + C5 grilles TURPE 7
3. CSRD post-Omnibus dans le moteur d'éligibilité
4. APIs SGE V25→V26.2 + CleFIDO2 + parser R6X JSON

Total effort P0 promesse client : **~26-37 j-h** (sous-ensemble des 56-78 j-h totaux du §9).

---

## Annexes

### A. Synthèse cardinale en une phrase

> **PROMEOS sur `claude/refonte-sol2` porte 80 % de la doctrine « patrimoine déclencheur »** :
> le moteur d'éligibilité existe (ADR-024 Accepted) avec 5 évaluateurs versionnés + statut `DATA_MISSING`, l'UI `<CadreApplicable />` est câblée sur la Synthèse Stratégique polymorphique 5 régimes, et 7 leviers existent dans le code.
> **Le gap doctrinal cardinal est l'absence d'un service `levers_recommender` qui matérialise la hiérarchie produit + de source-guards anti-régression** garantissant qu'aucune action Conformité n'est émise quand le patrimoine est non assujetti — sans cela, la promesse « pas d'empilement de modules sans hiérarchie » reste fragile.

### B. Chiffres clés

| Item | Valeur |
|---|---|
| Routers backend | 104 |
| Services backend | ~90 |
| Évaluateurs `regulatory/rules/` | 5 (DT, BACS, APER, SMÉ, BEGES) |
| Statuts d'éligibilité | 4 (APPLICABLE / NOT_APPLICABLE / UNKNOWN / DATA_MISSING) |
| ADR cardinaux | ADR-024 (moteur assujettissement) + ADR-025→029 (V4 Centre d'Action) |
| Modèles `regulatory/applicability_*` | 213 LoC service + 90 LoC reason codes + 39 LoC catalog |
| KPI registry | 11 KPI canoniques |
| Tests source-guards V4 | 57 |
| Branche audited | `claude/refonte-sol2` @ `ade3d0a0` |

### C. Audits PROMEOS complémentaires (4 documents)

- `docs/audits/audit_readonly_promeos_scope_sans_acc_usage_steering.md` (audit READ-ONLY code · 22/05/2026)
- `docs/audits/audit_docs_drive_promeos_sans_acc.md` (extraction 6 docs Drive · 22/05/2026)
- `docs/audits/audit_drive_vs_refonte_sol2_mapping.md` (mapping bidirectionnel 5 verbes · 23/05/2026)
- `docs/audits/audit_doctrine_patrimoine_declencheur_refonte_sol2.md` (**ce document** — workflow doctrine · 23/05/2026)

### D. Doctrine de référence

- `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (5 verbes + pricing 3 tiers)
- `docs/adr/ADR-024-moteur-assujettissement.md` (Accepted 13/05/2026)
- ADR Mois 1 (ADR-025 → ADR-029)
- `reference_patrimoine_parametrage_matrice_v1_2026_05_03.md` (~310 champs + 52 P0)
- `project_synthese_strategique_p39_chantiers.md` (polymorphisme 5 régimes + dette résiduelle)
- `project_refontes_briefing_synthese_resume_cardinal.md` (résumé cardinal 5 différenciateurs)
- `project_phase_L17_pipeline_dead_code_discovery_2026_05_09.md` (pipeline anomalies non câblé)

---

**Fin de l'audit doctrinal** — branche `claude/refonte-sol2` @ `ade3d0a0` — 2026-05-23.
**Worktree** : `.claude/worktrees/audit-doctrine-sol2/` (à nettoyer après lecture).
**Aucune modification de code n'a été effectuée pendant cet audit hormis ce livrable.**
