/**
 * Admin routes coverage — Sprint 1 Vague A phase A4
 *
 * Vérifie que toutes les routes /admin/* enregistrées dans App.jsx sont
 * exposées soit dans NAV_SECTIONS (panel Admin), soit dans HIDDEN_PAGES
 * (CommandPalette Ctrl+K). Anti-drift pour ne pas re-créer d'orphelin.
 */
import { describe, it, expect } from 'vitest';
import { NAV_SECTIONS, HIDDEN_PAGES } from '../NavRegistry';

const ADMIN_ROUTES = [
  '/admin/users',
  '/admin/roles',
  '/admin/assignments',
  '/admin/audit',
  '/admin/kb-metrics',
  '/admin/cx-dashboard',
  '/admin/enedis-health',
];

const NEW_ADMIN_ITEMS = [
  '/admin/roles',
  '/admin/assignments',
  '/admin/audit',
  '/admin/kb-metrics',
  '/admin/cx-dashboard',
  '/admin/enedis-health',
];

describe('Admin routes coverage (A4)', () => {
  const adminSections = NAV_SECTIONS.filter((s) => s.module === 'admin');
  const adminItems = adminSections.flatMap((s) => s.items ?? []);
  const adminHrefs = adminItems.map((i) => i.to);
  const hiddenHrefs = HIDDEN_PAGES.map((p) => p.to);
  const allExposed = [...adminHrefs, ...hiddenHrefs];

  it('every admin route is exposed in NAV_SECTIONS or HIDDEN_PAGES', () => {
    const orphans = ADMIN_ROUTES.filter((r) => !allExposed.includes(r));
    expect(orphans, `Admin routes not exposed (orphan): ${orphans.join(', ')}`).toEqual([]);
  });

  it('all new admin items (A4) are present in NAV_SECTIONS admin', () => {
    const missing = NEW_ADMIN_ITEMS.filter((r) => !adminHrefs.includes(r));
    expect(missing).toEqual([]);
  });

  it('all new admin items are requireAdmin: true', () => {
    NEW_ADMIN_ITEMS.forEach((route) => {
      const item = adminItems.find((i) => i.to === route);
      expect(item, `Admin item not found: ${route}`).toBeDefined();
      expect(item.requireAdmin, `${route} should be requireAdmin`).toBe(true);
    });
  });

  it('all new admin items are expertOnly: true', () => {
    NEW_ADMIN_ITEMS.forEach((route) => {
      const item = adminItems.find((i) => i.to === route);
      expect(item.expertOnly, `${route} should be expertOnly`).toBe(true);
    });
  });

  it('new admin items have label, icon, keywords', () => {
    NEW_ADMIN_ITEMS.forEach((route) => {
      const item = adminItems.find((i) => i.to === route);
      expect(item.label, `${route} missing label`).toBeTruthy();
      expect(item.icon, `${route} missing icon`).toBeTruthy();
      expect(Array.isArray(item.keywords), `${route} missing keywords array`).toBe(true);
      expect(item.keywords.length).toBeGreaterThan(0);
    });
  });

  it('admin section itself is expertOnly (section-level gate)', () => {
    expect(adminSections).toHaveLength(1);
    expect(adminSections[0].expertOnly).toBe(true);
  });
});
