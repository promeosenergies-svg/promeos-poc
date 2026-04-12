/**
 * PROMEOS — NavPanel (Contextual Module Panel — Premium Life)
 * Glass surface. Module-tinted header from TINT_PALETTE.
 * Quick actions, recents, pins, sections with premium hover/active.
 */
import { useState, useEffect, useMemo, useCallback, useRef, Fragment } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Star, X, Search, Clock } from 'lucide-react';
import {
  getActiveSite,
  clearActiveSite,
  setActiveSite,
  ACTIVE_SITE_EVENT,
} from '../utils/activeSite';
import { fmtArea } from '../utils/format';

const SITE360_RE = /^\/sites\/\d+/;
const STATUT_DOT_COLOR = {
  conforme: '#0F6E56',
  non_conforme: '#E24B4A',
  a_risque: '#E24B4A',
  a_evaluer: '#BA7517',
};

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
import { useScope } from '../contexts/ScopeContext';

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
  desc,
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
      title={desc || undefined}
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

/* ── Highlight helper for site search ── */
function highlightMatch(text, query) {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-amber-100 text-inherit rounded-sm px-px">
        {text.slice(idx, idx + query.length)}
      </mark>
      {text.slice(idx + query.length)}
    </>
  );
}

/* ── Recents (last 5 visited nav pages, persisted in localStorage) ── */
const RECENTS_KEY = 'promeos_nav_recents';
const MAX_RECENTS = 5;

function loadRecents() {
  try {
    return JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
  } catch {
    return [];
  }
}

function pushRecent(path) {
  const recents = loadRecents().filter((r) => r !== path);
  recents.unshift(path);
  localStorage.setItem(RECENTS_KEY, JSON.stringify(recents.slice(0, MAX_RECENTS)));
}

/* ── Main Panel ── */
export default function NavPanel({ activeModule, pins, onTogglePin, badges }) {
  const _location = useLocation();
  const _navigate = useNavigate();
  const { isExpert } = useExpertMode();

  // Track recent nav pages
  const [recents, setRecents] = useState(loadRecents);
  useEffect(() => {
    const base = _location.pathname.split('?')[0].split('#')[0];
    if (base !== '/' && !base.startsWith('/login')) {
      pushRecent(base);
      setRecents(loadRecents());
    }
  }, [_location.pathname]);

  // Active site context (for contextual nav item in patrimoine)
  const [activeSiteCtx, setActiveSiteCtx] = useState(() => getActiveSite());
  useEffect(() => {
    const handler = (e) => setActiveSiteCtx(e.detail);
    window.addEventListener(ACTIVE_SITE_EVENT, handler);
    return () => window.removeEventListener(ACTIVE_SITE_EVENT, handler);
  }, []);
  const isOnSite360 = SITE360_RE.test(_location.pathname);
  const { isAuthenticated, hasPermission } = useAuth();
  const { orgSites } = useScope();

  // ── Site search (inline in patrimoine section) ──
  const [siteQuery, setSiteQuery] = useState('');
  const [showResults, setShowResults] = useState(false);
  const searchInputRef = useRef(null);

  const siteResults = useMemo(() => {
    if (!siteQuery.trim()) return [];
    const q = siteQuery.trim().toLowerCase();
    return orgSites.filter((s) => {
      const nom = (s.nom || '').toLowerCase();
      const ville = (s.ville || s.city || '').toLowerCase();
      const code = (s.code_postal || '').toLowerCase();
      return nom.includes(q) || ville.includes(q) || code.includes(q);
    });
  }, [orgSites, siteQuery]);

  // "/" keyboard shortcut to focus site search
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const tag = document.activeElement?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable)
          return;
        if (!activeSiteCtx && activeModule === 'patrimoine') {
          e.preventDefault();
          searchInputRef.current?.focus();
        }
      }
      if (e.key === 'Escape' && showResults) {
        setShowResults(false);
        setSiteQuery('');
        searchInputRef.current?.blur();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [activeSiteCtx, activeModule, showResults]);

  // Click outside closes results (use the outer wrapper as containment boundary)
  const searchWrapperRef = useRef(null);
  useEffect(() => {
    if (!showResults) return;
    function onClickOutside(e) {
      if (searchWrapperRef.current?.contains(e.target)) return;
      setShowResults(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [showResults]);

  const handleSelectSite = useCallback(
    (site) => {
      setActiveSite(site);
      setActiveSiteCtx({
        id: site.id,
        nom: site.nom,
        statut: site.statut_conformite || 'a_evaluer',
      });
      setSiteQuery('');
      setShowResults(false);
      _navigate(`/sites/${site.id}`);
    },
    [_navigate]
  );

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

        {/* Recents — last visited pages (across all modules) */}
        {recents.length > 0 && pinnedItems.length === 0 && (
          <div className="pb-2 mb-1 border-b border-slate-200/40">
            <p className="px-2.5 pb-0.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Clock size={8} className="text-slate-400" /> Récents
            </p>
            {recents
              .map((path) => allModuleItems.find((item) => item.to.split('?')[0] === path))
              .filter(Boolean)
              .slice(0, 3)
              .map((item) => (
                <PanelLink key={`recent-${item.to}`} {...item} badge={0} tint={tint} />
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
                {section.items.map((item, idx) => (
                  <Fragment key={item.to}>
                    <PanelLink
                      {...item}
                      badge={item.badgeKey ? badges[item.badgeKey] : 0}
                      pinned={pins.includes(item.to)}
                      onTogglePin={onTogglePin}
                      tint={sectionTint}
                    />
                    {/* Mini site search (between Registre and Conformité, hidden when active site set) */}
                    {idx === 0 && section.key === 'patrimoine' && !activeSiteCtx && (
                      <div ref={searchWrapperRef} className="relative mx-1 mt-1.5 mb-1">
                        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-slate-50 border border-slate-200/60 focus-within:border-emerald-400 focus-within:ring-1 focus-within:ring-emerald-200 transition-all">
                          <Search size={12} className="text-slate-400 shrink-0" />
                          <input
                            ref={searchInputRef}
                            type="text"
                            value={siteQuery}
                            onChange={(e) => {
                              setSiteQuery(e.target.value);
                              setShowResults(true);
                            }}
                            onFocus={() => setShowResults(true)}
                            placeholder="Rechercher un site..."
                            className="flex-1 bg-transparent text-[11.5px] text-slate-700 placeholder:text-slate-400/70 outline-none min-w-0"
                          />
                          {!siteQuery && (
                            <kbd className="text-[9px] text-slate-400 bg-slate-100 rounded px-1 py-px font-mono">
                              /
                            </kbd>
                          )}
                          {siteQuery && (
                            <button
                              type="button"
                              onClick={() => {
                                setSiteQuery('');
                                searchInputRef.current?.focus();
                              }}
                              className="text-slate-400 hover:text-slate-600 p-0.5"
                            >
                              <X size={10} />
                            </button>
                          )}
                        </div>
                        {showResults && siteQuery.trim() && (
                          <div className="mt-1 rounded-md bg-white border border-slate-200 shadow-sm max-h-48 overflow-y-auto">
                            {siteResults.length === 0 && (
                              <p className="text-[11px] text-slate-400 px-2.5 py-2 text-center">
                                Aucun site trouvé
                              </p>
                            )}
                            {siteResults.slice(0, 5).map((s) => (
                              <button
                                key={s.id}
                                type="button"
                                className="w-full flex items-center gap-2 px-2.5 py-1.5 text-left hover:bg-emerald-50 transition-colors text-[11.5px]"
                                onClick={() => handleSelectSite(s)}
                              >
                                <span
                                  className="w-1.5 h-1.5 rounded-full shrink-0"
                                  style={{
                                    backgroundColor:
                                      STATUT_DOT_COLOR[s.statut_conformite] || '#888',
                                  }}
                                />
                                <span className="flex-1 truncate text-slate-700">
                                  {highlightMatch(s.nom, siteQuery.trim())}
                                </span>
                                <span className="text-[10px] text-slate-400 shrink-0 ml-1">
                                  {s.surface_m2 ? fmtArea(s.surface_m2) : ''}
                                  {s.surface_m2 && s.ville ? ' \u00b7 ' : ''}
                                  {s.ville || ''}
                                </span>
                              </button>
                            ))}
                            {siteResults.length > 5 && (
                              <p className="text-[10px] text-slate-400 px-2.5 py-1.5 text-center border-t border-slate-100">
                                et {siteResults.length - 5} autre
                                {siteResults.length - 5 > 1 ? 's' : ''}&hellip;
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {/* Item contextuel : site actif (entre Registre et Conformité) */}
                    {idx === 0 && section.key === 'patrimoine' && activeSiteCtx && (
                      <div
                        className={`group flex items-center gap-2 px-3.5 py-1.5 mx-1 rounded-md cursor-pointer text-[12px] transition-all ${
                          isOnSite360
                            ? 'bg-emerald-50 text-emerald-700 font-medium border-l-2 border-emerald-600'
                            : 'text-slate-400 hover:bg-slate-50 hover:text-slate-600'
                        }`}
                        onClick={() => _navigate(`/sites/${activeSiteCtx.id}`)}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full shrink-0"
                          style={{
                            backgroundColor: STATUT_DOT_COLOR[activeSiteCtx.statut] || '#888',
                          }}
                        />
                        <span className="truncate flex-1">{activeSiteCtx.nom}</span>
                        <button
                          type="button"
                          aria-label="Fermer la fiche site"
                          className="opacity-0 group-hover:opacity-100 hover:bg-slate-200 rounded p-0.5 transition-opacity"
                          onClick={(e) => {
                            e.stopPropagation();
                            clearActiveSite();
                            setActiveSiteCtx(null);
                            if (isOnSite360) _navigate('/patrimoine');
                          }}
                          title="Fermer la fiche site"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    )}
                  </Fragment>
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
