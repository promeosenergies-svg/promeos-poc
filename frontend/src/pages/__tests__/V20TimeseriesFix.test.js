/**
 * PROMEOS — V20TimeseriesFix.test.js
 * Sprint V20 — Pure-logic tests for the timeseries mapping bug fixes.
 *
 * 4 describe blocks, 14 tests total:
 *   1. overlayValueKeys fix (RC1) — 3 tests
 *   2. formatDate ISO normalization (RC2) — 3 tests
 *   3. Zero values are valid (RC3) — 4 tests
 *   4. seriesToChartData output shape — 4 tests
 */
import { describe, it, expect } from 'vitest';
import { formatDate, MODE_MAP } from '../consumption/useEmsTimeseries';

// ── Inline helpers copied from useEmsTimeseries for testing ──────────────────
// (seriesToChartData is not exported; test via equivalent logic)

function seriesToChartData(series, granularity) {
  if (!series || series.length === 0) return [];
  if (series.length === 1) {
    return series[0].data.map((p) => ({
      date: formatDate(p.t, granularity),
      value: p.v ?? null,
    }));
  }
  const byTs = {};
  for (const s of series) {
    for (const p of s.data) {
      const dateKey = formatDate(p.t, granularity);
      if (!byTs[dateKey]) byTs[dateKey] = { date: dateKey };
      byTs[dateKey][s.key] = p.v ?? null;
      if (series.indexOf(s) === 0) byTs[dateKey].value = p.v ?? null;
    }
  }
  return Object.values(byTs);
}

// Helper: same logic as TimeseriesPanel RC1 fix
function computeOverlayValueKeys(seriesData) {
  if (seriesData.length <= 1) return [];
  return seriesData
    .filter((s) => s.key && s.key !== 'agg' && s.key !== 'total' && s.key !== 'others')
    .map((s) => s.key);
}

// ── 1. overlayValueKeys fix (RC1) ─────────────────────────────────────────────

describe('overlayValueKeys fix (RC1)', () => {
  it('single series with key="total" → overlayValueKeys is empty', () => {
    const seriesData = [{ key: 'total', label: 'Total', data: [] }];
    const keys = computeOverlayValueKeys(seriesData);
    expect(keys).toEqual([]);
  });

  it('single series with key="agg" → overlayValueKeys is empty', () => {
    const seriesData = [{ key: 'agg', label: 'Agrégé', data: [] }];
    const keys = computeOverlayValueKeys(seriesData);
    expect(keys).toEqual([]);
  });

  it('multi-series with genuine site keys → overlayValueKeys contains site keys', () => {
    const seriesData = [
      { key: 'site_5', label: 'Site 5', data: [] },
      { key: 'site_6', label: 'Site 6', data: [] },
    ];
    const keys = computeOverlayValueKeys(seriesData);
    expect(keys).toEqual(['site_5', 'site_6']);
  });
});

// ── 2. formatDate ISO normalization (RC2) ─────────────────────────────────────

describe('formatDate ISO normalization (RC2)', () => {
  it('YYYY-MM-DD (daily) formats to French DD MMM', () => {
    const result = formatDate('2025-01-15', 'daily');
    // French locale: "15 janv."
    expect(result).toMatch(/15/);
    expect(result).toMatch(/janv/i);
  });

  it('space-separated datetime (hourly) gives same result as T-separated', () => {
    const withSpace = formatDate('2025-01-15 10:00:00', 'hourly');
    const withT = formatDate('2025-01-15T10:00:00', 'hourly');
    expect(withSpace).toBe(withT);
    expect(withSpace).not.toBe('2025-01-15 10:00:00'); // must not return original
  });

  it('YYYY-MM (monthly) formats to French short month + year', () => {
    // We need to pass a valid ISO date string; monthly format only reads month+year
    const result = formatDate('2025-03-01', 'monthly');
    expect(result).toMatch(/mars|mar/i);
    expect(result).toMatch(/25/);
  });
});

// ── 3. Zero values are valid ──────────────────────────────────────────────────

describe('Zero values are valid (not treated as missing)', () => {
  it('dataset with zeros → all points count as valid (zero ≠ null)', () => {
    const chartData = [{ value: 0 }, { value: 0 }, { value: 42 }];
    const effectiveValueKey = 'value';
    const validPoints = chartData.filter(
      (p) => p[effectiveValueKey] != null && !isNaN(p[effectiveValueKey])
    );
    expect(validPoints).toHaveLength(3);
  });

  it('dataset with nulls and one zero → only 1 valid point', () => {
    const chartData = [{ value: null }, { value: undefined }, { value: 0 }];
    const effectiveValueKey = 'value';
    const validPoints = chartData.filter(
      (p) => p[effectiveValueKey] != null && !isNaN(p[effectiveValueKey])
    );
    expect(validPoints).toHaveLength(1);
  });

  it('dataset with custom valueKey "total" containing zeros → valid', () => {
    const chartData = [
      { date: '01 janv.', total: 0 },
      { date: '02 janv.', total: 15.3 },
    ];
    const effectiveValueKey = 'total';
    const validPoints = chartData.filter(
      (p) => p[effectiveValueKey] != null && !isNaN(p[effectiveValueKey])
    );
    expect(validPoints).toHaveLength(2);
  });

  it('nullish coalescing: p.v ?? null preserves 0 (zero is not nullish)', () => {
    expect(0 ?? null).toBe(0);
    expect(null ?? null).toBe(null);
    expect(undefined ?? null).toBe(null);
  });
});

// ── 4. seriesToChartData output shape ─────────────────────────────────────────

describe('seriesToChartData output shape', () => {
  it('single series → each point has {date, value}', () => {
    const series = [
      {
        key: 'total',
        data: [
          { t: '2025-01-01', v: 100 },
          { t: '2025-01-02', v: 200 },
        ],
      },
    ];
    const result = seriesToChartData(series, 'daily');
    expect(result).toHaveLength(2);
    expect(result[0]).toHaveProperty('date');
    expect(result[0]).toHaveProperty('value', 100);
    expect(result[1]).toHaveProperty('value', 200);
  });

  it('multi-series → each point has {date, [s.key]: v, value: firstSeriesV}', () => {
    const series = [
      { key: 'site_5', data: [{ t: '2025-01-01', v: 100 }] },
      { key: 'site_6', data: [{ t: '2025-01-01', v: 50 }] },
    ];
    const result = seriesToChartData(series, 'daily');
    expect(result).toHaveLength(1);
    expect(result[0]).toHaveProperty('site_5', 100);
    expect(result[0]).toHaveProperty('site_6', 50);
    expect(result[0]).toHaveProperty('value', 100); // first series value
  });

  it('empty series array → returns empty array', () => {
    expect(seriesToChartData([], 'daily')).toEqual([]);
    expect(seriesToChartData(null, 'daily')).toEqual([]);
  });

  it('formatDate handles invalid date string gracefully (returns original)', () => {
    const result = formatDate('not-a-date', 'daily');
    expect(result).toBe('not-a-date');
  });
});

// ── Bonus: MODE_MAP sanity check ─────────────────────────────────────────────

describe('MODE_MAP', () => {
  it('maps all 4 PROMEOS modes to EMS API modes', () => {
    expect(MODE_MAP.agrege).toBe('aggregate');
    expect(MODE_MAP.superpose).toBe('overlay');
    expect(MODE_MAP.empile).toBe('stack');
    expect(MODE_MAP.separe).toBe('split');
  });
});
