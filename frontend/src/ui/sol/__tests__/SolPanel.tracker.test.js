/**
 * SolPanel + pages : tracker events — Sprint 1 Vague A phase A10
 *
 * Vérifie le wiring des 5 events instrumentés :
 *   - nav_panel_opened
 *   - nav_deep_link_click
 *   - anomaly_filter_applied (manual + deep_link)
 *   - aper_filter_applied (deep_link)
 *   - renouvellements_horizon_selected (manual + deep_link)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..', '..', '..'); // frontend/src

function read(p) {
  return readFileSync(join(root, p), 'utf-8');
}

describe('Tracker events — SolPanel (A10)', () => {
  const src = read('ui/sol/SolPanel.jsx');

  it('imports track from tracker service', () => {
    expect(src).toMatch(/import\s*\{\s*track\s*\}\s*from\s*['"]\.\.\/\.\.\/services\/tracker['"]/);
  });

  it("fires 'nav_panel_opened' on mount/route change", () => {
    expect(src).toMatch(/track\(\s*['"]nav_panel_opened['"]/);
    expect(src).toMatch(/module:\s*currentModule/);
    expect(src).toMatch(/is_expert:\s*isExpert/);
  });

  it("fires 'nav_deep_link_click' on item click", () => {
    expect(src).toMatch(/track\(\s*['"]nav_deep_link_click['"]/);
    expect(src).toMatch(/is_deep_link:\s*isDeepLink/);
  });

  it('distinguishes deep-links from top-level items (section_key === "deep-links")', () => {
    expect(src).toMatch(/DEEP_LINK_SECTION_KEY\s*=\s*['"]deep-links['"]/);
    expect(src).toMatch(/sectionKey === DEEP_LINK_SECTION_KEY/);
  });

  it('wires handleItemClick with section.key (not location)', () => {
    expect(src).toMatch(
      /onClick=\{locked \? undefined : \(\) => handleItemClick\(item, section\.key\)\}/
    );
  });

  // F3 fix P0-T4 : assertion NÉGATIVE que track() ne peut PAS être
  // invoqué sur le chemin locked. Une régression triviale (track()
  // inconditionnel dans handleItemClick, onMouseDown séparé, etc.)
  // passerait les tests positifs mais casserait ce guard.
  it('F3 P0-T4 : track nav_deep_link_click cannot fire when locked', () => {
    const trackCalls = src.match(/track\(\s*['"]nav_deep_link_click['"]/g) || [];
    expect(trackCalls.length).toBe(1); // un seul site d'appel
    expect(src).toMatch(/handleItemClick[\s\S]*?track\(\s*['"]nav_deep_link_click['"]/);
    expect(src).toMatch(/onClick=\{locked \? undefined : \(\) => handleItemClick/);
  });

  it('F3 : no onMouseDown / onTouchStart tracker leaks (track only on onClick)', () => {
    // Le panel n'expose aucun handler secondaire susceptible de fire
    // le tracker en bypassant le guard locked.
    expect(src).not.toMatch(/onMouseDown=.*track\(/);
    expect(src).not.toMatch(/onTouchStart=.*track\(/);
  });
});

describe('Tracker events — AperSol (A10)', () => {
  const src = read('pages/AperSol.jsx');

  it('imports track from tracker service', () => {
    expect(src).toMatch(/import\s*\{\s*track\s*\}\s*from\s*['"]\.\.\/services\/tracker['"]/);
  });

  it("fires 'aper_filter_applied' with source='deep_link' when URL filter is present", () => {
    expect(src).toMatch(/track\(\s*['"]aper_filter_applied['"]/);
    expect(src).toMatch(/source:\s*['"]deep_link['"]/);
    expect(src).toMatch(/filter_type:\s*activeFilter/);
  });
});

describe('Tracker events — AnomaliesPage (A10)', () => {
  const src = read('pages/AnomaliesPage.jsx');

  it('imports track from tracker service', () => {
    expect(src).toMatch(/import\s*\{\s*track\s*\}\s*from\s*['"]\.\.\/services\/tracker['"]/);
  });

  it("fires 'anomaly_filter_applied' with source='deep_link' at mount when fw present", () => {
    expect(src).toMatch(/track\(\s*['"]anomaly_filter_applied['"]/);
    expect(src).toMatch(/source:\s*['"]deep_link['"]/);
  });

  it("fires 'anomaly_filter_applied' with source='manual' in onChange of fw select", () => {
    expect(src).toMatch(/source:\s*['"]manual['"]/);
  });

  it('uses useRef(false) guard to fire deep_link only once', () => {
    expect(src).toMatch(/firedDeepLinkTrackRef/);
    expect(src).toMatch(/firedDeepLinkTrackRef\.current\s*=\s*true/);
  });
});

describe('Tracker events — ContractRadarPage (A10)', () => {
  const src = read('pages/ContractRadarPage.jsx');

  it('fires renouvellements_horizon_selected with source=manual in setHorizon', () => {
    expect(src).toMatch(/track\(\s*['"]renouvellements_horizon_selected['"]/);
    expect(src).toMatch(/source:\s*['"]manual['"]/);
  });

  it("fires renouvellements_horizon_selected with source='deep_link' at mount", () => {
    expect(src).toMatch(/source:\s*['"]deep_link['"]/);
    expect(src).toMatch(/firedHorizonDeepLinkRef/);
  });
});
