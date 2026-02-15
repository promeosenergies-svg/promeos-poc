/**
 * PROMEOS — Sidebar Navigation v3.5 (Phase 6 - Nav Redesign)
 * Collapsible sections, expert mode progressive disclosure, tinted badges.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight, ChevronDown } from 'lucide-react';
import { NAV_SECTIONS, ROUTE_MODULE_MAP } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Tooltip } from '../ui';

const COLLAPSE_KEY = 'promeos_sidebar_collapsed';
const SECTIONS_KEY = 'promeos_sidebar_sections';

/* ── Persisted section open/close state ── */
function loadSectionState() {
  try {
    return JSON.parse(localStorage.getItem(SECTIONS_KEY) || '{}');
  } catch {
    return {};
  }
}
function saveSectionState(state) {
  localStorage.setItem(SECTIONS_KEY, JSON.stringify(state));
}

/* ── Sidebar Link ── */
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
        <span className="ml-auto px-1.5 py-0.5 text-[10px] font-bold bg-blue-100 text-blue-700 rounded-full min-w-[18px] text-center">
          {badge > 99 ? '99+' : badge}
        </span>
      )}
      {collapsed && badge > 0 && (
        <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
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

/* ── Collapsible Section ── */
function CollapsibleSection({ label, isOpen, onToggle, collapsed: sidebarCollapsed, children }) {
  if (sidebarCollapsed) {
    return (
      <div className="pt-3 pb-1 border-t border-gray-100 mt-2">
        {children}
      </div>
    );
  }

  return (
    <div className="mt-1">
      <button
        onClick={onToggle}
        className="flex items-center w-full px-3 py-1.5 group"
        aria-expanded={isOpen}
        aria-label={`Section ${label}`}
      >
        <ChevronDown
          size={12}
          className={`text-gray-400 transition-transform duration-150 mr-1.5 ${isOpen ? '' : '-rotate-90'}`}
        />
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider group-hover:text-gray-600 transition-colors">
          {label}
        </span>
      </button>
      {isOpen && <div className="space-y-0.5">{children}</div>}
    </div>
  );
}

/* ── Static Section (non-collapsible) ── */
function StaticSection({ label, isFirst, collapsed: sidebarCollapsed, children }) {
  if (sidebarCollapsed) {
    if (isFirst) return <div>{children}</div>;
    return (
      <div className="pt-3 pb-1 border-t border-gray-100 mt-2">
        {children}
      </div>
    );
  }

  return (
    <div>
      {!isFirst && (
        <div className="pt-4 pb-1">
          <p className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
        </div>
      )}
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

/* ── Main Sidebar ── */
export default function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
  const [sectionState, setSectionState] = useState(loadSectionState);
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);
  const { isAuthenticated, hasPermission } = useAuth();
  const { isExpert } = useExpertMode();

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

  const toggleSection = useCallback((label) => {
    setSectionState((prev) => {
      const next = { ...prev, [label]: !prev[label] };
      saveSectionState(next);
      return next;
    });
  }, []);

  const badges = { alerts: alertBadge, monitoring: monitoringBadge };

  /* Permission filter */
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

  /* Sections filtered by expert mode + permissions */
  const visibleSections = useMemo(() => {
    return NAV_SECTIONS
      .filter((section) => !section.expertOnly || isExpert)
      .map((section) => {
        const items = filterItems(
          section.items.filter((item) => !item.expertOnly || isExpert)
        );
        return { ...section, items };
      })
      .filter((section) => section.items.length > 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isExpert, isAuthenticated]);

  /* Auto-open section containing the active route */
  useEffect(() => {
    const currentPath = location.pathname;
    for (const section of visibleSections) {
      if (!section.collapsible) continue;
      const hasActive = section.items.some((item) => currentPath === item.to || currentPath.startsWith(item.to + '/'));
      if (hasActive && sectionState[section.label] === undefined) {
        setSectionState((prev) => {
          if (prev[section.label] !== undefined) return prev;
          const next = { ...prev, [section.label]: true };
          saveSectionState(next);
          return next;
        });
      }
    }
  }, [location.pathname, visibleSections]); // eslint-disable-line react-hooks/exhaustive-deps

  /* Resolve open state for a section */
  const isSectionOpen = (section) => {
    if (sectionState[section.label] !== undefined) return sectionState[section.label];
    return !section.defaultCollapsed;
  };

  return (
    <aside
      className={`bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0 transition-all duration-200
        ${collapsed ? 'w-16' : 'w-60'}`}
      aria-label="Navigation principale"
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
          aria-label={collapsed ? 'Deployer la barre laterale' : 'Reduire la barre laterale'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className={`flex-1 py-2 overflow-y-auto ${collapsed ? 'px-1.5' : 'px-3'}`} aria-label="Menu principal">
        {visibleSections.map((section, idx) => {
          const sectionContent = section.items.map((item) => (
            <SidebarLink
              key={item.to}
              {...item}
              badge={item.badgeKey ? badges[item.badgeKey] : 0}
              collapsed={collapsed}
            />
          ));

          if (section.collapsible && !collapsed) {
            return (
              <CollapsibleSection
                key={section.label}
                label={section.label}
                isOpen={isSectionOpen(section)}
                onToggle={() => toggleSection(section.label)}
                collapsed={collapsed}
              >
                {sectionContent}
              </CollapsibleSection>
            );
          }

          return (
            <StaticSection
              key={section.label}
              label={section.label}
              isFirst={idx === 0}
              collapsed={collapsed}
            >
              {sectionContent}
            </StaticSection>
          );
        })}
      </nav>

      {/* Footer */}
      <div className={`py-3 border-t border-gray-100 text-xs text-gray-400 ${collapsed ? 'px-2 text-center' : 'px-5'}`}>
        {collapsed
          ? (isExpert ? 'E' : 'v3.5')
          : (
            <span className="flex items-center gap-2">
              v3.5
              {isExpert && (
                <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-50 text-indigo-600 rounded">Expert</span>
              )}
            </span>
          )
        }
      </div>
    </aside>
  );
}
