/**
 * PROMEOS — Sidebar Navigation (World-Class)
 * Linear-density, collapsible sections, progressive disclosure,
 * pins (favorites), severity-aware badges, left-border active.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight, ChevronDown, Star, ExternalLink } from 'lucide-react';
import { NAV_SECTIONS, ROUTE_MODULE_MAP } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { Tooltip } from '../ui';

const COLLAPSE_KEY = 'promeos_sidebar_collapsed';
const SECTIONS_KEY = 'promeos_sidebar_sections';
const PINS_KEY = 'promeos_sidebar_pins';
const MAX_PINS = 5;

/* ── Badge severity styles ── */
const BADGE_STYLES = {
  alerts: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  monitoring: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  _default: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

/* ── Persisted state helpers ── */
function loadJSON(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
}
function saveJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

/* ── Sidebar Link ── */
function SidebarLink({ to, icon: Icon, label, badge, badgeKey, collapsed, pinned, onTogglePin, showPinButton }) {
  const badgeStyle = badgeKey ? (BADGE_STYLES[badgeKey] || BADGE_STYLES._default) : BADGE_STYLES._default;

  const link = (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `group/link flex items-center gap-2.5 h-9 rounded-md text-sm transition-colors relative
        ${isActive
          ? 'bg-blue-50/60 text-slate-900 font-medium border-l-2 border-blue-600 pl-2.5 pr-3'
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-normal pl-3 pr-3'
        }
        ${collapsed ? 'justify-center !px-2 !h-9' : ''}
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={18} className={`shrink-0 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
          {!collapsed && <span className="flex-1 truncate">{label}</span>}
          {!collapsed && badge > 0 && (
            <span className={`ml-auto px-1.5 py-0.5 text-[10px] font-semibold rounded-full min-w-[18px] text-center ${badgeStyle}`}>
              {badge > 99 ? '99+' : badge}
            </span>
          )}
          {!collapsed && showPinButton && !badge && (
            <button
              type="button"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTogglePin(to); }}
              className={`ml-auto p-0.5 rounded transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                pinned
                  ? 'text-amber-500 opacity-100'
                  : 'text-slate-300 opacity-0 group-hover/link:opacity-100 hover:text-amber-400'
              }`}
              aria-label={pinned ? `Desepingler ${label}` : `Epingler ${label}`}
            >
              <Star size={12} fill={pinned ? 'currentColor' : 'none'} />
            </button>
          )}
          {collapsed && badge > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-red-500 rounded-full" />
          )}
        </>
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
function CollapsibleSection({ label, isOpen, onToggle, children }) {
  return (
    <div className="mt-3">
      <button
        onClick={onToggle}
        className="flex items-center w-full px-3 py-0.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        aria-expanded={isOpen}
        aria-label={`Section ${label}`}
      >
        <ChevronDown
          size={11}
          className={`text-slate-400 transition-transform duration-150 mr-1.5 ${isOpen ? '' : '-rotate-90'}`}
        />
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider group-hover:text-slate-600 transition-colors">
          {label}
        </span>
      </button>
      {isOpen && <div className="mt-0.5">{children}</div>}
    </div>
  );
}

/* ── Static Section (non-collapsible) ── */
function StaticSection({ label, isFirst, collapsed, children }) {
  if (collapsed) {
    if (isFirst) return <div>{children}</div>;
    return (
      <div className="pt-2 mt-2 border-t border-slate-100">
        {children}
      </div>
    );
  }

  return (
    <div>
      {!isFirst && (
        <div className="pt-3 pb-0.5">
          <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">{label}</p>
        </div>
      )}
      <div>{children}</div>
    </div>
  );
}

/* ── Pinned Section ── */
function PinnedSection({ pins, allItems, badges, collapsed, onTogglePin }) {
  if (pins.length === 0) return null;
  const pinnedItems = pins
    .map((path) => allItems.find((item) => item.to === path))
    .filter(Boolean);
  if (pinnedItems.length === 0) return null;

  if (collapsed) {
    return (
      <div className="pb-2 mb-1 border-b border-slate-100">
        {pinnedItems.map((item) => (
          <SidebarLink key={item.to} {...item} badge={item.badgeKey ? badges[item.badgeKey] : 0} collapsed pinned onTogglePin={onTogglePin} showPinButton={false} />
        ))}
      </div>
    );
  }

  return (
    <div className="pb-2 mb-1 border-b border-slate-100">
      <p className="px-3 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
        <Star size={9} className="text-amber-400" fill="currentColor" /> Epingles
      </p>
      {pinnedItems.map((item) => (
        <SidebarLink key={item.to} {...item} badge={item.badgeKey ? badges[item.badgeKey] : 0} collapsed={false} pinned onTogglePin={onTogglePin} showPinButton />
      ))}
    </div>
  );
}

/* ── Main Sidebar ── */
export default function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === 'true');
  const [sectionState, setSectionState] = useState(() => loadJSON(SECTIONS_KEY, {}));
  const [pins, setPins] = useState(() => loadJSON(PINS_KEY, []));
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
      saveJSON(SECTIONS_KEY, next);
      return next;
    });
  }, []);

  const togglePin = useCallback((path) => {
    setPins((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : prev.length < MAX_PINS ? [...prev, path] : prev;
      saveJSON(PINS_KEY, next);
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

  /* Flat items for pin lookup */
  const allItems = useMemo(() => visibleSections.flatMap((s) => s.items), [visibleSections]);

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
          saveJSON(SECTIONS_KEY, next);
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
      className={`bg-white border-r border-slate-200/70 flex flex-col h-screen sticky top-0 transition-all duration-200
        ${collapsed ? 'w-16' : 'w-60'}`}
      aria-label="Navigation principale"
    >
      {/* Logo */}
      <div className={`border-b border-slate-100 flex items-center ${collapsed ? 'px-2 py-4 justify-center' : 'px-4 py-4 justify-between'}`}>
        {!collapsed && (
          <div>
            <h1 className="text-lg font-bold text-blue-600 tracking-tight">PROMEOS</h1>
            <p className="text-[10px] text-slate-400 mt-0.5">Cockpit energetique</p>
          </div>
        )}
        {collapsed && (
          <span className="text-lg font-bold text-blue-600">P</span>
        )}
        <button
          onClick={toggleCollapse}
          className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label={collapsed ? 'Deployer la barre laterale' : 'Reduire la barre laterale'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className={`flex-1 py-2 overflow-y-auto ${collapsed ? 'px-1.5' : 'px-2'}`} aria-label="Menu principal">
        {/* Pinned items */}
        <PinnedSection pins={pins} allItems={allItems} badges={badges} collapsed={collapsed} onTogglePin={togglePin} />

        {visibleSections.map((section, idx) => {
          const sectionContent = section.items.map((item) => (
            <SidebarLink
              key={item.to}
              {...item}
              badge={item.badgeKey ? badges[item.badgeKey] : 0}
              collapsed={collapsed}
              pinned={pins.includes(item.to)}
              onTogglePin={togglePin}
              showPinButton={!collapsed}
            />
          ));

          if (section.collapsible && !collapsed) {
            return (
              <CollapsibleSection
                key={section.label}
                label={section.label}
                isOpen={isSectionOpen(section)}
                onToggle={() => toggleSection(section.label)}
              >
                {sectionContent}
              </CollapsibleSection>
            );
          }

          if (collapsed) {
            if (idx === 0) return <div key={section.label}>{sectionContent}</div>;
            return (
              <div key={section.label} className="pt-2 mt-2 border-t border-slate-100">
                {sectionContent}
              </div>
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
      <div className={`py-3 border-t border-slate-100 text-xs text-slate-400 ${collapsed ? 'px-2 text-center' : 'px-4'}`}>
        {collapsed
          ? (isExpert ? 'E' : 'v4')
          : (
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                v4
                {isExpert && (
                  <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-50 text-indigo-600 rounded">Expert</span>
                )}
              </span>
              <a
                href="https://docs.promeos.fr"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-slate-400 hover:text-blue-600 transition-colors"
                aria-label="Documentation"
              >
                <ExternalLink size={11} />
                <span className="text-[10px]">Docs</span>
              </a>
            </div>
          )
        }
      </div>
    </aside>
  );
}
