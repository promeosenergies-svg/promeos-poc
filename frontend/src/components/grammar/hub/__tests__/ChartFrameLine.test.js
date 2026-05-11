/**
 * grammar/hub/charts/ChartFrameLine — source-guards Vitest (Phase F.2)
 *
 * Pattern pure-grep readFileSync (env=node, aligne sur HubKpiCard.test.js).
 *
 * 6 tests couvrent :
 *   1. data-component="ChartFrameLine" (source-guard primitif)
 *   2. 2 series support (seriesHP + seriesHC) avec data-series="hp"/"hc"
 *   3. threshold optionnel (dashed line + label)
 *   4. JSDoc @typedef TimePoint + Threshold (contrat API)
 *   5. Fallback synthetique generateSyntheticHC si aucune serie fournie
 *   6. zero hex hardcoded (tokens-only)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../charts/ChartFrameLine.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/charts/ChartFrameLine', () => {
  it('data-component="ChartFrameLine" pose au root <svg>', () => {
    expect(read()).toContain('data-component="ChartFrameLine"');
  });

  it('2 series support (data-series="hp" + data-series="hc")', () => {
    const src = read();
    expect(src).toContain('data-series="hp"');
    expect(src).toContain('data-series="hc"');
    expect(src).toContain('STROKE_HP');
    expect(src).toContain('STROKE_HC');
    expect(src).toContain("'var(--sol-hph-fg)'");
    expect(src).toContain("'var(--sol-hch-fg)'");
  });

  it('threshold optionnel (dashed line + label)', () => {
    const src = read();
    expect(src).toContain('STROKE_THRESHOLD');
    expect(src).toContain("'var(--sol-refuse-line)'");
    expect(src).toContain('strokeDasharray="1.5,1.5"');
    expect(src).toContain('data-threshold-line');
    expect(src).toContain('data-has-threshold');
  });

  it('JSDoc @typedef TimePoint + Threshold (contrat API)', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} TimePoint');
    expect(src).toContain('@typedef {Object} Threshold');
    expect(src).toContain('@param {TimePoint[]}');
    expect(src).toContain('@param {Threshold}');
  });

  it('fallback synthetique generateSyntheticHC si aucune serie fournie', () => {
    const src = read();
    expect(src).toContain('function generateSyntheticHC');
    // Profil HELIOS demo : creux 0h-6h, plateau jour, pic 18h-20h
    expect(src).toMatch(/if\s*\(h\s*<\s*6\)/);
    expect(src).toMatch(/if\s*\(h\s*<\s*21\)/);
  });

  it('zero hex hardcoded (tokens-only doctrine §6.5)', () => {
    const src = read();
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
