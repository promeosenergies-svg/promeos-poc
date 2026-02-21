/**
 * PROMEOS — Consommations Layout Page
 * Wrapper with 3 tabs (Explorer | Import & Analyse | Knowledge Base)
 * and nested sub-routes via <Outlet />.
 */
import { NavLink, Outlet } from 'react-router-dom';
import { BarChart3, Upload, Database, Zap } from 'lucide-react';
import { PageShell } from '../ui';

const TABS = [
  { to: '/consommations/explorer', label: 'Explorer', icon: BarChart3 },
  { to: '/consommations/import', label: 'Import & Analyse', icon: Upload },
  { to: '/consommations/kb', label: 'Knowledge Base', icon: Database },
];

export default function ConsommationsPage() {
  return (
    <PageShell
      icon={Zap}
      title="Consommations"
      subtitle="Explorer, importer & analyser vos données énergie"
    >
      {/* Tab bar */}
      <div className="flex gap-2 -mt-2">
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Nested route content */}
      <Outlet />
    </PageShell>
  );
}
