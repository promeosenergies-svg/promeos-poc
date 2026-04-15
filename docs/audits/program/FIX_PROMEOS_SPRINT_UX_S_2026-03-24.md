# FIX PROMEOS — Sprint UX S — 24 mars 2026

## 1. Résumé exécutif

5 corrections premium appliquées. 1 point du plan s'est avéré déjà résolu (breakdown score conformité = déjà toujours visible). Breadcrumb Site360 = déjà fonctionnel via le composant global.

| # | Correction | Fichiers | Résultat |
|---|---|---|---|
| 1 | FreshnessIndicator ConformitePage (résiduel XS) | `ConformitePage.jsx` | ✅ Composant dynamique |
| 2a | TrustBadge ConformitePage | `ConformitePage.jsx` | ✅ Source + confidence |
| 2b | TrustBadge PurchasePage | `PurchasePage.jsx` | ✅ Source + is_demo aware |
| 3 | Score conformité explicite | `ComplianceScoreHeader.jsx` | ℹ️ Déjà toujours visible (0 modif) |
| 4 | Breadcrumb Site360 | `Breadcrumb.jsx` | ℹ️ Déjà fonctionnel (0 modif) |
| 5a | ErrorState AnomaliesPage | `AnomaliesPage.jsx` | ✅ ErrorState + fallback inline |
| 5b | ErrorState ContractRadarPage | `ContractRadarPage.jsx` | ✅ ErrorState + retry |

---

## 2. Modifications réalisées

### Fix 1 — FreshnessIndicator ConformitePage

Remplacé le `<span>` plat "Dernière évaluation : {date}" par `<FreshnessIndicator>` avec calcul dynamique (fresh < 45j, recent < 90j, stale < 365j, expired).

- Import ajouté : `import FreshnessIndicator from '../components/FreshnessIndicator'`
- Données : `bundle?.meta?.generated_at` → objet freshness

### Fix 2a — TrustBadge ConformitePage

Ajouté `<TrustBadge source="PROMEOS RegOps A.2" confidence={complianceScore?.confidence || 'medium'} />` après `ComplianceScoreHeader`.

- Import ajouté : `TrustBadge` depuis `'../ui'`
- Confidence dynamique : lit `complianceScore.confidence` (high/medium/low)
- Période : `bundle?.meta?.generated_at` formaté en date FR

### Fix 2b — TrustBadge PurchasePage

Ajouté `<TrustBadge source="PROMEOS Pricing Engine" confidence={...} />` après `MarketContextBanner`.

- Import ajouté : `TrustBadge` depuis `'../ui'`
- Confidence : `'low'` si `marketContext?.is_demo` (données seed), `'medium'` sinon
- Période : `marketContext?.spot_date`

### Fix 3 — Score conformité (0 modification)

**Constat** : le breakdown DT/BACS/APER (barres + poids + scores) est **DÉJÀ toujours visible** dans `ComplianceScoreHeader.jsx` lignes 67-125. Seule l'explication textuelle "Comment c'est calculé" est en hover (lignes 40-52). Aucune modification nécessaire.

### Fix 4 — Breadcrumb Site360 (0 modification)

**Constat** : `layout/Breadcrumb.jsx` (170L) résout déjà dynamiquement `/sites/42` → "Site #42" via `resolveBreadcrumbLabel()` + lookup `siteNameById` pour le nom réel. Le breadcrumb est rendu globalement dans `AppShell.jsx`. Aucune modification nécessaire.

### Fix 5a — ErrorState AnomaliesPage

- Import ajouté : `import ErrorState from '../ui/ErrorState'`
- Rendu : `ErrorState` complet si erreur ET aucune donnée, sinon bandeau inline rouge préservé

### Fix 5b — ErrorState ContractRadarPage

- Import ajouté : `import ErrorState from '../ui/ErrorState'`
- State ajouté : `loadError` avec `setLoadError`
- Fetch refactoré en `fetchRadar` (useCallback) pour permettre le retry
- Rendu : `ErrorState` avec `onRetry={fetchRadar}` si erreur ET pas de données

---

## 3. Fichiers touchés

| Fichier | Modification |
|---|---|
| `pages/ConformitePage.jsx` | Import FreshnessIndicator + TrustBadge, composant FreshnessIndicator, TrustBadge après score |
| `pages/PurchasePage.jsx` | Import TrustBadge, badge après MarketContextBanner |
| `pages/AnomaliesPage.jsx` | Import ErrorState, rendu conditionnel ErrorState/inline |
| `pages/ContractRadarPage.jsx` | Import ErrorState, state loadError, fetchRadar callback, rendu ErrorState |

---

## 4. Tests

| Suite | Résultat |
|---|---|
| `step4_co2_guard.test.js` | 9/9 ✅ |

---

## 5. Risques de régression

| Risque | Probabilité | Mitigation |
|---|---|---|
| TrustBadge avec confidence `undefined` | Faible | Fallback `'medium'` par défaut |
| FreshnessIndicator avec `generated_at` null | Faible | Statut `'no_data'` géré |
| ContractRadarPage `fetchRadar` appelé 2x | Nulle | `useCallback` avec deps `[horizon, selectedSiteId]` + useEffect |

---

## 6. Points non traités

| Point | Raison |
|---|---|
| ErrorState AdminUsersPage | Page admin, faible exposition démo |
| Unification KpiCard/MetricCard/UnifiedKpiCard | Effort M, hors scope sprint S |
| Accessibilité sr-only/ARIA | Effort M, sprint dédié |
| TrustBadge PurchaseAssistantPage | Effort XS mais page déjà PREMIUM |

---

## 7. Definition of Done

- [x] FreshnessIndicator composant sur ConformitePage (résiduel XS fermé)
- [x] TrustBadge sur ConformitePage avec confidence dynamique
- [x] TrustBadge sur PurchasePage avec détection is_demo
- [x] Breakdown score conformité = déjà toujours visible (confirmé)
- [x] Breadcrumb Site360 = déjà fonctionnel (confirmé)
- [x] ErrorState sur AnomaliesPage
- [x] ErrorState sur ContractRadarPage avec retry
- [x] 9 tests frontend passent
- [x] 0 fichier Yannick touché
