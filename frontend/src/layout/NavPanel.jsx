/**
 * PROMEOS — NavPanel
 * Contextual sub-navigation panel for the active module.
 * Shows sections, items, pins, badges, expert filtering.
 */
import { useCallback, useMemo, useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, Star, X } from 'lucide-react';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';
import { ROUTE_MODULE_MAP } from './NavRegistry';

const PINS_KEY = 'promeos_sidebar_pins';
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

/* ── Panel Link ── */
function PanelLink({ to, icon: Icon, label, badge, badgeKey, pinned, onTogglePin }) {
  const badgeStyle = badgeKey ? (BADGE_STYLES[badgeKey] || BADGE_STYLES._default) : BADGE_STYLES._default;

  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `group/link flex items-center gap-2.5 h-9 rounded-md text-sm transition-colors relative px-2.5
        ${isActive
          ? 'bg-blue-50/60 text-slate-900 font-medium border-l-2 border-blue-600 pl-2'
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-normal'
        }
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={16} className={`shrink-0 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
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
function SectionHeader({ label, isOpen, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className="flex items-center w-full px-2.5 py-1 group mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
      aria-expanded={isOpen}
    >
      <ChevronDown
        size={11}
        className={`text-slate-400 transition-transform duration-150 mr-1.5 ${isOpen ? '' : '-rotate-90'}`}
      />
      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider group-hover:text-slate-600 transition-colors">
        {label}
      </span>
    </button>
  );
}

export default function NavPanel({ sections, moduleLabel, badges, onClose }) {
  const location = useLocation();
  const { isExpert } = useExpertMode();
  const { isAuthenticated, hasPermission } = useAuth();
  const [pins, setPins] = useState(() => loadJSON(PINS_KEY, []));
  const [openSections, setOpenSections] = useState({});

  const togglePin = useCallback((path) => {
    setPins((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : prev.length < MAX_PINS ? [...prev, path] : prev;
      saveJSON(PINS_KEY, next);
      return next;
    });
  }, []);

  const toggleSection = useCallback((key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  /* Permission filter */
  const filterItems = useCallback((items) => {
    if (!isAuthenticated) return items;
    return items.filter((item) => {
      if (item.requireAdmin) return hasPermission('admin');
      const module = ROUTE_MODULE_MAP[item.to];
      if (module === undefined) return true;
      return hasPermission('view', module) || hasPermission('admin');
    });
  }, [isAuthenticated, hasPermission]);

  /* Filtered sections */
  const visibleSections = useMemo(() => {
    return sections
      .filter((s) => !s.expertOnly || isExpert)
      .map((s) => ({
        ...s,
        items: filterItems(s.items.filter((item) => !item.expertOnly || isExpert)),
      }))
      .filter((s) => s.items.length > 0);
  }, [sections, isExpert, filterItems]);

  /* All items for pin resolution */
  const allItems = useMemo(() => visibleSections.flatMap((s) => s.items), [visibleSections]);

  /* Pinned items in this module */
  const pinnedItems = useMemo(() => {
    return pins
      .map((path) => allItems.find((item) => item.to === path))
      .filter(Boolean);
  }, [pins, allItems]);

  /* Auto-open section containing active route */
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
    return true; // Default open in panel
  };

  return (
    <div
      id={`panel-${sections[0]?.module}`}
      role="tabpanel"
      className="w-52 bg-white border-r border-slate-200/70 flex flex-col h-screen shrink-0"
    >
      {/* Module header */}
      <div className="px-3 py-3 border-b border-slate-100 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-700">{moduleLabel}</h2>
        <button
          onClick={onClose}
          className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors lg:hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="Fermer le panneau"
        >
          <X size={14} />
        </button>
      </div>

      {/* Panel content */}
      <nav className="flex-1 overflow-y-auto py-2 px-1.5" aria-label={`Navigation ${moduleLabel}`}>
        {/* Pinned items */}
        {pinnedItems.length > 0 && (
          <div className="pb-2 mb-1 border-b border-slate-100">
            <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Star size={9} className="text-amber-400" fill="currentColor" /> Epingles
            </p>
            {pinnedItems.map((item) => (
              <PanelLink
                key={`pin-${item.to}`}
                {...item}
                badge={item.badgeKey ? badges[item.badgeKey] : 0}
                pinned
                onTogglePin={togglePin}
              />
            ))}
          </div>
        )}

        {/* Sections */}
        {visibleSections.map((section) => {
          const showHeader = visibleSections.length > 1;
          const isOpen = isSectionOpen(section);

          return (
            <div key={section.key}>
              {showHeader && (
                <SectionHeader
                  label={section.label}
                  isOpen={isOpen}
                  onToggle={() => toggleSection(section.key)}
                />
              )}
              {(isOpen || !showHeader) && (
                <div className="mt-0.5">
                  {section.items.map((item) => (
                    <PanelLink
                      key={item.to}
                      {...item}
                      badge={item.badgeKey ? badges[item.badgeKey] : 0}
                      pinned={pins.includes(item.to)}
                      onTogglePin={togglePin}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-2 border-t border-slate-100 text-[10px] text-slate-400">
        {isExpert && (
          <span className="px-1.5 py-0.5 font-semibold bg-indigo-50 text-indigo-600 rounded">Expert</span>
        )}
      </div>
    </div>
  );
}
