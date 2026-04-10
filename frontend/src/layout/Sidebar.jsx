/**
 * PROMEOS — Sidebar (Rail + Panel Orchestrator)
 * Composes NavRail (64px icon strip) + NavPanel (208px contextual content).
 * Manages shared state: active module, pins, badges, recents tracking.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import NavRail from './NavRail';
import NavPanel from './NavPanel';
import { resolveModule, matchRouteToModule, ALL_NAV_ITEMS } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { addRecent } from '../utils/navRecent';
import { resolveBreadcrumbLabel } from './Breadcrumb';

const PINS_KEY = 'promeos_sidebar_pins';
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

  /* ── Badges ── */
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);

  // Fetch badges on mount + auto-refresh every 2 minutes
  useEffect(() => {
    const fetchBadges = () => {
      getNotificationsSummary()
        .then((s) => setAlertBadge(s.new_critical + s.new_warn))
        .catch(() => {});
      getMonitoringAlerts(null, 'open', 200)
        .then((alerts) => setMonitoringBadge(Array.isArray(alerts) ? alerts.length : 0))
        .catch(() => {});
    };
    fetchBadges();
    const interval = setInterval(fetchBadges, 2 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const badges = useMemo(
    () => ({ alerts: alertBadge, monitoring: monitoringBadge }),
    [alertBadge, monitoringBadge]
  );

  /* ── Track recents on route change (V2: with label + module) ── */
  useEffect(() => {
    const path = location.pathname;
    // Match against nav items OR dynamic patterns
    const navItem = ALL_NAV_ITEMS.find((item) => path === item.to);
    const isNavRoute = navItem || ALL_NAV_ITEMS.some((item) => path.startsWith(item.to + '/'));
    if (isNavRoute || matchRouteToModule(path).pattern) {
      const { moduleId } = matchRouteToModule(path);
      // Build label: use nav item label, or derive from last path segment
      const parts = path.split('/').filter(Boolean);
      const label =
        navItem?.label || resolveBreadcrumbLabel(parts[parts.length - 1], parts[parts.length - 2]);
      addRecent(path, { label, module: moduleId });
    }
  }, [location.pathname]);

  return (
    // ── Z-index layer map ─────────────────────────────────────────────────────
    // z-30     Sidebar aside   (sticky, left column)
    // z-40     App header      (AppShell.jsx — sticky top-0 backdrop-blur-md)
    // z-[120]  Overlays        (dropdowns/popovers/tooltips — portal to body)
    // z-[200]  Modals/Drawers  (full-screen overlays — Modal.jsx, Drawer.jsx, wizards)
    // z-[210]  Nested modals   (confirm dialogs inside modals — PatrimoineWizard)
    // z-[250]  Toasts          (always on top — ToastProvider.jsx)
    // ─────────────────────────────────────────────────────────────────────────
    <aside className="flex h-full z-30 shrink-0 overflow-y-auto" aria-label="Navigation principale">
      <NavRail activeModule={displayModule} onSelectModule={handleSelectModule} />
      <NavPanel activeModule={displayModule} pins={pins} onTogglePin={togglePin} badges={badges} />
    </aside>
  );
}
