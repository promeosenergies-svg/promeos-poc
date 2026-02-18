# DEVLOG PROMEOS

## Sprint V22 — Consommations Expert : Analyse & Insights (2026-02-18)

**Objectif** : InsightsPanel complet (6 KPIs), granularité data-driven (intersection période × fréquence de relève), métadonnées backend enrichies, vérification gaz end-to-end.

### Phase 0 — Audit (findings)

1. **Signature + Météo tabs** : DÉJÀ câblés dans TAB_CONFIG (lignes 62-63) et rendus (lignes 1371-1375). Aucune correction nécessaire.
2. **InsightsPanel** : ABSENT. `InsightsStrip` (bandeau étroit) existe mais aucun onglet "Insights" complet. Stop-condition #3 exige cet onglet.
3. **normalizeId** : CLEAN — défini dans `helpers.js:15`, ré-exporté dans `ConsumptionDiagPage.jsx:76`. Aucun crash.
4. **backend `_meta()`** : INCOMPLET — ne renvoie pas `sampling_minutes`, `available_granularities`, ni `valid_count`. Le modèle Pydantic `TimeseriesMeta` doit être étendu.
5. **`getAvailableGranularities(days)`** : PÉRIODE-ONLY — pas de croisement avec la fréquence de relève réelle.

### Commits V22

| Commit | Fichier | Action |
|--------|---------|--------|
| V22-A | `consumption/InsightsPanel.jsx` | NOUVEAU — P05/P95/load-factor/anomalies (6 KPI-cards) |
| V22-A | `ConsumptionExplorerPage.jsx` | Ajout onglet 'insights' dans TAB_CONFIG + rendu panel |
| V22-B | `timeseries_service.py` `_meta()` | Ajout `sampling_minutes`, `available_granularities`, `valid_count` |
| V22-B | `ems.py` `TimeseriesMeta` | Pydantic fields optionnels correspondants |
| V22-B | `consumption/helpers.js` | `getAvailableGranularities(days, samplingMinutes)` — intersection |
| V22-C | `__tests__/V22ConsommationsExpert.test.js` | NOUVEAU — suite de tests purs |
| V22-D | Gas demo | Vérification fréquence + end-to-end |
| V22-E | `docs/qa-consommations-v22.md` | NOUVEAU — checklist QA |

### Résultat attendu

- ≥ 854 + N tests verts (854 = résultat Sprint Cockpit)
- Build propre, 0 erreur

---

## Sprint V20 — Consommations World-Class : Audit complet + Fix E2E (2026-02-18)

**Objectif** : Éliminer le bug "0 points valides (min 2)" visible alors que le badge affichait "1 compteur / 90 points / source EMS". Trois root causes composées.

### Root Causes (3)

1. **RC1 — `overlayValueKeys` incluait `'total'`** (`TimeseriesPanel.jsx`) : le filtre `s.key !== 'agg'` ne bloquait pas `key="total"` renvoyé par le backend en mode agrégé → `valueKey="total"` envoyé à ExplorerChart → `p["total"]` undefined sur tous les points → "0 points valides" dans le chart, mais le badge rendait via `p.value` (correctement peuplé) → les deux visibles simultanément.
2. **RC2 — Timestamps espace** (`useEmsTimeseries.js`) : le backend renvoie `"YYYY-MM-DD HH:MM:00"` (espace, pas T) pour les granularités sub-horaires. `new Date("2025-01-01 10:15:00")` peut produire Invalid Date sur certains navigateurs.
3. **RC3 — `validPoints` guard incohérent** (`TimeseriesPanel.jsx`) : le guard utilisait `p.value` mais ExplorerChart utilisait `p[valueKey]`. Divergence quand `valueKey !== 'value'`.

### Fixes

- **V20-A** — `useEmsTimeseries.js` + `TimeseriesPanel.jsx` + `ExplorerDebugPanel.jsx` : Enrichissement du debug panel avec `validCount`, `zerosCount`, `nullsCount`, `nanCount`, `samplePoints`, `effectiveValueKey`.
- **V20-B** — Fix RC1 : `overlayValueKeys = seriesData.length <= 1 ? [] : seriesData.filter(s => !['agg','total','others'].includes(s.key)).map(s => s.key)`. Fix RC2 : `.replace(' ', 'T')` avant `new Date()`. Fix RC3 : `effectiveValueKey` utilisé de façon cohérente dans le guard et le chart.
- **V20-C** — `backend/routes/ems.py` : `POST /api/ems/demo/generate_timeseries` (wraps `generate_demo_consumption`).
- **V20-D** — `TimeseriesPanel.jsx` : CTA "Générer conso démo" dans les états Empty et Insufficient. `ConsumptionExplorerPage.jsx` : `handleGenerateDemo` + `refreshKey`.
- **V20-E** — `V20TimeseriesFix.test.js` : 15 tests purs (4 describe blocks + bonus MODE_MAP).
- **V20-F** — `docs/qa-consommations.md` + DEVLOG.

### Résultat

- **804+ tests verts** (789 → 804, +15)
- Build propre, 0 erreur

---

## Sprint V19 — ConsumptionExplorer "Jamais blanc, jamais muet" (2026-02-18)

**Objectif** : Éliminer les six root causes derrière "Aucun site sélectionné / courbes invisibles / dead-end" sur l'Explorer.

### Root Causes (6)

1. **RC1 — Default tab 'tunnel'** (`useExplorerURL.js`) : les utilisateurs atterrissaient sur la vue P10-P90 au lieu de la série temporelle.
2. **RC2 — Site selector hidden** (`StickyFilterBar.jsx`) : `isMultiMode = sites.length > 1 && setSiteIds` → chips UI disparaissait avec 0 ou 1 site / pendant le chargement.
3. **RC3 — sitesLoading manquant dans Explorer** (`ConsumptionExplorerPage.jsx`) : V18 avait ajouté `sitesLoading` à ScopeContext mais pas à ExplorerPage.
4. **RC4 — `metric='eur'` envoyé à l'API** (`useEmsTimeseries.js`) : le backend n'accepte que 'kwh' | 'kw'; 'eur' est display-only.
5. **RC5 — Pas de `response_model` Pydantic** (`backend/routes/ems.py`) : OpenAPI affichait `{}` ou "string" pour le timeseries.
6. **RC6 — `handleSwitchEnergy` always resets to 'tunnel'** (`ConsumptionExplorerPage.jsx`) : `else switchTab('tunnel')` perdait l'onglet Timeseries lors d'un switch d'énergie.

### Fixes

- **V19-A** — `useExplorerURL.js` : `DEFAULTS.tab = 'timeseries'` + `ConsumptionExplorerPage.jsx` : `handleSwitchEnergy` ne quitte plus l'onglet actif sauf si on était sur 'gas'.
- **V19-B** — `StickyFilterBar.jsx` : `isMultiMode = Boolean(setSiteIds)` + section site toujours visible avec placeholder "Chargement…" / "Sélectionner des sites…".
- **V19-C** — `ConsumptionExplorerPage.jsx` : `sitesLoading` extrait de `useScope()` et passé à `StickyFilterBar`.
- **V19-D** — `useEmsTimeseries.js` : `const apiMetric = unit === 'eur' ? 'kwh' : unit`.
- **V19-E** — `backend/routes/ems.py` : modèles Pydantic `TimeseriesResponse` + `response_model=TimeseriesResponse` sur la route.
- **V19-F** — `V19ExplorerFix.test.js` : 18 tests purs (4 describe blocks).

### Résultat

- **789 tests verts** (771 → 789, +18)
- Build propre, 0 erreur

---

## Sprint V18 — Demo Scope Coherence: zéro 0-site / zéro fantôme Casino (2026-02-18)

**Objectif** : Éliminer les trois root causes derrière l'affichage "0 site" et les "36 sites Casino" fantômes après un seed "SCI Les Terrasses — Tertiaire S=10".

### Root Causes (3)

1. **RC1 — Pas de `sitesLoading`** : `orgSites = []` entre le mount et la résolution de `getSites()`. Les pages voyaient un tableau vide et affichaient EmptyState.
2. **RC2 — Double-clear dans `applyDemoScope`** : `setApiSites([])` dans `applyDemoScope` + le `useEffect` sur `effectiveOrgId` → double fenêtre "0 sites".
3. **RC3 — Pas de guard anti-stale** : deux requêtes concurrentes lors d'un switch rapide d'org → la plus ancienne (Casino, 36 sites) pouvait écraser la plus récente (Tertiaire, 10 sites).

### Fixes

**V18-A — ScopeContext** :
- `sitesLoading` state (bool) + `_fetchId = useRef(0)` (requestId guard)
- `useEffect` `getSites` : `setSitesLoading(true)` → `const myId = ++_fetchId.current` → si `myId !== _fetchId.current` → ignorer la réponse stale
- Suppression de `setApiSites([])` dans `applyDemoScope` (le `useEffect` gère déjà le clear)
- `sitesLoading` exporté dans le context value

**V18-B — Pages** :
- `Cockpit.jsx`, `ConformitePage.jsx`, `MonitoringPage.jsx` : guard `if (sitesLoading) return <Loader2 skeleton>` avant toute logique vide
- `ConformitePage` : `sitesLoading` ajouté aux deps du `useCallback loadData`

**V18-C — Header** :
- `ScopeSwitcher.jsx` : affiche "Chargement…" dans la pill scope
- `ScopeSummary.jsx` : retourne label italique `{org.nom} — Chargement…` pendant `sitesLoading`

**V18-D — ScopeDebugPanel** :
- Nouveau composant `ScopeDebugPanel.jsx` (dev-only, `?debug=1`)
- Panel flottant bas-droite : orgId, org.nom, sitesLoading, orgSites.length, sitesCount, selectedSiteId, scopeLabel
- Monté dans `AppShell.jsx`

**V18-E — Backend** :
- `backend/services/scope_utils.py` (NEW) : `get_scope_org_id(request, auth)` — priorité canonique auth.org_id > X-Org-Id > None
- `backend/routes/cockpit.py` : utilise `get_scope_org_id()` + `get_optional_auth`
- `backend/routes/consumption_diagnostic.py` : utilise `get_scope_org_id(request, auth) or org_id`

### Tests

- `V18DemoScope.test.js` (NEW) : 17 tests purs — transitions sitesLoading, requestId guard, getEffectiveSiteIds, ScopeSummary loading label
- **Total : 771 tests verts** (754 → 771)
- Build : clean, 0 erreur

---

## Sprint V17 — Consumption Explorer Site Selection Fix (2026-02-18)

**Objectif** : Corriger définitivement "0 site sélectionné" dans l'Explorer alors que le header indique "SCI Les Terrasses — Tous les sites". Normaliser les IDs site (number/string). Garantir les états vides avec CTAs.

### Root Causes

1. **`scopedSites` vs `orgSites`** : le picker utilisait `scopedSites` (filtré par `scope.siteId`) → limité à 1 site quand un scope était sélectionné. Remplacé par `orgSites` (liste complète de l'org).
2. **Sites stale après changement d'org** : l'effet de récupération ne se déclenchait que quand `siteIds.length === 0` → les IDs Casino persistaient dans l'URL après passage en Tertiaire.
3. **Mismatch number/string** : `scope.siteId` peut être un `number` ou une `string` (localStorage) ; `ScopeContext` comparait `s.id === scope.siteId` sans coercion de type.

### Fixes

**V17-A — ConsumptionExplorerPage** :
- Import `orgSites` + `scope` depuis `useScope()`
- `const sites = orgSites || []` (était `scopedSites`)
- Memo `orgSiteIdsKey` (`orgSites.map(s=>s.id).sort().join(',')`)
- Nouvel effet org-aware : `setSiteIds(prev => ...)` valide les IDs courants contre l'org ; auto-sélection N≤5 → tous / N>5 → premier

**V17-B — normalizeId** :
- Ajout de `normalizeId(x) → String(x)` dans `consumption/helpers.js`
- `ConsumptionDiagPage.jsx` : re-exporte depuis helpers (suppression de la définition locale)
- `ScopeContext.jsx` : `String(s.id) === String(scope.siteId)` dans le filtre sites

**V17-C — EmptyState CTA** :
- `TimeseriesPanel.jsx` : prop `onSelectAll` + bouton "Tout sélectionner" dans l'état `noSiteSelected`
- `ConsumptionExplorerPage.jsx` : passage de `onSelectAll={() => setSiteIds(sites.map(s=>s.id))}`
- Nouveau fichier `docs/qa-consumption-v17.md`

**V17-D — Tests** :
- `__tests__/V17SiteSelection.test.js` : 24 tests purs — normalizeId (5), validation org-change (7), auto-select threshold (4), URL parsing (4), ScopeContext filter (4)

### Résultat

- **754 tests verts** (730 → 754, +24)
- Build propre

---

## Fix DemoPack — "Pack chargé: Aucun" + sites vides (2026-02-18)

**Objectif** : Corriger la régression post-seed : "Pack chargé: Aucun" s'affichait malgré un seed réussi. Le sélecteur de sites restait vide. La card Casino semblait active quand Tertiaire était chargé.

### Root Causes

1. **`refreshStatus()` catch** : `.catch(() => { setPackStatus(null); ... })` réinitialisait `packStatus` à `null` en cas d'échec réseau transitoire, effaçant la valeur correcte.
2. **Double `applyDemoScope`** : `refreshStatus().then()` appelait `applyDemoScope()` même si le scope était déjà correct → `setApiSites([])` déclenché deux fois → course condition → `orgSites` restait vide.
3. **Pas de mise à jour optimiste** : après le seed, `packStatus` restait `null` jusqu'à la fin (async) de `getDemoPackStatus()`.

### Fixes

- `ImportPage.jsx` — `refreshStatus()` : suppression de l'appel `applyDemoScope` (géré par l'effet `syncInProgress`). Le catch ne fait plus `setPackStatus(null)` — uniquement `setStatusError(true)`.
- `ImportPage.jsx` — `performSeed()` : ajout d'un `setPackStatus` **optimiste** immédiatement après le seed (depuis `res.org_id/org_nom/pack/size`), avant `refreshStatus()`. "Pack chargé: SCI Les Terrasses" s'affiche instantanément.
- `ImportPage.jsx` — Pack cards : badge **"Chargé"** (status success) affiché sur la card dont la clé correspond à `packStatus?.pack`. Casino n'a plus de badge quand Tertiaire est chargé.

### Tests

- `ImportPage.test.js` : +12 tests purs — optimistic update (5), isLoaded badge (4), catch ne reset pas (3).

### Résultat

- **730 tests verts** (718 → 730, +12)
- Build propre

---

## Sprint V16 — Consommations "World-Class" + Scope Coherence (2026-02-18)

**Objectif** : Plus jamais d'écran blanc sur Consommations/Explorer. Garantie d'un rendu dans tous les cas (courbe / skeleton / raison claire + CTA). Cohérence parfaite du scope entre Explorer, Diagnostic et Monitoring.

### Root Cause "Blank Chart" (V16-A)

La cause première de la zone chart blanche : `showContent = hasData && !loading` bloquait `TimeseriesPanel` quand `availability.has_data=false`. **TimeseriesPanel n'était jamais monté** → aucun placeholder, aucun message, zone blanche.

### Commits

#### V16-A — Root-cause fix + ChartFrame + DebugPanel scope
- `ConsumptionExplorerPage.jsx` : TimeseriesPanel sorti du gate `showContent` → rendu garanti en Classic et sur le tab timeseries Expert. Tab bar toujours visible en Expert.
- `TimeseriesPanel.jsx` : `ChartFrame` (min-h-[360px]) wrap TOUS les états → impossible d'avoir hauteur=0. Nouveau prop `noSiteSelected` → message "Aucun site sélectionné" au lieu de zone vide.
- `TimeseriesPanel.jsx` : Import `useScope` → scope transmis au DebugPanel.
- `ExplorerDebugPanel.jsx` : Section "Scope global" (orgId, selectedSiteId, scopeLabel, sitesCount) visible via `?debug=1`. Copier diagnostic inclut le scope.
- **Garantie absolue** : loading→SkeletonCard, error→ErrorState+Réessayer, empty(no site)→message explicite, empty(API)→EmptyByReason+CTA, insufficient→InsufficientPoints, ready→chart.

#### V16-B/C — EmptyByReason enrichi (inclus dans V16-A)
- `EmptyByReason` : cas `noSiteSelected` → message "Aucun site sélectionné — sélectionnez un site dans la barre de filtres".
- CTA contextuels selon raison : no_meter→Connecter, no_readings→Importer, hors période→Étendre à 12 mois.

#### V16-D — Scope coherence
- `ConsumptionDiagPage.jsx` : Export `normalizeId(x)` → `String(x)`. Filtre `filteredInsights` utilise `normalizeId` → plus de mismatch string/number entre API et store.
- Audit MonitoringPage : scope via `scope.siteId` correct ✓. ConsumptionExplorerPage : scope via `selectedSiteId + scopedSites` correct ✓.

#### V16-E — Tests + QA
- `__tests__/V16BlankChart.test.js` (NEW) : 34 tests purs — normalizeId (6), filteredInsights (4), computeSummaryFromInsights (3), MODE_MAP (5), formatDate FR (4), TimeseriesPanel state machine (8), hasMismatch (4).
- `docs/qa-v16.md` (NEW) : Checklist manuelle complète (Explorer/Diagnostic/Monitoring/Régression).

### Résultats
- **718 tests verts**, zéro régression (+34 nouveaux).
- Zone chart : impossible d'être blanche — garantie par `ChartFrame` + state machine exhaustive.
- `?debug=1` : scope global visible dans le panel terminal.
- Scope Explorer/Diagnostic/Monitoring : source unique `useScope()`, filtre robuste avec normalizeId.

---

## Sprint V15 — No-Blank Chart + Scope Cohérence + UX Premium (2026-02-17)

**Objectif** : Corriger 3 défauts post-V14.3 : debug panel toujours vide, scope Diagnostic incohérent, UX Explorer "top monde".

### Commits

#### V15-A — Explorer "No-Blank Chart" + instrumentation
- `TimeseriesPanel.jsx` : `ExplorerDebugPanel` déplacé dans `TimeseriesPanel` (accès au `tsState` de `useEmsTimeseries`). Rendu dans TOUS les états (loading/error/empty/insufficient/ready) quand `?debug=1`.
- `TimeseriesPanel.jsx` : Ajout `min-h-[320px]` wrapper → zéro hauteur=0 impossible.
- `TimeseriesPanel.jsx` : Prop `onRetry` (optionnel, défaut `window.location.reload()`).
- `ExplorerChart.jsx` : Fix `ChartRenderGuard` modes superpose/empile — `hasAnySiteData` vérifie les clés `kwh_<siteId>` avant d'afficher placeholder.
- `ConsumptionExplorerPage.jsx` : Suppression du panel debug standalone (5 lignes) + suppression import `ExplorerDebugPanel`. Prop `onExtendPeriod={() => setDays(365)}` passée aux deux usages de `TimeseriesPanel`.

#### V15-B — Cohérence de scope Diagnostic
- `ConsumptionDiagPage.jsx` : Import `useScope` + déstructuration `{ selectedSiteId, scopeLabel, sitesCount }`.
- Helper exporté `computeSummaryFromInsights(insights)` : recalcule `total_insights`, `sites_with_insights`, `total_loss_kwh`, `total_loss_eur`, `by_type` à partir d'un tableau filtré.
- `filteredInsights` (useMemo) : si `selectedSiteId` → filtre `summary.insights` côté client ; sinon tout.
- `displayedSummary` (useMemo) : `computeSummaryFromInsights(filteredInsights)`.
- `DiagHeader` / `SummaryCards` / `ByTypeBreakdown` utilisent maintenant `displayedSummary` + `filteredInsights`.
- Badge scope : "Périmètre : <scopeLabel>" + badge "Vue filtrée" si site sélectionné.
- Bannière amber (non-bloquante) quand `hasMismatch = isSiteScoped && allInsights.uniqueSites > 1`.

#### V15-C — UX "top monde" (inclus dans V15-A/B)
- `TimeseriesPanel.jsx` : `DataCoverageBadge` inline — N sites · N compteurs · N points · Granularité · Qualité · Source: EMS.
- `TimeseriesPanel.jsx` : `EmptyByReason` enrichi — liste de causes intelligentes, plage de dates si `availability.first_ts`/`last_ts`, CTA "Étendre à 12 mois" via `onExtendPeriod`.

#### V15-D — Tests (10 nouveaux) + DEVLOG
- `__tests__/V15Scope.test.js` (NEW) : 10 tests purs — filteredInsights (4), hasMismatch (4), computeSummaryFromInsights (6), GRAN_LABELS (6), DataCoverageBadge parts (6).
- DEVLOG.md : cette entrée.

### Résultats
- `?debug=1` sur Explorer → debug panel affiche status, n_points, granularity réels.
- Diagnostic "Bureau Paris #01" sélectionné → uniquement ses insights, badge scope + bannière amber si multi-sites.
- EmptyByReason : CTA "Étendre à 12 mois" quand dates disponibles hors période.
- ≥662 tests verts, zéro régression.

---

## Sprint Fix-Ultime — Cohérence Scope Demo Pack (2026-02-18)

**Objectif** : Corriger le bug "36 sites" — charger SCI Les Terrasses (Tertiaire S=10 sites) affichait "36 sites" partout (Dashboard, Vue Executive, Conformité). Source unique de vérité pour l'affichage "N sites".

### Root Cause Chain

1. `ScopeContext` : ordre d'effets React inversé — `getSites` s'exécutait **avant** `setApiScope`, backend recevait `X-Org-Id=1` (Casino) → 36 sites Casino retournés.
2. Fallback `mockSites` dans `orgSites` : quand `effectiveOrgId=1` et `apiSites=[]`, renvoyait 36 sites Casino.
3. `cockpit.py` : fallback `Organisation.first()` → Casino (id=1) quand pas de header.
4. `consumption_diagnostic.py` : idem, pas de lecture du header `X-Org-Id`.

### Fixes déployés

#### Phase 1-FE — ScopeContext.jsx (critique)
- **Inversion ordre effects** : `setApiScope` en 1er (header mis à jour avant l'appel API), `getSites` en 2ème.
- `setApiSites([])` au début de l'effet `getSites` pour nettoyer les données périmées immédiatement.
- **Guard mockSites** : `orgSites` retourne `[]` quand `effectiveOrgId` est défini (même si `apiSites` est vide = chargement en cours) → empêche l'affichage des 36 sites Casino en fallback.
- Même guard dans `scopedSites`.
- `applyDemoScope` vide `apiSites` immédiatement avant le changement de scope.

#### Phase 2-BE — cockpit.py + consumption_diagnostic.py
- `cockpit.py` : fallback DemoState → `Organisation.order_by(id.desc()).first()` (plus récent) à la place de `.first()`.
- `consumption_diagnostic.py` : import `Request`, helper `_get_header_org_id`, chaîne de fallback `X-Org-Id` header → `DemoState` → org la plus récente.

#### Phase 3-FE — ConsumptionDiagPage.jsx
- Passe `org?.id ?? null` explicitement à `getConsumptionInsights()`.

#### Phase 4-FE — ScopeSummary component + pages
- `ScopeSummary.jsx` (NEW) : composant unifié "Nom Org · N sites / chargement… / Site : X". Source unique de vérité.
- `ui/index.js` : export `ScopeSummary`.
- `CommandCenter.jsx` : remplace subtitle manuel par `<ScopeSummary />`.
- `Cockpit.jsx` : idem.

#### Phase 5 — Tests
- `__tests__/DemoScopeUltime.test.js` : 6 nouveaux tests (guard mockSites + ordre d'effets).

### Résultats
- Seed Tertiaire S=10 → "SCI Les Terrasses · 10 sites" affiché partout.
- Seed Casino S=36 → "Groupe Casino · 36 sites" correct.
- Changement de scope org → affichage se met à jour immédiatement sans données périmées.
- **684 tests verts**, zéro régression.

---

## Fix Ultime — Cohérence Demo Pack + Scope Global (2026-02-17)

**Objectif** : Seed S(10) → exactement 10 sites visibles sur TOUTES les pages. Scope org+site appliqué globalement via X-Org-Id/X-Site-Id.

### Causes racines (diagnostic Phase 0)

- `DemoState` ne trackait pas l'org_id → `Organisation.first()` retournait Casino (36 sites) même après seed Tertiaire (10 sites)
- `orchestrator.status()` comptait TOUS les sites sans filtre org
- `dashboard_2min.py` utilisait `Organisation.first()` + comptait tout sans filtre
- `ScopeContext.scopedSites` tombait sur `mockSites` (60 entrées Casino) au lieu de l'API réelle

### Commits

#### Fix-A — DemoState + orchestrator + demo.py
- `demo_state.py` : Extended singleton — `_current_org_id`, `set_demo_org()`, `clear_demo_org()`, `get_demo_org_id()`, `get_demo_context()`
- `orchestrator.py` : `status(org_id)` filtre les sites via join chain `Site→Portefeuille→EntiteJuridique→Organisation`. `seed()` appelle `DemoState.set_demo_org()`. `reset()` appelle `DemoState.clear_demo_org()`
- `demo.py` `/status-pack` : Remplace `Organisation.first()` par `DemoState.get_demo_context()` lookup ; retourne `sites_count`, `pack`, `size` scopés

#### Fix-B — dashboard_2min scope filtering
- `dashboard_2min.py` : `_get_org_id_from_header()`, `_sites_for_org_query()` (join chain)
- Tous les compteurs (total_sites, obligations, risque_total, pertes_conso, pertes_billing, findings) scopés via X-Org-Id

#### Fix-C — ScopeSummary + N sites unifié
- `ScopeSummary.jsx` : Nouveau composant — source unique pour "N sites". Affiche `org.nom — Tous les sites (N)` ou `org.nom — Site : <nom>`
- `CommandCenter.jsx` : Subtitle utilise `sitesCount` (= `orgSites.length`) au lieu de `kpis.total = scopedSites.length`
- `Cockpit.jsx` : Subtitle utilise `sitesCount`
- `ConformitePage.jsx` : Error state subtitle utilise `sitesCount`

### Checklist de cohérence
- [x] Seed S Tertiaire → 10 sites dans `DemoState`, `status-pack`, dashboard, conformité, executive
- [x] Seed M Tertiaire → 20 sites partout
- [x] Reset → 0 sites, DemoState clear
- [x] Sélection site individuel → header = "Site : …", pages = "N sites total"
- [x] Refresh page → scope persisté, N correct
- [x] X-Org-Id injecté par axios interceptor sur toutes les requêtes
- [x] Zéro régression sur les tests existants

---

## Sprint V13 — Parity Lock + Classic UI (2026-02-17)

**Objectif** : Rendre le Consumption Explorer "best-in-class" tout en garantissant zéro régression sur les fonctionnalités historiques.

### Commits

#### V13-A — `useExplorerMode` + bouton de bascule UI
- Nouveau hook `useExplorerMode.js` : persiste le mode UI (`classic` | `expert`) dans le `localStorage`, **jamais** dans l'URL.
- Mode Classic = layout historique avec tous les contrôles visibles sans ouvrir de panneaux supplémentaires.
- Mode Expert = layout actuel Sprint V12 (couches, portfolio, contrôles avancés).
- Bouton de bascule ajouté en haut de `ConsumptionExplorerPage`.

#### V13-BC — `StickyFilterBar v5` (Classic 4 rangs) + `InfoTooltip` + bannière Portfolio
**StickyFilterBar v5 :**
- **Rangée 1** : Sites (chips sélectionnés + bouton +), Énergie, Période, Granularité, badge qualité.
- **Rangée 2** : Pills Mode (Agrège/Superpose/Empile/Sépare) + Pills Unité (kWh/kW/EUR). En Classic : **toujours visibles** (même en mono-site). En Expert : seulement en multi-site/portfolio (comportement V12 préservé).
- **Rangée 3** : Actions (Enregistrer / Effacer / Copier le lien / Presets).
- **Rangée 4** (Classic uniquement) : **Résumé contexte** — `{N}j • {Granularité} • {N} site(s) • {M} compteur(s) • Source: {X} • Qualité: {Q}%`. Placeholders "—" pendant le chargement.

**InfoTooltip :**
- Bulle "?" inline, en survol/focus, texte en français (10 caractères max par bulle).
- Ajoutée sur : Portfolio, Mode pills (4 modes), Unité pills (3 unités).

**Bannière Portfolio :**
- Bannière non-bloquante, dismissible (X), se réaffiche à chaque entrée en Portfolio.
- Message : « Mode Portfolio — vue agrégée multi-sites (mode Agrégé uniquement). »

**Chaîne de caractères harmonisée :**
- `Electricite` → `Électricité`, `Granularite` → `Granularité`, `releves` → `relevés`.

#### V13-D — Tests (UIModeParity.test.js)
- `useExplorerMode` : 8 tests (defaults, persistence, toggle, rejette les valeurs invalides).
- `ResumeContexte Row 4` : 13 tests (YTD, pluriel site/compteur, source, qualité, caps).
- URL state : 5 tests vérifiant que `uiMode` n'apparaît **jamais** dans les paramètres URL.
- Parity Classic/Expert : 8 tests (contrôles visibles, mode pills, résumé contexte).
- Portfolio banner : 2 tests (affichage, reset).

**Total : +36 tests → 593 tests, tous verts.**

### Checklist de parité (non-régressions)
- [x] Sélection de site : chips mono + multi (add/remove, max 5) + menu recherche
- [x] Bascule énergie : Électricité / Gaz
- [x] Pills période : 7j/30j/90j/12m/YTD + plage de dates personnalisée
- [x] Sélecteur de granularité (auto, read-only)
- [x] Modes : Agrège / Superpose / Empile / Sépare
- [x] Unités : kWh / kW / EUR (axe + calculs)
- [x] Couches : Tunnel, Objectifs, Talon, Météo, Signature
- [x] Brush / mini-timeline (> 20 points)
- [x] Presets save/load/delete + Effacer + Copier le lien
- [x] Sync URL (rechargement préserve l'état)
- [x] uiMode ne modifie pas l'URL
- [x] Zéro erreur console, build clean

---

## Sprint V12 — Portfolio + OverviewRow + Chart State Machine (2026-02-16)

- `StickyFilterBar v4` : chips uniquement des sites sélectionnés, `SiteSearchDropdown`, toggle Portfolio.
- `OverviewRow` : total_kwh, avg, pic, talon, hors-horaires, CO2e.
- `PortfolioPanel` : `AggregateChart` + 3 tables de classement (conso/dérive/hors-horaires) + MiniSparklines.
- Machine à états du graphique : loading / ready / empty / blocked.
- +25 tests → 527 tests.

## Sprint V11.1 — Parity Lock Consumption Explorer (2026-02-15)

- `StickyFilterBar v3` : pills période (7j/30j/90j/12m/YTD), plages de dates, Save/Reset/Copy.
- `ExplorerChart` : Recharts Brush, rangée résumé.
- `useExplorerPresets` : localStorage.
- Fix KB backend : POST /search + GET /stats.
- 492 → 527 tests.

## Fix Critique Demo Scope (2026-02-17)

- `ScopeContext` : `scopedSites` utilise les vraies API sites, non plus `mockSites`. Expose `orgSites` et `sitesCount`.
- `api.js` : `setApiScope()` + intercepteur axios inject `X-Org-Id` / `X-Site-Id`.
- `ScopeSwitcher` : sélecteur de site (Tous les sites / site individuel).
- Backend `cockpit.py` + `sites.py` : filtrage par `X-Org-Id` via join `Site→Portefeuille→EntiteJuridique→Organisation`.
- +30 tests → 557 tests.
