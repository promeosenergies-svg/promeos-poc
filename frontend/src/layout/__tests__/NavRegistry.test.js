/**
 * PROMEOS — NavRegistry Tests (Rail + Panel Architecture)
 * Covers: modules, sections, route mapping, expert filtering,
 *         helpers (getSectionsForModule, resolveModule), structure integrity.
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_MODULES,
  NAV_SECTIONS,
  MODULE_TINTS,
  ROUTE_MODULE_MAP,
  ALL_NAV_ITEMS,
  getSectionsForModule,
  resolveModule,
} from '../NavRegistry';

/* ── Module definitions ── */
describe('NAV_MODULES', () => {
  it('has exactly 5 modules', () => {
    expect(NAV_MODULES).toHaveLength(5);
  });

  it('modules are in correct order', () => {
    const keys = NAV_MODULES.map((m) => m.key);
    expect(keys).toEqual(['cockpit', 'operations', 'analyse', 'marche', 'donnees']);
  });

  it('order field is sequential 1-5', () => {
    const orders = NAV_MODULES.map((m) => m.order);
    expect(orders).toEqual([1, 2, 3, 4, 5]);
  });

  it('each module has icon, label, tint, expertOnly', () => {
    for (const mod of NAV_MODULES) {
      expect(mod.icon).toBeDefined();
      expect(typeof mod.label).toBe('string');
      expect(mod.label.length).toBeGreaterThan(0);
      expect(typeof mod.tint).toBe('string');
      expect(typeof mod.expertOnly).toBe('boolean');
    }
  });

  it('normal mode shows 3 modules', () => {
    const normal = NAV_MODULES.filter((m) => !m.expertOnly);
    expect(normal).toHaveLength(3);
    expect(normal.map((m) => m.key)).toEqual(['cockpit', 'operations', 'analyse']);
  });

  it('expert mode adds 2 modules (marche, donnees)', () => {
    const expert = NAV_MODULES.filter((m) => m.expertOnly);
    expect(expert).toHaveLength(2);
    expect(expert.map((m) => m.key)).toEqual(['marche', 'donnees']);
  });
});

/* ── Module tints ── */
describe('MODULE_TINTS', () => {
  it('has a tint for every module', () => {
    for (const mod of NAV_MODULES) {
      expect(MODULE_TINTS[mod.key]).toBeDefined();
    }
  });

  it('each tint is a gradient class string', () => {
    for (const [, tint] of Object.entries(MODULE_TINTS)) {
      expect(tint).toMatch(/^from-/);
      expect(tint).toContain('to-transparent');
    }
  });
});

/* ── Section definitions ── */
describe('NAV_SECTIONS', () => {
  it('has exactly 6 sections', () => {
    expect(NAV_SECTIONS).toHaveLength(6);
  });

  it('sections have correct labels and order', () => {
    const labels = NAV_SECTIONS.map((s) => s.label);
    expect(labels).toEqual([
      'Piloter',
      'Executer',
      'Analyser',
      'Marche & Factures',
      'Donnees',
      'Administration',
    ]);
  });

  it('order field is sequential 1-6', () => {
    const orders = NAV_SECTIONS.map((s) => s.order);
    expect(orders).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it('each section has a unique key', () => {
    const keys = NAV_SECTIONS.map((s) => s.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it('every section references a valid module', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const section of NAV_SECTIONS) {
      expect(moduleKeys).toContain(section.module);
    }
  });

  it('donnees module has 2 sections (donnees + admin)', () => {
    const donneesSections = NAV_SECTIONS.filter((s) => s.module === 'donnees');
    expect(donneesSections).toHaveLength(2);
    expect(donneesSections.map((s) => s.key)).toEqual(['donnees', 'admin']);
  });
});

/* ── Expert filtering ── */
describe('Expert filtering', () => {
  const normalSections = NAV_SECTIONS.filter((s) => !s.expertOnly);
  const expertSections = NAV_SECTIONS.filter((s) => s.expertOnly);

  it('normal mode shows 3 sections', () => {
    expect(normalSections).toHaveLength(3);
    expect(normalSections.map((s) => s.key)).toEqual(['cockpit', 'operations', 'analyse']);
  });

  it('expert mode adds 3 sections', () => {
    expect(expertSections).toHaveLength(3);
    expect(expertSections.map((s) => s.key)).toEqual(['marche', 'donnees', 'admin']);
  });

  it('normal mode shows ~8 items (excluding expertOnly items)', () => {
    const normalItems = normalSections.flatMap((s) =>
      s.items.filter((item) => !item.expertOnly)
    );
    expect(normalItems.length).toBeGreaterThanOrEqual(7);
    expect(normalItems.length).toBeLessThanOrEqual(9);
  });

  it('Diagnostic is expertOnly within Analyser', () => {
    const analyse = NAV_SECTIONS.find((s) => s.key === 'analyse');
    const diag = analyse.items.find((item) => item.to === '/diagnostic-conso');
    expect(diag).toBeDefined();
    expect(diag.expertOnly).toBe(true);
  });

  it('admin items are expertOnly + requireAdmin', () => {
    const admin = NAV_SECTIONS.find((s) => s.key === 'admin');
    const iamItems = admin.items.filter((item) => item.requireAdmin);
    expect(iamItems.length).toBeGreaterThanOrEqual(4);
    for (const item of iamItems) {
      expect(item.expertOnly).toBe(true);
      expect(item.requireAdmin).toBe(true);
    }
  });
});

/* ── Route mapping ── */
describe('Route mapping', () => {
  it('every nav item route exists in ROUTE_MODULE_MAP', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(ROUTE_MODULE_MAP).toHaveProperty(item.to);
    }
  });

  it('no duplicate routes across sections', () => {
    const routes = ALL_NAV_ITEMS.map((item) => item.to);
    expect(new Set(routes).size).toBe(routes.length);
  });

  it('ROUTE_MODULE_MAP values are valid module keys', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const [, module] of Object.entries(ROUTE_MODULE_MAP)) {
      expect(moduleKeys).toContain(module);
    }
  });

  it('every item has icon, label, and keywords', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(item.icon).toBeDefined();
      expect(typeof item.label).toBe('string');
      expect(item.label.length).toBeGreaterThan(0);
      expect(Array.isArray(item.keywords)).toBe(true);
      expect(item.keywords.length).toBeGreaterThan(0);
    }
  });
});

/* ── getSectionsForModule helper ── */
describe('getSectionsForModule', () => {
  it('returns sections for cockpit module', () => {
    const sections = getSectionsForModule('cockpit');
    expect(sections).toHaveLength(1);
    expect(sections[0].key).toBe('cockpit');
  });

  it('returns 2 sections for donnees module', () => {
    const sections = getSectionsForModule('donnees');
    expect(sections).toHaveLength(2);
    expect(sections.map((s) => s.key)).toEqual(['donnees', 'admin']);
  });

  it('returns empty array for unknown module', () => {
    const sections = getSectionsForModule('nonexistent');
    expect(sections).toHaveLength(0);
  });

  it('returns sections for every module', () => {
    for (const mod of NAV_MODULES) {
      const sections = getSectionsForModule(mod.key);
      expect(sections.length).toBeGreaterThanOrEqual(1);
    }
  });
});

/* ── resolveModule helper ── */
describe('resolveModule', () => {
  it('resolves exact routes', () => {
    expect(resolveModule('/')).toBe('cockpit');
    expect(resolveModule('/conformite')).toBe('operations');
    expect(resolveModule('/consommations')).toBe('analyse');
    expect(resolveModule('/bill-intel')).toBe('marche');
    expect(resolveModule('/import')).toBe('donnees');
  });

  it('resolves sub-routes by prefix', () => {
    expect(resolveModule('/consommations/explorer')).toBe('analyse');
    expect(resolveModule('/consommations/import')).toBe('analyse');
    expect(resolveModule('/admin/users')).toBe('donnees');
    expect(resolveModule('/admin/audit')).toBe('donnees');
  });

  it('falls back to cockpit for unknown routes', () => {
    expect(resolveModule('/unknown')).toBe('cockpit');
    expect(resolveModule('/random/deep/path')).toBe('cockpit');
  });
});

/* ── IA coherence ── */
describe('IA coherence', () => {
  it('Performance is next to Consommations in Analyser', () => {
    const analyse = NAV_SECTIONS.find((s) => s.key === 'analyse');
    const consoIdx = analyse.items.findIndex((item) => item.to === '/consommations');
    const perfIdx = analyse.items.findIndex((item) => item.to === '/monitoring');
    expect(consoIdx).toBeGreaterThanOrEqual(0);
    expect(perfIdx).toBe(consoIdx + 1);
  });

  it('Cockpit has Alertes with badge', () => {
    const cockpit = NAV_SECTIONS.find((s) => s.key === 'cockpit');
    const alertes = cockpit.items.find((item) => item.to === '/notifications');
    expect(alertes).toBeDefined();
    expect(alertes.badgeKey).toBe('alerts');
  });

  it('Analyse has Patrimoine', () => {
    const analyse = NAV_SECTIONS.find((s) => s.key === 'analyse');
    const patrimoine = analyse.items.find((item) => item.to === '/patrimoine');
    expect(patrimoine).toBeDefined();
  });

  it('ALL_NAV_ITEMS has section and module for each item', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(typeof item.section).toBe('string');
      expect(item.section.length).toBeGreaterThan(0);
      expect(typeof item.module).toBe('string');
      expect(item.module.length).toBeGreaterThan(0);
    }
  });
});
