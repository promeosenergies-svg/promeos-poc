/**
 * PROMEOS - Mini analytics tracker
 * Tracks: route_change, filter_apply, row_click, anomaly_open, action_create,
 *         scope_change, view_save, bulk_action, export_csv, nav_panel_opened,
 *         nav_deep_link_click, aper_filter_applied, anomaly_filter_applied,
 *         renouvellements_horizon_selected
 * Storage: console.log + localStorage ring buffer (last 200 events).
 */

const STORAGE_KEY = 'promeos_tracker';
const MAX_EVENTS = 200;

// Whitelist des query keys trackables dans `href` payload. Toute autre
// clé est stripped pour éviter PII leak localStorage (ex. ?site_id=123,
// ?email=x@y.z persistés sur poste partagé).
const SAFE_QUERY_KEYS = new Set([
  'tab',
  'filter',
  'horizon',
  'fw', // framework anomaly
  'source',
  'actionCenter',
  'wizard',
  'focus',
]);

function sanitizeHref(href) {
  if (typeof href !== 'string') return href;
  const queryStart = href.indexOf('?');
  if (queryStart === -1) return href;
  const base = href.slice(0, queryStart);
  const query = href.slice(queryStart + 1);
  try {
    const params = new URLSearchParams(query);
    const safeParams = new URLSearchParams();
    for (const [key, value] of params.entries()) {
      if (SAFE_QUERY_KEYS.has(key)) {
        safeParams.append(key, value);
      }
    }
    const safeQuery = safeParams.toString();
    return safeQuery ? `${base}?${safeQuery}` : base;
  } catch {
    return base;
  }
}

function loadEvents() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function persistEvents(events) {
  // try/catch obligatoire : Safari Private Mode / quota exceeded /
  // localStorage disabled — mieux drop des events que throw.
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
  } catch {
    /* noop */
  }
}

export function track(event, data = {}) {
  const safeData = 'href' in data ? { ...data, href: sanitizeHref(data.href) } : data;

  const entry = {
    event,
    timestamp: new Date().toISOString(),
    path: window.location.pathname,
    ...safeData,
  };

  if (import.meta.env.DEV) {
    console.log(`[tracker] ${event}`, safeData);
  }

  const events = loadEvents();
  events.push(entry);
  persistEvents(events);
}

export function getTrackerEvents() {
  return loadEvents();
}

export function clearTrackerEvents() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Hook: track route changes automatically.
 * Call in App or AppShell via useEffect.
 */
export function trackRouteChange(pathname) {
  track('route_change', { to: pathname });
}
