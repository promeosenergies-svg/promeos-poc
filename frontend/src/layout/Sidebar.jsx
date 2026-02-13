/**
 * PROMEOS — Sidebar Navigation
 * Imports nav structure from NavRegistry. Supports collapse/expand (localStorage).
 */
import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { NAV_SECTIONS, ROUTE_MODULE_MAP } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Tooltip } from '../ui';

const COLLAPSE_KEY = 'promeos_sidebar_collapsed';

function SidebarLink({ to, icon: Icon, label, badge, collapsed }) {
  const link = (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
        ${isActive
          ? 'bg-blue-50 text-blue-700'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        }
        ${collapsed ? 'justify-center' : ''}`
      }
    >
      <Icon size={18} className="shrink-0" />
      {!collapsed && <span className="flex-1 truncate">{label}</span>}
      {!collapsed && badge > 0 && (
        <span className="ml-auto px-1.5 py-0.5 text-[10px] font-bold bg-red-500 text-white rounded-full min-w-[18px] text-center">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
      {collapsed && badge > 0 && (
        <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
      )}
    </NavLink>
  );

  if (collapsed) {
    return (
      <Tooltip text={label} position="right">
        <span className="relative block w-full">{link}</span>
      </Tooltip>
    );
  }

  return link;
}

function SectionLabel({ label, collapsed }) {
  if (collapsed) return <div className="pt-3 pb-1 border-t border-gray-100 mt-2" />;
  return (
    <div className="pt-4 pb-1">
      <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
    </div>
  );
}

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
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

  const toggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSE_KEY, String(next));
      return next;
    });
  };

  const badges = { alerts: alertBadge, monitoring: monitoringBadge };

  const filterItems = (items) => {
    if (!isAuthenticated) return items;
    return items.filter((item) => {
      if (item.requireAdmin) return hasPermission('admin');
      const module = ROUTE_MODULE_MAP[item.to];
      if (module === undefined) return true;
      if (module === null) return hasPermission('admin');
      return hasPermission('view', module);
    });
  };

  return (
    <aside
      className={`bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0 transition-all duration-200
        ${collapsed ? 'w-16' : 'w-60'}`}
    >
      {/* Logo */}
      <div className={`border-b border-gray-100 flex items-center ${collapsed ? 'px-2 py-5 justify-center' : 'px-5 py-5 justify-between'}`}>
        {!collapsed && (
          <div>
            <h1 className="text-xl font-bold text-blue-600 tracking-tight">PROMEOS</h1>
            <p className="text-xs text-gray-400 mt-0.5">Cockpit energetique</p>
          </div>
        )}
        {collapsed && (
          <span className="text-xl font-bold text-blue-600">P</span>
        )}
        <button
          onClick={toggleCollapse}
          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className={`flex-1 py-2 space-y-0.5 overflow-y-auto ${collapsed ? 'px-1.5' : 'px-3'}`}>
        {NAV_SECTIONS.map((section, idx) => {
          const visibleItems = filterItems(section.items);
          if (visibleItems.length === 0) return null;
          return (
            <div key={section.label}>
              {idx > 0 && <SectionLabel label={section.label} collapsed={collapsed} />}
              {visibleItems.map((item) => (
                <SidebarLink
                  key={item.to}
                  {...item}
                  badge={item.badgeKey ? badges[item.badgeKey] : 0}
                  collapsed={collapsed}
                />
              ))}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className={`py-3 border-t border-gray-100 text-xs text-gray-400 ${collapsed ? 'px-2 text-center' : 'px-5'}`}>
        {collapsed ? 'v3.4' : 'v3.4 \u00b7 880 tests'}
      </div>
    </aside>
  );
}
