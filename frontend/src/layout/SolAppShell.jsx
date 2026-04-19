/**
 * PROMEOS — SolAppShell (Phase 3, refonte Sol V1 GLOBAL)
 *
 * Production wrapper qui remplace `AppShell` legacy sur toutes les routes
 * protégées. Absorbe le top-bar legacy (breadcrumb + search + expert + user)
 * dans un header Sol ≤ 40px + slots top/bottom du SolPanel.
 *
 * Contextes préservés (tous montés ici) :
 *   - ToastProvider, ActionDrawerProvider (autour de Outlet)
 *   - CommandPalette (⌘K global, trigger absorbé dans header-sol)
 *   - ActionCenterSlideOver (cloche absorbée dans rail-footer)
 *   - OnboardingOverlay (overlay conservé tel quel)
 *   - DevPanel (dev-only, ?debug)
 *   - SolTimerail fixed bottom 36px (livraison Phase 1)
 *   - SolCartouche bas-droit (livraison Phase 1, état Sol V1 Phase 4.6)
 *
 * Layout grid :
 *   ┌────┬──────┬────────────────────────────┐
 *   │rail│panel │ main                       │
 *   │ 56 │ 240  │ (outlet + routes)          │
 *   │    │      │                            │
 *   │    │      │                            │
 *   ├────┴──────┴────────────────────────────┤
 *   │ timerail 36px                          │
 *   └────────────────────────────────────────┘
 *
 * Le header-sol (≤ 40px) est INJECTÉ dans la zone main, en sticky top 0.
 * Il contient : SearchTrigger (⌘K) + Expert toggle + ActionCenter bell.
 * Scope switcher + user menu sont dans SolPanel (top/bottom).
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Search, Command, Bell, LogOut, ChevronDown, User, Settings, Shield } from 'lucide-react';
import SolRail from '../ui/sol/SolRail';
import SolPanel from '../ui/sol/SolPanel';
import SolTimerail from '../ui/sol/SolTimerail';
import SolCartouche from '../ui/sol/SolCartouche';
import ScopeSwitcher from './ScopeSwitcher';
import CommandPalette from '../ui/CommandPalette';
import ActionCenterSlideOver, { computeActionCenterBadge } from '../components/ActionCenterSlideOver';
import OnboardingOverlay from '../components/OnboardingOverlay';
import DevPanel from './DevPanel';
import { ToastProvider } from '../ui/ToastProvider';
import { ActionDrawerProvider } from '../contexts/ActionDrawerContext';
import { Toggle } from '../ui';
import { useAuth } from '../contexts/AuthContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { trackRouteChange } from '../services/tracker';
import {
  getActionCenterActionsSummary,
  getActionCenterNotifications,
} from '../services/api/actions';

const BADGE_COLOR_CLASS = {
  red: 'bg-red-500 text-white',
  amber: 'bg-amber-500 text-white',
  gray: 'bg-slate-400 text-white',
};

// ─────────────────────────────────────────────────────────────────────────────
// PanelHeaderSlot — scope switcher + status DB (haut du panel)
// PanelFooterSlot — user menu (bas du panel)
// ─────────────────────────────────────────────────────────────────────────────

function PanelHeaderSlot() {
  return (
    <div style={{ padding: '14px 14px 12px', borderBottom: '1px solid var(--sol-rule)' }}>
      <ScopeSwitcher />
    </div>
  );
}

const ROLE_LABELS = {
  dg_owner: 'DG / Propriétaire',
  daf: 'DAF',
  acheteur: 'Acheteur',
  resp_conformite: 'Resp. Conformité',
  energy_manager: 'Responsable Énergie',
  resp_immobilier: 'Resp. Immobilier',
  resp_site: 'Resp. Site',
  dsi_admin: 'DSI / Admin',
};

function PanelFooterSlot() {
  const { user, role, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const name = user?.name || user?.email?.split('@')[0] || 'Promeos Admin';
  const initials = name
    .split(/[\s@._-]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('') || 'PA';
  const roleLabel = ROLE_LABELS[role] || role || 'DG / Propriétaire';

  return (
    <div
      style={{
        borderTop: '1px solid var(--sol-rule)',
        padding: '10px 14px',
        position: 'relative',
      }}
    >
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        aria-label="Menu utilisateur"
        aria-expanded={open}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          width: '100%',
          padding: '4px 2px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--sol-ink-700)',
          fontSize: 13,
          textAlign: 'left',
          borderRadius: 4,
          transition: 'background 120ms',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--sol-bg-panel)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        <span
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: 'var(--sol-calme-bg)',
            color: 'var(--sol-calme-fg)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 11,
            fontWeight: 600,
            fontFamily: 'var(--sol-font-mono)',
          }}
        >
          {initials}
        </span>
        <span
          style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            fontWeight: 500,
          }}
        >
          {name}
        </span>
        <ChevronDown
          size={13}
          style={{
            color: 'var(--sol-ink-400)',
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 120ms',
          }}
        />
      </button>
      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 79 }}
            aria-hidden="true"
          />
          <div
            role="menu"
            style={{
              position: 'absolute',
              bottom: 'calc(100% - 2px)',
              left: 14,
              right: 14,
              background: 'var(--sol-bg-paper)',
              border: '1px solid var(--sol-rule)',
              borderRadius: 6,
              boxShadow: '0 4px 12px rgba(15, 23, 42, 0.08)',
              zIndex: 80,
              overflow: 'hidden',
            }}
          >
            {/* Info rôle — non-cliquable, juste afficher */}
            <div
              style={{
                padding: '10px 14px',
                borderBottom: '1px solid var(--sol-rule)',
                background: 'var(--sol-bg-canvas)',
              }}
            >
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: 'var(--sol-ink-500)',
                  fontWeight: 600,
                }}
              >
                <Shield size={11} /> Rôle
              </span>
              <div
                style={{
                  fontSize: 12,
                  color: 'var(--sol-ink-700)',
                  marginTop: 2,
                }}
              >
                {roleLabel}
              </div>
            </div>
            {[
              { icon: User, label: 'Profil', to: '/admin/users' },
              { icon: Settings, label: 'Paramètres', to: '/admin/users' },
            ].map(({ icon: Icon, label, to }) => (
              <button
                key={label}
                type="button"
                role="menuitem"
                onClick={() => { setOpen(false); navigate(to); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '9px 14px',
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--sol-ink-700)',
                  fontSize: 12.5,
                  textAlign: 'left',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--sol-bg-panel)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
              >
                <Icon size={13} /> {label}
              </button>
            ))}
            <button
              type="button"
              role="menuitem"
              onClick={() => { setOpen(false); logout?.(); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                width: '100%',
                padding: '9px 14px',
                background: 'transparent',
                border: 'none',
                borderTop: '1px solid var(--sol-rule)',
                cursor: 'pointer',
                color: 'var(--sol-refuse-fg)',
                fontSize: 12.5,
                textAlign: 'left',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--sol-refuse-bg)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            >
              <LogOut size={13} /> Se déconnecter
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Header Sol ≤ 40px : search trigger + expert toggle + notifications bell
// ─────────────────────────────────────────────────────────────────────────────

function SolAppShellHeader({
  onSearchClick,
  onActionCenterClick,
  actionCenterBadge,
  isExpert,
  toggleExpert,
}) {
  return (
    <header
      className="sol-app-header"
      style={{
        height: 40,
        minHeight: 40,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: 10,
        padding: '0 24px',
        background: 'var(--sol-bg-paper)',
        borderBottom: '1px solid var(--sol-rule)',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Command palette trigger */}
      <button
        type="button"
        onClick={onSearchClick}
        aria-label="Ouvrir la recherche (Ctrl+K)"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          background: 'var(--sol-bg-canvas)',
          border: '1px solid var(--sol-rule)',
          borderRadius: 4,
          color: 'var(--sol-ink-500)',
          fontSize: 12,
          fontFamily: 'var(--sol-font-body)',
          cursor: 'pointer',
          transition: 'border-color 120ms',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--sol-ink-300)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--sol-rule)'; }}
      >
        <Search size={12} />
        <span>Rechercher</span>
        <kbd
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '0 4px',
            marginLeft: 4,
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 9.5,
            background: 'var(--sol-bg-paper)',
            border: '1px solid var(--sol-rule)',
            borderRadius: 2,
            color: 'var(--sol-ink-400)',
          }}
        >
          <Command size={9} style={{ marginRight: 2 }} />K
        </kbd>
      </button>

      {/* Action Center bell */}
      <button
        type="button"
        onClick={onActionCenterClick}
        aria-label="Centre d'actions"
        title="Centre d'actions"
        style={{
          position: 'relative',
          width: 30,
          height: 30,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--sol-bg-canvas)',
          border: '1px solid var(--sol-rule)',
          borderRadius: 4,
          color: 'var(--sol-ink-500)',
          cursor: 'pointer',
          transition: 'border-color 120ms',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--sol-ink-300)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--sol-rule)'; }}
      >
        <Bell size={14} />
        {actionCenterBadge.count !== null && (
          <span
            className={BADGE_COLOR_CLASS[actionCenterBadge.color] || ''}
            style={{
              position: 'absolute',
              top: -4,
              right: -4,
              minWidth: 16,
              height: 16,
              padding: '0 4px',
              fontSize: 9,
              fontFamily: 'var(--sol-font-mono)',
              fontWeight: 700,
              borderRadius: 8,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: 1,
            }}
          >
            {actionCenterBadge.count}
          </span>
        )}
      </button>

      {/* Expert toggle */}
      <div
        style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
        title="Affiche sources, confiance, détails techniques"
      >
        <Toggle checked={isExpert} onChange={toggleExpert} label="Expert" size="sm" />
      </div>
    </header>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SolAppShell — wrapper global
// ─────────────────────────────────────────────────────────────────────────────

export default function SolAppShell() {
  const location = useLocation();
  const navigate = useNavigate();
  const { role } = useAuth();
  const { isExpert, toggleExpert } = useExpertMode();

  const [paletteOpen, setPaletteOpen] = useState(false);
  const [actionCenterOpen, setActionCenterOpen] = useState(false);
  const [actionCenterTab, setActionCenterTab] = useState('actions');
  const [actionCenterBadge, setActionCenterBadge] = useState({ count: null, color: 'gray' });

  // Track route changes (analytics)
  useEffect(() => { trackRouteChange(location.pathname); }, [location.pathname]);

  // URL param actionCenter=open → open slide-over
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

  // Action center badge polling (60s)
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
      } catch { /* ignore */ }
    };
    fetchBadge();
    const interval = setInterval(fetchBadge, 60_000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [actionCenterOpen]);

  // ⌘K / Ctrl+K global
  useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
      // Ctrl+Shift+X : toggle expert
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'X' || e.key === 'x')) {
        e.preventDefault();
        toggleExpert?.();
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [toggleExpert]);

  const panelProps = useMemo(
    () => ({
      isExpert,
      headerSlot: <PanelHeaderSlot />,
      footerSlot: <PanelFooterSlot />,
    }),
    [isExpert]
  );

  return (
    <div
      className="sol-app"
      style={{
        display: 'grid',
        gridTemplateColumns: '56px 240px 1fr',
        gridTemplateRows: '1fr 36px',
        gridTemplateAreas: '"rail panel main" "rail panel timerail"',
        minHeight: '100vh',
        background: 'var(--sol-bg-canvas)',
        color: 'var(--sol-ink-900)',
        fontFamily: 'var(--sol-font-body)',
      }}
    >
      {/* Skip link a11y */}
      <a
        href="#main-content"
        className="sr-only"
        style={{ position: 'absolute', left: -9999, top: 0 }}
      >
        Aller au contenu
      </a>

      <SolRail role={role} isExpert={isExpert} />
      <SolPanel {...panelProps} />

      <main
        id="main-content"
        style={{
          gridArea: 'main',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <SolAppShellHeader
          onSearchClick={() => setPaletteOpen(true)}
          onActionCenterClick={() => { setActionCenterTab('actions'); setActionCenterOpen(true); }}
          actionCenterBadge={actionCenterBadge}
          isExpert={isExpert}
          toggleExpert={toggleExpert}
        />
        <div style={{ flex: 1, padding: '24px 40px 48px' }}>
          <ToastProvider>
            <ActionDrawerProvider>
              <Outlet />
            </ActionDrawerProvider>
          </ToastProvider>
        </div>
      </main>

      <div style={{ gridArea: 'timerail' }}>
        <SolTimerail />
      </div>

      {/* Global overlays */}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onToggleExpert={toggleExpert}
      />
      <ActionCenterSlideOver
        open={actionCenterOpen}
        onClose={() => setActionCenterOpen(false)}
        defaultTab={actionCenterTab}
      />
      <DevPanel />
      <OnboardingOverlay />
      <SolCartouche state="default" />
    </div>
  );
}
