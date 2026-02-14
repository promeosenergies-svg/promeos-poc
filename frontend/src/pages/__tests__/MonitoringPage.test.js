/**
 * PROMEOS — Tests for MonitoringPage helpers
 * Covers: buildHeatmapGrid, kpiStatus
 */
import { describe, it, expect } from 'vitest';
import { buildHeatmapGrid, kpiStatus } from '../MonitoringPage';

describe('buildHeatmapGrid', () => {
  const weekday = Array.from({ length: 24 }, (_, i) => 10 + i);
  const weekend = Array.from({ length: 24 }, (_, i) => 5 + i * 0.5);

  it('returns 7x24 grid', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    expect(grid).toHaveLength(7);
    for (const row of grid) {
      expect(row).toHaveLength(24);
    }
  });

  it('Mon-Fri use weekday, Sat-Sun use weekend', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    // Monday (index 0) should match weekday
    expect(grid[0][0]).toBe(Number(weekday[0].toFixed(1)));
    expect(grid[4][12]).toBe(Number(weekday[12].toFixed(1)));
    // Saturday (index 5) should match weekend
    expect(grid[5][0]).toBe(Number(weekend[0].toFixed(1)));
    expect(grid[6][12]).toBe(Number(weekend[12].toFixed(1)));
  });

  it('returns null for null input', () => {
    expect(buildHeatmapGrid(null, null)).toBeNull();
    expect(buildHeatmapGrid(undefined, weekend)).toBeNull();
  });

  it('falls back to weekday when weekend is null', () => {
    const grid = buildHeatmapGrid(weekday, null);
    expect(grid[5][0]).toBe(Number(weekday[0].toFixed(1)));
    expect(grid[6][0]).toBe(Number(weekday[0].toFixed(1)));
  });

  it('all values are numbers', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    for (const row of grid) {
      for (const val of row) {
        expect(typeof val).toBe('number');
      }
    }
  });
});

describe('kpiStatus', () => {
  const thresholds = { ok: 80, warn: 60 };

  it('ok for high scores', () => {
    expect(kpiStatus(90, thresholds)).toBe('ok');
    expect(kpiStatus(80, thresholds)).toBe('ok');
  });

  it('surveiller for medium', () => {
    expect(kpiStatus(70, thresholds)).toBe('surveiller');
    expect(kpiStatus(60, thresholds)).toBe('surveiller');
  });

  it('critique for low', () => {
    expect(kpiStatus(50, thresholds)).toBe('critique');
    expect(kpiStatus(0, thresholds)).toBe('critique');
  });

  it('invert mode (risk: low=ok)', () => {
    const riskThresholds = { ok: 35, warn: 60 };
    expect(kpiStatus(20, riskThresholds, true)).toBe('ok');
    expect(kpiStatus(50, riskThresholds, true)).toBe('surveiller');
    expect(kpiStatus(80, riskThresholds, true)).toBe('critique');
  });

  it('null value returns no_data', () => {
    expect(kpiStatus(null, thresholds)).toBe('no_data');
    expect(kpiStatus(undefined, thresholds)).toBe('no_data');
  });

  it('zero is a real value (not no_data)', () => {
    expect(kpiStatus(0, thresholds)).toBe('critique');
    expect(kpiStatus(0, { ok: 35, warn: 60 }, true)).toBe('ok');
  });
});
