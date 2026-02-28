/**
 * PROMEOS — Sidebar (Rail + Panel Orchestrator)
 * Composes NavRail (64px icon strip) + NavPanel (208px contextual content).
 * Manages shared state: active module, pins, badges, recents tracking.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import NavRail from './NavRail';
import NavPanel from './NavPanel';
import { resolveModule, ALL_NAV_ITEMS } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { addRecent } from '../utils/navRecent';

const PINS_KEY = 'promeos_sidebar_pins';
const MAX_PINS = 5;

function loadJSON(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
}
function saveJSON(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export default function Sidebar() {
  const location = useLocation();

  /* ── Active module (derived from route) ── */
  const activeModule = useMemo(
    () => resolveModule(location.pathname),
    [location.pathname],
  );

  /* ── Module override: user clicks rail icon ── */
  const [overrideModule, setOverrideModule] = useState(null);
  const displayModule = overrideModule || activeModule;

  /* Reset override when route changes to a different module */
  useEffect(() => {
    setOverrideModule(null);
  }, [activeModule]);

  const handleSelectModule = useCallback((key) => {
    setOverrideModule((prev) => (prev === key ? null : key));
  }, []);

  /* ── Pins ── */
  const [pins, setPins] = useState(() => loadJSON(PINS_KEY, []));

  const togglePin = useCallback((path) => {
    setPins((prev) => {
      const next = prev.includes(path)
        ? prev.filter((p) => p !== path)
        : prev.length < MAX_PINS ? [...prev, path] : prev;
      saveJSON(PINS_KEY, next);
      return next;
    });
  }, []);

  /* ── Badges ── */
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);

  useEffect(() => {
    getNotificationsSummary()
      .then((s) => setAlertBadge(s.new_critical + s.new_warn))
      .catch(() => {});
    getMonitoringAlerts(null, 'open', 200)
      .then((alerts) => setMonitoringBadge(Array.isArray(alerts) ? alerts.length : 0))
      .catch(() => {});
  }, []);

  const badges = useMemo(
    () => ({ alerts: alertBadge, monitoring: monitoringBadge }),
    [alertBadge, monitoringBadge],
  );

  /* ── Track recents on route change ── */
  useEffect(() => {
    const path = location.pathname;
    const isNavItem = ALL_NAV_ITEMS.some((item) =>
      path === item.to || path.startsWith(item.to + '/')
    );
    if (isNavItem) {
      addRecent(path);
    }
  }, [location.pathname]);

  return (
    // ── Z-index layer map ─────────────────────────────────────────────────────
    // z-30     Sidebar aside   (sticky, left column)
    // z-40     App header      (AppShell.jsx — sticky top-0 backdrop-blur-md)
    // z-[120]  Overlays        (dropdowns/popovers/tooltips — portal to body)
    // z-[200]  Modals          (full-screen overlays — portal to body)
    // ─────────────────────────────────────────────────────────────────────────
    <aside className="flex h-screen sticky top-0 z-30 shrink-0" aria-label="Navigation principale">
      <NavRail
        activeModule={displayModule}
        onSelectModule={handleSelectModule}
      />
      <NavPanel
        activeModule={displayModule}
        pins={pins}
        onTogglePin={togglePin}
        badges={badges}
      />
    </aside>
  );
}
