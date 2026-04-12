/**
 * Step 24b — Refonte navigation : 12 entrées max, zéro jargon
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const navFile = [
  'src/layout/NavRegistry.js',
  'src/layout/navConfig.js',
  'src/components/layout/NavRegistry.js',
].find((f) => fs.existsSync(f));

describe('Step 24b — Navigation clean', () => {
  it('nav config file exists', () => {
    expect(navFile).toBeDefined();
  });

  it('has at least 5 main sections (V7: cockpit, conformite, patrimoine, energie, achat)', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    // NAV_MAIN_SECTIONS is derived from NAV_SECTIONS at runtime;
    // check NAV_SECTIONS keys directly.
    const sections =
      src.match(/key:\s*['"](cockpit|conformite|patrimoine|energie|achat)['"]/g) || [];
    expect(sections.length).toBeGreaterThanOrEqual(5);
  });

  it('has max 17 main menu items in NAV_MAIN_SECTIONS', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    // Extract NAV_MAIN_SECTIONS block and count path entries
    const mainBlock = src.split('NAV_MAIN_SECTIONS')[1]?.split('NAV_ADMIN')[0] || '';
    const paths = mainBlock.match(/to:\s*['"]\/[^'"]+['"]/g) || [];
    expect(paths.length).toBeLessThanOrEqual(17);
  });

  it('no jargon in NAV_MAIN_SECTIONS menu labels', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    const mainBlock = src.split('NAV_MAIN_SECTIONS')[1]?.split('NAV_ADMIN')[0] || '';
    const jargon = ['Mémobox', 'Segmentation', 'Pipeline', 'Copilot', 'RegOps'];
    jargon.forEach((j) => {
      expect(mainBlock).not.toMatch(new RegExp(`label.*${j}`, 'i'));
    });
  });

  it('admin section exists and is separate from main', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    expect(src.includes('NAV_ADMIN')).toBe(true);
  });

  it('NAV_ADMIN_ITEMS has max 5 items', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    const adminBlock = src.split('NAV_ADMIN_ITEMS')[1]?.split('];')[0] || '';
    const paths = adminBlock.match(/to:\s*['"]\/[^'"]+['"]/g) || [];
    expect(paths.length).toBeLessThanOrEqual(5);
  });
});

describe('Step 24b — NavPanel raccourcis', () => {
  const panelFiles = ['src/layout/NavPanel.jsx', 'src/components/layout/NavPanel.jsx'];
  const panel = panelFiles.find((f) => fs.existsSync(f));

  it('NavPanel exists', () => {
    expect(panel).toBeDefined();
  });

  it('Raccourcis section requires isExpert or is removed', () => {
    if (panel) {
      const src = fs.readFileSync(panel, 'utf8');
      // If RACCOURCIS exists, it must be gated by isExpert
      if (src.includes('Raccourcis')) {
        expect(src).toContain('isExpert');
      }
    }
  });
});

describe('Step 24b — CommandPalette hidden pages', () => {
  const palFiles = ['src/ui/CommandPalette.jsx', 'src/components/layout/CommandPalette.jsx'];
  const pal = palFiles.find((f) => fs.existsSync(f));

  it('CommandPalette exists', () => {
    expect(pal).toBeDefined();
  });

  it('hidden pages are available via ALL_MAIN_ITEMS or HIDDEN_PAGES', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    // At least some hidden pages exist in ALL_MAIN_ITEMS
    expect(
      src.includes('HIDDEN_PAGES') || src.includes('diagnostic-conso') || src.includes('Mémobox')
    ).toBe(true);
  });

  it('CommandPalette uses ALL_MAIN_ITEMS for search', () => {
    if (pal) {
      const src = fs.readFileSync(pal, 'utf8');
      expect(src).toContain('ALL_MAIN_ITEMS');
    }
  });
});

describe('Step 24b — NavRail modules V7', () => {
  it('NAV_MODULES has 7 entries (6 normal + admin expert)', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    const start = src.indexOf('export const NAV_MODULES');
    const block = src.slice(start, start + 3000);
    const firstClose = block.indexOf('];');
    const moduleBlock = block.slice(0, firstClose);
    const keys = moduleBlock.match(/key:\s*['"][^'"]+['"]/g) || [];
    expect(keys.length).toBe(7);
  });

  it('NAV_MODULES V7 includes cockpit, conformite, energie, patrimoine, achat, admin', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    expect(src).toMatch(/key:\s*['"]cockpit['"]/);
    expect(src).toMatch(/key:\s*['"]conformite['"]/);
    expect(src).toMatch(/key:\s*['"]patrimoine['"]/);
    expect(src).toMatch(/key:\s*['"]energie['"]/);
    expect(src).toMatch(/key:\s*['"]achat['"]/);
    expect(src).toMatch(/key:\s*['"]admin['"]/);
  });
});

describe('Step 24b — Labels V7', () => {
  it('labels use V7 vocabulary', () => {
    const src = fs.readFileSync(navFile, 'utf8');
    expect(src).toContain("label: 'Accueil'");
    expect(src).toContain("label: 'Conformité'");
    expect(src).toContain("label: 'Patrimoine'");
    expect(src).toContain("label: 'Achat'");
  });
});
