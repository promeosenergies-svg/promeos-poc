import { useState, lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DemoProvider } from './contexts/DemoContext';
import { ScopeProvider } from './contexts/ScopeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ExpertModeProvider } from './contexts/ExpertModeContext';
import ErrorBoundary from './components/ErrorBoundary';
import RequireAuth from './components/RequireAuth';
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
const PurchaseAssistantPage = lazy(() => import('./pages/PurchaseAssistantPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'));
const AdminRolesPage = lazy(() => import('./pages/AdminRolesPage'));
const AdminAssignmentsPage = lazy(() => import('./pages/AdminAssignmentsPage'));
const AdminAuditLogPage = lazy(() => import('./pages/AdminAuditLogPage'));
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
const CompliancePipelinePage = lazy(() => import('./pages/CompliancePipelinePage'));
const SiteCompliancePage = lazy(() => import('./pages/SiteCompliancePage'));
const PaymentRulesPage = lazy(() => import('./pages/PaymentRulesPage'));
const PortfolioReconciliationPage = lazy(() => import('./pages/PortfolioReconciliationPage'));
const ContractRadarPage = lazy(() => import('./pages/ContractRadarPage'));
const Contrats = lazy(() => import('./pages/Contrats'));
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'));
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
                    />
                    <Route
                      path="/patrimoine/nouveau"
                      element={<Navigate to="/patrimoine?wizard=open" replace />}
                    />
                    <Route path="/sites" element={<Navigate to="/patrimoine" replace />} />
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
                    {/* Energy Copilot — route supprimée (Sprint B P0-7: plus de doublon avec Cockpit) */}
                    <Route path="/energy-copilot" element={<Navigate to="/" replace />} />

                    {/* Legacy redirects */}
                    <Route path="/dashboard-legacy" element={<Navigate to="/" replace />} />
                    <Route
                      path="/cockpit"
                      element={
                        <PageSuspense>
                          <Cockpit />
                        </PageSuspense>
                      }
                    />
                    <Route
                      path="/sites-legacy/:id"
                      element={<Navigate to="/patrimoine" replace />}
                    />
                    <Route
                      path="/action-center"
                      element={
                        <PageSuspense>
                          <ActionCenterPage />
                        </PageSuspense>
                      }
                    />
                    <Route path="/action-plan" element={<Navigate to="/anomalies" replace />} />
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
                      <Route index element={<Navigate to="/consommations/portfolio" replace />} />
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
                    />
                    <Route path="/compliance" element={<Navigate to="/conformite" replace />} />
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
                    />
                    <Route
                      path="/compliance/sites"
                      element={<Navigate to="/conformite" replace />}
                    />
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
                    />
                    <Route
                      path="/achat-assistant"
                      element={
                        <PageSuspense>
                          <PurchaseAssistantPage />
                        </PageSuspense>
                      }
                    />
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
                    />
                    <Route
                      path="/explorer"
                      element={<Navigate to="/consommations/portfolio" replace />}
                    />
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

                    {/* URL aliases (redirect to canonical routes) */}
                    <Route
                      path="/plan-action"
                      element={<Navigate to="/anomalies?tab=actions" replace />}
                    />
                    <Route
                      path="/plan-actions"
                      element={<Navigate to="/anomalies?tab=actions" replace />}
                    />
                    <Route path="/factures" element={<Navigate to="/bill-intel" replace />} />
                    <Route path="/facturation" element={<Navigate to="/billing" replace />} />
                    <Route
                      path="/anomalies"
                      element={
                        <PageSuspense>
                          <AnomaliesPage />
                        </PageSuspense>
                      }
                    />
                    <Route
                      path="/diagnostic"
                      element={<Navigate to="/diagnostic-conso" replace />}
                    />
                    <Route path="/performance" element={<Navigate to="/monitoring" replace />} />
                    <Route path="/achats" element={<Navigate to="/achat-energie" replace />} />
                    <Route path="/purchase" element={<Navigate to="/achat-energie" replace />} />
                    <Route path="/referentiels" element={<Navigate to="/kb" replace />} />
                    <Route path="/synthese" element={<Navigate to="/cockpit" replace />} />
                    <Route path="/executive" element={<Navigate to="/cockpit" replace />} />
                    <Route path="/dashboard" element={<Navigate to="/cockpit" replace />} />
                    <Route
                      path="/conso"
                      element={<Navigate to="/consommations/portfolio" replace />}
                    />
                    <Route path="/imports" element={<Navigate to="/import" replace />} />
                    <Route path="/connexions" element={<Navigate to="/connectors" replace />} />
                    <Route path="/veille" element={<Navigate to="/watchers" replace />} />
                    <Route path="/alertes" element={<Navigate to="/notifications" replace />} />
                    <Route
                      path="/ems"
                      element={<Navigate to="/consommations/portfolio" replace />}
                    />
                    <Route path="/donnees" element={<Navigate to="/activation" replace />} />
                    <Route
                      path="/contracts-radar"
                      element={<Navigate to="/renouvellements" replace />}
                    />

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
          </ExpertModeProvider>
        </ScopeProvider>
      </DemoProvider>
    </AuthProvider>
  );
}

export default App;
