import { useEffect, useState, useRef } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Search, LogOut, ChevronDown, Building2, Shield } from 'lucide-react';
import Sidebar from './Sidebar';
import Breadcrumb from './Breadcrumb';
import ScopeSwitcher from './ScopeSwitcher';
import { trackRouteChange } from '../services/tracker';
import { useAuth } from '../contexts/AuthContext';

const ROLE_LABELS = {
  dg_owner: 'DG / Owner',
  dsi_admin: 'DSI / Admin',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Energy Manager',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  prestataire: 'Prestataire',
  auditeur: 'Auditeur',
  pmo_acc: 'PMO / Acc.',
};

function UserMenu() {
  const { user, org, role, orgs, logout, switchOrg, isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  if (!isAuthenticated) {
    return (
      <div className="w-8 h-8 rounded-full bg-gray-400 text-white flex items-center justify-center text-xs font-bold">
        ?
      </div>
    );
  }

  const initials = `${(user.prenom || '')[0] || ''}${(user.nom || '')[0] || ''}`.toUpperCase() || 'U';

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 hover:bg-gray-50 rounded-lg px-2 py-1 transition"
      >
        <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">
          {initials}
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-sm font-medium text-gray-700 leading-tight">{user.prenom} {user.nom}</p>
          <p className="text-[11px] text-gray-400 leading-tight">{ROLE_LABELS[role] || role}</p>
        </div>
        <ChevronDown size={14} className="text-gray-400" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
          {/* User info */}
          <div className="px-4 py-2 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-800">{user.prenom} {user.nom}</p>
            <p className="text-xs text-gray-400">{user.email}</p>
            <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold bg-blue-50 text-blue-700 rounded-full">
              {ROLE_LABELS[role] || role}
            </span>
          </div>

          {/* Current org */}
          <div className="px-4 py-2 border-b border-gray-100">
            <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide">Organisation</p>
            <div className="flex items-center gap-2 mt-1">
              <Building2 size={14} className="text-gray-400" />
              <span className="text-sm text-gray-700">{org?.nom || '—'}</span>
            </div>
          </div>

          {/* Switch org (if multi-org) */}
          {orgs && orgs.length > 1 && (
            <div className="px-4 py-2 border-b border-gray-100">
              <p className="text-[10px] uppercase text-gray-400 font-semibold tracking-wide mb-1">Changer d'org</p>
              {orgs.filter(o => o.id !== org?.id).map(o => (
                <button
                  key={o.id}
                  onClick={() => { switchOrg(o.id); setOpen(false); }}
                  className="w-full text-left px-2 py-1 text-sm text-gray-600 hover:bg-gray-50 rounded transition"
                >
                  {o.nom}
                </button>
              ))}
            </div>
          )}

          {/* Logout */}
          <button
            onClick={() => { logout(); setOpen(false); }}
            className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition"
          >
            <LogOut size={14} />
            Déconnexion
          </button>
        </div>
      )}
    </div>
  );
}

export default function AppShell() {
  const location = useLocation();

  useEffect(() => {
    trackRouteChange(location.pathname);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <Breadcrumb />
            <div className="relative">
              <ScopeSwitcher />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Rechercher..."
                className="pl-9 pr-4 py-2 w-52 bg-gray-50 border border-gray-200 rounded-lg text-sm
                  placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white"
              />
            </div>
            <UserMenu />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
