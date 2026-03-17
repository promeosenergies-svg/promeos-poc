/**
 * PROMEOS — Consommations Layout Page
 * Wrapper with tabs (Explorer | Portefeuille | Import & Analyse | Mémobox)
 * and nested sub-routes via <Outlet />.
 */
import { NavLink, Outlet } from 'react-router-dom';
import { BarChart3, Upload, Database, Zap, Building2 } from 'lucide-react';
import { PageShell } from '../ui';

const TABS = [
  { to: '/consommations/portfolio', label: 'Portefeuille', icon: Building2 },
  { to: '/consommations/explorer', label: 'Explorer', icon: BarChart3 },
  { to: '/consommations/import', label: 'Import & Analyse', icon: Upload },
  { to: '/consommations/kb', label: 'Mémobox', icon: Database },
];

export default function ConsommationsPage() {
  const tabBar = (
    <div className="flex gap-2">
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
  );

  return (
    <PageShell icon={Zap} title="Consommations" actions={tabBar}>
      {/* Nested route content */}
      <Outlet />
    </PageShell>
  );
}
