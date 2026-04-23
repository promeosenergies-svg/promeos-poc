/**
 * Admin routes coverage — Sprint 1 Vague A phase A4 + F3 fix P0-T1
 *
 * Vérifie que toutes les routes /admin/* enregistrées dans App.jsx sont
 * exposées soit dans NAV_SECTIONS (panel Admin), soit dans HIDDEN_PAGES
 * (CommandPalette Ctrl+K). Anti-drift pour ne pas re-créer d'orphelin.
 *
 * F3 fix P0-T1 : ADMIN_ROUTES est désormais dérivée dynamiquement de
 * App.jsx par lecture du source — si quelqu'un ajoute `<Route path=
 * "/admin/backup">` sans l'ajouter dans NAV_SECTIONS, le test échouera.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { NAV_SECTIONS, HIDDEN_PAGES } from '../NavRegistry';

const __dirname = dirname(fileURLToPath(import.meta.url));
const APP_SRC = readFileSync(join(__dirname, '..', '..', 'App.jsx'), 'utf-8');

// Dérive dynamiquement toutes les routes /admin/* depuis App.jsx.
// Inclut à la fois les Routes réelles (element={<X />}) et les
// redirections (<Navigate to="/admin/*">) — tant qu'elles sont
// attribuées à un path /admin/*.
const ADMIN_ROUTES = Array.from(
  new Set(Array.from(APP_SRC.matchAll(/path="(\/admin\/[^"]+)"/g), (m) => m[1]))
);

const NEW_ADMIN_ITEMS = [
  '/admin/roles',
  '/admin/assignments',
  '/admin/audit',
  '/admin/kb-metrics',
  '/admin/cx-dashboard',
  '/admin/enedis-health',
];

describe('Admin routes coverage (A4 + F3)', () => {
  const adminSections = NAV_SECTIONS.filter((s) => s.module === 'admin');
  const adminItems = adminSections.flatMap((s) => s.items ?? []);
  const adminHrefs = adminItems.map((i) => i.to);
  const hiddenHrefs = HIDDEN_PAGES.map((p) => p.to);
  const allExposed = [...adminHrefs, ...hiddenHrefs];

  it('App.jsx declares at least 7 /admin/* routes (A4 baseline)', () => {
    // Garde contre régression : si quelqu'un retire une Route admin
    // sans mettre à jour NAV_SECTIONS, on veut s'en apercevoir.
    expect(ADMIN_ROUTES.length).toBeGreaterThanOrEqual(7);
  });

  it('every /admin/* Route in App.jsx is exposed in NAV_SECTIONS or HIDDEN_PAGES', () => {
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
