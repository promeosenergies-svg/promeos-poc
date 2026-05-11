/**
 * grammar/hub/HubKpiCard — source-guards Vitest (Sprint Grammaire v1.2 / Phase F.1)
 *
 * Tests pure-grep : contrat de la carte KPI premium L11.2.
 * Aligne sur le pattern du repo (env=node, pas de @testing-library/react —
 * Phase 4 backlog cf RegulatoryRatesContext.test.js).
 *
 * 7 tests couvrent :
 *   1. data-component + data-kpi-id + data-delta-sentiment (source-guards)
 *   2. JSDoc typedef HubKpi + HubKpiDelta (contrat API)
 *   3. tokens severity DELTA_FG + DELTA_BG (positive/negative/neutral)
 *   4. eyebrow render font-mono uppercase tracking + ink-400
 *   5. value tabular-nums + sol-font-display + 28px
 *   6. delta sign convention (positive: prepend '+', negative: as-is)
 *   7. helpTooltip via title attribute (KPI 3 doctrine §L11.2)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../HubKpiCard.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/HubKpiCard', () => {
  it('data-component HubKpiCard + data-kpi-id + data-delta-sentiment', () => {
    const src = read();
    expect(src).toContain('data-component="HubKpiCard"');
    expect(src).toContain('data-kpi-id={id}');
    expect(src).toContain('data-delta-sentiment={sentiment}');
  });

  it('JSDoc typedef HubKpi + HubKpiDelta (contrat API)', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} HubKpi');
    expect(src).toContain('@typedef {Object} HubKpiDelta');
    expect(src).toContain('@param {HubKpi} props.kpi');
  });

  it('tokens severity DELTA_FG + DELTA_BG (positive/negative/neutral)', () => {
    const src = read();
    expect(src).toContain('DELTA_FG');
    expect(src).toContain('DELTA_BG');
    expect(src).toContain('sol-succes-fg');
    expect(src).toContain('sol-refuse-fg');
    expect(src).toContain('sol-ink-500');
    expect(src).toContain('sol-succes-bg');
    expect(src).toContain('sol-refuse-bg');
    expect(src).toContain('sol-bg-canvas');
  });

  it('eyebrow render font-mono uppercase tracking', () => {
    const src = read();
    // Eyebrow rendu avec font-mono + uppercase + letter-spacing 0.14em + ink-400
    expect(src).toMatch(/font-mono uppercase/);
    expect(src).toMatch(/letterSpacing:\s*'0\.14em'/);
    expect(src).toContain('sol-ink-400');
  });

  it('value tabular-nums + sol-font-display + 28px', () => {
    const src = read();
    expect(src).toContain('tabular-nums');
    expect(src).toContain('var(--sol-font-display)');
    expect(src).toMatch(/fontSize:\s*'28px'/);
  });

  it("delta sign convention (positive: prepend '+', negative: as-is)", () => {
    const src = read();
    // Convention : si delta.value > 0 → préfixer '+', sinon laisser le signe
    expect(src).toContain("{delta.value > 0 ? '+' : ''}");
  });

  it('helpTooltip via title attribute (KPI 3 doctrine §L11.2)', () => {
    const src = read();
    expect(src).toContain('title={helpTooltip || undefined}');
  });

  it('zero hardcoded hex color (tokens-only doctrine §6.5)', () => {
    const src = read();
    // Aucune couleur hex ; uniquement var(--sol-*)
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });

  it('return null si kpi prop absent (defensive render)', () => {
    const src = read();
    expect(src).toContain('if (!kpi) return null;');
  });
});
