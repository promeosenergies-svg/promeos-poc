/**
 * menuMarchePremium.test.js — Menu Marché Premium Guard-rails
 * Validates: grouped sections, shortLabel/longLabel, no duplicates,
 * tooltips (aria-label), apostrophe in "Assistant d'achat".
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';
import {
  NAV_SECTIONS,
  NAV_MODULES,
  ALL_NAV_ITEMS,
  getSectionsForModule,
} from '../../layout/NavRegistry';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Structure: 3 grouped sections for Marché ── */
describe('A. Marché grouped sections', () => {
  const marcheSections = getSectionsForModule('marche');

  it('Marché module has exactly 3 sections', () => {
    expect(marcheSections).toHaveLength(3);
  });

  it('sections are Facturation, Achats, Contrats in order', () => {
    expect(marcheSections.map((s) => s.label)).toEqual([
      'Facturation',
      'Achats',
      'Contrats',
    ]);
  });

  it('section keys are marche-facturation, marche-achats, marche-contrats', () => {
    expect(marcheSections.map((s) => s.key)).toEqual([
      'marche-facturation',
      'marche-achats',
      'marche-contrats',
    ]);
  });

  it('Marché module desc is "Factures & achats"', () => {
    const mod = NAV_MODULES.find((m) => m.key === 'marche');
    expect(mod.desc).toBe('Factures & achats');
  });
});

/* ── B. Labels: shortLabel (label) + longLabel ── */
describe('B. ShortLabel / LongLabel', () => {
  const allMarcheItems = getSectionsForModule('marche').flatMap((s) => s.items);

  it('Historique has longLabel "Historique (timeline & couverture)"', () => {
    const item = allMarcheItems.find((i) => i.to === '/billing');
    expect(item.label).toBe('Historique');
    expect(item.longLabel).toBe('Historique (timeline & couverture)');
  });

  it('Anomalies has longLabel "Anomalies de facturation"', () => {
    const item = allMarcheItems.find((i) => i.to === '/bill-intel');
    expect(item.label).toBe('Anomalies');
    expect(item.longLabel).toBe('Anomalies de facturation');
  });

  it('Achats has longLabel "Achats d\'énergie & scénarios"', () => {
    const item = allMarcheItems.find((i) => i.to === '/achat-energie');
    expect(item.label).toBe('Achats');
    expect(item.longLabel).toBe("Achats d'énergie & scénarios");
  });

  it('Assistant d\'achat has correct apostrophe and longLabel', () => {
    const item = allMarcheItems.find((i) => i.to === '/achat-assistant');
    expect(item.label).toBe("Assistant d'achat");
    expect(item.longLabel).toBe("Assistant d'achat (reco & arbitrages)");
  });

  it('Renouvellements has longLabel "Renouvellements & échéances"', () => {
    const item = allMarcheItems.find((i) => i.to === '/renouvellements');
    expect(item.label).toBe('Renouvellements');
    expect(item.longLabel).toBe('Renouvellements & échéances');
  });
});

/* ── C. No duplicates ── */
describe('C. No duplicates', () => {
  const allMarcheItems = getSectionsForModule('marche').flatMap((s) => s.items);

  it('"Achats" appears exactly once in marche items', () => {
    const achatsItems = allMarcheItems.filter(
      (i) => i.to === '/achat-energie'
    );
    expect(achatsItems).toHaveLength(1);
  });

  it('no duplicate routes across all marche sections', () => {
    const routes = allMarcheItems.map((i) => i.to);
    expect(new Set(routes).size).toBe(routes.length);
  });

  it('no duplicate routes globally in ALL_NAV_ITEMS', () => {
    const routes = ALL_NAV_ITEMS.map((i) => i.to);
    expect(new Set(routes).size).toBe(routes.length);
  });
});

/* ── D. Tooltips & accessibility (source-guard) ── */
describe('D. Tooltips & aria-label in NavPanel', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('PanelLink accepts longLabel prop', () => {
    expect(navPanel).toMatch(/longLabel/);
  });

  it('NavLink has aria-label with tipText (longLabel fallback)', () => {
    expect(navPanel).toMatch(/aria-label=\{tipText\}/);
  });

  it('panel width uses responsive clamp (248px–300px)', () => {
    expect(navPanel).toMatch(/clamp\(248px/);
  });

  it('section headers support line-clamp-2', () => {
    expect(navPanel).toMatch(/line-clamp-2/);
  });
});

/* ── E. Routes preserved ── */
describe('E. Routes unchanged', () => {
  const allMarcheItems = getSectionsForModule('marche').flatMap((s) => s.items);

  it('all expected marche routes are present', () => {
    const routes = allMarcheItems.map((i) => i.to);
    expect(routes).toContain('/billing');
    expect(routes).toContain('/bill-intel');
    expect(routes).toContain('/achat-energie');
    expect(routes).toContain('/achat-assistant');
    expect(routes).toContain('/renouvellements');
  });

  it('payment-rules and portfolio-reconciliation are NOT present', () => {
    const routes = allMarcheItems.map((i) => i.to);
    expect(routes).not.toContain('/payment-rules');
    expect(routes).not.toContain('/portfolio-reconciliation');
  });
});
