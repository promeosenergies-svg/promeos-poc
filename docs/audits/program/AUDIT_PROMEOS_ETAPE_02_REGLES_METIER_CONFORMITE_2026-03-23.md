# AUDIT PROMEOS — ÉTAPE 2 : RÈGLES MÉTIER & CONFORMITÉ

> **Date** : 2026-03-23
> **Baseline** : Étapes 0 et 1 (`docs/audits/program/AUDIT_PROMEOS_ETAPE_00_*.md`, `ETAPE_01_*.md`)
> **Méthode** : Lecture exhaustive de chaque moteur de conformité, chaque formule, chaque constante
> **Statut** : AUDIT UNIQUEMENT — aucune modification du repo

---

## 1. Résumé exécutif

Le moteur de conformité PROMEOS est **architecturalement solide** mais contient **4 incohérences critiques** entre ses différentes couches (YAML config, code legacy, code RegOps).

**Verdict par framework :**

| Framework | Moteur | Formules | Seuils | Preuves | Note |
| --- | --- | --- | --- | --- | --- |
| **BACS** | Complet (Putile, TRI, inspections, exemptions, R.175-3/4/5) | Exactes, auditables | Corrects (290/70 kW) | Structurées (8 types documents) | **8.5/10** |
| **Décret Tertiaire** | Double (dt_trajectory + operat_trajectory + compliance_engine) | Correctes mais **déconnectées du KPI** | Corrects (1000 m², -40%/-50%/-60%) | EFA + declarations + preuves | **6.5/10** |
| **APER** | Éligibilité réelle + estimation PV (PVGIS + zones climatiques) | Correctes | Corrects (1500/500 m², deadlines 2026-2028) | Absentes | **6/10** |
| **Scoring A.2** | Unifié (compliance_score_service) | Moyenne pondérée − pénalité critiques | **INCOHÉRENCE poids YAML vs hardcodé** | N/A | **5/10** |

**Découverte la plus grave** : `regs.yaml` définit **5 frameworks** (DT 35% + BACS 25% + APER 15% + DPE 15% + CSRD 10%) mais le fallback hardcodé n'en a que **3** (DT 45% + BACS 30% + APER 25%). Comme le code charge le YAML en priorité, le score affiché inclut potentiellement des poids pour DPE et CSRD **qui n'ont aucun évaluateur implémenté**.

---

## 2. Cartographie réelle du moteur conformité

```text
                    ARCHITECTURE CONFORMITÉ PROMEOS
                    ================================

[regs.yaml]  ────────────────────────────────────────────────────────┐
 5 frameworks: DT(35%) BACS(25%) APER(15%) DPE(15%) CSRD(10%)       │
                                                                      ▼
[RegOps Engine]                                              [compliance_score_service]
 regops/engine.py:evaluate_site()                            ← lit poids depuis regs.yaml
   ├── tertiaire_operat evaluator (rules/tertiaire_operat.py)   poids = {dt:0.35, bacs:0.25,
   ├── bacs evaluator (bacs_engine.py wrapper)                         aper:0.15, dpe:0.15,
   ├── aper evaluator (rules/aper.py)                                  csrd:0.10}
   ├── cee_p6 evaluator (financement, exclu du score)
   ├── ✗ dpe_tertiaire evaluator = NON IMPLÉMENTÉ             DPE score = fallback 50.0
   └── ✗ csrd evaluator = NON IMPLÉMENTÉ                      CSRD score = fallback 50.0
         │
         ▼                                                          │
[RegAssessment] ← persiste par framework                            │
         │                                                          ▼
         └──────────────────────────────────────────→ score = Σ(fw_score × weight) / Σ(weight)
                                                              − min(20, critical × 5)
                                                                    │
                                                                    ▼
[compliance_coordinator.py]                                  [Site.compliance_score_composite]
 recompute_site_full():
   1. compliance_engine.recompute_site()  ← LEGACY (snapshots Site)
   2. regops.engine.evaluate_site()       ← RegOps (RegAssessment)
   3. sync_site_unified_score()           ← Score A.2 → Site

                    PARALLÈLEMENT (LEGACY, DÉPRÉCIÉ)

[compliance_engine.py]
 ├── worst_status(obligations) → Site.statut_decret_tertiaire
 ├── average_avancement(obligations) → Site.avancement_decret_pct  ← CHAMP PLAT
 ├── risque_financier = 7500×NOK + 3750×RISK → Site.risque_financier_euro
 └── BACS_DEADLINE_70 = 2030-01-01  ← INCOHÉRENT avec regs.yaml (2027)
```

---

## 3. Décret Tertiaire / OPERAT

### 3.1 Formules réellement utilisées

**Trois services coexistent :**

| Service | Formule | Source conso référence | Source conso actuelle | Utilisé par |
| --- | --- | --- | --- | --- |
| `dt_trajectory_service.py:162` | `reduction_pct = (1 − actuelle/ref) × 100` puis `avancement_2030 = reduction_pct / 40 × 100` | 1. EFA `is_reference=True` 2. ConsumptionTarget oldest | 1. `consumption_unified_service` (12 mois) 2. `Site.annual_kwh_total` | **AUCUN appelant automatique** |
| `operat_trajectory.py:242-244` | `delta_kwh = current − target` puis `delta_pct = (current/target − 1) × 100` | `TertiaireEfaConsumption.is_reference=True` | `TertiaireEfaConsumption` par année | Routes tertiaire/EFA |
| `compliance_engine.py:211` | `AVG(Obligation.avancement_pct)` | N/A — lit un champ plat | N/A | **KPI cockpit** (via `kpi_service.py:218`) |

**Tag** : À RISQUE CRÉDIBILITÉ — Le KPI cockpit utilise la formule la plus pauvre (moyenne champs plats) alors que deux formules dynamiques existent.

### 3.2 Année de référence

| Aspect | Implémentation | Fichier:ligne | Verdict |
| --- | --- | --- | --- |
| Stockage | `TertiaireEfaConsumption.is_reference = True` (unique par EFA) | `operat_trajectory.py:90-103` | IMPLÉMENTÉ |
| Contrainte unicité | ValueError si 2 années de référence sur même EFA | `operat_trajectory.py:100-103` | IMPLÉMENTÉ |
| Cache sur EFA | `efa.reference_year`, `efa.reference_year_kwh` mis à jour | `operat_trajectory.py:144-146` | IMPLÉMENTÉ |
| Plage valide | 2000-2060 | `operat_trajectory.py:86-87` | IMPLÉMENTÉ |
| Lien avec KPI cockpit | **AUCUN** — `kpi_service.py:218` lit `Site.avancement_decret_pct` | Étape 1 R1 confirmé | CASSÉ |

### 3.3 Normalisation climatique

| Aspect | Implémentation | Fichier:ligne | Verdict |
| --- | --- | --- | --- |
| Champ `is_normalized` | Sur `TertiaireEfaConsumption` | `tertiaire.py:200` | IMPLÉMENTÉ |
| Méthode normalisation | `normalization_method` (dju_ratio/none) | `tertiaire.py:203` | IMPLÉMENTÉ |
| Confiance normalisation | `normalization_confidence` | `tertiaire.py:204` | IMPLÉMENTÉ |
| DJU chaud/froid | `dju_heating`, `dju_cooling` | `tertiaire.py:207-208` | IMPLÉMENTÉ |
| Source météo | `weather_data_source` (meteo_france/manual/estimated) | `tertiaire.py:209` | IMPLÉMENTÉ |
| Gouvernance 5 états | `operat_trajectory.py:324-352` : raw→normalized→review_required | | IMPLÉMENTÉ |
| Utilisé dans dt_trajectory_service | **NON** — ce service ne gère pas la normalisation | `dt_trajectory_service.py` | PARTIEL |

**Tag** : IMPLÉMENTÉ dans operat_trajectory, ABSENT dans dt_trajectory_service

### 3.4 Obligations auto-créées

| Condition | Seuil | Valeur initiale | Fichier:ligne | Correct ? |
| --- | --- | --- | --- | --- |
| `is_tertiaire(site.type)` AND `surface >= 1000` | 1000 m² | statut=A_RISQUE, avancement=0%, echeance=2030-12-31 | `onboarding_service.py:105-115` | ✅ Conforme art. R.174-1 CCH |
| Description obligation | "Reduction -40% en 2030 vs 2010" | | `onboarding_service.py:109` | ⚠️ "vs 2010" est simplificateur — l'année de référence est choisie entre 2010 et 2020 |

### 3.5 Fiabilité des sources

| Source | Reliability | Fichier:ligne |
| --- | --- | --- |
| `declared_manual` | medium | `operat_trajectory.py:24` |
| `import_invoice` | high | `operat_trajectory.py:25` |
| `api` | high | `operat_trajectory.py:26` |
| `factures` | high | `operat_trajectory.py:27` |
| `site_fallback` | low | `operat_trajectory.py:28` |
| `inferred` / `estimation` | low | `operat_trajectory.py:29-30` |
| `seed` | low | `operat_trajectory.py:31` |
| `unknown` / `None` | unverified | `operat_trajectory.py:32-33` |

**Tag** : IMPLÉMENTÉ — Système de fiabilité mature avec audit trail

---

## 4. BACS

### 4.1 Putile — Formule exacte

```python
# bacs_engine.py:86-124
Pour chaque channel (HEATING, COOLING) :
  - VENTILATION : ignoré
  - CASCADE ou NETWORK : channel_kw = Σ(unit_kw)  # somme
  - INDEPENDENT : channel_kw = max(unit_kw)        # maximum

putile_kw = max(putile_heating, putile_cooling)
```

**Tag** : IMPLÉMENTÉ — Formule correcte, conforme au décret 2020-887, avec trace d'audit

### 4.2 Seuils et deadlines

| Source | Seuil haut | Deadline haut | Seuil bas | Deadline bas |
| --- | --- | --- | --- | --- |
| `regs.yaml:61-66` | 290 kW | 2025-01-01 | 70 kW | **2027-01-01** |
| `compliance_engine.py:50-53` | 290 kW | 2025-01-01 | 70 kW | **2030-01-01** |
| `bacs_engine.py` (from YAML) | 290 kW | 2025-01-01 | 70 kW | 2030-01-01 |

**INCOHÉRENCE CRITIQUE** : `regs.yaml:66` indique `2027-01-01` avec commentaire "décret BACS 2025 (avancé de 2030 à 2027)". Le code legacy `compliance_engine.py:53` garde `2030-01-01`. Le RegOps bacs_engine charge depuis `regulations/bacs/v2.yaml` qui dit aussi `2030-01-01`.

**Tag** : À RISQUE RÉGLEMENTAIRE — Le décret BACS 2025 a effectivement avancé la deadline 70kW à 2027, mais seul `regs.yaml` reflète ce changement. Les deux moteurs de calcul utilisent encore 2030.

### 4.3 TRI Exemption

```python
# bacs_engine.py:220-276
cout_net = cout_bacs_eur × (1 − aides_pct / 100)
economies_annuelles = conso_kwh × (gain_pct / 100) × prix_kwh
tri_years = cout_net / economies_annuelles
exemption_possible = (tri_years > 10)  # Art. R.175-7 CCH
```

| Aspect | Verdict | Fichier |
| --- | --- | --- |
| Formule TRI | IMPLÉMENTÉ — conforme art. R.175-7 | `bacs_engine.py:220-276` |
| Inputs optionnels | ⚠️ `cout_bacs_eur`, `gain_pct`, `prix_kwh` doivent être fournis manuellement | |
| Aides | Prises en compte (`aides_pct`, default 0) | |
| Auto-fetch données site | NON — pas d'estimation automatique du coût/gain | IMPLICITE MAIS NON FIABILISÉ |

### 4.4 Modèle de preuves BACS

| Type preuve | Modèle | Workflow | Verdict |
| --- | --- | --- | --- |
| Attestation BACS | `BacsProofDocument.attestation_bacs` | Upload + valid_until | IMPLÉMENTÉ |
| Rapport inspection | `BacsProofDocument.rapport_inspection` | Upload + valid_until | IMPLÉMENTÉ |
| Formation exploitant | `BacsProofDocument.formation` + `BacsExploitationStatus.operator_trained` | Date + provider + certificate | IMPLÉMENTÉ |
| Consignes exploitation | `BacsProofDocument.consignes` | Upload | IMPLÉMENTÉ |
| Dérogation TRI | `BacsProofDocument.derogation_tri` + `BacsExemption` model | DRAFT→SUBMITTED→APPROVED/REJECTED→EXPIRED (5 ans) | IMPLÉMENTÉ |
| Certificat interop | `BacsProofDocument.interop_certificat` | Upload | IMPLÉMENTÉ |
| Exigences fonctionnelles R.175-3 | `BacsFunctionalRequirement` (10 critères) | Chaque: ok/partial/absent/not_demonstrated | IMPLÉMENTÉ |

**Tag** : IMPLÉMENTÉ — Modèle de preuves BACS le plus complet du POC. 8 types documents, workflow exemption complet.

### 4.5 Compliance Gate

| Statut | Signification | Fichier:ligne |
| --- | --- | --- |
| NOT_APPLICABLE | Bâtiment non tertiaire ou CVC < 70 kW | `bacs_compliance_gate.py:35` |
| POTENTIALLY_IN_SCOPE | Pas d'inventaire CVC | `bacs_compliance_gate.py:48` |
| IN_SCOPE_INCOMPLETE | Données manquantes | `bacs_compliance_gate.py:75` |
| REVIEW_REQUIRED | Blockers ou problèmes critiques | `bacs_compliance_gate.py:95` |
| READY_FOR_REVIEW | Données complètes, prêt pour revue | `bacs_compliance_gate.py:115` |

**Principe prudent** : Jamais de statut "conforme" — maximum = `READY_FOR_REVIEW` avec `is_compliant_claim_allowed = True` uniquement sans blockers ni warnings.

**Tag** : IMPLÉMENTÉ — Approche prudente correcte réglementairement

### 4.6 Alertes BACS

8 types d'alertes automatiques (`bacs_alerts.py`) :
- `inspection_overdue` (critical), `inspection_due_soon` (high/medium), `inspection_missing` (high)
- `proof_missing` (high), `proof_expired` (high)
- `action_overdue` (high), `training_missing` (high), `training_expired` (medium)

**Tag** : IMPLÉMENTÉ

### 4.7 Faiblesse : estimation CVC aléatoire

```python
# onboarding_service.py:56-60
def estimate_cvc_power(type_site, surface_m2):
    lo, hi = _CVC_RATIOS.get(type_site, (40, 70))
    watt_per_m2 = random.uniform(lo, hi)  # ← RANDOM
    return round(surface_m2 * watt_per_m2 / 1000, 1)
```

**Conséquence** : Même site créé 2 fois → CVC différent → obligation BACS potentiellement différente (si CVC oscille autour de 70 kW). Non-déterministe.

**Tag** : À RISQUE CRÉDIBILITÉ

---

## 5. APER

### 5.1 Logique d'éligibilité

```python
# aper_service.py:50-69
Parking : parking_area_m2 >= 1500 AND parking_type == "outdoor"
  - Large (> 10000 m²) : deadline 2026-07-01
  - Medium (1500-10000 m²) : deadline 2028-07-01

Toiture : roof_area_m2 >= 500
  - Deadline : 2028-01-01
```

**Tag** : IMPLÉMENTÉ — Conforme loi n°2023-175 du 10/03/2023

### 5.2 Estimation PV

| Aspect | Valeur | Fichier:ligne | Verdict |
| --- | --- | --- | --- |
| Couverture parking | 60% | `aper_service.py:193` | Réaliste (ombrières) |
| Couverture toiture | 80% | `aper_service.py:195` | Réaliste |
| Rendement panneau | 180 Wc/m² | `aper_service.py:196` | Correct (standard 2024) |
| Heures équivalentes H1 (Nord) | 1050 h/an | `aper_service.py:206` | Correct |
| Heures équivalentes H2 (Centre) | 1150 h/an | `aper_service.py:207` | Correct |
| Heures équivalentes H3 (Sud) | 1350 h/an | `aper_service.py:208` | Correct |
| Autoconsommation | 70% | `aper_service.py:216` | Conservateur (correct) |
| API PVGIS | Priorité 1 (fallback zones climatiques) | `aper_service.py:140-168` | IMPLÉMENTÉ |
| Dégradation panneaux | NON modélisée (~0.5%/an) | | NON TROUVÉ |

**Tag** : IMPLÉMENTÉ — Estimation crédible, quelques simplifications acceptables pour un POC

### 5.3 Intégration dans RegOps

| Aspect | Verdict | Fichier |
| --- | --- | --- |
| Évaluateur RegOps | **OUI** — `regops/rules/aper.py` (110 lignes) | 4 règles : PARKING_NOT_OUTDOOR, PARKING_LARGE, PARKING_MEDIUM, ROOF |
| RegAssessment APER créé | **OUI** — persiste via `regops/engine.py:persist_assessment()` | |
| Score APER | **OUI** — findings → score via `regops/scoring.py` | |
| Pénalités APER | ~20 EUR/m² parking (max 20k), ~15 EUR/m² toiture (max 15k) | `regops/rules/aper.py` |
| Obligations auto-créées | **NON** — Pas de modèle Obligation pour APER | Dashboard seulement |
| Preuves APER | **NON STRUCTURÉES** — Pas de modèle preuve spécifique APER | NON TROUVÉ |

**Tag** : PARTIEL — Éligibilité + scoring fonctionnent, mais pas d'obligations ni de preuves structurées

---

## 6. Scoring conformité

### 6.1 Formule réelle

```python
# compliance_score_service.py:225-232
raw_score = Σ(fw_score × weight) / Σ(weight)   # seuls les frameworks "available"
final_score = max(0, min(100, raw_score − critical_penalty))
critical_penalty = min(20, nb_findings_critiques × 5)
```

### 6.2 INCOHÉRENCE CRITIQUE : poids YAML vs hardcodé

| Source | DT | BACS | APER | DPE | CSRD | Total |
| --- | --- | --- | --- | --- | --- | --- |
| `regs.yaml:140-145` (source de vérité) | **0.35** | **0.25** | **0.15** | **0.15** | **0.10** | 1.00 |
| Fallback hardcodé `compliance_score_service.py:62-68` | 0.45 | 0.30 | 0.25 | — | — | 1.00 |

**Ce qui se passe réellement** (`compliance_score_service.py:47-52`) :
```python
_scoring_cfg = _load_scoring_config()  # charge regs.yaml
FRAMEWORK_WEIGHTS = _scoring_cfg.get("framework_weights", {fallback 3 frameworks})
```

→ Si `regs.yaml` est lisible (toujours le cas), les poids sont **5 frameworks**.
→ DPE et CSRD pèsent **25% du score combiné** mais n'ont **AUCUN évaluateur**.
→ Le fallback pour frameworks sans évaluateur : `_fallback_site_score()` retourne **50.0** (neutre) pour APER, et **rien** pour DPE/CSRD.
→ En pratique, DPE et CSRD sont `available=False` → exclus du dénominateur → **les poids effectifs se redistribuent sur les 3 frameworks évalués**.

**MAIS** : si un jour un RegAssessment DPE/CSRD est créé (même manuellement), il sera pris en compte avec son poids, **changeant le score** de façon inattendue.

**Tag** : À RISQUE CRÉDIBILITÉ — Incohérence latente entre config et implémentation

### 6.3 Fallback scores

| Framework | Si RegAssessment existe | Si absent, findings existent | Si rien n'existe |
| --- | --- | --- | --- |
| DT | `ra.compliance_score` | `(ok + unknown×0.5) / total × 100 − overdue×15` | `Site.statut_decret_tertiaire` → status_to_score |
| BACS | `ra.compliance_score` | idem | `Site.statut_bacs` → status_to_score |
| APER | `ra.compliance_score` | idem | **50.0** (neutre par défaut) |
| DPE | — | — | `available=False` → exclu |
| CSRD | — | — | `available=False` → exclu |

**Status-to-score mapping** (`compliance_score_service.py:114-127`) :

| Statut | Score |
| --- | --- |
| CONFORME | 100 |
| DEROGATION | 80 |
| A_RISQUE / EN_COURS / UNKNOWN | 50 |
| NON_CONFORME | 0 |

### 6.4 Confidence

| Condition | Confidence |
| --- | --- |
| 3+ frameworks évalués | high |
| 2 frameworks évalués | medium |
| 0-1 framework évalué | low |

**Note** : en pratique, avec DPE/CSRD non implémentés, le maximum atteignable est `frameworks_evaluated = 3` (DT + BACS + APER) → confidence = "high". Correct.

### 6.5 Grades et seuils UI

| Grade | Seuil | Couleur UI |
| --- | --- | --- |
| A | >= 85 | Vert |
| B | >= 70 → conforme | Vert |
| C | >= 50 | Orange |
| D | >= 40 → a_risque | Orange |
| F | < 40 → non_conforme | Rouge |

**Exposé via API** : `GET /api/compliance/meta` retourne poids, seuils, version scoring.

**Tag** : IMPLÉMENTÉ — Score explicable via l'API meta

---

## 7. Preuves / hypothèses / traçabilité

### 7.1 Distinction des sources de données

| Tag | Où utilisé | UI display |
| --- | --- | --- |
| `metered` (compteur) | `TertiaireEfaConsumption.source`, `DataPoint.source_type` | `ConsoSourceBadge` vert |
| `billed` (facture) | `TertiaireEfaConsumption.source = "import_invoice"` | `ConsoSourceBadge` bleu |
| `estimated` | `TertiaireEfaConsumption.source = "estimation"` | `ConsoSourceBadge` orange |
| `declared_manual` | `TertiaireEfaConsumption.source` | Non distingué en UI (medium reliability) |
| `seed` | `TertiaireEfaConsumption.source`, `ComplianceRunBatch.triggered_by = "demo_seed"` | Non distingué en UI |

**Tag** : PARTIEL — Le backend distingue 8 sources, mais l'UI n'en affiche que 3 (metered/billed/estimated)

### 7.2 Audit trail

| Modèle | Ce qu'il trace | Fichier |
| --- | --- | --- |
| `ComplianceEventLog` | Toute mutation : entity_type, entity_id, action, before/after JSON, actor, source_context | `models/compliance_event_log.py` |
| `ComplianceRunBatch` | Chaque évaluation : triggered_by, sites_count, findings_count, nok_count | `models/compliance_run_batch.py` |
| `ComplianceFinding.inputs_json` | Données d'entrée du finding | `models/compliance_finding.py` |
| `ComplianceFinding.params_json` | Seuils/paramètres appliqués | |
| `ComplianceFinding.engine_version` | Hash config du moteur | |
| `BacsAssessment.evidence_json` | Trace Putile, TRI, inspections | `models/bacs_models.py` |

**Tag** : IMPLÉMENTÉ — Audit trail complet côté backend

### 7.3 Explainabilité côté UI

| Aspect | Disponible ? | Fichier |
| --- | --- | --- |
| Glossaire termes conformité | OUI — `glossary.js` : compliance_score, decret_tertiaire, decret_bacs, aper, confiance | `frontend/src/ui/glossary.js` |
| Explain composant | OUI — `<Explain term="...">` avec tooltip | `frontend/src/ui/Explain.jsx` |
| Score breakdown par framework | OUI — API retourne `breakdown[]` | `compliance_score_service.py:ComplianceScoreResult` |
| Breakdown affiché en UI | **PARTIEL** — Score total + confidence affichés, breakdown pas systématiquement affiché | ConformitePage |
| "Pourquoi ce statut" | **PARTIEL** — findings ont `evidence` texte mais pas de modal dédié | |
| Confidence affiché | **PARTIEL** — Dans dossier print seulement, pas dans les badges | ConformitePage:801 |

**Tag** : PARTIEL — Backend explicable, UI sous-exploite les données disponibles

### 7.4 Preuves par framework

| Framework | Modèle preuve | Types | Upload | Validation | Workflow |
| --- | --- | --- | --- | --- | --- |
| BACS | `BacsProofDocument` + `BacsExemption` | 6 types + exemption full workflow | OUI (API) | Manual (admin) | DRAFT→SUBMITTED→APPROVED/REJECTED→EXPIRED |
| DT/OPERAT | `TertiaireProofArtifact` + `TertiaireDeclaration` | Audit, DPE, facture, etc. | OUI (API + kb_doc_id) | Checklist 6 critères | DRAFT→SUBMITTED→VERIFIED/REJECTED |
| APER | **AUCUN** | — | — | — | — |

**Tag** : BACS = IMPLÉMENTÉ, DT = IMPLÉMENTÉ, APER = NON TROUVÉ

---

## 8. KPI ou vues trompeuses

### V1 : Score conformité potentiellement biaisé par DPE/CSRD fantômes

**Problème** : `regs.yaml` alloue 25% du score (DPE 15% + CSRD 10%) à des frameworks sans évaluateur. Actuellement, ces frameworks sont `available=False` et exclus du dénominateur, donc le score est correct **par accident**. Mais la config suggère une couverture 5 frameworks que le produit n'a pas.

**Impact UX** : `GET /api/compliance/meta` expose les 5 poids. Si l'UI les affiche, l'utilisateur croira que 5 obligations sont évaluées.

**Tag** : À RISQUE UX

### V2 : avancement_decret_pct = moyenne manuelle, pas trajectoire

Confirmé étape 1. `kpi_service.py:218` lit `AVG(Site.avancement_decret_pct)` alimenté par `compliance_engine.py:211` = `average_avancement(obligations)` = **moyenne des Obligation.avancement_pct** (valeurs seed ou manuelles). La trajectoire dynamique (`dt_trajectory_service.py:162`) n'est jamais appelée.

**Tag** : À RISQUE CRÉDIBILITÉ (confirmé étape 1)

### V3 : APER dashboard isolé sans obligations ni preuves

L'utilisateur voit une page APER avec sites éligibles, deadlines, estimation PV. Mais :
- Pas d'obligation créée automatiquement
- Pas de preuve attendue/structurée
- Pas de workflow de mise en conformité

L'impression de maturité dépasse la réalité opérationnelle.

**Tag** : À RISQUE UX — Impression trompeuse de complétude

### V4 : `regs.yaml:66` contient une deadline BACS 70kW erronée (2027)

`regs.yaml:66` indique `"2027-01-01"` avec commentaire "avancé de 2030 à 2027" — **c'est l'inverse**. Le décret n°2025-1343 du 26/12/2025 a **REPOUSSÉ** la deadline de 2027 à 2030 (alignement directive EPBD). `compliance_engine.py:53` et `regulations/bacs/v2.yaml:12` sont corrects à `2030-01-01`. Seul `regs.yaml` est faux.

Source : [Décret n°2025-1343 — report officiel à 2030](https://www.sobre-energie.com/actus/decret-bacs-le-report-a-2030-est-officiel/)

**Tag** : À RISQUE RÉGLEMENTAIRE — `regs.yaml` doit être corrigé

---

## 9. Top P0 / P1 / P2

### P0 — Bloquant crédibilité

| # | Problème | Fichier:ligne | Impact | Vérification source officielle |
| --- | --- | --- | --- | --- |
| P0-1 | **Poids scoring YAML (5 fw) vs évaluateurs implémentés (3 fw)** | `regs.yaml:140-145` vs `compliance_score_service.py:62-68` | Score correct car DPE/CSRD exclus (`available=False`), mais config expose une ambition non réalisée | Les 5 frameworks sont réglementairement pertinents (DPE Tertiaire = décret n°2024-1040, CSRD = directive 2022/2464). Recommandation : ajouter `implemented: false` sur DPE/CSRD dans regs.yaml |
| P0-2 | **`regs.yaml:66` dit 2027 pour BACS 70kW — c'est FAUX** | `regs.yaml:66` (2027, commentaire inversé) vs `compliance_engine.py:53` et `regulations/bacs/v2.yaml:12` (2030, correct) | `regs.yaml` a un commentaire erroné ("avancé de 2030 à 2027") alors que le décret n°2025-1343 du 26/12/2025 a au contraire **REPOUSSÉ** la deadline de 2027 à 2030 (alignement EPBD). Le code legacy et le YAML BACS sont corrects | Source : [Décret n°2025-1343](https://www.sobre-energie.com/actus/decret-bacs-le-report-a-2030-est-officiel/) publié au JO 27/12/2025. Correctif : mettre `regs.yaml:66` à `"2030-01-01"` avec commentaire "décret n°2025-1343 — report de 2027 à 2030, alignement EPBD" |

### P1 — Crédibilité marché

| # | Problème | Fichier:ligne | Impact |
| --- | --- | --- | --- |
| P1-1 | **CVC estimation aléatoire** (`random.uniform`) | `onboarding_service.py:59` | Non-déterministe. Un site bureau 1500m² peut être 60 kW (hors scope BACS) ou 105 kW (obligé BACS) selon le random |
| P1-2 | **APER sans obligations ni preuves** | `aper_service.py` | Dashboard impressionnant mais pas de workflow de mise en conformité |
| P1-3 | **Confidence non affichée dans les badges UI** | `ConformitePage.jsx` | L'utilisateur ne sait pas si le score est fiable (high/medium/low) |
| P1-4 | **Données seed non distinguées des données réelles en UI** | `ConsoSourceBadge` ne montre pas `seed` | En démo, tout semble réel |

### P2 — Premium

| # | Problème | Impact |
| --- | --- | --- |
| P2-1 | Score breakdown DT/BACS/APER non affiché systématiquement | L'utilisateur ne comprend pas la composition du score |
| P2-2 | TRI exemption BACS nécessite inputs manuels (coût, gain, prix) | Pas d'estimation automatique → feature sous-utilisée |
| P2-3 | Dégradation panneaux PV non modélisée | Estimation APER optimiste sur 25 ans |
| P2-4 | Pénalités APER = estimation grossière (~20 EUR/m²) sans base réglementaire citée | Chiffre potentiellement contestable |

---

## 10. Plan de correction priorisé

### Immédiat (1-3 jours)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 1 | **Marquer DPE/CSRD comme non implémentés dans regs.yaml** : ajouter `implemented: false` sur ces 2 frameworks + commentaire explicatif. Les poids restent informatifs pour la roadmap | `regops/config/regs.yaml:140-145` | XS |
| 2 | **Corriger `regs.yaml:66`** : remplacer `"2027-01-01"` par `"2030-01-01"` et corriger le commentaire erroné (décret n°2025-1343 du 26/12/2025 a repoussé de 2027 à 2030, alignement EPBD). `compliance_engine.py:53` et `regulations/bacs/v2.yaml` sont déjà corrects | `regops/config/regs.yaml:66` | XS |
| 3 | **Rendre CVC estimation déterministe** : remplacer `random.uniform` par médiane du range ou hash(site_id) pour reproductibilité | `onboarding_service.py:59` | XS |

### Court terme (1 semaine)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 4 | Afficher confidence dans les badges conformité | `ConformitePage.jsx`, `ui/Badge.jsx` | S |
| 5 | Afficher breakdown DT/BACS/APER dans le score | `ConformitePage.jsx` (ComplianceScoreHeader) | S |
| 6 | Distinguer données seed en UI (badge "données démo") | `ConsoSourceBadge.jsx`, `DemoBanner.jsx` | S |
| 7 | Créer obligations APER automatiques (comme DT et BACS) | `onboarding_service.py`, `models/` | M |

### Moyen terme (2-4 semaines)

| # | Action | Fichier | Effort |
| --- | --- | --- | --- |
| 8 | Implémenter évaluateur DPE Tertiaire dans RegOps | `regops/rules/`, modèles | L |
| 9 | Ajouter preuves structurées APER (comme BACS) | `models/`, `routes/aper.py` | M |
| 10 | Auto-estimer coûts BACS pour pré-remplir TRI | `bacs_engine.py`, ratios sectoriels | L |

---

## 11. Definition of Done

| Critère | Statut |
| --- | --- |
| Formule DT trajectoire vérifiée (3 services) | FAIT |
| Formule BACS Putile vérifiée (cascade/réseau/indépendant) | FAIT |
| Formule TRI exemption vérifiée | FAIT |
| Formule scoring A.2 vérifiée | FAIT |
| Incohérence poids YAML vs hardcodé identifiée | FAIT — P0-1 |
| Incohérence deadline BACS 70kW identifiée | FAIT — P0-2 |
| CVC estimation aléatoire identifiée | FAIT — P1-1 |
| APER dashboard vs workflow évaluée | FAIT — P1-2 |
| Système de preuves audité par framework | FAIT (BACS=complet, DT=complet, APER=absent) |
| Traçabilité/audit trail vérifié | FAIT — ComplianceEventLog + inputs_json |
| Propagation vers KPI vérifiée | FAIT — confirmé rupture étape 1 |
| Vues trompeuses identifiées | FAIT — 4 vues documentées |
| P0/P1/P2 avec fichiers et effort | FAIT |

---

*Audit étape 2 réalisé le 2026-03-23. Prêt pour l'étape 3 : audit Bill Intelligence & Achat.*
