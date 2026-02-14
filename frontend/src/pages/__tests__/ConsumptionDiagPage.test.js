/**
 * PROMEOS — Tests for ConsumptionDiagPage helpers
 * Covers: recalcLosses, generateComparisonChart
 */
import { describe, it, expect } from 'vitest';
import { recalcLosses, generateComparisonChart } from '../ConsumptionDiagPage';

describe('recalcLosses', () => {
  it('multiplies kWh by custom price', () => {
    expect(recalcLosses(1000, 0.20)).toBe(200);
  });

  it('uses default price when customPrice is null', () => {
    expect(recalcLosses(1000, null)).toBe(150);
  });

  it('returns 0 for null kWh', () => {
    expect(recalcLosses(null, 0.15)).toBe(0);
  });

  it('uses custom default price', () => {
    expect(recalcLosses(1000, null, 0.10)).toBe(100);
  });

  it('rounds to integer', () => {
    expect(recalcLosses(333, 0.157)).toBe(Math.round(333 * 0.157));
  });
});

describe('generateComparisonChart', () => {
  const baseInsight = { id: 42, type: 'hors_horaires', estimated_loss_kwh: 200 };

  it('returns 24 data points', () => {
    const data = generateComparisonChart(baseInsight);
    expect(data).toHaveLength(24);
  });

  it('each point has hour, baseline, and actual', () => {
    const data = generateComparisonChart(baseInsight);
    for (const pt of data) {
      expect(pt).toHaveProperty('hour');
      expect(pt).toHaveProperty('baseline');
      expect(pt).toHaveProperty('actual');
      expect(typeof pt.baseline).toBe('number');
      expect(typeof pt.actual).toBe('number');
    }
  });

  it('hors_horaires: actual > baseline during night hours', () => {
    const data = generateComparisonChart({ id: 1, type: 'hors_horaires', estimated_loss_kwh: 500 });
    const night = data.filter((_, i) => i < 8 || i > 19);
    const excess = night.filter(pt => pt.actual > pt.baseline);
    expect(excess.length).toBeGreaterThan(0);
  });

  it('pointe: actual > baseline during peak hours (10-14)', () => {
    const data = generateComparisonChart({ id: 2, type: 'pointe', estimated_loss_kwh: 300 });
    const peak = data.filter((_, i) => i >= 10 && i <= 14);
    expect(peak.every(pt => pt.actual > pt.baseline)).toBe(true);
  });

  it('base_load: actual >= baseline everywhere', () => {
    const data = generateComparisonChart({ id: 3, type: 'base_load', estimated_loss_kwh: 200 });
    expect(data.every(pt => pt.actual >= pt.baseline)).toBe(true);
  });

  it('handles unknown type without crashing', () => {
    const data = generateComparisonChart({ id: 99, type: 'unknown_type', estimated_loss_kwh: 100 });
    expect(data).toHaveLength(24);
    expect(data.every(pt => typeof pt.actual === 'number')).toBe(true);
  });

  it('is deterministic (same input = same output)', () => {
    const a = generateComparisonChart(baseInsight);
    const b = generateComparisonChart(baseInsight);
    expect(a).toEqual(b);
  });
});
