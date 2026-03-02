/**
 * PROMEOS — Recents integration tests
 * Covers: deduplication, cross-module badge, FR labels, no duplicates.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getRecents, addRecent, clearRecents, getRecentPaths } from '../../utils/navRecent';
import { matchRouteToModule, NAV_MODULES, ALL_NAV_ITEMS } from '../NavRegistry';

/* Mock localStorage */
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

/* ── No duplicate paths ── */
describe('recents — deduplication', () => {
  it('does not show the same path twice', () => {
    addRecent('/actions', { label: "Plan d'actions", module: 'operations' });
    addRecent('/conformite', { label: 'Conformité', module: 'operations' });
    addRecent('/actions', { label: "Plan d'actions", module: 'operations' }); // re-visit
    const paths = getRecentPaths();
    expect(paths).toEqual(['/actions', '/conformite']);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('dynamic routes are also deduplicated', () => {
    addRecent('/sites/42', { label: 'Site #42', module: 'admin' });
    addRecent('/sites/42', { label: 'Site #42', module: 'admin' }); // re-visit same site
    expect(getRecentPaths()).toEqual(['/sites/42']);
  });
});

/* ── Cross-module detection ── */
describe('recents — cross-module badge', () => {
  it('marks correct module for cross-module items', () => {
    addRecent('/actions', { label: "Plan d'actions", module: 'operations' });
    addRecent('/patrimoine', { label: 'Patrimoine', module: 'admin' });

    const recents = getRecents();
    // If current module is 'cockpit', both should be marked as cross-module
    const currentModule = 'cockpit';
    for (const r of recents) {
      const isCross = r.module && r.module !== currentModule;
      expect(isCross).toBe(true);
    }
  });

  it('same-module items are not marked as cross-module', () => {
    addRecent('/conformite', { label: 'Conformité', module: 'operations' });
    addRecent('/actions', { label: "Plan d'actions", module: 'operations' });

    const currentModule = 'operations';
    for (const r of getRecents()) {
      expect(r.module === currentModule).toBe(true);
    }
  });
});

/* ── Dynamic routes produce valid module metadata ── */
describe('recents — dynamic route module resolution', () => {
  const dynamicPaths = [
    { path: '/sites/42', expectedModule: 'admin' },
    { path: '/actions/123', expectedModule: 'operations' },
    { path: '/conformite/tertiaire/efa/5', expectedModule: 'operations' },
    { path: '/compliance/sites/99', expectedModule: 'operations' },
  ];

  for (const { path, expectedModule } of dynamicPaths) {
    it(`${path} resolves to module ${expectedModule}`, () => {
      const { moduleId } = matchRouteToModule(path);
      addRecent(path, { label: `Test ${path}`, module: moduleId });
      const recent = getRecents()[0];
      expect(recent.module).toBe(expectedModule);
      // Module must be a valid NAV_MODULES key
      expect(NAV_MODULES.map((m) => m.key)).toContain(recent.module);
    });
  }
});

/* ── Static nav items always have labels ── */
describe('recents — label integrity', () => {
  it('static nav items have FR labels when stored as recents', () => {
    for (const item of ALL_NAV_ITEMS.slice(0, 10)) {
      addRecent(item.to, { label: item.label, module: item.module });
    }
    for (const r of getRecents()) {
      expect(r.label).toBeTruthy();
      expect(r.label.length).toBeGreaterThan(0);
    }
  });
});
