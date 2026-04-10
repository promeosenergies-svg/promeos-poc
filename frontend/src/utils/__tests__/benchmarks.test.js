import { describe, test, expect } from 'vitest';
import { getBenchmark, getIntensityRatio, OID_BENCHMARKS as _OID_BENCHMARKS } from '../benchmarks';

describe('OID Benchmarks — ADEME 2024', () => {
  test('bureau retourne 210 (ADEME ODP 2024)', () => {
    expect(getBenchmark('bureau')).toBe(210);
  });

  test('bureaux retourne 210', () => {
    expect(getBenchmark('bureaux')).toBe(210);
  });

  test('hotel retourne 280', () => {
    expect(getBenchmark('hotel')).toBe(280);
  });

  test('commerce retourne 330', () => {
    expect(getBenchmark('commerce')).toBe(330);
  });

  test('usine retourne 180 (industrie)', () => {
    expect(getBenchmark('usine')).toBe(180);
  });

  test('usage inconnu retourne default (210)', () => {
    expect(getBenchmark('xyz_inconnu')).toBe(210);
  });

  test('usage null retourne default', () => {
    expect(getBenchmark(null)).toBe(210);
  });

  test('ratio 300/210 ~ 1.43', () => {
    const ratio = getIntensityRatio(300, 'bureau');
    expect(ratio).toBeCloseTo(1.43, 1);
  });

  test('ratio null si données manquantes', () => {
    expect(getIntensityRatio(null, 'bureau')).toBeNull();
    expect(getIntensityRatio(300, null)).not.toBeNull();
  });

  test('ratio <= 1 pour site performant', () => {
    const ratio = getIntensityRatio(100, 'bureau');
    expect(ratio).toBeLessThanOrEqual(1);
  });
});
