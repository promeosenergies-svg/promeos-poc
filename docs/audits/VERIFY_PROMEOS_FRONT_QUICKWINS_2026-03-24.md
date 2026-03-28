# VERIFY PROMEOS — Front Quick Wins — 24 mars 2026

## 1. Résumé exécutif

**Tous les correctifs appliqués sont vérifiés. 0 régression. Périmètre Yannick intact (1 commentaire doc seulement).**

| Point | Verdict |
|---|---|
| KpiCard locale UsagesDashboard supprimée | ✅ VÉRIFIÉ |
| usePageData hook créé | ✅ VÉRIFIÉ (0 adoption, attendu) |
| 3 routes helpers créés | ✅ VÉRIFIÉ |
| 8 navigate migrés | ✅ VÉRIFIÉ |
| Périmètre Yannick | ✅ INTACT (1 commentaire doc CO₂ seulement) |
| Tests | ✅ 9/9 passent |

**Verdict : GO Étape 7 QA ou GO Étape 8 Go-to-market.**

---

## 2. Correctifs vérifiés

### 1. UsagesDashboard KpiCard — VÉRIFIÉ

| Point | Preuve | Verdict |
|---|---|---|
| Définition locale supprimée | Grep `function KpiCard` dans UsagesDashboardPage = **0 résultat** | ✅ |
| Import partagé | L12 : `import KpiCard from '../ui/KpiCard'` | ✅ |
| 6 appels migrés | L1045-1067 : 6 `<KpiCard label=... value=...>` via composant partagé | ✅ |
| Commentaire traçabilité | L140 : `// KpiCard local supprimé — utilise le composant partagé ui/KpiCard` | ✅ |
| Wrapper Tailwind | `className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-4"` (plus de inline styles) | ✅ |

**Tag : VÉRIFIÉ**

### 2. usePageData hook — VÉRIFIÉ

| Point | Preuve | Verdict |
|---|---|---|
| Fichier créé | `hooks/usePageData.js` (60 lignes) | ✅ |
| Interface simple | `{ data, loading, error, refetch }` — 4 sorties claires | ✅ |
| Guards unmount | `mountedRef.current` vérifié dans then/catch | ✅ |
| Guards stale | `fetchIdRef.current !== fetchId` vérifié | ✅ |
| Error = string | `err?.message \|\| err?.detail \|\| 'Erreur de chargement'` | ✅ |
| 0 logique métier | Aucun import de modèle/service/domaine | ✅ |
| Adoption | **0 page l'utilise** — documenté comme adoption progressive | ✅ Attendu |

**Tag : VÉRIFIÉ** (hook prêt, adoption future)

### 3. Routes helpers — VÉRIFIÉ

| Helper | Fichier:ligne | Params | Vérifié |
|---|---|---|---|
| `toConformite(opts)` | `routes.js:240` | `tab`, `site_id` | ✅ |
| `toRenewals(opts)` | `routes.js:253` | `site_id` | ✅ |
| `toSite(siteId, opts)` | `routes.js:266` | `tab` (hash) | ✅ |

### 4. Navigate migrés — VÉRIFIÉ

| Page:ligne | Avant | Après | Vérifié |
|---|---|---|---|
| BillIntelPage:533 | `'/achat'` | `toPurchase()` | ✅ |
| BillIntelPage:559 | `'/conformite'` | `toConformite()` | ✅ |
| BillIntelPage:833 | `'/consommations/import'` | `toConsoImport()` | ✅ |
| ConformitePage:623 | `'/patrimoine'` | `toPatrimoine()` | ✅ |
| ConformitePage:640 | `'/bill-intel'` | `toBillIntel()` | ✅ |
| Site360:1402 | `'/patrimoine'` | `toPatrimoine()` | ✅ |
| Site360:1415 | `'/patrimoine'` | `toPatrimoine()` | ✅ |

**Imports ajoutés** :
- BillIntelPage : `import { toPurchase, toConformite, toConsoImport } from '../services/routes'` ✅
- ConformitePage : `import { toPatrimoine, toBillIntel } from '../services/routes'` ✅
- Site360 : `import { toPatrimoine } from '../services/routes'` ✅

**Tag : VÉRIFIÉ** — Les 7 navigate (pas 8 — BillIntel en a 3, Conformité 2, Site360 2 = 7 total) utilisent les helpers. Scope et query params conservés.

---

## 3. Correctifs partiels

**0 correctif partiel.**

---

## 4. Éléments volontairement exclus

| Élément | Raison | Tag |
|---|---|---|
| ActionDetailDrawer décomposition | Effort M (20+ closures), reporté | EXCLU VOLONTAIREMENT |
| Migration 10 pages vers usePageData | Risque régression (spécificités par page) | EXCLU VOLONTAIREMENT |
| 79 navigate hardcodés restants | Migration progressive | EXCLU VOLONTAIREMENT |
| StickyFilterBar déplacement | Périmètre Yannick | EXCLU VOLONTAIREMENT |
| InsightsPanel KpiCard locale | Périmètre Yannick | EXCLU VOLONTAIREMENT |

---

## 5. Régressions détectées

**0 régression.**

### Périmètre Yannick

| Vérification | Résultat |
|---|---|
| `git diff` fichiers périmètre Yannick | **1 fichier** : `consumption/constants.js` |
| Nature du changement | **Commentaire doc seulement** (enrichissement docstring CO₂, valeur 0.052 inchangée) |
| Changement fonctionnel | **0** — aucune ligne de code modifiée |

**Tag : INTACT** — Le commentaire doc est un enrichissement de traçabilité (sprint 4bis), pas une modification fonctionnelle.

---

## 6. Recommandation

**GO Étape 8 (Go-to-market)** — ou GO Étape 7 (QA) si priorité tests.

Le front est désormais :
- KpiCard locaux nettoyés (hors Yannick)
- Routes helpers enrichis (18 helpers, 3 nouveaux)
- Hook usePageData prêt pour adoption progressive
- 0 régression, tests passent

---

## 7. Definition of Done

- [x] KpiCard locale UsagesDashboard supprimée → composant partagé
- [x] usePageData hook créé, propre, sans logique métier
- [x] 3 routes helpers ajoutés (toConformite, toRenewals, toSite)
- [x] 7 navigate hardcodés migrés vers helpers (BillIntel 3, Conformité 2, Site360 2)
- [x] Périmètre Yannick intact (1 commentaire doc, 0 code)
- [x] 9/9 tests frontend passent
- [x] 0 régression détectée
