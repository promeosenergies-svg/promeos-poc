# DEVLOG PROMEOS

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
