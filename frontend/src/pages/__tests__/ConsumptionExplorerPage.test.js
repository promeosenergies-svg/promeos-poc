/**
 * PROMEOS — Tests for ConsumptionExplorerPage helpers
 * Covers: stableColor, normalizeIndex100, sigInsights
 */
import { describe, it, expect } from 'vitest';
import { stableColor, normalizeIndex100, sigInsights } from '../ConsumptionExplorerPage';

describe('stableColor', () => {
  it('returns a valid hsl string', () => {
    const color = stableColor('site_1');
    expect(color).toMatch(/^hsl\(\d+,\s*\d+%,\s*\d+%\)$/);
  });

  it('is deterministic', () => {
    expect(stableColor('abc')).toBe(stableColor('abc'));
  });

  it('different keys produce different colors', () => {
    expect(stableColor('site_1')).not.toBe(stableColor('site_2'));
  });
});

describe('normalizeIndex100', () => {
  const data = [
    { t: '2025-01-01', a: 200, b: 50 },
    { t: '2025-01-02', a: 400, b: 100 },
    { t: '2025-01-03', a: 300, b: 75 },
  ];

  it('first value becomes 100', () => {
    const result = normalizeIndex100(data, ['a', 'b']);
    expect(result[0].a).toBe(100);
    expect(result[0].b).toBe(100);
  });

  it('second value is proportional', () => {
    const result = normalizeIndex100(data, ['a']);
    expect(result[1].a).toBe(200); // 400/200 * 100
  });

  it('preserves temp field', () => {
    const withTemp = data.map((d, i) => ({ ...d, temp: 10 + i }));
    const result = normalizeIndex100(withTemp, ['a']);
    expect(result[0].temp).toBe(10);
    expect(result[2].temp).toBe(12);
  });

  it('preserves temp_env field', () => {
    const withEnv = data.map((d, i) => ({ ...d, temp_env: [5 + i, 15 + i] }));
    const result = normalizeIndex100(withEnv, ['a']);
    expect(result[0].temp_env).toEqual([5, 15]);
    expect(result[2].temp_env).toEqual([7, 17]);
  });

  it('returns empty for empty input', () => {
    expect(normalizeIndex100([], ['a'])).toEqual([]);
  });
});

describe('sigInsights', () => {
  it('returns empty for null', () => {
    expect(sigInsights(null)).toEqual({});
  });

  it('high R² is ok', () => {
    const ins = sigInsights({ r_squared: 0.92, base_kwh: 150, a_heating: 0.5, b_cooling: 0.2 });
    expect(ins.r2.status).toBe('ok');
    expect(ins.r2.phrase).toContain('fiable');
  });

  it('medium R² is warn', () => {
    const ins = sigInsights({ r_squared: 0.70, base_kwh: 100, a_heating: 1, b_cooling: 0.5 });
    expect(ins.r2.status).toBe('warn');
  });

  it('low R² is crit', () => {
    const ins = sigInsights({ r_squared: 0.30, base_kwh: 50, a_heating: 0, b_cooling: 0 });
    expect(ins.r2.status).toBe('crit');
  });

  it('high heating slope is crit', () => {
    const ins = sigInsights({ r_squared: 0.90, base_kwh: 200, a_heating: 5, b_cooling: 0 });
    expect(ins.heat.status).toBe('crit');
    expect(ins.heat.phrase).toContain('Forte');
  });

  it('moderate cooling slope is warn', () => {
    const ins = sigInsights({ r_squared: 0.85, base_kwh: 100, a_heating: 0, b_cooling: 2 });
    expect(ins.cool.status).toBe('warn');
    expect(ins.cool.phrase).toContain('moderee');
  });

  it('zero base is warn', () => {
    const ins = sigInsights({ r_squared: 0.85, base_kwh: 0, a_heating: 0, b_cooling: 0 });
    expect(ins.base.status).toBe('warn');
  });

  it('positive base is ok', () => {
    const ins = sigInsights({ r_squared: 0.85, base_kwh: 100, a_heating: 0, b_cooling: 0 });
    expect(ins.base.status).toBe('ok');
    expect(ins.base.phrase).toContain('100');
  });
});
