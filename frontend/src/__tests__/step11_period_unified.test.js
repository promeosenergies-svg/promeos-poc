/**
 * PROMEOS — Step 11: Période unifiée via URL entre pages Analyse
 * Vérifie que usePeriodParams est branché et que la période est propagée.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readFrontend(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. usePeriodParams hook ─────────────────────────────────────────────────

describe('A. usePeriodParams hook', () => {
  test('A1. hook file exists', () => {
    expect(existsSync(join(__dirname, '..', 'hooks', 'usePeriodParams.js'))).toBe(true);
  });

  const src = readFrontend('hooks/usePeriodParams.js');

  test('A2. exports default function usePeriodParams', () => {
    expect(src).toMatch(/export default function usePeriodParams/);
  });

  test('A3. uses useSearchParams', () => {
    expect(src).toContain('useSearchParams');
  });

  test('A4. returns periodQueryString', () => {
    expect(src).toContain('periodQueryString');
  });

  test('A5. reads period_start param', () => {
    expect(src).toContain('period_start');
  });

  test('A6. reads period_end param', () => {
    expect(src).toContain('period_end');
  });

  test('A7. returns setPeriod function', () => {
    expect(src).toContain('setPeriod');
  });

  test('A8. supports defaultDays parameter', () => {
    expect(src).toMatch(/defaultDays/);
  });

  test('A9. backward compat: reads start/end/date_from/date_to', () => {
    expect(src).toContain("'start'");
    expect(src).toContain("'end'");
    expect(src).toContain("'date_from'");
    expect(src).toContain("'date_to'");
  });
});

// ── B. ConsumptionExplorerPage — period from URL ────────────────────────────

describe('B. Explorer period URL sync', () => {
  const src = readFrontend('pages/consumption/useExplorerURL.js');

  test('B1. useExplorerURL reads period_start param', () => {
    expect(src).toContain('period_start');
  });

  test('B2. useExplorerURL reads period_end param', () => {
    expect(src).toContain('period_end');
  });

  test('B3. backward compat: still reads start/end params', () => {
    expect(src).toContain("'start'");
    expect(src).toContain("'end'");
  });
});

// ── C. MonitoringPage uses usePeriodParams ──────────────────────────────────

describe('C. MonitoringPage period integration', () => {
  const src = readFrontend('pages/MonitoringPage.jsx');

  test('C1. imports usePeriodParams', () => {
    expect(src).toMatch(/import usePeriodParams/);
  });

  test('C2. calls usePeriodParams(90)', () => {
    expect(src).toMatch(/usePeriodParams\(90\)/);
  });

  test('C3. uses monitoringDays instead of hardcoded 90', () => {
    expect(src).toContain('monitoringDays');
  });

  test('C4. periodQueryString available', () => {
    expect(src).toContain('periodQueryString');
  });

  test('C5. period badge visible', () => {
    expect(src).toMatch(/Période/);
    expect(src).toContain('period.start');
  });
});

// ── D. ConsumptionDiagPage uses usePeriodParams ─────────────────────────────

describe('D. ConsumptionDiagPage period integration', () => {
  const src = readFrontend('pages/ConsumptionDiagPage.jsx');

  test('D1. imports usePeriodParams', () => {
    expect(src).toMatch(/import usePeriodParams/);
  });

  test('D2. calls usePeriodParams(90)', () => {
    expect(src).toMatch(/usePeriodParams\(90\)/);
  });

  test('D3. period badge visible', () => {
    expect(src).toMatch(/Période/);
    expect(src).toContain('period.start');
  });
});

// ── E. routes.js supports period propagation ────────────────────────────────

describe('E. routes.js period propagation', () => {
  const src = readFrontend('services/routes.js');

  test('E1. toConsoExplorer supports period_start', () => {
    expect(src).toContain('period_start');
  });

  test('E2. toConsoExplorer supports period_end', () => {
    expect(src).toContain('period_end');
  });

  test('E3. toConsoDiag supports period params', () => {
    const diagSection = src.split('function toConsoDiag')[1].split('function ')[0];
    expect(diagSection).toContain('period');
  });

  test('E4. toMonitoring supports period params', () => {
    const monSection = src.split('function toMonitoring')[1].split('function ')[0];
    expect(monSection).toContain('period');
  });
});
