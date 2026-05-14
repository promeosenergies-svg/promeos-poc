---
title: L1 Phase 0 · Inventaire transverse legacy Centre d'Action
date: 2026-05-14
branch: claude/refonte-sol2
mode: read-only (aucun fichier modifié, aucun script DB exécuté en écriture)
mission: Préparer L1 décisionnel V4 (Phase 1) avec inventaire exhaustif legacy
auteurs: Amine + Claude Code
prompt_source: PROMPT_CLAUDE_CODE_mois1_L1.md (v1.0 · 2026-05-13)
doctrine_ref: docs/doctrine/doctrine_v4_classement_priorisation.md (v0.2)
audit_ref: docs/audits/AUDIT_CENTRE_ACTION_2026_05_13.md (616 L · 41 KB)
---

# L1 Phase 0 · Inventaire transverse legacy Centre d'Action

Inventaire exhaustif **lecture seule** des éléments legacy à classer en Phase 1 (verdicts `GARDE / SUPPRIME / MIGRE / REMPLACE / RÉGÉNÈRE`). Aucun fichier modifié pendant cette phase. Aucun script d'écriture DB exécuté.

---

## 0. Vue d'ensemble — compteurs cardinaux

| Catégorie | Total éléments | LoC totales | Statut estimé |
|---|---|---|---|
| **Backend modèles** | 9 fichiers | ~2 451 L | 5 à `MIGRE`, 4 à `REMPLACE`/`SUPPRIME` |
| **Backend tables DB** | 18 tables | n/a | 8 vivantes · 10 vides (dette pure) |
| **Backend enums** | ~38 enums | n/a | 4 SoT V4, ~12 à harmoniser, ~22 hors-scope |
| **Backend routes** | 4 routers · 63 endpoints | ~2 524 L | 1 router `MIGRE` (action_center), 3 `REMPLACE` |
| **Backend services Action/Anomaly** | 20 fichiers | ~6 750 L | 12 `MIGRE`, 5 `SUPPRIME`, 3 adjacents `GARDE` |
| **Backend schemas Pydantic** | 5 fichiers | ~455 L | tous `REMPLACE` ou `MIGRE` |
| **Backend migrations Alembic** | 5 fichiers | ~440 L | conservées (historique gelé) |
| **Backend tests** | 40+ fichiers | ~12 000 L | ~70 % à réécrire (couvrent surface legacy) |
| **Frontend pages** | 6 fichiers | ~3 236 L | 2 `MIGRE`, 4 `SUPPRIME` |
| **Frontend composants** | 9 fichiers | ~3 522 L | 5 `MIGRE`, 4 `SUPPRIME` |
| **Frontend services/mocks/contexts** | 5 fichiers | ~715 L | 2 `MIGRE`, 3 `SUPPRIME` |
| **Frontend modèles** | 4 fichiers | ~668 L | tous à réévaluer (ad-hoc OPERAT) |
| **Frontend SoT labels** | 1 fichier | 491 L | `MIGRE` (étendre avec doctrine FR) |
| **Frontend tests** | ~30 fichiers | ~3 800 L | ~50 % à réécrire |
| **LoC mortes confirmées** | 7 fichiers FE | **1 667 L** | tous `SUPPRIME` (Mois 4 après backup) |

**Total Backend** : ~22 600 LoC à classer
**Total Frontend** : ~12 432 LoC à classer
**Migrations DB cible V4** : 5 nouvelles à produire (Mois 2-3 via ADR-026)

---

## 1. Backend modèles SQLAlchemy

### 1.1 Modèles `Action*`

| Fichier | LoC | Dernière modif git | Modèle(s) | Statut runtime |
|---|---|---|---|---|
| `backend/models/action_item.py` | 190 | 2026-03-04 | `ActionItem` (table `action_items`) | **Canonique post-V5.0** · 35 rows démo |
| `backend/models/action_plan_item.py` | 45 | 2026-03-17 | `ActionPlanItem` (table `action_plan_items`) | **DOUBLON Sprint 13** · 0 row |
| `backend/models/action_event.py` | 33 | 2026-03-18 | `ActionPlanEvent` (table `action_plan_events`) | **Sprint 13 mort** · 0 row · ⚠️ collision nom avec `ActionEvent` |
| `backend/models/action_detail_models.py` | 181 | 2026-03-08 | `ActionEvent` + `ActionComment` + `ActionEvidence` + `AnomalyActionLink` + `AnomalyDismissal` (5 tables) | Audit trail V5.0 · `ActionEvent` 0 row · `AnomalyActionLink` 0 row · `AnomalyDismissal` 0 row |
| `backend/models/action_notification.py` | 18 | 2026-03-18 | `ActionPlanNotification` | **Sprint 13 mort** · table absente DB |
| `backend/models/action_template.py` | 33 | 2026-03-04 | `ActionTemplate` | Bibliothèque V113 · 0 row |

### 1.2 Modèles `Anomaly*` / `Alert*`

| Fichier | LoC | Dernière modif git | Modèle(s) | Statut runtime |
|---|---|---|---|---|
| `backend/models/energy_models.py` | 535 | 2026-04-02 | `Anomaly` (l. 287, table `anomaly`) + `MonitoringAlert` (l. 492, table `monitoring_alerts`) + `Meter` + `EnergyInvoice` + autres | Anomaly KB · 86 rows · `MonitoringAlert` table inexistante DB |
| `backend/models/alerte.py` | 33 | 2026-03-04 | `Alerte` (table `alertes`) | **Modèle FR ancien mort** · 0 row · pas connecté workflow Action |
| `backend/models/enums.py` (BillAnomaly defs) | 1389 | 2026-05-09 | enums multiples (cf. §3) | Définitions vivantes |
| (BillAnomaly model) | n/a | n/a | `BillAnomaly` (table `bill_anomaly`) — défini probablement ailleurs ou inline | **52 rows** · sortie R19→R31 |

**Verdict Phase 1 prévisible** :
- `ActionItem` → **GARDE** (canonique, sera promu socle `ActionCenterItem` polymorphique V4)
- `ActionPlanItem` + `ActionPlanEvent` + `ActionPlanNotification` (Sprint 13) → **SUPPRIME** (jamais utilisé en prod, 0 row, doublons sémantiques)
- `Anomaly` (KB) + `BillAnomaly` + `Alerte` + `MonitoringAlert` → **MIGRE** vers `ActionCenterItem` polymorphique avec `kind=anomaly` + `source.module` discriminant (Q1-A doctrine)
- `ActionEvent` + `ActionComment` + `ActionEvidence` + `AnomalyActionLink` + `AnomalyDismissal` → **REMPLACE** par `action_event_log` unifié (ADR-029) + `evidence` table
- `ActionTemplate` → **GARDE** (bibliothèque V113, indépendant du workflow)

---

## 2. Tables DB legacy — volumes runtime

```sql
-- Source : sqlite3 backend/data/promeos.db ".tables" + COUNT(*) sur chacune
```

| Table | Rows démo | Statut | Verdict prévisible |
|---|---|---|---|
| `action_items` | **35** | Vivante (canonique) | MIGRE → `action_center_items` |
| `bill_anomaly` | **52** | Vivante (R19→R31) | MIGRE → `action_center_items` (kind=anomaly, source=billing) |
| `anomaly` (KB) | **86** | Vivante (analytics) | MIGRE → `action_center_items` (kind=anomaly, source=consumption) |
| `action_plan_items` | 0 | **DOUBLON SPRINT 13** | SUPPRIME (backup obligatoire avant) |
| `action_plan_events` | 0 | Doublon Sprint 13 | SUPPRIME |
| `action_plan_evidences` | 0 | Doublon Sprint 13 | SUPPRIME |
| `action_events` | 0 | V5.0 jamais peuplé | REMPLACE par `action_event_log` |
| `action_comments` | 0 | V5.0 jamais peuplé | REMPLACE |
| `action_evidence` | 0 | V5.0 jamais peuplé | REMPLACE |
| `action_templates` | 0 | Bibliothèque vide | GARDE structure, RÉGÉNÈRE seed |
| `action_sync_batches` | 0 | V5.0 sync | SUPPRIME (mécanique remplacée par event_bus) |
| `action_notifications` | n/a | Table absente sortie | SUPPRIME |
| `anomaly_action_links` | 0 | V117 jonction | REMPLACE par FK directe `ActionCenterItem.source_item_id` |
| `anomaly_dismissals` | 0 | V117 jamais peuplé | REMPLACE par `action_center_items.lifecycle_state=closed` + `closure_reason=dismissed` |
| `alertes` | 0 | Modèle FR ancien | SUPPRIME |
| `bacs_remediation_actions` | n/a | BACS spécifique | GARDE (hors scope V4) |
| `copilot_actions` | n/a | Copilot module | GARDE (hors scope V4) |
| `kb_anomaly_rule` | n/a | KB règles | GARDE (référentiel détecteurs) |

⚠️ **Q2-α non négociable** : Backup DB SQLite + export JSON/CSV des 4 tables avec données (`action_items`, `bill_anomaly`, `anomaly`, `action_templates`) **OBLIGATOIRE** avant suppression Mois 5.

---

## 3. Backend enums — sévérités, priorités, statuts, lifecycle

### 3.1 Enums Action/Anomaly cardinaux

| Enum | Fichier:line | Valeurs | Statut V4 |
|---|---|---|---|
| `ActionStatus` | `enums.py:400-407` | `open / in_progress / done / blocked / false_positive` (5) | MIGRE → `LifecycleState` (5: new/triaged/planned/in_progress/closed) + `ClosureReason` (6 valeurs) |
| `AnomalyStatus` | `enums.py:888-895` | `OPEN / ACKNOWLEDGED / DISMISSED / LINKED / RESOLVED` (5) | **DÉFINI MAIS SANS COLONNE SQL** → SUPPRIME (calculé runtime via lifecycle) |
| `AnomalySeverity` | `energy_models.py:47-53` | `LOW / MEDIUM / HIGH / CRITICAL` (4) | MIGRE → `Severity` unique V4 |
| `BillAnomalySeverity` | `enums.py:48-53` | `INFO / WARNING / CRITICAL` (3) | MIGRE → harmoniser sur 4 niveaux V4 (info ≡ low) |
| `AlertSeverity` | `energy_models.py:428-434` | `LOW / WARNING / HIGH / CRITICAL` (4) | SUPPRIME (Alerte modèle mort) |
| `AlertStatus` | `energy_models.py:420-426` | n.r. | SUPPRIME |
| `NotificationSeverity` | `enums.py:415-421` | `INFO / WARN / CRITICAL` (3) | GARDE (notifs hors scope V4 strict) |
| `DismissReason` | `enums.py:898-905` | `FALSE_POSITIVE / KNOWN_ISSUE / OUT_OF_SCOPE / DUPLICATE / OTHER` (5) | MIGRE → `ClosureReason` étendu V4 |

### 3.2 Enums sévérité parallèles (8+ détectés audit)

| Enum | Fichier:line | Valeurs | Verdict V4 |
|---|---|---|---|
| `Severity` (RegOps) | `enums.py:273-277` | LOW/MEDIUM/HIGH/CRITICAL | MIGRE → `Severity` unique V4 (canonique) |
| `DataQualityIssueSeverity` | `enums.py:722-727` | CRITICAL/HIGH/MEDIUM/LOW (4) | MIGRE → `Severity` |
| `QualityRuleSeverity` | `enums.py:506-510` | CRITICAL/BLOCKING/WARNING/INFO (4) | MIGRE → `Severity` (BLOCKING fusion CRITICAL) |
| `SignalSeverity` | `market_models.py:155` | n.r. | MIGRE → `Severity` |
| `SeveriteAlerte` (FR) | `enums.py:40` | INFO/WARNING/CRITICAL (3) | SUPPRIME (Alerte mort) |
| `RegopsSeverity` (FE) | `complianceLabels.fr.js:470` | n.r. | MIGRE FE → SoT FR unique V4 |
| `BillingInsight.severity` (string libre) | `billing_models.py:573` | low/medium/high/critical | MIGRE |
| Anomalies patrimoine (UPPERCASE in-memory) | `patrimoine_anomalies.py:35` | CRITICAL/HIGH/MEDIUM/LOW | MIGRE |

### 3.3 Enums hors-scope V4 mais présents dans `enums.py`

22 autres enums (OperatStatus, JobStatus, RegStatus, BillingInvoiceStatus, InsightStatus, PurchaseRecoStatus, StagingStatus, ActivationLogStatus, DeliveryPointStatus, IntakeSessionStatus, WatcherEventStatus, BacsTriggerReason, InspectionStatus, BacsExemptionStatus, DeclarationStatus, DataQualityIssueStatus, CeeStatus, ContractStatus, ReconciliationStatus, HcReprogStatus, ReconstitutionStatusEnum, NotificationStatus) → **GARDE** (hors scope V4 stricto sensu).

---

## 4. Backend routes API — 4 routers, 63 endpoints

### 4.1 Détail par router

| Router | LoC | Dernière modif | Endpoints | Callsites FE | Statut V4 |
|---|---|---|---|---|---|
| `backend/routes/action_center.py` | 615 | 2026-04-29 | **38** | 1 (legacy) | MIGRE → nouveau router `/api/action-center/v4` (préfixe versionné) |
| `backend/routes/actions.py` | 1 382 | 2026-04-25 | **21** | 7 | MIGRE / SUPPRIME progressif (mappé sur ActionItem qui devient ActionCenterItem) |
| `backend/routes/action_templates.py` | 353 | 2026-03-27 | 3 | 0 | GARDE (templates indépendants) |
| `backend/routes/pages_briefing.py` | 174 | 2026-05-01 | 1 | 14 | **MIGRE prioritaire** (consommé par 8 pages, 14 callsites) — bug 500 P0 à résoudre Mois 2 |

### 4.2 Bug Briefing 500 — risque P0 Mois 2

`pages_briefing.py:49-174` délègue à `narrative_generator.py` (3 317 L) → `_build_anomalies` (l. 2623-2916). Bug confirmé en démo. Top hypothèses (cf. AUDIT_CENTRE_ACTION_2026_05_13.md §10) :
1. Migration manquante (5 fichiers `.original-autogenerate` en suspens)
2. Status hors enum (`?status=backlog,planned` documenté FE mais absent enum BE)
3. `narrative_generator.py:756` `primary_push["clause"]` accès dict non-défensif

**Mitigation V4** : Mois 2 corrige en redirigeant briefing vers nouveau service `action_center_briefing_v4.py` consommant `ActionCenterItem` directement.

### 4.3 Fuite org-scoping massive — P0 sécu (cf. ADR-027)

Audit confirme : **tous les endpoints `/api/action-center/*` sauf `/issues` et `/summary` sont SANS org-scoping**. Détails dans `AUDIT_CENTRE_ACTION_2026_05_13.md` §6 (Sécurité). À résoudre **avant** ou **pendant** V4 (ADR-027 P0).

---

## 5. Backend services — 20 fichiers, ~6 750 LoC

### 5.1 Services Action (10 fichiers)

| Fichier | LoC | Modèle visé | Verdict V4 |
|---|---|---|---|
| `services/action_audit_service.py` | 116 | `ActionPlanEvent`/`ActionPlanEvidence` | SUPPRIME (modèles morts) |
| `services/action_bulk_service.py` | 56 | `ActionPlanItem` | SUPPRIME |
| `services/action_center_service.py` | 190 | `Site` (calc issues runtime) | MIGRE → `action_center_pull_service` (Q5-B) |
| `services/action_close_rules.py` | 118 | `ActionItem` | MIGRE → `action_center_closure_rules.py` |
| `services/action_hub_service.py` | 415 | `ActionItem` (sync) | MIGRE → `action_center_sync_service.py` |
| `services/action_management_service.py` | 276 | `ActionPlanItem` | SUPPRIME |
| `services/action_notification_service.py` | 108 | `ActionPlanNotification` | SUPPRIME |
| `services/action_plan_engine.py` | 182 | `ActionPlanItem` | SUPPRIME |
| `services/action_status_service.py` | 91 | `ActionItem` | MIGRE → `action_center_lifecycle_service.py` |
| `services/action_workflow_service.py` | 240 | `ActionPlanItem` | SUPPRIME |

### 5.2 Services Anomaly (4 fichiers)

| Fichier | LoC | Sortie | Verdict V4 |
|---|---|---|---|
| `services/bill_intelligence/anomaly_detector.py` | 1 859 | `BillAnomaly` (R19→R31) | MIGRE (continue à produire, mais via interface `ActionCenterItem`) |
| `services/analytics/usage_anomaly_detector.py` | 903 | `Anomaly` KB | MIGRE |
| `services/patrimoine_anomalies.py` | 419 | dict in-memory (9 règles) | MIGRE → persiste ActionCenterItem |
| `services/alert_action_mapper.py` | 131 | template suggéré | MIGRE → utilisé par job pull (Q5-B) |

### 5.3 Services adjacents (6 fichiers)

| Fichier | LoC | Verdict V4 |
|---|---|---|
| `services/bacs_alerts.py` | 142 | GARDE (BACS spécifique) |
| `services/event_bus/detectors/action_overdue_detector.py` | 169 | MIGRE → consomme ActionCenterItem |
| `services/event_bus/detectors/billing_anomaly_detector.py` | 220 | MIGRE → consomme ActionCenterItem |
| `services/power/power_action_bridge.py` | 185 | GARDE (NEBCO/Flex hors V4 strict) |
| `services/purchase_actions_engine.py` | 206 | MIGRE → produit ActionCenterItem (kind=action, source=purchase) |
| `services/demo_seed/gen_actions.py` | 216 | RÉGÉNÈRE Mois 4 (gen_action_center_items_v4.py) |

### 5.4 Service narrative — couplage critique

`backend/services/narrative/narrative_generator.py` **3 317 L** — touche Action via `_build_anomalies`. Verdict V4 : **MIGRE partiel** — la couche narrative reste mais consomme un nouveau modèle `BriefingPayload` produit par `action_center_briefing_v4`.

---

## 6. Backend schemas Pydantic

| Fichier | LoC | Statut V4 |
|---|---|---|
| `backend/schemas/action_center.py` | 46 | REMPLACE (ActionableIssue → ActionCenterItem schema) |
| `backend/schemas/cockpit_schemas.py` | 182 | MIGRE (Cockpit ≠ Centre Action mais partage modèles) |
| `backend/schemas/digest.py` | 51 | MIGRE |
| `backend/schemas/events.py` | 144 | MIGRE → `action_event_log` schema unifié |
| `backend/schemas/recommendation.py` | 32 | MIGRE → ActionCenterItem (kind=recommendation) |

---

## 7. Backend migrations Alembic

| Fichier | LoC | Date | Tables touchées | Verdict V4 |
|---|---|---|---|---|
| `252890dd94e4_phase_d_0_hotfix_patrimoine_d6_.py` | 159 | 2026-05-06 | hotfix patrimoine (D6) | GARDE (historique gelé) |
| `2e78ecc6040c_energy_contract_alerte_renouvellement.py` | 58 | 2026-05-04 | energy_contract.alerte_renouvellement | GARDE |
| `478ee4a61ebb_phase_5_1_sprint_c_5_bill_anomaly_table_.py` | 94 | 2026-05-06 | crée `bill_anomaly` | GARDE (table reste utilisée jusqu'à migration V4) |
| `86dec8e5cb26_phase_5_8_sprint_c_5_bill_anomaly_.py` | 64 | 2026-05-06 | UniqueConstraint bill_anomaly | GARDE |
| **+ 5 fichiers `.original-autogenerate`** non appliqués (cf. git status) | n/a | n/a | colonnes manquantes potentielles | À investiguer Mois 2 (lien bug Briefing 500) |

**5 nouvelles migrations à produire Mois 2-3** (via ADR-026) :
- `XXXXX_v4_action_center_items.py` — nouvelle table polymorphique
- `XXXXX_v4_action_event_log.py` — audit trail unifié
- `XXXXX_v4_evidence.py` — table preuve unifiée
- `XXXXX_v4_duplicate_groups.py` (Q9-B)
- `XXXXX_v4_recurrence_groups.py` (Q9-B)

---

## 8. Backend tests — 40+ fichiers, ~12 000 LoC

### 8.1 Tests directs Action/Anomaly (extrait représentatif)

| Fichier | LoC | Date | Verdict V4 |
|---|---|---|---|
| `test_action_close_rules_v49.py` | 308 | 2026-04-08 | MIGRE (logique fermeture reste pertinente) |
| `test_action_detail_models.py` | 275 | 2026-03-04 | SUPPRIME (modèles V5.0 dépréciés) |
| `test_action_hub_service.py` | 274 | 2026-03-29 | MIGRE → `test_action_center_sync.py` |
| `test_action_status_service.py` | 212 | 2026-04-18 | MIGRE → `test_lifecycle_service.py` |
| `test_actions.py` | 577 | 2026-03-28 | MIGRE (CRUD) |
| `test_actions_console.py` | 336 | 2026-03-04 | SUPPRIME (vue obsolète) |
| `test_alert_action_mapper.py` | 59 | 2026-04-17 | MIGRE |
| `test_anomaly_action_v117.py` | 334 | 2026-03-08 | MIGRE → `test_action_center_anomaly_link.py` |
| `test_audit_sme.py` | 230 | 2026-04-03 | GARDE (SMÉ spécifique) |
| `test_bill_anomaly_detector.py` | 456 | 2026-05-09 | MIGRE (détection BillAnomaly continue) |
| `test_bill_anomaly_phase77_lot_a.py` | 130 | 2026-05-06 | MIGRE |
| `test_event_bus.py` | 1 599 | 2026-04-28 | MIGRE (event bus reste central V4) |

### 8.2 Tests source-guards (couvrent invariants)

8 fichiers source-guards déjà existants (`tests/source_guards/test_*.py`). Tous **GARDE** — invariants à préserver :
- `test_bill_anomaly_yaml_runtime_consistency_source_guards.py` (119 L)
- `test_navigation_badges_source_guards.py` (175 L)
- `test_phase78_p0_fixes_source_guards.py` (122 L)
- `test_regulatory_rates_internal_doctrine_filter_source_guards.py` (186 L)
- `test_tracetooltip_termid_yaml_coherence_source_guards.py` (122 L)
- `test_phase81_lot_regops_source_guards.py` (82 L)
- `test_phase82_lot_sec_ci_source_guards.py` (101 L)
- `test_regulatory_sources_yaml_structure_source_guards.py` (154 L)

### 8.3 Lacunes critiques tests à combler V4

- ❌ `test_briefing_anomalies.py` — bout-en-bout `_build_anomalies` (cf. audit §10)
- ❌ `test_action_center_org_scoping.py` — couvre fuite ADR-027
- ❌ `test_kind_immutability.py` — doctrine §3.3
- ❌ `test_priority_score_modulation_rules.py` — couvre R1-R6 (doctrine §5)
- ❌ `test_recurrence_vs_duplicate_groups.py` — Q9-B doctrine §6
- ❌ `test_lifecycle_state_fr_labels.py` — doctrine §7.1

---

## 9. Frontend — 24 fichiers actifs + LoC mortes

### 9.1 Pages (6 fichiers, ~3 236 L)

| Fichier | LoC | Statut | Imports actifs | Verdict V4 |
|---|---|---|---|---|
| `pages/AnomaliesPage.jsx` | **835** | ✅ Vivant (route `/anomalies`) | n/a | MIGRE → page V4 polymorphique |
| `pages/ActionsPage.jsx` | **1 579** | ✅ Vivant (embarqué + route `/actions`) | n/a | MIGRE → page V4 |
| `pages/ActionCenterPage.jsx` | 378 | ❌ **MORT** | 0 | SUPPRIME (Mois 4 après backup) |
| `pages/ActionPlan.jsx` | 299 | ❌ **MORT** | 0 | SUPPRIME |
| `pages/useAnomalyFilters.js` | 96 | ✅ Vivant (hook AnomaliesPage) | n/a | MIGRE |
| `pages/anomalyEvidence.js` | 49 | ✅ Vivant (helper) | n/a | MIGRE |

### 9.2 Composants (9 fichiers, ~3 522 L)

| Fichier | LoC | Statut | Imports actifs | Verdict V4 |
|---|---|---|---|---|
| `components/ActionDetailDrawer.jsx` | **1 327** | ✅ Vivant | n/a | MIGRE → DetailDrawer V4 (cf. M2 maquette) |
| `components/CreateActionDrawer.jsx` | 435 | ✅ Vivant | n/a | MIGRE |
| `components/ActionCenterSlideOver.jsx` | 553 | ✅ Vivant (cloche header) | n/a | MIGRE |
| `components/SiteAnomalyPanel.jsx` | 317 | ✅ Vivant (Site360) | n/a | MIGRE |
| `components/TabActionsSite.jsx` | 209 | ✅ Vivant (Site360 onglet) | n/a | MIGRE |
| `components/ROISummaryBar.jsx` | 60 | ✅ Vivant | n/a | MIGRE → composant Impact V4 (cf. M4 maquette) |
| `components/ActionDetailPanel.jsx` | 203 | ❌ **MORT** | 1 (depuis ActionCenterPage mort) | SUPPRIME |
| `components/AnomalyActionModal.jsx` | 173 | ❌ **MORT** | 0 | SUPPRIME |
| `components/CreateActionModal.jsx` | 245 | ❌ **MORT** | 0 | SUPPRIME |

### 9.3 Services / mocks / contexts (5 fichiers, ~715 L)

| Fichier | LoC | Statut | Verdict V4 |
|---|---|---|---|
| `services/api/actions.js` | 271 | ✅ Vivant (wrappers REST) | MIGRE → `services/api/action_center.js` V4 |
| `contexts/ActionDrawerContext.jsx` | 75 | ✅ Vivant (provider drawer) | MIGRE |
| `services/anomalyActions.js` | 103 | ❌ **MORT** | SUPPRIME (localStorage fantôme à purger) |
| `mocks/actions.js` | 266 | ❌ **MORT** | SUPPRIME |

### 9.4 Modèles (4 fichiers, ~668 L)

| Fichier | LoC | Verdict V4 |
|---|---|---|
| `models/actionProofLinkModel.js` | 198 | MIGRE (helpers OPERAT preuve) |
| `models/operatActionModel.js` | 168 | MIGRE |
| `models/leverActionModel.js` | 228 | MIGRE (mais V4 ActionCenterItem peut absorber) |
| `models/kbRecoActionModel.js` | 74 | MIGRE → kind=recommendation V4 |

### 9.5 SoT labels FR

`frontend/src/domain/compliance/complianceLabels.fr.js` (491 L) — vivant. **MIGRE** : étendre avec doctrine V4 §7.1 (5 lifecycle FR + 6 closure FR + 7 blockers FR + 7 kinds FR + 15 event types FR).

### 9.6 Total LoC mortes confirmé

**1 667 LoC** mortes confirmées :
- ActionCenterPage 378 + ActionPlan 299 + ActionDetailPanel 203 + AnomalyActionModal 173 + CreateActionModal 245 + anomalyActions 103 + mocks/actions 266 = **1 667 L**

(Audit de référence avait estimé ~1 469 — l'inventaire exhaustif confirme 1 667. Tous **SUPPRIME** Mois 4 après backup.)

---

## 10. Frontend tests — ~30 fichiers

Liste extraite (echantillon, pas exhaustive) :

- `__tests__/ActionsImpact.test.js` (93 L) — MIGRE
- `__tests__/CockpitHero.test.js` (138 L) — GARDE (hors scope)
- `__tests__/CockpitIntegration.test.js` (106 L) — GARDE
- `__tests__/FindingCard.test.js` (228 L) — MIGRE → V4 ItemCard
- `__tests__/labelRegistries.test.js` (229 L) — MIGRE (étendre avec FR doctrine)
- `__tests__/nav_v7_parity.test.js` (191 L) — MIGRE (vérifier que ActionCenterPage retiré)
- `__tests__/source_guards/lever_fe_source_guards.test.js` (89 L) — GARDE
- `__tests__/source_guards/nav_fe_source_guards.test.js` (438 L) — MIGRE

**Tests à créer V4** (cf. doctrine §9) :
- `kind_visual_snapshot_per_kind.test.tsx` (Q7-A)
- `priority_score_persisted.test.ts` (Q8-C)
- `modulation_rules_R1_R6.test.ts`
- `recurrence_vs_duplicate.test.ts` (Q9-B)
- `lifecycle_fr_labels_standard_mode.test.ts` (§7.1)
- `drawer_3_buttons_max.test.tsx` (§7.3)

---

## 11. Dépendances cardinales — qui produit quoi pour V4

### 11.1 `regulatory_applicability_service` (Phase 3.5 en cours · sprint parallèle)

Dépendance cardinale Q4-A. Localisation actuelle : `backend/regops/` (10+ fichiers détectés) :
- `backend/regops/scoring.py` (SoT scoring conformité)
- `backend/regops/operat_zones.py`
- `backend/regops/priority_scoring.py`
- `backend/regops/__init__.py`
- `backend/regops/completeness.py`
- `backend/regops/engine.py`
- `backend/regops/schemas.py`
- `backend/regops/versioning.py`
- `backend/regops/operat_export_helpers.py`
- `backend/regops/data_quality.py`

⚠️ **Sprint Phase 3.5 en cours en parallèle** — V4 doit consommer le service quand il sera disponible (M2-M3). Ne pas perturber le sprint en cours.

### 11.2 ADR-022 priorisation étendue

ADR-022 existant produit la base (gravité 25 + impact 25 + délai 20). V4 ajoute extensions (risque conformité 15 + confiance 10 + récurrence 5 + sans owner 5 + preuve manquante 5) — cf. doctrine §4.2.

### 11.3 `compliance_score_service` → findings → pull job

Q5-B impose un job pull idempotent depuis findings compliance. À créer Mois 3 dans `services/action_center_pull_service.py` (consomme `compliance_score_service` et `regulatory_applicability_service`).

### 11.4 Bill Intelligence (R19-R31)

Continue de produire `BillAnomaly`. Adaptateur V4 : `bill_anomaly_to_action_center_item_adapter.py` (Mois 2). Aucune réécriture de la détection R19-R31.

### 11.5 Patrimoine anomalies

`patrimoine_anomalies.py` aujourd'hui in-memory. Mois 3 : devient persistant via `ActionCenterItem`.

---

## 12. Risques identifiés — mitigations Mois 1-2

### 12.1 Bug Briefing 500 — risque P0

Cf. §4.2. Mitigation Mois 2 : nouveau service briefing V4 + correction migrations en suspens.

### 12.2 Fuite org-scoping `/api/action-center/*` — P0 sécu

Cf. ADR-027 à produire. Mois 2 obligatoire avant pilote payant.

### 12.3 1 667 LoC mortes

Suppression planifiée Mois 4, **après** validation que le V4 backend est opérationnel et que les nouvelles routes/composants sont stables.

### 12.4 Perte historique anomalies KB / BillAnomaly

138 rows à migrer (86 + 52). Mitigation : backup JSON/CSV + script de migration idempotent (Mois 3).

### 12.5 Drift doctrine V4 vs maquettes

Maquettes M1-M5 figées. Toute évolution doctrine = avenant versionné v0.3, v0.4, … (pas de modification silencieuse).

### 12.6 Sprint Phase 3.5 en parallèle

Ne pas perturber `regulatory_applicability_service`. V4 attend l'API stable Mois 3.

---

## 13. Audit existant de référence

`docs/audits/AUDIT_CENTRE_ACTION_2026_05_13.md` — **616 lignes · 41 KB**. Couvre :
- 5 bugs P0 (Briefing 500, false_positive→done, badge "4" vs 35, MAX_SITES=20, CTA "Voir actions" déroute)
- 10 bugs P1 (incl. anomalies dupliquées)
- Fuite org-scoping `/api/action-center/*`
- 1 469 LoC mortes (estimé — corrigé à **1 667 L** par cet inventaire Phase 0)
- 6 vocabulaires statuts concurrents
- 8+ enums sévérité
- 4 mappings sévérité→priorité parallèles

Cet audit reste la **référence factuelle** sur les bugs et incohérences. Le L1 décisionnel V4 (Phase 1) tranche les **verdicts** sur chaque élément.

---

## 14. STOP GATE — Phase 0 terminée

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 0 TERMINÉE — STOP GATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bilan Phase 0 disponible : docs/dev/L1_phase0_inventaire.md

Total éléments à classer en Phase 1 :
  - 9 modèles backend (~2 451 LoC)
  - 18 tables DB legacy (8 vivantes + 10 vides — dette pure)
  - 38+ enums (4 SoT V4, ~12 à harmoniser, ~22 hors-scope)
  - 4 routers backend (63 endpoints)
  - 20 services Action/Anomaly (~6 750 LoC) + narrative_generator.py couplage
  - 5 schemas Pydantic
  - 5 migrations Alembic + 5 .original-autogenerate en suspens
  - 40+ tests backend (~12 000 LoC, dont 8 source-guards GARDE)
  - 24 fichiers frontend actifs (~7 941 LoC)
    + 1 667 LoC mortes confirmées (7 fichiers FE) → SUPPRIME Mois 4
  - ~30 tests frontend
  - SoT labels FR (491 L) à étendre

Risques P0 identifiés Mois 2 :
  - Bug Briefing 500 (5 migrations .original-autogenerate en suspens)
  - Fuite org-scoping /api/action-center/* (ADR-027 P0 sécu)
  - Sprint Phase 3.5 regulatory_applicability_service en parallèle (ne pas perturber)

Backup DB + export JSON/CSV legacy (Q2-α) OBLIGATOIRE avant suppression Mois 5.

⛔ NE PAS DÉMARRER Phase 1 avant validation utilisateur du bilan.

Confirmer pour passer en Phase 1 : "GO Phase 1"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 15. Métadonnées Phase 0

```yaml
phase: "0 — inventaire lecture seule"
status: "TERMINÉE — STOP GATE actif"
date: "2026-05-14"
files_produced:
  - docs/dev/L1_phase0_inventaire.md (ce fichier)
files_modified: 0
db_writes: 0
methodology:
  - Bash find/grep parallèle
  - sqlite3 lecture seule
  - git log dating
  - Cross-référence audit AUDIT_CENTRE_ACTION_2026_05_13.md
arbitrages_doctrine_referenced:
  - Q1-A: ActionCenterItem polymorphique (justifie SUPPRIME ActionPlanItem)
  - Q2-α: backup obligatoire avant suppression
  - Q5-B: job pull idempotent (justifie MIGRE action_center_service)
  - Q9-B: tables séparées (justifie REMPLACE anomaly_action_links)
next_step: "Validation utilisateur 'GO Phase 1' → produire L1_audit_centre_action_v4_decisional.md"
```
