/**
 * PROMEOS — Recent Navigation Tracking
 * Persists last 5 visited nav paths in localStorage.
 * Pure functions, no React dependency.
 *
 * V2: Stores objects {path, label, module} instead of plain strings
 * for contextualized display (module badge, dynamic route labels).
 * Backward-compatible: reads old string[] format gracefully.
 */
const STORAGE_KEY = 'promeos.nav.recent';
const MAX_RECENTS = 5;

/**
 * @returns {Array<{path: string, label?: string, module?: string}>}
 */
export function getRecents() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    // Backward compat: migrate old string[] to object[]
    return raw.map((entry) =>
      typeof entry === 'string' ? { path: entry } : entry
    );
  } catch {
    return [];
  }
}

/** @returns {string[]} — flat list of recent paths (for compatibility) */
export function getRecentPaths() {
  return getRecents().map((r) => r.path);
}

/**
 * Add a recent entry. Deduplicates by path, prepends, limits to MAX_RECENTS.
 * @param {string} path
 * @param {{ label?: string, module?: string }} meta — optional label + module
 */
export function addRecent(path, meta = {}) {
  const recents = getRecents();
  const entry = { path, ...meta };
  const updated = [entry, ...recents.filter((r) => r.path !== path)].slice(0, MAX_RECENTS);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function clearRecents() {
  localStorage.removeItem(STORAGE_KEY);
}
