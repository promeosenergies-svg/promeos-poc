# Audit navigation & routes — branche `claude/refonte-visuelle-sol`

Snapshot local HEAD = branche `claude/refonte-visuelle-sol` (2026-04-22,
`+93` commits vs `origin/main`). Même périmètre que
[audit-navigation-main-2026-04-22.md](audit-navigation-main-2026-04-22.md) :
cartographie navigation (NavRegistry V7) + routes (React Router) + shell.
Les deux serveurs de dev tournent (8001/5173) — smoke captures existantes
dans [tools/playwright/captures/sol-refonte-smoke/](tools/playwright/captures/sol-refonte-smoke/)
(31 steps).

## 0. Résumé des changements vs main

La refonte visuelle Sol remplace le shell (`AppShell` → `SolAppShell`),
réécrit le rail/panel (composants `SolRail` / `SolPanel` / `SolTimerail` /
`SolCartouche`) et migre **7 pages top-level** vers leur variante `*Sol`
avec un pattern A/B : la route canonique sert la version Sol, une route
`-legacy` sert l'ancienne version en miroir. Le NavRegistry V7 lui-même
évolue peu (même 6 modules, même ordering par rôle) : l'essentiel du delta
est dans `ROUTE_MODULE_MAP`, `App.jsx`, et l'ajout de la nouvelle
primitive `PANEL_DEEP_LINKS_BY_ROUTE`.

| Axe                              | main (`ec15f0bb`) | branch (`HEAD`)        | Δ         |
|----------------------------------|-------------------|------------------------|-----------|
| Routes React réelles             | 51                | **62**                 | +11       |
| Redirections `<Navigate>`        | 28                | 29                     | +1        |
| Entrées `ROUTE_MODULE_MAP`       | 44                | 56                     | +12       |
| Routes `-legacy` A/B             | 1 (`sites-legacy`)| **9**                  | +8        |
| Items NAV_SECTIONS (normal)      | 13                | 13                     | —         |
| Items NAV_SECTIONS (expert)      | 17                | 17                     | —         |
| HIDDEN_PAGES                     | 7                 | 7                      | —         |
| COMMAND_SHORTCUTS                | 10                | 10                     | —         |
| QUICK_ACTIONS                    | 15                | 15                     | —         |
| `PANEL_DEEP_LINKS_BY_ROUTE`      | ∅                 | **8 deep-links / 3 routes** | nouveau |
| Shell                            | AppShell (glass)  | **SolAppShell (grid)** | rewrite   |
| Rail / Panel                     | `NavRail` 64 / `NavPanel` 190-230 | **`SolRail` 56 / `SolPanel` 240** | rewrite |
| Timerail                         | —                 | **`SolTimerail` 36px** | nouveau   |
| Cartouche                        | —                 | **`SolCartouche`**     | nouveau   |

## 1. Architecture générale

### 1.1 Shell — `SolAppShell` ([frontend/src/layout/SolAppShell.jsx:449](frontend/src/layout/SolAppShell.jsx#L449))

Grid CSS 3×2 — `56px | 240px | 1fr` pour la largeur, `1fr | 36px` pour la
hauteur.

```
┌──────┬────────┬───────────────────────────────────┐
│ rail │ panel  │ main (header-sol 40px + outlet)   │
│ 56px │ 240px  │                                   │
├──────┴────────┴───────────────────────────────────┤
│  timerail 36px                                    │
└───────────────────────────────────────────────────┘
```

- **`SolRail`** ([frontend/src/ui/sol/SolRail.jsx](frontend/src/ui/sol/SolRail.jsx))
  — 56 px, logo « P. » Fraunces en tête, puis les icônes modules via
  `getOrderedModules(role, isExpert)`, `resolveModule(pathname)` pour l'actif.
  Chaque clic `navigate(MODULE_FIRST_ROUTE[key])` — **symétrique pour les 6
  modules** (vs. `MODULE_LANDING = { energie: '/consommations' }` unique sur
  main).
- **`SolPanel`** ([frontend/src/ui/sol/SolPanel.jsx](frontend/src/ui/sol/SolPanel.jsx))
  — 240 px fixe, titre module + description, sections rendues via la
  nouvelle fonction `getPanelSections(pathname, isExpert)` (§ 4.3), items
  cliquables directs (plus de pins, ni recents, ni site search inline ni
  progress bars DT/BACS/APER comme sur main `NavPanel`). Slots
  `headerSlot` / `footerSlot` injectés par `SolAppShell` pour le
  ScopeSwitcher et le UserMenu.
- **`SolAppShellHeader`** — hauteur 40 px (vs ~56-60 px main), 3 éléments
  seulement : CommandPalette trigger (⌘K) + bell Action Center + Toggle
  Expert. Breadcrumb, `DataReadinessBadge`, scope switcher **retirés du
  header** et absorbés dans le panel.
- **`SolTimerail`** ([frontend/src/ui/sol/SolTimerail.jsx](frontend/src/ui/sol/SolTimerail.jsx))
  — nouvelle barre fixe bas, 36 px.
- **`SolCartouche`** ([frontend/src/ui/sol/SolCartouche.jsx](frontend/src/ui/sol/SolCartouche.jsx))
  — nouvelle cartouche bas-droit.
- **Route hors shell** `/_sol_showcase` — démo Gate 1 (21 composants Sol,
  auth requis mais sans SolAppShell).
- **Raccourci** `Ctrl+Shift+X` désormais câblé dans `SolAppShell` (plus
  uniquement par CommandPalette comme sur main).

### 1.2 Pages migrées Sol (pattern A/B)

Chaque ligne : **route canonique → composant Sol** (principal) + **route
`-legacy` → composant legacy** (A/B comparaison, horizon suppression Lot 10).

| Route canonique       | Composant Sol          | Route legacy                 | Composant legacy       |
|-----------------------|------------------------|------------------------------|------------------------|
| `/`                   | `CommandCenterSol`     | `/home-legacy`               | `CommandCenter`        |
| `/cockpit`            | `CockpitSol`           | `/cockpit-legacy`            | `Cockpit`              |
|                       | (+ `/cockpit-fixtures` → `CockpitRefonte` démo) |              |                        |
| `/monitoring`         | `MonitoringSol`        | `/monitoring-legacy`         | `MonitoringPage`       |
| `/patrimoine`         | `PatrimoineSol`        | `/patrimoine-legacy`         | `Patrimoine`           |
| `/conformite`         | `ConformiteSol`        | `/conformite-legacy`         | `ConformitePage`       |
| `/conformite/aper`    | `AperSol`              | `/conformite/aper-legacy`    | `AperPage`             |
| `/bill-intel`         | `BillIntelSol`         | `/bill-intel-legacy`         | `BillIntelPage`        |
| `/achat-energie`      | `AchatSol`             | `/achat-energie-legacy`      | `PurchasePage`         |

Total : **8 pages migrées** (+ 1 fixtures démo + 1 showcase). Certaines
pages Sol supplémentaires existent sur disque (AnomaliesSol,
CompliancePipelineSol, ConformiteTertiaireSol, ContratsSol,
DiagnosticConsoSol, EfaSol, KBExplorerSol, RegOpsSol, RenouvellementsSol,
SegmentationSol, Site360Sol, UsagesHorairesSol, UsagesSol, WatchersSol)
mais **pas encore câblées dans `App.jsx`** — à vérifier par le propriétaire
du sprint.

### 1.3 Config inchangée vs main

- 6 modules (Cockpit, Conformité, Énergie, Patrimoine, Achat, Admin) —
  mêmes tints, mêmes libellés, même `ROLE_MODULE_ORDER` pour les 7 rôles
  + default.
- `NAV_SECTIONS` identique sur le fond (13 items normal / 17 items expert).
  Un seul libellé changé : `Performance énergétique` → **`Monitoring`** sur
  l'item `/monitoring` (§ module Énergie).
- `HIDDEN_PAGES`, `COMMAND_SHORTCUTS`, `QUICK_ACTIONS` : inchangés.
- `ALL_MAIN_ITEMS`, `NAV_MAIN_SECTIONS`, `NAV_ADMIN_ITEMS`,
  `ROUTE_SECTION_MAP` : dérivés identiques.

## 2. Inventaire routes React Router (62)

### 2.1 Routes réelles enregistrées (62)

Listing brut de `<Route path="…">` non-redirect, non-catch :

```
/                               /consommations
/_sol_showcase                  /consommations/explorer
/achat-energie                  /consommations/import
/achat-energie-legacy           /consommations/kb
/action-center                  /consommations/portfolio
/actions                        /contrats
/actions/:actionId              /diagnostic-conso
/actions/new                    /home-legacy
/activation                     /import
/admin/assignments              /kb
/admin/audit                    /login
/admin/cx-dashboard             /monitoring
/admin/enedis-health            /monitoring-legacy
/admin/kb-metrics               /notifications
/admin/roles                    /onboarding
/admin/users                    /onboarding/sirene
/anomalies                      /patrimoine
/bill-intel                     /patrimoine-legacy
/bill-intel-legacy              /payment-rules
/billing                        /portfolio-reconciliation
/cockpit                        /regops/:id
/cockpit-fixtures               /renouvellements
/cockpit-legacy                 /segmentation
/compliance/pipeline            /sites/:id
/compliance/sites/:siteId       /status
/conformite                     /usages
/conformite-legacy              /usages-horaires
/conformite/aper                /watchers
/conformite/aper-legacy
/conformite/tertiaire
/conformite/tertiaire/anomalies
/conformite/tertiaire/efa/:id
/conformite/tertiaire/wizard
/connectors
```

### 2.2 Redirections `<Navigate>` (29)

Idem main + `/action-plan → /anomalies` réintroduit, pas de nouvelle.
Commentaire explicite ajouté dans App.jsx :
> _« URL aliases → canonical routes. Horizon suppression post-Lot 10.
> Inventaire : docs/audit/nav_legacy_redirects.md »_

Inventaire détaillé des 22 alias « actifs » dans
[docs/audit/nav_legacy_redirects.md](docs/audit/nav_legacy_redirects.md).

### 2.3 Catch-all

`path="*"` → [NotFound](frontend/src/pages/NotFound.jsx) (inchangé).

## 3. Entrée `ROUTE_MODULE_MAP` (56)

12 entrées ajoutées vs main :

| Entrée                      | Module       | Motivation                    |
|-----------------------------|--------------|-------------------------------|
| `/home-legacy`              | cockpit      | A/B legacy                    |
| `/cockpit-legacy`           | cockpit      | A/B legacy                    |
| `/conformite-legacy`        | conformite   | A/B legacy                    |
| `/monitoring-legacy`        | energie      | A/B legacy                    |
| `/patrimoine-legacy`        | patrimoine   | A/B legacy                    |
| `/sites-legacy/:id`         | patrimoine   | A/B legacy                    |
| `/bill-intel-legacy`        | patrimoine   | A/B legacy                    |
| `/achat-energie-legacy`     | achat        | A/B legacy                    |
| `/admin/kb-metrics`         | admin        | **comble orphelin main §5.2** |
| `/admin/cx-dashboard`       | admin        | **comble orphelin main §5.2** |
| `/admin/enedis-health`      | admin        | **comble orphelin main §5.2** |

Commentaire inline explicatif pour la sécurité pré-redirect sur
`/compliance`, et pour le contexte patrimoine de `/onboarding/sirene`.

> ⚠️ **`/conformite/aper-legacy` manquant de `ROUTE_MODULE_MAP`** — la
> route React existe ([App.jsx:296](frontend/src/App.jsx#L296)) mais
> aucune entrée dédiée. Le fallback préfixe (`/conformite` → `conformite`)
> fonctionne, donc le rail reste vert et la page se rend, mais c'est
> incohérent avec les 7 autres `-legacy`. Oubli mineur à combler pour
> respecter l'invariant documenté dans
> [tests NavRegistry L387-394](frontend/src/layout/__tests__/NavRegistry.test.js#L387).

## 4. Croisement Nav → Routes

### 4.1 Tous les items NAV_SECTIONS + deep-links résolvent ✅

34 cibles NAV_SECTIONS + QUICK_ACTIONS + COMMAND_SHORTCUTS + HIDDEN_PAGES
+ **8 deep-links `PANEL_DEEP_LINKS_BY_ROUTE`** : toutes résolvent vers une
route réelle ou un redirect actif. Zéro lien mort dans les menus.

### 4.2 Routes orphelines (5 — n'apparaissent nulle part en nav/map/redirect)

| Route                      | Statut                                                              |
|----------------------------|---------------------------------------------------------------------|
| `/_sol_showcase`           | Gate 1 Sol — route démo/debug, volontaire                           |
| `/cockpit-fixtures`        | Démo fixtures CockpitRefonte, volontaire (note App.jsx)             |
| `/conformite/aper-legacy`  | Route A/B **non mappée** (oubli § 3) — fallback préfixe fonctionne  |
| `/consommations/kb`        | Sous-tab atteint via tabs `/consommations` (OK, UI interne)         |
| `/login`                   | Publique, hors shell (OK)                                           |

### 4.3 Routes admin orphelines du panel (6 — pas dans NAV_SECTIONS admin)

Mappées dans `ROUTE_MODULE_MAP`, rendues par `App.jsx`, mais **absentes**
de l'item list `admin-data` du panel ([NavRegistry.js:710-742](frontend/src/layout/NavRegistry.js#L710-L742)).

| Route                      | Exposition                                                 |
|----------------------------|------------------------------------------------------------|
| `/admin/audit`             | QUICK_ACTIONS (« Journal d'audit ») + URL directe          |
| `/admin/roles`             | URL directe uniquement                                     |
| `/admin/assignments`       | URL directe uniquement                                     |
| `/admin/kb-metrics`        | URL directe uniquement                                     |
| `/admin/cx-dashboard`      | URL directe uniquement                                     |
| `/admin/enedis-health`     | URL directe uniquement                                     |

Panel Admin liste uniquement 4 items : `/import`, `/admin/users`,
`/watchers`, `/status` (clé `system` regroupant connecteurs/kb/segmentation
via mot-clés, sans sous-items). Les 6 routes ci-dessus sont atteignables
par tapage URL + `Ctrl+K` pour `/admin/audit` uniquement.

> 🔧 Recommandation : ajouter 5 items expert à `NAV_SECTIONS.admin-data`
> (ou à `HIDDEN_PAGES` pour remontée CommandPalette à minima).

### 4.4 Entrées `ROUTE_MODULE_MAP` sans route réelle (3 — 404, **persistant**)

| Entrée                 | Résolveur de module | Route React |
|------------------------|---------------------|-------------|
| `/conformite/dt`       | ✅ conformite       | ❌ 404      |
| `/conformite/bacs`     | ✅ conformite       | ❌ 404      |
| `/conformite/audit-sme`| ✅ conformite       | ❌ 404      |

**Inchangé vs main** — même finding, toujours ouvert. L'audit
[docs/audit/deep_links_panel_triage.md](docs/audit/deep_links_panel_triage.md)
évoque ces 3 targets pour Vague 2 mais elles restent un risque UX : rail
teinté émeraude → NotFound.

> 🔧 Recommandation : câbler `<Navigate
> to="/conformite?tab=obligations&focus=dt|bacs|audit-sme">`, ou retirer
> du map si abandon confirmé.

## 5. `PANEL_DEEP_LINKS_BY_ROUTE` — nouvelle primitive (additive)

Feature introduite pendant le sprint refonte (commits `9b56e1a2`,
`ec15f0bb`, `1f8ca21e`, `ff2454f4`) — après un aller-retour doctrinal :
une version antérieure `PANEL_SECTIONS_BY_ROUTE` avait divergé du SSOT
`NAV_SECTIONS` (labels concurrents, items cachés ré-exposés), elle a été
vidée puis remplacée par un modèle **purement additif et paramétré**.

### 5.1 Contrat

- Schéma entrée : `{ href, label, hint? }[]`
- Uniquement query params (`?tab=`, `?filter=`, `?horizon=`, `?fw=`) ou
  sous-paths absents des items top-level `NAV_SECTIONS`.
- Zéro duplication de label top-level (garde-fou test).
- Zéro ré-exposition d'items cachés.
- Merge **additif** : `getPanelSections()` retourne SSOT d'abord, puis
  append une section « Raccourcis » si la route a des deep-links.
- Invariant testé : [panel_deep_links_invariant.test.js](frontend/src/layout/__tests__/panel_deep_links_invariant.test.js)
  + [panel_deep_links_vague1.test.js](frontend/src/layout/__tests__/panel_deep_links_vague1.test.js).

### 5.2 Contenu actuel (Vague 1 = 8 deep-links / 3 routes)

| Route                | Deep-links                                                                                            |
|----------------------|-------------------------------------------------------------------------------------------------------|
| `/anomalies`         | `?fw=DECRET_TERTIAIRE` · `?fw=FACTURATION` · `?fw=BACS`                                               |
| `/renouvellements`   | `?horizon=90` · `?horizon=180` · `?horizon=365`                                                       |
| `/conformite/aper`   | `?filter=parking` · `?filter=toiture`                                                                 |

Triage détaillé pour la Vague 2 (16 divergences + 9 experts + 4 items
cachés) : [docs/audit/deep_links_panel_triage.md](docs/audit/deep_links_panel_triage.md).

## 6. Matrice rôles → permissions (⚠️ identique à main)

**Même bug de cohérence que sur main.** Le code `NavPanel.filterItems`
(version main) n'est plus exécuté dans le shell Sol — `SolPanel` utilise
`getPanelSections()` qui n'applique **aucun filtre `hasPermission`** ; il
filtre uniquement `expertOnly` via `getVisibleItems()`. Conséquence :

> 🚨 **Régression potentielle** : sur le shell Sol, tous les rôles voient
> désormais **tous les items** (y compris les modules pour lesquels ils
> n'ont pas la permission `view`). Le bug main §7 disparaît par effet de
> bord… mais la sécurité « nav-level » des rôles restreints aussi.

Exemples concrets (à valider avec le métier) :

| Rôle              | View backend                                        | Avant (main)           | Maintenant (Sol)        |
|-------------------|-----------------------------------------------------|------------------------|-------------------------|
| `prestataire`     | patrimoine, consommations, monitoring               | Patrimoine OK, autres filtrés (bug) | **Tous modules visibles** |
| `resp_conformite` | conformite, actions, reports                        | Conformité OK          | **Tous modules visibles** |
| `acheteur`        | purchase, billing, actions                          | Tout filtré (bug)      | **Tous modules visibles** |

Deux lectures possibles :
- **A. Intentionnel** : on délègue le check d'accès à l'API (backend
  refuse 403) et on simplifie le nav.
- **B. Régression** : la sécurité UX « rôles ne voient pas ce qu'ils ne
  peuvent pas faire » a été perdue.

> 🔧 Recommandation : trancher A vs B. Si B, ré-introduire filtre
> `hasPermission` dans `SolPanel.items` (attention : nécessite résoudre le
> mismatch de clés identifié sur main §7 — module NavRegistry
> (`energie`/`achat`) vs capability backend (`consommations`/`purchase`)).

## 7. Backend — inchangé vs main

Aucun changement détecté sur la branche dans `backend/routes/*` pour la
couche navigation — 65 prefixes `/api/...` identiques (cf.
[audit-navigation-main §8](audit-navigation-main-2026-04-22.md#8-backend--inventaire-des-prefixes-api-api)).
Le split Sol porte uniquement sur la couche présentation frontend.

## 8. Accessibilité & UX

### 8.1 Points solides conservés

- **Skip link** `#main-content` présent dans `SolAppShell` (style fallback
  inline, pas Tailwind).
- `role="navigation"`, `aria-label="Navigation principale"` sur `SolRail`,
  `aria-label="Navigation contextuelle"` sur `SolPanel`.
- `aria-current="page"` sur le module actif (rail) et sur l'item actif
  (panel).
- `aria-label`, `title` sur toutes les icônes rail.
- Toggle Expert avec `aria-label="Basculer mode expert (Ctrl+Shift+X)"`.
- CommandPalette ⌘K + raccourcis Ctrl+Shift+* identiques.

### 8.2 Points d'attention nouveaux

- **Focus rings** : l'ancien `NavPanel` a des
  `focus-visible:ring-2 focus-visible:ring-blue-500` systématiques.
  `SolPanel` utilise des styles inline sans `:focus-visible` visible —
  ne pas vérifié dans le code lu § 1.1 pour les boutons items. À vérifier
  sur les captures Playwright.
- **Keyboard nav Up/Down** entre items du panel : présente sur `NavPanel`
  main ([NavPanel.jsx:463](frontend/src/layout/NavPanel.jsx#L463)),
  **absente** de `SolPanel` (pas de `onKeyDown` détecté). Navigation Tab
  uniquement.
- **Skip link `SolAppShell`** : style `{position:absolute, left:-9999}`
  — ancien pattern pre-`.sr-only` utility. Focus-visible non géré, donc
  le lien reste invisible même au focus clavier : régression a11y. Sur
  main, `AppShell` utilise
  `focus:not-sr-only focus:absolute focus:z-[300] focus:top-2 focus:left-2 focus:px-4 …`.
- **Pins, Recents, Site search inline** (`NavPanel` main) : **disparus**
  dans `SolPanel`. Site search reste disponible via `ScopeSwitcher`
  header + recherche CommandPalette.
- **Progress bars DT/BACS/APER** (conformité) : disparues de `SolPanel`.
- **Mobile / Drawer** : `SolAppShell` est grid fixe. Pas de `useMediaQuery`
  détecté, pas de Drawer mobile. La responsivité < 768 px est
  probablement dégradée (3-col grid qui ne s'adapte pas). À vérifier sur
  `step11_responsive_1280x720.png` mais ce breakpoint est desktop.

> 🔧 Recommandations :
> 1. Restaurer le skip link fonctionnel (`:focus-visible` qui le ramène
>    à `left:0`).
> 2. Ajouter `onKeyDown` Up/Down dans `SolPanel` (parité avec `NavPanel`).
> 3. Valider comportement mobile (< 768 px) — worst case, reconnecter
>    `useMediaQuery` + Drawer.
> 4. Restaurer les `focus-visible:ring` sur les boutons items.

## 9. Tests de navigation

Couvrent la branche :

- [NavRegistry.test.js:379-394](frontend/src/layout/__tests__/NavRegistry.test.js#L379-L394)
  — `matchRouteToModule` pour les 8 routes `-legacy` (oublie
  `/conformite/aper-legacy` § 3).
- [panel_deep_links_invariant.test.js](frontend/src/layout/__tests__/panel_deep_links_invariant.test.js)
  — contrat SSOT du § 5 (pas de duplication, pas d'items cachés ré-exposés).
- [panel_deep_links_vague1.test.js](frontend/src/layout/__tests__/panel_deep_links_vague1.test.js)
  — shape Vague 1 (3 routes, 8 entrées).
- [routeMatching.test.js](frontend/src/layout/__tests__/routeMatching.test.js)
  — score du pattern matcher.
- [nav_v7_parity.test.js](frontend/src/__tests__/nav_v7_parity.test.js)
  — parité V7.
- [nav_a11y.test.js](frontend/src/__tests__/nav_a11y.test.js) — axe-core.
- [sol_components.source.test.js](frontend/src/ui/sol/__tests__/sol_components.source.test.js)
  — source-guards des composants Sol.

Non couverts par les tests actuels (à compléter) :

- Présence d'une route React pour chaque entrée `ROUTE_MODULE_MAP` (le bug
  § 4.4 passe donc à travers).
- Présence d'un item Admin ou d'un `HIDDEN_PAGES` pour chaque route
  `/admin/*` enregistrée (pour éviter l'orphelin § 4.3).
- `hasPermission` × rôles restreints × modules Nav (§ 6).

## 10. Captures Playwright existantes

[tools/playwright/captures/sol-refonte-smoke/](tools/playwright/captures/sol-refonte-smoke/)
— 31 steps (step00 → step31) qui couvrent :

- step00-08 : Command Center, Cockpit, panel items, Conformité, Bill Intel,
  Patrimoine (+ filter + drilldown), Achat.
- step09-10 : ⌘K palette + Ctrl+Shift+X expert mode.
- step11 : responsive 1280×720.
- step12 : deep-link bill-intel (vérifie §5).
- step20-28 : Aper, Monitoring, Site360 (Pattern C), RegOps, EFA,
  Diagnostic (Pattern A), Anomalies (Pattern B), Contrats, Renouvellements.
- step29-31 : Usages, Usages horaires, Watchers (Pattern B prelude).

Couverture runtime de la nav majoritairement saine. **Manquant** : captures
pour les 6 routes Admin orphelines § 4.3, les 3 `/conformite/*` cassées
§ 4.4, et un test A/B côte-à-côte `/cockpit` vs `/cockpit-legacy`.

## 11. Synthèse des findings (branche)

### P0 (à clarifier avec métier)

1. **Filtre permissions nav absent en shell Sol § 6** — `SolPanel`
   n'applique plus `hasPermission('view', module)`. Soit délégation
   API-only intentionnelle (à documenter), soit régression sécurité UX
   (à corriger en résolvant au passage le mismatch de clés identifié sur
   main §7).

### P1 (dette technique contenue)

2. **3 deep-links `/conformite/dt|bacs|audit-sme` cassés (persistant) §4.4**
   — identiques à main, toujours ouverts. Triage Vague 2.

3. **6 routes Admin orphelines du panel § 4.3** — `/admin/audit`,
   `/admin/roles`, `/admin/assignments`, `/admin/kb-metrics`,
   `/admin/cx-dashboard`, `/admin/enedis-health` visibles uniquement par
   URL directe (5/6 sans aucun raccourci).

4. **a11y régressions § 8.2** — skip link cassé, pas de Tab/Shift+Tab
   explicite, pas de navigation clavier Up/Down dans `SolPanel`, focus
   ring absent sur items. Perte vs shell main.

5. **Responsive mobile < 768 px non couvert § 8.2** — grid 3-col fixe de
   `SolAppShell`, pas de Drawer. À valider sur petit écran.

### P2 (polish)

6. **`/conformite/aper-legacy` absent de `ROUTE_MODULE_MAP` § 3** —
   oubli unique parmi les 9 pairs `-legacy`. Test d'invariant § 9 à
   étendre.

7. **`SolPanel` a perdu des features NavPanel** : pins, recents, site
   search inline, progress bars Conformité. Choix design assumé (panel
   minimal) mais à documenter dans le changelog.

8. **14 pages Sol présentes sur disque, non câblées dans App.jsx** —
   `AnomaliesSol`, `ContratsSol`, `DiagnosticConsoSol`, `EfaSol`,
   `KBExplorerSol`, `RegOpsSol`, `RenouvellementsSol`, `SegmentationSol`,
   `Site360Sol`, `UsagesHorairesSol`, `UsagesSol`, `WatchersSol`,
   `ConformiteTertiaireSol`, `CompliancePipelineSol`. Code mort tant
   qu'elles ne sont pas importées — à nettoyer ou à wiring.

### Non-issues

- 8 routes `-legacy` + `/cockpit-fixtures` + `/_sol_showcase` : chemin
  assumé du sprint refonte, documenté dans les commit messages et les
  commentaires App.jsx.
- `NAV_SECTIONS`/`HIDDEN_PAGES`/`QUICK_ACTIONS`/`COMMAND_SHORTCUTS` :
  inchangés, aucune divergence d'intentions vs V7.

## 12. Delta detaillé vs main

| Catégorie                 | main          | branche      | Commentaire |
|---------------------------|---------------|--------------|-------------|
| `App.jsx` lignes          | 634           | **754**      | +120 (legacy routes + showcase + imports Sol) |
| `NavRegistry.js` lignes   | 990           | **1119**     | +129 (deep-links + legacy entries + helpers) |
| Shell lignes              | 393 (AppShell)| **608** (SolAppShell) + 403 legacy conservé | refonte |
| Rail composant            | `NavRail` 92L | **`SolRail` 90L** | rewrite style inline |
| Panel composant           | `NavPanel` 699L | **`SolPanel` 186L** | **-513L** (features retirées) |
| Pages Sol                 | 0             | 22 `*Sol.jsx` | 8 câblées + 14 en attente |
| Tests navigation          | 6 fichiers    | +2 (`panel_deep_links_*`) | nouveau contrat |

## 13. Angle non couvert

- **Performance** : bundle cockpit / patrimoine / conformite post-Sol
  (réécrites, potentiellement plus légères ou plus lourdes). Non mesuré.
- **Runtime tests E2E Playwright** : captures existantes OK mais pas
  couvrant les régressions a11y § 8.2. À étendre.
- **Parité visuelle côté-à-côté** A/B : aucune capture « same viewport,
  sol vs legacy » dans le dossier smoke.

---

_Rapport généré depuis l'arbre de travail branche
`claude/refonte-visuelle-sol` (HEAD = `ec129bf9`, +93 commits vs
`origin/main`) — 2026-04-22._
