/**
 * navUxV114b.test.js — V114b UX Guard-rail Tests
 * 10 source-guard tests verifying 2-clicks reachability.
 * No DOM, no mocks — readFileSync + regex + NavRegistry imports.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  QUICK_ACTIONS,
} from '../../layout/NavRegistry';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

describe('V114b UX 2-clicks guard-rails', () => {
  it('1. Import factures: sidebar /bill-intel + QUICK_ACTIONS factures', () => {
    const facturation = NAV_SECTIONS.find((s) => s.key === 'marche-facturation');
    expect(facturation.items.find((i) => i.to === '/bill-intel')).toBeDefined();
    const qa = QUICK_ACTIONS.find((a) => a.key === 'factures');
    expect(qa).toBeDefined();
    expect(qa.to).toBe('/bill-intel');
  });

  it('2. Voir anomalies: sidebar /anomalies in operations', () => {
    const ops = NAV_SECTIONS.find((s) => s.key === 'operations');
    const centre = ops.items.find((i) => i.to === '/anomalies');
    expect(centre).toBeDefined();
    expect(centre.label).toBe("Centre d'actions");
  });

  it('3. Exporter OPERAT: QUICK_ACTIONS operat → /conformite/tertiaire', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'operat');
    expect(qa).toBeDefined();
    expect(qa.to).toBe('/conformite/tertiaire');
    expect(qa.keywords).toContain('operat');
  });

  it('4. Corriger données: QUICK_ACTIONS corriger → /conformite?tab=donnees', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'corriger');
    expect(qa).toBeDefined();
    expect(qa.to).toContain('/conformite');
    expect(qa.keywords).toContain('corriger');
  });

  it('5. Créer action: QUICK_ACTIONS creer-action → /actions/new', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'creer-action');
    expect(qa).toBeDefined();
    expect(qa.to).toBe('/actions/new');
    expect(qa.keywords).toContain('créer');
  });

  it("6. À traiter aujourd'hui: TodayActionsCard in CommandCenter", () => {
    const code = src('src/pages/CommandCenter.jsx');
    expect(code).toMatch(/TodayActionsCard/);
    expect(code).toMatch(/import.*TodayActionsCard/);
  });

  it("7. Centre d'actions hub: AnomaliesPage has CENTRE_TABS", () => {
    const code = src('src/pages/AnomaliesPage.jsx');
    expect(code).toMatch(/CENTRE_TABS/);
    expect(code).toMatch(/anomalies/);
    expect(code).toMatch(/actions/);
  });

  it('8. Preuves manquantes: QUICK_ACTIONS preuves → /conformite?tab=preuves', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'preuves');
    expect(qa).toBeDefined();
    expect(qa.to).toBe('/conformite?tab=preuves');
    expect(qa.keywords).toContain('preuves');
  });

  it("9. Journal d'audit: QUICK_ACTIONS audit → /admin/audit", () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'audit');
    expect(qa).toBeDefined();
    expect(qa.to).toBe('/admin/audit');
    expect(qa.keywords).toContain('audit');
  });

  it('10. toActionsList() points to /anomalies hub (not /actions)', () => {
    const code = src('src/services/routes.js');
    expect(code).toMatch(/function toActionsList/);
    expect(code).toMatch(/return `\/anomalies/);
  });
});
