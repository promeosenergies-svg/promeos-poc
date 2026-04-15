# FIX PROMEOS — Sprint QA S — 24 mars 2026

## 1. Résumé exécutif

3 suites de tests créées, **51 tests** au total, **1 bug réel découvert et corrigé**.

| # | Suite | Tests | Résultat | Bug |
|---|---|---|---|---|
| 1 | `test_billing_catalog.py` | 30 | ✅ 30/30 | 0 |
| 2 | `test_action_hub_service.py` | 8 | ✅ 8/8 | **1 bug corrigé** |
| 3 | `usePageData.test.js` (frontend) | 13 | ✅ 13/13 | 0 |

---

## 2. Bug découvert et corrigé

### `build_actions_from_billing()` ne filtrait pas les insights RESOLVED

**Fichier** : `backend/services/action_hub_service.py:179`

**Avant** :
```python
BillingInsight.insight_status != InsightStatus.FALSE_POSITIVE,
```

**Après** :
```python
BillingInsight.insight_status.notin_([InsightStatus.FALSE_POSITIVE, InsightStatus.RESOLVED]),
```

**Impact** : les insights billing marqués "résolu" continuaient à générer des actions dans le hub. Incohérence : l'utilisateur résout une anomalie facture → elle réapparaît comme action à chaque sync.

**Découverte** : test `test_resolved_insight_excluded` (assertion `len(actions) == 0` échouait avec 1 action générée).

---

## 3. Tests ajoutés

### Test 1 — billing_engine/catalog.py (30 tests)

| Classe | Tests | Couvre |
|---|---|---|
| `TestCatalogStructure` | 14 (7 existence + 7 champs) | Structure des entrées TURPE 7 |
| `TestTurpe7Rates` | 4 | Taux gestion C4 (217.80), C5 (16.80), TVA réduite 5.5% |
| `TestTicgnTemporalResolution` | 5 | 3 périodes TICGN + 2 frontières temporelles |
| `TestAcciseResolution` | 4 | 4 périodes ACCISE ELEC |
| `TestGetRateErrors` | 3 | KeyError code inconnu, get_rate_source, no-date fallback |

### Test 2 — action_hub_service.py (8 tests)

| Classe | Tests | Couvre |
|---|---|---|
| `TestBuildActionsFromCompliance` | 3 | NOK→action, FALSE_POSITIVE exclu, recommended_actions_json parsé (2 actions) |
| `TestBuildActionsFromBilling` | 3 | Insight→action avec gain, RESOLVED exclu, no reco JSON exclu |
| `TestSyncActionsDedup` | 2 | Create→skip idempotent, workflow préservé sur update |

### Test 3 — usePageData.test.js (13 tests)

| Describe | Tests | Couvre |
|---|---|---|
| `structure` | 3 | Export default, params fetcher/deps, return shape |
| `guards` | 3 | mountedRef, fetchIdRef stale guard, error→string |
| `no business logic` | 4 | Pas d'import API/models/domain, pas de Math, pas de EUR/kWh |
| `defaults` | 3 | loading=true, data=null, deps=[] |

---

## 4. Fichiers touchés

| Fichier | Type |
|---|---|
| `backend/tests/test_billing_catalog.py` | **Nouveau** (30 tests) |
| `backend/tests/test_action_hub_service.py` | **Nouveau** (8 tests) |
| `frontend/src/__tests__/usePageData.test.js` | **Nouveau** (13 tests) |
| `backend/services/action_hub_service.py:179` | **Corrigé** (bug RESOLVED non filtré) |

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| Fix `notin_` casse d'autres comportements | Nulle | `notin_` est plus restrictif (exclut plus), pas moins |
| Tests catalog importent `_resolve_temporal_code` (private) | Faible | Fonction stable, testée indirectement depuis V68 |
| Tests action_hub créent des ComplianceFinding/BillingInsight en mémoire | Nulle | Pattern SQLite in-memory standard |

---

## 6. Points non traités

| Point | Raison |
|---|---|
| Tests DOM render (jsdom) | Sprint QA M |
| E2E upload preuve conformité | Sprint QA M |
| E2E responsive 768px | Sprint QA M |
| `build_actions_from_consumption` test isolé | Périmètre Yannick (ConsumptionInsight) |

---

## 7. Definition of Done

- [x] `billing_engine/catalog.py` : 30 tests (structure, taux TURPE 7, TICGN temporel, ACCISE, erreurs)
- [x] `action_hub_service.py` : 8 tests (compliance builder, billing builder, sync dedup, workflow preserve)
- [x] `usePageData` hook : 13 tests (structure, guards, no business logic, defaults)
- [x] Bug `RESOLVED` billing insight corrigé (`notin_` au lieu de `!=`)
- [x] 51/51 tests passent
- [x] 0 fichier Yannick touché
