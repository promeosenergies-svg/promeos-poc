/**
 * PROMEOS — Sprint V21 "Analyse World-Class" — Pure-logic tests
 * Covers: getAvailableGranularities, aggregateToHeatmap, MeteoPanel helpers, gas CTA logic
 *
 * All tests run in Vitest node environment (no DOM).
 */
import { describe, it, expect } from 'vitest';
import { getAvailableGranularities } from '../consumption/helpers';
import { aggregateToHeatmap } from '../consumption/SignaturePanel';
import { generateSyntheticTemp, computeCorrelation } from '../consumption/MeteoPanel';

// ── getAvailableGranularities ─────────────────────────────────────────────────

describe('getAvailableGranularities', () => {
  it('days=7: includes auto, 15min, 30min, hourly, daily; excludes monthly', () => {
    const keys = getAvailableGranularities(7).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('15min');
    expect(keys).toContain('30min');
    expect(keys).toContain('hourly');
    expect(keys).toContain('daily');
    expect(keys).not.toContain('monthly');
  });

  it('days=90: includes auto, daily, monthly; excludes 15min and 30min', () => {
    const keys = getAvailableGranularities(90).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('daily');
    expect(keys).toContain('monthly');
    expect(keys).not.toContain('15min');
    expect(keys).not.toContain('30min');
  });

  it('days=365: includes auto, daily, monthly; excludes 15min, 30min and hourly', () => {
    const keys = getAvailableGranularities(365).map((g) => g.key);
    expect(keys).toContain('auto');
    expect(keys).toContain('daily');
    expect(keys).toContain('monthly');
    expect(keys).not.toContain('15min');
    expect(keys).not.toContain('30min');
    expect(keys).not.toContain('hourly');
  });

  it('always includes "auto" for any days value', () => {
    [1, 7, 30, 90, 180, 365].forEach((d) => {
      const keys = getAvailableGranularities(d).map((g) => g.key);
      expect(keys).toContain('auto');
    });
  });
});

// ── Signature heatmap aggregation ─────────────────────────────────────────────

describe('aggregateToHeatmap', () => {
  it('empty seriesData → returns empty array', () => {
    expect(aggregateToHeatmap([])).toEqual([]);
    expect(aggregateToHeatmap(null)).toEqual([]);
    expect(aggregateToHeatmap([{ data: [] }])).toEqual([]);
  });

  it('single data point → produces exactly one heatmap cell', () => {
    const seriesData = [
      {
        key: 'agg',
        data: [{ t: '2025-01-06T10:00:00', v: 42.5 }], // Monday (getDay=1 → frDay=0)
      },
    ];
    const cells = aggregateToHeatmap(seriesData);
    expect(cells.length).toBeGreaterThan(0);
    const cell = cells.find((c) => c.day === 0 && c.hour === 10);
    expect(cell).toBeDefined();
    expect(cell.avg_kwh).toBe(42.5);
  });

  it('two points same slot → averages correctly (not sums)', () => {
    const seriesData = [
      {
        key: 'agg',
        data: [
          { t: '2025-01-06T10:00:00', v: 40.0 }, // Monday 10h
          { t: '2025-01-13T10:00:00', v: 60.0 }, // Monday 10h next week
        ],
      },
    ];
    const cells = aggregateToHeatmap(seriesData);
    const cell = cells.find((c) => c.day === 0 && c.hour === 10);
    expect(cell).toBeDefined();
    expect(cell.avg_kwh).toBe(50); // average of 40 and 60
  });

  it('null or NaN values are skipped', () => {
    const seriesData = [
      {
        key: 'agg',
        data: [
          { t: '2025-01-06T10:00:00', v: null },
          { t: '2025-01-06T10:00:00', v: undefined },
          { t: '2025-01-06T10:00:00', v: NaN },
          { t: '2025-01-06T11:00:00', v: 30.0 },
        ],
      },
    ];
    const cells = aggregateToHeatmap(seriesData);
    const cell10 = cells.find((c) => c.day === 0 && c.hour === 10);
    const cell11 = cells.find((c) => c.day === 0 && c.hour === 11);
    expect(cell10).toBeUndefined(); // no valid data
    expect(cell11).toBeDefined();
    expect(cell11.avg_kwh).toBe(30);
  });
});

// ── MeteoPanel synthetic temperature ──────────────────────────────────────────

describe('generateSyntheticTemp', () => {
  it('summer date (July 15) → temperature > 18°C', () => {
    const t = generateSyntheticTemp('2025-07-15T12:00:00');
    expect(t).toBeGreaterThan(18);
  });

  it('winter date (January 15) → temperature < 10°C', () => {
    const t = generateSyntheticTemp('2025-01-15T12:00:00');
    expect(t).toBeLessThan(10);
  });

  it('returns a number between -5 and 40°C for any valid date', () => {
    const dates = ['2025-01-01', '2025-04-01', '2025-07-01', '2025-10-01'];
    for (const d of dates) {
      const t = generateSyntheticTemp(d);
      expect(t).toBeGreaterThan(-5);
      expect(t).toBeLessThan(40);
    }
  });
});

// ── computeCorrelation ────────────────────────────────────────────────────────

describe('computeCorrelation', () => {
  it('perfect positive correlation → 1.0', () => {
    const r = computeCorrelation([1, 2, 3], [1, 2, 3]);
    expect(r).toBeCloseTo(1.0, 5);
  });

  it('perfect negative correlation → -1.0', () => {
    const r = computeCorrelation([1, 2, 3], [3, 2, 1]);
    expect(r).toBeCloseTo(-1.0, 5);
  });

  it('empty or mismatched arrays → 0', () => {
    expect(computeCorrelation([], [])).toBe(0);
    expect(computeCorrelation([1, 2], [1])).toBe(0);
    expect(computeCorrelation(null, [1, 2])).toBe(0);
  });
});

// ── Gas demo CTA logic ────────────────────────────────────────────────────────

describe('Gas demo CTA logic (hasGasData)', () => {
  // Helper mirrors the logic in TimeseriesPanel/GasPanel: show CTA when no data
  function hasGasData(seriesData) {
    if (!seriesData?.length) return false;
    return seriesData.some((s) => s.data && s.data.length > 0 && s.data.some((p) => p.v != null));
  }

  function generateDemoEndpoint(siteId, energyVector) {
    return `/api/ems/demo/generate_timeseries?site_id=${siteId}&days=90&energy_vector=${energyVector}`;
  }

  it('empty series → false (show CTA)', () => {
    expect(hasGasData([])).toBe(false);
    expect(hasGasData(null)).toBe(false);
  });

  it('series with valid data → true (hide CTA)', () => {
    expect(hasGasData([{ key: 'agg', data: [{ t: '2025-01-01', v: 150 }] }])).toBe(true);
  });

  it('series with all-null values → false (show CTA)', () => {
    expect(hasGasData([{ key: 'agg', data: [{ t: '2025-01-01', v: null }] }])).toBe(false);
  });

  it('generateDemoEndpoint returns correct URL for gas', () => {
    const url = generateDemoEndpoint(5, 'gas');
    expect(url).toBe('/api/ems/demo/generate_timeseries?site_id=5&days=90&energy_vector=gas');
  });
});
