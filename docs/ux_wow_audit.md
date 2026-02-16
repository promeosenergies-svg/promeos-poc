# PROMEOS UX/UI Audit — Sprint WOW DIAMANT

> Date: 2026-02-13 | Version: v3.4 | Branch: `feat-bacs-expert`

---

## 1. Inventaire Architecture Frontend

### 1.1 Stack

| Layer | Tech |
|-------|------|
| Framework | React 18 (lazy + Suspense) |
| Routing | react-router-dom v6 |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`) |
| Icons | Lucide React |
| HTTP | Axios (`services/api.js`) |
| Build | Vite |
| Tests | Vitest (14 tests) |

### 1.2 Context Providers

| Context | Role |
|---------|------|
| `AuthProvider` | IAM (login, roles, permissions, org switching) |
| `DemoProvider` | Demo mode + seed data |
| `ScopeProvider` | Multi-site scope filtering |
| `ExpertModeProvider` | Toggle expert-only UI sections |

### 1.3 Layout

| Composant | Fichier | Role |
|-----------|---------|------|
| `AppShell` | `layout/AppShell.jsx` | Sidebar + Header + Outlet |
| `Sidebar` | `layout/Sidebar.jsx` | Nav sections, collapse, badges, RBAC filter |
| `Breadcrumb` | `layout/Breadcrumb.jsx` | Fil d'Ariane contextuel |
| `ScopeSwitcher` | `layout/ScopeSwitcher.jsx` | Filtre portefeuille/site |
| `NavRegistry` | `layout/NavRegistry.js` | Source unique nav items + keywords |

---

## 2. Design System V1

### 2.1 Composants UI (`src/ui/`)

| Composant | Fichier | Usage |
|-----------|---------|-------|
| `Button` | Button.jsx | Primaire, secondaire, ghost, danger |
| `Badge` | Badge.jsx | Status pills (success, warning, danger, info, neutral) |
| `Card` / `CardHeader` / `CardBody` | Card.jsx | Conteneurs de section |
| `Input` | Input.jsx | Champ texte avec label, erreur |
| `Select` | Select.jsx | Dropdown natif style |
| `Tabs` | Tabs.jsx | Navigation par onglets |
| `Table` / `Thead` / `Tbody` / `Th` / `Tr` / `Td` | Table.jsx | Tables avec sort, checkbox |
| `Pagination` | Pagination.jsx | Navigation pages |
| `Skeleton` / `SkeletonCard` / `SkeletonTable` | Skeleton.jsx | Loading states |
| `EmptyState` | EmptyState.jsx | Zero-data + CTA |
| `ErrorState` | ErrorState.jsx | Erreur + retry |
| `TrustBadge` | TrustBadge.jsx | Badge source donnees |
| `Modal` | Modal.jsx | Dialog overlay |
| `PageShell` | PageShell.jsx | Layout page (icon, titre, sous-titre, actions) |
| `KpiCard` | KpiCard.jsx | Carte metrique avec icone + trend |
| `FilterBar` | FilterBar.jsx | Barre de filtres horizontale |
| `Toggle` | Toggle.jsx | Switch on/off |
| `Tooltip` | Tooltip.jsx | Popover info |
| `Progress` | Progress.jsx | Barre de progression |
| `Drawer` | Drawer.jsx | Panel slide-over (Escape, focus trap, scroll lock) |
| `ToastProvider` / `useToast` | ToastProvider.jsx | Notifications toast |
| `CommandPalette` | CommandPalette.jsx | Ctrl+K search (nav items + quick actions) |

**Total: 22 composants UI**

### 2.2 Composants Feature (`src/components/`)

| Composant | Role |
|-----------|------|
| `DemoBanner` | Bandeau mode demo |
| `UpgradeWizard` | Wizard onboarding |
| `SegmentationWidget` | Widget segmentation inline |
| `ErrorBoundary` | Catch React errors |
| `CreateActionModal` | Modal creation action |
| `RequireAuth` | Route guard IAM |
| `PatrimoineWizard` | Wizard patrimoine DIAMANT |
| `IntakeWizard` | Wizard smart intake |
| `BacsWizard` | Wizard BACS expert |
| `BacsOpsPanel` | Panel operations BACS |
| `SitePicker` | Picker multi-sites |

**Total: 11 composants feature**

---

## 3. Carte des Routes

### 3.1 Routes canoniques (31)

| Section | Path | Page | Lazy | Lines |
|---------|------|------|------|-------|
| **Pilotage** | `/` | CommandCenter | Yes | 318 |
| | `/cockpit` | Cockpit | Yes | 352 |
| | `/notifications` | NotificationsPage | Yes | 348 |
| **Execution** | `/conformite` | ConformitePage | Yes | 994 |
| | `/actions` | ActionsPage | Yes | 944 |
| **Analyse** | `/patrimoine` | Patrimoine | Yes | 333 |
| | `/consommations` | ConsommationsUsages | Yes | 604 |
| | `/diagnostic-conso` | ConsumptionDiagPage | Yes | 314 |
| | `/bill-intel` | BillIntelPage | Yes | 356 |
| | `/achat-energie` | PurchasePage | Yes | 655 |
| | `/monitoring` | MonitoringPage | Yes | 587 |
| | `/explorer` | ConsumptionExplorerPage | Yes | 1069 |
| **Administration** | `/import` | ImportPage | Yes | 274 |
| | `/connectors` | ConnectorsPage | Yes | 184 |
| | `/segmentation` | SegmentationPage | Yes | 197 |
| | `/watchers` | WatchersPage | Yes | 315 |
| | `/kb` | KBExplorerPage | Yes | 308 |
| **IAM** | `/admin/users` | AdminUsersPage | Yes | 260 |
| | `/admin/roles` | AdminRolesPage | Yes | 146 |
| | `/admin/assignments` | AdminAssignmentsPage | Yes | 351 |
| | `/admin/audit` | AdminAuditLogPage | Yes | 235 |
| **Detail** | `/sites/:id` | Site360 | Yes | 438 |
| **Legacy** | `/dashboard-legacy` | Dashboard | Yes | 182 |
| | `/cockpit-2min` | Cockpit2MinPage | Yes | 327 |
| | `/sites-legacy/:id` | SiteDetail | Yes | 487 |
| | `/action-plan` | ActionPlan | Yes | 253 |
| | `/regops/:id` | RegOps | Yes | 314 |
| | `/compliance` | CompliancePage | Yes | 303 |
| | `/status` | StatusPage | Yes | 163 |
| **Auth** | `/login` | LoginPage | No | 86 |
| **404** | `*` | NotFound | Yes | 18 |

### 3.2 Redirections (19 aliases)

| Alias | Target |
|-------|--------|
| `/plan-action`, `/plan-actions` | `/actions` |
| `/factures`, `/facturation` | `/bill-intel` |
| `/anomalies`, `/diagnostic` | `/diagnostic-conso` |
| `/performance` | `/monitoring` |
| `/achats`, `/purchase` | `/achat-energie` |
| `/referentiels` | `/kb` |
| `/synthese`, `/executive` | `/cockpit` |
| `/dashboard` | `/` |
| `/conso` | `/consommations` |
| `/imports` | `/import` |
| `/connexions` | `/connectors` |
| `/veille` | `/watchers` |
| `/alertes` | `/notifications` |
| `/ems` | `/explorer` |

### 3.3 Sidebar Navigation (5 sections, 25 items)

| Section | Items |
|---------|-------|
| Pilotage (3) | Tableau de bord, Vue executive, Alertes |
| Execution (2) | Conformite, Plan d'actions |
| Analyse (7) | Patrimoine, Consommations, Diagnostic, Facturation, Achats energie, Performance, Explorateur Conso |
| Administration (5) | Imports, Connexions, Segmentation, Veille, Referentiels |
| IAM (4) | Utilisateurs, Roles, Assignments, Audit Log |

---

## 4. Audit UX par Page

### 4.1 Matrice Design System

| Page | PageShell | EmptyState | useToast | ErrorState | KpiCard | Skeleton | FilterBar | Drawer | Pagination | TrustBadge | Progress | Modal |
|------|:---------:|:----------:|:--------:|:----------:|:-------:|:--------:|:---------:|:------:|:----------:|:----------:|:--------:|:-----:|
| CommandCenter | Y | Y | Y | - | Y | Y | - | - | - | Y | Y | - |
| Cockpit | Y | - | - | - | Y | - | - | - | Y | Y | Y | Y |
| NotificationsPage | Y | Y | Y | - | Y | Y | Y | - | Y | Y | - | - |
| ConformitePage | Y | Y | Y | - | - | - | - | Y | - | Y | Y | Y |
| ActionsPage | Y | Y | Y | - | - | - | - | - | Y | Y | - | Y |
| Patrimoine | Y | Y | - | - | Y | - | - | - | Y | Y | - | Y |
| ConsommationsUsages | Y | - | - | - | - | - | - | - | - | - | Y | - |
| ConsumptionDiagPage | Y | - | - | - | - | - | - | - | - | - | - | - |
| BillIntelPage | Y | - | - | - | - | - | - | - | - | Y | - | - |
| PurchasePage | Y | - | - | - | - | - | - | - | - | - | - | - |
| MonitoringPage | Y | Y | - | - | - | Y | - | - | - | Y | - | - |
| ConsumptionExplorerPage | Y | Y | Y | - | Y | - | - | - | - | Y | - | - |
| Dashboard (legacy) | Y | Y | - | - | Y | Y | - | - | - | - | - | - |
| ImportPage | - | - | - | - | - | - | - | - | - | - | - | - |
| ConnectorsPage | - | - | - | - | - | - | - | - | - | - | - | - |
| SegmentationPage | - | - | - | - | - | - | - | - | - | - | - | - |
| WatchersPage | - | - | - | - | - | - | - | - | - | - | - | - |
| KBExplorerPage | - | - | - | - | - | - | - | - | - | Y | - | - |
| AdminUsersPage | - | - | - | - | - | - | - | - | - | - | - | - |
| AdminRolesPage | - | - | - | - | - | - | - | - | - | - | - | - |
| AdminAssignmentsPage | - | - | - | - | - | - | - | - | - | - | - | - |
| AdminAuditLogPage | - | - | - | - | - | - | - | - | Y | - | - | - |
| Site360 | - | Y | - | - | - | - | - | - | - | Y | - | - |
| LoginPage | - | - | - | - | - | - | - | - | - | - | - | - |

**Couverture PageShell: 13/24 pages (54%)**
**Couverture EmptyState: 10/24 pages (42%)**
**Couverture useToast: 5/24 pages (21%)**
**Couverture ErrorState: 0/24 pages (0%)**

### 4.2 Scores UX par page

| Page | Score | Top Issues |
|------|:-----:|------------|
| **CommandCenter** | 8/10 | Skeleton ok, empty states ok; manque search inline, cartes non cliquables pour nav |
| **Cockpit** | 8/10 | Tri + search + pagination ok; portefeuilles enrichis; manque export CSV |
| **NotificationsPage** | 8/10 | FilterBar ok, Skeleton ok, Pagination ok; bonne couverture DS |
| **ConformitePage** | 8/10 | Drawer UI kit, toasts, recherche obligations; page complexe bien structuree |
| **ActionsPage** | 9/10 | Kanban, group-by, inline status, search, colored pills, bulk bar; page la plus polie |
| **Patrimoine** | 7/10 | PageShell ok, Pagination ok, EmptyState ok; manque skeleton loading, search |
| **ConsommationsUsages** | 6/10 | PageShell ok, Progress ok; pas d'EmptyState, pas de toast, pas de search |
| **ConsumptionDiagPage** | 6/10 | PageShell ok; pas d'EmptyState, pas de skeleton, minimal DS usage |
| **BillIntelPage** | 7/10 | PageShell ok, TrustBadge ok; pas d'EmptyState, pas de skeleton |
| **PurchasePage** | 7/10 | PageShell ok, tabs; pas de skeleton, pas d'empty state, page complexe |
| **MonitoringPage** | 7/10 | PageShell ok, EmptyState ok, Skeleton ok; pas de toast |
| **ConsumptionExplorerPage** | 8/10 | Graphes avances, PageShell, EmptyState, toast, KpiCard, TrustBadge; client-side fallback |
| **Dashboard (legacy)** | 7/10 | Bien structure mais legacy; badge warning visible |
| **ImportPage** | 4/10 | Pas de PageShell, pas de DS components, styles inline |
| **ConnectorsPage** | 3/10 | Pas de PageShell, `prompt()` natif (!), pas de DS, console.error |
| **SegmentationPage** | 4/10 | Pas de PageShell, pas de DS, styles inline, pas d'error handling |
| **WatchersPage** | 5/10 | Pas de PageShell, custom Modal au lieu de DS Modal |
| **KBExplorerPage** | 5/10 | TrustBadge ok; pas de PageShell, pas d'EmptyState |
| **AdminUsersPage** | 4/10 | Pas de PageShell, pas de DS, styles inline |
| **AdminRolesPage** | 4/10 | Pas de PageShell, pas de DS, minimal |
| **AdminAssignmentsPage** | 5/10 | Pas de PageShell, pagination custom |
| **AdminAuditLogPage** | 5/10 | Pagination ok; pas de PageShell |
| **Site360** | 6/10 | EmptyState ok, TrustBadge ok; pas de PageShell, melange DS + custom |
| **LoginPage** | 6/10 | Fonctionnel; pas de DS, styles custom |

**Score moyen: 6.1/10**

---

## 5. Backlog WOW — Priorise

### P0 — Quick Wins (11 pages sans PageShell)

| # | Page | Action | Effort |
|---|------|--------|--------|
| 1 | ImportPage | Ajouter PageShell + EmptyState + remplacer styles inline par DS | S |
| 2 | ConnectorsPage | Ajouter PageShell + remplacer `prompt()` par Modal + DS components | M |
| 3 | SegmentationPage | Ajouter PageShell + error handling + DS components | S |
| 4 | WatchersPage | Ajouter PageShell + remplacer custom Modal par DS Modal | S |
| 5 | KBExplorerPage | Ajouter PageShell + EmptyState | S |
| 6 | AdminUsersPage | Ajouter PageShell + DS Table + EmptyState | S |
| 7 | AdminRolesPage | Ajouter PageShell + DS Table | S |
| 8 | AdminAssignmentsPage | Ajouter PageShell + remplacer pagination custom par DS Pagination | S |
| 9 | AdminAuditLogPage | Ajouter PageShell | XS |
| 10 | Site360 | Ajouter PageShell | XS |
| 11 | LoginPage | Polish visuel (reste hors PageShell, c'est normal) | S |

### P1 — Polish Analyse Pages

| # | Page | Action | Effort |
|---|------|--------|--------|
| 1 | ConsommationsUsages | Ajouter EmptyState + skeleton loading + search | M |
| 2 | ConsumptionDiagPage | Ajouter EmptyState + skeleton + toast errors | M |
| 3 | BillIntelPage | Ajouter EmptyState + skeleton | S |
| 4 | PurchasePage | Ajouter EmptyState + skeleton + toast errors | M |
| 5 | MonitoringPage | Ajouter toast errors | S |

### P2 — Cross-Cutting

| # | Theme | Action | Effort |
|---|-------|--------|--------|
| 1 | ErrorState | Aucune page n'utilise `ErrorState` — ajouter sur API fail pour les 13 pages avec data fetch | M |
| 2 | Toast errors | Etendre `useToast` aux 19 pages qui ne l'utilisent pas (au moins sur API fail) | M |
| 3 | Skeleton loading | Ajouter `SkeletonCard`/`SkeletonTable` aux 20 pages sans skeleton | M |
| 4 | Export CSV | Ajouter bouton export CSV sur tables majeures (Cockpit, Actions, Conformite, Monitoring) | M |
| 5 | Accessibility | Ajouter `aria-label` sur boutons icones, `role="status"` sur badges, focus-visible ring | L |
| 6 | Keyboard nav | Escape ferme modals/drawers (deja fait pour Drawer/Modal DS), Tab order correct | S |

---

## 6. Resume Executif

| Metrique | Valeur |
|----------|--------|
| Pages totales | 24 (+ 7 legacy/detail) |
| Routes canoniques | 31 |
| Redirections | 19 |
| UI components | 22 |
| Feature components | 11 |
| Score UX moyen | **6.1/10** |
| Pages avec PageShell | 13/24 (54%) |
| Pages avec EmptyState | 10/24 (42%) |
| Pages avec toast | 5/24 (21%) |
| Pages avec ErrorState | 0/24 (0%) |
| Pages avec Skeleton | 4/24 (17%) |
| Cible post-sprint | **8+/10 sur toutes les pages** |

### Top 5 actions a fort impact

1. **Ajouter PageShell sur 11 pages** — uniformise le look instantly
2. **Ajouter EmptyState sur 14 pages** — zero-data UX pro
3. **Ajouter Skeleton loading sur 20 pages** — perceived performance
4. **Remplacer `prompt()` ConnectorsPage par Modal** — elimine le plus gros red flag UX
5. **Ajouter useToast sur erreurs API** — feedback utilisateur coherent
