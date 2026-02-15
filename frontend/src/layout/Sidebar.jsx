/**
 * PROMEOS — Sidebar (Rail + Panel)
 * Composes NavRail (icons) + NavPanel (contextual items).
 * Rail always visible; Panel shows for active module.
 * Persists active module + panel visibility in localStorage.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import NavRail from './NavRail';
import NavPanel from './NavPanel';
import { NAV_MODULES, getSectionsForModule, resolveModule } from './NavRegistry';
import { getNotificationsSummary, getMonitoringAlerts } from '../services/api';
import { useExpertMode } from '../contexts/ExpertModeContext';

const MODULE_KEY = 'promeos_active_module';
const PANEL_KEY = 'promeos_panel_open';

export default function Sidebar() {
  const location = useLocation();
  const { isExpert } = useExpertMode();

  /* ── State ── */
  const [activeModule, setActiveModule] = useState(() => {
    const saved = localStorage.getItem(MODULE_KEY);
    return saved || 'cockpit';
  });
  const [panelOpen, setPanelOpen] = useState(() => {
    const saved = localStorage.getItem(PANEL_KEY);
    return saved !== 'false'; // Default open
  });
  const [alertBadge, setAlertBadge] = useState(0);
  const [monitoringBadge, setMonitoringBadge] = useState(0);

  /* ── Fetch badges ── */
  useEffect(() => {
    getNotificationsSummary()
      .then((s) => setAlertBadge(s.new_critical + s.new_warn))
      .catch(() => {});
    getMonitoringAlerts(null, 'open', 200)
      .then((alerts) => setMonitoringBadge(Array.isArray(alerts) ? alerts.length : 0))
      .catch(() => {});
  }, []);

  const badges = { alerts: alertBadge, monitoring: monitoringBadge };

  /* ── Visible modules (expert filter) ── */
  const visibleModules = useMemo(() => {
    return NAV_MODULES.filter((m) => !m.expertOnly || isExpert);
  }, [isExpert]);

  /* ── Auto-select module from route ── */
  useEffect(() => {
    const resolved = resolveModule(location.pathname);
    if (resolved && resolved !== activeModule) {
      // Only auto-switch if the resolved module is visible
      const isVisible = visibleModules.some((m) => m.key === resolved);
      if (isVisible) {
        setActiveModule(resolved);
        localStorage.setItem(MODULE_KEY, resolved);
        if (!panelOpen) {
          setPanelOpen(true);
          localStorage.setItem(PANEL_KEY, 'true');
        }
      }
    }
  }, [location.pathname, visibleModules]); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── Module select handler ── */
  const handleModuleSelect = useCallback((key) => {
    if (key === activeModule) {
      // Toggle panel
      setPanelOpen((prev) => {
        const next = !prev;
        localStorage.setItem(PANEL_KEY, String(next));
        return next;
      });
    } else {
      setActiveModule(key);
      localStorage.setItem(MODULE_KEY, key);
      if (!panelOpen) {
        setPanelOpen(true);
        localStorage.setItem(PANEL_KEY, 'true');
      }
    }
  }, [activeModule, panelOpen]);

  /* ── Has badge for rail dots ── */
  const hasBadge = useCallback((moduleKey) => {
    if (moduleKey === 'cockpit') return alertBadge > 0;
    if (moduleKey === 'analyse') return monitoringBadge > 0;
    return false;
  }, [alertBadge, monitoringBadge]);

  /* ── Sections for active module ── */
  const activeSections = useMemo(() => {
    return getSectionsForModule(activeModule);
  }, [activeModule]);

  const activeModuleDef = visibleModules.find((m) => m.key === activeModule);

  return (
    <aside className="flex h-screen sticky top-0" aria-label="Navigation principale">
      {/* Rail (always visible) */}
      <NavRail
        modules={visibleModules}
        activeModule={activeModule}
        onModuleSelect={handleModuleSelect}
        hasBadge={hasBadge}
      />

      {/* Panel (contextual, toggleable) */}
      {panelOpen && activeModuleDef && (
        <NavPanel
          sections={activeSections}
          moduleLabel={activeModuleDef.label}
          badges={badges}
          onClose={() => {
            setPanelOpen(false);
            localStorage.setItem(PANEL_KEY, 'false');
          }}
        />
      )}
    </aside>
  );
}
