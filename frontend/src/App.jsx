import { useState, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DemoProvider } from './contexts/DemoContext';
import { ScopeProvider } from './contexts/ScopeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ExpertModeProvider } from './contexts/ExpertModeContext';
import { EmissionFactorsProvider } from './contexts/EmissionFactorsContext';
import { PriceReferenceProvider } from './contexts/PriceReferenceContext';
import ErrorBoundary from './components/ErrorBoundary';
import RequireAuth from './components/RequireAuth';
import { LEGACY_REDIRECTS } from './routes/legacyRedirects';
import UpgradeWizard from './components/UpgradeWizard';
import AppShell from './layout/AppShell';
import { SkeletonCard } from './ui/Skeleton';

// Lazy-loaded pages — code-split per route
const CommandCenter = lazy(() => import('./pages/CommandCenter'));
const Patrimoine = lazy(() => import('./pages/Patrimoine'));
const Site360 = lazy(() => import('./pages/Site360'));
const ActionsPage = lazy(() => import('./pages/ActionsPage'));
const ActionCenterPage = lazy(() => import('./pages/ActionCenterPage'));
const ConformitePage = lazy(() => import('./pages/ConformitePage'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Cockpit = lazy(() => import('./pages/Cockpit'));
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
// CompliancePage deprecated — /compliance root redirects to /conformite (V92)
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
const AdminKBMetricsPage = lazy(() => import('./pages/AdminKBMetricsPage'));
const CxDashboardPage = lazy(() => import('./pages/admin/CxDashboardPage'));
const EnedisPromotionHealthPage = lazy(() => import('./pages/EnedisPromotionHealthPage'));
const ConsumptionExplorerPage = lazy(() => import('./pages/ConsumptionExplorerPage'));
// EnergyCopilotPage — dead code, no active route (Sprint B P0-7)
// const EnergyCopilotPage = lazy(() => import('./pages/EnergyCopilotPage'));
const ConsumptionPortfolioPage = lazy(() => import('./pages/ConsumptionPortfolioPage'));
const ActivationPage = lazy(() => import('./pages/ActivationPage'));
const TertiaireDashboardPage = lazy(() => import('./pages/tertiaire/TertiaireDashboardPage'));
const TertiaireWizardPage = lazy(() => import('./pages/tertiaire/TertiaireWizardPage'));
const TertiaireEfaDetailPage = lazy(() => import('./pages/tertiaire/TertiaireEfaDetailPage'));
const TertiaireAnomaliesPage = lazy(() => import('./pages/tertiaire/TertiaireAnomaliesPage'));
const ConsumptionContextPage = lazy(() => import('./pages/ConsumptionContextPage'));
const AnomaliesPage = lazy(() => import('./pages/AnomaliesPage'));
const FlexPage = lazy(() => import('./pages/FlexPage'));
const CompliancePipelinePage = lazy(() => import('./pages/CompliancePipelinePage'));
const SiteCompliancePage = lazy(() => import('./pages/SiteCompliancePage'));
const PaymentRulesPage = lazy(() => import('./pages/PaymentRulesPage'));
const PortfolioReconciliationPage = lazy(() => import('./pages/PortfolioReconciliationPage'));
const ContractRadarPage = lazy(() => import('./pages/ContractRadarPage'));
const MethodologiePage = lazy(() => import('./pages/MethodologiePage'));
const Contrats = lazy(() => import('./pages/Contrats'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
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
          <ExpertModeProvider>
            <EmissionFactorsProvider>
              <PriceReferenceProvider>
                <ErrorBoundary>
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
                        {/* V1 + V2 pages */}
                        <Route
                          path="/"
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
                        <Route
                          path="/actions"
                          element={
                            <PageSuspense>
                              <ActionsPage />
                            </PageSuspense>
                          }
                        />
                        <Route
                          path="/actions/new"
                          element={
                            <PageSuspense>
                              <ActionsPage autoCreate />
                            </PageSuspense>
                          }
                        />
                        <Route
                          path="/actions/:actionId"
                          element={
                            <PageSuspense>
                              <ActionsPage />
                            </PageSuspense>
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
                        {/* Phase 3.1 — Cockpit dual sol2 routes canoniques :
                            /cockpit/jour       → Pilotage (CommandCenter, energy manager 30s)
                            /cockpit/strategique → Décision (Cockpit, dirigeant 3min)
                            /cockpit            → redirect /cockpit/jour (default mode)
                            Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §4.B Phase 3.1 */}
                        <Route
                          path="/cockpit/jour"
                          element={
                            <PageSuspense>
                              <CommandCenter />
                            </PageSuspense>
                          }
                        />
                        <Route
                          path="/cockpit/strategique"
                          element={
                            <PageSuspense>
                              <Cockpit />
                            </PageSuspense>
                          }
                        />{' '}
                        <Route
                          path="/action-center"
                          element={
                            <PageSuspense>
                              <ActionCenterPage />
                            </PageSuspense>
                          }
                        />{' '}
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
                        <Route
                          path="/usages-horaires"
                          element={
                            <PageSuspense>
                              <ConsumptionContextPage />
                            </PageSuspense>
                          }
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
                        <Route
                          path="/notifications"
                          element={
                            <PageSuspense>
                              <NotificationsPage />
                            </PageSuspense>
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
                        <Route
                          path="/onboarding"
                          element={
                            <PageSuspense>
                              <OnboardingPage />
                            </PageSuspense>
                          }
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
                        {/* URL aliases (redirect to canonical routes) */}{' '}
                        <Route
                          path="/anomalies"
                          element={
                            <PageSuspense>
                              <AnomaliesPage />
                            </PageSuspense>
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
                          <Route key={from} path={from} element={<Navigate to={to} replace />} />
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
                </ErrorBoundary>
              </PriceReferenceProvider>
            </EmissionFactorsProvider>
          </ExpertModeProvider>
        </ScopeProvider>
      </DemoProvider>
    </AuthProvider>
  );
}

export default App;
