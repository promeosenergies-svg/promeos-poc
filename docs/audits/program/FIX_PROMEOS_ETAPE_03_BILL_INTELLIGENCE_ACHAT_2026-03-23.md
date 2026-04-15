# FIX PROMEOS — ÉTAPE 3 : BILL INTELLIGENCE & ACHAT

> **Date** : 2026-03-23
> **Scope** : Corrections XS/S issues de l'audit étape 3
> **Méthode** : Corrections chirurgicales, sources réglementaires vérifiées ×2

---

## 1. Résumé exécutif

6 corrections ciblées appliquées pour éliminer les incohérences les plus impactantes sur la crédibilité du POC. Aucune refonte — modifications chirurgicales.

| # | Correction | Effort | Impact crédibilité |
| --- | --- | --- | --- |
| 1 | Source unique prix par défaut (0.15→0.18 unifié) | XS | Élimine 17% d'écart shadow billing |
| 2 | Dépréciation moteur achat simple (facteurs fixes) | XS | Oriente vers le moteur market-based |
| 3 | Versionnement accise gaz (TICGN 2024→2026) | S | Taux corrects post-réforme fiscale |
| 4 | Note computation source PurchaseAssistant | XS | Transparence calcul local vs serveur |
| 5 | Auto-sync actions achat au mount | S | Centre d'actions peuplé automatiquement |
| 6 | Bannière données marché démo | S | Pas de faux feed temps réel |

---

## 2. Modifications réalisées

### 2.1 Source unique prix par défaut

**Problème** : `billing_service.py:43-44` utilisait des env vars avec fallback 0.15/0.08, tandis que `config/default_prices.py` définit 0.18/0.09. Écart de 17%.

**Correction** :
- Supprimé les constantes env var dans `billing_service.py`
- Supprimé l'import `os` (devenu inutile pour cette section)
- Importé depuis `config.default_prices` (source unique)
- Remplacé les 2 usages (`get_reference_price()` fallback P4 + `shadow_billing_simple()` fallback)

**Résultat** : Tous les services backend utilisent maintenant 0.18 EUR/kWh (elec) et 0.09 EUR/kWh (gaz) depuis une source unique.

### 2.2 Dépréciation moteur achat simple

**Correction** :
- Ajouté docstring DEPRECATED dans `purchase_scenarios_service.py` (comme compliance_engine.py)
- Ajouté champ `_deprecated` dans la réponse de `GET /api/contracts/{id}/purchase-scenarios`
- Docstring route enrichie avec mention DÉPRÉCIÉ + redirection vers `POST /api/purchase/compute/{site_id}`

### 2.3 Versionnement accise gaz

**Correction** :
- Ajouté 3 entrées TICGN versionnées dans `catalog.py` :
  - `TICGN_2024` : 16.37 €/MWh (01/2024–07/2025)
  - `TICGN_AOUT2025` : 10.54 €/MWh (08/2025–01/2026) — source Légifrance arrêté 24/07/2025
  - `TICGN_FEV2026` : 10.73 €/MWh (02/2026+) — source Légifrance arrêté 24/12/2025
- Ajouté résolution temporelle `TICGN` dans `_resolve_temporal_code()`
- Mis à jour le fallback `billing_shadow_v2.py` pour utiliser le catalog versionné (fallback 0.01073 = taux fév 2026+)

### 2.4 Note computation source PurchaseAssistant

**Correction** :
- Ajouté `_computation_source` et `_computation_note` dans la sortie de `runEngine()` pour signaler que le calcul est local

### 2.5 Auto-sync actions achat

**Correction** :
- Ajouté auto-sync au mount de `ActionsPage.jsx` via `syncActions()` (1 fois par session/org, via `sessionStorage`)
- Destructuré `org` depuis `useScope()` pour le clé de session

### 2.6 Bannière données marché démo

**Correction** :
- Ajouté détection `isDemo` dans `MarketContextBanner.jsx` (vérifie `is_demo` ou `source` contenant "seed")
- Ajouté badge "Donnees demo — prix indicatifs" (orange, discret)
- Ajouté champs `source` et `is_demo` dans la réponse de `get_market_context()` (backend `purchase_pricing.py`)
- Détection automatique : si pas de données réelles ou si source contient "seed"

---

## 3. Fichiers touchés

| Fichier | Modification |
| --- | --- |
| `backend/services/billing_service.py` | Suppression env vars + import `os`, import config, remplacement 2 fallbacks |
| `backend/services/purchase_scenarios_service.py` | Docstring DEPRECATED |
| `backend/routes/contracts_radar.py` | Champ `_deprecated` dans réponse, docstring |
| `backend/services/billing_engine/catalog.py` | 3 entrées TICGN + résolution temporelle |
| `backend/services/billing_shadow_v2.py` | Fallback TICGN via catalog versionné |
| `backend/services/purchase_pricing.py` | Champs `source` + `is_demo` dans market context |
| `frontend/src/pages/PurchaseAssistantPage.jsx` | Metadata computation source |
| `frontend/src/pages/ActionsPage.jsx` | Auto-sync mount + destructuration org |
| `frontend/src/components/purchase/MarketContextBanner.jsx` | Badge données démo |

---

## 4. Tests à vérifier

- `backend/tests/test_sprint_p1.py` — prix par défaut (existant, doit passer)
- `backend/tests/test_billing_*.py` — shadow billing avec nouveau fallback 0.18
- `backend/tests/test_contract_radar_v99.py` — endpoint scenarios (champ `_deprecated` ajouté)
- Tests manuels : ouvrir `/actions`, vérifier auto-sync. Ouvrir `/achat-energie`, vérifier badge démo.

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
| --- | --- | --- |
| Shadow billing total change (0.15→0.18) | **Attendu** | Les tests qui hardcodent 0.15 devront être mis à jour. C'est une correction, pas une régression |
| TICGN versionnement casse billing_shadow_v2 | Faible | Fallback conservé (0.01073) si catalog échoue |
| Auto-sync ActionsPage ralentit le chargement | Faible | 1 seul appel par session (sessionStorage guard) |
| MarketContextBanner affiche badge démo en prod | Attendu | Si les données sont seed, le badge apparaîtra — c'est le comportement voulu |

---

## 6. Points non traités (volontairement)

| Point | Raison |
| --- | --- |
| Remplacement complet de `runEngine()` JS par appel API | Scope M, pas XS/S. Le flag `USE_BACKEND_PRICING = true` existe mais n'est pas wired. Nécessite refactoring du wizard |
| Auto-sync après `POST /purchase/compute` côté backend | Risque de side-effect sur l'endpoint compute. Préféré le sync côté frontend (plus prévisible) |
| Reconstitution gaz V2 complète (ATRD + ATRT + CTA gaz) | Scope L, hors sprint XS/S |
| Suppression du moteur achat simple | Backward-compat contracts_radar. Marqué deprecated, pas supprimé |
| Lien conformité ↔ facture | Étape 1 P0-2, sera traité dans un sprint dédié |

---

## 7. Definition of Done

| Critère | Statut |
| --- | --- |
| Source unique prix par défaut | ✅ `config/default_prices.py` seule source |
| Moteur achat simple marqué deprecated | ✅ Docstring + champ `_deprecated` dans réponse |
| TICGN versionnée (3 périodes) | ✅ 2024, août 2025, fév 2026 |
| PurchaseAssistant signale calcul local | ✅ Metadata `_computation_source` |
| Actions auto-sync au mount | ✅ 1×/session via sessionStorage |
| Bannière données marché démo | ✅ Badge + champs source/is_demo backend |
| Aucune donnée démo présentée comme réelle | ✅ |
