# V1.B — Cartographie frontend REFONTE SOL

**Date**: 2026-04-24 · **Branche**: `origin/claude/refonte-visuelle-sol` · **Worktree**: `/Users/amine/projects/promeos-audit-refonte-sol/` · **Commit**: `261e3a2e` · **Delta vs main**: 119 commits ahead

## 1. Routes React (App.jsx)

**Total : 92 routes** (62 lazy-loaded pages + 30 routes imbriquées/redirects). **Architecture A/B** : chaque page migrée a sa variante `-legacy` pour rollback.

### Routes par module

#### Module COCKPIT
| Path | Composant | Notes |
|------|-----------|-------|
| `/` | **CommandCenterSol** | Pattern A refonte Phase 1.1 (395 LOC vs 760 LOC legacy) |
| `/home-legacy` | CommandCenter | Legacy A/B |
| `/cockpit` | **CockpitSol** | Phase 2 : APIs réelles |
| `/cockpit-legacy` | Cockpit | Legacy Recharts |
| `/cockpit-fixtures` | CockpitRefonte | Fixtures Lot 1.1 (démo) |
| `/actions`, `/actions/new`, `/actions/:actionId` | ActionsPage | |
| `/anomalies` | AnomaliesPage | |
| `/notifications` | NotificationsPage | |

#### Module CONFORMITÉ
| Path | Composant | Notes |
|------|-----------|-------|
| `/conformite` | **ConformiteSol** | Phase 4.1, tabs DT/OPERAT/BACS/APER (routes `/conformite/dt`, `/conformite/bacs`, `/conformite/operat` tombent 404) |
| `/conformite-legacy` | ConformitePage | Legacy A/B |
| `/conformite/aper` | **AperSol** | Phase 1.2 Solarisation V2 raw |
| `/conformite/aper-legacy` | AperPage | Legacy (Recharts BarChart) |
| `/conformite/tertiaire` | TertiaireDashboardPage | DT hub |
| `/conformite/tertiaire/wizard` | TertiaireWizardPage | |
| `/conformite/tertiaire/efa/:id` | TertiaireEfaDetailPage | |
| `/conformite/tertiaire/anomalies` | TertiaireAnomaliesPage | |
| `/compliance` | redirect → `/conformite` | V92 |
| `/compliance/pipeline` | CompliancePipelinePage | +486 LOC refonte |
| `/compliance/sites/:siteId` | SiteCompliancePage | |

#### Module ÉNERGIE
| Path | Composant | Notes |
|------|-----------|-------|
| `/consommations` | ConsommationsPage | Hub 4-tabs |
| `/consommations/explorer` | ConsumptionExplorerPage | |
| `/consommations/portfolio` | ConsumptionPortfolioPage | Default tab |
| `/consommations/import` | ImportWizard | |
| `/consommations/kb` | KBAdminPanel | |
| `/diagnostic-conso` | ConsumptionDiagPage | |
| `/usages` | UsagesDashboardPage | |
| `/usages-horaires` | ConsumptionContextPage | |
| `/monitoring` | **MonitoringSol** | Phase 1.3 |
| `/monitoring-legacy` | MonitoringPage | |

#### Module PATRIMOINE
| Path | Composant | Notes |
|------|-----------|-------|
| `/patrimoine` | **PatrimoineSol** | Phase 4.3 portfolio |
| `/patrimoine-legacy` | Patrimoine | |
| `/patrimoine/nouveau` | redirect → `/patrimoine?wizard=open` | |
| `/sites/:id` | Site360 | |
| `/sites-legacy/:id` | redirect → `/patrimoine` | |
| `/billing` | BillingPage | Facturation migrée Patrimoine |
| `/bill-intel` | **BillIntelSol** | Phase 4.2 |
| `/bill-intel-legacy` | BillIntelPage | |
| `/contrats` | Contrats | |
| `/renouvellements` | ContractRadarPage | |
| `/payment-rules` | PaymentRulesPage | |
| `/portfolio-reconciliation` | PortfolioReconciliationPage | |

#### Module ACHAT
| Path | Composant | Notes |
|------|-----------|-------|
| `/achat-energie` | **AchatSol** | Scénarios + simulateur |
| `/achat-energie-legacy` | PurchasePage | |
| `/achat-assistant` | redirect → `/achat-energie?tab=assistant` | |

#### Module ADMIN
`/import`, `/connectors`, `/segmentation`, `/watchers`, `/kb`, `/activation`, `/status`, `/admin/users`, `/admin/roles`, `/admin/assignments`, `/admin/audit`, `/admin/kb-metrics`, `/admin/cx-dashboard`, `/admin/enedis-health`.

#### Autres
`/login`, `/_sol_showcase` (SolShowcase : 21 composants Sol hors AppShell), `/onboarding`, `/onboarding/sirene`, `/regops/:id`, `*` → NotFound.

#### Aliases legacy (redirects)
`/plan-action`, `/plan-actions`, `/diagnostic`, `/performance`, `/achats`, `/purchase`, `/referentiels`, `/synthese`, `/executive`, `/dashboard`, `/conso`, `/imports`, `/connexions`, `/veille`, `/alertes`, `/ems`, `/donnees`, `/contracts-radar`.

### Routes mortes
- `/energy-copilot` : EnergyCopilotPage commenté (Sprint B P0-7)
- `/audit-sme` : **route absente** mais attendue (tab ConformiteSol manquante)
- `/conformite/dt`, `/conformite/bacs`, `/conformite/operat` : **404** (dépendance onglets futurs)

## 2. Navigation — Rail + Panel Sol V7

### Composants
- `ui/sol/SolRail.jsx` — 56px vertical, icons modules, active tint
- `ui/sol/SolPanel.jsx` — 240px, sections NAV_SECTIONS, keyboard nav Up/Down/Home/End, locked badge
- `layout/SolAppShell.jsx` — wrapper global (Rail + Panel + Outlet), header slim ≤40px, SearchTrigger + Expert toggle + ActionCenter bell
- `layout/NavRegistry.js` — SSOT 6 modules, 17 items normal + 4 expertOnly

### 6 modules (identiques à main en surface)

| Module | Icône | Route 1ère | Couleur | Expert |
|--------|-------|-----------|---------|--------|
| cockpit | LayoutDashboard | `/` | Bleu | Non |
| conformite | ShieldCheck | `/conformite` | Émeraude | Non |
| energie | Zap | `/consommations` | Indigo | Non |
| patrimoine | Building2 | `/patrimoine` | Ambre | Non |
| achat | ShoppingCart | `/achat-energie` | Violet | Non |
| admin | Settings | `/admin/users` | Ardoise | **OUI** |

### Items par module (NAV_SECTIONS)
- **Cockpit (5)** : Accueil, Suivi actions, Centre d'actions (bell), Onboarding, Status
- **Conformité (5)** : Vue globale, DT, APER, Pipeline (expertOnly), onglets HIDDEN
- **Énergie (6)** : Consommations, Explorateur, **Usages (NEW V7)**, Profils horaires, Monitoring, Diagnostic (expertOnly)
- **Patrimoine (5)** : Sites, **Contrats (NEW)**, **Factures (NEW migrée Énergie)**, Bill intel, **Audit SME (expertOnly, route ABSENTE)**
- **Achat (2)** : Scénarios d'achat (**NEW V7, was expertOnly**), Renouvellements
- **Admin (9)** : Users/Roles/Assignments/Audit/KB metrics/Import/Connectors/Segmentation/Watchers

### Permissions
`PERMISSION_KEY_MAP` relie items à `hasPermission(permKey)`. Items verrouillés → badge "locked" + a11y P0 fix (PR audit v2).

### Analytics nav
`services/tracker.js` : events `nav_panel_opened` + distinction `manual`/`deep_link` source via `DEEP_LINK_SECTION_KEY`.

## 3. Modules fonctionnels

22 pages refonte nommées *Sol identifiées. 40+ composants dans `ui/sol/`.

| Module | Pages | État |
|--------|-------|------|
| Cockpit | CommandCenterSol, ActionsPage, AnomaliesPage, NotificationsPage | PARTIEL (CockpitSol Phase 2 fixtures, APIs Vague D) |
| Conformité | ConformiteSol, AperSol, TertiaireDashboard, SiteCompliance, CompliancePipelineSol | PARTIAL (onglets DT/OPERAT/BACS absents) |
| Énergie | ConsommationsPage, Explorer, Portfolio, UsagesDashboard, MonitoringSol, DiagnosticConsoSol | COMPLET |
| Patrimoine | PatrimoineSol, Site360Sol, Contrats, BillingPage, BillIntelSol, PaymentRules | COMPLET |
| Achat | AchatSol, RenouvellementsSol | COMPLET |
| Admin | 12 pages | COMPLET |

**ABSENTS** : `/audit-sme`, `/facturation` (expert).

## 4. API — Services

`services/api/` (19 modules) : `auth.js`, `core.js`, `cockpit.js`, `actions.js`, `conformite.js`, `energy.js`, `ems.js`, `patrimoine.js`, `billing.js`, `purchase.js`, `market.js`, `admin.js`, `enedis.js`, `sirene.js`.

**Nouveautés refonte** :
- `services/tracker.js` (analytics refonte)
- `services/kpiMessaging.js` (signaux "calme/attention/à faire")

**Timeout** : axios 15s (fix `a2109d52`).
**Bug connu** : `getCockpit()` null fallback sur org vide (issue #257).

## 5. États produit gérés

Composants existants main + nouveaux refonte :
- `ui/sol/SolPendingBanner.jsx` — banner refonte
- `ui/EmptyState.jsx` — enrichi ctaLabel/ctaHref (V114)

**Patterns refonte** : AsyncState (`loading`/`error`/`empty`/`success`) + SkeletonCard awaiting APIs.

## 6. Feature flags & env

Identique à main (`VITE_API_URL`, `VITE_SENTRY_DSN`, `import.meta.env.DEV`). **Pas de flag feature dédié refonte** (pas de mécanisme A/B dynamique ; toggle via routes `-legacy`).

## 7. Composants data refonte

**Recharts** + composants Sol custom :
- `SolLoadCurve` (Recharts wrap)
- `SolTrajectoryChart` (custom SVG)
- `SolBarChart`
- `SolWeekGrid`
- `SolKpiCard`
- `SolKpiRow`
- `SolSourceChip`
- `SolStatusPill`
- `SolEntityCard`
- `FindingCard` (finding impact signal)
- `SolSparkline`

**Design tokens** (`ui/sol/tokens.css`) :
- Palette WARM "journal en terrasse" : `--sol-calme-bg #e3f0ed`, `--sol-attention-bg #f6ead2`, `--sol-afaire-bg #f7e4d8`, `--sol-refuse-bg #f3dddb`
- Ink scale `--sol-ink-900` → `100`
- Rule `#e2e8f0`
- Typo : **Fraunces** (serif display) + **DM Sans** (body) + **JetBrains Mono**

## 8. Top 10 risques UX (refonte)

1. `/audit-sme` : route absente, tab ConformiteSol manquante (A5 V114 signalé, implé Vague D attendue)
2. `/conformite/dt`, `/conformite/bacs`, `/conformite/operat` → **404** (onglets futurs non câblés)
3. `getCockpit()` null fallback org vide → CommandCenterSol `status='loading'` indéfini (issue #257)
4. Legacy pages 2× taille (CommandCenter 760 LOC vs Sol 395 LOC) — maintenabilité A/B
5. Animations Sol non reduced-motion safe (SolTimerail, SolCartouche pulse)
6. Items Panel verrouillés cliquables puis blocked (a11y P0 fixed mais coverage à vérifier)
7. Deep-link tracking complexe, edge case `/conformite/aper` exact
8. Placeholders inputs sans aria-label explicite (AdminAssignmentsPage, KBExplorerPage)
9. `useDataReadiness()` expose `sitesLoading` mais Pages Sol ignorent (skeleton delay possible)
10. Routes `-legacy` → confusion utilisateur si URL partagée par mail

## 9. BONUS — Spécificités refonte SOL

### Pages *Sol ajoutées (22)
```
AchatSol · AnomaliesSol · AperSol · BillIntelSol · CockpitSol
CommandCenterSol · CompliancePipelineSol · ConformiteSol · ConformiteTertiaireSol
ContratsSol · DiagnosticConsoSol · EfaSol · KBExplorerSol · MonitoringSol
PatrimoineSol · RegOpsSol · RenouvellementsSol · SegmentationSol
Site360Sol · UsagesHorairesSol · UsagesSol · WatchersSol
```

### Composants Sol (40+)
Header/Voice (SolPageHeader, SolHeadline, SolSubline) · Data (SolKpiCard, SolKpiRow, SolSourceChip, SolStatusPill) · Hero (SolHero, SolCartouche, SolWeekCard, SolWeekGrid) · Charts (SolLoadCurve, SolTrajectoryChart, SolBarChart, SolTimerail) · Nav (SolRail, SolPanel, SolAppShell) · Pattern C (SolDetailPage, SolBreadcrumb, SolEntityCard, SolTimeline) · Pattern B (SolListPage, SolExpertToolbar, SolExpertGridFull, SolPagination) · Overlays (SolDrawer) · Primitives (SolButton).

### Commits récents clés
- `249a4ef9 refactor(nav-sol): simplify post-audit fixes`
- `662cfe1d fix(polish): NBSP FR + icon distinct + tracker sanitize`
- `97984b6c test(nav-sol): dynamic invariants + negative assertions`
- `8e3d7ea8 fix(a11y): P1 keyboard nav Escape + hit area`
- `a87286b6 fix(a11y): P0 locked items accessibility + WCAG contrast`

## 10. Structure globale refonte

```
frontend/src/
├── App.jsx (92 routes, 62 lazy pages)
├── layout/
│   ├── SolAppShell.jsx (new global layout, +608 LOC)
│   ├── AppShell.jsx (legacy, non modifié)
│   ├── NavRegistry.js (SSOT +210 LOC)
│   └── permissionMap.js (NEW)
├── pages/ (22 *Sol + 40 legacy)
├── ui/sol/ (40+ composants refonte)
├── ui/ (legacy : KpiCard, Table, Button…)
├── services/api/ (19 modules)
└── index.css (+1003 LOC override Tailwind)
```

## Fichiers clés (absolus)

- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/App.jsx`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/layout/SolAppShell.jsx`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/layout/NavRegistry.js`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/ui/sol/tokens.css`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/index.css`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/pages/SolShowcase.jsx`
- `/Users/amine/projects/promeos-audit-refonte-sol/frontend/src/services/tracker.js`
