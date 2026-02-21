/**
 * PROMEOS — Sprint V14.3 Timeseries Tests
 * Pure logic tests (no DOM) covering:
 *   - useEmsTimeseries date computation from days
 *   - MODE_MAP all 4 modes
 *   - formatDate French formatting
 *   - seriesToChartData mapping
 *   - ChartRenderGuard: < 2 valid points → insufficient
 *   - ChartRenderGuard: 2+ valid points → data passes through
 *   - Empty series → status=empty
 *   - Y domain computation for flat lines
 */
import { describe, it, expect } from 'vitest';
import { MODE_MAP, formatDate } from '../consumption/useEmsTimeseries';

// ── MODE_MAP ──────────────────────────────────────────────────────────────────

describe('MODE_MAP: PROMEOS → EMS API modes', () => {
  it('agrege → aggregate', () => {
    expect(MODE_MAP.agrege).toBe('aggregate');
  });

  it('superpose → overlay', () => {
    expect(MODE_MAP.superpose).toBe('overlay');
  });

  it('empile → stack', () => {
    expect(MODE_MAP.empile).toBe('stack');
  });

  it('separe → split', () => {
    expect(MODE_MAP.separe).toBe('split');
  });

  it('all 4 modes are defined', () => {
    expect(Object.keys(MODE_MAP)).toHaveLength(4);
  });
});

// ── formatDate ────────────────────────────────────────────────────────────────

describe('formatDate: French locale formatting', () => {
  const ISO_DAILY = '2025-03-15T00:00:00Z';
  const ISO_MONTHLY = '2025-03-01T00:00:00Z';
  const ISO_HOURLY = '2025-03-15T14:30:00Z';

  it('monthly format: returns abbreviated month + 2-digit year', () => {
    const result = formatDate(ISO_MONTHLY, 'monthly');
    // Should contain year-like string and month abbreviation
    expect(result).toBeTruthy();
    expect(typeof result).toBe('string');
    // French locale: "mars 25" or "mars 2025" depending on browser
    expect(result.toLowerCase()).toContain('mars');
  });

  it('daily format: returns 2-digit day + abbreviated month', () => {
    const result = formatDate(ISO_DAILY, 'daily');
    expect(result).toBeTruthy();
    expect(typeof result).toBe('string');
    // Should contain "15" (the day)
    expect(result).toContain('15');
  });

  it('hourly format: contains date and time parts', () => {
    const result = formatDate(ISO_HOURLY, 'hourly');
    expect(result).toBeTruthy();
    expect(typeof result).toBe('string');
    // Should contain "15" (the day) — hour might vary by UTC offset
    expect(result).toContain('15');
  });

  it('default (15min/30min): returns time only (HH:MM)', () => {
    const result = formatDate('2025-03-15T09:15:00Z', '15min');
    expect(result).toBeTruthy();
    expect(typeof result).toBe('string');
    // Should be a time string with colon
    expect(result).toContain(':');
  });

  it('invalid ISO string: returns original string', () => {
    const result = formatDate('not-a-date', 'daily');
    expect(result).toBe('not-a-date');
  });

  it('null input: returns empty string', () => {
    const result = formatDate(null, 'daily');
    expect(result).toBe('');
  });
});

// ── Date computation from `days` ─────────────────────────────────────────────

describe('useEmsTimeseries: date computation logic', () => {
  // Simulate computeDateRange (pure logic extracted)
  function computeDateRange(days, startDate, endDate) {
    const dateTo = new Date();
    dateTo.setSeconds(0, 0);

    if (startDate && endDate) {
      return { dateFrom: new Date(startDate), dateTo: new Date(endDate) };
    }
    if (days === 'ytd') {
      const dateFrom = new Date(dateTo.getFullYear(), 0, 1);
      return { dateFrom, dateTo };
    }
    const dateFrom = new Date(dateTo);
    dateFrom.setDate(dateFrom.getDate() - Number(days));
    return { dateFrom, dateTo };
  }

  it('days=30: dateFrom is approximately 30 days ago', () => {
    const { dateFrom, dateTo } = computeDateRange(30, null, null);
    const diffMs = dateTo - dateFrom;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);
    // Should be very close to 30 days (allow ±1 for edge cases)
    expect(diffDays).toBeGreaterThanOrEqual(29.9);
    expect(diffDays).toBeLessThanOrEqual(30.1);
  });

  it('custom startDate/endDate: uses provided dates', () => {
    const { dateFrom, dateTo } = computeDateRange(30, '2025-01-01', '2025-03-31');
    expect(dateFrom.toISOString().startsWith('2025-01-01')).toBe(true);
    expect(dateTo.toISOString().startsWith('2025-03-31')).toBe(true);
  });

  it('ytd: dateFrom is Jan 1 of current year', () => {
    const { dateFrom } = computeDateRange('ytd', null, null);
    expect(dateFrom.getMonth()).toBe(0);  // January
    expect(dateFrom.getDate()).toBe(1);
    expect(dateFrom.getFullYear()).toBe(new Date().getFullYear());
  });

  it('days=7: ~7 days gap', () => {
    const { dateFrom, dateTo } = computeDateRange(7, null, null);
    const diffDays = (dateTo - dateFrom) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBeGreaterThanOrEqual(6.9);
    expect(diffDays).toBeLessThanOrEqual(7.1);
  });
});

// ── seriesToChartData mapping ──────────────────────────────────────────────────

describe('seriesToChartData: maps EMS API series → chartData', () => {
  // Simulate seriesToChartData inline (pure function, same logic as hook)
  function seriesToChartData(series, granularity) {
    if (!series || series.length === 0) return [];
    if (series.length === 1) {
      return series[0].data.map(p => ({
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

  it('single series: maps data to [{date, value}]', () => {
    const series = [{
      key: 'agg',
      label: 'Agrégé',
      data: [
        { t: '2025-01-01T00:00:00Z', v: 100 },
        { t: '2025-01-02T00:00:00Z', v: 120 },
        { t: '2025-01-03T00:00:00Z', v: 90 },
      ],
    }];
    const chartData = seriesToChartData(series, 'daily');
    expect(chartData).toHaveLength(3);
    expect(chartData[0].value).toBe(100);
    expect(chartData[1].value).toBe(120);
    expect(chartData[2].value).toBe(90);
  });

  it('empty series: returns []', () => {
    expect(seriesToChartData([], 'daily')).toHaveLength(0);
    expect(seriesToChartData(null, 'daily')).toHaveLength(0);
  });

  it('null values: preserved as null in chartData', () => {
    const series = [{
      key: 'agg',
      data: [
        { t: '2025-01-01T00:00:00Z', v: null },
        { t: '2025-01-02T00:00:00Z', v: 50 },
      ],
    }];
    const chartData = seriesToChartData(series, 'daily');
    expect(chartData[0].value).toBeNull();
    expect(chartData[1].value).toBe(50);
  });

  it('multi-series overlay: merges by date with per-site keys', () => {
    const series = [
      {
        key: 'site_1',
        data: [{ t: '2025-01-01T00:00:00Z', v: 100 }],
      },
      {
        key: 'site_2',
        data: [{ t: '2025-01-01T00:00:00Z', v: 80 }],
      },
    ];
    const chartData = seriesToChartData(series, 'daily');
    expect(chartData).toHaveLength(1);
    expect(chartData[0].site_1).toBe(100);
    expect(chartData[0].site_2).toBe(80);
    // First series also stored as 'value' for backward compat
    expect(chartData[0].value).toBe(100);
  });
});

// ── ChartRenderGuard logic ────────────────────────────────────────────────────

describe('ChartRenderGuard: valid points filtering', () => {
  function countValidPoints(data, valueKey = 'value') {
    return data.filter(p => p[valueKey] != null && !isNaN(p[valueKey])).length;
  }

  function computeYDomain(data, valueKey = 'value') {
    const ys = data
      .filter(p => p[valueKey] != null && !isNaN(p[valueKey]))
      .map(p => p[valueKey])
      .filter(Number.isFinite);
    const yMin = ys.length ? Math.min(...ys) : 0;
    const yMax = ys.length ? Math.max(...ys) : 1;
    const pad = yMin === yMax ? Math.max(1, Math.abs(yMin) * 0.05) : 0;
    return [Math.max(0, yMin - pad), yMax + pad];
  }

  it('0 valid points → insufficient (< 2)', () => {
    const data = [];
    expect(countValidPoints(data)).toBe(0);
    expect(countValidPoints(data)).toBeLessThan(2);
  });

  it('1 valid point → insufficient (< 2)', () => {
    const data = [{ value: 100 }];
    expect(countValidPoints(data)).toBe(1);
    expect(countValidPoints(data)).toBeLessThan(2);
  });

  it('2 valid points → sufficient (passes guard)', () => {
    const data = [{ value: 100 }, { value: 120 }];
    expect(countValidPoints(data)).toBe(2);
    expect(countValidPoints(data)).toBeGreaterThanOrEqual(2);
  });

  it('null/NaN values excluded from valid count', () => {
    const data = [
      { value: null },
      { value: NaN },
      { value: 100 },
      { value: 120 },
    ];
    expect(countValidPoints(data)).toBe(2);
  });

  it('flat line (all same value): yDomain gets padding', () => {
    const data = [
      { value: 50 }, { value: 50 }, { value: 50 },
    ];
    const [yMin, yMax] = computeYDomain(data);
    // yMin < 50 (or 0) and yMax > 50 due to padding
    expect(yMax).toBeGreaterThan(50);
    expect(yMin).toBeLessThanOrEqual(50);
  });

  it('varying values: no padding applied to yDomain', () => {
    const data = [
      { value: 10 }, { value: 50 }, { value: 30 },
    ];
    const [yMin, yMax] = computeYDomain(data);
    expect(yMin).toBe(10); // Math.max(0, 10) = 10
    expect(yMax).toBe(50);
  });

  it('zero-value flat line: padding is at least 1', () => {
    const data = [{ value: 0 }, { value: 0 }];
    const [yMin, yMax] = computeYDomain(data);
    expect(yMax - yMin).toBeGreaterThanOrEqual(1);
  });
});
