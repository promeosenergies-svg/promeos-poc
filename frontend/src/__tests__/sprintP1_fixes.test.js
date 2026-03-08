/**
 * Sprint P1 — Source-guard tests for 8 audit fixes.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src = join(__dirname, '..');
const backend = join(__dirname, '..', '..', '..', 'backend');

function read(p) {
  return existsSync(p) ? readFileSync(p, 'utf-8') : null;
}

describe('Sprint P1 — FIX 1: Jargon FR', () => {
  it('no "Insights detectes" in ConsumptionDiagPage', () => {
    const f = read(join(src, 'pages', 'ConsumptionDiagPage.jsx'));
    expect(f).not.toMatch(/'Insights détectés'|"Insights détectés"/);
  });

  it('no "Insights" as tab label in ConsumptionExplorerPage', () => {
    const f = read(join(src, 'pages', 'ConsumptionExplorerPage.jsx'));
    expect(f).not.toMatch(/label: ['"]Insights['"]/);
  });

  it('no "Load Factor" as visible label in ProfileHeatmapTab', () => {
    const f = read(join(src, 'pages', 'consumption', 'ProfileHeatmapTab.jsx'));
    expect(f).not.toMatch(/"Load Factor"|'Load Factor'/);
  });

  it('has "Facteur de charge" in ProfileHeatmapTab', () => {
    const f = read(join(src, 'pages', 'consumption', 'ProfileHeatmapTab.jsx'));
    expect(f).toMatch(/Facteur de charge/);
  });

  it('no "Findings" as visible label in PatrimoineWizard', () => {
    const f = read(join(src, 'components', 'PatrimoineWizard.jsx'));
    expect(f).not.toMatch(/label="Findings"/);
  });

  it('has "Constats" label in PatrimoineWizard', () => {
    const f = read(join(src, 'components', 'PatrimoineWizard.jsx'));
    expect(f).toMatch(/label="Constats"/);
  });

  it('no "Findings par site" in ObligationsTab', () => {
    const f = read(join(src, 'pages', 'conformite-tabs', 'ObligationsTab.jsx'));
    expect(f).not.toMatch(/Findings par site/);
  });

  it('has "Constats par site" in ObligationsTab', () => {
    const f = read(join(src, 'pages', 'conformite-tabs', 'ObligationsTab.jsx'));
    expect(f).toMatch(/Constats par site/);
  });
});

describe('Sprint P1 — FIX 2: Default prices', () => {
  it('default_prices.py exists', () => {
    expect(existsSync(join(backend, 'config', 'default_prices.py'))).toBe(true);
  });

  it('no 0.18 hardcode in consumption_diagnostic.py', () => {
    const f = read(join(backend, 'services', 'consumption_diagnostic.py'));
    if (f) {
      const lines = f
        .split('\n')
        .filter(
          (l) =>
            !l.trim().startsWith('#') &&
            l.includes('0.18') &&
            !l.includes('default_prices') &&
            !l.includes('DEFAULT_PRICE')
        );
      expect(lines.length).toBe(0);
    }
  });

  it('no 0.18 hardcode in copilot_engine.py', () => {
    const f = read(join(backend, 'services', 'copilot_engine.py'));
    if (f) {
      const lines = f
        .split('\n')
        .filter(
          (l) =>
            !l.trim().startsWith('#') &&
            l.includes('0.18') &&
            !l.includes('default_prices') &&
            !l.includes('DEFAULT_PRICE')
        );
      expect(lines.length).toBe(0);
    }
  });
});

describe('Sprint P1 — FIX 3: TURPE unified', () => {
  it('offer_pricing_v1 uses tarif_loader', () => {
    const f = read(join(backend, 'services', 'offer_pricing_v1.py'));
    if (f) {
      expect(f.includes('tarif_loader') || f.includes('get_turpe')).toBe(true);
    }
  });
});

describe('Sprint P1 — FIX 6: ErrorState in ConsumptionExplorerPage', () => {
  it('imports ErrorState', () => {
    const f = read(join(src, 'pages', 'ConsumptionExplorerPage.jsx'));
    expect(f).toMatch(/ErrorState/);
  });

  it('uses motorError', () => {
    const f = read(join(src, 'pages', 'ConsumptionExplorerPage.jsx'));
    expect(f).toMatch(/motorError/);
  });
});

describe('Sprint P1 — FIX 7: Nav cleanup', () => {
  it('no /consommations/export in NavRegistry', () => {
    const f = read(join(src, 'layout', 'NavRegistry.js'));
    expect(f).not.toContain('/consommations/export');
  });

  it('no /consommations/kb in ROUTE_MODULE_MAP', () => {
    const f = read(join(src, 'layout', 'NavRegistry.js'));
    expect(f).not.toMatch(/['"]\/consommations\/kb['"]/);
  });
});

describe('Sprint P1 — FIX 8: ErrorState in BillingPage and AperPage', () => {
  it('BillingPage imports ErrorState', () => {
    const f = read(join(src, 'pages', 'BillingPage.jsx'));
    expect(f).toMatch(/ErrorState/);
  });

  it('AperPage imports ErrorState', () => {
    const f = read(join(src, 'pages', 'AperPage.jsx'));
    expect(f).toMatch(/ErrorState/);
  });
});
