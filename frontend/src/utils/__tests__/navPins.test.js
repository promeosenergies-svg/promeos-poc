/**
 * navPins — unit tests (Sprint 1 Vague B · B1.2)
 * Couvre : CRUD, dédup, FIFO drop, corruption-safe, input sanitization.
 *
 * Environnement vitest = 'node' (pas de localStorage natif), donc on
 * mocke un localStorage in-memory minimaliste avant les imports.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock localStorage avant l'import du module testé
if (typeof globalThis.localStorage === 'undefined') {
  const store = new Map();
  globalThis.localStorage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
    clear: () => store.clear(),
    key: (i) => Array.from(store.keys())[i] ?? null,
    get length() {
      return store.size;
    },
  };
}

const { getPins, addPin, removePin, togglePin, isPinned, clearPins, PINS_MAX, PINS_STORAGE_KEY } =
  await import('../navPins');

describe('navPins', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns empty array when no pins stored', () => {
    expect(getPins()).toEqual([]);
  });

  it('addPin stores item and returns updated list', () => {
    const result = addPin('/conformite');
    expect(result).toEqual(['/conformite']);
    expect(getPins()).toEqual(['/conformite']);
  });

  it('addPin is idempotent (duplicate ignored)', () => {
    addPin('/a');
    addPin('/a');
    expect(getPins()).toEqual(['/a']);
  });

  it('addPin respects PINS_MAX with FIFO drop of oldest', () => {
    for (let i = 0; i < PINS_MAX + 2; i++) {
      addPin(`/item-${i}`);
    }
    const pins = getPins();
    expect(pins).toHaveLength(PINS_MAX);
    // Le plus récent est en tête
    expect(pins[0]).toBe(`/item-${PINS_MAX + 1}`);
    // Les 2 plus anciens ont été droppés
    expect(pins).not.toContain('/item-0');
    expect(pins).not.toContain('/item-1');
  });

  it('removePin removes item and returns updated list', () => {
    addPin('/a');
    addPin('/b');
    const result = removePin('/a');
    expect(result).toEqual(['/b']);
    expect(getPins()).toEqual(['/b']);
  });

  it('removePin is a no-op on absent item', () => {
    addPin('/a');
    removePin('/not-pinned');
    expect(getPins()).toEqual(['/a']);
  });

  it('togglePin adds when absent, removes when present', () => {
    expect(togglePin('/a')).toEqual(['/a']);
    expect(togglePin('/a')).toEqual([]);
  });

  it('isPinned reflects current state', () => {
    expect(isPinned('/x')).toBe(false);
    addPin('/x');
    expect(isPinned('/x')).toBe(true);
    removePin('/x');
    expect(isPinned('/x')).toBe(false);
  });

  it('clearPins empties storage', () => {
    addPin('/a');
    addPin('/b');
    clearPins();
    expect(getPins()).toEqual([]);
  });

  it('uses stable localStorage key `promeos.nav.pins`', () => {
    expect(PINS_STORAGE_KEY).toBe('promeos.nav.pins');
    addPin('/foo');
    expect(localStorage.getItem(PINS_STORAGE_KEY)).toBe('["/foo"]');
  });

  it('handles corrupt localStorage gracefully (invalid JSON)', () => {
    localStorage.setItem(PINS_STORAGE_KEY, '{invalid json}');
    expect(getPins()).toEqual([]);
  });

  it('handles non-array stored content gracefully', () => {
    localStorage.setItem(PINS_STORAGE_KEY, '{"not":"an array"}');
    expect(getPins()).toEqual([]);
  });

  it('filters out non-string items from stored array', () => {
    localStorage.setItem(PINS_STORAGE_KEY, JSON.stringify(['/a', 42, null, '/b', '']));
    // 42, null, '' sont filtrés
    expect(getPins()).toEqual(['/a', '/b']);
  });

  it('rejects non-string itemKey in addPin (input sanitization)', () => {
    addPin(null);
    addPin(undefined);
    addPin(42);
    addPin({});
    addPin('');
    expect(getPins()).toEqual([]);
  });

  it('PINS_MAX is 5 (matches V7 NavPanel legacy)', () => {
    expect(PINS_MAX).toBe(5);
  });
});
