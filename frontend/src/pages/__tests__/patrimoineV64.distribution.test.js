/**
 * patrimoineV64.distribution.test.js — Guards V64 PatrimoineRiskDistributionBar
 *
 * 5 tests :
 *   1. empty array → all zeros
 *   2. all-zeros → ok = N, warn = 0, critical = 0
 *   3. N=5 (< 8) → top1 critical, next2 warn, rest ok (stable)
 *   4. N=20 (≥ 8) → quantile buckets, somme = N, chaque bucket > 0
 *   5. Integration : composant importable + topSlot dans Patrimoine.jsx
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';
import { computeRiskBuckets } from '../../components/PatrimoineRiskDistributionBar';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');

const DIST_JSX      = src('components/PatrimoineRiskDistributionBar.jsx');
const HEATMAP_JSX   = src('components/PatrimoineHeatmap.jsx');
const PATRIMOINE_JSX = src('pages/Patrimoine.jsx');

// ── 1. Empty ─────────────────────────────────────────────────────────────

describe('computeRiskBuckets — guard 1 : tableau vide', () => {
  test('retourne {ok:0, warn:0, critical:0, thresholds:{p40:0,p80:0}}', () => {
    const result = computeRiskBuckets([]);
    expect(result).toEqual({ ok: 0, warn: 0, critical: 0, thresholds: { p40: 0, p80: 0 } });
  });
});

// ── 2. All-zeros ─────────────────────────────────────────────────────────

describe('computeRiskBuckets — guard 2 : tous zéros', () => {
  test('3 zéros → ok=3, warn=0, critical=0', () => {
    const { ok, warn, critical } = computeRiskBuckets([0, 0, 0]);
    expect(ok).toBe(3);
    expect(warn).toBe(0);
    expect(critical).toBe(0);
  });

  test('1 zéro → ok=1', () => {
    const { ok, warn, critical } = computeRiskBuckets([0]);
    expect(ok).toBe(1);
    expect(warn).toBe(0);
    expect(critical).toBe(0);
  });
});

// ── 3. N < 8 (stable) ────────────────────────────────────────────────────

describe('computeRiskBuckets — guard 3 : N=5 (< 8)', () => {
  const risks = [10_000, 20_000, 30_000, 40_000, 50_000];

  test('critical = 1 (top 1)', () => {
    const { critical } = computeRiskBuckets(risks);
    expect(critical).toBe(1);
  });

  test('warn = 2 (next 2)', () => {
    const { warn } = computeRiskBuckets(risks);
    expect(warn).toBe(2);
  });

  test('ok = 2 (reste)', () => {
    const { ok } = computeRiskBuckets(risks);
    expect(ok).toBe(2);
  });

  test('somme = N = 5', () => {
    const { ok, warn, critical } = computeRiskBuckets(risks);
    expect(ok + warn + critical).toBe(5);
  });

  test('N=2 → critical=1, warn=1, ok=0', () => {
    const { ok, warn, critical } = computeRiskBuckets([1000, 2000]);
    expect(critical).toBe(1);
    expect(warn).toBe(1);
    expect(ok).toBe(0);
  });

  test('N=1 → critical=1, warn=0, ok=0', () => {
    const { ok, warn, critical } = computeRiskBuckets([5000]);
    expect(critical).toBe(1);
    expect(warn).toBe(0);
    expect(ok).toBe(0);
  });
});

// ── 4. N=20 (≥ 8, quantiles) ─────────────────────────────────────────────

describe('computeRiskBuckets — guard 4 : N=20 (≥ 8)', () => {
  // risks = [1k, 2k, ..., 20k]
  const risks = Array.from({ length: 20 }, (_, i) => (i + 1) * 1_000);

  test('somme ok + warn + critical = 20', () => {
    const { ok, warn, critical } = computeRiskBuckets(risks);
    expect(ok + warn + critical).toBe(20);
  });

  test('ok > 0', () => {
    const { ok } = computeRiskBuckets(risks);
    expect(ok).toBeGreaterThan(0);
  });

  test('warn > 0', () => {
    const { warn } = computeRiskBuckets(risks);
    expect(warn).toBeGreaterThan(0);
  });

  test('critical > 0', () => {
    const { critical } = computeRiskBuckets(risks);
    expect(critical).toBeGreaterThan(0);
  });

  test('thresholds p40 < p80', () => {
    const { thresholds } = computeRiskBuckets(risks);
    expect(thresholds.p40).toBeLessThan(thresholds.p80);
  });

  test('p40 = 8000, p80 = 16000 pour 1k..20k', () => {
    // p40 = sorted[floor(0.4*19)] = sorted[7] = 8k
    // p80 = sorted[floor(0.8*19)] = sorted[15] = 16k
    const { thresholds } = computeRiskBuckets(risks);
    expect(thresholds.p40).toBe(8_000);
    expect(thresholds.p80).toBe(16_000);
  });
});

// ── 5. Integration source-guards ─────────────────────────────────────────

describe('PatrimoineRiskDistributionBar V64 — intégration', () => {
  test('default export PatrimoineRiskDistributionBar présent', () => {
    expect(DIST_JSX).toMatch(/export default function PatrimoineRiskDistributionBar/);
  });

  test('computeRiskBuckets exporté nominalement', () => {
    expect(DIST_JSX).toMatch(/export function computeRiskBuckets/);
  });

  test('barre segmentée bg-green-300 + bg-amber-400 + bg-red-500', () => {
    expect(DIST_JSX).toMatch(/bg-green-300/);
    expect(DIST_JSX).toMatch(/bg-amber-400/);
    expect(DIST_JSX).toMatch(/bg-red-500/);
  });

  test('aria-label sur la barre', () => {
    expect(DIST_JSX).toMatch(/aria-label/);
  });

  test('titre tooltip mentionnant quantiles', () => {
    expect(DIST_JSX).toMatch(/quantiles/);
  });

  test('null safety : sites.length === 0 → return null', () => {
    expect(DIST_JSX).toMatch(/sites\.length\s*===\s*0.*return null|return null.*sites\.length/s);
  });

  test('fallback risque_eur dans extraction', () => {
    expect(DIST_JSX).toMatch(/risque_eur/);
  });

  test('PatrimoineHeatmap accepte topSlot prop', () => {
    expect(HEATMAP_JSX).toMatch(/topSlot/);
  });

  test('topSlot rendu dans PatrimoineHeatmap', () => {
    expect(HEATMAP_JSX).toMatch(/\{topSlot\}/);
  });

  test('PatrimoineRiskDistributionBar importé dans Patrimoine.jsx', () => {
    expect(PATRIMOINE_JSX).toMatch(/import PatrimoineRiskDistributionBar/);
  });

  test('topSlot passé à PatrimoineHeatmap dans Patrimoine.jsx', () => {
    expect(PATRIMOINE_JSX).toMatch(/topSlot=\{<PatrimoineRiskDistributionBar/);
  });

  test('sites={filtered} passé à PatrimoineRiskDistributionBar', () => {
    expect(PATRIMOINE_JSX).toMatch(/sites=\{filtered\}/);
  });
});
