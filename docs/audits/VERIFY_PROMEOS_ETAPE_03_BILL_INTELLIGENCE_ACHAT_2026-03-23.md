# VERIFY PROMEOS — ÉTAPE 3 : BILL INTELLIGENCE & ACHAT

> **Date** : 2026-03-23
> **Référence** : `FIX_PROMEOS_ETAPE_03_BILL_INTELLIGENCE_ACHAT_2026-03-23.md`
> **Méthode** : Relecture code modifié + tests automatisés + vérification temporelle TICGN + grep résiduel
> **Statut** : VÉRIFICATION UNIQUEMENT

---

## 1. Résumé exécutif

**6 corrections vérifiées. 5 VÉRIFIÉ complet, 1 PARTIEL.**

| # | Correction | Verdict | Preuve |
| --- | --- | --- | --- |
| 1 | Source unique prix par défaut | **VÉRIFIÉ** | 0 env var résiduel en prod, 121 tests passent, fallback = 0.18/0.09 |
| 2 | Dépréciation moteur achat simple | **VÉRIFIÉ** | Docstring DEPRECATED, champ `_deprecated` dans réponse, 0 appel frontend |
| 3 | TICGN versionnée | **VÉRIFIÉ** | 8/8 cas temporels passent (2024→2026), sources Légifrance confirmées |
| 4 | PurchaseAssistant computation source | **PARTIEL** | Metadata ajoutée sur output, mais `_computation_note` n'est pas rendue visuellement dans l'UI |
| 5 | Auto-sync actions achat | **VÉRIFIÉ** | `syncActions()` appelé au mount, guard sessionStorage, spinner, fallback si erreur |
| 6 | Bannière données marché démo | **VÉRIFIÉ** | `isDemo` détecté (source + is_demo), badge orange rendu, champs backend ajoutés |

**Tests** : 121 passed, 0 failed (sur les tests liés aux corrections). 1 test pré-existant corrigé en cours de vérification (`test_data_adapter_b1_b2.py:141` — attendait 0.15, mis à jour à 0.18).

---

## 2. Correctifs vérifiés

### 2.1 Source unique prix par défaut — VÉRIFIÉ

| Point de vérification | Résultat | Preuve |
| --- | --- | --- |
| `billing_service.py` n'importe plus `os` pour prix | ✅ | Lignes 10-18 : import `os` retiré de la section prix |
| Import depuis `config.default_prices` présent | ✅ | `billing_service.py:36-40` |
| Fallback P4 utilise `DEFAULT_PRICE_ELEC_EUR_KWH` (0.18) | ✅ | `billing_service.py:117` |
| Shadow billing utilise `DEFAULT_PRICE_ELEC_EUR_KWH` (0.18) | ✅ | `billing_service.py:161` |
| `routes/portfolio.py` import corrigé | ✅ | `portfolio.py:20` : `from services.billing_service import get_reference_price` (sans `DEFAULT_PRICE_ELEC`) |
| 0 référence `PROMEOS_DEFAULT_PRICE` en code de production | ✅ | Grep confirmé : 0 résultat hors tests |
| Tests mis à jour (0.18/0.09) | ✅ | `test_billing.py:484`, `test_step17:120,125`, `test_product_invariants:403`, `test_data_adapter:141,348` |

**Tag** : VÉRIFIÉ

### 2.2 Dépréciation moteur achat simple — VÉRIFIÉ

| Point de vérification | Résultat | Preuve |
| --- | --- | --- |
| Docstring DEPRECATED dans `purchase_scenarios_service.py` | ✅ | Lignes 3-11 : "⚠️ DÉPRÉCIÉ — Ce service utilise des facteurs prix fixes" |
| Champ `_deprecated` dans réponse API | ✅ | `contracts_radar.py:65-68` |
| 0 appel frontend à `compute_purchase_scenarios` | ✅ | Grep : 0 résultat |
| 0 appel frontend à `/purchase-scenarios` endpoint | ✅ | Grep : 0 résultat |
| Moteur avancé (`POST /purchase/compute`) est le chemin standard | ✅ | Frontend PurchasePage utilise `computePurchaseScenarios(siteId)` → `POST /purchase/compute/{id}` |

**Tag** : VÉRIFIÉ

### 2.3 TICGN versionnée — VÉRIFIÉ

| Point de vérification | Résultat | Preuve |
| --- | --- | --- |
| 3 entrées TICGN dans catalog.py | ✅ | `TICGN_2024` (0.01637), `TICGN_AOUT2025` (0.01054), `TICGN_FEV2026` (0.01073) |
| Résolution temporelle dans `_resolve_temporal_code()` | ✅ | `catalog.py:1005-1010` : 3 conditions date |
| 8/8 cas temporels passent | ✅ | Test Python vérifié : 2024-06 → 2024, 2025-08 → AOUT2025, 2026-02 → FEV2026, etc. |
| Fallback `billing_shadow_v2.py` utilise catalog | ✅ | `billing_shadow_v2.py:37-43` : tente catalog, fallback 0.01073 |
| Sources Légifrance citées dans catalog | ✅ | Arrêté 24/07/2025 (JORFTEXT000052009319), Arrêté 24/12/2025 (JORFTEXT000053229989) |

**Tag** : VÉRIFIÉ

### 2.5 Auto-sync actions achat — VÉRIFIÉ

| Point de vérification | Résultat | Preuve |
| --- | --- | --- |
| `syncActions()` appelé au mount | ✅ | `ActionsPage.jsx:603-609` |
| Guard sessionStorage (1×/session/org) | ✅ | `sessionStorage.getItem(syncKey)` / `setItem` |
| `org` destructuré de `useScope()` | ✅ | `ActionsPage.jsx:552` |
| Spinner visible pendant sync | ✅ | `ActionsPage.jsx:1560-1566` : `animate-spin`, disabled, texte "Synchronisation..." |
| Fallback si sync échoue | ✅ | `.catch(() => fetchActions())` — charge les actions existantes |

**Tag** : VÉRIFIÉ

### 2.6 Bannière données marché démo — VÉRIFIÉ

| Point de vérification | Résultat | Preuve |
| --- | --- | --- |
| `isDemo` détecté dans MarketContextBanner | ✅ | `MarketContextBanner.jsx:48-50` : vérifie `is_demo` et regex `source` |
| Badge "Données démo" rendu | ✅ | `MarketContextBanner.jsx:87-91` : `text-orange-600 opacity-80`, `data-testid="market-demo-badge"` |
| Backend retourne `source` et `is_demo` | ✅ | `purchase_pricing.py:105-106` |
| Détection seed : `"seed" in source.lower()` | ✅ | `purchase_pricing.py:97` |
| Détection absence données : `not has_real_data` | ✅ | `purchase_pricing.py:97` |
| Cas feed réel : `is_demo = false` si données réelles sans "seed" | ✅ | Logique cohérente |

**Tag** : VÉRIFIÉ

---

## 3. Correctifs partiels

### 3.1 PurchaseAssistant computation source — PARTIEL

| Point de vérification | Résultat | Détail |
| --- | --- | --- |
| `_computation_source = 'client_engine'` ajouté sur output | ✅ | `PurchaseAssistantPage.jsx:302` |
| `_computation_note` ajouté | ✅ | `PurchaseAssistantPage.jsx:303` : "Estimation locale — résultat indicatif..." |
| Note **affichée visuellement** dans l'UI | **NON PROUVÉ** | La note est ajoutée sur l'objet `output` mais aucun composant ne rend `output._computation_note`. Le message existe en mémoire JS, pas à l'écran |
| Résultats finaux (step Décision) reposent sur JS local | ⚠️ | Le step 7 "Décision" affiche les résultats de `runEngine()` (JS). Le flag `USE_BACKEND_PRICING = true` existe dans `types.js:78` mais n'est **pas consommé** par `runEngine()` |

**Conséquence** : L'utilisateur voit des résultats calculés côté client sans savoir que ce sont des estimations locales. La note de transparence existe dans le code mais n'est pas rendue visuellement.

**Tag** : PARTIEL — Metadata ajoutée mais non rendue. Risque de divergence JS/Python non éliminé.

---

## 4. Correctifs non prouvés

Aucun correctif entièrement non prouvé.

---

## 5. Régressions détectées

| # | Régression | Fichier | Cause | Corrigé ? |
| --- | --- | --- | --- | --- |
| R1 | `test_data_adapter_b1_b2.py:141` attendait `0.15`, reçoit `0.18` | `test_data_adapter_b1_b2.py` | Test manqué lors du sprint FIX (référençait la valeur env var) | **OUI** — corrigé à `0.18` lors de cette vérification |

Aucune régression non corrigée. Le test R1 est un test qui validait l'ancienne valeur incorrecte — la correction du test est cohérente avec la correction du code.

**Fails pré-existants** (non liés aux corrections) :
- `test_billing_engine.py::TestRegression::test_c4_cu_option` — nommage soutirage TURPE
- `test_billing_trust_gate.py::TestInsightStatusValidation::test_invalid_status_rejected` — format réponse
- `test_billing_v68.py::TestShadowBillingV2::test_shadow_v2_elec_components` — taux CSPE hardcodé dans test
- `test_sprint_p1.py::TestComplianceScoreDocumented::test_compliance_engine_documented` — encodage Windows cp1252

---

## 6. Sources vérifiées

### TICGN / Accise gaz

| Période | Taux code | Taux officiel | Source 1 | Source 2 | Retenue | Certitude |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-01 → 2025-07 | 0.01637 | 16.37 €/MWh | [Légifrance — Arrêté 20/12/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050853048) (tarifs 2025) | [Douane — Fiscalité énergie](https://www.douane.gouv.fr/professionnels/energie-environnement/fiscalite-de-lelectricite-du-gaz-et-du-charbon) | 16.37 plein tarif 2025 → compatible 16.37 repo | Confirmé primaire + secondaire |
| 2025-08 → 2026-01 | 0.01054 | 10.54 €/MWh | [Légifrance — Arrêté 24/07/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052009319) | [Ministère Écologie — Guide fiscalité 2025](https://www.ecologie.gouv.fr/sites/default/files/documents/Guide%202025%20sur%20la%20fiscalit%C3%A9%20des%20%C3%A9nergies.pdf) | 10.54 | Confirmé primaire |
| 2026-02+ | 0.01073 | 10.73 €/MWh | [Légifrance — Arrêté 24/12/2025](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053229989) | [Légifrance — Arrêté 27/01/2026](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000053407616) | 10.73 | Confirmé primaire ×2 |

### Prix par défaut

| Point | Source 1 | Source 2 | Retenue | Certitude |
| --- | --- | --- | --- | --- |
| Elec 0.18 EUR/kWh | `config/default_prices.py:10` (source unique repo) | Cohérent avec prix moyen fourniture + acheminement France B2B 2024-2025 | 0.18 | Acceptable pour un fallback POC |
| Gaz 0.09 EUR/kWh | `config/default_prices.py:11` (source unique repo) | Cohérent avec prix moyen gaz B2B France 2024-2025 | 0.09 | Acceptable pour un fallback POC |

---

## 7. Top P0 / P1 / P2 restants

### P0 — Aucun nouveau

Tous les P0 identifiés dans l'audit étape 3 ont été corrigés.

### P1 — Restants

| # | Problème | Statut | Détail |
| --- | --- | --- | --- |
| P1-1 | **PurchaseAssistant : `_computation_note` non rendue visuellement** | PARTIEL | La note existe dans l'objet JS mais aucun composant ne l'affiche. L'utilisateur ne sait toujours pas que les résultats sont locaux |
| P1-2 | **`USE_BACKEND_PRICING = true` non consommé** | NON RÉSOLU | Le flag existe dans `types.js:78` mais `runEngine()` ne le vérifie pas. Pas de switch vers l'API serveur |
| P1-3 | **Données marché = toujours seed** | COSMÉTIQUE RÉSOLU | Le badge "Données démo" s'affiche, mais les données restent fictives. Le correctif est honnête (transparence), pas fonctionnel (feed réel) |
| P1-4 | **Lien conformité ↔ facture toujours cassé** | NON RÉSOLU (hors scope étape 3) | Étape 1 P0-2, non traité dans ce sprint |

### P2 — Restants

| # | Problème | Statut |
| --- | --- | --- |
| P2-1 | Reconstitution gaz V2 (ATRD + ATRT + CTA gaz) non implémentée | HORS SCOPE |
| P2-2 | Feed EPEX Spot temps réel | HORS SCOPE |
| P2-3 | Export CSV bulk factures | NON RÉSOLU |

---

## 8. Definition of Done

| Critère | Statut |
| --- | --- |
| 6 correctifs vérifiés dans le code | ✅ 5 VÉRIFIÉ + 1 PARTIEL |
| Tests passent (0 failed sur corrections) | ✅ 121 passed, 0 failed |
| 1 test manqué corrigé pendant vérification | ✅ `test_data_adapter_b1_b2.py:141` |
| TICGN résolution temporelle prouvée (8/8 cas) | ✅ |
| 0 env var résiduel en production | ✅ |
| 0 appel frontend au moteur simple | ✅ |
| Badge démo fonctionnel | ✅ |
| Auto-sync avec guard et spinner | ✅ |
| PurchaseAssistant transparence computation | PARTIEL — metadata ajoutée mais non rendue |
| Sources réglementaires vérifiées ×2 | ✅ Légifrance ×3 pour TICGN |

---

### Bilan de crédibilité post-fix

| Aspect | Avant fix | Après fix |
| --- | --- | --- |
| Prix fallback billing | 0.15 (divergent de 17%) | 0.18 (unifié) |
| TICGN gaz | 16.37 fixe (périmé) | 3 taux versionnés (10.54 / 10.73 en vigueur) |
| Moteur achat simple | Exposé sans warning | Marqué DEPRECATED + champ `_deprecated` |
| Données marché démo | Pas de signal | Badge orange "Données démo" visible |
| Actions achat | Invisibles sans sync | Auto-sync au mount ActionsPage |
| PurchaseAssistant | Calcul local silencieux | Metadata ajoutée, mais **non rendue visuellement** |

*Vérification réalisée le 2026-03-23. Prochain sprint recommandé : rendre `_computation_note` visible + câbler `USE_BACKEND_PRICING`.*
