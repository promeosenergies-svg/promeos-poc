/**
 * PROMEOS — navRecent utility tests (V2: object format)
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getRecents, getRecentPaths, addRecent, clearRecents } from '../navRecent';

/* Mock localStorage for Node test environment */
const store = {};
const localStorageMock = {
  getItem: vi.fn((key) => store[key] ?? null),
  setItem: vi.fn((key, val) => {
    store[key] = val;
  }),
  removeItem: vi.fn((key) => {
    delete store[key];
  }),
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

  it('returns stored object array', () => {
    store['promeos.nav.recent'] = JSON.stringify([
      { path: '/actions', label: "Plan d'actions", module: 'operations' },
    ]);
    expect(getRecents()).toEqual([
      { path: '/actions', label: "Plan d'actions", module: 'operations' },
    ]);
  });

  it('backward compat: migrates old string[] to object[]', () => {
    store['promeos.nav.recent'] = JSON.stringify(['/actions', '/conformite']);
    const result = getRecents();
    expect(result).toEqual([{ path: '/actions' }, { path: '/conformite' }]);
  });

  it('returns empty array on corrupt JSON', () => {
    store['promeos.nav.recent'] = 'not-json{{{';
    expect(getRecents()).toEqual([]);
  });
});

describe('getRecentPaths', () => {
  it('returns flat path array from object entries', () => {
    addRecent('/actions', { label: 'Actions', module: 'operations' });
    addRecent('/conformite', { label: 'Conformité', module: 'operations' });
    expect(getRecentPaths()).toEqual(['/conformite', '/actions']);
  });
});

describe('addRecent', () => {
  it('adds a path with metadata', () => {
    const result = addRecent('/actions', { label: "Plan d'actions", module: 'operations' });
    expect(result).toEqual([{ path: '/actions', label: "Plan d'actions", module: 'operations' }]);
  });

  it('prepends new paths (most recent first)', () => {
    addRecent('/actions');
    const result = addRecent('/conformite');
    expect(result[0].path).toBe('/conformite');
    expect(result[1].path).toBe('/actions');
  });

  it('deduplicates and moves to front', () => {
    addRecent('/actions');
    addRecent('/conformite');
    const result = addRecent('/actions');
    expect(result.map((r) => r.path)).toEqual(['/actions', '/conformite']);
  });

  it('limits to 5 recents', () => {
    addRecent('/a');
    addRecent('/b');
    addRecent('/c');
    addRecent('/d');
    addRecent('/e');
    const result = addRecent('/f');
    expect(result).toHaveLength(5);
    expect(result[0].path).toBe('/f');
    expect(result.map((r) => r.path)).not.toContain('/a');
  });

  it('persists to localStorage', () => {
    addRecent('/actions', { label: 'Test' });
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'promeos.nav.recent',
      expect.stringContaining('/actions')
    );
  });

  it('works without metadata (backward compat)', () => {
    const result = addRecent('/actions');
    expect(result[0]).toEqual({ path: '/actions' });
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

/* ── Anti saut de contexte ── */
describe('recents context integrity', () => {
  it('stores module metadata for cross-module detection', () => {
    addRecent('/actions', { label: "Plan d'actions", module: 'operations' });
    addRecent('/patrimoine', { label: 'Patrimoine', module: 'admin' });
    const recents = getRecents();
    expect(recents[0].module).toBe('admin');
    expect(recents[1].module).toBe('operations');
  });

  it('never stores duplicate paths', () => {
    addRecent('/actions');
    addRecent('/conformite');
    addRecent('/actions');
    const paths = getRecents().map((r) => r.path);
    expect(new Set(paths).size).toBe(paths.length);
  });
});
