/**
 * PROMEOS — NavRegistry Tests V7 (Rail + Panel Architecture)
 * Covers: 7 modules (6 normal + admin expertOnly), conformité autonome,
 *         facturation autonome (Phase 1.D — P0.1), vocabulaire v7, route
 *         mapping, expert filtering au niveau item.
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
  getOrderedModules,
} from '../NavRegistry';

/* ── Module definitions V7 ── */
describe('NAV_MODULES V7', () => {
  // Phase 1.D — P0.1 (audit navigation_audit_20260501.md §4.5) : Bill
  // Intelligence promu en module rail dédié. Compteurs passent de 6 → 7
  // total et 5 → 6 normal. L'ordre rail final cible Sol v1.1
  // (Accueil → Énergie → Conformité → Facturation → Achat → [sep] →
  // Patrimoine) sera fixé par P0.5 (decoupling structure / ordre).
  it('has exactly 7 modules (6 normal + admin expert, Flex WIP hidden)', () => {
    expect(NAV_MODULES).toHaveLength(7);
  });

  it('modules are in correct order with correct keys', () => {
    const keys = NAV_MODULES.map((m) => m.key);
    expect(keys).toEqual([
      'cockpit',
      'conformite',
      'energie',
      'patrimoine',
      'achat',
      'facturation',
      'admin',
    ]);
  });

  it('order field is sequential 1-7', () => {
    const orders = NAV_MODULES.map((m) => m.order);
    expect(orders).toEqual([1, 2, 3, 4, 5, 6, 7]);
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

  it('normal mode shows 6 modules (Flex WIP hidden)', () => {
    const normal = NAV_MODULES.filter((m) => !m.expertOnly);
    expect(normal).toHaveLength(6);
    expect(normal.map((m) => m.key)).toEqual([
      'cockpit',
      'conformite',
      'energie',
      'patrimoine',
      'achat',
      'facturation',
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
  // Phase 1.D — P0.1 : 1 section ajoutée (`facturation`). Total 6 → 7.
  it('has exactly 7 sections (one per module, Flex WIP hidden)', () => {
    expect(NAV_SECTIONS).toHaveLength(7);
  });

  it('every section references a valid module', () => {
    const moduleKeys = NAV_MODULES.map((m) => m.key);
    for (const section of NAV_SECTIONS) {
      expect(moduleKeys).toContain(section.module);
    }
  });

  // Cleanup sidebar Conformité (2026-05-24) : /conformite redevient le hub
  // unique. Les sous-items Décret Tertiaire / OPERAT et Solarisation (APER)
  // sont retirés de la sidebar — ils existent désormais comme chips
  // réglementaires internes à /conformite (?regulation=dt|aper). Doctrine
  // §6.2 hub unique : la section ne contient plus qu'un seul item.
  it('conformite section exists with exactly 1 item (hub unique)', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    expect(conformite).toBeDefined();
    expect(conformite.items).toHaveLength(1);
  });

  it('conformite section contains only Conformité hub (no DT/APER sub-items)', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const labels = conformite.items.map((i) => i.label);
    expect(labels).toContain('Conformité');
    expect(labels).not.toContain('Décret Tertiaire / OPERAT');
    expect(labels).not.toContain('Solarisation (APER)');
  });

  it('no conformite sidebar item points to /conformite/tertiaire or /conformite/aper', () => {
    const conformite = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const tos = conformite.items.map((i) => i.to);
    expect(tos).not.toContain('/conformite/tertiaire');
    expect(tos).not.toContain('/conformite/aper');
  });

  // Phase 1.D — P0.1 : Bill Intelligence promu de l'item enfoui dans
  // Patrimoine vers module rail dédié `facturation`. Doctrine §4.4 +
  // §11 intention "Facture, anomalie, contestation".
  it('facturation is a standalone module (Phase 1.D — P0.1)', () => {
    const facturation = NAV_SECTIONS.find((s) => s.module === 'facturation');
    expect(facturation).toBeDefined();
    expect(facturation.items.length).toBeGreaterThan(0);
  });

  it('facturation panel exposes /bill-intel as primary entry', () => {
    const facturation = NAV_SECTIONS.find((s) => s.module === 'facturation');
    const overview = facturation.items.find((i) => i.to === '/bill-intel');
    expect(overview).toBeDefined();
    expect(overview.expertOnly).toBeFalsy();
  });

  it('facturation no longer appears under patrimoine (Phase 1.D extraction)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.module === 'patrimoine');
    const energie = NAV_SECTIONS.find((s) => s.module === 'energie');
    expect(patrimoine.items.find((i) => i.label === 'Facturation')).toBeUndefined();
    expect(patrimoine.items.find((i) => i.to === '/bill-intel')).toBeUndefined();
    expect(energie.items.find((i) => i.label === 'Facturation')).toBeUndefined();
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

/* ── Cleanup sidebar Conformité (2026-05-24) ── */
describe('Cleanup sidebar Conformité — deep-link discoverability', () => {
  // Sidebar Conformité ne contient plus que /conformite (hub unique). Les
  // routes /conformite/tertiaire et /conformite/aper restent accessibles en
  // deep-link et doivent rester indexées dans CommandPalette via HIDDEN_PAGES
  // pour discoverability ⌘K (anti-pattern §6.2 : pas de page invisible
  // sans porte d'entrée).
  it('HIDDEN_PAGES contains /conformite/tertiaire (deep-link only)', async () => {
    const { HIDDEN_PAGES } = await import('../NavRegistry');
    const dt = HIDDEN_PAGES.find((p) => p.to === '/conformite/tertiaire');
    expect(dt).toBeDefined();
    expect(dt.hidden).toBe(true);
    expect(dt.reason).toMatch(/deep-link/);
  });

  it('HIDDEN_PAGES contains /conformite/aper (deep-link only)', async () => {
    const { HIDDEN_PAGES } = await import('../NavRegistry');
    const aper = HIDDEN_PAGES.find((p) => p.to === '/conformite/aper');
    expect(aper).toBeDefined();
    expect(aper.hidden).toBe(true);
    expect(aper.reason).toMatch(/deep-link/);
  });

  it('ROUTE_MODULE_MAP keeps /conformite/tertiaire and /conformite/aper deep-links', () => {
    // Les routes doivent rester accessibles : retirer de la sidebar ≠ retirer
    // les routes. Garantit que la nav module fonctionne pour ces deep-links.
    expect(ROUTE_MODULE_MAP['/conformite/tertiaire']).toBe('conformite');
    expect(ROUTE_MODULE_MAP['/conformite/aper']).toBe('conformite');
  });

  it('parent /conformite item keywords cover DT, BACS, APER, SMÉ, BEGES for search', () => {
    // La sidebar ayant fusionné les sous-items en chips internes, la search
    // palette ⌘K doit pouvoir résoudre les acronymes vers /conformite (hub
    // unique) — keywords étendus au moment du cleanup.
    const confo = NAV_SECTIONS.find((s) => s.module === 'conformite');
    const parent = confo.items.find((i) => i.to === '/conformite');
    for (const kw of ['tertiaire', 'operat', 'bacs', 'aper', 'sme', 'beges']) {
      expect(parent.keywords).toContain(kw);
    }
  });
});

/* ── Expert filtering (item level) ── */
describe('Expert filtering V7', () => {
  // Cleanup sidebar Conformité (2026-05-24) : retrait des 2 sous-items
  // DT/APER de la sidebar (hub unique /conformite) → 16 → 14 items.
  it('normal mode: 14 visible items (cleanup sidebar Conformité)', () => {
    const normal = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      getVisibleItems(s.items, false)
    );
    expect(normal).toHaveLength(14);
  });

  it('expert mode: same 14 items (no expertOnly items left)', () => {
    const expert = NAV_SECTIONS.filter((s) => !s.expertOnly).flatMap((s) =>
      getVisibleItems(s.items, true)
    );
    expect(expert).toHaveLength(14);
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

  it('patrimoine routes are limited to sites + contrats (Phase 1.D — P0.1)', () => {
    expect(resolveModule('/contrats')).toBe('patrimoine');
    expect(resolveModule('/patrimoine')).toBe('patrimoine');
  });

  it('facturation routes resolve to facturation module (Phase 1.D — P0.1)', () => {
    expect(resolveModule('/bill-intel')).toBe('facturation');
    expect(resolveModule('/billing')).toBe('facturation');
    expect(resolveModule('/payment-rules')).toBe('facturation');
    expect(resolveModule('/portfolio-reconciliation')).toBe('facturation');
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

/* ── Phase 1.C — P0.3 : Centre d'action en panel Accueil ── */
describe("Phase 1.C — P0.3 Centre d'action (panel Accueil)", () => {
  // Audit §4.4 + §7 Q2 : Centre d'action exposé en 3e position du panel
  // Accueil pour discoverability (icône Inbox, badge actionCenter).
  // 2026-05-02 : route repointée /action-center → /anomalies (legacy hub).
  // 2026-05-20 : M2-5.11 livre la refonte V4 (NarrativeBar 5 stats CFO +
  // colonne € + colonne Pilote + workflow assign). Le hub canonique bascule
  // sur /action-center-v4/pilotage (file prioritaire = vue matin Resp.
  // Énergie, cohérent LoginPage post-login redirect). /anomalies reste
  // accessible en deep-link mais n'est plus l'entrée nav par défaut.

  it("Centre d'action est en 3e position de la section Accueil", () => {
    const cockpit = NAV_SECTIONS.find((s) => s.module === 'cockpit');
    expect(cockpit.items).toHaveLength(3);
    expect(cockpit.items[2].to).toBe('/action-center-v4/pilotage');
    expect(cockpit.items[2].label).toBe("Centre d'action");
  });

  it("Centre d'action utilise le badgeKey actionCenter (réutilise fetch AppShell)", () => {
    const item = ALL_NAV_ITEMS.find((i) => i.label === "Centre d'action");
    expect(item).toBeDefined();
    expect(item.badgeKey).toBe('actionCenter');
  });

  it("Centre d'action keywords couvrent les axes prompt P0.3", () => {
    const item = ALL_NAV_ITEMS.find((i) => i.label === "Centre d'action");
    expect(item.keywords).toEqual(
      expect.arrayContaining(['action', 'actions', 'centre', 'inbox', 'anomalies', 'notifications'])
    );
  });

  it('/action-center est mappé au module cockpit dans ROUTE_MODULE_MAP (rétro-compat bookmarks)', () => {
    expect(ROUTE_MODULE_MAP['/action-center']).toBe('cockpit');
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
  it('has 15 quick actions (14 base + 1 sirene V118)', () => {
    expect(QUICK_ACTIONS).toHaveLength(15);
  });

  it('contains sirene entry with keywords siren/siret', () => {
    const sirene = QUICK_ACTIONS.find((a) => a.key === 'sirene');
    expect(sirene).toBeDefined();
    expect(sirene.to).toBe('/onboarding/sirene');
    expect(sirene.keywords).toContain('siren');
    expect(sirene.keywords).toContain('siret');
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

  // Phase 1.D — P0.1 : 1 section ajoutée (`facturation`). Total 5 → 6.
  it('has 6 main sections (Flex WIP hidden)', () => {
    expect(NAV_MAIN_SECTIONS).toHaveLength(6);
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

/* ── Phase 1.E — P0.5 : ordre rail final cible Sol v1.1 ── */
// Audit navigation_audit_20260501.md §4 + §7 Q3+Q4 :
//   Accueil → Énergie → Conformité → Facturation → Achat → [sep] → Patrimoine
// Patrimoine porte `groupBoundary: 'config'` et est systématiquement en
// dernière position visible peu importe le persona. Le séparateur est rendu
// par NavRail (cf. NavRail.jsx + NavRail rendering tests).
describe('Phase 1.E — P0.5 ordre rail cible Sol v1.1', () => {
  const PERSONAS = [
    'default',
    'energy_manager',
    'daf',
    'acheteur',
    'dg_owner',
    'resp_conformite',
    'resp_immobilier',
    'resp_site',
  ];

  // ── Module group boundary ──
  it("NAV_MODULES.patrimoine porte groupBoundary='config'", () => {
    const patrimoine = NAV_MODULES.find((m) => m.key === 'patrimoine');
    expect(patrimoine).toBeDefined();
    expect(patrimoine.groupBoundary).toBe('config');
  });

  it('aucun autre module visible ne porte de groupBoundary', () => {
    const others = NAV_MODULES.filter((m) => m.key !== 'patrimoine' && !m.expertOnly);
    for (const mod of others) {
      expect(mod.groupBoundary).toBeUndefined();
    }
  });

  // ── Patrimoine toujours en dernière position visible ──
  PERSONAS.forEach((role) => {
    it(`Patrimoine est la dernière position visible pour persona '${role}'`, () => {
      const ordered = getOrderedModules(role, false);
      const visibleKeys = ordered.map((m) => m.key);
      expect(visibleKeys[visibleKeys.length - 1]).toBe('patrimoine');
    });
  });

  // ── Default ordre = cible Sol v1.1 ──
  it('default order = Accueil → Énergie → Conformité → Facturation → Achat → Patrimoine', () => {
    const ordered = getOrderedModules('default', false);
    expect(ordered.map((m) => m.key)).toEqual([
      'cockpit',
      'energie',
      'conformite',
      'facturation',
      'achat',
      'patrimoine',
    ]);
  });

  // ── Default = energy_manager (cible Sol §2 persona dominant) ──
  it("default ordre identique à 'energy_manager' (persona dominant Sol §2)", () => {
    const defaultOrdered = getOrderedModules('default', false).map((m) => m.key);
    const emOrdered = getOrderedModules('energy_manager', false).map((m) => m.key);
    expect(defaultOrdered).toEqual(emOrdered);
  });

  // ── DAF priorité Facturation #2 (audit §5.3 hebdo) ──
  it('daf : Facturation est en position 2 (juste après cockpit)', () => {
    const ordered = getOrderedModules('daf', false).map((m) => m.key);
    expect(ordered[0]).toBe('cockpit');
    expect(ordered[1]).toBe('facturation');
  });

  // ── Tous les personas ont les 6 modules visibles, sans doublon ──
  PERSONAS.forEach((role) => {
    it(`persona '${role}' expose 6 modules visibles uniques`, () => {
      const ordered = getOrderedModules(role, false).map((m) => m.key);
      expect(ordered).toHaveLength(6);
      expect(new Set(ordered).size).toBe(6);
    });
  });

  // ── Expert mode : admin ajouté en queue (post-patrimoine) ──
  it('expert mode : admin ajouté en queue (après patrimoine)', () => {
    const ordered = getOrderedModules('default', true).map((m) => m.key);
    expect(ordered[ordered.length - 2]).toBe('patrimoine');
    expect(ordered[ordered.length - 1]).toBe('admin');
  });
});

/* ── Phase 3.D — P1.7 persona dominant module position parity ──
 *
 * Audit Phase 0.ter §5 + Q3 : tests parité par persona pour la position
 * 2 du rail (= module dominant après Cockpit). Cette suite complète le
 * test isolé `daf : Facturation #2` (P0.5) — couvre les 8 personas
 * pour qu'aucune dérive silencieuse de ROLE_MODULE_ORDER ne passe sans
 * détection.
 *
 * Si un test échoue ici → ROLE_MODULE_ORDER a été modifié sans mise à
 * jour de la matrice attendue. STOP audit forensique nécessaire avant
 * tout fix (cf. discipline Phase 0.ter Hypothèse C).
 */
describe('Phase 3.D — P1.7 persona dominant module position parity', () => {
  // Mapping persona → module dominant (position 2 du rail rendu).
  // Source : ROLE_MODULE_ORDER (NavRegistry.js:981-995) figé en P0.5
  // + AUDITEUR ajouté Phase 3.G (audit personas P0.1).
  const POSITION_2_BY_PERSONA = {
    default: 'energie', // = energy_manager (cible Sol §2)
    energy_manager: 'energie',
    daf: 'facturation', // hebdo finance — audit §5.3
    dg_owner: 'facturation', // mensuel finance + décisionnel
    acheteur: 'achat',
    resp_conformite: 'conformite',
    resp_immobilier: 'conformite',
    resp_site: 'energie',
    auditeur: 'conformite', // Phase 3.G — fonction audit réglementaire
  };

  for (const [persona, expectedModule] of Object.entries(POSITION_2_BY_PERSONA)) {
    it(`${persona} → ${expectedModule} en position 2`, () => {
      const ordered = getOrderedModules(persona, false);
      expect(ordered[1].key).toBe(expectedModule);
    });
  }

  // Cross-cutting : Patrimoine en dernière position visible pour tous
  // (filtre expertOnly pour ignorer admin en mode expert). Doublonne
  // intentionnellement le forEach P0.5 mais avec un angle filtre
  // expertOnly explicite — couvre le cas où admin serait inséré ailleurs.
  it('cross-cutting : Patrimoine est le dernier module visible pour les 8 personas', () => {
    const personas = Object.keys(POSITION_2_BY_PERSONA);
    for (const persona of personas) {
      const ordered = getOrderedModules(persona, false);
      const lastVisible = ordered.filter((m) => !m.expertOnly).slice(-1)[0];
      expect(lastVisible.key, `persona '${persona}' : dernier visible attendu = patrimoine`).toBe(
        'patrimoine'
      );
    }
  });
});

/* ── Phase 1.E — NavRail rendering séparateur ── */
describe('Phase 1.E — NavRail rendering séparateur (source-guard)', () => {
  // Source-guard : vérifie que NavRail.jsx implémente bien le rendering
  // du séparateur lié à `groupBoundary` selon les contraintes a11y du
  // prompt P0.5 (role="separator", aria-orientation="vertical", non
  // focusable). Évite les régressions silencieuses du rendering.
  const fs = require('fs');
  const path = require('path');
  const NAV_RAIL_SRC = fs.readFileSync(path.join(__dirname, '..', 'NavRail.jsx'), 'utf8');

  it('NavRail détecte mod.groupBoundary dans le map des modules', () => {
    expect(NAV_RAIL_SRC).toMatch(/mod\.groupBoundary/);
  });

  it('NavRail rend un élément role="separator"', () => {
    expect(NAV_RAIL_SRC).toMatch(/role="separator"/);
  });

  it('NavRail rend aria-orientation="vertical" sur le séparateur', () => {
    expect(NAV_RAIL_SRC).toMatch(/aria-orientation="vertical"/);
  });

  it("NavRail n'insère le séparateur qu'à partir du 2e module (idx > 0)", () => {
    // Garde-fou : ne JAMAIS rendre un séparateur en tête de liste —
    // le séparateur est sémantiquement entre 2 groupes.
    expect(NAV_RAIL_SRC).toMatch(/groupBoundary\s*&&\s*idx\s*>\s*0/);
  });
});
