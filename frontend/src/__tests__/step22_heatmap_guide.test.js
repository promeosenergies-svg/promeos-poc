/**
 * Step 22 — F5 : Guide de lecture heatmap Usages & Horaires
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const readSrc = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. HeatmapLegend component ────────────────────────────────────────────

describe('Step 22 — HeatmapLegend component', () => {
  it('HeatmapLegend.jsx exists', () => {
    const candidates = [
      'src/pages/consumption/HeatmapLegend.jsx',
      'src/components/consumption/HeatmapLegend.jsx',
      'src/components/HeatmapLegend.jsx',
    ];
    expect(candidates.some((f) => fs.existsSync(f))).toBe(true);
  });

  it('has color scale (gradient)', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src.includes('gradient') || src.includes('Faible') || src.includes('Élevé')).toBe(true);
  });

  it('has 3 severity levels (Normal/À surveiller/Anormal)', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('Normal');
    expect(src.includes('surveiller') || src.includes('Surveiller')).toBe(true);
    expect(src.includes('Anormal') || src.includes('anormal')).toBe(true);
  });

  it('has annotations based on night_ratio', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('night_ratio');
    expect(src.includes('nocturne') || src.includes('22h')).toBe(true);
  });

  it('has annotations based on weekend_ratio', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('weekend_ratio');
  });

  it('has annotations based on off_hours_ratio', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('off_hours_ratio');
  });

  it('shows schedule hours (open_time/close_time)', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('open_time');
    expect(src).toContain('close_time');
    expect(src.includes('Horaires')).toBe(true);
  });

  it('has data-testid heatmap-legend', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('heatmap-legend');
  });

  it('supports isExpert prop for detailed stats', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapLegend.jsx');
    expect(src).toContain('isExpert');
  });
});

// ── B. Heatmap page integration ───────────────────────────────────────────

describe('Step 22 — Heatmap page integration', () => {
  it('ProfileHeatmapTab imports and uses HeatmapLegend', () => {
    const src = readSrc('pages', 'consumption', 'ProfileHeatmapTab.jsx');
    expect(src).toContain('HeatmapLegend');
  });

  it('ProfileHeatmapTab accepts schedule and stats props', () => {
    const src = readSrc('pages', 'consumption', 'ProfileHeatmapTab.jsx');
    expect(src).toContain('schedule');
    expect(src).toContain('stats');
  });

  it('ConsumptionContextPage passes schedule to ProfileHeatmapTab', () => {
    const src = readSrc('pages', 'ConsumptionContextPage.jsx');
    expect(src).toContain('schedule=');
  });

  it('ConsumptionContextPage passes stats to ProfileHeatmapTab', () => {
    const src = readSrc('pages', 'ConsumptionContextPage.jsx');
    expect(src).toContain('stats=');
  });
});

// ── C. Tooltip enrichment ─────────────────────────────────────────────────

describe('Step 22 — Tooltip enrichment', () => {
  it('HeatmapChart shows vs moyenne in tooltip', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(src.includes('moyenne') || src.includes('vs moy')).toBe(true);
  });

  it('HeatmapChart shows hors horaires in tooltip', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(src.includes('Hors horaires') || src.includes('hors horaires')).toBe(true);
  });

  it('HeatmapChart has isOffHours helper', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(src).toContain('isOffHours');
  });

  it('HeatmapChart accepts schedule prop', () => {
    const src = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(src).toContain('schedule');
  });
});
