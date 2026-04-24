/**
 * PROMEOS — SolPanel pinned items
 *
 * Stockage : localStorage key `promeos.nav.pins` · array string[]
 * Limite : 5 items max, FIFO drop du plus ancien
 *
 * Design : pure functions, zéro dépendance React. Les consommateurs
 * (SolPanel) forcent le re-render via un state "version".
 */

const STORAGE_KEY = 'promeos.nav.pins';
const MAX_PINS = 5;

function safeRead() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((s) => typeof s === 'string' && s.length > 0) : [];
  } catch {
    return [];
  }
}

function safeWrite(pins) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pins));
  } catch (err) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn('[navPins] localStorage write failed', err);
    }
  }
}

/** @returns {string[]} */
export function getPins() {
  return safeRead();
}

/**
 * Idempotent. Dédup. FIFO drop si > MAX_PINS.
 * @param {string} itemKey — généralement `item.to`
 * @returns {string[]} liste mise à jour
 */
export function addPin(itemKey) {
  if (!itemKey || typeof itemKey !== 'string') return safeRead();
  const current = safeRead();
  if (current.includes(itemKey)) return current;
  const next = [itemKey, ...current].slice(0, MAX_PINS);
  safeWrite(next);
  return next;
}

/** @returns {string[]} */
export function removePin(itemKey) {
  const current = safeRead();
  const next = current.filter((k) => k !== itemKey);
  safeWrite(next);
  return next;
}

/** @returns {string[]} */
export function togglePin(itemKey) {
  return isPinned(itemKey) ? removePin(itemKey) : addPin(itemKey);
}

/** @returns {boolean} */
export function isPinned(itemKey) {
  return safeRead().includes(itemKey);
}

export function clearPins() {
  safeWrite([]);
}

export const PINS_MAX = MAX_PINS;
export const PINS_STORAGE_KEY = STORAGE_KEY;
