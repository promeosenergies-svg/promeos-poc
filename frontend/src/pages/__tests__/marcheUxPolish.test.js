/**
 * marcheUxPolish.test.js — Marché UX Polish Guard-rails
 * Validates: contextual recents, raccourcis header, no orange dots,
 * w-80 panel, harmonized quick action labels, aria-current.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';
import {
  QUICK_ACTIONS,
  getSectionsForModule,
} from '../../layout/NavRegistry';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Récents contextuel ── */
describe('A. Récents filtré par module', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('recents are filtered by activeModule', () => {
    expect(navPanel).toMatch(/recentModule\s*===\s*activeModule/);
  });

  it('no cross-module badge (_recentModule removed)', () => {
    expect(navPanel).not.toMatch(/_recentModule/);
  });

  it('recents comment says "same module only" or "current module"', () => {
    expect(navPanel).toMatch(/same module|current module|filtered by/i);
  });
});

/* ── B. Raccourcis premium ── */
describe('B. Raccourcis header & harmonized labels', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('quick actions section has "Raccourcis" header', () => {
    expect(navPanel).toMatch(/Raccourcis/);
  });

  it('quick action pills have focus-visible ring', () => {
    expect(navPanel).toMatch(/focus-visible:.*ring.*blue/);
  });

  it('QUICK_ACTIONS "achats" label matches arbo shortLabel', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'achats');
    expect(qa.label).toBe('Achats');
    expect(qa.longLabel).toBe("Achats d'énergie & scénarios");
  });

  it('QUICK_ACTIONS "factures" label matches arbo shortLabel', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'factures');
    expect(qa.label).toBe('Anomalies');
    expect(qa.longLabel).toBe('Anomalies de facturation');
  });

  it('quick action tiles route to same paths as arbo items', () => {
    const marcheItems = getSectionsForModule('marche').flatMap((s) => s.items);
    const achatsQa = QUICK_ACTIONS.find((a) => a.key === 'achats');
    const facturesQa = QUICK_ACTIONS.find((a) => a.key === 'factures');
    expect(marcheItems.find((i) => i.to === achatsQa.to)).toBeDefined();
    expect(marcheItems.find((i) => i.to === facturesQa.to)).toBeDefined();
  });
});

/* ── C. Pastilles orange supprimées ── */
describe('C. Group headers — no orange dots', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('SectionHeader does NOT render a dot span', () => {
    // Old pattern: <span className={`w-1.5 h-1.5 rounded-full ${dotClass}...`} />
    expect(navPanel).not.toMatch(/dotClass/);
    expect(navPanel).not.toMatch(/w-1\.5 h-1\.5 rounded-full/);
  });

  it('SectionHeader still has chevron + label', () => {
    expect(navPanel).toMatch(/ChevronDown/);
    expect(navPanel).toMatch(/uppercase tracking-wider/);
  });
});

/* ── D. Micro-details premium ── */
describe('D. Micro-details', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('panel width uses responsive clamp (248px–300px)', () => {
    expect(navPanel).toMatch(/clamp\(248px/);
  });

  it('PanelLink has aria-label for accessibility', () => {
    expect(navPanel).toMatch(/aria-label=\{tipText\}/);
  });

  it('section headers have line-clamp-2 for long labels', () => {
    expect(navPanel).toMatch(/line-clamp-2/);
  });

  it('no native title on PanelLink (avoid title natif)', () => {
    // PanelLink NavLink should NOT have title={tipText}
    expect(navPanel).not.toMatch(/title=\{tipText\}/);
  });
});
