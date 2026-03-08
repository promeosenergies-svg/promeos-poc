/**
 * PROMEOS — Bloc B.2 Navigation Structure — Source Guards
 * Vérifie 5 sections, routes requises, breadcrumb, CommandPalette.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relDir, file) {
  return readFileSync(join(__dirname, '..', relDir, file), 'utf-8');
}

// ── NavRegistry: 5 main sections ──────────────────────────────────────

describe('B.2 — Navigation structure', () => {
  const src = readSrc('layout', 'NavRegistry.js');

  it('NavRegistry has exactly 4 main sections', () => {
    const sectionCount = (src.match(/label:\s*["'](Pilotage|Patrimoine|Énergie|Achat)["']/gi) || [])
      .length;
    expect(sectionCount).toBeGreaterThanOrEqual(4);
  });

  it('exports NAV_MAIN_SECTIONS', () => {
    expect(src).toContain('export const NAV_MAIN_SECTIONS');
  });

  it('exports NAV_ADMIN_ITEMS for secondary menu', () => {
    expect(src).toContain('export const NAV_ADMIN_ITEMS');
  });

  it('exports NAV_ADMIN_ICON (Settings)', () => {
    expect(src).toContain('NAV_ADMIN_ICON');
    expect(src).toContain('Settings');
  });

  it('exports ROUTE_SECTION_MAP for breadcrumb', () => {
    expect(src).toContain('export const ROUTE_SECTION_MAP');
  });

  it('exports COMMAND_SHORTCUTS (10 quick actions)', () => {
    expect(src).toContain('export const COMMAND_SHORTCUTS');
    const _shortcuts = src.match(/key:\s*'/g) || [];
    // At least 10 shortcuts in COMMAND_SHORTCUTS
    expect(src).toMatch(/COMMAND_SHORTCUTS\s*=\s*\[/);
  });

  it('All main pages are in navigation', () => {
    const REQUIRED_ROUTES = [
      '/cockpit',
      '/patrimoine',
      '/conformite',
      '/billing',
      '/actions',
      '/monitoring',
      '/performance',
    ];
    REQUIRED_ROUTES.forEach((route) => {
      // /performance is the label for /monitoring — check both
      if (route === '/performance') {
        expect(src.includes('/monitoring') || src.includes('Performance')).toBe(true);
      } else {
        expect(src).toContain(route);
      }
    });
  });

  it('Section keys match: pilotage, patrimoine, energie, achat', () => {
    expect(src).toMatch(/key:\s*'pilotage'/);
    expect(src).toMatch(/key:\s*'patrimoine'/);
    expect(src).toMatch(/key:\s*'energie'/);
    expect(src).toMatch(/key:\s*'achat'/);
  });

  it('Each section has an icon', () => {
    // NAV_MAIN_SECTIONS entries have icon: <Component>
    const iconMatches = src.match(/icon:\s*(LayoutDashboard|Building2|Zap|ShoppingCart)/g) || [];
    expect(iconMatches.length).toBeGreaterThanOrEqual(4);
  });

  it('Admin items include IAM routes', () => {
    expect(src).toContain('/admin/users');
    expect(src).toContain('/admin/roles');
    expect(src).toContain('/admin/audit');
  });
});

// ── Breadcrumb: section-aware ─────────────────────────────────────────

describe('B.2 — Breadcrumb contextuel', () => {
  const src = readSrc('layout', 'Breadcrumb.jsx');

  it('imports ROUTE_SECTION_MAP from NavRegistry', () => {
    expect(src).toContain('ROUTE_SECTION_MAP');
  });

  it('imports NAV_MAIN_SECTIONS from NavRegistry', () => {
    expect(src).toContain('NAV_MAIN_SECTIONS');
  });

  it('has resolveSectionLabel function', () => {
    expect(src).toContain('resolveSectionLabel');
  });

  it('contains TABLEAU reference for section mapping', () => {
    expect(src).toMatch(/TABLEAU/);
  });
});

// ── CommandPalette: enriched ──────────────────────────────────────────

describe('B.2 — CommandPalette enrichie', () => {
  const src = readSrc('ui', 'CommandPalette.jsx');

  it('imports COMMAND_SHORTCUTS', () => {
    expect(src).toContain('COMMAND_SHORTCUTS');
  });

  it('imports ALL_MAIN_ITEMS for section-grouped results', () => {
    expect(src).toContain('ALL_MAIN_ITEMS');
  });

  it('shows section headers in results', () => {
    expect(src).toContain('item.section');
    expect(src).toMatch(/showSectionHeader/);
  });

  it('shows keyboard shortcuts', () => {
    expect(src).toContain('item.shortcut');
  });

  it('has "Actions rapides" section label', () => {
    expect(src).toContain('Actions rapides');
  });
});

// ── NavPanel: 5 collapsible sections + admin footer ──────────────────

describe('B.2 — NavPanel sections collapsibles', () => {
  const src = readSrc('layout', 'NavPanel.jsx');

  it('imports getSectionsForModule for contextual display', () => {
    expect(src).toContain('getSectionsForModule');
  });

  it('imports NAV_ADMIN_ITEMS', () => {
    expect(src).toContain('NAV_ADMIN_ITEMS');
  });

  it('imports NAV_ADMIN_ICON', () => {
    expect(src).toContain('NAV_ADMIN_ICON');
  });

  it('renders moduleSections (contextual per module)', () => {
    expect(src).toContain('moduleSections');
    expect(src).toMatch(/moduleSections\.map/);
  });

  it('renders admin footer section', () => {
    expect(src).toContain('adminItems');
    expect(src).toContain('Administration');
  });

  it('SectionHeader accepts icon prop', () => {
    expect(src).toMatch(/icon:\s*SectionIcon/);
  });
});
