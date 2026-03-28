# AUDIT PROMEOS — ÉTAPE 7 : TESTS & QA — 24 mars 2026

> Évaluer si le niveau de sécurité qualité soutient un POC premium à 9.1/10.
> Méthode : inventaire exhaustif backend (224 fichiers, 4107 tests) + frontend (66 fichiers, ~900 tests) + E2E (20 specs Playwright).

---

## 1. Résumé exécutif

**Verdict QA : 8/10** — Couverture exceptionnelle en volume (4107 tests backend, ~900 frontend, 20 E2E). Qualité d'assertions forte (invariants produit, précision numérique). Deux trous critiques backend (catalog TURPE, purchase actions engine). Frontend = tests logiques solides mais 0 test de rendu DOM (choix architectural : env node, pas jsdom).

**Le POC est déjà mieux testé que la plupart des POC B2B.** Les gaps sont ciblés et corrigeables en sprint XS/S.

---

## 2. Forces QA réelles

| Force | Preuve | Impact |
|---|---|---|
| **4107 fonctions test backend** | 224 fichiers, 64 708 lignes de code test | Couverture volume exceptionnelle |
| **10 invariants produit** | `test_product_invariants.py` + `test_invariants.py` (2407L total) : total_sites, risque_financier, hiérarchie conformité, scoping org, facture=somme lignes, shadow billing, FK compteur, staging blocked | Architecture protégée |
| **Assertions numériques fortes** | `assert price_e == 0.18`, `assert score >= 70` — pas de mocks flous | Régression détectée immédiatement |
| **20 specs E2E Playwright** | 8 parcours utilisateur complets (e1-e8) + 4 features (f1-f4) + smoke + a11y | Couverture journeys |
| **886 cas tests frontend** | 37 unit + 9 models + 20 E2E, focus logique métier | Guards structurels solides |
| **Conftest auto-cleanup** | Cache portfolio auto-clear avant chaque test, DEMO_MODE auto | Isolation test fiable |
| **Tests CO₂/émissions** | `test_co2_service.py` + `test_emissions.py` (508L) + `test_step4_emission_factors.py` | Facteurs vérifiés |
| **BACS engine 9 fichiers** | De `test_bacs_engine.py` à `test_bacs_exemption_workflow.py` | Moteur réglementaire le mieux testé |

---

## 3. Faiblesses QA réelles

### 3.1 Deux trous critiques backend

| Gap | Service | Risque | Preuve |
|---|---|---|---|
| **TURPE 7 rates non testés unitairement** | `billing_engine/catalog.py` | Régression silencieuse sur mise à jour tarifaire | Grep `catalog` dans tests/ = 0 test dédié. Couvert uniquement par intégration `test_turpe_calendar.py` (logique calendrier, pas taux) |
| **Purchase actions engine non testé** | `purchase_actions_engine.py` | Actions éphémères cassées sans détection | Grep `purchase_actions_engine` dans tests/ = 0 résultat |

### 3.2 Couverture partielle sur services critiques

| Service | Fichier test | Couverture | Gap |
|---|---|---|---|
| `compliance_coordinator.py` | `test_compliance_contracts.py` (indirect) | PARTIEL | `recompute_site_full()` + `update_site_avancement()` peu couverts |
| `action_hub_service.py` | 2 fichiers indirects | PARTIEL | `sync_actions()` et 4 builders jamais testés en isolation |
| `compliance_score_service.py` | `test_compliance_score_service.py` (342L) | CORRECT | Couverture A.2 acceptable mais pas exhaustive |

### 3.3 Frontend : 0 test de rendu DOM

| Constat | Détail |
|---|---|
| Environnement test | `node` (pas `jsdom` ni `happy-dom`) |
| `render()` / `screen.*` | **0 occurrence** dans les 37 fichiers test |
| Pattern | Tous les tests frontend sont des **guards structurels** : `readFileSync()` → regex/assertion sur le code source |
| Impact | Pas de vérification que les composants se rendent correctement, pas de test d'interaction |
| Mitigation | Les 20 E2E Playwright couvrent les parcours critiques (mais pas les edge cases DOM) |

### 3.4 Hooks et composants récents non testés

| Élément | Test dédié | Statut |
|---|---|---|
| `usePageData` hook | Non | Créé sprint S, aucun test |
| `FreshnessIndicator` composant | Non | Ajouté sprint UX, pas de test |
| `TrustBadge` composant | Non | Ajouté sprint UX, pas de test |
| Route helpers `toConformite/toRenewals/toSite` | Non | Ajoutés sprint S, pas de test |
| Badge aliases `success`/`warning` | Non | Ajoutés sprint UX XS, pas de test |

---

## 4. Zones peu couvertes

### Backend

| Zone | Tests existants | Couverture | Tag |
|---|---|---|---|
| `billing_engine/catalog.py` (taux TURPE 7) | 0 dédié | Intégration seulement | FRAGILE |
| `purchase_actions_engine.py` | 0 | Aucune | FRAGILE |
| `compliance_coordinator.py` | 1 indirect | Partiel | PARTIEL |
| `action_hub_service.py` (4 builders) | 2 indirects | Partiel | PARTIEL |
| `billing_shadow_v2.py` (TICGN) | 1 dédié | Correct | CORRECT |

### Frontend

| Zone | Tests | Couverture | Tag |
|---|---|---|---|
| Rendu DOM composants | 0 | Aucun (env node) | ABSENT |
| `usePageData` hook | 0 | Aucun | ABSENT |
| Route helpers nouveaux | 0 | Aucun | ABSENT |
| Composants UX récents (FreshnessIndicator, TrustBadge) | 0 | Aucun | ABSENT |
| `ScopeContext` switching | Implicite via multi-org | Partiel | PARTIEL |

### E2E

| Zone | Specs | Couverture | Tag |
|---|---|---|---|
| Parcours conformité → facture → action | `e4` + `e7` | Bon | CORRECT |
| Parcours achat complet | `e6` | Correct | CORRECT |
| Upload preuves conformité | 0 dédié | Absent | ABSENT |
| Workflow litige facture | 0 | Absent | ABSENT |
| Responsive < 768px | `f1` (1024px seulement) | Partiel | PARTIEL |

---

## 5. Risques de régression

| Zone sensible | Protections existantes | Risque résiduel |
|---|---|---|
| Scoring conformité A.2 | `test_compliance_score_service.py` + invariants | Faible |
| Shadow billing TURPE 7 | `test_billing_engine.py` (109 tests) | Faible (taux = risque moyen) |
| KPI cockpit | `test_invariants.py` INV-1 à INV-10 | Faible |
| Parcours démo | `golden-demo.spec.js` + `smoke.spec.js` | Faible |
| CO₂ facteurs | `test_step4_emission_factors.py` + `step4_co2_guard.test.js` | Faible |
| BACS Putile | 9 fichiers test BACS | Très faible |
| Actions achat éphémères | **0 test** | **Élevé** |
| Taux TURPE catalog | **0 test unitaire** | **Moyen** |
| Hooks front récents | **0 test** | **Moyen** |

---

## 6. Quick wins QA

### XS (< 1 jour)

| # | Action | Impact | Fichier à créer |
|---|---|---|---|
| 1 | Test unitaire `purchase_actions_engine.py` : 5 types d'actions, priorités, filtres | Ferme gap critique | `tests/test_purchase_actions_engine.py` |
| 2 | Test `compliance_coordinator.py` : `recompute_site_full()` appelle bien les 3 étapes + `update_site_avancement()` | Protège le câblage P0-1 | `tests/test_compliance_coordinator.py` |
| 3 | Test frontend route helpers : `toConformite()`, `toRenewals()`, `toSite()` retournent les bons paths | Protège sprint S | `__tests__/routes.test.js` |

### S (1-3 jours)

| # | Action | Impact |
|---|---|---|
| 4 | Test unitaire `billing_engine/catalog.py` : validation taux TURPE 7 C4/C5, résolution temporelle TICGN | Protège le billing engine |
| 5 | Test `action_hub_service.py` : 4 builders en isolation (compliance, conso, billing, purchase) + sync dedup | Protège l'action hub |
| 6 | Test frontend `usePageData` hook : loading→data, loading→error, refetch, stale guard, unmount guard | Protège le hook |

### M (1-2 semaines)

| # | Action | Impact |
|---|---|---|
| 7 | Ajouter `jsdom` en env test pour 5 composants critiques (FreshnessIndicator, TrustBadge, Badge, ErrorState, EmptyState) | Tests de rendu |
| 8 | E2E : parcours upload preuve conformité → clôture action | Couverture workflow complet |
| 9 | E2E : responsive 768px (mobile) sur cockpit + patrimoine | Couverture mobile |

---

## 7. Plan de correction priorisé

### Sprint QA XS (< 1 jour)
- Points 1-3 ci-dessus
- Gain : ferme les 2 gaps critiques + protège les quick wins récents

### Sprint QA S (1 semaine)
- Points 4-6
- Gain : catalog TURPE + action hub + hook front couverts

### Sprint QA M (2 semaines)
- Points 7-9
- Gain : tests de rendu DOM + E2E workflows complets

---

## 8. Definition of Done

Le QA sera considéré **suffisant pour un POC premium** quand :

1. ✅ `purchase_actions_engine.py` a des tests unitaires (5 types d'actions)
2. ✅ `compliance_coordinator.py` a des tests directs (3 étapes + avancement)
3. ✅ `billing_engine/catalog.py` a des tests de taux (TURPE 7 + TICGN)
4. ✅ `action_hub_service.py` 4 builders testés en isolation
5. ✅ Route helpers front testés
6. ✅ `usePageData` hook testé
7. ✅ 0 gap critique restant

**Score QA cible après corrections : 9/10.**

---

## Annexe — Scorecard QA

| Dimension | Score | Tag |
|---|---|---|
| Volume tests backend (4107) | A+ | SOLIDE |
| Invariants produit (10) | A+ | SOLIDE |
| Qualité assertions | A | SOLIDE |
| BACS engine tests (9 fichiers) | A+ | SOLIDE |
| Billing tests (29 fichiers) | A | SOLIDE |
| E2E Playwright (20 specs) | A- | SOLIDE |
| CO₂/Émissions tests | A | SOLIDE |
| Compliance scoring | B+ | CORRECT |
| Frontend guards (886 cas) | B+ | CORRECT |
| Compliance coordinator | C | PARTIEL |
| Action hub service | C | PARTIEL |
| Purchase actions engine | F | FRAGILE |
| TURPE catalog unit tests | F | FRAGILE |
| Frontend DOM render tests | F | ABSENT |
| Hooks/composants récents | D | ABSENT |

*Audit Tests & QA — 24 mars 2026. Verdict : 8/10, volume exceptionnel, 2 trous critiques ciblés.*
