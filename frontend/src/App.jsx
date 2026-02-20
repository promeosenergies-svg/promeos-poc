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
const ConformitePage = lazy(() => import('./pages/ConformitePage'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Cockpit = lazy(() => import('./pages/Cockpit'));
const SiteDetail = lazy(() => import('./pages/SiteDetail'));
const ActionPlan = lazy(() => import('./pages/ActionPlan'));
const RegOps = lazy(() => import('./pages/RegOps'));
const ConnectorsPage = lazy(() => import('./pages/ConnectorsPage'));
const WatchersPage = lazy(() => import('./pages/WatchersPage'));
const ConsommationsPage = lazy(() => import('./pages/ConsommationsPage'));
const ConsommationsImportTab = lazy(() => import('./pages/ConsommationsUsages').then(m => ({ default: m.ImportWizard })));
const ConsommationsKBTab = lazy(() => import('./pages/ConsommationsUsages').then(m => ({ default: m.KBAdminPanel })));
const MonitoringPage = lazy(() => import('./pages/MonitoringPage'));
const StatusPage = lazy(() => import('./pages/StatusPage'));
const ImportPage = lazy(() => import('./pages/ImportPage'));
const SegmentationPage = lazy(() => import('./pages/SegmentationPage'));
const CompliancePage = lazy(() => import('./pages/CompliancePage'));
const ConsumptionDiagPage = lazy(() => import('./pages/ConsumptionDiagPage'));
const BillIntelPage = lazy(() => import('./pages/BillIntelPage'));
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
const ActivationPage = lazy(() => import('./pages/ActivationPage'));

function PageSuspense({ children }) {
  return (
    <Suspense fallback={
      <div className="px-6 py-6 space-y-6">
        <div className="h-8 bg-gray-200 rounded w-1/3 animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    }>
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
                <Route path="/login" element={<PageSuspense><LoginPage /></PageSuspense>} />

                {/* Protected: AppShell layout wraps all routes */}
                <Route element={<RequireAuth><AppShell /></RequireAuth>}>
                  {/* V1 + V2 pages */}
                  <Route path="/" element={<PageSuspense><CommandCenter /></PageSuspense>} />
                  <Route path="/patrimoine" element={<PageSuspense><Patrimoine /></PageSuspense>} />
                  <Route path="/sites/:id" element={<PageSuspense><Site360 /></PageSuspense>} />
                  <Route path="/actions" element={<PageSuspense><ActionsPage /></PageSuspense>} />
                  <Route path="/conformite" element={<PageSuspense><ConformitePage /></PageSuspense>} />

                  {/* Existing pages */}
                  <Route path="/dashboard-legacy" element={<PageSuspense><Dashboard onUpgradeClick={() => setShowUpgradeWizard(true)} /></PageSuspense>} />
                  {/* /cockpit-2min redirige vers la vue exécutive canonique */}
                  <Route path="/cockpit-2min" element={<Navigate to="/cockpit" replace />} />
                  <Route path="/cockpit" element={<PageSuspense><Cockpit /></PageSuspense>} />
                  <Route path="/sites-legacy/:id" element={<PageSuspense><SiteDetail /></PageSuspense>} />
                  <Route path="/action-plan" element={<PageSuspense><ActionPlan /></PageSuspense>} />
                  <Route path="/regops/:id" element={<PageSuspense><RegOps /></PageSuspense>} />
                  {/* Consommations: 3-tab layout (Explorer | Import & Analyse | KB) */}
                  <Route path="/consommations" element={<PageSuspense><ConsommationsPage /></PageSuspense>}>
                    <Route index element={<Navigate to="/consommations/explorer" replace />} />
                    <Route path="explorer" element={<PageSuspense><ConsumptionExplorerPage bare /></PageSuspense>} />
                    <Route path="import" element={<PageSuspense><ConsommationsImportTab /></PageSuspense>} />
                    <Route path="kb" element={<PageSuspense><ConsommationsKBTab /></PageSuspense>} />
                  </Route>
                  <Route path="/connectors" element={<PageSuspense><ConnectorsPage /></PageSuspense>} />
                  <Route path="/watchers" element={<PageSuspense><WatchersPage /></PageSuspense>} />
                  <Route path="/monitoring" element={<PageSuspense><MonitoringPage /></PageSuspense>} />
                  <Route path="/compliance" element={<PageSuspense><CompliancePage /></PageSuspense>} />
                  <Route path="/diagnostic-conso" element={<PageSuspense><ConsumptionDiagPage /></PageSuspense>} />
                  <Route path="/bill-intel" element={<PageSuspense><BillIntelPage /></PageSuspense>} />
                  <Route path="/achat-energie" element={<PageSuspense><PurchasePage /></PageSuspense>} />
                  <Route path="/achat-assistant" element={<PageSuspense><PurchaseAssistantPage /></PageSuspense>} />
                  <Route path="/kb" element={<PageSuspense><KBExplorerPage /></PageSuspense>} />
                  <Route path="/segmentation" element={<PageSuspense><SegmentationPage /></PageSuspense>} />
                  <Route path="/import" element={<PageSuspense><ImportPage /></PageSuspense>} />
                  <Route path="/notifications" element={<PageSuspense><NotificationsPage /></PageSuspense>} />
                  <Route path="/explorer" element={<Navigate to="/consommations/explorer" replace />} />
                  <Route path="/activation" element={<PageSuspense><ActivationPage /></PageSuspense>} />
                  <Route path="/status" element={<PageSuspense><StatusPage /></PageSuspense>} />

                  {/* IAM pages */}
                  <Route path="/admin/users" element={<PageSuspense><AdminUsersPage /></PageSuspense>} />
                  <Route path="/admin/roles" element={<PageSuspense><AdminRolesPage /></PageSuspense>} />
                  <Route path="/admin/assignments" element={<PageSuspense><AdminAssignmentsPage /></PageSuspense>} />
                  <Route path="/admin/audit" element={<PageSuspense><AdminAuditLogPage /></PageSuspense>} />

                  {/* URL aliases (redirect to canonical routes) */}
                  <Route path="/plan-action" element={<Navigate to="/actions" replace />} />
                  <Route path="/plan-actions" element={<Navigate to="/actions" replace />} />
                  <Route path="/factures" element={<Navigate to="/bill-intel" replace />} />
                  <Route path="/facturation" element={<Navigate to="/bill-intel" replace />} />
                  <Route path="/anomalies" element={<Navigate to="/diagnostic-conso" replace />} />
                  <Route path="/diagnostic" element={<Navigate to="/diagnostic-conso" replace />} />
                  <Route path="/performance" element={<Navigate to="/monitoring" replace />} />
                  <Route path="/achats" element={<Navigate to="/achat-energie" replace />} />
                  <Route path="/purchase" element={<Navigate to="/achat-energie" replace />} />
                  <Route path="/referentiels" element={<Navigate to="/kb" replace />} />
                  <Route path="/synthese" element={<Navigate to="/cockpit" replace />} />
                  <Route path="/executive" element={<Navigate to="/cockpit" replace />} />
                  <Route path="/dashboard" element={<Navigate to="/" replace />} />
                  <Route path="/conso" element={<Navigate to="/consommations/explorer" replace />} />
                  <Route path="/imports" element={<Navigate to="/import" replace />} />
                  <Route path="/connexions" element={<Navigate to="/connectors" replace />} />
                  <Route path="/veille" element={<Navigate to="/watchers" replace />} />
                  <Route path="/alertes" element={<Navigate to="/notifications" replace />} />
                  <Route path="/ems" element={<Navigate to="/consommations/explorer" replace />} />
                  <Route path="/donnees" element={<Navigate to="/activation" replace />} />

                  {/* Catch-all */}
                  <Route path="*" element={<PageSuspense><NotFound /></PageSuspense>} />
                </Route>
              </Routes>

              {/* Upgrade Wizard Modal */}
              {showUpgradeWizard && (
                <UpgradeWizard onClose={() => setShowUpgradeWizard(false)} />
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
