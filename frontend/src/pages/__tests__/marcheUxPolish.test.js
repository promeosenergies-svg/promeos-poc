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

/* ── A. Récents retirés Phase 3.F (2026-05-02) ──
 *
 * La feature "Récents" du panel a été retirée — décision UX (audit
 * docs/audits/ui_ux/02_navpanel_ux_audit_20260502.md P0.2 duplication
 * store + P2.2 sub-utilité). Le Command Palette ⌘K reste l'entrée
 * canonique pour retrouver une page récemment visitée.
 *
 * Ce describe block joue désormais le rôle de garde-fou anti-régression :
 * empêche la réintroduction silencieuse de la feature.
 */
describe('A. Récents retirés du panneau (Phase 3.F)', () => {
  const navPanel = src('src/layout/NavPanel.jsx');

  it('Clock icon NOT imported (recents section removed)', () => {
    expect(navPanel).not.toMatch(/\bClock\b/);
  });

  it('RECENTS_KEY / MAX_RECENTS constants NOT present', () => {
    expect(navPanel).not.toMatch(/RECENTS_KEY/);
    expect(navPanel).not.toMatch(/MAX_RECENTS/);
  });

  it('loadRecents / pushRecent helpers NOT present', () => {
    expect(navPanel).not.toMatch(/\bloadRecents\b/);
    expect(navPanel).not.toMatch(/\bpushRecent\b/);
  });

  it('still uses moduleSections for contextual display (sections preserved)', () => {
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

  it('QUICK_ACTIONS "achats" label V7 matches arbo shortLabel', () => {
    const qa = QUICK_ACTIONS.find((a) => a.key === 'achats');
    expect(qa.label).toBe('Achats');
    expect(qa.longLabel).toBe("Scénarios d'achat & échéances");
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
