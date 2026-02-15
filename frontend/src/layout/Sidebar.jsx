/**
 * PROMEOS — Sidebar (Expandable Rail)
 * Single sidebar that morphs between rail (64px, icons) and expanded (240px, full nav).
 * Hover to expand, pin to lock. Favorites, recents, quick actions, expert filtering.
 */
import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, Star, Pin, PinOff, Clock } from 'lucide-react';
import { Tooltip } from '../ui';
import {
  NAV_SECTIONS, ROUTE_MODULE_MAP, ALL_NAV_ITEMS, QUICK_ACTIONS,
  SECTION_TINTS, SIDEBAR_ITEM_TINTS,
} from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';
import { getRecents, addRecent } from '../utils/navRecent';

const PINS_KEY = 'promeos_sidebar_pins';
const PINNED_KEY = 'promeos.sidebar.pinned';
const MAX_PINS = 5;

/* ── Badge severity styles ── */
const BADGE_STYLES = {
  alerts: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  monitoring: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  _default: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

function loadJSON(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
}
function saveJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

/* ── Sidebar Link ── */
function SidebarLink({ to, icon: Icon, label, badge, badgeKey, pinned, onTogglePin, expanded, tint, sectionLabel }) {
  const tintClasses = SIDEBAR_ITEM_TINTS[tint] || SIDEBAR_ITEM_TINTS.blue;
  const badgeStyle = badgeKey ? (BADGE_STYLES[badgeKey] || BADGE_STYLES._default) : BADGE_STYLES._default;

  if (!expanded) {
    return (
      <Tooltip text={`${label} — ${sectionLabel}`} position="right">
        <NavLink
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `relative flex items-center justify-center w-10 h-10 mx-auto rounded-lg transition-colors duration-150
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
            ${isActive
              ? `${tintClasses.activeBg} ${tintClasses.activeText}`
              : 'text-slate-400 hover:bg-slate-50 hover:text-slate-600'
            }`
          }
        >
          <Icon size={18} />
          {badge > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
          )}
        </NavLink>
      </Tooltip>
    );
  }

  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `group/link flex items-center gap-2.5 h-9 rounded-md text-sm transition-colors relative px-2.5
        ${isActive
          ? `${tintClasses.activeBg} text-slate-900 font-medium border-l-2 ${tintClasses.activeBorder} pl-2`
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-normal'
        }
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={16} className={`shrink-0 ${isActive ? tintClasses.activeText : 'text-slate-400'}`} />
          <span className="flex-1 truncate">{label}</span>
          {badge > 0 && (
            <span className={`ml-auto px-1.5 py-0.5 text-[10px] font-semibold rounded-full min-w-[18px] text-center ${badgeStyle}`}>
              {badge > 99 ? '99+' : badge}
            </span>
          )}
          {!badge && onTogglePin && (
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
              <Star size={11} fill={pinned ? 'currentColor' : 'none'} />
            </button>
          )}
        </>
      )}
    </NavLink>
  );
}

/* ── Section Header ── */
function SectionHeader({ label, isOpen, onToggle, tint }) {
  const dotClass = SIDEBAR_ITEM_TINTS[tint]?.dot || 'bg-slate-400';
  return (
    <button
      onClick={onToggle}
      className="flex items-center w-full px-2.5 py-1 group mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
      aria-expanded={isOpen}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass} mr-1.5 shrink-0`} />
      <ChevronDown
        size={11}
        className={`text-slate-400 transition-transform duration-150 mr-1 ${isOpen ? '' : '-rotate-90'}`}
      />
      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider group-hover:text-slate-600 transition-colors">
        {label}
      </span>
    </button>
  );
}

/* ── Quick Actions (expanded only) ── */
function QuickActions() {
  return (
    <div className="px-2.5 py-2 border-b border-slate-100">
      <div className="grid grid-cols-2 gap-1">
        {QUICK_ACTIONS.map((action) => (
          <NavLink
            key={action.key}
            to={action.to}
            className="flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] font-medium text-slate-500
              hover:bg-slate-50 hover:text-slate-700 transition-colors truncate"
          >
            <action.icon size={13} className="text-slate-400 shrink-0" />
            <span className="truncate">{action.label}</span>
          </NavLink>
        ))}
      </div>
    </div>
  );
}

/* ── Main Sidebar ── */
export default function Sidebar() {
  const location = useLocation();
  const { isExpert } = useExpertMode();
  const { isAuthenticated, hasPermission } = useAuth();

  /* ── State ── */
  const [pinned, setPinned] = useState(() => localStorage.getItem(PINNED_KEY) === 'true');
  const [hovered, setHovered] = useState(false);
  const [pins, setPins] = useState(() => loadJSON(PINS_KEY, []));
  const [openSections, setOpenSections] = useState({});
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);
  const [recents, setRecents] = useState(() => getRecents());

  const expanded = pinned || hovered;
  const hoverTimeoutRef = useRef(null);

  /* ── Hover handlers ── */
  const handleMouseEnter = useCallback(() => {
    clearTimeout(hoverTimeoutRef.current);
    setHovered(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    hoverTimeoutRef.current = setTimeout(() => setHovered(false), 150);
  }, []);

  useEffect(() => {
    return () => clearTimeout(hoverTimeoutRef.current);
  }, []);

  /* ── Pin toggle ── */
  const togglePinned = useCallback(() => {
    setPinned((prev) => {
      const next = !prev;
      localStorage.setItem(PINNED_KEY, String(next));
      return next;
    });
  }, []);

  /* ── Fetch badges ── */
  useEffect(() => {
    getNotificationsSummary()
      .then((s) => setAlertBadge(s.new_critical + s.new_warn))
      .catch(() => {});
    getMonitoringAlerts(null, 'open', 200)
      .then((alerts) => setMonitoringBadge(Array.isArray(alerts) ? alerts.length : 0))
      .catch(() => {});
  }, []);

  const badges = { alerts: alertBadge, monitoring: monitoringBadge };

  /* ── Track recents on route change ── */
  useEffect(() => {
    const path = location.pathname;
    const isNavItem = ALL_NAV_ITEMS.some((item) =>
      path === item.to || path.startsWith(item.to + '/')
    );
    if (isNavItem) {
      const updated = addRecent(path);
      setRecents(updated);
    }
  }, [location.pathname]);

  /* ── Pins ── */
  const togglePin = useCallback((path) => {
    setPins((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : prev.length < MAX_PINS ? [...prev, path] : prev;
      saveJSON(PINS_KEY, next);
      return next;
    });
  }, []);

  /* ── Section toggle ── */
  const toggleSection = useCallback((key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  /* ── Permission filter ── */
  const filterItems = useCallback((items) => {
    if (!isAuthenticated) return items;
    return items.filter((item) => {
      if (item.requireAdmin) return hasPermission('admin');
      const module = ROUTE_MODULE_MAP[item.to];
      if (module === undefined) return true;
      return hasPermission('view', module) || hasPermission('admin');
    });
  }, [isAuthenticated, hasPermission]);

  /* ── Filtered sections ── */
  const visibleSections = useMemo(() => {
    return NAV_SECTIONS
      .filter((s) => !s.expertOnly || isExpert)
      .map((s) => ({
        ...s,
        items: filterItems(s.items.filter((item) => !item.expertOnly || isExpert)),
      }))
      .filter((s) => s.items.length > 0);
  }, [isExpert, filterItems]);

  /* ── All visible items for pin/recent resolution ── */
  const allItems = useMemo(() => visibleSections.flatMap((s) => s.items), [visibleSections]);

  /* ── Pinned items ── */
  const pinnedItems = useMemo(() => {
    return pins.map((path) => allItems.find((item) => item.to === path)).filter(Boolean);
  }, [pins, allItems]);

  /* ── Recent items (resolved against nav items, exclude pins) ── */
  const recentItems = useMemo(() => {
    return recents
      .filter((path) => !pins.includes(path))
      .map((path) => ALL_NAV_ITEMS.find((item) => item.to === path))
      .filter(Boolean)
      .slice(0, 5);
  }, [recents, pins]);

  /* ── Auto-open section containing active route ── */
  useEffect(() => {
    const currentPath = location.pathname;
    for (const section of visibleSections) {
      const hasActive = section.items.some((item) =>
        currentPath === item.to || currentPath.startsWith(item.to + '/')
      );
      if (hasActive) {
        setOpenSections((prev) => ({ ...prev, [section.key]: true }));
      }
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const isSectionOpen = (section) => {
    if (openSections[section.key] !== undefined) return openSections[section.key];
    return true;
  };

  /* ── Find section tint for an item ── */
  const getTintForItem = useCallback((itemTo) => {
    for (const section of visibleSections) {
      if (section.items.some((i) => i.to === itemTo)) {
        return SECTION_TINTS[section.key] || 'blue';
      }
    }
    return 'blue';
  }, [visibleSections]);

  return (
    <aside
      className={`flex flex-col h-screen sticky top-0 bg-white border-r border-slate-200/70
        transition-all duration-200 ease-in-out shrink-0 overflow-hidden
        ${expanded ? 'w-60' : 'w-16'}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label="Navigation principale"
    >
      {/* Logo + Pin */}
      <div className="px-3 py-3 border-b border-slate-100 flex items-center gap-2 shrink-0">
        <span className="text-lg font-bold text-blue-600 shrink-0 w-10 flex items-center justify-center">P</span>
        {expanded && (
          <>
            <span className="text-sm font-semibold text-slate-700 flex-1 truncate">PROMEOS</span>
            <button
              onClick={togglePinned}
              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              aria-label={pinned ? 'Desepingler la sidebar' : 'Epingler la sidebar'}
            >
              {pinned ? <PinOff size={14} /> : <Pin size={14} />}
            </button>
          </>
        )}
      </div>

      {/* Quick Actions (expanded only) */}
      {expanded && <QuickActions />}

      {/* Scrollable nav */}
      <nav className="flex-1 overflow-y-auto py-2 px-1.5" aria-label="Navigation">
        {/* Pinned items */}
        {pinnedItems.length > 0 && (
          <div className="pb-2 mb-1 border-b border-slate-100">
            {expanded && (
              <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Star size={9} className="text-amber-400" fill="currentColor" /> Epingles
              </p>
            )}
            {pinnedItems.map((item) => (
              <SidebarLink
                key={`pin-${item.to}`}
                {...item}
                badge={item.badgeKey ? badges[item.badgeKey] : 0}
                pinned
                onTogglePin={togglePin}
                expanded={expanded}
                tint={getTintForItem(item.to)}
                sectionLabel="Epingles"
              />
            ))}
          </div>
        )}

        {/* Recents */}
        {recentItems.length > 0 && (
          <div className="pb-2 mb-1 border-b border-slate-100">
            {expanded && (
              <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Clock size={9} className="text-slate-400" /> Recents
              </p>
            )}
            {recentItems.map((item) => (
              <SidebarLink
                key={`recent-${item.to}`}
                {...item}
                badge={0}
                pinned={pins.includes(item.to)}
                onTogglePin={togglePin}
                expanded={expanded}
                tint={getTintForItem(item.to)}
                sectionLabel="Recents"
              />
            ))}
          </div>
        )}

        {/* Main sections */}
        {visibleSections.map((section) => {
          const tint = SECTION_TINTS[section.key] || 'blue';
          const isOpen = isSectionOpen(section);

          return (
            <div key={section.key}>
              {expanded ? (
                <SectionHeader
                  label={section.label}
                  isOpen={isOpen}
                  onToggle={() => toggleSection(section.key)}
                  tint={tint}
                />
              ) : (
                <div className="mx-3 my-1.5 border-t border-slate-100" />
              )}
              {(isOpen || !expanded) && (
                <div className={expanded ? 'mt-0.5' : ''}>
                  {section.items.map((item) => (
                    <SidebarLink
                      key={item.to}
                      {...item}
                      badge={item.badgeKey ? badges[item.badgeKey] : 0}
                      pinned={pins.includes(item.to)}
                      onTogglePin={togglePin}
                      expanded={expanded}
                      tint={tint}
                      sectionLabel={section.label}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      {expanded && (
        <div className="px-3 py-2 border-t border-slate-100 text-[10px] text-slate-400 shrink-0">
          {isExpert && (
            <span className="px-1.5 py-0.5 font-semibold bg-indigo-50 text-indigo-600 rounded">Expert</span>
          )}
        </div>
      )}
    </aside>
  );
}
