# AUDIT PROMEOS — ÉTAPE 6 : FRONT TECHNIQUE — 24 mars 2026

> Évaluer si le frontend soutient un POC à 9.1/10 sans dette cachée dangereuse.
> Méthode : exploration exhaustive fichiers/tailles/patterns/dépendances + design system + robustesse.

---

## 1. Résumé exécutif

**Verdict front technique : 7.5/10** — Fondations solides (design system A+, lazy loading A, null guards A-), mais dette structurelle réelle sur 3 axes : fetch patterns dupliqués (50+ pages), 6 pages > 1500L non décomposées, routes hardcodées (87 occurrences).

**Aucune dette bloquante pour le 9/10.** Les faiblesses sont de la dette de croissance, pas de la dette d'architecture.

---

## 2. Forces front réelles

### Tag : SOLIDE

| Force | Preuve | Score |
|---|---|---|
| **Design system barrel** | 51 exports dans `ui/index.js`, 113 imports centralisés, 0 duplication de composants UI | A+ |
| **Lazy loading** | 46 routes lazy-loadées via `React.lazy`, Suspense avec SkeletonCard, maplibre chunké | A |
| **Null/undefined guards** | 1040 instances `?.`, `|| []`, `??` dans pages/, 0 crash null-pointer dans les tests | A- |
| **State management propre** | 5 contexts (Auth, Scope, Demo, Expert, ActionDrawer), pas de Redux/Zustand, `useScope()` dans 32 pages | A |
| **Prop drilling minimal** | Max 2-3 niveaux, contextes utilisés stratégiquement | A |
| **CSS pur Tailwind** | 5535 `className=`, 1 seul .css (login décoratif), 0 SCSS, pas de CSS-in-JS | A |
| **Dépendances saines** | 12 packages, tous à jour, 0 vulnérabilité, stack React 18 + Vite 5 + Tailwind 4 | A |
| **Tests logiques** | 886 cas de tests dans 112 fichiers, focus business logic (pas DOM) | B+ |
| **Memoization** | 264 `useMemo`/`useCallback` dans 58 fichiers, pages lourdes bien couvertes | 7/10 |
| **Code mort** | 0 TODO/FIXME/HACK dans les pages, CommandCenter/EnergyCopilot = choix intentionnel | A |

---

## 3. Dettes front réelles

### 3.1 Fetch patterns dupliqués — Tag : DUPLIQUÉ

**Constat** : 50+ pages réimplémentent le même pattern ad-hoc :
```jsx
const [data, setData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
useEffect(() => {
  setLoading(true);
  apiCall().then(setData).catch(setError).finally(() => setLoading(false));
}, [deps]);
```

**Chiffres** :
- 198 `useState(*loading)` dans 53 fichiers
- 132 `useEffect(...fetch)` dans 50 fichiers
- Seulement 8 fichiers utilisent les hooks partagés (`useCockpitData`, `useActivationData`, etc.)

**Impact** : ~250 déclarations `useState` redondantes. Maintenance coûteuse, correction d'un pattern de fetch = toucher 50 fichiers.

**Hooks existants mais sous-adoptés** :
- `useApiCache.js` — stale-while-revalidate avec TTL (prêt, peu utilisé)
- `useCockpitData.js` — agrégation cockpit (5 fichiers)
- `useActivationData.js` — triple-fetch dédupliqué (2 fichiers)

### 3.2 Pages surdimensionnées — Tag : FRAGILE

| Page | Lignes | Raison | Risque |
|---|---|---|---|
| MonitoringPage.jsx | **3112** | 13+ fonctions helper, 34 useState, 8 StatusKpiCard locaux | **Périmètre Yannick — ne pas toucher** |
| Patrimoine.jsx | **2243** | Table virtualisée + 7 drawers + 6 KPIs + carte | À RISQUE MAINTENANCE |
| PurchasePage.jsx | **2029** | 4 tabs + scénarios + slider RéFlex + historique | À RISQUE MAINTENANCE |
| PurchaseAssistantPage.jsx | **1864** | Wizard 8 étapes + Monte Carlo engine | À RISQUE MAINTENANCE |
| Site360.jsx | **1619** | 6 tabs + 15 Explain + drawers BACS/Intake | FRAGILE |
| ActionsPage.jsx | **1592** | 3 vues (table/kanban/runbook) + filtres + ROI bar | FRAGILE |

**Composants surdimensionnés** :
- `ActionDetailDrawer.jsx` — **1327L** (5 tabs dans un drawer)
- `PatrimoineWizard.jsx` — **1163L** (wizard monolithique)
- `SiteCreationWizard.jsx` — **1040L**
- `StickyFilterBar.jsx` — **910L** (dans pages/ au lieu de components/)

### 3.3 Routes hardcodées — Tag : FRAGILE

- **87 `navigate('/...')`** hardcodés dans 34 fichiers
- **15 helpers centralisés** dans `services/routes.js` (233L) — mais adoption < 20%
- Pire cas : PurchasePage (25+ routes hardcodées), Patrimoine (12), Site360 (5)

### 3.4 KpiCard fragmenté — Tag : DUPLIQUÉ

| Variante | Occurrences | Statut |
|---|---|---|
| `KpiCard` (générique) | ~80 | Principal |
| `KpiCardInline` (plat) | ~40 | Actif |
| `KpiCardCompact` (dense) | ~10 | Actif |
| `MetricCard` (déprécié) | ~12 | À migrer |
| `UnifiedKpiCard` (cible) | ~5 | Sous-adopté |
| **Définitions locales** | **3** | **UsagesDashboard, InsightsPanel, MonitoringPage** |

3 pages définissent leur propre `KpiCard` local au lieu d'importer le composant UI.

### 3.5 Expert mode omniprésent — Tag : PARTIEL

- **207 références `isExpert`** dans 35 fichiers
- ~60% = rendu conditionnel (show/hide sections)
- ~20% = niveau de détail UI
- ~20% = filtrage/agrégation données
- MonitoringPage : 30 refs, Cockpit : 17 refs, BillIntelPage : 12 refs

---

## 4. Duplication / incohérences détaillées

| Type | Occurrences | Fichiers | Impact |
|---|---|---|---|
| Fetch pattern ad-hoc | 198 useState + 132 useEffect | 50+ pages | Élevé — maintenabilité |
| KpiCard local redéfini | 3 définitions | UsagesDashboard, InsightsPanel, MonitoringPage | Moyen — cohérence |
| Navigate hardcodé | 87 strings | 34 pages | Élevé — refactoring risqué |
| Naming Page suffix | Incohérent | ~60 avec suffix, ~50 sans | Faible — cosmétique |
| French/English mix fichiers | 45 fichiers | ConsommationsUsages, ActionsPage, etc. | Faible — cosmétique |

---

## 5. Risques de régression

| Zone | Risque | Raison | Recommandation |
|---|---|---|---|
| MonitoringPage (3112L) | **ÉLEVÉ** | Périmètre Yannick, 30 isExpert, 34 useState | **Ne pas toucher** |
| Patrimoine (2243L) | **MOYEN** | Table virtualisée + 7 drawers — sensible aux refactors | Extraire drawers seulement |
| PurchaseAssistantPage (1864L) | **MOYEN** | Monte Carlo engine côté client | Déjà isolé dans `domain/purchase/engine.js` |
| ActionDetailDrawer (1327L) | **FAIBLE** | 5 tabs indépendants | Safe à décomposer |
| routes.js (233L) | **FAIBLE** | Helpers isolés, pas d'effet de bord | Safe à enrichir |

---

## 6. Quick wins par effort

### XS (< 1 heure)

| # | Action | Impact | Fichier |
|---|---|---|---|
| 1 | Supprimer 3 définitions `KpiCard` locales (UsagesDashboard, InsightsPanel, MonitoringPage) | Cohérence | 3 fichiers |
| 2 | Déplacer `StickyFilterBar.jsx` de pages/ vers components/ | Organisation | 1 fichier |

**Note** : le point 1 pour MonitoringPage = périmètre Yannick → ne faire que UsagesDashboard + InsightsPanel.

### S (1-3 jours)

| # | Action | Impact |
|---|---|---|
| 3 | Créer `usePageData(apiCall, deps)` hook générique — remplacer le pattern ad-hoc dans 10 pages prioritaires | Maintenabilité |
| 4 | Migrer 20 `navigate('/...')` les plus fréquents vers `routes.js` helpers | Robustesse |
| 5 | Extraire `ActionDetailDrawer` (1327L) en 5 tab-components | Maintenabilité |

### M (1-2 semaines)

| # | Action | Impact |
|---|---|---|
| 6 | Décomposer Patrimoine.jsx (2243L) : extraire 7 drawers en composants | Maintenabilité |
| 7 | Décomposer PurchasePage.jsx (2029L) : extraire 4 tabs | Maintenabilité |
| 8 | Migrer MetricCard (12 usages) → UnifiedKpiCard | Unification |
| 9 | Adopter `usePageData` dans 40 pages restantes | Systématique |

---

## 7. Plan de correction priorisé

### Immédiat (Sprint XS, < 1 jour)
- Points 1-2 ci-dessus
- Gain : cohérence composants, organisation fichiers

### Court terme (Sprint S, 1 semaine)
- Points 3-5
- Gain : pattern fetch unifié + routes centralisées + ActionDetailDrawer maintenable

### Moyen terme (Sprint M, 2-3 semaines)
- Points 6-9
- Gain : pages < 1000L, KpiCard unifié, fetch systématique

---

## 8. Definition of Done

Le front sera considéré **techniquement solide pour un POC premium** quand :

1. ✅ 0 définition KpiCard locale (tout passe par ui/)
2. ✅ Hook `usePageData` adopté dans les 10 pages à plus forte exposition
3. ✅ 0 `navigate('/...')` hardcodé dans les 10 pages clés (helpers utilisés)
4. ✅ ActionDetailDrawer < 500L (5 tabs extraits)
5. ✅ Patrimoine < 1500L (drawers extraits)
6. ✅ MetricCard retiré (migré UnifiedKpiCard)
7. ✅ StickyFilterBar dans components/ (pas pages/)

**Score front cible après corrections : 8.5/10.**

---

## Annexe — Scorecard front

| Dimension | Score | Tag |
|---|---|---|
| Design system barrel | A+ | SOLIDE |
| State management | A | SOLIDE |
| Lazy loading | A | SOLIDE |
| Null guards | A- | SOLIDE |
| Prop drilling | A | SOLIDE |
| CSS discipline | A | SOLIDE |
| Dépendances | A | SOLIDE |
| Tests (886 cas) | B+ | SOLIDE |
| Memoization | 7/10 | PARTIEL |
| Fetch patterns | 4/10 | DUPLIQUÉ |
| Pages sizing | 5/10 | FRAGILE |
| Routes centralisation | 4/10 | FRAGILE |
| KpiCard unification | 5/10 | DUPLIQUÉ |
| Expert mode gestion | 6/10 | PARTIEL |

*Audit front technique — 24 mars 2026. Verdict : 7.5/10, fondations solides, dette de croissance à absorber progressivement.*
