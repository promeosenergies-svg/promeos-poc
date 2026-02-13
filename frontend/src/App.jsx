import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { DemoProvider } from './contexts/DemoContext';
import { ScopeProvider } from './contexts/ScopeContext';
import { AuthProvider } from './contexts/AuthContext';
import { ExpertModeProvider } from './contexts/ExpertModeContext';
import ErrorBoundary from './components/ErrorBoundary';
import RequireAuth from './components/RequireAuth';
import UpgradeWizard from './components/UpgradeWizard';
import AppShell from './layout/AppShell';

// Pages — V1 + V2
import CommandCenter from './pages/CommandCenter';
import Patrimoine from './pages/Patrimoine';
import Site360 from './pages/Site360';
import ActionsPage from './pages/ActionsPage';
import ConformitePage from './pages/ConformitePage';
import NotFound from './pages/NotFound';

// Pages — existing (kept as-is)
import Dashboard from './pages/Dashboard';
import Cockpit from './pages/Cockpit';
import SiteDetail from './pages/SiteDetail';
import ActionPlan from './pages/ActionPlan';
import RegOps from './pages/RegOps';
import ConnectorsPage from './pages/ConnectorsPage';
import WatchersPage from './pages/WatchersPage';
import ConsommationsUsages from './pages/ConsommationsUsages';
import MonitoringPage from './pages/MonitoringPage';
import StatusPage from './pages/StatusPage';
import ImportPage from './pages/ImportPage';
import Cockpit2MinPage from './pages/Cockpit2MinPage';
import SegmentationPage from './pages/SegmentationPage';
import CompliancePage from './pages/CompliancePage';
import ConsumptionDiagPage from './pages/ConsumptionDiagPage';
import BillIntelPage from './pages/BillIntelPage';
import KBExplorerPage from './pages/KBExplorerPage';
import PurchasePage from './pages/PurchasePage';
import NotificationsPage from './pages/NotificationsPage';

// IAM pages
import LoginPage from './pages/LoginPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminRolesPage from './pages/AdminRolesPage';
import AdminAssignmentsPage from './pages/AdminAssignmentsPage';
import AdminAuditLogPage from './pages/AdminAuditLogPage';

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
                <Route path="/login" element={<LoginPage />} />

                {/* Protected: AppShell layout wraps all routes */}
                <Route element={<RequireAuth><AppShell /></RequireAuth>}>
                  {/* V1 + V2 pages */}
                  <Route path="/" element={<CommandCenter />} />
                  <Route path="/patrimoine" element={<Patrimoine />} />
                  <Route path="/sites/:id" element={<Site360 />} />
                  <Route path="/actions" element={<ActionsPage />} />
                  <Route path="/conformite" element={<ConformitePage />} />

                  {/* Existing pages (unchanged) */}
                  <Route path="/dashboard-legacy" element={<Dashboard onUpgradeClick={() => setShowUpgradeWizard(true)} />} />
                  <Route path="/cockpit-2min" element={<Cockpit2MinPage onUpgradeClick={() => setShowUpgradeWizard(true)} />} />
                  <Route path="/cockpit" element={<Cockpit />} />
                  <Route path="/sites-legacy/:id" element={<SiteDetail />} />
                  <Route path="/action-plan" element={<ActionPlan />} />
                  <Route path="/regops/:id" element={<RegOps />} />
                  <Route path="/consommations" element={<ConsommationsUsages />} />
                  <Route path="/connectors" element={<ConnectorsPage />} />
                  <Route path="/watchers" element={<WatchersPage />} />
                  <Route path="/monitoring" element={<MonitoringPage />} />
                  <Route path="/compliance" element={<CompliancePage />} />
                  <Route path="/diagnostic-conso" element={<ConsumptionDiagPage />} />
                  <Route path="/bill-intel" element={<BillIntelPage />} />
                  <Route path="/achat-energie" element={<PurchasePage />} />
                  <Route path="/kb" element={<KBExplorerPage />} />
                  <Route path="/segmentation" element={<SegmentationPage />} />
                  <Route path="/import" element={<ImportPage />} />
                  <Route path="/notifications" element={<NotificationsPage />} />
                  <Route path="/status" element={<StatusPage />} />

                  {/* IAM pages */}
                  <Route path="/admin/users" element={<AdminUsersPage />} />
                  <Route path="/admin/roles" element={<AdminRolesPage />} />
                  <Route path="/admin/assignments" element={<AdminAssignmentsPage />} />
                  <Route path="/admin/audit" element={<AdminAuditLogPage />} />

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
                  <Route path="/conso" element={<Navigate to="/consommations" replace />} />
                  <Route path="/imports" element={<Navigate to="/import" replace />} />
                  <Route path="/connexions" element={<Navigate to="/connectors" replace />} />
                  <Route path="/veille" element={<Navigate to="/watchers" replace />} />
                  <Route path="/alertes" element={<Navigate to="/notifications" replace />} />

                  {/* Catch-all */}
                  <Route path="*" element={<NotFound />} />
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
