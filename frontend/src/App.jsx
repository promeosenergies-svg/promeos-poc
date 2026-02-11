import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { DemoProvider } from './contexts/DemoContext';
import { ScopeProvider } from './contexts/ScopeContext';
import ErrorBoundary from './components/ErrorBoundary';
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

function App() {
  const [showUpgradeWizard, setShowUpgradeWizard] = useState(false);

  return (
    <DemoProvider>
      <ScopeProvider>
        <ErrorBoundary>
          <Router>
            <Routes>
              {/* AppShell layout wraps all routes */}
              <Route element={<AppShell />}>
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
                <Route path="/segmentation" element={<SegmentationPage />} />
                <Route path="/import" element={<ImportPage />} />
                <Route path="/status" element={<StatusPage />} />

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
      </ScopeProvider>
    </DemoProvider>
  );
}

export default App;
