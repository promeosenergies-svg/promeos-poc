/**
 * PROMEOS — NavPanel (Contextual Module Panel — Premium Life)
 * Glass surface. Module-tinted header from TINT_PALETTE.
 * Quick actions, recents, pins, sections with premium hover/active.
 */
import { useMemo, useCallback } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Star } from 'lucide-react';
import {
  NAV_MODULES,
  ROUTE_MODULE_MAP,
  QUICK_ACTIONS,
  TINT_PALETTE,
  NAV_ADMIN_ITEMS,
  NAV_ADMIN_ICON,
  getSectionsForModule,
} from './NavRegistry';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useAuth } from '../contexts/AuthContext';

/* ── Badge severity styles ── */
const BADGE_STYLES = {
  alerts: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  monitoring: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  _default: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

/* ── Panel Link (premium active/hover) ── */
function PanelLink({
  to,
  icon: Icon,
  label,
  longLabel,
  badge,
  badgeKey,
  pinned,
  onTogglePin,
  tint,
  indent,
}) {
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
        `group/link flex items-center gap-1.5 h-7 rounded-lg text-[12.5px] leading-5 transition-all duration-150 relative py-0.5 px-2${indent ? ' ml-3' : ''}
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

/* ── Section Header (static label — always visible, no toggle) ── */
function SectionHeader({ label, icon: SectionIcon, tintColor }) {
  const t = tintColor ? TINT_PALETTE[tintColor] || TINT_PALETTE.slate : null;
  return (
    <div className="flex items-center w-full px-2 py-1 mt-2 first:mt-0">
      {SectionIcon && (
        <SectionIcon size={12} className={`mr-1.5 shrink-0 ${t ? t.icon : 'text-slate-400'}`} />
      )}
      <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
        {label}
      </span>
    </div>
  );
}

/* ── Main Panel ── */
export default function NavPanel({ activeModule, pins, onTogglePin, badges }) {
  const _location = useLocation();
  const { isExpert } = useExpertMode();
  const { isAuthenticated, hasPermission } = useAuth();
  // Sections are always open — no toggle state needed

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

  /* ── Admin items (secondary menu) ── */
  const adminItems = useMemo(() => {
    return filterItems(NAV_ADMIN_ITEMS);
  }, [filterItems]);

  /* ── All visible items in this module ── */
  const allModuleItems = useMemo(() => moduleSections.flatMap((s) => s.items), [moduleSections]);

  /* ── Pinned items (only from this module's items) ── */
  const pinnedItems = useMemo(() => {
    return pins.map((path) => allModuleItems.find((item) => item.to === path)).filter(Boolean);
  }, [pins, allModuleItems]);

  /* Sections are always visible — no toggle/auto-open needed */

  /* ── Quick actions relevant to this module ── */
  const moduleQuickActions = useMemo(() => {
    const moduleRoutes = new Set(allModuleItems.map((i) => i.to));
    return QUICK_ACTIONS.filter((a) => moduleRoutes.has(a.to));
  }, [allModuleItems]);

  return (
    <div
      className="flex flex-col h-screen bg-white/80 backdrop-blur-sm border-r border-slate-200/60 shrink-0"
      style={{ width: 'clamp(190px, 14vw, 230px)' }}
      role="navigation"
      aria-label={`Module ${mod.label}`}
    >
      {/* Module header — tinted gradient */}
      <div
        className={`px-3 pt-3 pb-2 border-b border-slate-200/50 bg-gradient-to-b ${t.panelHeader}`}
      >
        <div className="flex items-center gap-2">
          <mod.icon size={16} className={t.icon} />
          <h2 className="text-sm font-semibold text-slate-800">{mod.label}</h2>
        </div>
        <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{mod.desc}</p>
      </div>

      {/* Quick actions — Raccourcis (expert only) */}
      {isExpert && moduleQuickActions.length > 0 && (
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
                  ${
                    isActive
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

        {/* Main sections — only for active module */}
        {moduleSections.map((section) => {
          const sectionTint = section.tint || tint;

          return (
            <div key={section.key}>
              <SectionHeader label={section.label} icon={section.icon} tintColor={sectionTint} />
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
            </div>
          );
        })}
      </nav>

      {/* Secondary menu — Administration (gear icon) */}
      {adminItems.length > 0 && (
        <div className="border-t border-slate-200/50 px-2 py-2">
          <SectionHeader label="Administration" icon={NAV_ADMIN_ICON} tintColor="slate" />
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
        </div>
      )}
    </div>
  );
}
