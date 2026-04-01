/**
 * marcheUxPolish.test.js — Marché UX Polish Guard-rails
 * Validates: contextual recents, raccourcis header, no orange dots,
 * w-80 panel, harmonized quick action labels, aria-current.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';
import { QUICK_ACTIONS, getSectionsForModule } from '../../layout/NavRegistry';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Récents supprimé — panneau contextuel par module ── */
describe('A. Récents supprimé du panneau', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('no recentItems rendering in NavPanel', () => {
    expect(navPanel).not.toMatch(/recentItems\.map/);
  });

  it('no Clock icon import (recents removed)', () => {
    expect(navPanel).not.toMatch(/Clock/);
  });

  it('uses moduleSections for contextual display', () => {
    expect(navPanel).toMatch(/moduleSections\.map/);
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

  it('quick action tiles route to valid paths', () => {
    const achatsQa = QUICK_ACTIONS.find((a) => a.key === 'achats');
    const facturesQa = QUICK_ACTIONS.find((a) => a.key === 'factures');
    // achat-energie is in the achat section
    const achatItems = getSectionsForModule('achat').flatMap((s) => s.items);
    expect(achatItems.find((i) => i.to === achatsQa.to)).toBeDefined();
    // bill-intel is now accessible via QUICK_ACTIONS (hidden page in energie)
    expect(facturesQa.to).toBe('/bill-intel');
  });
});

/* ── C. Pastilles orange supprimées ── */
describe('C. Group headers — no orange dots', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('SectionHeader does NOT render a dot span', () => {
    // Old pattern: <span className={`w-1.5 h-1.5 rounded-full ${dotClass}...`} />
    expect(navPanel).not.toMatch(/dotClass/);
    // Note: w-1.5 h-1.5 rounded-full is now used for the contextual site status dot,
    // but SectionHeader itself must not use it (check SectionHeader function block only)
    const shStart = navPanel.indexOf('function SectionHeader');
    const shEnd = navPanel.indexOf('\n}', shStart + 10);
    if (shStart >= 0 && shEnd >= 0) {
      const shBlock = navPanel.slice(shStart, shEnd);
      expect(shBlock).not.toMatch(/w-1\.5 h-1\.5 rounded-full/);
    }
  });

  it('SectionHeader has static label (always visible, no toggle)', () => {
    expect(navPanel).not.toMatch(/ChevronDown/);
    expect(navPanel).toMatch(/uppercase tracking-wider/);
  });
});

/* ── D. Micro-details premium ── */
describe('D. Micro-details', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('panel width uses responsive clamp (190px–230px)', () => {
    expect(navPanel).toMatch(/clamp\(190px/);
  });

  it('PanelLink has aria-label for accessibility', () => {
    expect(navPanel).toMatch(/aria-label=\{tipText\}/);
  });

  it('section headers are always visible (no toggle state)', () => {
    expect(navPanel).not.toMatch(/openSections\[section\.key\]/);
  });

  it('no native title on PanelLink (avoid title natif)', () => {
    // PanelLink NavLink should NOT have title={tipText}
    expect(navPanel).not.toMatch(/title=\{tipText\}/);
  });
});
