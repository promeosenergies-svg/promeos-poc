/**
 * PROMEOS - Mini analytics tracker
 * Tracks: route_change, filter_apply, row_click, anomaly_open, action_create,
 *         scope_change, view_save, bulk_action, export_csv
 * Storage: console.log + localStorage ring buffer (last 200 events).
 */

const STORAGE_KEY = 'promeos_tracker';
const MAX_EVENTS = 200;

function loadEvents() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch { return []; }
}

function persistEvents(events) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
}

export function track(event, data = {}) {
  const entry = {
    event,
    timestamp: new Date().toISOString(),
    path: window.location.pathname,
    ...data,
  };

  if (import.meta.env.DEV) {
    console.log(`[tracker] ${event}`, data);
  }

  const events = loadEvents();
  events.push(entry);
  persistEvents(events);
}

export function getTrackerEvents() {
  return loadEvents();
}

export function clearTrackerEvents() {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Hook: track route changes automatically.
 * Call in App or AppShell via useEffect.
 */
export function trackRouteChange(pathname) {
  track('route_change', { to: pathname });
}
