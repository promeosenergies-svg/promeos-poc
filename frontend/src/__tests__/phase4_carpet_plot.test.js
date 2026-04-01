/**
 * phase4_carpet_plot.test.js — Phase 4 Carpet Plot source guards
 *
 * Verifies:
 *   A. CarpetPlot component exists with canvas, tooltip, legend
 *   B. TabConsoSite integrates CarpetPlot with hourly data
 *   C. No TabStub remains in Site360
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', rel), 'utf8');

const CARPET = src('components/CarpetPlot.jsx');
const TAB_CONSO = src('components/TabConsoSite.jsx');
const SITE360 = src('pages/Site360.jsx');

// ── A. CarpetPlot component ─────────────────────────────────────────────

describe('A. CarpetPlot component', () => {
  test('file exists', () => {
    expect(existsSync(path.resolve(__dirname, '..', 'components', 'CarpetPlot.jsx'))).toBe(true);
  });

  test('uses canvas ref for rendering', () => {
    expect(CARPET).toMatch(/useRef/);
    expect(CARPET).toMatch(/canvasRef/);
    expect(CARPET).toMatch(/<canvas/);
  });

  test('has quantile-based color palette (7 colors)', () => {
    expect(CARPET).toMatch(/PALETTE/);
    expect(CARPET).toMatch(/quantile/);
  });

  test('has tooltip on mouse move', () => {
    expect(CARPET).toMatch(/onMouseMove/);
    expect(CARPET).toMatch(/tooltip/);
  });

  test('has legend with min/median/max stats', () => {
    expect(CARPET).toMatch(/stats\.min/);
    expect(CARPET).toMatch(/stats\.median/);
    expect(CARPET).toMatch(/stats\.max/);
  });

  test('has data-testid for integration', () => {
    expect(CARPET).toMatch(/data-testid="carpet-plot"/);
  });

  test('handles empty data gracefully', () => {
    expect(CARPET).toMatch(/Aucune donnée horaire/);
  });

  test('parses EMS format {t, v}', () => {
    expect(CARPET).toMatch(/d\.t/);
    expect(CARPET).toMatch(/d\.v/);
  });

  test('supports onCellClick callback', () => {
    expect(CARPET).toMatch(/onCellClick/);
  });
});

// ── B. TabConsoSite integrates CarpetPlot ───────────────────────────────

describe('B. TabConsoSite + CarpetPlot integration', () => {
  test('imports CarpetPlot', () => {
    expect(TAB_CONSO).toMatch(/import CarpetPlot from/);
  });

  test('fetches hourly data for carpet plot', () => {
    expect(TAB_CONSO).toMatch(/granularity: 'hourly'/);
  });

  test('has hourlyData state', () => {
    expect(TAB_CONSO).toMatch(/hourlyData/);
    expect(TAB_CONSO).toMatch(/hourlyStatus/);
  });

  test('renders CarpetPlot component', () => {
    expect(TAB_CONSO).toMatch(/<CarpetPlot/);
  });

  test('has carpet plot section title', () => {
    expect(TAB_CONSO).toMatch(/Carpet plot/);
  });

  test('keeps existing daily AreaChart', () => {
    expect(TAB_CONSO).toMatch(/AreaChart/);
    expect(TAB_CONSO).toMatch(/granularity: 'daily'/);
  });

  test('keeps explorer CTA', () => {
    expect(TAB_CONSO).toMatch(/Explorer en détail/);
  });
});

// ── C. Site360 — zero stubs ─────────────────────────────────────────────

describe('C. Site360 — onglets vivants', () => {
  test('no TabStub in Site360', () => {
    const stubUsages = SITE360.split('\n').filter(
      (l) => l.includes('TabStub') && !l.includes('//') && !l.includes('import')
    );
    expect(stubUsages.length).toBe(0);
  });

  test('TabConsoSite is imported and used', () => {
    expect(SITE360).toMatch(/TabConsoSite/);
  });

  test('TabActionsSite is imported and used', () => {
    expect(SITE360).toMatch(/TabActionsSite/);
  });

  test('6 tab IDs are defined', () => {
    const tabIds = SITE360.match(/id: '[a-z]+'/g) || [];
    expect(tabIds.length).toBeGreaterThanOrEqual(6);
  });

  test('no "Bientôt disponible" text remains', () => {
    expect(SITE360).not.toMatch(/Bientôt disponible/);
    expect(SITE360).not.toMatch(/à venir/i);
  });
});
