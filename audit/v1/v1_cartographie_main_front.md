# V1.A — Cartographie frontend MAIN

**Date**: 2026-04-24 · **Branche**: `origin/main` · **Worktree**: `/Users/amine/projects/promeos-audit-main/` · **Commit**: `a5e2424d`

## 1. Routes React (App.jsx)

**Architecture** : `<BrowserRouter>` + `<Routes>` unique, `RequireAuth` + `AppShell` wrapper, lazy-loaded pages, fallback `PageSuspense` (Skeleton).

### Routes principales

| Path | Composant | Layout | Guard | Notes |
|------|-----------|--------|-------|-------|
| `/login` | LoginPage | — | Public | Pas protégée |
| `/` | CommandCenter | AppShell | RequireAuth | Accueil = tableau de bord |
| `/patrimoine` | Patrimoine | AppShell | RequireAuth | Registre sites/bâtiments |
| `/patrimoine/nouveau` | redirect → `/patrimoine?wizard=open` | — | RequireAuth | |
| `/sites` | redirect → `/patrimoine` | — | RequireAuth | |
| `/sites/:id` | Site360 | AppShell | RequireAuth | Fiche site détaillée |
| `/actions` | ActionsPage | AppShell | RequireAuth | Gestion actions |
| `/actions/new` | ActionsPage autoCreate | AppShell | RequireAuth | |
| `/actions/:actionId` | ActionsPage | AppShell | RequireAuth | Détail action |
| `/conformite` | ConformitePage | AppShell | RequireAuth | Hub réglementaire |
| `/conformite/tertiaire` | TertiaireDashboardPage | AppShell | RequireAuth | Décret Tertiaire OPERAT |
| `/conformite/tertiaire/wizard` | TertiaireWizardPage | AppShell | RequireAuth | Wizard EFA |
| `/conformite/tertiaire/efa/:id` | TertiaireEfaDetailPage | AppShell | RequireAuth | Détail EFA |
| `/conformite/tertiaire/anomalies` | TertiaireAnomaliesPage | AppShell | RequireAuth | Anomalies Tertiaire |
| `/conformite/aper` | AperPage | AppShell | RequireAuth | Solarisation APER |
| `/cockpit` | Cockpit | AppShell | RequireAuth | Vue exécutive |
| `/consommations` | ConsommationsPage | AppShell | RequireAuth | Hub 4 tabs |
| `/consommations/explorer` | ConsumptionExplorerPage | AppShell | RequireAuth | Courbes charge |
| `/consommations/portfolio` | ConsumptionPortfolioPage | AppShell | RequireAuth | Vue portefeuille |
| `/consommations/import` | ImportWizard | AppShell | RequireAuth | Import données |
| `/consommations/kb` | KBAdminPanel | AppShell | RequireAuth | Admin KB |
| `/connectors` | ConnectorsPage | AppShell | RequireAuth | Connecteurs API (HIDDEN) |
| `/watchers` | WatchersPage | AppShell | RequireAuth | Veille RSS |
| `/monitoring` | MonitoringPage | AppShell | RequireAuth | KPIs puissance + heatmap |
| `/usages` | UsagesDashboardPage | AppShell | RequireAuth | Ventilation CVC/éclairage |
| `/usages-horaires` | ConsumptionContextPage | AppShell | RequireAuth | Heatmap horaires (HIDDEN) |
| `/diagnostic-conso` | ConsumptionDiagPage | AppShell | RequireAuth | Anomalies & gisements |
| `/bill-intel` | BillIntelPage | AppShell | RequireAuth | Facturation & anomalies |
| `/billing` | BillingPage | AppShell | RequireAuth | Historique shadow billing |
| `/achat-energie` | PurchasePage | AppShell | RequireAuth | Scénarios achat + assistant |
| `/achat-assistant` | redirect → `/achat-energie?tab=assistant` | — | RequireAuth | |
| `/renouvellements` | ContractRadarPage | AppShell | RequireAuth | Contrats à renouveler |
| `/contrats` | Contrats | AppShell | RequireAuth | Gestion contrats |
| `/kb` | KBExplorerPage | AppShell | RequireAuth | Base connaissances (HIDDEN) |
| `/segmentation` | SegmentationPage | AppShell | RequireAuth | Segmentation (HIDDEN) |
| `/import` | ImportPage | AppShell | RequireAuth | Import CSV |
| `/notifications` | NotificationsPage | AppShell | RequireAuth | Centre alertes |
| `/anomalies` | AnomaliesPage | AppShell | RequireAuth | Détection auto (HIDDEN) |
| `/payment-rules` | PaymentRulesPage | AppShell | RequireAuth | Règles paiement |
| `/portfolio-reconciliation` | PortfolioReconciliationPage | AppShell | RequireAuth | Rapprochement |
| `/activation` | ActivationPage | AppShell | RequireAuth | Disponibilité données |
| `/status` | StatusPage | AppShell | RequireAuth | Health système |
| `/onboarding` | OnboardingPage | AppShell | RequireAuth | Setup initial |
| `/onboarding/sirene` | SireneOnboardingPage | AppShell | RequireAuth | Patrimoine SIREN |
| `/admin/users` | AdminUsersPage | AppShell | RequireAuth | Utilisateurs |
| `/admin/roles` | AdminRolesPage | AppShell | RequireAuth | Rôles |
| `/admin/assignments` | AdminAssignmentsPage | AppShell | RequireAuth | Affectations |
| `/admin/audit` | AdminAuditLogPage | AppShell | RequireAuth | Journal audit |
| `/admin/kb-metrics` | AdminKBMetricsPage | AppShell | RequireAuth | Métriques KB |
| `/admin/cx-dashboard` | CxDashboardPage | AppShell | RequireAuth | CX dashboard |
| `/admin/enedis-health` | EnedisPromotionHealthPage | AppShell | RequireAuth | Health Enedis |
| `*` | NotFound | AppShell | RequireAuth | 404 |

### Redirects legacy (cleanup nav V92+)
`/compliance`, `/compliance/sites`, `/dashboard-legacy`, `/sites-legacy/:id`, `/action-plan`, `/plan-action`, `/plan-actions`, `/factures`, `/facturation`, `/diagnostic`, `/performance`, `/achats`, `/purchase`, `/referentiels`, `/synthese`, `/executive`, `/dashboard`, `/conso`, `/imports`, `/connexions`, `/veille`, `/alertes`, `/ems`, `/donnees`, `/contracts-radar`, `/explorer`.

### Routes orphelines / mortes
- `/compliance/pipeline` — Défini mais inaccessible via nav
- `/regops/:id` — Charger possible, non documenté dans NAV_SECTIONS
- `EnergyCopilotPage` — Lazy import commenté
- `Dashboard.jsx` — Fichier existe, jamais utilisé
- `PurchaseAssistantPage.jsx` — Fusionné en tab, fichier jamais supprimé

## 2. Navigation (NavRegistry.js — SSOT)

**6 modules, 5 visibles en normal, 1 expertOnly** :

| Module | Icône | Tint | ExpertOnly | Route primary |
|--------|-------|------|-----------|---------------|
| Accueil (Cockpit) | LayoutDashboard | blue | Non | `/` |
| Conformité | ShieldCheck | emerald | Non | `/conformite` |
| Énergie | Zap | indigo | Non | `/consommations` |
| Patrimoine | Building2 | amber | Non | `/patrimoine` |
| Achat | ShoppingCart | violet | Non | `/achat-energie` |
| Administration | Settings | slate | **OUI** | `/import` |

### NAV_SECTIONS par module
- **Accueil** : Tableau de bord (`/`), Vue exécutive (`/cockpit`)
- **Conformité** : Conformité (`/conformite`), Solarisation (APER)(`/conformite/aper`)
- **Énergie** : Consommations, Performance (`/monitoring`), Répartition (`/usages`), Diagnostics (`/diagnostic-conso`)
- **Patrimoine** : Sites & bâtiments (`/patrimoine`), Contrats (`/contrats`), Facturation (`/bill-intel`)
- **Achat** : Échéances (`/renouvellements`), Scénarios (`/achat-energie`)
- **Admin** : Import, Utilisateurs, Veille, Système

### Composants de navigation
- `layout/AppShell.jsx` — conteneur + header + toast
- `layout/Sidebar.jsx` — Rail + NavPanel
- `layout/NavRail.jsx` — rail icônes (min 768px)
- `layout/NavPanel.jsx` — contenu gauche
- `layout/Breadcrumb.jsx` — miettes contextuelles
- `layout/ScopeSwitcher.jsx` — org/portefeuille
- `ui/CommandPalette.jsx` — Cmd+K (10 shortcuts)
- `components/ActionCenterSlideOver.jsx` — bell icon top-right

### HIDDEN_PAGES (accès via palette/direct URL)
`/kb`, `/segmentation`, `/connectors`, `/usages-horaires`, `/conformite/tertiaire`, `/compliance/pipeline`, `/anomalies`.

## 3. Modules fonctionnels

### Cockpit — CommandCenter
Fichier : `pages/CommandCenter.jsx` + 16 sous-composants dans `pages/cockpit/` (CockpitHero, SanteKpiGrid, AlertesPrioritaires, PriorityActions, TrajectorySection, TopSitesCard, EvenementsRecents, MarketWidget, DataActivationPanel). **États UX** : Loading/Empty/Error gérés.

### Patrimoine
`pages/Patrimoine.jsx` + `Site360.jsx`, `Contrats.jsx`, `BillIntelPage.jsx`, `BillingPage.jsx` + wizards (`PatrimoineWizard`, `DrawerAddCompteur`, `DrawerAddContrat`, `DrawerEditSite`) + `SiteContractsSummary`, `SiteBillingMini`. **Imports commentés** détectés dans Patrimoine.jsx : `PatrimoinePortfolioHealthBar`, `PatrimoineHeatmap`, `PatrimoineRiskDistributionBar`, `SegmentationWidget`.

### Conformité
Hub `ConformitePage.jsx` + tabs (`ExecutionTab`, `ObligationsTab`, `PreuvesTab`, `DonneesTab`) + sous-module Tertiaire (`pages/tertiaire/` × 4) + APER (`AperPage.jsx`).

### Consommation & Performance
Hub 4 tabs `ConsommationsPage.jsx` + explorer (`pages/consumption/` × 11 panels : ExplorerChart, TimeseriesPanel, InsightsPanel, SignaturePanel, TargetsPanel, BenchmarkPanel, GasPanel, HPHCPanel, CDCViewerPanel, MeteoPanel, HeatmapChart, ProfileHeatmapTab) + Portfolio + Monitoring + Usages + Diagnostic.

### Achat
`PurchasePage.jsx` (3 tabs) + `PurchaseAssistantWizard` + `components/purchase/` × 5 + `PurchaseErrorBoundary` + `ContractRadarPage` + `Contrats` + `ContractKpiStrip`.

### Facturation
`BillIntelPage.jsx` (anomalies + cards) + `BillingPage.jsx` (historique + `BillingTimeline`, Recharts).

### Actions & Anomalies
`ActionsPage.jsx` + `ActionDetailDrawer.jsx` (**55 KB, très complexe**) + `ActionDetailPanel.jsx` + `AnomaliesPage.jsx` + `AnomalyActionModal` + `ActionCenterSlideOver`.

### Admin
7 pages Admin + `StatusPage`, `ConnectorsPage`, `WatchersPage`, `ImportPage`, `SegmentationPage` (HIDDEN).

### KB & Onboarding
`KBExplorerPage` (HIDDEN) + `OnboardingPage` + `SireneOnboardingPage` + `OnboardingOverlay`.

## 4. Points d'intégration API

**Client** : Axios instance `services/api/core.js` avec cache GET 60s + `X-Org-Id` auto-header.
**Base URL** : `import.meta.env.VITE_API_URL || '/api'`
**19 fichiers services domaine** dans `services/api/`.

### Endpoints clés par module
- **Auth** : `/auth/me`, `/auth/login`, `/auth/logout`
- **Patrimoine** : `/patrimoines`, `/sites`, `/energy/meters`, `/contracts`, `/delivery_points`
- **Conformité** : `/compliance/portfolio/score`, `/compliance/sites/{id}/score`, `/compliance/recompute`, `/compliance/findings`, `/compliance/tertiaire/efas`, `/compliance/aper/obligations`, `/compliance/proof/upload`
- **Consommation** : `/consommations`, `/consumption/availability`, `/consumption/tunnel_v2`, `/consumption/targets`, `/consumption/hphc_ratio`, `/consumption/insights`, `/monitoring/kpis`, `/usages/breakdown`, `/power/nebco`
- **Billing** : `/billing/invoices`, `/billing/anomalies`, `/billing/payment_rules`, `/billing/reconcile`
- **Achat** : `/purchase/scenarios`
- **Actions** : `/guidance/action-plan`, `/actions`, `/actions/{id}/evidence`
- **Admin** : `/admin/users`, `/admin/roles`, `/admin/audit-log`, `/import/jobs`
- **Demo** : `/api/demo/status`, `/api/demo/generate`, `/energy/demo/generate`

## 5. États produit gérés

| Composant | Loading | Empty | Error |
|-----------|---------|-------|-------|
| Skeleton / SkeletonCard | ✓ | — | — |
| EmptyState | — | ✓ | — |
| ErrorState | — | — | ✓ |
| AsyncState (wrapper) | ✓ | ✓ | ✓ |
| ErrorBoundary | — | — | ✓ |

### Couverture par module
CommandCenter/Patrimoine/Conformité/Consommation/Facturation/Actions : **Complet**.
Achat/Admin : **Partiel** (list views TBD, Skeletons Admin incomplets).

## 6. Feature flags & env vars

| Var | Défaut | Usage |
|-----|--------|-------|
| `VITE_API_URL` | `/api` | Base URL backend |
| `VITE_SENTRY_DSN` | - | Monitoring si défini |
| `import.meta.env.DEV` | boolean | DevPanel, PurchaseDebugDrawer, ExplorerDebugPanel |
| `isExpertMode` (Context) | false | Admin + features avancées |
| `isDemoMode` (Context) | API | Seed démo |

**Pas de flag feature central** ; toggles via contextes React.

## 7. Composants KPI/données

`ui/KpiCard`, `ui/MetricCard`, `ui/UnifiedKpiCard`, `ui/Sparkline`, `ui/Table`, Recharts (LineChart/AreaChart/BarChart) dans `pages/consumption/`.

**Tooltips/définitions** : `ui/glossary.js` (30+ termes) + `ui/tooltips.js` + composant `<Explain>`. **Risque** : KPI sans `<Explain>` ne montre aucun terme générique.

## 8. Top 10 risques UX statiques

1. Routes orphelines `/compliance/pipeline`, `/regops/:id` sans entrée nav
2. Imports commentés dans Patrimoine.jsx (5 composants fantômes : PatrimoinePortfolioHealthBar, PatrimoineHeatmap, PatrimoineRiskDistributionBar, SegmentationWidget, FlexPortfolioSummary)
3. `Dashboard.jsx` — fichier mort, jamais routé
4. `EnergyCopilotPage` lazy-import commenté (Sprint B P0-7)
5. `PurchaseAssistantPage.jsx` — dead code post-fusion en tab
6. Dual routing conformite/compliance → `/compliance/pipeline` sans fallback
7. Mode Demo sans badge "DEMO MODE" visible clair
8. Loading states incomplets en Admin pages (disabled buttons mais pas de Skeleton)
9. Tooltip glossaire silencieux si définition absente (pas de fallback)
10. CommandPalette shortcuts hardcodés (pas de registry génératif)

## 9. Fichiers clés (absolus)

- Routing : `/Users/amine/projects/promeos-audit-main/frontend/src/App.jsx`
- Nav SSOT : `/Users/amine/projects/promeos-audit-main/frontend/src/layout/NavRegistry.js`
- Layout : `/Users/amine/projects/promeos-audit-main/frontend/src/layout/AppShell.jsx`
- API core : `/Users/amine/projects/promeos-audit-main/frontend/src/services/api/core.js`
- 19 services API : `/Users/amine/projects/promeos-audit-main/frontend/src/services/api/`
- 60+ pages : `/Users/amine/projects/promeos-audit-main/frontend/src/pages/`
- 45 composants UI primitifs : `/Users/amine/projects/promeos-audit-main/frontend/src/ui/`
- 5 contextes : `/Users/amine/projects/promeos-audit-main/frontend/src/contexts/`

## 10. Routes prioritaires V2 Playwright

**Publiques** : `/login`
**Protégées critiques** : `/`, `/patrimoine`, `/conformite`, `/consommations/portfolio`, `/cockpit`, `/achat-energie`, `/anomalies`
**Dynamiques** : `/sites/:id`, `/actions/:actionId`, `/conformite/tertiaire/efa/:id`
**Orphelines à clarifier** : `/compliance/pipeline`, `/regops/:id`
