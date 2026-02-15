/**
 * PROMEOS — navRecent utility tests
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getRecents, addRecent, clearRecents } from '../navRecent';

/* Mock localStorage for Node test environment */
const store = {};
const localStorageMock = {
  getItem: vi.fn((key) => store[key] ?? null),
  setItem: vi.fn((key, val) => { store[key] = val; }),
  removeItem: vi.fn((key) => { delete store[key]; }),
};
vi.stubGlobal('localStorage', localStorageMock);

beforeEach(() => {
  Object.keys(store).forEach((k) => delete store[k]);
  vi.clearAllMocks();
});

describe('getRecents', () => {
  it('returns empty array when nothing stored', () => {
    expect(getRecents()).toEqual([]);
  });

  it('returns stored array', () => {
    store['promeos.nav.recent'] = JSON.stringify(['/actions', '/conformite']);
    expect(getRecents()).toEqual(['/actions', '/conformite']);
  });

  it('returns empty array on corrupt JSON', () => {
    store['promeos.nav.recent'] = 'not-json{{{';
    expect(getRecents()).toEqual([]);
  });
});

describe('addRecent', () => {
  it('adds a path', () => {
    const result = addRecent('/actions');
    expect(result).toEqual(['/actions']);
  });

  it('prepends new paths (most recent first)', () => {
    addRecent('/actions');
    const result = addRecent('/conformite');
    expect(result).toEqual(['/conformite', '/actions']);
  });

  it('deduplicates and moves to front', () => {
    addRecent('/actions');
    addRecent('/conformite');
    const result = addRecent('/actions');
    expect(result).toEqual(['/actions', '/conformite']);
  });

  it('limits to 5 recents', () => {
    addRecent('/a');
    addRecent('/b');
    addRecent('/c');
    addRecent('/d');
    addRecent('/e');
    const result = addRecent('/f');
    expect(result).toHaveLength(5);
    expect(result[0]).toBe('/f');
    expect(result).not.toContain('/a');
  });

  it('persists to localStorage', () => {
    addRecent('/actions');
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'promeos.nav.recent',
      JSON.stringify(['/actions']),
    );
  });
});

describe('clearRecents', () => {
  it('removes recents from storage', () => {
    addRecent('/actions');
    clearRecents();
    expect(getRecents()).toEqual([]);
  });

  it('calls removeItem on localStorage', () => {
    clearRecents();
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('promeos.nav.recent');
  });
});
