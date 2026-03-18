/**
 * PROMEOS — Step 10: Comparaison temporelle N vs N-1 source-guard tests
 * Verifie que le YoY compare est branche dans le backend et le frontend.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readBackend(relPath) {
  return readFileSync(join(__dirname, '..', '..', '..', 'backend', relPath), 'utf-8');
}

function readFrontend(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. Backend — timeseries_service.py ──────────────────────────────────────

describe('A. timeseries_service.py YoY support', () => {
  const src = readBackend('services/ems/timeseries_service.py');

  test('A1. query_timeseries has compare param', () => {
    expect(src).toMatch(/compare/);
  });

  test('A2. _query_yoy_prev function exists', () => {
    expect(src).toMatch(/def _query_yoy_prev/);
  });

  test('A3. _shift_timestamp_forward_1y function exists', () => {
    expect(src).toMatch(/def _shift_timestamp_forward_1y/);
  });

  test('A4. compare_summary function exists', () => {
    expect(src).toMatch(/def compare_summary/);
  });

  test('A5. _prev key suffix for YoY series', () => {
    expect(src).toMatch(/_prev/);
  });
});

// ── B. Backend — routes wiring ──────────────────────────────────────────────

describe('B. EMS routes YoY wiring', () => {
  const src = readBackend('routes/ems.py');

  test('B1. compare param in get_timeseries', () => {
    expect(src).toMatch(/compare/);
  });

  test('B2. compare-summary endpoint', () => {
    expect(src).toMatch(/compare-summary/);
  });

  test('B3. compare_summary imported', () => {
    expect(src).toMatch(/from services\.ems\.timeseries_service import compare_summary/);
  });
});

// ── C. Frontend — StickyFilterBar toggle ────────────────────────────────────

describe('C. StickyFilterBar compare toggle', () => {
  const src = readFrontend('pages/consumption/StickyFilterBar.jsx');

  test('C1. compareYoy prop exists', () => {
    expect(src).toMatch(/compareYoy/);
  });

  test('C2. setCompareYoy prop exists', () => {
    expect(src).toMatch(/setCompareYoy/);
  });

  test('C3. Comparer N-1 button text', () => {
    // Compact label "N-1" with full text in title attribute (#90)
    expect(src).toMatch(/N-1/);
  });

  test('C4. not-portfolio guard (no single-site restriction)', () => {
    expect(src).not.toMatch(/effectiveSiteIds\.length === 1/);
  });

  test('C5. not in portfolio mode guard', () => {
    expect(src).toMatch(/!isPortfolioMode/);
  });
});

// ── D. Frontend — useEmsTimeseries hook ─────────────────────────────────────

describe('D. useEmsTimeseries YoY support', () => {
  const src = readFrontend('pages/consumption/useEmsTimeseries.js');

  test('D1. compareYoy param accepted', () => {
    expect(src).toMatch(/compareYoy/);
  });

  test('D2. compare=yoy sent to API', () => {
    expect(src).toMatch(/compare.*yoy/);
  });
});

// ── E. Frontend — ExplorerChart _prev rendering ─────────────────────────────

describe('E. ExplorerChart _prev series rendering', () => {
  const src = readFrontend('pages/consumption/ExplorerChart.jsx');

  test('E1. total_prev series rendered', () => {
    expect(src).toMatch(/total_prev/);
  });

  test('E2. dashed strokeDasharray for _prev', () => {
    expect(src).toMatch(/strokeDasharray/);
  });

  test('E3. N-1 label in chart', () => {
    expect(src).toMatch(/N-1/);
  });

  test('E4. reduced opacity for _prev', () => {
    expect(src).toMatch(/strokeOpacity/);
  });
});

// ── F. Frontend — ConsoKpiHeader TrendDelta ─────────────────────────────────

describe('F. ConsoKpiHeader TrendDelta', () => {
  const src = readFrontend('components/ConsoKpiHeader.jsx');

  test('F1. TrendDelta component exists', () => {
    expect(src).toMatch(/TrendDelta/);
  });

  test('F2. compareSummary prop', () => {
    expect(src).toMatch(/compareSummary/);
  });

  test('F3. delta_pct displayed', () => {
    expect(src).toMatch(/delta_pct/);
  });

  test('F4. vs N-1 label', () => {
    expect(src).toMatch(/vs N-1/);
  });
});

// ── G. Frontend — API function ──────────────────────────────────────────────

describe('G. API compare-summary function', () => {
  const src = readFrontend('services/api.js');

  test('G1. getEmsCompareSummary function exists', () => {
    expect(src).toMatch(/getEmsCompareSummary/);
  });

  test('G2. calls /ems/timeseries/compare-summary', () => {
    expect(src).toMatch(/\/ems\/timeseries\/compare-summary/);
  });
});
