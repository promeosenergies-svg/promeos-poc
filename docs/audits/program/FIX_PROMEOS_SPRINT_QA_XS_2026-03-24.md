# FIX PROMEOS — Sprint QA XS — 24 mars 2026

## 1. Résumé exécutif

3 suites de tests créées, 39 tests au total, 0 bug découvert.

| # | Suite | Tests | Résultat |
|---|---|---|---|
| 1 | `test_purchase_actions_engine.py` | 10 tests | ✅ 10/10 |
| 2 | `test_compliance_coordinator.py` | 5 tests | ✅ 5/5 |
| 3 | `routeHelpers.test.js` (frontend) | 24 tests | ✅ 24/24 |

Les 2 gaps critiques identifiés dans l'audit QA sont fermés.

---

## 2. Tests ajoutés

### Test 1 — purchase_actions_engine.py (10 tests)

**Fichier** : `backend/tests/test_purchase_actions_engine.py`

| Classe | Test | Couvre |
|---|---|---|
| `TestRenewalActions` | `test_renewal_urgent_past_notice` | Préavis passé → type `renewal_urgent`, severity `red`, priority 100 |
| | `test_renewal_soon_within_60_days` | Préavis 31-60j → type `renewal_soon`, severity `orange`, priority 70 |
| | `test_renewal_plan_within_90_days` | Préavis 61-90j → type `renewal_plan`, severity `yellow`, priority 40 |
| | `test_no_action_if_notice_far` | Préavis > 90j → aucune action |
| | `test_expired_contract_skipped` | Contrat expiré → ignoré |
| `TestScenarioActions` | `test_strategy_switch_if_savings_above_5pct` | Savings > 5% → `strategy_switch`, severity `blue`, priority 60 |
| | `test_accept_reco_if_savings_below_5pct` | Savings ≤ 5% → `accept_reco`, severity `blue`, priority 50 |
| | `test_gain_potentiel_computed` | Gain = `current_cost × savings%` (vérifié à ±1€) |
| `TestPriorityAndOrdering` | `test_actions_sorted_by_priority_desc` | Tri décroissant + rank 1-indexed |
| | `test_empty_org_returns_empty` | Org inexistante → 0 actions |

### Test 2 — compliance_coordinator.py (5 tests)

**Fichier** : `backend/tests/test_compliance_coordinator.py`

| Test | Couvre |
|---|---|
| `test_all_4_steps_called` | Les 5 fonctions (recompute, avancement, evaluate, persist, sync) sont toutes appelées |
| `test_avancement_updates_snapshot` | `update_site_avancement()` retourne 42.5 → snapshot mis à jour |
| `test_step2_failure_does_not_block_step3` | Exception RegOps → sync A.2 quand même appelé |
| `test_avancement_none_keeps_original_snapshot` | Avancement incalculable → snapshot garde valeur étape 1 |
| `test_avancement_failure_graceful` | Exception trajectoire → étapes 2+3 exécutées |

### Test 3 — routeHelpers.test.js (24 tests)

**Fichier** : `frontend/src/__tests__/routeHelpers.test.js`

| Describe | Tests | Couvre |
|---|---|---|
| `toConformite()` | 4 | Path de base, tab, site_id, combiné |
| `toRenewals()` | 2 | Path de base, site_id |
| `toSite()` | 3 | Path, tab hash, string id |
| `toConsoExplorer()` | 3 | Path, sites comma-separated, days |
| `toBillIntel()` | 2 | Path, site_id + month |
| `toPatrimoine()` | 2 | Path, site_id |
| `toPurchase()` | 2 | Path, tab |
| `toConsoImport()` | 1 | Path statique |
| `toActionsList()` | 2 | tab=actions, source_type |
| `toConsoDiag()` | 1 | site_id |
| `toMonitoring()` | 1 | site_id |
| `toPurchaseAssistant()` | 1 | step |

---

## 3. Fichiers touchés

| Fichier | Type |
|---|---|
| `backend/tests/test_purchase_actions_engine.py` | **Nouveau** |
| `backend/tests/test_compliance_coordinator.py` | **Nouveau** |
| `frontend/src/__tests__/routeHelpers.test.js` | **Nouveau** |

---

## 4. Risques de régression

| Risque | Probabilité |
|---|---|
| Tests purchase_actions_engine utilisent SQLite in-memory (pattern standard) | Nulle |
| Tests compliance_coordinator mockent les lazy imports (pattern standard) | Nulle |
| Tests route helpers sont des assertions de string (aucun effet de bord) | Nulle |

---

## 5. Bugs découverts

**0 bug découvert.** Les 5 types d'actions, les 4 étapes du coordinator, et les 12 route helpers fonctionnent comme documenté.

---

## 6. Points non traités

| Point | Raison |
|---|---|
| `billing_engine/catalog.py` test unitaire | Sprint QA S |
| `action_hub_service.py` 4 builders isolés | Sprint QA S |
| `usePageData` hook test | Sprint QA S |
| Tests DOM render (jsdom) | Sprint QA M |

---

## 7. Definition of Done

- [x] `purchase_actions_engine.py` : 10 tests couvrant 5 types, priorités, gain, tri, edge cases
- [x] `compliance_coordinator.py` : 5 tests couvrant 4 étapes, avancement, résilience erreurs
- [x] Route helpers : 24 tests couvrant 12 helpers (3 nouveaux + 9 existants)
- [x] 39/39 tests passent
- [x] 0 bug découvert
- [x] 0 fichier Yannick touché
- [x] 0 fichier métier modifié (tests seulement)
