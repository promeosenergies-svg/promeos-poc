/**
 * PROMEOS — A.1: Unified Consumption — Source-guard tests
 * Verifies source code structure using readFileSync + regex.
 *
 * A. ConsoSourceBadge component: exists with 3 source configs
 * B. Cockpit integration: imports ConsoSourceBadge, passes consoSource
 * C. EssentialsRow integration: receives consoSource, renders badge
 * D. PerformanceSnapshot integration: imports ConsoSourceBadge
 * E. API: consumption-unified endpoints registered
 * F. Backend service: consumption_unified_service exists
 * G. Backend routes: consumption_unified.py exists
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. ConsoSourceBadge component
// ============================================================
describe('A - ConsoSourceBadge component', () => {
  const code = readSrc('components', 'ConsoSourceBadge.jsx');

  it('exports default function ConsoSourceBadge', () => {
    expect(code).toContain('export default function ConsoSourceBadge');
  });

  it('has metered source config', () => {
    expect(code).toContain('metered:');
  });

  it('has billed source config', () => {
    expect(code).toContain('billed:');
  });

  it('has estimated source config', () => {
    expect(code).toContain('estimated:');
  });

  it('renders Compteur label for metered', () => {
    expect(code).toContain('Compteur');
  });

  it('renders Facture label for billed', () => {
    expect(code).toContain('Facture');
  });

  it('renders Estime label for estimated', () => {
    expect(code).toContain('Estime');
  });

  it('has data-testid="conso-source-badge"', () => {
    expect(code).toContain('data-testid="conso-source-badge"');
  });
});

// ============================================================
// B. Cockpit integration
// ============================================================
describe('B - Cockpit uses ConsoSourceBadge', () => {
  const code = readSrc('pages', 'Cockpit.jsx');

  it('has consoSource state', () => {
    expect(code).toContain('consoSource');
  });

  it('passes consoSource to EssentialsRow', () => {
    expect(code).toContain('consoSource={consoSource}');
  });

  it('fetches /api/cockpit for consumption data', () => {
    expect(code).toContain('/api/cockpit');
  });
});

// ============================================================
// C. EssentialsRow integration
// ============================================================
describe('C - EssentialsRow receives consoSource', () => {
  const code = readSrc('pages', 'cockpit', 'EssentialsRow.jsx');

  it('imports ConsoSourceBadge', () => {
    expect(code).toContain('ConsoSourceBadge');
  });

  it('accepts consoSource prop', () => {
    expect(code).toContain('consoSource');
  });

  it('renders ConsoSourceBadge with source prop', () => {
    expect(code).toContain('<ConsoSourceBadge');
  });
});

// ============================================================
// D. PerformanceSnapshot integration
// ============================================================
describe('D - PerformanceSnapshot uses ConsoSourceBadge', () => {
  const code = readSrc('components', 'PerformanceSnapshot.jsx');

  it('imports ConsoSourceBadge', () => {
    expect(code).toContain('ConsoSourceBadge');
  });

  it('renders ConsoSourceBadge', () => {
    expect(code).toContain('<ConsoSourceBadge');
  });
});

// ============================================================
// E. API: consumption-unified endpoints registered
// ============================================================
describe('E - API has consumption-unified endpoints', () => {
  const code = readSrc('services', 'api.js');

  it('exports getConsumptionUnifiedSite', () => {
    expect(code).toContain('getConsumptionUnifiedSite');
  });

  it('exports getConsumptionUnifiedPortfolio', () => {
    expect(code).toContain('getConsumptionUnifiedPortfolio');
  });

  it('exports getConsumptionReconcile', () => {
    expect(code).toContain('getConsumptionReconcile');
  });

  it('calls /consumption-unified/ endpoints', () => {
    expect(code).toContain('/consumption-unified/');
  });
});

// ============================================================
// F. Backend service: consumption_unified_service exists
// ============================================================
describe('F - Backend unified consumption service', () => {
  const backendRoot = resolve(__dirname, '../../../../backend');
  const code = readFileSync(
    resolve(backendRoot, 'services', 'consumption_unified_service.py'),
    'utf-8'
  );

  it('defines ConsumptionSource enum', () => {
    expect(code).toContain('class ConsumptionSource');
  });

  it('has get_consumption_summary function', () => {
    expect(code).toContain('def get_consumption_summary');
  });

  it('has get_portfolio_consumption function', () => {
    expect(code).toContain('def get_portfolio_consumption');
  });

  it('has reconcile_metered_billed function', () => {
    expect(code).toContain('def reconcile_metered_billed');
  });

  it('uses MeterReading for metered data', () => {
    expect(code).toContain('MeterReading');
  });

  it('uses EnergyInvoice for billed data', () => {
    expect(code).toContain('EnergyInvoice');
  });

  it('has METERED_COVERAGE_THRESHOLD = 0.80', () => {
    expect(code).toContain('METERED_COVERAGE_THRESHOLD = 0.80');
  });

  it('has RECONCILIATION_ALERT_THRESHOLD = 0.10', () => {
    expect(code).toContain('RECONCILIATION_ALERT_THRESHOLD = 0.10');
  });

  it('returns source_used in result', () => {
    expect(code).toContain('"source_used"');
  });

  it('returns confidence in result', () => {
    expect(code).toContain('"confidence"');
  });
});

// ============================================================
// G. Backend routes: consumption_unified.py exists
// ============================================================
describe('G - Backend unified consumption routes', () => {
  const backendRoot = resolve(__dirname, '../../../../backend');
  const code = readFileSync(resolve(backendRoot, 'routes', 'consumption_unified.py'), 'utf-8');

  it('defines /site/{site_id} endpoint', () => {
    expect(code).toContain('/site/{site_id}');
  });

  it('defines /portfolio endpoint', () => {
    expect(code).toContain('/portfolio');
  });

  it('defines /reconcile/{site_id} endpoint', () => {
    expect(code).toContain('/reconcile/{site_id}');
  });

  it('uses consumption_unified_service', () => {
    expect(code).toContain('consumption_unified_service');
  });
});
