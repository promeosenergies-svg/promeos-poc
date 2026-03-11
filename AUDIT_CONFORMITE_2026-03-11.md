# AUDIT SÉVÈRE — BRIQUE CONFORMITÉ PROMEOS

**Date** : 11 mars 2026
**Auteur** : Principal Product Architect + Staff Engineer + Energy Regulation Lead
**Périmètre** : Brique Conformité PROMEOS — code, données, UI, réglementation
**Méthode** : Audit 8 angles + Gap Analysis + Plan d'upgrade 4 niveaux

---

## 1. SYNTHÈSE EXÉCUTIVE

**Verdict** : La brique Conformité PROMEOS est **significativement plus avancée qu'attendu pour un POC**. Elle couvre 3 cadres réglementaires (Décret Tertiaire, BACS, APER) avec de vrais moteurs de calcul, un modèle de données riche (17+ tables), des YAML versionnés, et un frontend avec workflow guidé. Ce n'est pas un dashboard décoratif.

**Mais** : elle souffre de 3 moteurs concurrents mal articulés, d'un fossé entre la richesse backend et l'exposition frontend, d'incohérences de deadlines entre fichiers, et d'un coffre de preuves embryonnaire. L'APER est sous-modélisée. Le CEE est un placeholder. La différenciation marché est là en fondation mais pas encore lisible.

### Note globale : 62/100

| Critère | Note | Commentaire |
|---------|------|-------------|
| Couverture réglementaire | 72/100 | DT+BACS solides, APER faible, CEE stub |
| Modèle de données | 78/100 | Très riche, quelques trous (APER, exemptions) |
| Moteur de décision | 55/100 | 3 engines en parallèle = confusion |
| Preuves & audit trail | 45/100 | Modèle OK, UX minimal, pas de coffre |
| UX / Lisibilité | 68/100 | Guided mode excellent, mais surcharge |
| Orchestration opérationnelle | 60/100 | Actions liées, mais pas de packs reg |
| Intégration briques | 65/100 | Liens Patrimoine+Actions OK, Billing/Achat faibles |
| Différenciation marché | 55/100 | Fondations uniques, pas encore exploitées |

### Potentiel

| Horizon | Score cible | Condition |
|---------|-------------|-----------|
| Aujourd'hui | 62/100 | — |
| +30 jours | 78/100 | Quick wins + consolidation moteurs + preuves |
| +90 jours | 88/100 | BACS readiness, timeline enrichie, exports, pédagogie |

### Message central

PROMEOS a déjà les fondations d'un cockpit réglementaire opérationnel que peu de concurrents possèdent. Le problème n'est pas le manque de contenu — c'est la fragmentation. Trois moteurs, deux pages conformité (legacy + V92), des données riches mais mal surfacées. La priorité absolue est de consolider, pas d'ajouter. Rendre lisible ce qui existe déjà ferait gagner 15 points immédiatement.

---

## 2. AUDIT DÉTAILLÉ — 8 ANGLES

---

### ANGLE 1 — COUVERTURE RÉGLEMENTAIRE

#### FAITS

- **Décret Tertiaire (n°2019-771)** : Modélisé en profondeur. EFA (Entité Fonctionnelle Assujettie) avec bâtiments, surfaces, usages, rôles (propriétaire/locataire/mandataire), événements de périmètre, déclarations annuelles, contrôles qualité. 5 règles YAML (`DT_SCOPE`, `DT_OPERAT`, `DT_TRAJECTORY_2030`, `DT_TRAJECTORY_2040`, `DT_ENERGY_DATA`). Seuil 1000 m² tertiaire. Export OPERAT CSV fonctionnel.

- **BACS (n°2020-887)** : Le plus abouti. Moteur Putile V2 réel (cascade/réseau=somme, indépendant=max). Deux paliers (290kW→2025, 70kW→2030). Exemption TRI >10 ans. Inspection quinquennale. Cutoff renouvellement 2023-04-09. CVC inventory par système. Attestation/dérogation tracking.

- **APER (Loi n°2023-175)** : Couverture minimale. Parking ≥1500 m² outdoor, toiture ≥500 m². Deadlines correctes (2026-07/2028-07/2028-01). Pas de modèle dédié — juste des champs sur Site.

- **CEE P6** : Placeholder. Détection d'opportunité (gros site sans GTB → CEE BAT-TH-158) mais pas de logique métier.

- **3 packs YAML versionnés** : `decret_tertiaire_operat_v1.yaml`, `decret_bacs_v1.yaml`, `loi_aper_v1.yaml` + config RegOps `regs.yaml`.

#### HYPOTHÈSES

- **Incohérence deadline BACS 70-290kW** : Le frontend (`complianceLabels.fr.js`) affiche 2027-01-01, le backend (`regulations/bacs/v2.yaml`) dit 2030-01-01, le YAML rules dit "2027". La date réglementaire réelle est **1er janvier 2025 pour >290kW** et **1er janvier 2027 pour 70-290kW** (modifié par décret 2023-444). Ni 2027 ni 2030 n'est totalement exact sans préciser le contexte (bâtiments existants vs neufs).

- **Trajectoire Décret Tertiaire** : Le système stocke `avancement_pct` mais ne calcule pas réellement l'écart par rapport à l'année de référence. C'est un champ saisi/estimé, pas calculé depuis les consommations réelles.

- **Penalties** : Les montants (7500€ non-déclaration, 1500€ non-affichage) sont corrects pour le DT. BACS n'a pas de pénalité directe dans le décret — le 7500€ dans `regs.yaml` est une estimation. APER 20€/m² est une approximation grossière.

- **Surface retenue vs exclue** : Le modèle ne distingue pas surface SDP vs SHON vs utile. `tertiaire_area_m2` est un champ unique sans qualification.

#### DÉCISIONS

- **Conserver** : Tout le modèle BACS V2 (le plus solide). Le système EFA Tertiaire. Les YAML versionnés. Le scoring unifié (45/30/25).
- **Corriger** : Harmoniser les deadlines BACS entre backend/frontend/YAML. Clarifier le type de surface.
- **Ajouter** : Calcul réel de trajectoire DT depuis consommations. Modèle APER dédié. Exemptions détaillées.

---

### ANGLE 2 — MODÈLE DE DONNÉES

#### FAITS

Le modèle est **remarquablement complet** pour un POC :

| Capacité | Statut | Tables/Champs |
|----------|--------|---------------|
| Site / Bâtiment | ✅ Complet | `Site`, `Batiment` avec surface, CVC, année construction |
| Unité foncière / EFA | ✅ Complet | `TertiaireEfa` + `TertiaireEfaBuilding` |
| Propriétaire / Locataire / Mandataire | ✅ Modélisé | `EfaRole` enum + `TertiaireResponsibility` |
| Surface tertiaire | ⚠️ Partiel | `tertiaire_area_m2` unique, pas de split SDP/SHON |
| Système CVC / BACS | ✅ Complet | `BacsAsset`, `BacsCvcSystem` avec architecture + Putile |
| APER toiture / parking | ⚠️ Minimal | Champs sur `Site` uniquement, pas de table dédiée |
| Documents de preuve | ✅ Modélisé | `Evidence` + `TertiaireProofArtifact` |
| Obligations | ✅ Modélisé | `Obligation` + `ComplianceFinding` |
| Audit trail | ✅ Partiel | `inputs_json`, `params_json`, `evidence_json`, `engine_version` dans ComplianceFinding |
| Score historique | ✅ Complet | `ComplianceScoreHistory` mensuel avec breakdown |
| Workflow OPS | ✅ Complet | `InsightStatus` (open/ack/resolved/false_positive) |
| Run batch | ✅ Complet | `ComplianceRunBatch` trace chaque évaluation |
| Événements périmètre | ✅ Complet | `TertiairePerimeterEvent` (changement occupant, vacance, rénovation, scission, fusion) |
| Déclarations annuelles | ✅ Complet | `TertiaireDeclaration` (draft→prechecked→exported→submitted) |
| Data quality issues | ✅ Complet | `TertiaireDataQualityIssue` avec severity + remediation |

#### Tables SQL complètes

```
Core Compliance:
  - obligations (site_id, type, statut, echeance, avancement_pct)
  - compliance_findings (site_id, regulation, rule_id, status, severity, deadline, evidence_json, inputs_json, params_json)
  - compliance_score_history (site_id, org_id, month_key UNIQUE, score, grade, breakdown_json)
  - compliance_run_batches (org_id, triggered_by, sites_count, findings_count, nok_count)
  - evidences (site_id, type, statut, file_url)
  - reg_assessments (object_type, object_id, computed_at, global_status, compliance_score, findings_json)

BACS:
  - bacs_assets (site_id, building_id, is_tertiary_non_residential, pc_date, renewal_events_json)
  - bacs_cvc_systems (asset_id, system_type, architecture, units_json, putile_kw_computed)
  - bacs_assessments (asset_id, assessed_at, threshold_applied, is_obligated, deadline_date, trigger_reason, tri_years, compliance_score)
  - bacs_inspections (asset_id, inspection_date, due_next_date, report_ref, status)

Tertiaire/OPERAT:
  - tertiaire_efa (org_id, site_id, nom, statut, role_assujetti, reporting_start/end)
  - tertiaire_efa_building (efa_id, building_id, usage_label, surface_m2)
  - tertiaire_responsibility (efa_id, role, entity_type, entity_value, contact_email)
  - tertiaire_perimeter_event (efa_id, type, effective_date, description, justification)
  - tertiaire_declaration (efa_id, year, status, checklist_json, exported_pack_path)
  - tertiaire_proof_artifact (efa_id, type, file_path, kb_doc_id, owner_role, valid_from/to)
  - tertiaire_data_quality_issue (efa_id, year, code, severity, message_fr, status, proof_required_json)
```

#### HYPOTHÈSES

- Les JSON fields (`renewal_events_json`, `units_json`, `responsible_party_json`) sont fragiles : pas de validation schema, pas d'index, pas de requêtes performantes.
- `Evidence.file_url` est un simple string — pas de vrai stockage objet, pas de checksum, pas de versioning.
- Le lien `TertiaireProofArtifact.kb_doc_id` vers la KB Memobox existe en modèle mais l'intégration semble stub.

#### DÉCISIONS

- **Conserver** : Tout le modèle. C'est la force cachée de PROMEOS.
- **Corriger** : Ajouter validation JSON (Pydantic models pour les JSON fields). Qualifier le type de surface.
- **Ajouter** : Table `AperAssessment` dédiée (miroir de `BacsAssessment`). Champ `surface_type` (SDP/SHON/utile).

---

### ANGLE 3 — MOTEUR DE DÉCISION

#### FAITS

**3 moteurs coexistent** — c'est le problème principal :

| Moteur | Fichier | Rôle | Utilisé par |
|--------|---------|------|-------------|
| Legacy | `compliance_engine.py` | Calcul snapshots depuis `Obligation` | `POST /compliance/recompute` |
| Rules | `compliance_rules.py` | Évalue YAML packs → `ComplianceFinding` | `POST /compliance/recompute-rules` |
| RegOps | `regops/engine.py` | Évalue 4 regulations → cache `RegAssessment` | `POST /regops/evaluate` |

Plus le **BACS V2** (`bacs_engine.py`) qui est un sous-moteur appelé par RegOps.

Le **scoring unifié** (`compliance_score_service.py`) agrège les résultats : DT 45% + BACS 30% + APER 25% - pénalités critiques (max -20 pts).

```
Score = (DT_score × 0.45) + (BACS_score × 0.30) + (APER_score × 0.25) − critical_penalty

Status mapping: COMPLIANT=100, AT_RISK=50, NON_COMPLIANT=0, UNKNOWN=50, DEROGATION=80
critical_penalty = min(critical_findings_count × 5, 20) pts

Grade: A ≥ 85, B ≥ 70, C ≥ 50, D ≥ 30, F < 30
Conforme (vert): ≥ 70 | À risque (orange): ≥ 40 | Non conforme (rouge): < 40
Confidence: High (3/3 frameworks), Medium (2/3), Low (0-1)
```

#### HYPOTHÈSES

- L'utilisateur ne sait pas quel moteur est actif. Le frontend appelle `/compliance/bundle` qui utilise Rules, mais le Cockpit peut lire `RegAssessment` (RegOps). Résultats potentiellement divergents.
- Le `compliance_engine.py` (legacy) travaille depuis les `Obligation` (saisie manuelle), tandis que Rules et RegOps travaillent depuis les données site (automatique). Deux paradigmes incompatibles.
- La pondération 45/30/25 est hardcodée dans `compliance_score_service.py` — pas dans le YAML. Non configurable.

#### DÉCISIONS

- **Conserver** : RegOps + BACS V2 comme moteurs principaux. Le scoring unifié.
- **Corriger** : Déprécier `compliance_engine.py` (legacy). Clarifier dans le code quel moteur est source de vérité. Externaliser les poids du scoring dans le YAML.
- **Ne pas ajouter** : Pas besoin d'un 4ème moteur. Consolider les 3 en 1 pipeline.

---

### ANGLE 4 — PREUVES & AUDIT TRAIL

#### FAITS

- **2 modèles de preuve** : `Evidence` (générique, lié à Site) + `TertiaireProofArtifact` (lié à EFA).
- **Catalogue de preuves** : `tertiaire_proof_catalog.py` avec 6 types + mapping issue→preuve.
- **Audit trail** : `ComplianceFinding` stocke `inputs_json`, `params_json`, `evidence_json`, `engine_version`. `ComplianceRunBatch` trace chaque évaluation.
- **Frontend** : `PreuvesTab.jsx` permet l'upload. `ExecutionTab.jsx` affiche les preuves attendues par finding.

#### Champs d'audit dans ComplianceFinding

| JSON Field | Contenu | Exemple |
|-----------|---------|---------|
| `inputs_json` | Données d'entrée de l'évaluation | `{"tertiaire_area_m2": 2500, "cvc_power_kw": 150}` |
| `params_json` | Seuils/paramètres appliqués | `{"scope_threshold_m2": 1000, "tier1_kw": 290}` |
| `evidence_json` | Références preuves | `{"attestation_bacs": "VALID", "derogation_bacs": null}` |
| `engine_version` | Hash version moteur | `"bacs_v2.0"`, `"compliance_score_service_v33"` |

#### HYPOTHÈSES

- L'upload est cosmétique. Pas de validation de contenu, pas de signature, pas d'expiration automatique.
- Les `Evidence` liées au Site et les `TertiaireProofArtifact` liées à l'EFA ne sont pas liées entre elles. Deux silos.
- L'audit trail backend (JSON fields) n'est **jamais surfacé dans le frontend** en mode non-expert. Données riches mais invisibles.
- Pas de coffre-fort documentaire. `file_url` pointe vers un path local — pas de stockage sécurisé.

#### DÉCISIONS

- **Conserver** : Le catalogue de preuves. Le modèle `TertiaireProofArtifact`. Les JSON d'audit dans ComplianceFinding.
- **Corriger** : Unifier les deux modèles de preuve ou créer un bridge. Surfacer l'audit trail dans le drawer de finding. Ajouter expiration/alerte sur les preuves.
- **Ajouter** : Section "Historique d'évaluation" dans le frontend (dates, versions, deltas). Alerte preuve expirée.

---

### ANGLE 5 — UX / UI / LISIBILITÉ

#### FAITS

- **Page principale** : `ConformitePage.jsx` avec 4 onglets (Obligations, Données, Plan d'exécution, Preuves).
- **Guided Mode** : 7 étapes (assujettissement → données → deadlines → plan → CEE → preuves → M&V). Bandeau de progression. Next Best Action. C'est excellent.
- **ObligationsTab** : Score gauge + 3 KPIs (non conformes, à risque, impact EUR) + cartes par obligation avec "Pourquoi concerné" + "Ce qu'il faut faire" + findings par site + workflow (prendre en charge → résolu).
- **RegulatoryTimeline** : Timeline horizontale avec deadlines, couleurs par framework, today marker, tooltip avec pénalités.
- **ExecutionTab** : Par finding, affiche next steps + preuves attendues. Bouton "Créer action".
- **DonneesTab** : Data Quality Gate par site (BLOCKED/WARNING/OK).
- **2 pages conformité** : `ConformitePage.jsx` (V92, principale) ET `CompliancePage.jsx` (legacy, moins bonne). La legacy est toujours accessible.

#### Évaluation UX par composant

| Composant | Explicatif ? | Actionnable ? | Verdict |
|-----------|-------------|---------------|---------|
| ConformitePage + Tabs | **Excellent** | **Excellent** | ✅ Guided workflow, aide contextuelle, drill-down |
| SiteCompliancePage | **Excellent** | **Excellent** | ✅ Readiness gate + M&V tracking |
| CompliancePipelinePage | **Bon** | **Bon** | ✅ Hub portfolio, CTAs vers données manquantes |
| RegulatoryTimeline | **Excellent** | **Bon** | ✅ Communication d'urgence des deadlines |
| ObligationsTab | **Excellent** | **Excellent** | ✅ Pourquoi + quoi faire + progression |
| ExecutionTab | **Excellent** | **Excellent** | ✅ Next steps + preuves attendues par finding |
| PreuvesTab | **Basique** | **Basique** | ⚠️ Juste upload fichier, pas de guidance |
| CompliancePage (legacy) | **Minimal** | **Minimal** | ⚠️ Findings bruts, pas de contexte UX |
| AperPage | **Bon** | **Bon** | ✅ ROI + timeline |

#### HYPOTHÈSES

- L'utilisateur moyen est submergé. 4 onglets + guided mode + timeline + 3 KPIs + cartes obligation + per-finding drill-down. Trop de niveaux pour un non-expert.
- La page legacy (`CompliancePage.jsx`) crée de la confusion si elle est encore dans le menu.
- Le mode Expert montre `rule_id` + `inputs_json` brut — pas adapté même pour un expert. Il faudrait un format lisible.
- Les labels FR sont bons (`complianceLabels.fr.js` couvre ~15 rule_ids avec `title_fr` + `why_fr` + `next_steps` + `expected_proofs`).
- Le lien "Pourquoi suis-je concerné ?" par obligation est un différenciateur fort. Mais il manque "Quelles sont mes options ?" (exemption, modulation, dérogation).

#### DÉCISIONS

- **Conserver** : Guided Mode. ObligationsTab cards. Timeline. Labels FR.
- **Corriger** : Retirer ou masquer la page legacy. Simplifier le premier écran (score + top 3 urgences + timeline suffit). Humaniser le mode Expert (pas de JSON brut).
- **Ajouter** : Section "Vos options" par obligation (exemption possible ? modulation ? dérogation ?). Résumé exécutif imprimable.

---

### ANGLE 6 — ORCHESTRATION OPÉRATIONNELLE

#### FAITS

- `ExecutionTab` crée des actions depuis les findings (via `ActionItem` avec `source_type='compliance'`).
- Workflow OPS : open → ack → resolved → false_positive (pattern partagé avec BillingInsight).
- CEE Pipeline V69 : Work Packages (S/M/L) + Dossier Kanban (6 étapes : devis → engagement → travaux → pv_photos → mv → versement) + M&V.
- L'action model a `due_date`, `priority`, `estimated_gain_eur`, `evidence_required`.

#### HYPOTHÈSES

- Les actions créées sont individuelles, pas groupées par réglementation. Pas de "Pack Décret Tertiaire" avec toutes les étapes.
- Pas de notion de campagne réglementaire (ex: "Campagne OPERAT 2025" avec checklist commune).
- Le lien action → preuve existe (`evidence_required` flag) mais la boucle n'est pas fermée (pas de vérification auto que la preuve a été déposée).

#### DÉCISIONS

- **Conserver** : Le workflow OPS. Le CEE Pipeline. Le lien finding → action.
- **Corriger** : Fermer la boucle action → preuve (vérifier auto le dépôt).
- **Ajouter** : Packs d'actions par réglementation (template). Notion de campagne.

---

### ANGLE 7 — INTÉGRATION AUX AUTRES BRIQUES

#### FAITS

| Brique | Lien avec Conformité | Force |
|--------|---------------------|-------|
| Patrimoine | Site + Batiment alimentent les règles d'assujettissement | ✅ Fort |
| Actions | ComplianceFinding → ActionItem (source_type='compliance') | ✅ Fort |
| Consommation | `annual_kwh_total` sur Site + Data Quality Gate | ⚠️ Moyen |
| Billing | `anomalie_facture` flag + penalty risk roll-up | ⚠️ Faible |
| Achat / Scénarios | Aucun lien direct | ❌ Absent |
| Connecteurs | Data activation nourrit le readiness gate | ⚠️ Indirect |
| Cockpit | Score compliance + risque financier affiché | ✅ Fort |
| Notifications | Pas de canal compliance dédié | ⚠️ Absent |

#### HYPOTHÈSES

- Le lien Conformité → Consommation devrait être le plus fort (le Décret Tertiaire EST une obligation de réduction de consommation). Or `avancement_pct` n'est pas calculé depuis les données de consommation.
- Billing : les pénalités réglementaires ne remontent pas dans le risk assessment billing. Un surcoût réglementaire de 7500€/site devrait apparaître dans l'analyse d'impact.
- Achat : le renouvellement de contrat devrait intégrer les obligations réglementaires (ex: contrat vert pour APER, coefficient d'émission pour DT).

#### DÉCISIONS

- **Corriger** : Calculer `avancement_pct` depuis les données de consommation réelles.
- **Ajouter** : Remontée des pénalités conformité dans le risk billing. Lien Achat → obligations (coefficient énergie verte).

---

### ANGLE 8 — DIFFÉRENCIATION MARCHÉ

#### FAITS — Ce que PROMEOS fait déjà mieux que le marché

1. **Moteur Putile BACS calculé** (pas juste déclaratif) — rare dans les outils conformité
2. **YAML versionné** pour les règles réglementaires — traçabilité
3. **Guided Mode 7 étapes** — aucun concurrent GTB/conformité ne propose ça
4. **Multi-framework unifié** (DT + BACS + APER dans un score unique) — les cabinets traitent séparément
5. **Workflow OPS** sur les findings — pattern billing insight appliqué à la conformité
6. **EFA modeling complet** avec événements de périmètre — niveau expert
7. **OPERAT CSV export** — utilité directe
8. **Data Quality Gate** bloquant — force la complétude avant évaluation

#### Ce qui manque pour dépasser le marché

1. **Pas de benchmark sectoriel** — le score 62/100 ne dit rien sans comparaison
2. **Pas de projection temporelle** — "Où serez-vous en 2030 ?" manque
3. **Pas de simulation** — "Si je rénove le bâtiment A, quel impact sur mon score ?"
4. **Pas d'export comité** — Le DG a besoin d'un one-pager, pas d'un dashboard
5. **Pas de multi-sites agrégé lisible** — Le pipeline existe mais manque de synthèse visuelle

---

## 3. GAP ANALYSIS

| # | Capacité Cible | État Actuel | Gravité Gap | Impact Business | Effort | Priorité ICE |
|---|---------------|-------------|-------------|-----------------|--------|-------------|
| 1 | Moteur d'assujettissement explicable | ✅ Existe (3 moteurs), ⚠️ pas unifié | **Haute** | Crédibilité moteur | M | **9** (I:9 C:9 E:8) |
| 2 | Registre de règles versionné | ✅ YAML v1 existe | Faible | Audit trail | S | 6 |
| 3 | Coffre de preuves réglementaires | ⚠️ Modèle OK, UX minimal | **Haute** | Opposabilité | M | **8** (I:9 C:8 E:7) |
| 4 | Timeline réglementaire multi-sites | ✅ Composant RegulatoryTimeline existe | Faible | Visibilité | S | 5 |
| 5 | Gestion multi-acteurs / responsabilités | ✅ Modélisé (EfaRole, TertiaireResponsibility) | Moyenne | Multi-tenant | M | 6 |
| 6 | BACS readiness engine | ✅ V2 complet | Faible | Déjà fort | S | 4 |
| 7 | APER scanner toiture/parking | ⚠️ Basique (champs Site) | **Moyenne** | Complétude | M | 7 |
| 8 | Lien conformité → actions → conso/facture | ⚠️ Actions OK, conso/facture faibles | **Haute** | Narration produit | L | **8** (I:9 C:7 E:6) |
| 9 | Exports / dossiers / attestations | ⚠️ OPERAT CSV seul | **Haute** | Démonstration valeur | M | **9** (I:10 C:8 E:8) |
| 10 | Pédagogie expert + grand public | ⚠️ Labels FR bons, options manquantes | Moyenne | Adoption | S | 7 |

---

## 4. PLAN D'ACTION PRIORISÉ

---

### NIVEAU A — QUICK WINS VISIBLES (1 à 3 jours)

| # | Action | Effort | Impact | Confiance | Owner | Délai | Dépendances | Comment tester |
|---|--------|--------|--------|-----------|-------|-------|-------------|----------------|
| A1 | **Harmoniser deadline BACS** : aligner frontend `complianceLabels.fr.js` et backend YAMLs sur les dates réglementaires exactes (>290kW: 01/01/2025, 70-290kW: 01/01/2027) | 2h | Haute | Haute | Frontend+Backend | J+1 | Aucune | Vérifier labels + YAML + seeds cohérents |
| A2 | **Retirer/masquer la page legacy** `CompliancePage.jsx` du menu (garder `ConformitePage` seule) | 1h | Haute | Haute | Frontend | J+1 | Aucune | Menu ne montre qu'une entrée Conformité |
| A3 | **Ajouter "Vos options"** par obligation dans ObligationsTab : "Exemption possible", "Modulation", "Dérogation" — contenu statique FR dans `complianceLabels.fr.js` | 4h | Haute | Haute | Frontend+Content | J+2 | Aucune | Chaque carte obligation a section Options |
| A4 | **Surfacer l'audit trail** dans le drawer de finding : afficher `inputs_json` et `params_json` formatés (pas JSON brut) en mode Expert | 3h | Moyenne | Haute | Frontend | J+2 | Aucune | Mode Expert montre tableau inputs lisible |
| A5 | **Base légale visible** : ajouter lien source réglementaire (Légifrance) sur chaque carte obligation. Données déjà dans YAML (`reference` field). | 2h | Haute | Haute | Frontend | J+1 | Aucune | Chaque obligation a lien cliquable |
| A6 | **Pénalités sourçées** : afficher `penalty_basis` et `penalty_source` à côté du montant estimé dans ObligationsTab | 1h | Moyenne | Haute | Frontend | J+1 | Aucune | Montant + source visible |
| A7 | **Externaliser poids scoring** dans `regs.yaml` (45/30/25) au lieu de hardcode dans `compliance_score_service.py` | 2h | Moyenne | Haute | Backend | J+2 | Aucune | Test scoring lit YAML |

---

### NIVEAU B — STRUCTURE PRODUIT (3 à 7 jours)

| # | Action | Effort | Impact | Confiance | Owner | Délai | Dépendances | Comment tester |
|---|--------|--------|--------|-----------|-------|-------|-------------|----------------|
| B1 | **Consolider moteurs** : déprécier `compliance_engine.py`, faire de RegOps le moteur unique, `compliance_rules.py` comme wrapper thin | 3j | Très haute | Moyenne | Backend | J+7 | A1 | Tous endpoints retournent résultats cohérents |
| B2 | **Résumé exécutif imprimable** : ajouter section conformité dans `DossierPrintView.jsx` — score, top 3 urgences, timeline, pénalités | 2j | Haute | Haute | Frontend | J+5 | Aucune | Bouton Dossier inclut conformité |
| B3 | **Calcul trajectoire DT réel** : calculer `avancement_pct` depuis consommations annuelles vs année de référence | 2j | Haute | Moyenne | Backend | J+7 | Données conso existantes | Test: avancement = f(conso) |
| B4 | **Coffre de preuves unifié** : merger `Evidence` et `TertiaireProofArtifact` en un modèle unique avec expiration + alerte | 2j | Haute | Haute | Backend+Frontend | J+7 | Aucune | Upload + expiration visible |
| B5 | **Packs d'actions réglementaires** : template par régulation (ex: "Pack DT" = 5 actions standard, "Pack BACS >290kW" = 3 actions) | 2j | Haute | Haute | Backend+Content | J+5 | Aucune | API retourne packs, UI les propose |
| B6 | **Notifications conformité** : alertes sur deadlines proches (<90j), preuves expirées, score dégradé | 1j | Moyenne | Haute | Backend | J+5 | Aucune | Notifications apparaissent dans le centre |

---

### NIVEAU C — DIFFÉRENCIATION FORTE (7 à 15 jours)

| # | Action | Effort | Impact | Confiance | Owner | Délai | Dépendances | Comment tester |
|---|--------|--------|--------|-----------|-------|-------|-------------|----------------|
| C1 | **Modèle APER dédié** : table `AperAssessment` (miroir BACS), scanner parking/toiture avec PVGIS réel, ROI estimé | 5j | Haute | Moyenne | Backend+Frontend | J+15 | Connecteur PVGIS | Assessment persisté + ROI affiché |
| C2 | **Simulation "What-if"** : "Si je rénove bâtiment X, quel impact sur mon score ?" — recalcul avec paramètres modifiés | 5j | Très haute | Moyenne | Backend+Frontend | J+15 | B1 (moteur unifié) | UI slider → nouveau score |
| C3 | **Export comité** : One-pager PDF par site avec score, obligations, deadlines, actions, preuves manquantes | 3j | Haute | Haute | Backend+Frontend | J+10 | B2 | PDF généré et lisible |
| C4 | **Lien Conformité → Billing** : pénalités réglementaires dans l'analyse d'impact financier | 2j | Haute | Haute | Backend | J+10 | Aucune | Pénalités dans impact decision |
| C5 | **Vue portfolio agrégée** : heat map sites × obligations avec score couleur, tri par urgence | 3j | Haute | Moyenne | Frontend | J+12 | Aucune | Vue synthétique portfolio |

---

### NIVEAU D — FONDATIONS TECHNIQUES (si nécessaires)

| # | Action | Effort | Impact | Confiance | Owner | Délai | Dépendances | Comment tester |
|---|--------|--------|--------|-----------|-------|-------|-------------|----------------|
| D1 | **Validation JSON schemas** : Pydantic models pour `units_json`, `renewal_events_json`, `responsible_party_json` | 2j | Moyenne | Haute | Backend | J+10 | Aucune | Validation auto à l'écriture |
| D2 | **Moteur de statut par obligation** : state machine formelle (draft→evaluated→action_required→in_progress→resolved) | 3j | Moyenne | Moyenne | Backend | J+15 | B1 | State transitions traçées |
| D3 | **Source map réglementaire** : lier chaque règle YAML à l'article de loi exact (ex: "Art. R.174-22 CCH" pour DT scope) | 2j | Haute | Haute | Content+YAML | J+10 | Aucune | Chaque rule_id a article_ref |

---

## 5. PROPOSITIONS D'ÉVOLUTION UI/UX

### Structure de page Conformité idéale (sans tout refaire)

```
┌─────────────────────────────────────────────────┐
│  SCORE 62/100 [C]   ●●●○○  Confiance: Moyenne  │  ← Existant, garder
│  "3 obligations actives · 1 deadline < 90j"     │  ← AJOUTER: résumé 1 ligne
├─────────────────────────────────────────────────┤
│  ⏱ TIMELINE RÉGLEMENTAIRE                       │  ← Existant, remonter en haut
│  ──●────●────●──▼──────●───────●──────→         │
│  2025  2026  2027   2028      2030              │
├─────────────────────────────────────────────────┤
│  🔴 TOP 3 URGENCES                              │  ← AJOUTER: extraction auto
│  1. BACS >290kW — deadline dépassée — 7500€     │
│  2. OPERAT 2025 — non déclaré — 7500€           │
│  3. Parking 8500m² — deadline 07/2028 — ~4000€  │
├─────────────────────────────────────────────────┤
│  ONGLETS: [Obligations] [Données] [Exécution] [Preuves]  ← Existant
│  ... contenu onglets inchangé ...               │
└─────────────────────────────────────────────────┘
```

### Blocs à ajouter

1. **"Résumé 1 ligne"** sous le score — synthèse narrative autogénérée
2. **"Top 3 urgences"** — les 3 findings les plus critiques (par deadline × severity)
3. **"Vos options"** dans chaque carte obligation — exemption, modulation, dérogation
4. **"Base légale"** — lien Légifrance par obligation
5. **"Historique d'évaluation"** — dans le mode Expert, dates + versions + deltas

### Blocs à retirer

1. Page legacy `CompliancePage.jsx` — masquer du menu

### Blocs à regrouper

1. Les preuves (2 modèles) en un flux unifié
2. Le score + la timeline en header fixe (visible dans tous les onglets)

### Wording critique à corriger

| Actuel | Corrigé | Raison |
|--------|---------|--------|
| "À qualifier" | "En attente de données" | Plus clair pour un non-expert |
| "OUT_OF_SCOPE" | "Non assujetti" | FR obligatoire |
| JSON brut en mode Expert | Tableau formaté avec labels FR | Même un expert ne lit pas du JSON |

### Éléments à relier aux autres briques

| Obligation | → Brique liée | Lien à créer |
|-----------|---------------|--------------|
| DT trajectoire | Diagnostic Consommation | Lien direct vers courbe conso du site |
| BACS assessment | Patrimoine | Lien vers bâtiment + système CVC |
| APER surfaces | Patrimoine | Lien vers parking/toiture du site |
| Pénalités totales | Cockpit Impact & Décision | Intégrer dans risk assessment |
| Preuves requises | KB / Memobox | Bridge via `kb_doc_id` |

---

## 6. SPÉCIFICATION V1.1 — BRIQUE CONFORMITÉ

### Objectif

Transformer la brique conformité de "cockpit fragmenté avec 3 moteurs" en **"cockpit réglementaire opérationnel unifié"** où chaque obligation est :
- **explicable** (pourquoi suis-je concerné + base légale + options)
- **traçable** (audit trail + version moteur + preuve)
- **actionnable** (next steps + pack d'actions + deadline)
- **mesurable** (score + tendance + projection)

### Périmètre V1.1

| Framework | Scope V1.1 |
|-----------|-----------|
| Décret Tertiaire | Trajectoire calculée depuis consommations réelles |
| BACS | Inchangé (déjà solide) |
| APER | Modèle dédié + PVGIS intégration |
| CEE P6 | Reste hints (pas d'obligation) |
| Multi-acteurs | Responsabilités exposées dans l'UI |
| Preuves | Modèle unifié avec expiration |
| Exports | Résumé exécutif + dossier comité |

### Composants

| Composant | Type | Rôle |
|-----------|------|------|
| RegOps Engine (unifié) | Backend | Évaluation unique → findings → score |
| Compliance Score Service | Backend | Score 0-100 avec breakdown + tendance |
| Proof Vault | Backend+Frontend | Upload + validation + expiration + alerte |
| Obligation Cards | Frontend | Par obligation : statut + pourquoi + options + actions |
| Timeline | Frontend | Deadlines multi-reg + today marker |
| Top Urgences | Frontend | Top 3 findings critiques autogénéré |
| Résumé Exécutif | Frontend | One-pager pour DossierPrintView |
| Action Packs | Backend+Frontend | Templates d'actions par réglementation |

### Données d'entrée

| Source | Données | Criticité |
|--------|---------|-----------|
| Patrimoine | Sites + Bâtiments + Surfaces + Parking/Toiture | CRITIQUE |
| Connectors + Import | Consommations annuelles (kWh) | HAUTE |
| BACS intake | CVC inventory (système, architecture, puissance) | HAUTE |
| Patrimoine | Surfaces parking/toiture (m², type) | MOYENNE |
| Billing | Contrats + factures | MOYENNE |
| Saisie manuelle | OPERAT status, attestations | BASSE |

### Logique métier

1. **Assujettissement** : DT si `surface_tertiaire ≥ 1000m²`, BACS si `CVC > 70kW` et tertiaire, APER si `parking ≥ 1500m²` outdoor ou `toiture ≥ 500m²`
2. **Évaluation** : RegOps parcourt les règles YAML, produit des findings avec status/severity/deadline
3. **Scoring** : DT×45% + BACS×30% + APER×25% - penalties (max -20pts)
4. **Actions** : findings NOK/UNKNOWN → action recommandée avec deadline + preuve requise
5. **Preuves** : catalogue attendu → dépôt → validation → expiration

### Sorties attendues

- Score composite 0-100 avec grade A-F
- Liste findings par site × obligation avec workflow
- Timeline agrégée
- Résumé exécutif imprimable
- Export OPERAT CSV
- Notifications deadlines
- One-pager comité par site

### Dépendances avec autres briques

| Brique | Type de dépendance | Criticité |
|--------|-------------------|-----------|
| **Patrimoine** | Source de données sites/bâtiments/surfaces | CRITIQUE |
| **Consommation** | Trajectoire DT calculée depuis conso | FORTE |
| **Billing** | Pénalités dans impact financier | MOYENNE |
| **Actions** | Exécution des recommandations | FORTE |
| **Connecteurs** | Data quality gate | MOYENNE |
| **Achat** | Contrat vert / coefficient énergie | FUTURE |

### Points de preuve

- Chaque finding doit pouvoir être prouvé (inputs + params + source YAML + version moteur)
- Chaque obligation doit référencer l'article de loi
- Chaque pénalité doit être sourcée (regs.yaml ou texte officiel)

### Points de vigilance

- Ne pas afficher de deadline fausse (vérifier chaque date contre le texte officiel)
- Ne pas confondre "non évalué" et "conforme"
- Ne pas donner de conseil juridique (toujours "estimation", "recommandation", pas "obligation")
- La consolidation des moteurs doit être progressive (ne pas casser les tests existants)

---

## 7. TOP 5 ACTIONS FINALES

| # | Action | Effort | Owner | Deadline |
|---|--------|--------|-------|----------|
| **1** | **Harmoniser deadlines BACS** + retirer page legacy + ajouter base légale (A1+A2+A5) | 5h | Frontend+YAML | J+1 |
| **2** | **Résumé exécutif conformité** dans DossierPrintView + top 3 urgences en header (A6+B2) | 2j | Frontend | J+5 |
| **3** | **Ajouter "Vos options"** par obligation (exemption/modulation/dérogation) + section audit trail formatée (A3+A4) | 1j | Frontend+Content | J+3 |
| **4** | **Consolider moteurs** : RegOps comme source unique + dépréciation legacy (B1) | 3j | Backend | J+10 |
| **5** | **Export comité + packs d'actions** : one-pager PDF par site + templates d'actions par réglementation (B5+C3) | 3j | Full-stack | J+12 |

---

## ANNEXES

### A. Seuils & Deadlines réglementaires

| Réglementation | Concept | Seuil/Deadline | Notes |
|---------------|---------|----------------|-------|
| **Décret Tertiaire** | Assujettissement | Surface tertiaire ≥ 1000 m² | En-dessous : hors périmètre |
| | Trajectoire 2030 | −40% vs référence | Avancement ≥ 40% requis |
| | Trajectoire 2040 | −50% vs référence | Avancement ≥ 50% requis |
| | Déclaration OPERAT | 2026-09-30 | Pénalité : 7500 €/site |
| | Affichage attestation | 2026-07-01 | Pénalité : 1500 €/site |
| **BACS** | Palier 1 | CVC > 290 kW | Tertiaire uniquement |
| | Deadline palier 1 | 2025-01-01 | GTB/GTC classe B minimum |
| | Palier 2 | CVC 70-290 kW | |
| | Deadline palier 2 | 2027-01-01 | Décret 2023-444 |
| | Cutoff renouvellement | 2023-04-09 | Affecte le trigger reason |
| | Exemption TRI | Retour > 10 ans | Exemption possible |
| | Inspection | 5 ans | Intervalle max entre inspections |
| **APER** | Parking large | > 10 000 m² | Deadline 2026-07-01 |
| | Parking moyen | 1 500–10 000 m² | Deadline 2028-07-01 |
| | Toiture | ≥ 500 m² | Deadline 2028-01-01 |
| | Type parking | Extérieur obligatoire | Couvert/souterrain exempt |

### B. Enums de conformité (exhaustif)

```
StatutConformite: conforme, derogation, a_risque, non_conforme
TypeObligation: decret_tertiaire, bacs, aper
TypeEvidence: audit, facture, certificat, rapport, photo, declaration, attestation_bacs, derogation_bacs
StatutEvidence: valide, en_attente, manquant, expire
RegStatus: compliant, at_risk, non_compliant, unknown, out_of_scope, exemption_possible
InsightStatus: open, ack, resolved, false_positive
EfaStatut: active, closed, draft
EfaRole: proprietaire, locataire, mandataire
DeclarationStatus: draft, prechecked, exported, submitted_simulated
PerimeterEventType: changement_occupant, vacance, renovation_majeure, scission, fusion, changement_usage, autre
CvcSystemType: heating, cooling, ventilation
CvcArchitecture: cascade, network, independent
BacsTriggerReason: threshold_290, threshold_70, renewal, new_construction
InspectionStatus: scheduled, completed, overdue
```

### C. Fichiers clés cartographiés

**Backend — Moteurs** :
- `services/compliance_engine.py` — Legacy engine (snapshots depuis Obligations)
- `services/compliance_rules.py` — YAML pack evaluator → ComplianceFinding
- `services/compliance_score_service.py` — Score unifié 0-100
- `services/compliance_score_trend.py` — Snapshots mensuels
- `regops/engine.py` — RegOps orchestrateur
- `services/bacs_engine.py` — BACS V2 (Putile, TRI, inspections)
- `services/tertiaire_service.py` — EFA qualification + contrôles
- `services/aper_service.py` — APER eligibility + PV estimation

**Backend — Modèles** :
- `models/conformite.py` — Obligation
- `models/compliance_finding.py` — ComplianceFinding
- `models/compliance_score_history.py` — Score History
- `models/compliance_run_batch.py` — Run Batch
- `models/evidence.py` — Evidence
- `models/bacs_models.py` — BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
- `models/tertiaire.py` — EFA + 6 sous-tables
- `models/reg_assessment.py` — RegAssessment cache

**Backend — YAML** :
- `rules/decret_tertiaire_operat_v1.yaml`
- `rules/decret_bacs_v1.yaml`
- `rules/loi_aper_v1.yaml`
- `regops/config/regs.yaml`
- `regulations/bacs/v2.yaml`

**Frontend — Pages** :
- `pages/ConformitePage.jsx` — Page principale V92 (4 onglets + guided mode)
- `pages/CompliancePage.jsx` — Legacy (à masquer)
- `pages/SiteCompliancePage.jsx` — Détail site (readiness + CEE + M&V)
- `pages/CompliancePipelinePage.jsx` — Pipeline portfolio
- `pages/AperPage.jsx` — APER dédié

**Frontend — Onglets** :
- `pages/conformite-tabs/ObligationsTab.jsx`
- `pages/conformite-tabs/DonneesTab.jsx`
- `pages/conformite-tabs/ExecutionTab.jsx`
- `pages/conformite-tabs/PreuvesTab.jsx`

**Frontend — Modèles** :
- `models/guidedModeModel.js` — 7 étapes guided workflow
- `models/dataReadinessModel.js` — Data quality gates
- `models/complianceSignalsContract.js` — Type contract
- `domain/compliance/complianceLabels.fr.js` — Labels FR (15 rules)

---

*Fin de l'audit. Aucun code modifié. Prêt à exécuter le plan sur instruction.*
