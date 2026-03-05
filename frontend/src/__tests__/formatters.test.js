/**
 * PROMEOS — Tests unitaires pour utils/format.js
 * Guards anti-NaN/Infinity/null + formatters centralisés.
 */
import { describe, it, expect } from 'vitest';
import {
  fmtEur,
  fmtEurFull,
  fmtKwh,
  fmtKw,
  fmtNum,
  fmtPct,
  fmtArea,
  fmtAreaCompact,
  fmtDateFR,
  fmtDateLong,
  fmtDateRange,
  formatPercentFR,
  pl,
} from '../utils/format';

// ── Guards universels ────────────────────────────────────────────────────────

describe('Guards — toutes fonctions retournent "—" pour valeurs invalides', () => {
  const fns = [
    ['fmtEur', fmtEur],
    ['fmtEurFull', fmtEurFull],
    ['fmtKwh', fmtKwh],
    ['fmtKw', fmtKw],
    ['fmtArea', fmtArea],
    ['fmtAreaCompact', fmtAreaCompact],
    ['formatPercentFR', formatPercentFR],
  ];

  for (const [name, fn] of fns) {
    it(`${name}(null) → '—'`, () => expect(fn(null)).toBe('—'));
    it(`${name}(undefined) → '—'`, () => expect(fn(undefined)).toBe('—'));
    it(`${name}(Infinity) → '—'`, () => expect(fn(Infinity)).toBe('—'));
    it(`${name}(-Infinity) → '—'`, () => expect(fn(-Infinity)).toBe('—'));
    it(`${name}(NaN) → '—'`, () => expect(fn(NaN)).toBe('—'));
  }

  it('fmtNum(null) → "—"', () => expect(fmtNum(null)).toBe('—'));
  it('fmtNum(Infinity) → "—"', () => expect(fmtNum(Infinity)).toBe('—'));
  it('fmtNum(NaN) → "—"', () => expect(fmtNum(NaN)).toBe('—'));

  it('fmtPct(null) → "—"', () => expect(fmtPct(null)).toBe('—'));
  it('fmtPct(Infinity) → "—"', () => expect(fmtPct(Infinity)).toBe('—'));
  it('fmtPct(NaN) → "—"', () => expect(fmtPct(NaN)).toBe('—'));
});

// ── fmtEur ────────────────────────────────────────────────────────────────────

describe('fmtEur', () => {
  it('0 → "—"', () => expect(fmtEur(0)).toBe('—'));
  it('850 → "850 €"', () => expect(fmtEur(850)).toBe('850 €'));
  it('23995 → "24 k€"', () => expect(fmtEur(23995)).toBe('24 k€'));
  it('1234567 → contient M€', () => expect(fmtEur(1234567)).toContain('M€'));
  it('negative → conserve le signe', () => expect(fmtEur(-5000)).toContain('k€'));
});

// ── fmtEurFull ────────────────────────────────────────────────────────────────

describe('fmtEurFull', () => {
  it('0 → "—"', () => expect(fmtEurFull(0)).toBe('—'));
  it('23995 → contient "€"', () => expect(fmtEurFull(23995)).toContain('€'));
});

// ── fmtKwh ────────────────────────────────────────────────────────────────────

describe('fmtKwh', () => {
  it('0 → "—"', () => expect(fmtKwh(0)).toBe('—'));
  it('500 → "500 kWh"', () => expect(fmtKwh(500)).toBe('500 kWh'));
  it('15000 → contient "k kWh"', () => expect(fmtKwh(15000)).toContain('k kWh'));
  it('1500000 → contient "GWh"', () => expect(fmtKwh(1500000)).toContain('GWh'));
});

// ── fmtKw ─────────────────────────────────────────────────────────────────────

describe('fmtKw', () => {
  it('0 → "—"', () => expect(fmtKw(0)).toBe('—'));
  it('750 → contient "kW"', () => expect(fmtKw(750)).toContain('kW'));
  it('1500 → contient "k kW"', () => expect(fmtKw(1500)).toContain('k kW'));
  it('2000000 → contient "MW"', () => expect(fmtKw(2000000)).toContain('MW'));
});

// ── fmtNum ────────────────────────────────────────────────────────────────────

describe('fmtNum', () => {
  it('entier sans unité', () => expect(fmtNum(1234, 0)).toMatch(/1[\s\u00A0.]?234/));
  it('avec décimales et unité', () => {
    const r = fmtNum(12.345, 2, '°C');
    expect(r).toContain('°C');
  });
  it('0 → "0"', () => expect(fmtNum(0, 0)).toBe('0'));
});

// ── fmtPct ────────────────────────────────────────────────────────────────────

describe('fmtPct', () => {
  it('ratio 0.85 → "85%"', () => expect(fmtPct(0.85)).toBe('85%'));
  it('ratio 0.851, 1 decimal → "85,1%"', () => expect(fmtPct(0.851, true, 1)).toBe('85,1%'));
  it('value 42, isRatio=false → "42%"', () => expect(fmtPct(42, false)).toBe('42%'));
  it('ratio 0 → "0%"', () => expect(fmtPct(0)).toBe('0%'));
});

// ── fmtArea ───────────────────────────────────────────────────────────────────

describe('fmtArea', () => {
  it('0 → "—"', () => expect(fmtArea(0)).toBe('—'));
  it('contient m²', () => expect(fmtArea(11562)).toContain('m²'));
});

// ── Dates ─────────────────────────────────────────────────────────────────────

describe('fmtDateFR', () => {
  it('null → "—"', () => expect(fmtDateFR(null)).toBe('—'));
  it('invalid → "—"', () => expect(fmtDateFR('not-a-date')).toBe('—'));
  it('valid → contient année', () => expect(fmtDateFR('2025-03-14')).toContain('2025'));
});

describe('fmtDateLong', () => {
  it('null → "—"', () => expect(fmtDateLong(null)).toBe('—'));
  it('valid → contient année', () => expect(fmtDateLong('2025-03-14')).toContain('2025'));
});

describe('fmtDateRange', () => {
  it('both null → "—"', () => expect(fmtDateRange(null, null)).toBe('—'));
  it('valid range → contient "—"', () => {
    const r = fmtDateRange('2025-03-01', '2025-06-01');
    expect(r).toContain('—');
    expect(r).toContain('2025');
  });
});

// ── formatPercentFR ───────────────────────────────────────────────────────────

describe('formatPercentFR', () => {
  it('NaN → "—"', () => expect(formatPercentFR(NaN)).toBe('—'));
  it('24 → contient %', () => expect(formatPercentFR(24)).toContain('%'));
});

// ── pl ────────────────────────────────────────────────────────────────────────

describe('pl', () => {
  it('1 site → pas de s', () => expect(pl(1, 'site')).toContain('site'));
  it('3 sites → s', () => expect(pl(3, 'site')).toContain('sites'));
});
