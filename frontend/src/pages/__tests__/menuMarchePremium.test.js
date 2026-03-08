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

/* ── A. Structure: energie + achat modules (previously Marché) ── */
describe('A. Energie + Achat modules', () => {
  const energieSections = getSectionsForModule('energie');
  const achatSections = getSectionsForModule('achat');

  it('Energie module has exactly 1 section', () => {
    expect(energieSections).toHaveLength(1);
  });

  it('Achat module has exactly 1 section', () => {
    expect(achatSections).toHaveLength(1);
  });

  it('Energie section label is Énergie', () => {
    expect(energieSections[0].label).toBe('Énergie');
  });

  it('Achat module desc is "Stratégies d\'achat énergie"', () => {
    const mod = NAV_MODULES.find((m) => m.key === 'achat');
    expect(mod.desc).toBe("Stratégies d'achat énergie");
  });
});

/* ── B. Labels: items now in energie / achat sections ── */
describe('B. Labels in new modules', () => {
  const energieItems = getSectionsForModule('energie').flatMap((s) => s.items);
  const achatItems = getSectionsForModule('achat').flatMap((s) => s.items);

  it('Facturation (/bill-intel) is in energie section', () => {
    const item = energieItems.find((i) => i.to === '/bill-intel');
    expect(item).toBeDefined();
    expect(item.label).toBe('Facturation');
  });

  it('Consommations (/consommations) is in energie section', () => {
    const item = energieItems.find((i) => i.to === '/consommations');
    expect(item).toBeDefined();
    expect(item.label).toBe('Consommations');
  });

  it("Stratégies d'achat (/achat-energie) is in achat section", () => {
    const item = achatItems.find((i) => i.to === '/achat-energie');
    expect(item).toBeDefined();
    expect(item.label).toBe("Stratégies d'achat");
  });

  it('/achat-assistant is in main nav', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/achat-assistant');
    expect(item).toBeDefined();
  });

  it('/renouvellements is in main nav', () => {
    const item = ALL_NAV_ITEMS.find((i) => i.to === '/renouvellements');
    expect(item).toBeDefined();
  });
});

/* ── C. No duplicates ── */
describe('C. No duplicates', () => {
  const achatItems = getSectionsForModule('achat').flatMap((s) => s.items);

  it('/achat-energie appears exactly once in achat items', () => {
    const achatsItems = achatItems.filter(
      (i) => i.to === '/achat-energie'
    );
    expect(achatsItems).toHaveLength(1);
  });

  it('no duplicate routes across achat sections', () => {
    const routes = achatItems.map((i) => i.to);
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

  it('panel width uses responsive clamp (220px–260px)', () => {
    expect(navPanel).toMatch(/clamp\(220px/);
  });

  it('section headers support line-clamp-2', () => {
    expect(navPanel).toMatch(/line-clamp-2/);
  });
});

/* ── E. Routes in new modules ── */
describe('E. Routes in new modules', () => {
  const energieItems = getSectionsForModule('energie').flatMap((s) => s.items);
  const achatItems = getSectionsForModule('achat').flatMap((s) => s.items);

  it('billing route is in energie section', () => {
    const routes = energieItems.map((i) => i.to);
    expect(routes).toContain('/bill-intel');
  });

  it('achat-energie route is in achat section', () => {
    const routes = achatItems.map((i) => i.to);
    expect(routes).toContain('/achat-energie');
  });

  it('payment-rules and portfolio-reconciliation are NOT in nav sections', () => {
    const allRoutes = ALL_NAV_ITEMS.map((i) => i.to);
    expect(allRoutes).not.toContain('/payment-rules');
    expect(allRoutes).not.toContain('/portfolio-reconciliation');
  });
});
