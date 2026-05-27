/**
 * PROMEOS — Consommations Layout Page
 * Wrapper with tabs (Portefeuille | Explorer | Import & Analyse)
 * and nested sub-routes via <Outlet />.
 *
 * Énergie P0b visual credibility (2026-05-27, brief C6) — onglet
 * « Memobox » retiré du wrapper. Il pointait vers /kb (route Admin)
 * ce qui créait un saut de contexte cross-module et cassait la
 * cohérence du wrapper « Consommations → vues énergétiques ». /kb
 * reste accessible via module admin NavRegistry + ⌘K search.
 */
import { NavLink, Outlet } from 'react-router-dom';
import { BarChart3, Upload, Zap, Building2 } from 'lucide-react';
import { PageShell } from '../ui';
import { useScope } from '../contexts/ScopeContext';

const TABS = [
  { to: '/consommations/portfolio', label: 'Portefeuille', icon: Building2 },
  { to: '/consommations/explorer', label: 'Explorer', icon: BarChart3 },
  { to: '/consommations/import', label: 'Import', icon: Upload },
];

export default function ConsommationsPage() {
  const { sitesLoading } = useScope();

  if (sitesLoading) {
    return (
      <PageShell icon={Zap} title="Consommations" subtitle="Chargement...">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-gray-200 rounded" />
          <div className="h-60 bg-gray-200 rounded-lg" />
        </div>
      </PageShell>
    );
  }

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
