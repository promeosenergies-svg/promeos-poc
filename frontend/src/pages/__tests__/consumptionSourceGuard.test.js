/**
 * PROMEOS — A.1 minor fix: Source-guard for consumption_source annotations.
 * Verifies glossary terms + backend source annotations via readFileSync.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const backendRoot = resolve(__dirname, '../../../../backend');

// ============================================================
// A. Glossary has 3 unified consumption terms
// ============================================================
describe('A - Glossary unified consumption terms', () => {
  const code = readFileSync(resolve(root, 'src', 'ui', 'glossary.js'), 'utf-8');

  it('has conso_metered key', () => {
    expect(code).toContain('conso_metered');
  });

  it('has conso_billed key', () => {
    expect(code).toContain('conso_billed');
  });

  it('has reconciliation_conso key', () => {
    expect(code).toContain('reconciliation_conso');
  });

  it('conso_metered has correct term', () => {
    expect(code).toContain('Consommation mesurée');
  });

  it('conso_billed has correct term', () => {
    expect(code).toContain('Consommation facturée');
  });

  it('reconciliation_conso mentions 10 %', () => {
    expect(code).toContain('10 %');
  });
});

// ============================================================
// B. kpi_engine.py exposes consumption_source
// ============================================================
describe('B - kpi_engine.py consumption_source', () => {
  const code = readFileSync(
    resolve(backendRoot, 'services', 'electric_monitoring', 'kpi_engine.py'),
    'utf-8'
  );

  it('returns consumption_source in compute result', () => {
    expect(code).toContain('"consumption_source"');
  });

  it('consumption_source value is metered', () => {
    expect(code).toContain('"metered"');
  });

  it('docstring references get_consumption_summary', () => {
    expect(code).toContain('get_consumption_summary');
  });

  it('docstring references consumption_unified_service', () => {
    expect(code).toContain('consumption_unified_service');
  });
});

// ============================================================
// C. consumption_diagnostic.py exposes consumption_source
// ============================================================
describe('C - consumption_diagnostic.py consumption_source', () => {
  const code = readFileSync(
    resolve(backendRoot, 'services', 'consumption_diagnostic.py'),
    'utf-8'
  );

  it('sets consumption_source in metrics', () => {
    expect(code).toContain('consumption_source');
  });

  it('consumption_source value is metered', () => {
    expect(code).toContain('"metered"');
  });

  it('_get_readings docstring references unified service', () => {
    expect(code).toContain('get_consumption_summary');
  });
});
