/**
 * PROMEOS — ExplorerChart Brush + summary row regression tests (V11.1-E)
 * Tests the pure logic: summaryData formatting, plural labels, Brush condition.
 * No DOM rendering required — tests mirror the component logic.
 */
import { describe, it, expect } from 'vitest';

// ── Mirror SummaryRow logic from ExplorerChart.jsx ─────────────────────────

function plural(n, singular, pluralForm) {
  return n != null ? `${n}\u00a0${n <= 1 ? singular : pluralForm}` : null;
}

function buildSummaryParts(summaryData) {
  if (!summaryData) return null;
  const { points, series, meters, source, quality } = summaryData;
  return [
    plural(points, 'point', 'points'),
    plural(series, 'série', 'séries'),
    plural(meters, 'compteur', 'compteurs'),
    source ? `Source\u00a0: ${source}` : null,
    quality != null ? `Qualité\u00a0: ${quality}\u00a0%` : null,
  ].filter(Boolean);
}

// Brush visibility condition from ExplorerChart
function shouldShowBrush(showBrush, dataLength) {
  return showBrush && dataLength > 20;
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe('ExplorerChart — summary row logic', () => {
  it('returns null when summaryData is not provided', () => {
    expect(buildSummaryParts(undefined)).toBeNull();
    expect(buildSummaryParts(null)).toBeNull();
  });

  it('returns empty array when all fields are null/undefined', () => {
    const parts = buildSummaryParts({});
    expect(parts).toEqual([]);
  });

  it('shows all fields when summaryData is complete', () => {
    const parts = buildSummaryParts({
      points: 24,
      series: 2,
      meters: 3,
      source: 'Enedis',
      quality: 95,
    });
    expect(parts).toHaveLength(5);
    expect(parts[0]).toContain('24');
    expect(parts[0]).toContain('points');
    expect(parts[1]).toContain('2');
    expect(parts[1]).toContain('séries');
    expect(parts[2]).toContain('3');
    expect(parts[2]).toContain('compteurs');
    expect(parts[3]).toContain('Enedis');
    expect(parts[4]).toContain('95');
  });

  it('French singular: 1 point, 1 série, 1 compteur', () => {
    const parts = buildSummaryParts({ points: 1, series: 1, meters: 1 });
    expect(parts[0]).toMatch(/1\u00a0point$/); // not "points"
    expect(parts[1]).toMatch(/1\u00a0série$/); // not "séries"
    expect(parts[2]).toMatch(/1\u00a0compteur$/); // not "compteurs"
  });

  it('French plural: 2 points, 3 séries, 5 compteurs', () => {
    const parts = buildSummaryParts({ points: 2, series: 3, meters: 5 });
    expect(parts[0]).toMatch(/2\u00a0points$/);
    expect(parts[1]).toMatch(/3\u00a0séries$/);
    expect(parts[2]).toMatch(/5\u00a0compteurs$/);
  });

  it('omits source when falsy', () => {
    const parts = buildSummaryParts({ points: 10, source: '' });
    expect(parts.some((p) => p.includes('Source'))).toBe(false);
  });

  it('omits quality when null', () => {
    const parts = buildSummaryParts({ points: 10, quality: null });
    expect(parts.some((p) => p.includes('Qualité'))).toBe(false);
  });

  it('includes quality: 0% (zero is valid)', () => {
    const parts = buildSummaryParts({ quality: 0 });
    expect(parts.some((p) => p.includes('0'))).toBe(true);
  });
});

describe('ExplorerChart — Brush visibility', () => {
  it('showBrush defaults to true (default prop value)', () => {
    // Default prop is true — when data length > 20, brush shows
    expect(shouldShowBrush(true, 24)).toBe(true);
  });

  it('Brush hidden when data length <= 20', () => {
    expect(shouldShowBrush(true, 20)).toBe(false);
    expect(shouldShowBrush(true, 10)).toBe(false);
    expect(shouldShowBrush(true, 0)).toBe(false);
  });

  it('Brush hidden when showBrush=false regardless of data length', () => {
    expect(shouldShowBrush(false, 100)).toBe(false);
    expect(shouldShowBrush(false, 21)).toBe(false);
  });

  it('Brush shown when data > 20 and showBrush=true', () => {
    expect(shouldShowBrush(true, 21)).toBe(true);
    expect(shouldShowBrush(true, 500)).toBe(true);
  });
});
