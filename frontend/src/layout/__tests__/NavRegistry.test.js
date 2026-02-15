/**
 * PROMEOS — NavRegistry Tests (World-Class IA)
 * Covers: section order, expert filtering, route presence, structure integrity.
 */
import { describe, it, expect } from 'vitest';
import { NAV_SECTIONS, ROUTE_MODULE_MAP, ALL_NAV_ITEMS } from '../NavRegistry';

describe('NavRegistry section order', () => {
  it('has exactly 5 sections', () => {
    expect(NAV_SECTIONS).toHaveLength(5);
  });

  it('sections are in correct order', () => {
    const labels = NAV_SECTIONS.map((s) => s.label);
    expect(labels).toEqual([
      'Piloter',
      'Executer',
      'Analyser',
      'Marche & Factures',
      'Donnees & Admin',
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
});

describe('NavRegistry expert filtering', () => {
  const normalSections = NAV_SECTIONS.filter((s) => !s.expertOnly);
  const expertSections = NAV_SECTIONS.filter((s) => s.expertOnly);

  it('normal mode shows 3 sections', () => {
    expect(normalSections).toHaveLength(3);
    expect(normalSections.map((s) => s.key)).toEqual(['piloter', 'executer', 'analyser']);
  });

  it('expert mode adds 2 sections', () => {
    expect(expertSections).toHaveLength(2);
    expect(expertSections.map((s) => s.key)).toEqual(['marche', 'admin']);
  });

  it('normal mode shows ~8 items (excluding expertOnly items)', () => {
    const normalItems = normalSections.flatMap((s) =>
      s.items.filter((item) => !item.expertOnly)
    );
    expect(normalItems.length).toBeGreaterThanOrEqual(7);
    expect(normalItems.length).toBeLessThanOrEqual(9);
  });

  it('Diagnostic is expertOnly within Analyser', () => {
    const analyser = NAV_SECTIONS.find((s) => s.key === 'analyser');
    const diag = analyser.items.find((item) => item.to === '/diagnostic-conso');
    expect(diag).toBeDefined();
    expect(diag.expertOnly).toBe(true);
  });

  it('admin IAM items are expertOnly + requireAdmin', () => {
    const admin = NAV_SECTIONS.find((s) => s.key === 'admin');
    const iamItems = admin.items.filter((item) => item.requireAdmin);
    expect(iamItems.length).toBeGreaterThanOrEqual(4);
    for (const item of iamItems) {
      expect(item.expertOnly).toBe(true);
      expect(item.requireAdmin).toBe(true);
    }
  });
});

describe('NavRegistry route presence', () => {
  it('every nav item route exists in ROUTE_MODULE_MAP', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(ROUTE_MODULE_MAP).toHaveProperty(item.to);
    }
  });

  it('no duplicate routes across sections', () => {
    const routes = ALL_NAV_ITEMS.map((item) => item.to);
    expect(new Set(routes).size).toBe(routes.length);
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

describe('NavRegistry IA coherence', () => {
  it('Performance is next to Consommations in Analyser', () => {
    const analyser = NAV_SECTIONS.find((s) => s.key === 'analyser');
    const consoIdx = analyser.items.findIndex((item) => item.to === '/consommations');
    const perfIdx = analyser.items.findIndex((item) => item.to === '/monitoring');
    expect(consoIdx).toBeGreaterThanOrEqual(0);
    expect(perfIdx).toBe(consoIdx + 1);
  });

  it('Piloter has Alertes with badge', () => {
    const piloter = NAV_SECTIONS.find((s) => s.key === 'piloter');
    const alertes = piloter.items.find((item) => item.to === '/notifications');
    expect(alertes).toBeDefined();
    expect(alertes.badgeKey).toBe('alerts');
  });

  it('Analyser has Patrimoine', () => {
    const analyser = NAV_SECTIONS.find((s) => s.key === 'analyser');
    const patrimoine = analyser.items.find((item) => item.to === '/patrimoine');
    expect(patrimoine).toBeDefined();
  });

  it('collapsible sections have defaultCollapsed', () => {
    for (const section of NAV_SECTIONS) {
      if (section.collapsible) {
        expect(typeof section.defaultCollapsed).toBe('boolean');
      }
    }
  });

  it('ALL_NAV_ITEMS has section label for each item', () => {
    for (const item of ALL_NAV_ITEMS) {
      expect(typeof item.section).toBe('string');
      expect(item.section.length).toBeGreaterThan(0);
    }
  });
});
