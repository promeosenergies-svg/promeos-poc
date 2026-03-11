/**
 * PROMEOS — AppShell Layout (Rail + Panel)
 * Sidebar (Rail+Panel) + Header + Content with module-tinted header bands.
 */
import { useEffect, useState, useRef, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Outlet, useLocation } from 'react-router-dom';
import { Search, LogOut, ChevronDown, Building2, Command } from 'lucide-react';
import Sidebar from './Sidebar';
import Breadcrumb from './Breadcrumb';
import ScopeSwitcher from './ScopeSwitcher';
import DataReadinessBadge from '../components/DataReadinessBadge';
import DevPanel from './DevPanel';
import CommandPalette from '../ui/CommandPalette';
import { ToastProvider } from '../ui/ToastProvider';
import { ActionDrawerProvider } from '../contexts/ActionDrawerContext';
import { Toggle } from '../ui';
import { trackRouteChange } from '../services/tracker';
import { getMetaVersion } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { resolveModule, MODULE_TINTS } from './NavRegistry';

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
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { isExpert, toggleExpert } = useExpertMode();
  const [appVersion, setAppVersion] = useState(null);

  useEffect(() => {
    if (isExpert) getMetaVersion().then(setAppVersion);
    else setAppVersion(null);
  }, [isExpert]);

  useEffect(() => {
    trackRouteChange(location.pathname);
  }, [location.pathname]);

  // Global Ctrl+K shortcut
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

  // Module-tinted header band
  const currentModule = useMemo(() => resolveModule(location.pathname), [location.pathname]);
  const headerBandClass = MODULE_TINTS[currentModule] || MODULE_TINTS.cockpit;

  return (
    <div className="flex min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-50/80">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
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

            {/* Expert Mode toggle */}
            <div title="Le mode Expert affiche la formule de score, les paramètres, les hypothèses et les références utilisées pour chaque évaluation.">
              <Toggle checked={isExpert} onChange={toggleExpert} label="Expert" size="sm" />
            </div>
            {isExpert && appVersion && (
              <span
                className="text-xs font-mono text-slate-400 border border-slate-200 rounded px-1.5 py-0.5"
                title={`branch: ${appVersion.branch} — ${appVersion.build_time}`}
              >
                {appVersion.sha}
              </span>
            )}

            <UserMenu />
          </div>
        </header>

        {/* Module-tinted header band — subtle depth glow */}
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

      {/* Dev Panel — dev-only, visible when ?debug */}
      <DevPanel />
    </div>
  );
}
