import { useState, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DemoProvider } from './contexts/DemoContext';
import { ScopeProvider } from './contexts/ScopeContext';
import { FilterProvider } from './contexts/FilterContext';
import { AuthProvider } from './contexts/AuthContext';
import { ExpertModeProvider } from './contexts/ExpertModeContext';
import { PersonaProvider } from './contexts/PersonaContext';
import { EmissionFactorsProvider } from './contexts/EmissionFactorsContext';
import { PriceReferenceProvider } from './contexts/PriceReferenceContext';
import { RegulatoryConstantsProvider } from './contexts/RegulatoryConstantsContext';
import { RegulatoryRatesProvider } from './contexts/RegulatoryRatesContext';
import { NavigationBadgesProvider } from './contexts/NavigationBadgesContext';
import { EventsProvider } from './contexts/EventsContext';
import ErrorBoundary from './components/ErrorBoundary';
import RequireAuth from './components/RequireAuth';
import { LEGACY_REDIRECTS } from './routes/legacyRedirects';
import UpgradeWizard from './components/UpgradeWizard';
import AppShell from './layout/AppShell';
import { SkeletonCard } from './ui/Skeleton';
import { isActionCenterV4Enabled } from './featureFlags';

// Lazy-loaded pages — code-split per route
const CommandCenter = lazy(() => import('./pages/CommandCenter'));
// Sprint Grammaire v1.2 / Phase 3.4 — Hub Page L11 « Briefing du jour ».
// Énergie P0a cleanup (2026-05-27) — CockpitPilotage lazy import retiré :
// la route /cockpit/pilotage redirige désormais vers /cockpit/jour (cf. App.jsx
// route plus bas). Le fichier pages/CockpitPilotage.jsx reste sur disque (L8
// Mois 5 suppression) mais n'est plus chargé. Source-guard
// test_no_cockpit_pilotage_active_link garantit qu'aucun lien actif ne pointe
// vers /cockpit/pilotage.
// CockpitPilotage est conservé pour les routes legacy d'accès direct mais la
// route canonique /cockpit/jour pointe désormais vers la composition pure L11.
const CockpitJour = lazy(() => import('./pages/CockpitJour'));
// const CockpitPilotage = lazy(() => import('./pages/CockpitPilotage')); // Énergie P0a cleanup 2026-05-27 — route redirigée vers /cockpit/jour
// M2-5.11 audit routes — CockpitDecision et Cockpit imports lazy retirés
// (orphelins : jamais routés, remplacés par CockpitStrategique et CockpitJour
// depuis Phase 3.5 Vague D.5). Fichiers physiques conservés jusqu'au L8
// plan suppression legacy Mois 5 ; on retire juste de l'arbre de modules.
const Patrimoine = lazy(() => import('./pages/Patrimoine'));
const Site360 = lazy(() => import('./pages/Site360'));
const ActionsPage = lazy(() => import('./pages/ActionsPage'));
const ConformitePage = lazy(() => import('./pages/ConformitePage'));
const NotFound = lazy(() => import('./pages/NotFound'));
// Phase 3.5 Vague D.5 — page Synthèse Stratégique data-driven from scratch (ADR-023)
const CockpitStrategique = lazy(() => import('./pages/CockpitStrategique'));
const RegOps = lazy(() => import('./pages/RegOps'));
const ConnectorsPage = lazy(() => import('./pages/ConnectorsPage'));
const WatchersPage = lazy(() => import('./pages/WatchersPage'));
const ConsommationsPage = lazy(() => import('./pages/ConsommationsPage'));
const ConsommationsImportTab = lazy(() =>
  import('./pages/ConsommationsUsages').then((m) => ({ default: m.ImportWizard }))
);
const ConsommationsKBTab = lazy(() =>
  import('./pages/ConsommationsUsages').then((m) => ({ default: m.KBAdminPanel }))
);
const MonitoringPage = lazy(() => import('./pages/MonitoringPage'));
const StatusPage = lazy(() => import('./pages/StatusPage'));
const ImportPage = lazy(() => import('./pages/ImportPage'));
const SegmentationPage = lazy(() => import('./pages/SegmentationPage'));
const ConsumptionDiagPage = lazy(() => import('./pages/ConsumptionDiagPage'));
const BillIntelPage = lazy(() => import('./pages/BillIntelPage'));
const BillingPage = lazy(() => import('./pages/BillingPage'));
const KBExplorerPage = lazy(() => import('./pages/KBExplorerPage'));
const PurchasePage = lazy(() => import('./pages/PurchasePage'));
// PurchaseAssistantPage — now embedded as tab in PurchasePage, route redirects
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'));
const AdminRolesPage = lazy(() => import('./pages/AdminRolesPage'));
const AdminAssignmentsPage = lazy(() => import('./pages/AdminAssignmentsPage'));
const AdminAuditLogPage = lazy(() => import('./pages/AdminAuditLogPage'));
const CxDashboardPage = lazy(() => import('./pages/admin/CxDashboardPage'));
const EnedisPromotionHealthPage = lazy(() => import('./pages/EnedisPromotionHealthPage'));
const ConsumptionExplorerPage = lazy(() => import('./pages/ConsumptionExplorerPage'));
const ConsumptionPortfolioPage = lazy(() => import('./pages/ConsumptionPortfolioPage'));
const ActivationPage = lazy(() => import('./pages/ActivationPage'));
const TertiaireDashboardPage = lazy(() => import('./pages/tertiaire/TertiaireDashboardPage'));
const TertiaireWizardPage = lazy(() => import('./pages/tertiaire/TertiaireWizardPage'));
const TertiaireEfaDetailPage = lazy(() => import('./pages/tertiaire/TertiaireEfaDetailPage'));
const TertiaireAnomaliesPage = lazy(() => import('./pages/tertiaire/TertiaireAnomaliesPage'));
// Usage Steering P2 cleanup (2026-05-27, brief C1) — lazy import retiré :
// la route /usages-horaires redirige désormais vers /usages (cf. plus bas).
// pages/ConsumptionContextPage.jsx reste sur disque (L8 Mois 5 cleanup
// formelle) mais n'est plus chargé par Vite. Source-guard vérifie
// l'absence d'usage actif.
// const ConsumptionContextPage = lazy(() => import('./pages/ConsumptionContextPage'));
const AnomaliesPage = lazy(() => import('./pages/AnomaliesPage'));
// M2-5.2 — Centre d'Action V4 (derrière feature flag VITE_FEATURE_ACTION_CENTER_V4).
const ActionCenterV4ListPage = lazy(() =>
  import('./pages/action-center-v4/ActionCenterV4ListPage').then((m) => ({
    default: m.ActionCenterV4ListPage,
  }))
);
// M2-5.10.D — Page Pilotage / File prioritaire (sous le même feature flag).
const ActionCenterV4PilotagePage = lazy(() =>
  import('./pages/action-center-v4/ActionCenterV4PilotagePage').then((m) => ({
    default: m.ActionCenterV4PilotagePage,
  }))
);
// M2-5.10.E — Page Pilotage / Journal (flux org-wide 7j, même flag).
const ActionCenterV4JournalPage = lazy(() =>
  import('./pages/action-center-v4/ActionCenterV4JournalPage').then((m) => ({
    default: m.ActionCenterV4JournalPage,
  }))
);
const FlexPage = lazy(() => import('./pages/FlexPage'));
const CompliancePipelinePage = lazy(() => import('./pages/CompliancePipelinePage'));
const SiteCompliancePage = lazy(() => import('./pages/SiteCompliancePage'));
const PaymentRulesPage = lazy(() => import('./pages/PaymentRulesPage'));
const PortfolioReconciliationPage = lazy(() => import('./pages/PortfolioReconciliationPage'));
const ContractRadarPage = lazy(() => import('./pages/ContractRadarPage'));
const MethodologiePage = lazy(() => import('./pages/MethodologiePage'));
const Contrats = lazy(() => import('./pages/Contrats'));
// Audit Phase 1.7 P2 : OnboardingPage lazy import retiré — la route /onboarding
// redirige vers /cockpit/jour depuis Phase 0.1, ce chunk n'était jamais rendu
// et alourdissait le bundle. Le fichier `pages/OnboardingPage.jsx` reste sur
// disque pour réutilisation Phase 4 (vrai wizard premier-pas) — il faudra
// alors restaurer l'import lazy ici.
const SireneOnboardingPage = lazy(() => import('./pages/SireneOnboardingPage'));
const AperPage = lazy(() => import('./pages/AperPage'));
const UsagesDashboardPage = lazy(() => import('./pages/UsagesDashboardPage'));

function PageSuspense({ children }) {
  return (
    <Suspense
      fallback={
        <div className="px-6 py-6 space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/3 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function App() {
  const [showUpgradeWizard, setShowUpgradeWizard] = useState(false);

  return (
    <AuthProvider>
      <DemoProvider>
        <ScopeProvider>
          {/* Sprint Grammaire v1.2 — FilterProvider distinct de ScopeContext :
              gère uniquement période/vue/sort, pas la hiérarchie patrimoine.
              Cf docs/vision/promeos_sol_doctrine.md §12 (L11 Hub Page). */}
          <FilterProvider>
            <ExpertModeProvider>
              <PersonaProvider>
                <EmissionFactorsProvider>
                  <PriceReferenceProvider>
                    <RegulatoryConstantsProvider>
                      <RegulatoryRatesProvider>
                        <ErrorBoundary>
                          <NavigationBadgesProvider>
                            <EventsProvider>
                              <Router>
                                <Routes>
                                  {/* Public: Login page */}
                                  <Route
                                    path="/login"
                                    element={
                                      <PageSuspense>
                                        <LoginPage />
                                      </PageSuspense>
                                    }
                                  />

                                  {/* Protected: AppShell layout wraps all routes */}
                                  <Route
                                    element={
                                      <RequireAuth>
                                        <AppShell />
                                      </RequireAuth>
                                    }
                                  >
                                    {/* Phase 15.bis (régression user 30/04) : à la connexion,
                            React Router redirigeait sur "/" qui rendait `<CommandCenter />`
                            (page legacy V1) au lieu du Cockpit dual sol2 refonte.
                            L'utilisateur devait refresh manuellement pour atteindre la
                            nouvelle Vue exécutive — UX cassée première impression démo.
                            Désormais : "/" redirige vers /cockpit/strategique (cohérent
                            Phase 13.D nav démo CFO). CommandCenter reste accessible via
                            /command-center pour rétro-compat audits/tests. */}
                                    <Route
                                      path="/"
                                      element={<Navigate to="/cockpit/strategique" replace />}
                                    />
                                    <Route
                                      path="/command-center"
                                      element={
                                        <PageSuspense>
                                          <CommandCenter />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/patrimoine"
                                      element={
                                        <PageSuspense>
                                          <Patrimoine />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    <Route
                                      path="/sites/:id"
                                      element={
                                        <PageSuspense>
                                          <Site360 />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* M2-5.11.J audit routes — la refonte Centre d'Action V4
                                        remplace le « Plan d'actions » legacy (ActionsPage).
                                        Doctrine §6.2 « pas de coexistence legacy/refonte » :
                                        /actions et ses variantes redirigent vers le référentiel
                                        V4. AnomaliesPage + ActionsPage = même intention =
                                        chemin unique vers /action-center-v4/. */}
                                    <Route
                                      path="/actions"
                                      element={
                                        isActionCenterV4Enabled() ? (
                                          <Navigate to="/action-center-v4" replace />
                                        ) : (
                                          <PageSuspense>
                                            <ActionsPage />
                                          </PageSuspense>
                                        )
                                      }
                                    />
                                    <Route
                                      path="/actions/new"
                                      element={
                                        isActionCenterV4Enabled() ? (
                                          <Navigate to="/action-center-v4" replace />
                                        ) : (
                                          <PageSuspense>
                                            <ActionsPage autoCreate />
                                          </PageSuspense>
                                        )
                                      }
                                    />
                                    <Route
                                      path="/actions/:actionId"
                                      element={
                                        isActionCenterV4Enabled() ? (
                                          <Navigate to="/action-center-v4" replace />
                                        ) : (
                                          <PageSuspense>
                                            <ActionsPage />
                                          </PageSuspense>
                                        )
                                      }
                                    />
                                    <Route
                                      path="/conformite"
                                      element={
                                        <PageSuspense>
                                          <ConformitePage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/conformite/tertiaire"
                                      element={
                                        <PageSuspense>
                                          <TertiaireDashboardPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/conformite/tertiaire/wizard"
                                      element={
                                        <PageSuspense>
                                          <TertiaireWizardPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/conformite/tertiaire/efa/:id"
                                      element={
                                        <PageSuspense>
                                          <TertiaireEfaDetailPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/conformite/tertiaire/anomalies"
                                      element={
                                        <PageSuspense>
                                          <TertiaireAnomaliesPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/conformite/aper"
                                      element={
                                        <PageSuspense>
                                          <AperPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* Energy Copilot — route supprimée (Sprint B P0-7 + Sprint C cleanup) */}
                                    {/* Legacy redirects */}{' '}
                                    {/* Phase Refonte WOW (29/04/2026) — Cockpit dual sol2 :
                            /cockpit/jour       → Briefing L11 Hub Page (CockpitJour, grammaire v1.2)
                            /cockpit/pilotage   → CockpitPilotage (legacy retro-compat)
                            /cockpit/strategique → Décision (Cockpit, dirigeant 3min)
                            /cockpit            → redirect /cockpit/jour (default mode)
                            CommandCenter est conservé temporairement pour rétro-compat
                            d'autres routes legacy ; sera décommissionné Étape 3 du sprint.
                            Sprint Grammaire v1.2 / Phase 3.4 : /cockpit/jour pointe désormais
                            sur CockpitJour (composition pure primitifs grammar/hub L11). */}
                                    {/* M2-5.11 audit routes — route /cockpit manquait (le
                                        COMMAND_SHORTCUTS y pointait sans cible, l'URL retombait
                                        sur la redirect root). Ajoutée : alias canonique du
                                        briefing L11 Energy Manager (cohérent doctrine §6.2 +
                                        commentaire ci-dessus « /cockpit → redirect /cockpit/jour »). */}
                                    <Route
                                      path="/cockpit"
                                      element={<Navigate to="/cockpit/jour" replace />}
                                    />
                                    <Route
                                      path="/cockpit/jour"
                                      element={
                                        <PageSuspense>
                                          <CockpitJour />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* Énergie P0a cleanup (2026-05-27, audit menu Énergie §5
                                        D1 doublon) — /cockpit/pilotage (CockpitPilotage 1722 l
                                        legacy) décommissionné : route remplacée par redirect
                                        canonique vers /cockpit/jour (briefing Energy Manager
                                        L11). Pilotage opérationnel canonique = /action-center-
                                        v4/pilotage (V4 file prioritaire). L'endpoint BE
                                        /api/cockpit/pilotage est passé en 410 Gone FR dans le
                                        même sprint pour cohérence. */}
                                    <Route
                                      path="/cockpit/pilotage"
                                      element={<Navigate to="/cockpit/jour" replace />}
                                    />
                                    {/* Phase 3.5 Vague D.5 — Synthèse Stratégique data-driven from scratch
                                        (ADR-023 + ADR-024). Legacy CockpitDecision accessible via ?legacy=1. */}
                                    <Route
                                      path="/cockpit/strategique"
                                      element={
                                        <PageSuspense>
                                          <CockpitStrategique />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    {/* M2-5.11 — Centre d'Action V4 livré (merge PR #280).
                                        Quand le flag V4 est ON, l'alias legacy /action-center
                                        redirige directement vers la file prioritaire V4 (au
                                        lieu de passer par /anomalies — anti-pattern doctrine
                                        §6.2 chemins multiples vers même intention). Quand le
                                        flag est OFF (kill-switch), retour à l'alias legacy
                                        vers /anomalies pour rétro-compat bookmarks. */}
                                    <Route
                                      path="/action-center"
                                      element={
                                        <Navigate
                                          to={
                                            isActionCenterV4Enabled()
                                              ? '/action-center-v4/pilotage'
                                              : '/anomalies'
                                          }
                                          replace
                                        />
                                      }
                                    />{' '}
                                    {/* M2-5.2 — Centre d'Action V4. Flag OFF =
                                        route absente (404 standard), legacy intact. */}
                                    {isActionCenterV4Enabled() && (
                                      <Route
                                        path="/action-center-v4"
                                        element={
                                          <PageSuspense>
                                            <ActionCenterV4ListPage />
                                          </PageSuspense>
                                        }
                                      />
                                    )}{' '}
                                    {/* M2-5.10.D — Pilotage / File prioritaire (sous
                                        le même feature flag). */}
                                    {isActionCenterV4Enabled() && (
                                      <Route
                                        path="/action-center-v4/pilotage"
                                        element={
                                          <PageSuspense>
                                            <ActionCenterV4PilotagePage />
                                          </PageSuspense>
                                        }
                                      />
                                    )}{' '}
                                    {/* M2-5.10.E — Pilotage / Journal org-wide. */}
                                    {isActionCenterV4Enabled() && (
                                      <Route
                                        path="/action-center-v4/pilotage/journal"
                                        element={
                                          <PageSuspense>
                                            <ActionCenterV4JournalPage />
                                          </PageSuspense>
                                        }
                                      />
                                    )}{' '}
                                    <Route
                                      path="/regops/:id"
                                      element={
                                        <PageSuspense>
                                          <RegOps />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* Consommations: 4-tab layout (Explorer | Portfolio | Import & Analyse | KB) */}
                                    <Route
                                      path="/consommations"
                                      element={
                                        <PageSuspense>
                                          <ConsommationsPage />
                                        </PageSuspense>
                                      }
                                    >
                                      <Route
                                        index
                                        element={<Navigate to="/consommations/portfolio" replace />}
                                      />
                                      <Route
                                        path="explorer"
                                        element={
                                          <PageSuspense>
                                            <ConsumptionExplorerPage bare />
                                          </PageSuspense>
                                        }
                                      />
                                      <Route
                                        path="portfolio"
                                        element={
                                          <PageSuspense>
                                            <ConsumptionPortfolioPage />
                                          </PageSuspense>
                                        }
                                      />
                                      <Route
                                        path="import"
                                        element={
                                          <PageSuspense>
                                            <ConsommationsImportTab />
                                          </PageSuspense>
                                        }
                                      />
                                      <Route
                                        path="kb"
                                        element={
                                          <PageSuspense>
                                            <ConsommationsKBTab />
                                          </PageSuspense>
                                        }
                                      />
                                    </Route>
                                    <Route
                                      path="/connectors"
                                      element={
                                        <PageSuspense>
                                          <ConnectorsPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/watchers"
                                      element={
                                        <PageSuspense>
                                          <WatchersPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/monitoring"
                                      element={
                                        <PageSuspense>
                                          <MonitoringPage />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    <Route
                                      path="/compliance/pipeline"
                                      element={
                                        <PageSuspense>
                                          <CompliancePipelinePage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/compliance/sites/:siteId"
                                      element={
                                        <PageSuspense>
                                          <SiteCompliancePage />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    <Route
                                      path="/diagnostic-conso"
                                      element={
                                        <PageSuspense>
                                          <ConsumptionDiagPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/usages"
                                      element={
                                        <PageSuspense>
                                          <UsagesDashboardPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* Usage Steering P2 cleanup (2026-05-27, brief C1) —
                                        /usages-horaires fusionné dans /usages. La page legacy
                                        ConsumptionContextPage (181 l) restait orpheline en
                                        HIDDEN_PAGES « doublon-sub-page » depuis audit menu
                                        Énergie #313. Redirect propre vers la route canonique
                                        /usages — préserve les deep-links sans casser. */}
                                    <Route
                                      path="/usages-horaires"
                                      element={<Navigate to="/usages" replace />}
                                    />
                                    <Route
                                      path="/bill-intel"
                                      element={
                                        <PageSuspense>
                                          <BillIntelPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/billing"
                                      element={
                                        <PageSuspense>
                                          <BillingPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/achat-energie"
                                      element={
                                        <PageSuspense>
                                          <PurchasePage />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    <Route
                                      path="/kb"
                                      element={
                                        <PageSuspense>
                                          <KBExplorerPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/segmentation"
                                      element={
                                        <PageSuspense>
                                          <SegmentationPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/import"
                                      element={
                                        <PageSuspense>
                                          <ImportPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* M2-5.11.J audit routes — Notifications absorbées par
                                        le Journal V4 (cross-items + cross-event_types). Quand
                                        le flag V4 est ON, /notifications redirige vers le
                                        journal V4 ; sinon NotificationsPage legacy en kill-switch. */}
                                    <Route
                                      path="/notifications"
                                      element={
                                        isActionCenterV4Enabled() ? (
                                          <Navigate
                                            to="/action-center-v4/pilotage/journal"
                                            replace
                                          />
                                        ) : (
                                          <PageSuspense>
                                            <NotificationsPage />
                                          </PageSuspense>
                                        )
                                      }
                                    />{' '}
                                    <Route
                                      path="/activation"
                                      element={
                                        <PageSuspense>
                                          <ActivationPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/status"
                                      element={
                                        <PageSuspense>
                                          <StatusPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/payment-rules"
                                      element={
                                        <PageSuspense>
                                          <PaymentRulesPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/portfolio-reconciliation"
                                      element={
                                        <PageSuspense>
                                          <PortfolioReconciliationPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/contrats"
                                      element={
                                        <PageSuspense>
                                          <Contrats />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/renouvellements"
                                      element={
                                        <PageSuspense>
                                          <ContractRadarPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* P0-B 2026-05-23 : `/onboarding` redirige vers le parcours
                                canonique Sirène (création initiale du patrimoine).
                                Précédemment : redirect vers `/cockpit/jour` qui était une
                                impasse fonctionnelle — un utilisateur tapant `/onboarding`
                                tombait sur le cockpit sans comprendre comment créer son
                                patrimoine. Décision produit P0-B :
                                  - parcours initial = SireneOnboardingPage (SIREN/SIRET)
                                  - import bulk = PatrimoineWizard (déclenché depuis Patrimoine)
                                  - création manuelle = QuickCreateSite drawer
                                  - SiteCreationWizard masqué des entrées principales (legacy)
                                Référence : docs/dev/patrimoine_routes_canonical.md §9. */}
                                    <Route
                                      path="/onboarding"
                                      element={<Navigate to="/onboarding/sirene" replace />}
                                    />
                                    <Route
                                      path="/onboarding/sirene"
                                      element={
                                        <PageSuspense>
                                          <SireneOnboardingPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* IAM pages */}
                                    <Route
                                      path="/admin/users"
                                      element={
                                        <PageSuspense>
                                          <AdminUsersPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/admin/roles"
                                      element={
                                        <PageSuspense>
                                          <AdminRolesPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/admin/assignments"
                                      element={
                                        <PageSuspense>
                                          <AdminAssignmentsPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/admin/audit"
                                      element={
                                        <PageSuspense>
                                          <AdminAuditLogPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/admin/enedis-health"
                                      element={
                                        <PageSuspense>
                                          <EnedisPromotionHealthPage />
                                        </PageSuspense>
                                      }
                                    />
                                    <Route
                                      path="/admin/cx-dashboard"
                                      element={
                                        <PageSuspense>
                                          <CxDashboardPage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* M2-5.11 — quand le flag Action Center V4 est ON,
                                        /anomalies redirige vers /action-center-v4/pilotage
                                        (la refonte V4 est le hub canonique, AnomaliesPage
                                        legacy n'est plus rendue — doctrine §6.2 : pas de
                                        coexistence legacy/refonte). Le composant AnomaliesPage
                                        reste importé pour le kill-switch flag=OFF. */}
                                    <Route
                                      path="/anomalies"
                                      element={
                                        isActionCenterV4Enabled() ? (
                                          <Navigate to="/action-center-v4/pilotage" replace />
                                        ) : (
                                          <PageSuspense>
                                            <AnomaliesPage />
                                          </PageSuspense>
                                        )
                                      }
                                    />
                                    {/* Sprint 1.10 — page 10/10 Flex Intelligence (couverture nav 100%). */}
                                    <Route
                                      path="/flex"
                                      element={
                                        <PageSuspense>
                                          <FlexPage />
                                        </PageSuspense>
                                      }
                                    />{' '}
                                    {/* Legacy redirects → routes Phase 3.1 (alias mode strategique pour CFO/DG) */}{' '}
                                    {/* Sprint 1.3bis P0-A — Méthodologie Sol §5 trust signals */}
                                    <Route
                                      path="/methodologie/:docKey"
                                      element={
                                        <PageSuspense>
                                          <MethodologiePage />
                                        </PageSuspense>
                                      }
                                    />
                                    {/* Phase 3.bis.a — 31 redirects legacy factorisés
                            (cf routes/legacyRedirects.js).
                            React Router résoud les paths les plus spécifiques
                            d'abord, donc l'ordre n'a pas d'impact sur le matching. */}
                                    {LEGACY_REDIRECTS.map(([from, to]) => (
                                      <Route
                                        key={from}
                                        path={from}
                                        element={<Navigate to={to} replace />}
                                      />
                                    ))}
                                    {/* Catch-all */}
                                    <Route
                                      path="*"
                                      element={
                                        <PageSuspense>
                                          <NotFound />
                                        </PageSuspense>
                                      }
                                    />
                                  </Route>
                                </Routes>

                                {/* Upgrade Wizard Modal */}
                                {showUpgradeWizard && (
                                  <UpgradeWizard
                                    onClose={(completed) => {
                                      setShowUpgradeWizard(false);
                                      if (completed) window.location.assign('/patrimoine');
                                    }}
                                  />
                                )}
                              </Router>
                            </EventsProvider>
                          </NavigationBadgesProvider>
                        </ErrorBoundary>
                      </RegulatoryRatesProvider>
                    </RegulatoryConstantsProvider>
                  </PriceReferenceProvider>
                </EmissionFactorsProvider>
              </PersonaProvider>
            </ExpertModeProvider>
          </FilterProvider>
        </ScopeProvider>
      </DemoProvider>
    </AuthProvider>
  );
}

export default App;
