/**
 * PROMEOS — NavPanel (Contextual Module Panel — Premium Life)
 * Glass surface. Module-tinted header from TINT_PALETTE.
 * Quick actions, recents, pins, sections with premium hover/active.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, Star, Clock } from 'lucide-react';
import {
  NAV_MODULES,
  ROUTE_MODULE_MAP,
  ALL_NAV_ITEMS,
  QUICK_ACTIONS,
  SECTION_TINTS,
  TINT_PALETTE,
  NAV_MAIN_SECTIONS,
  NAV_ADMIN_ITEMS,
  NAV_ADMIN_ICON,
  getSectionsForModule,
  matchRouteToModule,
} from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';
import { getRecents } from '../utils/navRecent';

/* ── Badge severity styles ── */
const BADGE_STYLES = {
  alerts: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  monitoring: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  _default: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

/* ── Panel Link (premium active/hover) ── */
function PanelLink({ to, icon: Icon, label, longLabel, badge, badgeKey, pinned, onTogglePin, tint, indent }) {
  const t = TINT_PALETTE[tint] || TINT_PALETTE.slate;
  const badgeStyle = badgeKey
    ? BADGE_STYLES[badgeKey] || BADGE_STYLES._default
    : BADGE_STYLES._default;
  const tipText = longLabel || label;

  return (
    <NavLink
      to={to}
      end={to === '/'}
      aria-label={tipText}
      className={({ isActive }) =>
        `group/link flex items-center gap-2 h-8 rounded-lg text-[13px] leading-5 transition-all duration-150 relative py-1 px-2.5${indent ? ' ml-4' : ''}
        ${
          isActive
            ? `${t.activeBg} text-slate-900 font-medium border-l-2 ${t.activeBorder} pl-2`
            : `text-slate-600 hover:${t.hoverBg.replace('bg-', 'bg-')} hover:text-slate-900 font-normal`
        }
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1`
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={14}
            className={`shrink-0 transition-colors duration-150 ${isActive ? t.icon : 'text-slate-400'}`}
          />
          <span className="flex-1 truncate">{label}</span>
          {badge > 0 && (
            <span
              className={`ml-auto px-1 py-px text-[9px] font-semibold rounded-full min-w-[16px] text-center ${badgeStyle}`}
            >
              {badge > 99 ? '99+' : badge}
            </span>
          )}
          {!badge && onTogglePin && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onTogglePin(to);
              }}
              className={`ml-auto p-0.5 rounded transition-opacity focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                pinned
                  ? 'text-amber-500 opacity-100'
                  : 'text-slate-300 opacity-0 group-hover/link:opacity-100 hover:text-amber-400'
              }`}
              aria-label={pinned ? `Désépingler ${label}` : `Épingler ${label}`}
            >
              <Star size={10} fill={pinned ? 'currentColor' : 'none'} />
            </button>
          )}
        </>
      )}
    </NavLink>
  );
}

/* ── Section Header (premium — icon + chevron + label) ── */
function SectionHeader({ label, icon: SectionIcon, isOpen, onToggle, tintColor }) {
  const t = tintColor ? TINT_PALETTE[tintColor] || TINT_PALETTE.slate : null;
  return (
    <button
      onClick={onToggle}
      className="flex items-center w-full px-2.5 py-1.5 group mt-3 first:mt-0
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md
        hover:bg-slate-50/60 transition-colors duration-150"
      aria-expanded={isOpen}
    >
      <ChevronDown
        size={11}
        className={`text-slate-400 transition-transform duration-150 mr-1.5 ${isOpen ? '' : '-rotate-90'}`}
      />
      {SectionIcon && (
        <SectionIcon size={12} className={`mr-1 shrink-0 ${t ? t.icon : 'text-slate-400'}`} />
      )}
      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider group-hover:text-slate-700 transition-colors duration-150 line-clamp-2">
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
  const t = TINT_PALETTE[tint] || TINT_PALETTE.slate;

  /* ── Permission filter ── */
  const filterItems = useCallback(
    (items) => {
      if (!isAuthenticated) return items;
      return items.filter((item) => {
        if (item.requireAdmin) return hasPermission('admin');
        const module = ROUTE_MODULE_MAP[item.to];
        if (module === undefined) return true;
        return hasPermission('view', module) || hasPermission('admin');
      });
    },
    [isAuthenticated, hasPermission]
  );

  /* ── Visible sections for this module (legacy — used by pins/recents) ── */
  const moduleSections = useMemo(() => {
    return getSectionsForModule(activeModule)
      .filter((s) => !s.expertOnly || isExpert)
      .map((s) => ({
        ...s,
        items: filterItems(
          s.items.filter((item) => (!item.expertOnly || isExpert) && !item.hidden)
        ),
      }))
      .filter((s) => s.items.length > 0);
  }, [activeModule, isExpert, filterItems]);

  /* ── B.2: 5 main sections (all visible, collapsible) ── */
  const mainSections = useMemo(() => {
    return NAV_MAIN_SECTIONS.map((s) => ({
      ...s,
      items: filterItems(
        s.items.filter((item) => (!item.expertOnly || isExpert) && !item.hidden)
      ),
    })).filter((s) => s.items.length > 0);
  }, [isExpert, filterItems]);

  /* ── Admin items (secondary menu) ── */
  const adminItems = useMemo(() => {
    return filterItems(NAV_ADMIN_ITEMS);
  }, [filterItems]);

  /* ── All visible items in this module ── */
  const allModuleItems = useMemo(() => mainSections.flatMap((s) => s.items), [mainSections]);

  /* ── Pinned items (only from this module's items) ── */
  const pinnedItems = useMemo(() => {
    return pins.map((path) => allModuleItems.find((item) => item.to === path)).filter(Boolean);
  }, [pins, allModuleItems]);

  /* ── Recents (filtered by current module only — no cross-module pollution) ── */
  const recentItems = useMemo(() => {
    const recents = getRecents();
    const visiblePaths = new Set(allModuleItems.map((i) => i.to));
    const seen = new Set();
    return recents
      .filter((r) => {
        if (pins.includes(r.path) || visiblePaths.has(r.path) || seen.has(r.path)) return false;
        seen.add(r.path);
        const recentModule = r.module || matchRouteToModule(r.path).moduleId;
        return recentModule === activeModule;
      })
      .map((r) => {
        const navItem = ALL_NAV_ITEMS.find((item) => item.to === r.path);
        if (navItem) return { ...navItem };
        const { moduleId } = matchRouteToModule(r.path);
        const m = NAV_MODULES.find((mod) => mod.key === moduleId);
        return {
          to: r.path,
          label: r.label || r.path,
          icon: m?.icon || NAV_MODULES[0].icon,
          module: moduleId,
        };
      })
      .filter(Boolean)
      .slice(0, 3);
  }, [allModuleItems, pins, activeModule, location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Section toggle ── */
  const toggleSection = useCallback((key) => {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  /* ── Auto-open section containing active route ── */
  useEffect(() => {
    const currentPath = location.pathname;
    for (const section of mainSections) {
      const hasActive = section.items.some(
        (item) => currentPath === item.to || currentPath.startsWith(item.to + '/')
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
      className="flex flex-col h-screen bg-white/80 backdrop-blur-sm border-r border-slate-200/60 shrink-0"
      style={{ width: 'clamp(248px, 18vw, 300px)' }}
      role="navigation"
      aria-label={`Module ${mod.label}`}
    >
      {/* Module header — tinted gradient */}
      <div
        className={`px-4 pt-4 pb-3 border-b border-slate-200/50 bg-gradient-to-b ${t.panelHeader}`}
      >
        <div className="flex items-center gap-2">
          <mod.icon size={16} className={t.icon} />
          <h2 className="text-sm font-semibold text-slate-800">{mod.label}</h2>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{mod.desc}</p>
      </div>

      {/* Quick actions — Raccourcis */}
      {moduleQuickActions.length > 0 && (
        <div className="px-3 py-2 border-b border-slate-200/40">
          <p className="px-0.5 pb-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Raccourcis
          </p>
          <div className="flex flex-wrap gap-1">
            {moduleQuickActions.map((action) => (
              <NavLink
                key={action.key}
                to={action.to}
                aria-label={action.longLabel || action.label}
                className={({ isActive }) =>
                  `flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium
                  transition-all duration-150
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1
                  ${isActive
                    ? `${t.pillBg} ${t.pillText} ring-1 ${t.pillRing}`
                    : `text-slate-500 hover:text-slate-700 ${t.softBg} hover:ring-1 ${t.pillRing}`
                  }`
                }
              >
                <action.icon size={11} className={`${t.icon} shrink-0`} />
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
          <div className="pb-2 mb-1 border-b border-slate-200/40">
            <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Star size={8} className="text-amber-400" fill="currentColor" /> Epingles
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

        {/* Recents (same module only) */}
        {recentItems.length > 0 && (
          <div className="pb-2 mb-1 border-b border-slate-200/40">
            <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Clock size={8} className="text-slate-400" /> Récents
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

        {/* 5 Main sections (collapsible) */}
        {mainSections.map((section) => {
          const sectionTint = section.tint || tint;
          const isOpen = isSectionOpen(section);

          return (
            <div key={section.key}>
              <SectionHeader
                label={section.label}
                icon={section.icon}
                isOpen={isOpen}
                onToggle={() => toggleSection(section.key)}
                tintColor={sectionTint}
              />
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

      {/* Secondary menu — Administration (gear icon) */}
      {adminItems.length > 0 && (
        <div className="border-t border-slate-200/50 px-2 py-2">
          <SectionHeader
            label="Administration"
            icon={NAV_ADMIN_ICON}
            isOpen={!!openSections._admin}
            onToggle={() => toggleSection('_admin')}
            tintColor="slate"
          />
          {openSections._admin && (
            <div className="mt-0.5">
              {adminItems.map((item) => (
                <PanelLink
                  key={item.to}
                  {...item}
                  badge={0}
                  pinned={pins.includes(item.to)}
                  onTogglePin={onTogglePin}
                  tint="slate"
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
