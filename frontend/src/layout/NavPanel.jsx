/**
 * PROMEOS — NavPanel (Contextual Module Panel)
 * Shows header (module title + desc), quick actions, recents, pins,
 * then the module's sections with items. Filtered by expert + permissions.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, Star, Clock } from 'lucide-react';
import {
  NAV_MODULES, NAV_SECTIONS, ROUTE_MODULE_MAP, ALL_NAV_ITEMS,
  QUICK_ACTIONS, SECTION_TINTS, SIDEBAR_ITEM_TINTS,
  getSectionsForModule,
} from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';
import { getRecents } from '../utils/navRecent';

/* ── Badge severity styles ── */
const BADGE_STYLES = {
  alerts:     'bg-red-50 text-red-700 ring-1 ring-red-200',
  monitoring: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  _default:   'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

/* ── Panel Link ── */
function PanelLink({ to, icon: Icon, label, badge, badgeKey, pinned, onTogglePin, tint }) {
  const tintClasses = SIDEBAR_ITEM_TINTS[tint] || SIDEBAR_ITEM_TINTS.blue;
  const badgeStyle = badgeKey ? (BADGE_STYLES[badgeKey] || BADGE_STYLES._default) : BADGE_STYLES._default;

  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `group/link flex items-center gap-2.5 h-9 rounded-md text-[13px] transition-colors relative px-2.5
        ${isActive
          ? `${tintClasses.activeBg} text-slate-900 font-medium border-l-2 ${tintClasses.activeBorder} pl-2`
          : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-normal'
        }
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1`
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={15} className={`shrink-0 ${isActive ? tintClasses.activeText : 'text-slate-400'}`} />
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
      className="flex items-center w-full px-2.5 py-1 group mt-3 first:mt-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
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

/* ── Main Panel ── */
export default function NavPanel({ activeModule, pins, onTogglePin, badges }) {
  const location = useLocation();
  const { isExpert } = useExpertMode();
  const { isAuthenticated, hasPermission } = useAuth();
  const [openSections, setOpenSections] = useState({});

  const mod = NAV_MODULES.find((m) => m.key === activeModule) || NAV_MODULES[0];
  const tint = mod.tint;

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

  /* ── Visible sections for this module ── */
  const moduleSections = useMemo(() => {
    return getSectionsForModule(activeModule)
      .filter((s) => !s.expertOnly || isExpert)
      .map((s) => ({
        ...s,
        items: filterItems(s.items.filter((item) => !item.expertOnly || isExpert)),
      }))
      .filter((s) => s.items.length > 0);
  }, [activeModule, isExpert, filterItems]);

  /* ── All visible items in this module ── */
  const allModuleItems = useMemo(
    () => moduleSections.flatMap((s) => s.items),
    [moduleSections],
  );

  /* ── Pinned items (only from this module's items) ── */
  const pinnedItems = useMemo(() => {
    return pins.map((path) => allModuleItems.find((item) => item.to === path)).filter(Boolean);
  }, [pins, allModuleItems]);

  /* ── Recents (only from this module, exclude pins) ── */
  const recentItems = useMemo(() => {
    const recents = getRecents();
    return recents
      .filter((path) => !pins.includes(path))
      .map((path) => allModuleItems.find((item) => item.to === path))
      .filter(Boolean)
      .slice(0, 3);
  }, [allModuleItems, pins, location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Section toggle ── */
  const toggleSection = useCallback((key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  /* ── Auto-open section containing active route ── */
  useEffect(() => {
    const currentPath = location.pathname;
    for (const section of moduleSections) {
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

  /* ── Quick actions relevant to this module ── */
  const moduleQuickActions = useMemo(() => {
    const moduleRoutes = new Set(allModuleItems.map((i) => i.to));
    return QUICK_ACTIONS.filter((a) => moduleRoutes.has(a.to));
  }, [allModuleItems]);

  return (
    <div
      className="flex flex-col w-52 h-screen bg-white border-r border-slate-200/70 shrink-0 overflow-hidden"
      role="navigation"
      aria-label={`Module ${mod.label}`}
    >
      {/* Module header */}
      <div className={`px-4 pt-4 pb-3 border-b border-slate-100 bg-gradient-to-b from-${mod.tint === 'slate' ? 'slate-50/60' : `${mod.tint}-50/30`} to-transparent`}>
        <div className="flex items-center gap-2">
          <mod.icon size={18} className={SIDEBAR_ITEM_TINTS[tint]?.activeText || 'text-slate-600'} />
          <h2 className="text-sm font-semibold text-slate-800">{mod.label}</h2>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{mod.desc}</p>
      </div>

      {/* Quick actions (if any for this module) */}
      {moduleQuickActions.length > 0 && (
        <div className="px-3 py-2 border-b border-slate-100">
          <div className="flex flex-wrap gap-1">
            {moduleQuickActions.map((action) => (
              <NavLink
                key={action.key}
                to={action.to}
                className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-slate-500
                  hover:bg-slate-50 hover:text-slate-700 transition-colors"
              >
                <action.icon size={12} className="text-slate-400 shrink-0" />
                <span className="truncate">{action.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      )}

      {/* Scrollable content */}
      <nav className="flex-1 overflow-y-auto py-2 px-2" aria-label={`Navigation ${mod.label}`}>
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
                onTogglePin={onTogglePin}
                tint={tint}
              />
            ))}
          </div>
        )}

        {/* Recents */}
        {recentItems.length > 0 && (
          <div className="pb-2 mb-1 border-b border-slate-100">
            <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Clock size={9} className="text-slate-400" /> Recents
            </p>
            {recentItems.map((item) => (
              <PanelLink
                key={`recent-${item.to}`}
                {...item}
                badge={0}
                pinned={pins.includes(item.to)}
                onTogglePin={onTogglePin}
                tint={tint}
              />
            ))}
          </div>
        )}

        {/* Module sections */}
        {moduleSections.map((section) => {
          const sectionTint = SECTION_TINTS[section.key] || tint;
          const isOpen = isSectionOpen(section);

          return (
            <div key={section.key}>
              {moduleSections.length > 1 && (
                <SectionHeader
                  label={section.label}
                  isOpen={isOpen}
                  onToggle={() => toggleSection(section.key)}
                  tint={sectionTint}
                />
              )}
              {isOpen && (
                <div className="mt-0.5">
                  {section.items.map((item) => (
                    <PanelLink
                      key={item.to}
                      {...item}
                      badge={item.badgeKey ? badges[item.badgeKey] : 0}
                      pinned={pins.includes(item.to)}
                      onTogglePin={onTogglePin}
                      tint={sectionTint}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </div>
  );
}
