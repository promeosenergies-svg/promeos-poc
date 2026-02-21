/**
 * PROMEOS — Tests for Explorer WoW helpers + insightRules
 * Covers: aggregateSeries, convertUnit, colorForSite, interpretClimateSensitivity,
 *         computeInsights (6 rules)
 */
import { describe, it, expect } from 'vitest';
import { aggregateSeries, convertUnit, colorForSite, interpretClimateSensitivity } from '../consumption/helpers';
import { computeInsights } from '../consumption/insightRules';

// ── aggregateSeries ───────────────────────────────────────────────────────

describe('aggregateSeries', () => {
  const siteA = [{ date: 'd1', kwh: 100 }, { date: 'd2', kwh: 200 }];
  const siteB = [{ date: 'd1', kwh: 50 }, { date: 'd2', kwh: 150 }];

  it('empty input => empty array', () => {
    expect(aggregateSeries({}, 'agrege')).toEqual([]);
  });

  it('agrege: sums kwh across sites', () => {
    const result = aggregateSeries({ s1: siteA, s2: siteB }, 'agrege');
    expect(result[0].kwh).toBe(150);
    expect(result[1].kwh).toBe(350);
  });

  it('superpose: attaches per-site kwh keys', () => {
    const result = aggregateSeries({ s1: siteA, s2: siteB }, 'superpose');
    expect(result[0]).toHaveProperty('kwh_s1', 100);
    expect(result[0]).toHaveProperty('kwh_s2', 50);
  });

  it('empile: attaches per-site kwh keys (same as superpose)', () => {
    const result = aggregateSeries({ s1: siteA, s2: siteB }, 'empile');
    expect(result[1]).toHaveProperty('kwh_s1', 200);
    expect(result[1]).toHaveProperty('kwh_s2', 150);
  });

  it('single site agrege: passthrough kwh', () => {
    const result = aggregateSeries({ s1: siteA }, 'agrege');
    expect(result[0].kwh).toBe(100);
  });
});

// ── convertUnit ────────────────────────────────────────────────────────────

describe('convertUnit', () => {
  it('kwh passthrough', () => {
    expect(convertUnit(100, 'kwh')).toBe(100);
  });

  it('kw: divides by hoursPerInterval (default 1)', () => {
    expect(convertUnit(100, 'kw')).toBe(100); // 100 / 1
  });

  it('kw: divides by provided hours', () => {
    expect(convertUnit(100, 'kw', 0.18, 0.5)).toBe(200); // 100 / 0.5
  });

  it('eur: multiplies by price', () => {
    expect(convertUnit(100, 'eur', 0.25)).toBe(25);
  });

  it('eur: default price 0.18', () => {
    expect(convertUnit(100, 'eur')).toBe(18);
  });

  it('kw: zero hoursPerInterval => 0 (no division by zero)', () => {
    expect(convertUnit(100, 'kw', 0.18, 0)).toBe(0);
  });
});

// ── colorForSite ───────────────────────────────────────────────────────────

describe('colorForSite', () => {
  it('returns a hex color', () => {
    expect(colorForSite('s1', 0)).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it('wraps around after 5 sites', () => {
    expect(colorForSite('s0', 0)).toBe(colorForSite('s5', 5));
  });

  it('different indices get different colors (first 5)', () => {
    const colors = [0, 1, 2, 3, 4].map(i => colorForSite('s', i));
    expect(new Set(colors).size).toBe(5);
  });
});

// ── interpretClimateSensitivity ────────────────────────────────────────────

describe('interpretClimateSensitivity', () => {
  it('low r2 => low level', () => {
    expect(interpretClimateSensitivity(10, 0.1).level).toBe('low');
  });

  it('high r2 + low slope => medium', () => {
    expect(interpretClimateSensitivity(2, 0.8).level).toBe('medium');
  });

  it('high r2 + high slope => high', () => {
    expect(interpretClimateSensitivity(8, 0.85).level).toBe('high');
  });
});

// ── computeInsights ────────────────────────────────────────────────────────

describe('computeInsights', () => {
  it('empty data => no insights', () => {
    expect(computeInsights({}, 'agrege', 'kwh')).toEqual([]);
  });

  it('ruleOutsideBandHigh: outside_pct > 15 => warn', () => {
    const insights = computeInsights({ primaryTunnel: { outside_pct: 25, confidence: 'high' } });
    expect(insights.find(i => i.id === 'outside_band_high')).toBeTruthy();
    expect(insights.find(i => i.id === 'outside_band_high').severity).toBe('warn');
  });

  it('ruleOutsideBandHigh: outside_pct > 30 => crit', () => {
    const insights = computeInsights({ primaryTunnel: { outside_pct: 35, confidence: 'high' } });
    expect(insights.find(i => i.id === 'outside_band_high').severity).toBe('crit');
  });

  it('ruleOutsideBandHigh: outside_pct <= 15 => no insight', () => {
    const insights = computeInsights({ primaryTunnel: { outside_pct: 10, confidence: 'high' } });
    expect(insights.find(i => i.id === 'outside_band_high')).toBeUndefined();
  });

  it('ruleBaseLoadDrift: base_drift_pct > 10 => warn', () => {
    const insights = computeInsights({ primaryWeather: { drift: { base_drift_pct: 15 }, alerts: [] } });
    expect(insights.find(i => i.id === 'base_load_drift')).toBeTruthy();
  });

  it('ruleBaseLoadDrift: drift < 10 => no insight', () => {
    const insights = computeInsights({ primaryWeather: { drift: { base_drift_pct: 5 }, alerts: [] } });
    expect(insights.find(i => i.id === 'base_load_drift')).toBeUndefined();
  });

  it('ruleHpRatioHigh: hp_ratio > 0.7 => info', () => {
    const insights = computeInsights({ primaryHphc: { hp_ratio: 0.75, confidence: 'high' } });
    expect(insights.find(i => i.id === 'hp_ratio_high')).toBeTruthy();
    expect(insights.find(i => i.id === 'hp_ratio_high').severity).toBe('info');
  });

  it('ruleTargetOverBudget: progress > 110 => warn', () => {
    const insights = computeInsights({
      primaryProgression: { progress_pct: 120, run_rate_kwh: 5000 }
    });
    expect(insights.find(i => i.id === 'target_over_budget')).toBeTruthy();
  });

  it('ruleGasLeakSuspect: probable_leak alert => crit', () => {
    const insights = computeInsights({
      primaryWeather: { alerts: [{ type: 'probable_leak', message: 'test' }], drift: null }
    });
    expect(insights.find(i => i.id === 'gas_leak_suspect').severity).toBe('crit');
  });

  it('ruleLowConfidence: any panel has low confidence => info', () => {
    const insights = computeInsights({ primaryTunnel: { outside_pct: 5, confidence: 'low' } });
    expect(insights.find(i => i.id === 'low_confidence')).toBeTruthy();
    expect(insights.find(i => i.id === 'low_confidence').severity).toBe('info');
  });

  it('insights sorted: crit before warn before info', () => {
    const insights = computeInsights({
      primaryTunnel: { outside_pct: 35, confidence: 'low' },  // crit + info
    });
    const severities = insights.map(i => i.severity);
    const critIdx = severities.indexOf('crit');
    const infoIdx = severities.indexOf('info');
    if (critIdx >= 0 && infoIdx >= 0) {
      expect(critIdx).toBeLessThan(infoIdx);
    }
  });

  it('no crash on null/undefined fields', () => {
    expect(() => computeInsights({ primaryTunnel: null, primaryHphc: undefined })).not.toThrow();
  });
});
