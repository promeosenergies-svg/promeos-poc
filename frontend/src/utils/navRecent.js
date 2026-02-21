/**
 * PROMEOS — Recent Navigation Tracking
 * Persists last 5 visited nav paths in localStorage.
 * Pure functions, no React dependency.
 */
const STORAGE_KEY = 'promeos.nav.recent';
const MAX_RECENTS = 5;

export function getRecents() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

export function addRecent(path) {
  const recents = getRecents();
  const updated = [path, ...recents.filter((p) => p !== path)].slice(0, MAX_RECENTS);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function clearRecents() {
  localStorage.removeItem(STORAGE_KEY);
}
