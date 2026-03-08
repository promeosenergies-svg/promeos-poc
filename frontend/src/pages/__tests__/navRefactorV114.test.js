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
  it('Pilotage has exactly 3 items (Cockpit + Centre d\'actions + Notifications)', () => {
    const pilotage = NAV_SECTIONS.find((s) => s.key === 'pilotage');
    expect(pilotage.items).toHaveLength(3);
    expect(pilotage.items.map((i) => i.to)).toEqual(['/cockpit', '/actions', '/notifications']);
  });

  it('Patrimoine has exactly 2 items (Sites & Bâtiments + Conformité)', () => {
    const patrimoine = NAV_SECTIONS.find((s) => s.key === 'patrimoine');
    expect(patrimoine.items).toHaveLength(2);
    expect(patrimoine.items.map((i) => i.to)).toEqual([
      '/patrimoine',
      '/conformite',
    ]);
  });

  it("Actions & Suivi at /actions has alerts badge", () => {
    const pilotage = NAV_SECTIONS.find((s) => s.key === 'pilotage');
    const centre = pilotage.items.find((i) => i.to === '/actions');
    expect(centre.label).toBe("Actions & Suivi");
    expect(centre.badgeKey).toBe('alerts');
  });

  it('/notifications IS in sidebar and in ROUTE_MODULE_MAP', () => {
    const inNav = ALL_NAV_ITEMS.find((i) => i.to === '/notifications');
    expect(inNav).toBeDefined();
    expect(ROUTE_MODULE_MAP['/notifications']).toBe('pilotage');
  });

  it('/actions IS in sidebar and in ROUTE_MODULE_MAP', () => {
    const inNav = ALL_NAV_ITEMS.find((i) => i.to === '/actions');
    expect(inNav).toBeDefined();
    expect(ROUTE_MODULE_MAP['/actions']).toBe('pilotage');
  });

  it('Energie section does NOT contain payment-rules and portfolio-reconciliation in nav items', () => {
    const energie = NAV_SECTIONS.find((s) => s.key === 'energie');
    const routes = energie.items.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });

  it('Admin-data section does NOT contain payment-rules or portfolio-reconciliation', () => {
    const adminData = NAV_SECTIONS.find((s) => s.key === 'admin-data');
    expect(adminData.label).toBe('Données');
    const routes = adminData.items.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });

  it('QUICK_ACTIONS has 14 entries', () => {
    expect(QUICK_ACTIONS).toHaveLength(14);
  });

  it('/import is visible (not hidden)', () => {
    const adminData = NAV_SECTIONS.find((s) => s.key === 'admin-data');
    const importItem = adminData.items.find((i) => i.to === '/import');
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
