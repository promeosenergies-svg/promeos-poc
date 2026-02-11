import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Settings, HelpCircle,
  BarChart3, Import, Users, Receipt,
} from 'lucide-react';

const NAV = [
  { to: '/',                icon: LayoutDashboard, label: 'Command Center' },
  { to: '/patrimoine',     icon: Building2,       label: 'Patrimoine' },
  { to: '/conformite',     icon: ShieldCheck,     label: 'Conformite' },
  { to: '/actions',        icon: ListChecks,      label: 'Actions' },
  { to: '/consommations',  icon: Zap,             label: 'Conso & Usages' },
  { to: '/diagnostic-conso', icon: BarChart3,     label: 'Diagnostic Conso' },
  { to: '/bill-intel',     icon: Receipt,         label: 'Bill Intelligence' },
  { to: '/monitoring',     icon: Activity,        label: 'Monitoring' },
];

const NAV_SECONDARY = [
  { to: '/cockpit-2min',  icon: FileText,   label: '2 Minutes' },
  { to: '/cockpit',       icon: FileText,   label: 'Cockpit Executif' },
  { to: '/segmentation',  icon: Users,      label: 'Segmentation' },
  { to: '/import',        icon: Import,     label: 'Import' },
  { to: '/connectors',    icon: Settings,   label: 'Connecteurs' },
  { to: '/watchers',      icon: HelpCircle, label: 'Veille Regl.' },
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

export default function Sidebar() {
  return (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-100">
        <h1 className="text-xl font-bold text-blue-600 tracking-tight">PROMEOS</h1>
        <p className="text-xs text-gray-400 mt-0.5">Cockpit Energetique</p>
      </div>

      {/* Main nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV.map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}

        <div className="pt-4 pb-2">
          <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">Outils</p>
        </div>
        {NAV_SECONDARY.map((item) => (
          <SidebarLink key={item.to} {...item} />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400">
        v1.0 &middot; 546 tests
      </div>
    </aside>
  );
}
