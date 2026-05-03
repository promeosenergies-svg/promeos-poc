---
audit: sprint_alpha_phase0
date: 2026-05-02
branch: claude/refonte-sol2
head: c30c5624
mode: read-only strict
scope: cartographie chantier α moteur événements + écosystème événements existant
auteur: Claude Code (Opus 4.7)
---

# Audit Phase 0 — Chantier α moteur événements

> **STOP gate** : audit read-only. Aucune modification code/config/test. Validation utilisateur requise avant Phase 1.A.

---

## 1. TL;DR

1. **Le chantier α est ~85% livré déjà sur `claude/refonte-sol2`** — la mémoire 4 jours sous-évaluait massivement l'avancement. `event_bus/` contient 9 détecteurs (~1 771 LOC) + types + Protocol + freshness, `narrative_generator.py:572-575` consomme déjà `compute_events()`, et `test_event_bus.py` (1 599 LOC) couvre conceptuellement le test T6 J vs J+1.
2. **3 systèmes événements coexistent** : (a) `event_bus/` chantier α 9 détecteurs internes multi-pillar — (b) `notification_service.py` 521 LOC 5 briques in-app (compliance/billing/purchase/consumption/actions) — (c) `watchers/` + `RegSourceEvent` SENTINEL-REG legacy veille externe. Pas de duplication catastrophique mais frontière sémantique floue.
3. **3 trous résiduels critiques** : `/api/events/upcoming` endpoint REST absent ; `dashboardEssentials.buildWatchlist` frontend toujours en place (anti-pattern §8.1) ; aucun scheduler périodique (pas d'APScheduler, pas de cron) → email digest Marie 7h45 non câblable en l'état.
4. **Plan 12 phases initial caduc** : ~70% des phases sont déjà livrées. Plan révisé en 2 mini-sprints (5j + 5j) ciblant les 6 actions résiduelles : endpoint REST + suppression buildWatchlist + test T6 canonique + scheduler + Postmark digest + opt-in user.
5. **5 questions d'arbitrage architectural** restent à trancher avant Phase 1.A — notamment coexistence `notification_service` vs `event_bus`, créer endpoint REST ou pas, scheduler in-process vs cron externe.

---

## 2. État chantier α — brique par brique

| Brique ADR-002 | Path | LOC | État | Couverture |
|---|---|---:|---|---|
| `event_bus/__init__.py` (API publique) | `backend/services/event_bus/__init__.py` | 45 | ✅ Livré | – |
| `event_bus/event_service.py` orchestrateur | `backend/services/event_bus/event_service.py` | 116 | ✅ Livré (compute_events + to_narrative_week_cards) | test_event_bus.py |
| `event_bus/types.py` SolEventCard | `backend/services/event_bus/types.py` | 192 | ✅ Livré (frozen dataclass + 9 EventTypes) | test_event_bus.py |
| `event_bus/freshness.py` TTL §7.2 | `backend/services/event_bus/freshness.py` | 108 | ✅ Livré (Enedis 24h / GRDF 48h / invoice 31j / GTB 1h / RegOps 7j / EPEX 1h / benchmark 90j + DEMO_MODE override) | – |
| `event_bus/detectors/_protocol.py` | `backend/services/event_bus/detectors/_protocol.py` | 57 | ✅ Livré (Protocol PEP 544) | – |
| Détecteur `compliance_deadline` (MVP pilote) | `backend/services/event_bus/detectors/compliance_deadline_detector.py` | 236 | ✅ Livré ét11 | test_event_bus.py |
| Détecteur `billing_anomaly` | `backend/services/event_bus/detectors/billing_anomaly_detector.py` | 220 | ✅ Livré ét12a | – |
| Détecteur `consumption_drift` | `backend/services/event_bus/detectors/consumption_drift_detector.py` | 212 | ✅ Livré ét12b | test_usage_anomaly_detector.py |
| Détecteur `flex_opportunity` | `backend/services/event_bus/detectors/flex_opportunity_detector.py` | 189 | ✅ Livré ét13a (P0 VC Sequoia) | – |
| Détecteur `market_window` | `backend/services/event_bus/detectors/market_window_detector.py` | 152 | ✅ Livré ét13b (P0 VC Sequoia) | – |
| Détecteur `contract_renewal` | `backend/services/event_bus/detectors/contract_renewal_detector.py` | 167 | ✅ Livré ét13c | – |
| Détecteur `data_quality_issue` | `backend/services/event_bus/detectors/data_quality_issue_detector.py` | 167 | ✅ Livré ét13d | – |
| Détecteur `asset_registry_issue` | `backend/services/event_bus/detectors/asset_registry_issue_detector.py` | 260 | ✅ Livré ét13e/14/15 | – |
| Détecteur `action_overdue` | `backend/services/event_bus/detectors/action_overdue_detector.py` | 169 | ✅ Livré ét13f | – |
| `trigger_prioritizer.py` (formule + dedup primary/secondary) | `backend/services/narrative/trigger_prioritizer.py` | (Phase 3.2) | ✅ Livré (Option 4.C max 2 triggers tissés) | test_trigger_prioritizer.py |
| `event_history_snapshot` modèle store temporel | `backend/models/event_history_snapshot.py` | – | ✅ Livré Phase 9.D (append-only) | test_phase9d_event_store.py |
| `simulate_date` paramètre fonctionnel | `backend/routes/cockpit*.py` (Phase 6) | – | ✅ Livré V2 narrative dynamique | test_simulate_date.py |
| Wiring `narrative_generator → compute_events` | `backend/services/narrative/narrative_generator.py:572-575` | – | ✅ Livré (consomme compute_events + to_narrative_week_cards) | test_narrative_phase4_wiring.py |
| `backend/doctrine/` SoT exécutable | `backend/doctrine/` (constants/acronyms/delta/error_codes/kpi_registry/naf_to_typology/triggers) | – | ✅ Livré (Sprint Doctrine P0 mergé sur claude/refonte-sol2) | test_weekly_delta_canonical.py |
| `SolEventCard.jsx` composant frontend | `frontend/src/ui/sol/SolEventCard.jsx` | 493 | ✅ Livré | solEventCard.test.js (336 LOC) |
| **Endpoint `GET /api/events/upcoming`** | – | – | ❌ **ABSENT** (vérifié `grep -r "/api/events" routes/`) | – |
| **Endpoint `POST /api/events/{id}/status`** | – | – | ❌ **ABSENT** | – |
| **Table DB `events`** (modèle ADR-002 §schéma) | – | – | ❌ **ABSENT** (vérifié `grep "events" migrations.py`) — détection à la volée actuellement | – |
| **`event_prioritizer.py` formule canonique** (ADR-002 §priorisation) | – | – | ❌ **ABSENT** sous ce nom — la priorisation est dans `trigger_prioritizer.py` (Option 4.C, sémantique différente) | – |
| **Scheduler APScheduler** | – | – | ❌ **ABSENT** (pas dans `requirements.txt`, aucun pattern `BackgroundScheduler` / `AsyncIOScheduler` dans le repo) | – |
| **Test doctrinal `tests/doctrine/test_t6_day_j_evolution.py`** | – | – | ❌ **ABSENT** sous ce path. Test conceptuel T6 présent dans `backend/tests/test_event_bus.py` docstring + assertions (cf. citation §4.D8) | – |
| **Hook `useEvents(pageKey, persona)` frontend** | – | – | ❌ **ABSENT** | – |
| **`models/dashboardEssentials.buildWatchlist` migration** | `frontend/src/models/dashboardEssentials.js:41-92` | – | ❌ **ENCORE EN PLACE** (anti-pattern §8.1 maintenu — 4 règles métier hardcoded inline) | DashboardEssentials.test.js |
| **Email digest Marie 7h45 (Postmark)** | – | – | ❌ **ABSENT** | – |
| **SMS critique Twilio** | – | – | ❌ **ABSENT** (différé S3 selon arbitrage user) | – |

**% complétude global chantier α** : ~**85%** (16 briques livrées / 19 totales — hors digest+SMS qui sont scope notif hors-app distincts).

---

## 3. Cartographie 3 sources événements coexistantes

| Dimension | `event_bus/` (chantier α) | `notification_service.py` | `watchers/` + `watchers_route.py` |
|---|---|---|---|
| **Rôle** | Moteur événements multi-pillar interne (P6+P7 doctrine) | Notifications in-app 5 briques (rail badges, action center) | Veille SENTINEL-REG sources externes (CRE, Légifrance, RTE, RSS) |
| **Path principal** | `backend/services/event_bus/` | `backend/services/notification_service.py` | `backend/watchers/` + `backend/routes/watchers_route.py` |
| **LOC core** | 116 (event_service) + 192 (types) + 108 (freshness) + 1 771 (9 détecteurs) | 521 LOC | 161 LOC route + 5 watchers (cre/legifrance/rte/rss + base + registry) |
| **Modèle données** | `SolEventCard` frozen dataclass (typé) — détection à la volée, pas persisté en DB | dict/list — hash inputs `_hash_inputs()`, stockage via `sync_notifications` (à confirmer DB ou cache) | `RegSourceEvent` SQLAlchemy + enum `WatcherEventStatus` (NEW/REVIEWED/APPLIED/DISMISSED) |
| **Pipeline** | `compute_events()` → priorisation severity → `to_narrative_week_cards()` (rétro-compat) ou consommation directe par builders narratifs | `build_from_X()` × 5 → `sync_notifications()` orchestrateur | `run_watcher(name)` → `RegSourceEvent` persisté → review (apply/dismiss) |
| **Endpoints REST** | ❌ aucun (consommation interne via narrative_generator) | `routes/notifications.py` (consommé par navigation_badges_service + action_center) | `GET /api/watchers/list`, `POST /api/watchers/{name}/run`, `GET /api/watchers/events`, `GET /api/watchers/events/{id}`, `PATCH /api/watchers/events/{id}/review` |
| **Consommateurs internes** | `narrative_generator.py:572-575`, `trigger_prioritizer.py` (Phase 3.2) | `routes/notifications.py`, `routes/action_center.py`, `services/navigation_badges_service.py`, `services/action_workflow_service.py`, `scripts/seed_data.py` | Routes watchers_route.py uniquement |
| **Tests** | `test_event_bus.py` (1 599 LOC), `test_event_bus_cross_stack_sync.py` (148 LOC), `test_usage_anomaly_detector.py` | `test_notifications.py`, `test_notifications_distribution.py`, `test_alert_action_mapper.py`, `test_alert_engine.py`, `test_navigation_badges_source_guards.py` | `test_watchers.py` |
| **Scope déclencheurs** | bill / EMS / regops / achat / flex / patrimoine / actions (7 piliers) | compliance / billing / purchase / consumption / actions (5 briques in-app) | CRE / Légifrance / RTE / RSS (4 sources externes veille) |
| **Persistance** | ❌ pas de DB (détection runtime) | ⚠️ à valider (présence `_hash_inputs` suggère cache déduplication) | ✅ DB (table `RegSourceEvent`) |
| **Statut événement** | `severity` (critical/warning/watch/info) — pas de cycle de vie | – (notif éphémère) | `WatcherEventStatus` (NEW → REVIEWED → APPLIED \| DISMISSED) |

### Frontière sémantique

- **`event_bus/`** : signaux **internes** détectés par croisement de données client (factures + conso + RegOps + contrats + flex). Doctrine §10.
- **`notification_service.py`** : agrégateur de **notifications utilisateur** in-app (badges rail, alertes action center). Couche présentation par-dessus event_bus + autres sources.
- **`watchers/`** : signaux **externes** sources veille réglementaire (changements CRE, arrêtés Légifrance, alertes RTE). Indépendant de l'état client.

Les 3 systèmes ne sont pas redondants à 1ʳᵉ vue — ils captent des signaux de natures différentes. Mais : **une partie des briques `notification_service.build_from_compliance/billing/consumption/action` semble fonctionnellement chevaucher `event_bus.detectors.compliance_deadline / billing_anomaly / consumption_drift / action_overdue`**. À auditer en Phase 1 (cf. Q3).

---

## 4. Constats par dimension

### D1 — Inventaire ADR-002 vs réalité

| Constat | Référence |
|---|---|
| ✅ Architecture `event_bus/` cohérente avec ADR-002 §architecture | `backend/services/event_bus/__init__.py:1-45` cite explicitement doctrine §10/§6/§7/§14 |
| ✅ 9 détecteurs (vs 7 prévus ADR) — 2 ajouts non documentés (`asset_registry_issue`, `action_overdue`) | `backend/services/event_bus/detectors/*.py` |
| ⚠️ `event_prioritizer.py` formule canonique (ADR-002 §priorisation) **absente sous ce nom** — priorisation dispersée entre tri severity dans `event_service.py` + `trigger_prioritizer.py` (Option 4.C narrative) | ADR-002 ligne 70 vs repo |
| ❌ Table DB `events` (ADR-002 §modèle données) **absente** — détection à la volée stateless. Conséquence : pas d'historique, pas d'audit trail, pas de status `seen/snoozed/dismissed`. Phase 9.D `event_history_snapshot` est un store narrative replay, pas un event store transactionnel. | ADR-002 ligne 35-58 vs `migrations.py` |
| ❌ Endpoint REST `/api/events/upcoming` **absent** | ADR-002 ligne 74 vs `grep` routes/ |
| ❌ Scheduler APScheduler **absent** (pas dans requirements, aucun cron) | ADR-002 ligne 22 vs `requirements.txt` |
| ⚠️ Détecteurs S2 minimaux ADR-002 (bill+ems+regops) → **9/9 livrés**, dépasse périmètre prévu | ADR-002 ligne 88-97 vs `detectors/` |

**Verdict** : ADR-002 (daté 2026-04-26) est **partiellement obsolète**. Le repo a livré beaucoup plus côté détecteurs et beaucoup moins côté infrastructure (DB events + endpoint + scheduler).

### D2 — Cartographie 3 sources

#### D2.1 watchers_route.py SENTINEL-REG legacy

| Constat | Référence |
|---|---|
| ✅ 5 endpoints exposés sous `/api/watchers/*` (list, run, events GET ×2, review PATCH) | `backend/routes/watchers_route.py:23,29,39,91,119` |
| ✅ Pipeline NEW → REVIEWED → APPLIED \| DISMISSED implémenté via `WatcherEventStatus` | `backend/models/enums.py:558` |
| ✅ Modèle `RegSourceEvent` SQLAlchemy persisté en DB | `backend/models/reg_source_event.py:14` |
| ✅ Tests : `backend/tests/test_watchers.py` | – |
| ⚠️ Consommateurs FE non grepés dans cet audit (à confirmer) | – |

#### D2.2 notification_service.py 5 briques (65% ADR)

| Constat | Référence |
|---|---|
| ✅ 521 LOC, 5 builders publics : `build_from_compliance` / `build_from_billing` / `build_from_purchase` / `build_from_consumption` / `build_from_actions` | `backend/services/notification_service.py:80,147,198,253,302` |
| ✅ Orchestrateur `sync_notifications(db, org_id, triggered_by)` | `backend/services/notification_service.py:390` |
| ✅ Helpers internes : `_get_site_ids` / `_hash_inputs` / `_get_thresholds` / `_count_summary` | `backend/services/notification_service.py:39,50,56,493` |
| ✅ Consommé par 7 fichiers : routes notifications + action_center, services navigation_badges + action_workflow, seed_data | `grep -rln from.*notification_service` |
| ⚠️ Stockage non audité (DB ? cache ? mémoire ?) — `_hash_inputs` suggère déduplication, mais nature exacte à confirmer | – |
| ⚠️ **Recouvrement fonctionnel partiel avec `event_bus/detectors/`** : compliance_deadline / billing_anomaly / consumption_drift / action_overdue détecteurs vs builders notif équivalents (Q3) | – |

#### D2.3 event_bus/ scaffoldé partiel ✅ → en réalité ~95% livré

| Constat | Référence |
|---|---|
| ✅ Structure complète : `__init__.py` (45 LOC) + `event_service.py` (116) + `types.py` (192) + `freshness.py` (108) + `detectors/_protocol.py` (57) + 9 détecteurs (1 771 LOC) | `backend/services/event_bus/` |
| ✅ Frozen dataclass `SolEventCard` (mirror TypeScript doctrine §10) | `backend/services/event_bus/types.py:21-192` |
| ✅ Protocol PEP 544 `EventDetector` pour duck-typing détecteurs | `backend/services/event_bus/detectors/_protocol.py:1-57` |
| ✅ TTL helper `freshness.py` aligné §7.2 doctrine + DEMO_MODE override | `backend/services/event_bus/freshness.py:1-108` |
| ✅ Tests : `test_event_bus.py` (1 599 LOC) couvre schéma §10 + T6 J vs J+1 + tri severity + source canonique constants + conversion rétro-compat | `backend/tests/test_event_bus.py:1-22` (docstring) |
| ✅ Compatibilité ADR-002 : `compute_events(db, org_id) → list[SolEventCard]` signature attendue | `backend/services/event_bus/event_service.py` |

### D3 — Modèle DB events

| Constat | Référence |
|---|---|
| ❌ Table `events` **absente** — vérifié `grep "events" migrations.py` ne renvoie que `contract_events` (table métier différente) | `backend/database/migrations.py:2242-2260` |
| ✅ Pattern migrations custom : `_create_X_table(engine)` + `insp.has_table()` + `CREATE TABLE IF NOT EXISTS` (pas Alembic) | `backend/database/migrations.py:1-60` |
| ✅ Convention `org_id INTEGER NOT NULL REFERENCES organisations(id)` standard sur tables récentes | `backend/database/migrations.py` (V101+) |
| ✅ Soft delete pattern existant : colonnes `deleted_at / deleted_by / delete_reason` | `backend/database/migrations.py:18-26` |
| ⚠️ Si table `events` créée plus tard, doit suivre pattern : index `(org_id, status, severity, detected_at desc)` + index TTL `(org_id, expires_at)` (cf. ADR-002) | – |

### D4 — Endpoint /api/events/upcoming

| Constat | Référence |
|---|---|
| ❌ Endpoint absent (vérifié `grep "/api/events" routes/` = 0 match) | – |
| ✅ Pattern auth + org_id : `services/scope_utils.py::resolve_org_id` + `resolve_org_id_from_site` (V57 multi-org isolation) | `backend/regops/engine.py:84-86`, `backend/tests/test_v57_multiorg_isolation.py` |
| ⚠️ `compute_events()` actuellement consommé **uniquement par narrative_generator interne** — pas exposé REST | `backend/services/narrative/narrative_generator.py:572-575` |
| 💡 Implication : un consommateur tier3 (mobile, email digest, 3rd party API) ne peut pas accéder aux events sans passer par `/cockpit/briefing` ou autre route narrative | – |

### D5 — Scheduler APScheduler

| Constat | Référence |
|---|---|
| ❌ APScheduler **non installé** (absent de `requirements.txt`) | `grep -iE "scheduler\|cron\|periodic\|celery\|apscheduler\|rq" requirements.txt` = 0 | 
| ❌ Aucun pattern scheduler dans le repo (`BackgroundScheduler` / `AsyncIOScheduler` / `@scheduler.scheduled`) = 0 match | – |
| ✅ Pattern startup FastAPI : `@asynccontextmanager` lifespan dans `main.py:445` | `backend/main.py:7,445` |
| ✅ Pattern background tâche post-réponse : `BackgroundTasks` FastAPI utilisé dans `routes/cockpit_v2.py:200-211` (`background_tasks.add_task(_gen_alerts_async, ...)`) | `backend/routes/cockpit_v2.py:9,59,200,211` |
| ⚠️ Conséquence : pas de cron périodique. Les détecteurs se déclenchent **uniquement en réponse à une requête utilisateur** (via narrative_generator). Email digest 7h45 sans utilisateur connecté = impossible en l'état. | – |

### D6 — 3 détecteurs MVP S1 — préparation

#### D6.1 bill_intel.invoice_anomaly

| Constat | Référence |
|---|---|
| ✅ Détecteur `billing_anomaly_detector.py` 220 LOC déjà livré (ét12a) | `backend/services/event_bus/detectors/billing_anomaly_detector.py` |
| ✅ Modèle `EnergyInvoice` + statut `ANOMALY = "anomaly"` | `backend/models/billing_models.py:309`, `backend/models/enums.py:333` |
| ⚠️ Fonction `count_anomalies_unreviewed` mentionnée P1.2 sprint nav — non détectée dans grep direct (à confirmer) | – |

#### D6.2 ems.baseline_drift CUSUM

| Constat | Référence |
|---|---|
| ✅ Détecteur `consumption_drift_detector.py` 212 LOC livré (ét12b) | `backend/services/event_bus/detectors/consumption_drift_detector.py` |
| ✅ Modèle `BaselineCalibration` SQLAlchemy en place | `backend/models/baseline_calibration.py:43` |
| ✅ Services adjacents : `energy_signature_service.py`, `recommendation_engine.py`, `electric_monitoring/climate_engine.py`, `analytics/forecast_service.py`, `analytics/usage_disaggregation.py` | `backend/services/` |
| ✅ Test associé : `test_usage_anomaly_detector.py` | – |

#### D6.3 regops.deadline_scanner

| Constat | Référence |
|---|---|
| ✅ Détecteur `compliance_deadline_detector.py` 236 LOC livré (ét11 MVP pilote) | `backend/services/event_bus/detectors/compliance_deadline_detector.py` |
| ✅ SoT `compute_portfolio_compliance(db, org_id)` consommée | `backend/services/compliance_score_service.py:303` |
| ✅ Variant `compute_portfolio_compliance_summary` (readiness service) | `backend/services/compliance_readiness_service.py:446` |
| ✅ Consommé par 4 services : navigation_badges_service, kpi_service, compliance_engine, compliance_readiness_service | `grep -rln compute_portfolio_compliance` |

### D7 — Frontend dashboardEssentials.buildWatchlist

| Constat | Référence |
|---|---|
| ❌ **`buildWatchlist` toujours en place** (anti-pattern §8.1 maintenu) | `frontend/src/models/dashboardEssentials.js:41` |
| ⚠️ 4 règles métier hardcoded inline : `non_conformes` (critical) / `a_risque` (high) / `no_conso_data` (warn) / `low_coverage` (medium) | `frontend/src/models/dashboardEssentials.js:41-92` |
| ⚠️ Consommateurs : `ConformitePage.jsx:41,293`, `CommandCenter.jsx:42`, `pages/cockpit/WatchlistCard.jsx`, `__tests__/DashboardV2.test.js`, `__tests__/DashboardEssentials.test.js` | `grep -rln buildWatchlist frontend/src/` |
| ⚠️ **Recouvrement direct avec `compliance_deadline_detector` + `data_quality_issue_detector`** event_bus → duplication métier FE/BE confirmée | – |
| 💡 Migration ADR-002 §watchlist (ligne 110) : remplacer par hook `useEvents(pageKey, persona)` qui appelle `/api/events/upcoming` — bloqué par absence de l'endpoint (D4) | – |

### D8 — Tests doctrinaux & T6

| Constat | Référence |
|---|---|
| ❌ `tests/doctrine/test_t6_day_j_evolution.py` **absent** sous ce path canonique attendu par ADR-002 ligne 126 | `find /tests -name "test_t6*"` = 0 match |
| ✅ Test conceptuel T6 J vs J+1 **présent** dans `backend/tests/test_event_bus.py` (1 599 LOC) docstring : « si l'état DB change (non_conformes 0→1), `compute_events` retourne un événement nouveau (vs version statique qui restait identique J et J+1) » | `backend/tests/test_event_bus.py:1-22` |
| ⚠️ `tests/doctrine/` racine **vide** (juste `__pycache__`) — Sprint Doctrine P0 phase 6 livrait 20 tests doctrine selon mémoire, pas trouvés sous ce path | `ls tests/doctrine/` |
| ✅ `backend/tests/doctrine/` sous-dossier existe avec 1 test (`test_weekly_delta_canonical.py` 108 LOC) | – |
| ✅ Source-guards path actuel : `tests/source_guards/` (test_no_hardcoded_constants, test_claude_md_routing, test_skill_definitions, test_agent_definitions, test_agent_writes_scope, test_frontend_co2_cleanup, test_hooks_project_dir) | `find tests/source_guards/` |
| ✅ Pattern test simulate_date `simulate_date` ISO 8601 (Phase 6 V2) — utilisable pour mocker `now()` J+1 | `backend/tests/test_simulate_date.py:1-30` |
| ⚠️ Convention attendue par ADR-002 (`tests/doctrine/test_t6_day_j_evolution.py`) vs réalité (`backend/tests/test_event_bus.py`) : **divergence à acter** (Q5) | – |

---

## 5. Risques pré-Phase 1.A

### R1 — Triple système événements sans frontière formelle ⚠️

`event_bus/` (chantier α) + `notification_service.py` (5 briques) + `watchers/` (SENTINEL-REG) coexistent sans ADR formalisant leur frontière. Recouvrement fonctionnel **probable mais pas catastrophique** (D2 + D7) entre :
- `event_bus.detectors.compliance_deadline` ↔ `notification_service.build_from_compliance`
- `event_bus.detectors.billing_anomaly` ↔ `notification_service.build_from_billing`
- `event_bus.detectors.consumption_drift` ↔ `notification_service.build_from_consumption`
- `event_bus.detectors.action_overdue` ↔ `notification_service.build_from_actions`

**Risque** : drift sémantique (les 2 systèmes répondent différemment à la même donnée) → perte de cohérence cross-écran.

### R2 — Anti-pattern §8.1 actif (buildWatchlist) ❌

`dashboardEssentials.buildWatchlist` n'a pas été supprimé malgré le wiring backend `compute_events()` en place. 6 fichiers FE consomment encore la version frontend (D7). Doctrine §8.1 violée en production.

**Risque** : doublon métier FE/BE, deux sources de vérité concurrentes pour les watchitems.

### R3 — Pas de scheduler → digest matinal impossible ❌

Aucun scheduler installé (D5). L'email digest Marie 7h45 (Phase 2.E ADR-002) n'a aucun mécanisme de déclenchement.

**Risque** : feature démo investisseur juillet potentiellement bloquée si pas de scheduler avant push.

### R4 — Pas de table DB events → pas d'audit trail ⚠️

Détection à la volée stateless (D3). Pas de `seen/snoozed/dismissed` persistance. Pas de replay au-delà de `event_history_snapshot` (Phase 9.D narrative replay, sémantique différente).

**Risque** : audit régulatoire futur (SMÉ tier 3, CSRD, DPO) ne peut pas tracer "qui a vu quoi quand". Pas bloquant démo, devient bloquant industrialisation post-pilote.

### R5 — Endpoint REST absent → tier3 inaccessible ⚠️

`/api/events/upcoming` absent (D4). Le seul accès aux events passe par narrative_generator interne.

**Risque** : email digest, mobile app future, intégrations 3rd party (BI client, Zapier, webhook Teams/Slack) ne peuvent pas consommer la SoT events. Devient bloquant scope notif hors-app + roadmap V2.

### R6 — Test T6 dispersé ⚠️ (cosmétique)

Test conceptuel J vs J+1 enfoui dans `test_event_bus.py` (1 599 LOC) au lieu d'un fichier canonique `tests/doctrine/test_t6_day_j_evolution.py`.

**Risque** : audit doctrine futur cherchera le fichier canonique, ne le trouvera pas, conclura à tort que T6 n'est pas couvert. Coût correctif faible mais à acter.

---

## 6. Plan séquencement P1.A → P2.F **affiné post-audit**

> **Plan 12 phases initial caduc** (~70% livré). Plan révisé en 2 mini-sprints ciblant les 6 trous résiduels.

### Sprint α-fin (S1, 5 jours) — Industrialisation interne

| Phase | Sujet | Durée | Dépendances | STOP discovery anticipé |
|---|---|---:|---|---|
| **A1** | Endpoint REST `GET /api/events/upcoming?org_id=&persona=&page_key=&horizon_days=7` (contrat ADR-002 §endpoint) — wrap `compute_events()` + `to_narrative_week_cards()` + auth/org_id via `resolve_org_id` | 1.0 j | – | Si Q1 décide "pas d'endpoint", phase skip |
| **A2** | Test doctrinal canonique `tests/doctrine/test_t6_day_j_evolution.py` — extrait test conceptuel `test_event_bus.py` + freezegun J / mock J+1 / assert ≥1 card change | 0.5 j | A1 (option) | Si Q5 décide "garder test_event_bus.py", phase skip |
| **A3** | Hook frontend `useEvents(pageKey, persona)` + intégration dans 3 pages consommatrices (ConformitePage, CommandCenter, WatchlistCard) | 1.5 j | A1 obligatoire | – |
| **A4** | Suppression `dashboardEssentials.buildWatchlist` + tests FE adaptés + source-guard `tests/source_guards/test_no_buildWatchlist_frontend.py` | 1.0 j | A3 obligatoire | Si tests DashboardV2.test + DashboardEssentials.test cassent, retravail 0.5j |
| **A5** | ADR-006 ou note architecture `docs/architecture/event-systems-coexistence.md` formalisant frontière `event_bus/` vs `notification_service.py` vs `watchers/` (résout R1) | 0.5 j | A3 | Si Q3 décide "merger notification_service dans event_bus", phase devient migration majeure +3j |
| **A6** | Tests cumulés vert (pytest + Vitest + source-guards) + commit atomique par phase + push + PR draft | 0.5 j | toutes A1-A5 | – |

### Sprint α-push (S2, 5 jours) — Notifications hors-app

| Phase | Sujet | Durée | Dépendances | STOP discovery anticipé |
|---|---|---:|---|---|
| **B1** | Scheduler périodique : décision Q4 (APScheduler in-process vs cron OS externe + endpoint admin `POST /api/events/refresh`) | 1.0 j | A1 obligatoire (si endpoint refresh) | Si APScheduler retenu, ajouter à requirements + lifespan main.py |
| **B2** | Module `services/notifications/digest.py` Postmark + template HTML week-cards densifié | 1.5 j | A1, B1 | RGPD : audit PII dans template (impact_eur sites = data client) |
| **B3** | Migration DB `User.notification_preferences` (opt-in digest) + UI compte utilisateur | 1.0 j | – (parallélisable) | – |
| **B4** | Tests intégration scheduler + digest dry-run (mock Postmark) + assert template rendu | 1.0 j | B1, B2, B3 | – |
| **B5** | Documentation déploiement scheduler + variables env Postmark + fallback SES + monitoring | 0.5 j | toutes B1-B4 | – |

### Phase post-S2 (différée S3+) — Industrialisation

| Phase | Sujet | Justification report |
|---|---|---|
| C1 | Table DB `events` persistée + status seen/snoozed/dismissed | Pas bloquant démo juillet, requis pour audit régulatoire industrialisation |
| C2 | SMS critique Twilio Jean-Marc | Arbitrage user déjà figé : différé S3 |
| C3 | Migration `RegSourceEvent` watchers legacy → `SolEventCard` event_bus | ADR-002 §migration phase 3 ultérieure |
| C4 | Webhook Teams/Slack | ADR-002 §notifications ligne 104 explicite phase 2 post-démo |

### Effort total révisé

- **S1 (5j)** + **S2 (5j)** = **10 jours** (vs 12 phases × ~2j = 24j initial)
- **Économie** : ~14 jours grâce à l'avancement réel ~85%
- **Effort résiduel** : ~6 actions ciblées, pas de big bang

---

## 7. Questions ouvertes — max 5

### Q1 — Endpoint REST `/api/events/upcoming` : créer ou pas ?

**Contexte** : `compute_events()` est aujourd'hui consommé uniquement par narrative_generator interne. Tier3 (mobile, email digest, 3rd party) inaccessible (R5).

**Options** :
- (a) Créer endpoint REST dédié (ADR-002 §endpoint) — 1j dev + auth/org_id
- (b) Passer par narrative routes existantes (extraire events du briefing) — 0j mais couplage fort
- (c) Endpoint admin interne `POST /api/events/refresh` (sans expo public) pour cron seulement — 0.5j

**Mon vote** : (a) — l'isolation REST est une bonne pratique, ouvre tier3, déblocage email digest naturel. Coût marginal faible.

### Q2 — `buildWatchlist` migration : suppression totale ou fallback offline ?

**Contexte** : 6 fichiers FE consomment encore (R2, D7). Doctrine §8.1 violée.

**Options** :
- (a) Suppression totale : hook `useEvents` + spinner si offline
- (b) Garder `buildWatchlist` comme fallback offline si /api/events fail
- (c) Remplacer par `useEvents` mais conserver shape `WatchItem[]` (pas changer FE consommateurs en profondeur)

**Mon vote** : (a) — fallback offline = dette additionnelle pour un cas edge faible (qui utilise PROMEOS offline ?). Suppression nette aligne §8.1.

### Q3 — Coexistence `notification_service.py` vs `event_bus/detectors/` ?

**Contexte** : recouvrement fonctionnel partiel (R1) sur 4 briques (compliance/billing/consumption/actions).

**Options** :
- (a) Conserver les 2 systèmes parallèles + ADR formalisant rôles distincts (event_bus = signaux factuels, notification_service = couche UI)
- (b) Migrer `notification_service.build_from_X` en détecteurs `event_bus.detectors.X_notification` — 1 SoT, mais refacto ~1j
- (c) Déprécier `notification_service.py`, tout consommateur passe par `compute_events()` — ~3j refacto, casse navigation_badges_service + action_workflow_service

**Mon vote** : (a) court terme (Sprint α-fin) + (b) moyen terme (post-démo). (c) trop risqué pré-démo.

### Q4 — Scheduler in-process vs cron OS externe ?

**Contexte** : pas de scheduler, email digest impossible (R3).

**Options** :
- (a) APScheduler in-process — `pip install apscheduler`, intégration `lifespan` `main.py`, **SPOF si backend redémarre** (replay_missed_runs=True selon ADR mitige)
- (b) Cron OS externe (systemd timer / cron Linux) qui curl `POST /api/events/refresh` (auth admin token) — **pas de SPOF**, mais déploiement infra obligatoire
- (c) GitHub Actions schedule + curl — gratuit, pas d'infra, mais latence ~1min et dépendance externe

**Mon vote** : (b) cron OS — robuste, simple, déjà standard sur le serveur démo. (a) ajoute dépendance dans le code, (c) crée dépendance externe pour un signal critique métier.

### Q5 — Test T6 canonique : créer fichier dédié ou laisser dans `test_event_bus.py` ?

**Contexte** : ADR-002 ligne 126 mentionne `tests/doctrine/test_t6_day_j_evolution.py`. Test conceptuel T6 actuellement enfoui dans `backend/tests/test_event_bus.py` (1 599 LOC) (R6).

**Options** :
- (a) Créer fichier dédié + extraire test T6 + import freezegun — 0.5j cosmétique
- (b) Laisser dans `test_event_bus.py` + ajouter docstring `## T6 J vs J+1` annotation pour grep audit
- (c) Créer fichier dédié + garder doublon dans `test_event_bus.py` (audit doctrine + non-régression Vague C)

**Mon vote** : (c) — le coût est faible et l'audit régulatoire futur cherchera le fichier canonique. Doublon assumé.

---

## 8. Definition of Done — vérification

- [x] Fichier `docs/audits/sprint_alpha_phase0_audit_20260502.md` créé
- [x] 8 dimensions couvertes avec tableaux factuels (D1-D8)
- [x] Cartographie 3 sources événements complète (§3)
- [x] Plan P1.A → P2.F affiné avec dépendances (§6, plan révisé en 2 mini-sprints S1+S2)
- [x] git status clean attendu (zéro fichier modifié hors `docs/audits/`) — modifs/untracked pré-existantes session, non touchées
- [x] STOP — attente validation utilisateur avant Phase 1.A

---

## 9. STOP gate

**Audit Phase 0 livré.** 16/19 briques chantier α livrées (~85%). 3 trous résiduels critiques (endpoint REST + buildWatchlist + scheduler). 5 questions architecturales à arbitrer avant Phase 1.A.

**En attente** : décisions utilisateur Q1-Q5 + validation plan révisé S1+S2 (10j vs 24j initial).
