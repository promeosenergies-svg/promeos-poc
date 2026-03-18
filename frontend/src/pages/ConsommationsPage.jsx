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
  { to: '/consommations/import', label: 'Import', icon: Upload },
  { to: '/consommations/kb', label: 'Memobox', icon: Database },
];

export default function ConsommationsPage() {
  const tabBar = (
    <div className="flex gap-1 ml-4">
      {TABS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              isActive ? 'bg-blue-600 text-white' : 'text-gray-500 bg-gray-100 hover:bg-gray-200'
            }`
          }
        >
          <Icon size={13} />
          {label}
        </NavLink>
      ))}
    </div>
  );

  return (
    <PageShell icon={Zap} title="Consommations" inlineActions={tabBar}>
      {/* Nested route content */}
      <Outlet />
    </PageShell>
  );
}
