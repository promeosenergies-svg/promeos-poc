/**
 * PROMEOS — Sidebar (Rail + Panel Orchestrator)
 * Composes NavRail (64px icon strip) + NavPanel (208px contextual content).
 * Manages shared state: active module, pins, badges.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronsLeft, ChevronsRight } from 'lucide-react';
import NavRail from './NavRail';
import NavPanel from './NavPanel';
import { resolveModule } from './NavRegistry';
// Phase 2.B — P1.2.bis : les compteurs nav rail/panel viennent désormais
// d'un seul fetch consolidé via NavigationBadgesContext (endpoint backend
// /api/v1/navigation/badges). Suppression des fetches dispersés
// getNotificationsSummary, getMonitoringAlerts,
// getActionCenterActionsSummary, getActionCenterNotifications +
// computeActionCenterBadge — résolution dette TECH-badge-context-dedup.
//
// Phase 3.F (2026-05-02) : feature "Récents" retirée — décision UX
// audit docs/audits/ui_ux/02_navpanel_ux_audit_20260502.md (P0.2 dup
// store + P2.2 sub-utilité). Le Command Palette ⌘K reste l'entrée
// canonique pour retrouver une page récemment visitée.
import { useNavigationBadges } from '../contexts/NavigationBadgesContext';

const PINS_KEY = 'promeos_sidebar_pins';
const COLLAPSED_KEY = 'promeos_sidebar_collapsed';
const MAX_PINS = 5;

function loadJSON(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
}
function saveJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  /* ── Active module (derived from route) ── */
  const activeModule = useMemo(() => resolveModule(location.pathname), [location.pathname]);

  /* ── Module override: user clicks rail icon ── */
  const [overrideModule, setOverrideModule] = useState(null);
  const displayModule = overrideModule || activeModule;

  /* Reset override when route changes to a different module */
  useEffect(() => {
    setOverrideModule(null);
  }, [activeModule]);

  /* ── Module landing routes (icon click → navigate) ── */
  const MODULE_LANDING = { energie: '/consommations' };

  const handleSelectModule = useCallback(
    (key) => {
      if (key !== activeModule && MODULE_LANDING[key]) {
        navigate(MODULE_LANDING[key]);
      }
      setOverrideModule((prev) => (prev === key ? null : key));
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [activeModule, navigate]
  );

  /* ── Panel collapsed ── */
  const [collapsed, setCollapsed] = useState(() => loadJSON(COLLAPSED_KEY, false));
  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      saveJSON(COLLAPSED_KEY, next);
      return next;
    });
  }, []);

  /* ── Pins ── */
  const [pins, setPins] = useState(() => loadJSON(PINS_KEY, []));

  const togglePin = useCallback((path) => {
    setPins((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : prev.length < MAX_PINS
          ? [...prev, path]
          : prev;
      saveJSON(PINS_KEY, next);
      return next;
    });
  }, []);

  /* ── Badges (Phase 2.B — P1.2.bis) ──
   * Source unique : NavigationBadgesContext (endpoint backend
   * /api/v1/navigation/badges agrégeant 8 compteurs en un call). Fini
   * les 3 fetches dispersés (notifs + monitoring + action-center) qui
   * doublaient avec AppShell — résolution dette TECH-badge-context-dedup.
   *
   * Mapping doctrine §11.3 :
   *   - rail Conformité    ← compliance_alerts (notifs critical+warn)
   *   - rail Énergie       ← energy_alerts (monitoring open)
   *   - rail Facturation   ← billing_anomalies (Phase 1.D module)
   *   - rail Achat         ← purchase_deadlines (contrats <= 90 j)
   *   - item Centre d'action ← action_center (issues ouvertes)
   * Stale-while-revalidate côté Context : pas de flicker pendant refetch.
   */
  const { data: navBadges } = useNavigationBadges();
  const badges = useMemo(
    () => ({
      alerts: navBadges?.compliance_alerts ?? 0,
      monitoring: navBadges?.energy_alerts ?? 0,
      actionCenter: navBadges?.action_center ?? 0,
      facturation: navBadges?.billing_anomalies ?? 0,
      achat: navBadges?.purchase_deadlines ?? 0,
      // Progress conformité — recâblage post-P0.4 (dead-code retiré
      // en Phase 1.B faute de source). NavPanel les rend désormais.
      conformiteDt: navBadges?.conformite_dt_progress ?? 0,
      conformiteBacs: navBadges?.conformite_bacs_progress ?? 0,
      conformiteAper: navBadges?.conformite_aper_progress ?? 0,
    }),
    [navBadges]
  );

  return (
    // ── Z-index layer map ─────────────────────────────────────────────────────
    // z-30     Sidebar aside   (sticky, left column)
    // z-40     App header      (AppShell.jsx — sticky top-0 backdrop-blur-md)
    // z-[120]  Overlays        (dropdowns/popovers/tooltips — portal to body)
    // z-[200]  Modals/Drawers  (full-screen overlays — Modal.jsx, Drawer.jsx, wizards)
    // z-[210]  Nested modals   (confirm dialogs inside modals — PatrimoineWizard)
    // z-[250]  Toasts          (always on top — ToastProvider.jsx)
    // ─────────────────────────────────────────────────────────────────────────
    <aside
      className="flex h-full z-30 shrink-0 overflow-y-auto relative"
      aria-label="Navigation principale"
    >
      <NavRail activeModule={displayModule} onSelectModule={handleSelectModule} badges={badges} />
      {!collapsed && (
        <NavPanel
          activeModule={displayModule}
          pins={pins}
          onTogglePin={togglePin}
          badges={badges}
        />
      )}
      {/* Collapse/expand toggle — anchored at panel edge */}
      <button
        onClick={toggleCollapsed}
        aria-label={collapsed ? 'Ouvrir le panneau' : 'Réduire le panneau'}
        className="absolute top-3 -right-3 z-40 w-6 h-6 flex items-center justify-center
          bg-white border border-slate-200 rounded-full shadow-sm
          text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-all"
      >
        {collapsed ? <ChevronsRight size={12} /> : <ChevronsLeft size={12} />}
      </button>
    </aside>
  );
}
