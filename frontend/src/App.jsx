import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { Rocket } from 'lucide-react';
import { DemoProvider } from './contexts/DemoContext';
import DemoBanner from './components/DemoBanner';
import UpgradeWizard from './components/UpgradeWizard';
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

function App() {
  const [showUpgradeWizard, setShowUpgradeWizard] = useState(false);

  return (
    <DemoProvider>
      <Router>
        <div className="min-h-screen bg-gray-100">
          {/* Demo Banner */}
          <DemoBanner onUpgradeClick={() => setShowUpgradeWizard(true)} />

          {/* Navigation */}
          <nav className="bg-white shadow-sm">
            <div className="max-w-7xl mx-auto px-6 py-4">
              <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-blue-600">PROMEOS</h1>
                <div className="flex items-center gap-3">
                  <Link
                    to="/"
                    className="px-4 py-2 rounded hover:bg-blue-50 text-gray-700 hover:text-blue-600 transition text-sm"
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/cockpit-2min"
                    className="px-4 py-2 rounded bg-emerald-600 text-white hover:bg-emerald-700 transition text-sm"
                  >
                    2 minutes
                  </Link>
                  <Link
                    to="/cockpit"
                    className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 transition text-sm"
                  >
                    Cockpit Executif
                  </Link>
                  <Link
                    to="/action-plan"
                    className="px-4 py-2 rounded bg-indigo-600 text-white hover:bg-indigo-700 transition text-sm"
                  >
                    Plan d'action
                  </Link>
                  <Link
                    to="/consommations"
                    className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 transition text-sm"
                  >
                    Conso & Usages
                  </Link>
                  <Link
                    to="/monitoring"
                    className="px-4 py-2 rounded bg-amber-600 text-white hover:bg-amber-700 transition text-sm"
                  >
                    Monitoring
                  </Link>
                  <Link
                    to="/connectors"
                    className="px-4 py-2 rounded hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition text-sm"
                  >
                    Connecteurs
                  </Link>
                  <Link
                    to="/watchers"
                    className="px-4 py-2 rounded hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition text-sm"
                  >
                    Veille Réglementaire
                  </Link>
                  <Link
                    to="/segmentation"
                    className="px-4 py-2 rounded hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition text-sm"
                  >
                    Segmentation
                  </Link>
                  <Link
                    to="/import"
                    className="px-4 py-2 rounded hover:bg-gray-100 text-gray-700 hover:text-gray-900 transition text-sm"
                  >
                    Import
                  </Link>
                  <Link
                    to="/status"
                    className="px-3 py-2 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition text-xs"
                  >
                    Statut
                  </Link>
                  <button
                    onClick={() => setShowUpgradeWizard(true)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-sm font-semibold hover:from-blue-700 hover:to-indigo-700 transition"
                  >
                    <Rocket size={16} />
                    Rendre actionnable
                  </button>
                </div>
              </div>
            </div>
          </nav>

          {/* Routes */}
          <Routes>
            <Route path="/" element={<Dashboard onUpgradeClick={() => setShowUpgradeWizard(true)} />} />
            <Route path="/cockpit-2min" element={<Cockpit2MinPage onUpgradeClick={() => setShowUpgradeWizard(true)} />} />
            <Route path="/cockpit" element={<Cockpit />} />
            <Route path="/sites/:id" element={<SiteDetail />} />
            <Route path="/action-plan" element={<ActionPlan />} />
            <Route path="/regops/:id" element={<RegOps />} />
            <Route path="/consommations" element={<ConsommationsUsages />} />
            <Route path="/connectors" element={<ConnectorsPage />} />
            <Route path="/watchers" element={<WatchersPage />} />
            <Route path="/monitoring" element={<MonitoringPage />} />
            <Route path="/segmentation" element={<SegmentationPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/status" element={<StatusPage />} />
          </Routes>

          {/* Upgrade Wizard Modal */}
          {showUpgradeWizard && (
            <UpgradeWizard onClose={() => setShowUpgradeWizard(false)} />
          )}
        </div>
      </Router>
    </DemoProvider>
  );
}

export default App;
