import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Building2, ShieldCheck, FileText,
  Zap, ListChecks, Activity, Settings, HelpCircle,
  BarChart3, Import, Users, Receipt, BookOpen, ShoppingCart,
  Search, Link2, Eye, Bell, Lock,
} from 'lucide-react';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

// Map nav routes to permission modules for view filtering
const ROUTE_MODULE_MAP = {
  '/': 'cockpit',
  '/cockpit': 'cockpit',
  '/notifications': 'cockpit',
  '/conformite': 'conformite',
  '/actions': 'actions',
  '/patrimoine': 'patrimoine',
  '/consommations': 'consommations',
  '/diagnostic-conso': 'diagnostic',
  '/bill-intel': 'billing',
  '/achat-energie': 'purchase',
  '/monitoring': 'monitoring',
  '/import': null,         // admin-only items
  '/connectors': null,
  '/segmentation': null,
  '/watchers': null,
  '/kb': null,
  '/admin/users': null,
};

const NAV_PILOTAGE = [
  { to: '/',              icon: LayoutDashboard, label: 'Tableau de bord' },
  { to: '/cockpit',       icon: FileText,        label: 'Vue exécutive' },
  { to: '/notifications', icon: Bell,            label: 'Alertes', badgeKey: 'alerts' },
];

const NAV_EXECUTION = [
  { to: '/conformite', icon: ShieldCheck, label: 'Conformité' },
  { to: '/actions',    icon: ListChecks,  label: "Plan d'actions" },
];

const NAV_ANALYSE = [
  { to: '/patrimoine',       icon: Building2,    label: 'Patrimoine' },
  { to: '/consommations',    icon: Zap,          label: 'Consommations' },
  { to: '/diagnostic-conso', icon: Search,       label: 'Diagnostic' },
  { to: '/bill-intel',       icon: Receipt,      label: 'Facturation' },
  { to: '/achat-energie',    icon: ShoppingCart,  label: 'Achats énergie' },
  { to: '/monitoring',       icon: Activity,     label: 'Performance', badgeKey: 'monitoring' },
];

const NAV_ADMIN = [
  { to: '/import',       icon: Import,     label: 'Imports' },
  { to: '/connectors',   icon: Link2,      label: 'Connexions' },
  { to: '/segmentation', icon: Users,      label: 'Segmentation' },
  { to: '/watchers',     icon: Eye,        label: 'Veille' },
  { to: '/kb',           icon: BookOpen,   label: 'Référentiels' },
];

const NAV_IAM = [
  { to: '/admin/users',       icon: Lock,       label: 'Utilisateurs', requireAdmin: true },
  { to: '/admin/roles',       icon: ShieldCheck, label: 'Roles',       requireAdmin: true },
  { to: '/admin/assignments', icon: Users,      label: 'Assignments',  requireAdmin: true },
  { to: '/admin/audit',       icon: FileText,   label: 'Audit Log',    requireAdmin: true },
];

const SECTIONS = [
  { label: 'Pilotage',       items: NAV_PILOTAGE },
  { label: 'Exécution',      items: NAV_EXECUTION },
  { label: 'Analyse',        items: NAV_ANALYSE },
  { label: 'Administration', items: NAV_ADMIN },
  { label: 'IAM',            items: NAV_IAM },
];

function SidebarLink({ to, icon: Icon, label, badge }) {
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
      <span className="flex-1">{label}</span>
      {badge > 0 && (
        <span className="ml-auto px-1.5 py-0.5 text-[10px] font-bold bg-red-500 text-white rounded-full min-w-[18px] text-center">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
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
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);
  const { isAuthenticated, hasPermission } = useAuth();

  useEffect(() => {
    getNotificationsSummary()
      .then((s) => setAlertBadge(s.new_critical + s.new_warn))
      .catch(() => {});
    getMonitoringAlerts(null, 'open', 200)
      .then((alerts) => setMonitoringBadge(Array.isArray(alerts) ? alerts.length : 0))
      .catch(() => {});
  }, []);

  const badges = { alerts: alertBadge, monitoring: monitoringBadge };

  // Filter items based on user permissions
  const filterItems = (items) => {
    if (!isAuthenticated) return items; // demo mode: show all
    return items.filter((item) => {
      if (item.requireAdmin) return hasPermission('admin');
      const module = ROUTE_MODULE_MAP[item.to];
      if (module === undefined) return true; // route not in map → show
      if (module === null) return hasPermission('admin'); // admin-only
      return hasPermission('view', module);
    });
  };

  return (
    <aside className="w-60 bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-100">
        <h1 className="text-xl font-bold text-blue-600 tracking-tight">PROMEOS</h1>
        <p className="text-xs text-gray-400 mt-0.5">Cockpit énergétique</p>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        {SECTIONS.map((section, idx) => {
          const visibleItems = filterItems(section.items);
          if (visibleItems.length === 0) return null;
          return (
            <div key={section.label}>
              {idx > 0 && <SectionLabel label={section.label} />}
              {visibleItems.map((item) => (
                <SidebarLink key={item.to} {...item} badge={item.badgeKey ? badges[item.badgeKey] : 0} />
              ))}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400">
        v3.4 &middot; 709 tests
      </div>
    </aside>
  );
}
