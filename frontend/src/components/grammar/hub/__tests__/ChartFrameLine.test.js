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
    // Phase F.8 — HP = attention-fg (orange), HC = hch-fg (bleu). Tokens canoniques.
    expect(src).toContain("'var(--sol-attention-fg)'");
    expect(src).toContain("'var(--sol-hch-fg)'");
  });

  it('Phase F.10 polish maquette V2 : viewBox 340×150 + axe Y + HC zones + peak + HP gradient + légende', () => {
    const src = read();
    // Phase F.10 — viewBox élargi (340×150) vs F.8 (320×130) pour donner
    // de l'air aux labels (1 000 axe Y / kW seuil) et accueillir la légende
    // HP/HC en haut. Audit user F.9 "courbe tronquée, légende absente".
    expect(src).toContain('viewBox="0 0 340 160"');
    // Axe Y (yTicks)
    expect(src).toContain('function yTicks');
    expect(src).toContain('y-tick');
    // HC zones (rect en fond bleu clair)
    expect(src).toContain('data-hc-zone-index');
    expect(src).toContain('FILL_HC_ZONE');
    // HP gradient defs + polygon fill
    expect(src).toContain('linearGradient');
    expect(src).toContain('data-series="hp-fill"');
    // Peak annotation (circle + label)
    expect(src).toContain('data-peak');
    expect(src).toContain('data-has-peak');
    // Phase F.10 — Légende HP/HC visible (audit user "légende absente")
    expect(src).toContain('data-legend');
    expect(src).toContain('Heures pleines (HP)');
    expect(src).toContain('Heures creuses (HC)');
  });

  it('threshold optionnel (dashed line + label)', () => {
    const src = read();
    expect(src).toContain('STROKE_THRESHOLD');
    expect(src).toContain("'var(--sol-refuse-line)'");
    // Phase F.8 dasharray "3,3" (vs "1.5,1.5" F.2) — visibilité accrue
    expect(src).toContain('strokeDasharray="3,3"');
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

  it('PAS de fallback synthetique frontend (Correctif #1 audit /simplify + CS)', () => {
    const src = read();
    // Audit Sprint F P1 fix : le frontend ne fabrique plus de courbes plausibles
    // qui pourraient être prises pour des CDC réelles en démo investisseur.
    // Phase F.8 : les données series_hc/series_hp/peak/hc_zones sont fournies
    // par le backend HELIOS demo (cf _build_cockpit_jour_charts).
    expect(src).not.toContain('function generateSyntheticHC');
    expect(src).not.toContain('generateSyntheticHC()');
  });

  it('Phase F.8 coordinate helpers : hourToX + kwToY pour viewBox 320×130', () => {
    const src = read();
    // Helpers de mapping coordonnées source-of-truth (vs magic factor F.2).
    expect(src).toContain('function hourToX');
    expect(src).toContain('function kwToY');
    // Bornes plot area
    expect(src).toContain('PLOT_LEFT');
    expect(src).toContain('PLOT_RIGHT');
    expect(src).toContain('PLOT_TOP');
    expect(src).toContain('PLOT_BOTTOM');
  });

  it('zero hex hardcoded (tokens-only doctrine §6.5)', () => {
    const src = read();
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
