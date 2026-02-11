import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Settings, HelpCircle,
  BarChart3, Import, Users, Receipt, BookOpen, ShoppingCart,
} from 'lucide-react';

const NAV_COCKPIT = [
  { to: '/',           icon: LayoutDashboard, label: 'Accueil' },
  { to: '/cockpit',    icon: FileText,        label: 'Vue Ex\u00e9cutive' },
];

const NAV_EXECUTION = [
  { to: '/conformite', icon: ShieldCheck, label: 'Conformit\u00e9' },
  { to: '/actions',    icon: ListChecks,  label: "Plan d'action" },
];

const NAV_ANALYSE = [
  { to: '/patrimoine',      icon: Building2,    label: 'Patrimoine' },
  { to: '/consommations',   icon: Zap,          label: 'Consommation' },
  { to: '/diagnostic-conso', icon: BarChart3,   label: 'Anomalies' },
  { to: '/bill-intel',      icon: Receipt,      label: 'Factures & \u00e9carts' },
  { to: '/achat-energie',   icon: ShoppingCart, label: 'Achat \u00c9nergie' },
  { to: '/monitoring',      icon: Activity,     label: 'Performance & suivi' },
];

const NAV_ADMIN = [
  { to: '/import',       icon: Import,     label: 'Importer des fichiers' },
  { to: '/connectors',   icon: Settings,   label: 'Connecter des sources' },
  { to: '/segmentation', icon: Users,      label: 'Segmentation' },
  { to: '/watchers',     icon: HelpCircle, label: 'Veille r\u00e9glementaire' },
  { to: '/kb',           icon: BookOpen,   label: 'R\u00e8gles & r\u00e9f\u00e9rentiels' },
];

const SECTIONS = [
  { label: 'Cockpit',        items: NAV_COCKPIT },
  { label: 'Ex\u00e9cution',   items: NAV_EXECUTION },
  { label: 'Analyse',        items: NAV_ANALYSE },
  { label: 'Administration', items: NAV_ADMIN },
];

function SidebarLink({ to, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition
        ${isActive
          ? 'bg-blue-50 text-blue-700'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        }`
      }
    >
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  );
}

function SectionLabel({ label }) {
  return (
    <div className="pt-4 pb-1">
      <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
    </div>
  );
}

export default function Sidebar() {
  return (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-100">
        <h1 className="text-xl font-bold text-blue-600 tracking-tight">PROMEOS</h1>
        <p className="text-xs text-gray-400 mt-0.5">Cockpit \u00c9nerg\u00e9tique</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        {SECTIONS.map((section, idx) => (
          <div key={section.label}>
            {idx > 0 && <SectionLabel label={section.label} />}
            {section.items.map((item) => (
              <SidebarLink key={item.to} {...item} />
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400">
        v3.2.1 &middot; 654 tests
      </div>
    </aside>
  );
}
