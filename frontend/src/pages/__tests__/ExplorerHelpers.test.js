/**
 * PROMEOS — Tests for Explorer WoW helpers.
 *
 * Couvre : aggregateSeries, convertUnit, colorForSite,
 * interpretClimateSensitivity.
 *
 * Sprint Énergie P0.S1c (2026-05-29) — tests `computeInsights` retirés :
 * la fonction et le module `consumption/insightRules.js` ont été
 * supprimés. Migration vers backend SoT canonique
 * `services.explorer_insights_service.build_explorer_insights`
 * (cf. backend/tests/services/test_explorer_insights_service.py — 28
 * cas verts couvrant les 6 règles + tri sévérité + provenance).
 */
import { describe, it, expect } from 'vitest';
import {
  aggregateSeries,
  convertUnit,
  colorForSite,
  interpretClimateSensitivity,
} from '../consumption/helpers';

// ── aggregateSeries ───────────────────────────────────────────────────────

describe('aggregateSeries', () => {
  const siteA = [
    { date: 'd1', kwh: 100 },
    { date: 'd2', kwh: 200 },
  ];
  const siteB = [
    { date: 'd1', kwh: 50 },
    { date: 'd2', kwh: 150 },
  ];

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

  it('agrege: aligns by date with mismatched data lengths', () => {
    const short = [{ date: 'd1', kwh: 50 }]; // missing d2
    const result = aggregateSeries({ s1: siteA, s2: short }, 'agrege');
    expect(result).toHaveLength(2);
    expect(result[0].kwh).toBe(150); // 100 + 50
    expect(result[1].kwh).toBe(200); // 200 + 0 (s2 missing d2)
  });

  it('agrege: handles non-overlapping dates', () => {
    const onlyD3 = [{ date: 'd3', kwh: 99 }];
    const result = aggregateSeries({ s1: siteA, s2: onlyD3 }, 'agrege');
    expect(result).toHaveLength(3); // d1, d2, d3
    expect(result.find((r) => r.date === 'd1').kwh).toBe(100);
    expect(result.find((r) => r.date === 'd3').kwh).toBe(99);
  });

  it('superpose: aligns by date with gaps', () => {
    const short = [{ date: 'd2', kwh: 77 }]; // only d2
    const result = aggregateSeries({ s1: siteA, s2: short }, 'superpose');
    expect(result).toHaveLength(2);
    expect(result.find((r) => r.date === 'd1').kwh_s2).toBeNull();
    expect(result.find((r) => r.date === 'd2').kwh_s2).toBe(77);
  });

  it('agrege: uses p50 fallback when kwh missing', () => {
    const p50Data = [
      { date: 'd1', p50: 30 },
      { date: 'd2', p50: 40 },
    ];
    const result = aggregateSeries({ s1: siteA, s2: p50Data }, 'agrege');
    expect(result[0].kwh).toBe(130); // 100 + 30
    expect(result[1].kwh).toBe(240); // 200 + 40
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

  it('eur: default price 0.068 (spot bridgé)', () => {
    expect(convertUnit(100, 'eur')).toBeCloseTo(6.8, 1);
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

  it('wraps around after 12 sites', () => {
    expect(colorForSite('s0', 0)).toBe(colorForSite('s12', 12));
  });

  it('different indices get different colors (first 12)', () => {
    const colors = Array.from({ length: 12 }, (_, i) => colorForSite('s', i));
    expect(new Set(colors).size).toBe(12);
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

// ── Sprint Énergie P0.S1c (2026-05-29) ─────────────────────────────────────
// Tests `computeInsights` retirés : la fonction a été migrée vers backend
// (services.explorer_insights_service.build_explorer_insights, cf.
// backend/tests/services/test_explorer_insights_service.py 28 cas verts).
// Le fichier consumption/insightRules.js a été supprimé.
