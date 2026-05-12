/**
 * grammar/hub/charts/ChartFrameBars — source-guards Vitest (Phase F.2)
 *
 * Pattern pure-grep readFileSync (env=node, pas de DOM, aligne sur
 * HubKpiCard.test.js / HubHighlight.test.js).
 *
 * 6 tests couvrent :
 *   1. data-component="ChartFrameBars" (source-guard primitif)
 *   2. TONE_FILL frozen object avec 4 tones (crit/warn/pos/neutral)
 *   3. resolveTone priorite (datum.tone > toneRules > neutral)
 *   4. JSDoc @typedef BarsDatum + ToneRule (contrat API)
 *   5. defensive null-render (data invalide / vide)
 *   6. zero hex hardcode (tokens-only)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../charts/ChartFrameBars.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/charts/ChartFrameBars', () => {
  it('data-component="ChartFrameBars" pose au root <svg>', () => {
    expect(read()).toContain('data-component="ChartFrameBars"');
  });

  it('TONE_FILL frozen + 4 tones (crit/warn/pos/neutral)', () => {
    const src = read();
    expect(src).toContain('TONE_FILL');
    expect(src).toContain('Object.freeze');
    expect(src).toContain("crit: 'var(--sol-refuse-line)'");
    expect(src).toContain("warn: 'var(--sol-attention-line)'");
    expect(src).toContain("pos: 'var(--sol-succes-line)'");
    expect(src).toContain("neutral: 'var(--sol-ink-300)'");
  });

  it('Phase F.8 polish maquette V2 : viewBox 320×130 + axe Y + baseline + annotation', () => {
    const src = read();
    // viewBox plus haut (vs 100×60 F.2) pour respirer
    expect(src).toContain('viewBox="0 0 320 130"');
    // Axe Y avec graduations (yTicks helper)
    expect(src).toContain('function yTicks');
    expect(src).toContain('y-tick');
    // Baseline rendering conditionnel
    expect(src).toContain('data-baseline');
    expect(src).toContain('baseline');
    // Annotation pour anomalies (eg "+72 %")
    expect(src).toContain('annotation');
    expect(src).toContain('isAnnotated');
  });

  it('resolveTone priorite (datum.tone > toneRules > neutral)', () => {
    const src = read();
    expect(src).toContain('function resolveTone');
    expect(src).toMatch(/if\s*\(\s*datum\?\.tone/);
    expect(src).toMatch(/Array\.isArray\(toneRules\)/);
    expect(src).toContain("return 'neutral';");
  });

  it('JSDoc @typedef BarsDatum + ToneRule (contrat API)', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} BarsDatum');
    expect(src).toContain('@typedef {Object} ToneRule');
    expect(src).toContain('@param {BarsDatum[]} props.data');
    expect(src).toContain('@param {ToneRule[]}');
  });

  it('defensive null-render (data invalide / vide retourne null)', () => {
    const src = read();
    expect(src).toContain('if (!Array.isArray(data) || data.length === 0) return null;');
  });

  it('zero hex hardcoded (tokens-only doctrine §6.5)', () => {
    const src = read();
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
