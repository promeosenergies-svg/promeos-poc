/**
 * V114 Navigation Refactor — Guard-rail tests
 * Ensures the sidebar restructure is correct:
 * - Cockpit: 2 items (no Alertes)
 * - Operations: 3 items (Centre d'actions replaces Anomalies + Plan d'actions)
 * - Marche: includes payment-rules + reconciliation (moved from Admin)
 * - Referentiels: slimmed, /import visible
 * - QUICK_ACTIONS: 8 entries
 */
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  QUICK_ACTIONS,
  ALL_NAV_ITEMS,
  ROUTE_MODULE_MAP,
} from '../../layout/NavRegistry';

describe('V114 Nav Refactor guard-rails', () => {
  it('Cockpit has exactly 2 items (Tableau de bord + Vue executive)', () => {
    const cockpit = NAV_SECTIONS.find((s) => s.key === 'cockpit');
    expect(cockpit.items).toHaveLength(2);
    expect(cockpit.items.map((i) => i.to)).toEqual(['/', '/cockpit']);
  });

  it('Operations has exactly 3 items (Conformite + Tertiaire + Centre d\'actions)', () => {
    const ops = NAV_SECTIONS.find((s) => s.key === 'operations');
    expect(ops.items).toHaveLength(3);
    expect(ops.items.map((i) => i.to)).toEqual([
      '/conformite',
      '/conformite/tertiaire',
      '/anomalies',
    ]);
  });

  it("Centre d'actions at /anomalies has alerts badge", () => {
    const ops = NAV_SECTIONS.find((s) => s.key === 'operations');
    const centre = ops.items.find((i) => i.to === '/anomalies');
    expect(centre.label).toBe("Centre d'actions");
    expect(centre.badgeKey).toBe('alerts');
  });

  it('/notifications is NOT in sidebar but IS in ROUTE_MODULE_MAP', () => {
    const inNav = ALL_NAV_ITEMS.find((i) => i.to === '/notifications');
    expect(inNav).toBeUndefined();
    expect(ROUTE_MODULE_MAP['/notifications']).toBe('cockpit');
  });

  it('/actions is NOT in sidebar but IS in ROUTE_MODULE_MAP', () => {
    const inNav = ALL_NAV_ITEMS.find((i) => i.to === '/actions');
    expect(inNav).toBeUndefined();
    expect(ROUTE_MODULE_MAP['/actions']).toBe('operations');
  });

  it('Marche contains payment-rules and portfolio-reconciliation', () => {
    const marche = NAV_SECTIONS.find((s) => s.key === 'marche');
    const routes = marche.items.map((i) => i.to);
    expect(routes).toContain('/payment-rules');
    expect(routes).toContain('/portfolio-reconciliation');
  });

  it('Referentiels does NOT contain payment-rules or portfolio-reconciliation', () => {
    const donnees = NAV_SECTIONS.find((s) => s.key === 'donnees');
    expect(donnees.label).toBe('Référentiels');
    const routes = donnees.items.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });

  it('QUICK_ACTIONS has 8 entries', () => {
    expect(QUICK_ACTIONS).toHaveLength(8);
  });

  it('/import is visible (not hidden)', () => {
    const donnees = NAV_SECTIONS.find((s) => s.key === 'donnees');
    const importItem = donnees.items.find((i) => i.to === '/import');
    expect(importItem).toBeDefined();
    expect(importItem.hidden).toBeFalsy();
  });

  it('no English labels in nav items', () => {
    const blacklist = ['Center', 'Dashboard', 'Home', 'Knowledge Base', 'Settings'];
    for (const item of ALL_NAV_ITEMS) {
      for (const word of blacklist) {
        expect(item.label.toLowerCase()).not.toContain(word.toLowerCase());
      }
    }
  });
});
