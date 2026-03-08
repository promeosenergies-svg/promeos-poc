/**
 * PROMEOS — NavRegistry Tests (Rail + Panel Architecture)
 * Covers: modules, sections, route mapping, expert filtering,
 *         helpers, quick actions, sidebar tints, structure integrity,
 *         5-module rule, Patrimoine in Admin, IA coherence.
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_MODULES,
  NAV_SECTIONS,
  MODULE_TINTS,
  ROUTE_MODULE_MAP,
  ALL_NAV_ITEMS,
  QUICK_ACTIONS,
  SECTION_TINTS,
  SIDEBAR_ITEM_TINTS,
  TINT_PALETTE,
  getSectionsForModule,
  resolveModule,
  matchRouteToModule,
  getModuleTint,
} from '../NavRegistry';

/* ── Module definitions ── */
describe('NAV_MODULES', () => {
  it('has exactly 5 modules', () => {
    expect(NAV_MODULES).toHaveLength(5);
  });

  it('modules are in correct order', () => {
    const keys = NAV_MODULES.map((m) => m.key);
    expect(keys).toEqual(['pilotage', 'patrimoine', 'energie', 'achat', 'admin']);
  });

  it('order field is sequential 1-5', () => {
    const orders = NAV_MODULES.map((m) => m.order);
    expect(orders).toEqual([1, 2, 3, 4, 5]);
  });

  it('each module has icon, label, tint, expertOnly, desc', () => {
    for (const mod of NAV_MODULES) {
      expect(mod.icon).toBeDefined();
      expect(typeof mod.label).toBe('string');
      expect(mod.label.length).toBeGreaterThan(0);
      expect(typeof mod.tint).toBe('string');
      expect(typeof mod.expertOnly).toBe('boolean');
      expect(typeof mod.desc).toBe('string');
      expect(mod.desc.length).toBeGreaterThan(0);
    }
  });

  it('normal mode shows 4 modules', () => {
    const normal = NAV_MODULES.filter((m) => !m.expertOnly);
    expect(normal).toHaveLength(4);
    expect(normal.map((m) => m.key)).toEqual(['pilotage', 'patrimoine', 'energie', 'achat']);
  });

  it('expert mode adds 1 module (admin)', () => {
    const expert = NAV_MODULES.filter((m) => m.expertOnly);
    expect(expert).toHaveLength(1);
    expect(expert.map((m) => m.key)).toEqual(['admin']);
  });

  it('5-module rule: no more than 5 modules allowed', () => {
    expect(NAV_MODULES.length).toBeLessThanOrEqual(5);
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
  it('has exactly 5 sections', () => {
    expect(NAV_SECTIONS).toHaveLength(5);
  });

  it('sections have correct labels and order', () => {
    const labels = NAV_SECTIONS.map((s) => s.label);
    expect(labels).toEqual([
      'Pilotage',
      'Patrimoine',
      'Énergie',
      'Achat',
      'Données',
    ]);
  });

  it('order field is sequential 1-5', () => {
    const orders = NAV_SECTIONS.map((s) => s.order);
    expect(orders).toEqual([1, 2, 3, 4, 5]);
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

  it('admin module has 1 section (admin-data)', () => {
    const adminSections = NAV_SECTIONS.filter((s) => s.module === 'admin');
    expect(adminSections).toHaveLength(1);
    expect(adminSections.map((s) => s.key)).toEqual(['admin-data']);
  });
});

/* ── Expert filtering ── */
describe('Expert filtering', () => {
  const normalSections = NAV_SECTIONS.filter((s) => !s.expertOnly);
  const expertSections = NAV_SECTIONS.filter((s) => s.expertOnly);

  it('normal mode shows 4 sections', () => {
    expect(normalSections).toHaveLength(4);
    expect(normalSections.map((s) => s.key)).toEqual(['pilotage', 'patrimoine', 'energie', 'achat']);
  });

  it('expert mode adds 1 section', () => {
    expect(expertSections).toHaveLength(1);
    expect(expertSections.map((s) => s.key)).toEqual([
      'admin-data',
    ]);
  });

  it('normal mode shows ~9 items (excluding expertOnly items)', () => {
    const normalItems = normalSections.flatMap((s) => s.items.filter((item) => !item.expertOnly));
    expect(normalItems.length).toBeGreaterThanOrEqual(5);
    expect(normalItems.length).toBeLessThanOrEqual(12);
  });

  it('Diagnostic is in ROUTE_MODULE_MAP as energie (hidden page)', () => {
    expect(ROUTE_MODULE_MAP['/diagnostic-conso']).toBe('energie');
  });

  it('admin-data section has requireAdmin items', () => {
    const adminData = NAV_SECTIONS.find((s) => s.key === 'admin-data');
    const adminItems = adminData.items.filter((item) => item.requireAdmin);
    expect(adminItems.length).toBeGreaterThanOrEqual(1);
    for (const item of adminItems) {
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
  it('returns sections for pilotage module', () => {
    const sections = getSectionsForModule('pilotage');
    expect(sections).toHaveLength(1);
    expect(sections[0].key).toBe('pilotage');
  });

  it('returns 1 section for admin module', () => {
    const sections = getSectionsForModule('admin');
    expect(sections).toHaveLength(1);
    expect(sections.map((s) => s.key)).toEqual(['admin-data']);
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
    expect(resolveModule('/')).toBe('pilotage');
    expect(resolveModule('/conformite')).toBe('patrimoine');
    expect(resolveModule('/consommations')).toBe('energie');
    expect(resolveModule('/bill-intel')).toBe('energie');
    expect(resolveModule('/import')).toBe('admin');
    expect(resolveModule('/patrimoine')).toBe('patrimoine');
  });

  it('resolves sub-routes by prefix', () => {
    expect(resolveModule('/consommations/explorer')).toBe('energie');
    expect(resolveModule('/consommations/import')).toBe('energie');
    expect(resolveModule('/admin/users')).toBe('admin');
    expect(resolveModule('/admin/audit')).toBe('admin');
  });

  it('falls back to cockpit for unknown routes', () => {
    expect(resolveModule('/unknown')).toBe('cockpit');
    expect(resolveModule('/random/deep/path')).toBe('cockpit');
  });
});

/* ── IA coherence ── */
describe('IA coherence', () => {
  it('Performance is next to Consommations in Énergie', () => {
    const energie = NAV_SECTIONS.find((s) => s.key === 'energie');
    const consoIdx = energie.items.findIndex((item) => item.to === '/consommations');
    const perfIdx = energie.items.findIndex((item) => item.to === '/monitoring');
    expect(consoIdx).toBeGreaterThanOrEqual(0);
    expect(perfIdx).toBe(consoIdx + 1);
  });

  it("Actions & Suivi has alerts badge in Pilotage", () => {
    const pilotage = NAV_SECTIONS.find((s) => s.key === 'pilotage');
    const centre = pilotage.items.find((item) => item.to === '/actions');
    expect(centre).toBeDefined();
    expect(centre.badgeKey).toBe('alerts');
    expect(centre.label).toBe("Actions & Suivi");
  });

  it('Patrimoine lives in Patrimoine module (patrimoine section)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.key === 'patrimoine');
    expect(patrimoine.module).toBe('patrimoine');
    const patrimoineItem = patrimoine.items.find((item) => item.to === '/patrimoine');
    expect(patrimoineItem).toBeDefined();
  });

  it('Patrimoine is first item in patrimoine section', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.key === 'patrimoine');
    expect(patrimoine.items[0].to).toBe('/patrimoine');
  });

  it('Patrimoine is NOT in Énergie section', () => {
    const energie = NAV_SECTIONS.find((s) => s.key === 'energie');
    const patrimoine = energie.items.find((item) => item.to === '/patrimoine');
    expect(patrimoine).toBeUndefined();
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

/* ── Quick Actions ── */
describe('QUICK_ACTIONS', () => {
  it('has exactly 14 quick actions', () => {
    expect(QUICK_ACTIONS).toHaveLength(14);
  });

  it('each action has key, label, icon, to', () => {
    for (const action of QUICK_ACTIONS) {
      expect(typeof action.key).toBe('string');
      expect(typeof action.label).toBe('string');
      expect(action.icon).toBeDefined();
      expect(typeof action.to).toBe('string');
    }
  });

  it('all quick action base routes resolve to a valid module', () => {
    for (const action of QUICK_ACTIONS) {
      const basePath = action.to.split('?')[0];
      const { moduleId } = matchRouteToModule(basePath);
      const moduleKeys = NAV_MODULES.map((m) => m.key);
      expect(moduleKeys).toContain(moduleId);
    }
  });
});

/* ── Section tints ── */
describe('SECTION_TINTS', () => {
  it('has a tint for every section', () => {
    for (const section of NAV_SECTIONS) {
      expect(SECTION_TINTS[section.key]).toBeDefined();
    }
  });

  it('tint values are valid SIDEBAR_ITEM_TINTS keys', () => {
    const validTints = Object.keys(SIDEBAR_ITEM_TINTS);
    for (const tint of Object.values(SECTION_TINTS)) {
      expect(validTints).toContain(tint);
    }
  });
});

/* ── Sidebar item tints ── */
describe('SIDEBAR_ITEM_TINTS', () => {
  it('has activeBg, activeText, activeBorder, dot for each tint', () => {
    for (const [, classes] of Object.entries(SIDEBAR_ITEM_TINTS)) {
      expect(typeof classes.activeBg).toBe('string');
      expect(typeof classes.activeText).toBe('string');
      expect(typeof classes.activeBorder).toBe('string');
      expect(typeof classes.dot).toBe('string');
    }
  });

  it('covers all 5 module tints', () => {
    expect(Object.keys(SIDEBAR_ITEM_TINTS)).toEqual(
      expect.arrayContaining(['blue', 'emerald', 'indigo', 'amber', 'slate'])
    );
  });
});

/* ── TINT_PALETTE (Color Life System) ── */
describe('TINT_PALETTE', () => {
  const REQUIRED_KEYS = [
    'headerBand',
    'panelHeader',
    'softBg',
    'hoverBg',
    'activeBg',
    'activeText',
    'activeBorder',
    'railActiveBg',
    'railActiveRing',
    'railActiveText',
    'dot',
    'icon',
    'pillBg',
    'pillText',
    'pillRing',
  ];

  it('has entries for all 5 module tints', () => {
    const tintNames = NAV_MODULES.map((m) => m.tint);
    for (const name of tintNames) {
      expect(TINT_PALETTE[name]).toBeDefined();
    }
  });

  it('each palette entry has all required semantic keys', () => {
    for (const [_name, palette] of Object.entries(TINT_PALETTE)) {
      for (const key of REQUIRED_KEYS) {
        expect(typeof palette[key]).toBe('string');
      }
    }
  });

  it('headerBand values are gradient strings', () => {
    for (const [, p] of Object.entries(TINT_PALETTE)) {
      expect(p.headerBand).toMatch(/^from-/);
      expect(p.headerBand).toContain('to-transparent');
    }
  });

  it('SIDEBAR_ITEM_TINTS is derived from TINT_PALETTE', () => {
    for (const [name, tint] of Object.entries(SIDEBAR_ITEM_TINTS)) {
      expect(tint.activeBg).toBe(TINT_PALETTE[name].activeBg);
      expect(tint.dot).toBe(TINT_PALETTE[name].dot);
    }
  });

  it('MODULE_TINTS is derived from TINT_PALETTE', () => {
    for (const mod of NAV_MODULES) {
      expect(MODULE_TINTS[mod.key]).toBe(TINT_PALETTE[mod.tint].headerBand);
    }
  });
});

/* ── getModuleTint helper ── */
describe('getModuleTint', () => {
  it('returns palette by module key', () => {
    const t = getModuleTint('pilotage');
    expect(t).toBe(TINT_PALETTE.blue);
  });

  it('returns palette by pathname', () => {
    const t = getModuleTint('/conformite');
    expect(t).toBe(TINT_PALETTE.emerald);
  });

  it('falls back to slate for unknown path', () => {
    const t = getModuleTint('/unknown');
    // cockpit fallback — no module with key 'cockpit' so falls to slate
    expect(t).toBe(TINT_PALETTE.slate);
  });

  it('resolves for all routes in ROUTE_MODULE_MAP', () => {
    for (const [path, moduleKey] of Object.entries(ROUTE_MODULE_MAP)) {
      const mod = NAV_MODULES.find((m) => m.key === moduleKey);
      expect(mod).toBeDefined();
      const t = getModuleTint(path);
      expect(t).toBe(TINT_PALETTE[mod.tint]);
    }
  });

  it('every module has exactly one unique tint key', () => {
    const tints = NAV_MODULES.map((m) => m.tint);
    expect(new Set(tints).size).toBe(tints.length);
  });
});

/* ── Route coverage guard-rails ── */
describe('Route coverage guard-rails', () => {
  it('compliance routes resolve to patrimoine', () => {
    expect(resolveModule('/compliance')).toBe('patrimoine');
    expect(resolveModule('/compliance/findings')).toBe('patrimoine');
    expect(resolveModule('/compliance/obligations')).toBe('patrimoine');
  });

  it('consommations/portfolio resolves to energie', () => {
    expect(resolveModule('/consommations/portfolio')).toBe('energie');
  });

  it('no English labels in NAV_SECTIONS items', () => {
    for (const section of NAV_SECTIONS) {
      for (const item of section.items) {
        expect(item.label).not.toMatch(/\bCenter\b/i);
        expect(item.label).not.toMatch(/\bKnowledge Base\b/i);
      }
    }
  });

  it('all nav item routes are in ROUTE_MODULE_MAP', () => {
    const knownRoutes = Object.keys(ROUTE_MODULE_MAP);
    for (const item of ALL_NAV_ITEMS) {
      expect(knownRoutes).toContain(item.to);
    }
  });

  it("actions label is Actions & Suivi (FR)", () => {
    const actions = ALL_NAV_ITEMS.find((item) => item.to === '/actions');
    expect(actions).toBeDefined();
    expect(actions.label).toBe("Actions & Suivi");
  });

  it('dynamic routes resolve correctly (not fallback to cockpit)', () => {
    expect(resolveModule('/sites/42')).toBe('patrimoine');
    expect(resolveModule('/actions/123')).toBe('pilotage');
    expect(resolveModule('/conformite/tertiaire/efa/5')).toBe('patrimoine');
    expect(resolveModule('/compliance/sites/99')).toBe('patrimoine');
  });
});

/* ── V2 Guard-rails: IDs, labels, FR ── */
describe('Guard-rails — IDs and labels', () => {
  it('all nav item routes start with /', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(item.to.startsWith('/')).toBe(true);
    }
  });

  it('no duplicate labels within the same section', () => {
    for (const section of NAV_SECTIONS) {
      const labels = section.items.map((item) => item.label);
      const unique = new Set(labels);
      expect(unique.size).toBe(labels.length);
    }
  });

  it('no English words in nav labels (extended blacklist)', () => {
    const blacklist = [
      'Dashboard',
      'Settings',
      'Home',
      'Center',
      'Knowledge Base',
      'Overview',
      'Reports',
      'Search',
      'Delete',
      'Edit',
      'Create',
      'Submit',
    ];
    for (const item of ALL_NAV_ITEMS) {
      for (const word of blacklist) {
        expect(item.label.toLowerCase()).not.toContain(word.toLowerCase());
      }
    }
  });

  it('matchRouteToModule returns valid moduleLabel for all static routes', () => {
    const validLabels = NAV_MODULES.map((m) => m.label);
    for (const [path] of Object.entries(ROUTE_MODULE_MAP)) {
      if (path.includes(':')) continue; // skip dynamic patterns
      const { moduleLabel } = matchRouteToModule(path);
      expect(validLabels).toContain(moduleLabel);
    }
  });

  it('every section key is unique across all sections', () => {
    const keys = NAV_SECTIONS.map((s) => s.key);
    expect(new Set(keys).size).toBe(keys.length);
  });
});
