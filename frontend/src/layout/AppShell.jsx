/**
 * PROMEOS — AppShell Layout (Rail + Panel)
 * Sidebar (Rail+Panel) + Header + Content with module-tinted header bands.
 */
import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Search, LogOut, ChevronDown, Building2, Command, Bell } from 'lucide-react';
import Sidebar from './Sidebar';
import Breadcrumb from './Breadcrumb';
import ScopeSwitcher from './ScopeSwitcher';
import DataReadinessBadge from '../components/DataReadinessBadge';
import DevPanel from './DevPanel';
import CommandPalette from '../ui/CommandPalette';
import ActionCenterSlideOver, {
  computeActionCenterBadge,
} from '../components/ActionCenterSlideOver';
import { ToastProvider } from '../ui/ToastProvider';
import { ActionDrawerProvider } from '../contexts/ActionDrawerContext';
import { Toggle } from '../ui';
import { trackRouteChange } from '../services/tracker';
import { useAuth } from '../contexts/AuthContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { resolveModule, MODULE_TINTS } from './NavRegistry';
import {
  getActionCenterActionsSummary,
  getActionCenterNotifications,
} from '../services/api/actions';

const BADGE_COLOR_CLASS = {
  red: 'bg-red-500 text-white',
  amber: 'bg-amber-500 text-white',
  gray: 'bg-slate-400 text-white',
};

const ROLE_LABELS = {
  dg_owner: 'DG / Propriétaire',
  dsi_admin: 'DSI / Admin',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Responsable Énergie',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  prestataire: 'Prestataire',
  auditeur: 'Auditeur',
  pmo_acc: 'PMO / Acc.',
};

function UserMenu() {
  const { user, org, role, orgs, logout, switchOrg, isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const [dropCoords, setDropCoords] = useState(null);
  const triggerRef = useRef(null);
  const dropRef = useRef(null);

  // Close on outside click — checks both trigger and portal dropdown
  useEffect(() => {
    if (!open) return;
    function onClickOutside(e) {
      if (triggerRef.current?.contains(e.target)) return;
      if (dropRef.current?.contains(e.target)) return;
      setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [open]);

  const toggleOpen = useCallback(() => {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setDropCoords({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    }
    setOpen((prev) => !prev);
  }, [open]);

  if (!isAuthenticated) {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-400 text-white flex items-center justify-center text-xs font-bold">
        ?
      </div>
    );
  }

  const initials =
    `${(user.prenom || '')[0] || ''}${(user.nom || '')[0] || ''}`.toUpperCase() || 'U';

  return (
    <div>
      <button
        ref={triggerRef}
        onClick={toggleOpen}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-2 py-1 transition"
      >
        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
          {initials}
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-sm font-medium text-gray-700 leading-tight">
            {user.prenom} {user.nom}
          </p>
          <p className="text-[11px] text-gray-500 leading-tight">{ROLE_LABELS[role] || role}</p>
        </div>
        <ChevronDown size={14} className="text-gray-400" />
      </button>

      {/* Menu — portal to document.body, position:fixed right-aligned, z-[120] */}
      {open &&
        dropCoords &&
        createPortal(
          <div
            ref={dropRef}
            role="menu"
            className="fixed w-64 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-[120]"
            style={{ top: dropCoords.top, right: dropCoords.right }}
          >
            <div className="px-4 py-2 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-800">
                {user.prenom} {user.nom}
              </p>
              <p className="text-xs text-gray-400">{user.email}</p>
              <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 rounded-full">
                {ROLE_LABELS[role] || role}
              </span>
            </div>

            <div className="px-4 py-2 border-b border-gray-100">
              <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">
                Organisation
              </p>
              <div className="flex items-center gap-2 mt-1">
                <Building2 size={14} className="text-gray-400" />
                <span className="text-sm text-gray-700">{org?.nom || '\u2014'}</span>
              </div>
            </div>

            {orgs && orgs.length > 1 && (
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide mb-1">
                  Changer d&apos;org
                </p>
                {orgs
                  .filter((o) => o.id !== org?.id)
                  .map((o) => (
                    <button
                      key={o.id}
                      onClick={() => {
                        switchOrg(o.id);
                        setOpen(false);
                      }}
                      className="w-full text-left px-2 py-1 text-sm text-gray-600 hover:bg-gray-50 rounded transition"
                    >
                      {o.nom}
                    </button>
                  ))}
              </div>
            )}

            <button
              onClick={() => {
                logout();
                setOpen(false);
              }}
              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition"
            >
              <LogOut size={14} />
              Déconnexion
            </button>
          </div>,
          document.body
        )}
    </div>
  );
}

export default function AppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [actionCenterOpen, setActionCenterOpen] = useState(false);
  const [actionCenterTab, setActionCenterTab] = useState('actions');
  const [actionCenterBadge, setActionCenterBadge] = useState({ count: null, color: 'gray' });
  const { isExpert, toggleExpert } = useExpertMode();

  useEffect(() => {
    trackRouteChange(location.pathname);
  }, [location.pathname]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('actionCenter') === 'open') {
      setActionCenterOpen(true);
      setActionCenterTab(params.get('tab') || 'actions');
      params.delete('actionCenter');
      params.delete('tab');
      const search = params.toString();
      navigate(
        { pathname: location.pathname, search: search ? `?${search}` : '' },
        { replace: true }
      );
    }
  }, [location.search, location.pathname, navigate]);

  useEffect(() => {
    if (actionCenterOpen) return undefined;
    let cancelled = false;
    const fetchBadge = async () => {
      try {
        const [summary, notif] = await Promise.all([
          getActionCenterActionsSummary().catch(() => null),
          getActionCenterNotifications({ unread_only: true }).catch(() => ({ notifications: [] })),
        ]);
        if (cancelled) return;
        const next = computeActionCenterBadge(summary, notif?.notifications || []);
        setActionCenterBadge((prev) =>
          prev.count === next.count && prev.color === next.color ? prev : next
        );
      } catch {
        /* ignore */
      }
    };
    fetchBadge();
    const interval = setInterval(fetchBadge, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [actionCenterOpen]);

  useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const currentModule = useMemo(() => resolveModule(location.pathname), [location.pathname]);
  const headerBandClass = MODULE_TINTS[currentModule] || MODULE_TINTS.cockpit;
  const badgeColorClass = BADGE_COLOR_CLASS[actionCenterBadge.color];

  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-50/80">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header — glass surface */}
        <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/70 px-6 py-3 flex items-center justify-between sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <Breadcrumb />
            <div className="relative">
              <ScopeSwitcher />
            </div>
            <DataReadinessBadge />
          </div>
          <div className="flex items-center gap-3">
            {/* Command Palette trigger */}
            <button
              onClick={() => setPaletteOpen(true)}
              aria-label="Ouvrir la recherche (Ctrl+K)"
              className="flex items-center gap-2 px-3 py-2 bg-white/60 border border-slate-200/80 rounded-lg text-sm text-slate-400
                hover:bg-white hover:text-slate-600 hover:border-slate-300 transition-all duration-150 shadow-sm"
            >
              <Search size={14} />
              <span className="hidden sm:inline">Rechercher...</span>
              <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono bg-slate-50 border border-slate-200/80 rounded ml-2">
                <Command size={10} className="mr-0.5" />K
              </kbd>
            </button>

            {/* Centre d'actions — cloche (V7) */}
            <button
              onClick={() => {
                setActionCenterTab('actions');
                setActionCenterOpen(true);
              }}
              aria-label="Centre d'actions"
              title="Centre d'actions"
              className="relative p-2 bg-white/60 border border-slate-200/80 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-white hover:border-slate-300 transition-all shadow-sm"
            >
              <Bell size={16} />
              {actionCenterBadge.count !== null && (
                <span
                  className={`absolute -top-1 -right-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full min-w-[18px] text-center leading-tight ${badgeColorClass}`}
                >
                  {actionCenterBadge.count}
                </span>
              )}
            </button>

            {/* Expert Mode toggle */}
            <div title="Affiche source, confiance et détails techniques">
              <Toggle checked={isExpert} onChange={toggleExpert} label="Expert" size="sm" />
            </div>
            <UserMenu />
          </div>
        </header>

        {/* Tinted header band */}
        <div
          className={`h-24 bg-gradient-to-b ${headerBandClass} -mb-24 pointer-events-none`}
          aria-hidden="true"
        />

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          <ToastProvider>
            <ActionDrawerProvider>
              <Outlet />
            </ActionDrawerProvider>
          </ToastProvider>
        </main>
      </div>

      {/* Command Palette overlay */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onToggleExpert={toggleExpert}
      />

      {/* Centre d'actions slide-over (V7) */}
      <ActionCenterSlideOver
        open={actionCenterOpen}
        onClose={() => setActionCenterOpen(false)}
        defaultTab={actionCenterTab}
      />

      {/* Dev Panel — dev-only, visible when ?debug */}
      <DevPanel />
    </div>
  );
}
