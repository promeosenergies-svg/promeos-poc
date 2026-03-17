/**
 * PROMEOS — Sprint V22 "Consommations Expert : Analyse & Insights" — Pure-logic tests
 * Covers:
 *   - computeInsightKpis (InsightsPanel)
 *   - extractValues (InsightsPanel)
 *   - percentile (InsightsPanel)
 *   - getAvailableGranularities with samplingMinutes intersection (helpers)
 *
 * All tests run in Vitest node environment (no DOM).
 */
import { describe, it, expect } from 'vitest';
import { computeInsightKpis, extractValues, percentile } from '../consumption/InsightsPanel';
import { getAvailableGranularities } from '../consumption/helpers';

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeSeries(values) {
  return [
    {
      key: 'agg',
      label: 'Total',
      data: values.map((v, i) => ({ t: `2025-01-${String(i + 1).padStart(2, '0')}`, v })),
    },
  ];
}

// ── extractValues ─────────────────────────────────────────────────────────────

describe('extractValues', () => {
  it('returns empty array for empty seriesData', () => {
    expect(extractValues([])).toHaveLength(0);
  });

  it('returns empty array for null seriesData', () => {
    expect(extractValues(null)).toHaveLength(0);
  });

  it('filters out null and NaN values', () => {
    const series = [
      {
        key: 'agg',
        data: [
          { t: 't1', v: 100 },
          { t: 't2', v: null },
          { t: 't3', v: NaN },
          { t: 't4', v: 200 },
        ],
      },
    ];
    const result = extractValues(series);
    expect(result).toHaveLength(2);
    expect(result).toContain(100);
    expect(result).toContain(200);
  });

  it('collects values from multiple series', () => {
    const series = [
      {
        key: 's1',
        data: [
          { t: 't1', v: 10 },
          { t: 't2', v: 20 },
        ],
      },
      {
        key: 's2',
        data: [
          { t: 't1', v: 30 },
          { t: 't2', v: 40 },
        ],
      },
    ];
    expect(extractValues(series)).toHaveLength(4);
  });
});

// ── percentile ────────────────────────────────────────────────────────────────

describe('percentile', () => {
  it('P50 of [1,2,3,4,5] → 3', () => {
    expect(percentile([1, 2, 3, 4, 5], 50)).toBeCloseTo(3);
  });

  it('P0 → first element', () => {
    expect(percentile([5, 10, 15], 0)).toBe(5);
  });

  it('P100 → last element', () => {
    expect(percentile([5, 10, 15], 100)).toBe(15);
  });

  it('empty array → 0', () => {
    expect(percentile([], 50)).toBe(0);
  });

  it('P95 of 100-element array is near the upper end', () => {
    const arr = Array.from({ length: 100 }, (_, i) => i + 1); // [1..100]
    // P95: idx = 0.95 * 99 = 94.05 → arr[94] + 0.05 * (arr[95] - arr[94]) = 95 + 0.05 = 95.05
    expect(percentile(arr, 95)).toBeCloseTo(95.05, 1);
  });
});

// ── computeInsightKpis ────────────────────────────────────────────────────────

describe('computeInsightKpis', () => {
  it('empty seriesData → all zeros, n_valid=0', () => {
    const kpis = computeInsightKpis([], 90);
    expect(kpis.n_valid).toBe(0);
    expect(kpis.total_kwh).toBe(0);
    expect(kpis.avg_per_day).toBe(0);
    expect(kpis.p95).toBe(0);
    expect(kpis.p05).toBe(0);
    expect(kpis.load_factor).toBe(0);
    expect(kpis.anomaly_count).toBe(0);
  });

  it('10 equal values of 100 → total=1000, avg=1000/days, load_factor=1', () => {
    const series = makeSeries(Array(10).fill(100));
    const kpis = computeInsightKpis(series, 10);
    expect(kpis.total_kwh).toBe(1000);
    expect(kpis.avg_per_day).toBe(100);
    expect(kpis.load_factor).toBeCloseTo(1, 2); // avg/p95 = 100/100
    expect(kpis.n_valid).toBe(10);
  });

  it('P95 is above P05 for varied data', () => {
    const values = Array.from({ length: 100 }, (_, i) => i + 1); // 1..100
    const series = makeSeries(values);
    const kpis = computeInsightKpis(series, 100);
    expect(kpis.p95).toBeGreaterThan(kpis.p05);
    expect(kpis.p95).toBeGreaterThan(90);
    expect(kpis.p05).toBeLessThan(10);
  });

  it('anomaly_count: spike values above P99 are counted', () => {
    // 99 normal values + 1 extreme spike (10x)
    const values = [...Array.from({ length: 99 }, () => 100), 10000];
    const series = makeSeries(values);
    const kpis = computeInsightKpis(series, 100);
    // The spike at 10000 should be counted as anomaly (P99 ~= 100)
    expect(kpis.anomaly_count).toBeGreaterThan(0);
  });

  it('no anomalies when all values equal', () => {
    const series = makeSeries(Array(50).fill(100));
    const kpis = computeInsightKpis(series, 50);
    // All values are at P99 → anomaly_threshold = P99 = 100 → no value > 100
    expect(kpis.anomaly_count).toBe(0);
  });
});

// ── getAvailableGranularities with samplingMinutes intersection ───────────────

describe('getAvailableGranularities — samplingMinutes intersection (V22-B)', () => {
  it('samplingMinutes=null → behaves as period-only (backward compat)', () => {
    const keys = getAvailableGranularities(90, null).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('daily');
    expect(keys).toContain('monthly');
    expect(keys).not.toContain('15min'); // period > 14d
    expect(keys).not.toContain('30min'); // period > 14d
  });

  it('samplingMinutes=1440 (daily) → 15min, 30min and hourly excluded even within period window', () => {
    // days=7 normally includes 15min, 30min and hourly, but daily data can't be sub-hourly
    const keys = getAvailableGranularities(7, 1440).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('daily');
    expect(keys).not.toContain('15min');
    expect(keys).not.toContain('30min');
    expect(keys).not.toContain('hourly');
  });

  it('samplingMinutes=30 → 30min and coarser available for short period, 15min excluded', () => {
    const keys = getAvailableGranularities(7, 30).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).not.toContain('15min'); // 15 < 30 sampling
    expect(keys).toContain('30min');
    expect(keys).toContain('hourly');
    expect(keys).toContain('daily');
  });

  it('samplingMinutes=15 → 15min available for short period', () => {
    const keys = getAvailableGranularities(7, 15).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('15min');
    expect(keys).toContain('30min');
    expect(keys).toContain('hourly');
    expect(keys).toContain('daily');
  });

  it('samplingMinutes=60 (hourly) → 15min and 30min excluded', () => {
    const keys = getAvailableGranularities(7, 60).map((g) => g.key);
    expect(keys).not.toContain('15min');
    expect(keys).not.toContain('30min');
    expect(keys).toContain('hourly');
  });

  it('always includes auto regardless of samplingMinutes', () => {
    expect(getAvailableGranularities(7, 1440).map((g) => g.key)).toContain('auto');
    expect(getAvailableGranularities(90, 30).map((g) => g.key)).toContain('auto');
    expect(getAvailableGranularities(365, 43200).map((g) => g.key)).toContain('auto');
  });
});
