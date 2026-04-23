# Audit navigation & routes — branche `main` (snapshot 2026-04-22)

Périmètre : architecture de navigation et cartographie des routes du POC côté
frontend (React Router + NavRegistry V7) et backend (FastAPI prefixes), lus
depuis `git show main:...` (HEAD main = `ec15f0bb`). Le stack en cours
d'exécution (ports 8001/5173) tourne sur `claude/refonte-visuelle-sol` et
diverge de main de 93 commits — cet audit est statique, sans capture Playwright.

## 1. Architecture générale

- **Shell** : [AppShell.jsx](frontend/src/layout/AppShell.jsx) compose
  `Sidebar` (Rail + Panel) + `Header` (Breadcrumb, ScopeSwitcher,
  DataReadinessBadge, CommandPalette trigger, Centre d'actions, Toggle Expert,
  UserMenu) + `Outlet`.
- **Rail** 64 px : [NavRail.jsx](frontend/src/layout/NavRail.jsx), 5 modules
  visibles (+1 admin en mode expert), ordering role-based.
- **Panel** contextuel 190-230 px : [NavPanel.jsx](frontend/src/layout/NavPanel.jsx)
  avec items tintés par module, pins, recents, quick actions, badges.
- **CommandPalette** (`Ctrl+K`) — source complète `ALL_MAIN_ITEMS` +
  `COMMAND_SHORTCUTS` (10 raccourcis Ctrl+Shift+*).
- **Mobile** : `useMediaQuery('(min-width: 768px)')` → Sidebar dans un
  `Drawer` + hamburger header.
- **Auth shell** : `RequireAuth` protège tout sauf `/login`.
- **Code-split** : 100 % des pages lazy-loaded avec `<PageSuspense>` (skeleton
  cards).

## 2. Modules de navigation (V7)

| # | Module       | Key          | Tint    | Expert | Ordre | Label            |
|---|--------------|--------------|---------|--------|-------|------------------|
| 1 | Cockpit      | `cockpit`    | blue    | non    | 1     | Accueil          |
| 2 | Conformité   | `conformite` | emerald | non    | 2     | Conformité       |
| 3 | Énergie      | `energie`    | indigo  | non    | 3     | Énergie          |
| 4 | Patrimoine   | `patrimoine` | amber   | non    | 4     | Patrimoine       |
| 5 | Achat        | `achat`      | violet  | non    | 5     | Achat            |
| 6 | Admin        | `admin`      | slate   | **oui**| 6     | Administration   |

13 items en mode normal, 17 en mode expert (+4 : audit-sme, diagnostics,
facturation, simulateur). 3 items supprimés du menu et déplacés dans le Centre
d'actions (cloche) : Actions, Suivi, Notifications.

## 3. Ordering par rôle

Défini dans `ROLE_MODULE_ORDER` de
[NavRegistry.js:777](frontend/src/layout/NavRegistry.js#L777). 7 rôles custom
+ default. Le rail ré-ordonne les icônes selon le rôle connecté. Exemples :

| Rôle                | Ordre                                           |
|---------------------|-------------------------------------------------|
| `dg_owner`          | cockpit → achat → conformite → patrimoine → energie |
| `daf`               | cockpit → patrimoine → achat → conformite → energie |
| `acheteur`          | cockpit → achat → patrimoine → conformite → energie |
| `energy_manager`    | cockpit → energie → conformite → patrimoine → achat |
| `resp_conformite`   | cockpit → conformite → patrimoine → energie → achat |
| `resp_site`         | cockpit → patrimoine → energie → conformite → achat |
| default             | cockpit → conformite → energie → patrimoine → achat |

## 4. Inventaire des routes React Router (main)

### 4.1 Routes réelles enregistrées (51)

```
/                                   /monitoring
/achat-energie                      /notifications
/action-center                      /onboarding
/actions                            /onboarding/sirene
/actions/:actionId                  /patrimoine
/actions/new                        /payment-rules
/activation                         /portfolio-reconciliation
/admin/assignments                  /regops/:id
/admin/audit                        /renouvellements
/admin/cx-dashboard                 /segmentation
/admin/enedis-health                /sites/:id
/admin/kb-metrics                   /status
/admin/roles                        /usages
/admin/users                        /usages-horaires
/anomalies                          /watchers
/bill-intel                         /conformite
/billing                            /conformite/aper
/cockpit                            /conformite/tertiaire
/compliance/pipeline                /conformite/tertiaire/anomalies
/compliance/sites/:siteId           /conformite/tertiaire/efa/:id
/connectors                         /conformite/tertiaire/wizard
/consommations                      /consommations/explorer
/consommations/import               /consommations/kb
/consommations/portfolio            /contrats
/diagnostic-conso                   /import
/kb                                 /login
```

### 4.2 Redirections `<Navigate>` (28)

URL humaines / legacy vers URL canoniques — tous OK.

| Source                  | Cible                             |
|-------------------------|-----------------------------------|
| `/patrimoine/nouveau`   | `/patrimoine?wizard=open`         |
| `/sites`                | `/patrimoine`                     |
| `/sites-legacy/:id`     | `/patrimoine`                     |
| `/dashboard-legacy`     | `/`                               |
| `/dashboard`            | `/cockpit`                        |
| `/executive`            | `/cockpit`                        |
| `/synthese`             | `/cockpit`                        |
| `/compliance`           | `/conformite`                     |
| `/compliance/sites`     | `/conformite`                     |
| `/achat-assistant`      | `/achat-energie?tab=assistant`    |
| `/achats`, `/purchase`  | `/achat-energie`                  |
| `/factures`             | `/bill-intel`                     |
| `/facturation`          | `/billing`                        |
| `/diagnostic`           | `/diagnostic-conso`               |
| `/performance`          | `/monitoring`                     |
| `/referentiels`         | `/kb`                             |
| `/conso`, `/ems`, `/explorer` | `/consommations/portfolio`  |
| `/imports`              | `/import`                         |
| `/connexions`           | `/connectors`                     |
| `/veille`               | `/watchers`                       |
| `/alertes`              | `/notifications`                  |
| `/donnees`              | `/activation`                     |
| `/contracts-radar`      | `/renouvellements`                |
| `/plan-action[s]`       | `/anomalies?tab=actions`          |
| `/action-plan`          | `/anomalies`                      |

### 4.3 Catch-all

`path="*"` → [NotFound](frontend/src/pages/NotFound.jsx).

## 5. Croisement Nav → Routes

### 5.1 Tous les items NAV_SECTIONS résolvent ✅

34 cibles distinctes dans `NAV_SECTIONS`, `QUICK_ACTIONS`,
`COMMAND_SHORTCUTS`, `HIDDEN_PAGES` : **toutes pointent vers une route réelle
ou un redirect actif**. Pas de lien mort dans le menu.

### 5.2 Routes orphelines — existent mais ne sont listées ni en menu, ni en CommandPalette (5)

| Route                   | Statut                                                   |
|-------------------------|----------------------------------------------------------|
| `/admin/cx-dashboard`   | Dashboard North-Star T2V/IAR/WAU (référencé uniquement en dur) |
| `/admin/kb-metrics`     | KB observability (PR #221)                               |
| `/admin/enedis-health`  | Enedis promotion health                                  |
| `/admin/roles`          | IAM — non listé même en admin Panel                      |
| `/admin/assignments`    | IAM — non listé même en admin Panel                      |
| `/consommations/kb`     | Sous-tab atteint via `/consommations` tabs (UI interne, OK) |
| `/login`                | Public, exclu du shell (OK)                              |

> ⚠️ **5 routes Admin ne sont discoverable que par tapage manuel d'URL**
> `/admin/cx-dashboard`, `/admin/kb-metrics`, `/admin/enedis-health`,
> `/admin/roles`, `/admin/assignments`. Le module Admin (Panel) ne liste que
> 4 items (Import / Utilisateurs / Veille / Système). Les 5 orphelins n'ont
> ni entrée NAV_SECTIONS ni entrée HIDDEN_PAGES ni COMMAND_SHORTCUTS.
>
> 🔧 Recommandation : ajouter à `NAV_SECTIONS.admin-data` ou `HIDDEN_PAGES`
> (au minimum pour qu'elles remontent dans `Ctrl+K`).

### 5.3 Entrées ROUTE_MODULE_MAP sans route réelle (3 — 404)

| Entrée                 | Résolveur de module | Route React |
|------------------------|---------------------|-------------|
| `/conformite/dt`       | ✅ conformite       | ❌ 404      |
| `/conformite/bacs`     | ✅ conformite       | ❌ 404      |
| `/conformite/audit-sme`| ✅ conformite       | ❌ 404      |

La page `ConformitePage` utilise `?tab=obligations|donnees|execution|preuves`
et filtre les obligations par code (`dt`, `bacs`, `audit-sme`). Ces 3 paths
suggèrent des deep-links prévus mais jamais implémentés — résultat : le rail
s'illumine bien en Conformité (via `matchRouteToModule`), puis la page
affiche NotFound.

> 🔧 Recommandation : soit câbler ces 3 paths en `<Navigate
> to="/conformite?tab=obligations&focus=XXX">`, soit les retirer de
> `ROUTE_MODULE_MAP`.

## 6. Shortcuts, HIDDEN_PAGES, QUICK_ACTIONS

### 6.1 HIDDEN_PAGES (7)

Accessibles uniquement par CommandPalette :
`/kb`, `/segmentation`, `/connectors`, `/usages-horaires`,
`/conformite/tertiaire`, `/compliance/pipeline`, `/anomalies`.

### 6.2 COMMAND_SHORTCUTS (10)

Tous câblés avec un raccourci `Ctrl+Shift+<X>` :
`A` Créer action · `I` Importer · `L` Centre d'actions · `C` Cockpit ·
`S` Changer site · `E` Exporter CSV · `F` Conformité · `B` Factures ·
`X` Mode expert · `F1` Aide.

### 6.3 QUICK_ACTIONS (15)

Utilisées par le Panel (section "Raccourcis" visible en mode expert
uniquement, filtrées par module) et par la CommandPalette. Exemples :
`/conformite?tab=donnees`, `/anomalies?tab=actions&source=copilot`,
`/bill-intel`, `/achat-energie`, `/onboarding/sirene`,
`/conformite/tertiaire` (Export OPERAT).

## 7. Matrice rôles → permissions (⚠️ incohérence)

`NavPanel.filterItems` appelle `hasPermission('view', module)` où `module`
est la clé NavRegistry (`cockpit|conformite|energie|patrimoine|achat|admin`).

Mais [`ROLE_PERMISSIONS`](backend/services/iam_service.py#L54) utilise des
clés **capabilités** (pas module) : `cockpit`, `billing`, `purchase`,
`consommations`, `monitoring`, `diagnostic`, `conformite`, `patrimoine`,
`actions`, `reports`.

> 🚨 **Bug de cohérence** : les rôles restreints voient une nav vide sur
> certains modules.

| Rôle              | View (backend)                                          | Nav attendu   | Nav réel calculé |
|-------------------|---------------------------------------------------------|---------------|------------------|
| `daf`             | cockpit, billing, purchase, actions, reports            | Cockpit + Patrimoine(billing) + Achat | Cockpit seul (les autres masquent car `patrimoine` ≠ `billing`, `achat` ≠ `purchase`) |
| `acheteur`        | purchase, billing, actions                              | Achat + Patrimoine | Achat 0 item, Patrimoine 0 item (même mismatch) |
| `resp_conformite` | conformite, actions, reports                            | Conformité    | ✅ OK (même clé)  |
| `resp_immobilier` | patrimoine, consommations, actions                      | Patrimoine + Énergie | Patrimoine OK, Énergie 0 item (`energie` ≠ `consommations`) |
| `resp_site`       | patrimoine, consommations, conformite, actions          | Patrimoine + Énergie + Conformité | Énergie 0 item |
| `prestataire`     | patrimoine, consommations, monitoring                   | Patrimoine + Énergie | Patrimoine OK, Énergie 0 item |
| `dg_owner`, `dsi_admin`, `energy_manager`, `auditeur`, `pmo_acc` | `__all__` | Tout | ✅ OK (bypass via `__all__`) |

Déclencheur silencieux : en `DEMO_MODE=true` avec `dg_owner` par défaut, le
bug ne se voit pas. Dès qu'un pilote teste avec un rôle restreint, son Panel
montre une section vide après avoir cliqué sur l'icône rail → UX dead-end.

> 🔧 Recommandation : soit mapper frontend `energie`↔backend `consommations`
> dans `hasPermission`, soit renommer les permission keys backend vers les
> module keys frontend (`energie`, `achat`), soit ajouter une table de
> correspondance dédiée. Le plus propre est d'aligner les deux sur un même
> vocabulaire (préférer les module keys NavRegistry V7).

## 8. Backend — inventaire des prefixes API (`/api/...`)

65 prefixes distincts répartis sur 82 fichiers [backend/routes/](backend/routes/).
Groupement logique :

| Domaine            | Prefixes                                                                 |
|--------------------|--------------------------------------------------------------------------|
| Auth & IAM         | `/api/auth`, `/api/admin`                                                |
| Cockpit            | `/api/cockpit`, `/api`                                                   |
| Conformité         | `/api/compliance`, `/api/regops`, `/api/regops/bacs`, `/api/tertiaire`, `/api/operat`, `/api/aper`, `/api/data-quality` |
| Énergie / Conso    | `/api/consommations`, `/api/consumption`, `/api/consumption-context`, `/api/consumption-unified`, `/api/portfolio/consumption`, `/api/ems`, `/api/energy`, `/api/monitoring`, `/api/power`, `/api/usages`, `/api/analytics` |
| Patrimoine         | `/api/patrimoine`, `/api/patrimoine/crud`, `/api/sites`, `/api/site`, `/api/compteurs`, `/api/contracts`, `/api/contracts/v2`, `/api/geocode` |
| Billing            | `/api/billing`, `/api/billing/usage-ventilation`                         |
| Achat              | `/api/purchase`, `/api/purchase/strategy`, `/api/purchase/cost-simulation`, `/api/market`, `/api/market-intelligence`, `/api/referentiel` |
| Action Hub         | `/api/actions`, `/api/action-center`, `/api/action-templates`, `/api/alertes`, `/api/notifications`, `/api/nps`, `/api/feedback` |
| Imports & Connect  | `/api/import`, `/api/intake`, `/api/onboarding`, `/api/onboarding-progress`, `/api/connectors`, `/api/dataconnect`, `/api/enedis`, `/api/grdf`, `/api/bridge` |
| KB / AI            | `/api/kb`, `/api/ai`, `/api/copilot`, `/api/watchers`                    |
| Pilotage / Flex    | `/api/pilotage`, `/api/flex/score`                                       |
| Divers             | `/api/segmentation`, `/api/guidance`, `/api/reports`, `/api/dashboard`, `/api/demo`, `/api/dev`, `/api/public` |

Pas de route backend visiblement orpheline du frontend — le couplage est
piloté côté frontend via `frontend/src/services/routes.js` (helpers + query
builders) et [frontend/src/services/api/](frontend/src/services/api/).

## 9. Accessibilité & UX

Points solides relevés :

- **Skip link** `aria-label="Aller au contenu"` qui cible `#main-content`.
- `role="navigation"` + `aria-label` sur Rail et Panel.
- `aria-current="page"` sur `NavLink` actif, `aria-describedby` pour les
  descriptions (`sr-only`), `aria-label` sur tous les boutons icon-only.
- `focus-visible:ring-2 focus-visible:ring-blue-500` partout (pas de `focus:`
  nu).
- Navigation clavier Up/Down dans le panel
  ([NavPanel.jsx:463](frontend/src/layout/NavPanel.jsx#L463)).
- `/` focus inline site search (patrimoine).
- `Ctrl+K` ouvre CommandPalette ; `Ctrl+Shift+*` raccourcis.
- Badge count avec `aria-valuenow/min/max` sur la barre de progression
  Conformité.

Points d'attention :

- `aria-expanded` absent sur les triggers de sections (sections toujours
  ouvertes — OK mais pas sémantiquement explicite).
- Le toggle Expert n'annonce pas son changement d'état (pas de
  `aria-live`).
- Tooltip du rail utilise `<TooltipPortal>` qui montre le label — accessible.
- `longLabel` utilisé pour `aria-label` mais `title` garde `desc` → conflit
  potentiel avec screen-readers sur 2 items (`PanelLink`
  [NavPanel.jsx:65-74](frontend/src/layout/NavPanel.jsx#L65-L74)).

## 10. Scrollback ROUTE_MODULE_MAP vs App.jsx

`ROUTE_MODULE_MAP` contient 44 entrées (dont 3 sans route réelle §5.3). Les
patterns `:id`, `:actionId`, `:siteId` sont tous bien matchés par le
résolveur pattern-score.

Entrées légères (non-redirect) correctement couvertes par une route :

- `/` `/cockpit` `/onboarding` `/onboarding/sirene`
- `/notifications` `/actions` `/actions/new` `/actions/:actionId` `/anomalies` `/action-center`
- `/conformite` `/conformite/aper` `/conformite/tertiaire` `/conformite/tertiaire/wizard` `/conformite/tertiaire/anomalies` `/conformite/tertiaire/efa/:id`
- `/compliance` (redirect) `/compliance/pipeline` `/compliance/sites/:siteId` `/regops/:id`
- `/consommations` `/consommations/explorer` `/consommations/import` `/consommations/portfolio` `/diagnostic-conso` `/usages` `/usages-horaires` `/monitoring`
- `/patrimoine` `/patrimoine/nouveau` (redirect) `/sites/:id` `/contrats` `/billing` `/bill-intel` `/payment-rules` `/portfolio-reconciliation`
- `/achat-energie` `/renouvellements`
- `/import` `/connectors` `/segmentation` `/watchers` `/kb` `/admin/users` `/admin/roles` `/admin/assignments` `/admin/audit` `/activation` `/status`

## 11. Synthèse des findings

### P0 (bloquant pour pilote multi-rôles)

1. **Permission key mismatch §7** — 5 rôles (`daf`, `acheteur`,
   `resp_immobilier`, `resp_site`, `prestataire`) se retrouvent avec un Panel
   vide sur ≥ 1 module parce que `NavPanel.filterItems` compare clé
   NavRegistry vs clé permission backend. Invisible en DEMO_MODE +
   `dg_owner`, mais bloque un pilote réel.

### P1 (UX dégradée)

2. **3 deep-links `/conformite/dt|bacs|audit-sme` cassés §5.3** — le rail
   devient vert (Conformité détectée) puis affiche NotFound. Soit supprimer
   du map, soit convertir en redirects `?tab=obligations&focus=X`.

3. **5 routes Admin orphelines §5.2** — `/admin/cx-dashboard`,
   `/admin/kb-metrics`, `/admin/enedis-health`, `/admin/roles`,
   `/admin/assignments` — indécouvrables autrement qu'en tapant l'URL.

### P2 (polish)

4. `a11y` : toggle Expert sans `aria-live`, `longLabel`/`title` qui se
   chevauchent sur 2 items du Panel.
5. `MODULE_LANDING` [Sidebar.jsx:48](frontend/src/layout/Sidebar.jsx#L48)
   n'a qu'une entrée (`energie → /consommations`) ; les 5 autres modules
   utilisent l'override sans navigation. Comportement asymétrique volontaire
   mais non documenté.

### Non-issues (design intentionnel)

- Modal `?actionCenter=open&tab=actions` non route — géré dans AppShell.
- `Actions & Suivi` / `Notifications` absents du rail — déplacés dans
  Centre d'actions cloche header (changelog V7).
- `admin` expertOnly — volontaire (`ROLE_MODULE_ORDER` n'inclut jamais
  `admin`, ajouté par `getOrderedModules` si `isExpert`).

## 12. Angle non couvert par cet audit

- **Runtime / Playwright** : les serveurs locaux (8001/5173) tournent sur
  `claude/refonte-visuelle-sol` (93 commits d'écart avec main, dont une
  refonte visuelle Sol et un AppShell différent). Une capture Playwright sur
  cette instance **ne refléterait pas main**. À refaire sur un worktree main
  ou après un rebase si une vérification visuelle est nécessaire.
- **Performance** : pas mesurée (bundle size per-module, code-split
  efficacité).
- **E2E** : les tests `blocB2_navigation.test.js` et `menuMarchePremium`
  couvrent une partie mais pas les cas de rôles restreints du §7.

---

_Rapport généré depuis `git show main:...` — snapshot HEAD main
`ec15f0bb` (2026-04-22)._
