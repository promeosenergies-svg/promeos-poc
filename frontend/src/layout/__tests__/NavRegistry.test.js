/**
 * PROMEOS — NavRegistry Tests V7 (Rail + Panel Architecture)
 * Covers: 6 modules (5 normal + admin expertOnly), conformité autonome,
 *         vocabulaire v7, route mapping, expert filtering au niveau item.
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_MODULES,
  NAV_SECTIONS,
  NAV_MAIN_SECTIONS,
  NAV_ADMIN_ITEMS,
  MODULE_TINTS,
  ROUTE_MODULE_MAP,
  ALL_NAV_ITEMS,
  QUICK_ACTIONS,
  SECTION_TINTS,
  SIDEBAR_ITEM_TINTS,
  TINT_PALETTE,
  getSectionsForModule,
  getVisibleItems,
  resolveModule,
  matchRouteToModule,
  getModuleTint,
} from '../NavRegistry';

/* ── Module definitions V7 ── */
describe('NAV_MODULES V7', () => {
  it('has exactly 6 modules (5 normal + admin expert)', () => {
    expect(NAV_MODULES).toHaveLength(6);
  });

  it('modules are in correct order with correct keys', () => {
    const keys = NAV_MODULES.map((m) => m.key);
    expect(keys).toEqual(['cockpit', 'conformite', 'energie', 'patrimoine', 'achat', 'admin']);
  });

  it('order field is sequential 1-6', () => {
    const orders = NAV_MODULES.map((m) => m.order);
    expect(orders).toEqual([1, 2, 3, 4, 5, 6]);
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

  it('normal mode shows 5 modules (rail stable)', () => {
    const normal = NAV_MODULES.filter((m) => !m.expertOnly);
    expect(normal).toHaveLength(5);
    expect(normal.map((m) => m.key)).toEqual([
      'cockpit',
      'conformite',
      'energie',
      'patrimoine',
      'achat',
    ]);
  });

  it('expert mode adds 1 module (admin)', () => {
    const expert = NAV_MODULES.filter((m) => m.expertOnly);
    expect(expert).toHaveLength(1);
    expect(expert.map((m) => m.key)).toEqual(['admin']);
  });

  it('cockpit module has label "Accueil" (renamed from Pilotage)', () => {
    const cockpit = NAV_MODULES.find((m) => m.key === 'cockpit');
    expect(cockpit.label).toBe('Accueil');
  });

  it('conformite is a standalone module with tint emerald', () => {
    const conformite = NAV_MODULES.find((m) => m.key === 'conformite');
    expect(conformite).toBeDefined();
    expect(conformite.tint).toBe('emerald');
    expect(conformite.expertOnly).toBe(false);
  });

  it('achat is visible in normal mode (not expertOnly)', () => {
    const achat = NAV_MODULES.find((m) => m.key === 'achat');
    expect(achat).toBeDefined();
    expect(achat.expertOnly).toBe(false);
    expect(achat.tint).toBe('violet');
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

  it('cockpit uses blue, conformite emerald, achat violet', () => {
    expect(MODULE_TINTS.cockpit).toContain('blue');
    expect(MODULE_TINTS.conformite).toContain('emerald');
    expect(MODULE_TINTS.achat).toContain('violet');
  });
});

/* ── Section definitions V7 ── */
describe('NAV_SECTIONS V7', () => {
  it('has exactly 6 sections (one per module)', () => {
    expect(NAV_SECTIONS).toHaveLength(6);
  });

  it('every section references a valid module', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const section of NAV_SECTIONS) {
      expect(moduleKeys).toContain(section.module);
    }
  });

  it('conformite section exists with 2 items (parent + APER)', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    expect(conformite).toBeDefined();
    expect(conformite.items).toHaveLength(2);
  });

  it('conformite section contains Conformité and APER (tabs merged)', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const labels = conformite.items.map((i) => i.label);
    expect(labels).toContain('Conformité');
    expect(labels).toContain('Solarisation (APER)');
  });

  it('facturation is under patrimoine (not energie)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.module === 'patrimoine');
    const energie = NAV_SECTIONS.find((s) => s.module === 'energie');
    expect(patrimoine.items.find((i) => i.label === 'Facturation')).toBeDefined();
    expect(energie.items.find((i) => i.label === 'Facturation')).toBeUndefined();
  });

  it('facturation is visible in normal mode (promoted from expertOnly)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.module === 'patrimoine');
    const facturation = patrimoine.items.find((i) => i.label === 'Facturation');
    expect(facturation).toBeDefined();
    expect(facturation.expertOnly).toBeFalsy();
  });

  it('usages is visible in normal mode (not expertOnly)', () => {
    const energie = NAV_SECTIONS.find((s) => s.module === 'energie');
    const usages = energie.items.find((i) => i.label === 'Répartition par usage');
    expect(usages).toBeDefined();
    expect(usages.expertOnly).toBeFalsy();
  });

  it('achat module has echeances and scenarios visible in normal', () => {
    const achat = NAV_SECTIONS.find((s) => s.module === 'achat');
    const labels = achat.items.map((i) => i.label);
    expect(labels).toContain('Échéances');
    expect(labels).toContain("Scénarios d'achat");
  });

  it('conformite has no tab-level items (DT/BACS/SMÉ merged into parent)', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const labels = conformite.items.map((i) => i.label);
    expect(labels).not.toContain('Décret Tertiaire');
    expect(labels).not.toContain('Pilotage bâtiment');
    expect(labels).not.toContain('Audit SMÉ');
  });
});

/* ── Expert filtering (item level) ── */
describe('Expert filtering V7', () => {
  it('normal mode: 13 visible items (1 page per concept)', () => {
    const normal = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      getVisibleItems(s.items, false)
    );
    expect(normal).toHaveLength(13);
  });

  it('expert mode: same 13 items (no expertOnly items left)', () => {
    const expert = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      getVisibleItems(s.items, true)
    );
    expect(expert).toHaveLength(13);
  });

  it('zero expert-only items (all tabs merged into parent pages)', () => {
    const expertItems = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      s.items.filter((i) => i.expertOnly)
    );
    expect(expertItems).toHaveLength(0);
  });

  it('getVisibleItems returns all items in expert mode', () => {
    const items = [
      { label: 'A', expertOnly: true },
      { label: 'B', expertOnly: false },
      { label: 'C' },
    ];
    expect(getVisibleItems(items, true)).toHaveLength(3);
    expect(getVisibleItems(items, false)).toHaveLength(2);
  });
});

/* ── Route mapping ── */
describe('Route mapping V7', () => {
  it('every nav item base path exists in ROUTE_MODULE_MAP', () => {
    for (const item of ALL_NAV_ITEMS) {
      const basePath = item.to.split('?')[0].split('#')[0];
      expect(ROUTE_MODULE_MAP).toHaveProperty(basePath);
    }
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

  it('conformite routes resolve to conformite module', () => {
    expect(resolveModule('/conformite')).toBe('conformite');
    expect(resolveModule('/conformite/aper')).toBe('conformite');
    expect(resolveModule('/compliance')).toBe('conformite');
  });

  it('patrimoine routes include bill-intel (facturation)', () => {
    expect(resolveModule('/bill-intel')).toBe('patrimoine');
    expect(resolveModule('/contrats')).toBe('patrimoine');
  });

  it('/ resolves to cockpit', () => {
    expect(resolveModule('/')).toBe('cockpit');
  });

  it('dynamic routes resolve correctly', () => {
    expect(resolveModule('/sites/42')).toBe('patrimoine');
    expect(resolveModule('/actions/123')).toBe('cockpit');
    expect(resolveModule('/conformite/tertiaire/efa/5')).toBe('conformite');
    expect(resolveModule('/compliance/sites/99')).toBe('conformite');
  });
});

/* ── getSectionsForModule helper ── */
describe('getSectionsForModule', () => {
  it('returns sections for cockpit module', () => {
    const sections = getSectionsForModule('cockpit');
    expect(sections).toHaveLength(1);
  });

  it('returns sections for every module', () => {
    for (const mod of NAV_MODULES) {
      const sections = getSectionsForModule(mod.key);
      expect(sections.length).toBeGreaterThanOrEqual(1);
    }
  });

  it('returns empty array for unknown module', () => {
    expect(getSectionsForModule('nonexistent')).toHaveLength(0);
  });
});

/* ── Vocabulaire V7 ── */
describe('Vocabulary V7', () => {
  it('Cockpit module is labeled "Accueil"', () => {
    const mod = NAV_MODULES.find((m) => m.key === 'cockpit');
    expect(mod.label).toBe('Accueil');
  });

  it('BACS keywords are in conformite parent item (merged from tab)', () => {
    const confo = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const parent = confo.items.find((i) => i.to === '/conformite');
    expect(parent.keywords).toContain('bacs');
    expect(parent.keywords).toContain('gtb');
  });

  it('Usages is labeled "Répartition par usage"', () => {
    const energie = NAV_SECTIONS.find((s) => s.module === 'energie');
    const usages = energie.items.find((i) => i.label === 'Répartition par usage');
    expect(usages).toBeDefined();
  });

  it('Performance is labeled "Performance énergétique"', () => {
    const energie = NAV_SECTIONS.find((s) => s.module === 'energie');
    const perf = energie.items.find((i) => i.label === 'Performance énergétique');
    expect(perf).toBeDefined();
  });

  it("Achat item 'Scénarios d'achat' replaces 'Stratégies d'achat'", () => {
    const achat = NAV_SECTIONS.find((s) => s.module === 'achat');
    const scenarios = achat.items.find((i) => i.label === "Scénarios d'achat");
    expect(scenarios).toBeDefined();
  });

  it("Simulateur keywords are in Scénarios d'achat parent item (merged from tab)", () => {
    const achat = NAV_SECTIONS.find((s) => s.module === 'achat');
    const scenarios = achat.items.find((i) => i.to === '/achat-energie');
    expect(scenarios.keywords).toContain('simulateur');
    expect(scenarios.keywords).toContain('assistant');
  });
});

/* ── Source guard (deprecated labels/routes absents) ── */
describe('Source guard V7', () => {
  it('no "Actions & Suivi" label in nav', () => {
    const flat = JSON.stringify(NAV_SECTIONS);
    expect(flat).not.toContain('Actions & Suivi');
  });

  it('no "Notifications" label in nav (moved to Centre d\'actions)', () => {
    const labels = ALL_NAV_ITEMS.map((i) => i.label);
    expect(labels).not.toContain('Notifications');
  });

  it("no deprecated labels: BACS (GTB/GTC), Loi APER (ENR), Stratégies d'achat", () => {
    const labels = ALL_NAV_ITEMS.map((i) => i.label);
    expect(labels).not.toContain('BACS (GTB/GTC)');
    expect(labels).not.toContain('Loi APER (ENR)');
    expect(labels).not.toContain("Stratégies d'achat");
  });

  it('/actions and /notifications not in nav items (only in backward compat routes)', () => {
    const paths = ALL_NAV_ITEMS.map((i) => i.to.split('?')[0].split('#')[0]);
    expect(paths).not.toContain('/actions');
    expect(paths).not.toContain('/notifications');
  });
});

/* ── Quick Actions ── */
describe('QUICK_ACTIONS', () => {
  it('has 14 quick actions', () => {
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

/* ── SIDEBAR_ITEM_TINTS ── */
describe('SIDEBAR_ITEM_TINTS', () => {
  it('has activeBg, activeText, activeBorder, dot for each tint', () => {
    for (const [, classes] of Object.entries(SIDEBAR_ITEM_TINTS)) {
      expect(typeof classes.activeBg).toBe('string');
      expect(typeof classes.activeText).toBe('string');
      expect(typeof classes.activeBorder).toBe('string');
      expect(typeof classes.dot).toBe('string');
    }
  });

  it('covers all 6 module tints (blue, emerald, indigo, amber, violet, slate)', () => {
    expect(Object.keys(SIDEBAR_ITEM_TINTS)).toEqual(
      expect.arrayContaining(['blue', 'emerald', 'indigo', 'amber', 'violet', 'slate'])
    );
  });
});

/* ── TINT_PALETTE ── */
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

  it('has entries for all 6 module tints', () => {
    const tintNames = NAV_MODULES.map((m) => m.tint);
    for (const name of tintNames) {
      expect(TINT_PALETTE[name]).toBeDefined();
    }
  });

  it('each palette entry has all required semantic keys', () => {
    for (const [, palette] of Object.entries(TINT_PALETTE)) {
      for (const key of REQUIRED_KEYS) {
        expect(typeof palette[key]).toBe('string');
      }
    }
  });

  it('violet palette exists for achat module', () => {
    expect(TINT_PALETTE.violet).toBeDefined();
    expect(TINT_PALETTE.violet.icon).toContain('violet');
  });
});

/* ── getModuleTint helper ── */
describe('getModuleTint', () => {
  it('returns palette by module key', () => {
    expect(getModuleTint('cockpit')).toBe(TINT_PALETTE.blue);
    expect(getModuleTint('conformite')).toBe(TINT_PALETTE.emerald);
    expect(getModuleTint('achat')).toBe(TINT_PALETTE.violet);
  });

  it('returns palette by pathname', () => {
    expect(getModuleTint('/conformite')).toBe(TINT_PALETTE.emerald);
    expect(getModuleTint('/patrimoine')).toBe(TINT_PALETTE.amber);
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

/* ── NAV_MAIN_SECTIONS (miroir pour Breadcrumb) ── */
describe('NAV_MAIN_SECTIONS', () => {
  it('excludes admin module', () => {
    const adminInMain = NAV_MAIN_SECTIONS.find((s) => s.label === 'Administration');
    expect(adminInMain).toBeUndefined();
  });

  it('has 5 main sections', () => {
    expect(NAV_MAIN_SECTIONS).toHaveLength(5);
  });

  it('is synchronized with NAV_SECTIONS (same items)', () => {
    for (const mainSection of NAV_MAIN_SECTIONS) {
      const source = NAV_SECTIONS.find((s) => s.key === mainSection.key);
      expect(source).toBeDefined();
      expect(mainSection.items).toEqual(source.items);
    }
  });
});

/* ── NAV_ADMIN_ITEMS ── */
describe('NAV_ADMIN_ITEMS', () => {
  it('has at least 1 admin item', () => {
    expect(NAV_ADMIN_ITEMS.length).toBeGreaterThanOrEqual(1);
  });

  it('includes Utilisateurs with requireAdmin', () => {
    const users = NAV_ADMIN_ITEMS.find((i) => i.label === 'Utilisateurs');
    expect(users).toBeDefined();
    expect(users.requireAdmin).toBe(true);
  });
});

/* ── Guard-rails IDs and labels ── */
describe('Guard-rails — IDs and labels', () => {
  it('all nav item routes start with /', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(item.to.startsWith('/')).toBe(true);
    }
  });

  it('no duplicate labels within the same section', () => {
    for (const section of NAV_SECTIONS) {
      const labels = section.items.map((i) => i.label);
      expect(new Set(labels).size).toBe(labels.length);
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
});
