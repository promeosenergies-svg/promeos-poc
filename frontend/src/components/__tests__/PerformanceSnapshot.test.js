/**
 * PROMEOS — Tests for PerformanceSnapshot helpers
 * Covers: fmtN, SEVERITY_COLOR
 */
import { describe, it, expect } from 'vitest';
import { fmtN, SEVERITY_COLOR } from '../PerformanceSnapshot';

describe('fmtN', () => {
  it('formats integer with locale FR', () => {
    const result = fmtN(12345);
    // fr-FR uses non-breaking space as thousands sep
    expect(result.replace(/\s/g, ' ')).toBe('12 345');
  });

  it('formats with decimals', () => {
    const result = fmtN(3.14159, 2);
    expect(result).toContain('3');
    expect(result).toContain('14');
  });

  it('returns dash for null', () => {
    expect(fmtN(null)).toBe('-');
  });

  it('returns dash for undefined', () => {
    expect(fmtN(undefined)).toBe('-');
  });

  it('returns dash for NaN', () => {
    expect(fmtN(NaN)).toBe('-');
  });

  it('handles zero', () => {
    expect(fmtN(0)).toBe('0');
  });

  it('handles negative values', () => {
    const result = fmtN(-42);
    expect(result).toContain('42');
  });

  it('defaults to 0 decimals', () => {
    const result = fmtN(7.89);
    expect(result).toBe('8');
  });
});

describe('SEVERITY_COLOR', () => {
  it('has 4 severity levels', () => {
    expect(Object.keys(SEVERITY_COLOR)).toHaveLength(4);
  });

  it('includes critical, high, warning, info', () => {
    expect(SEVERITY_COLOR).toHaveProperty('critical');
    expect(SEVERITY_COLOR).toHaveProperty('high');
    expect(SEVERITY_COLOR).toHaveProperty('warning');
    expect(SEVERITY_COLOR).toHaveProperty('info');
  });

  it('each severity has Tailwind classes', () => {
    for (const [key, value] of Object.entries(SEVERITY_COLOR)) {
      expect(value).toContain('bg-');
      expect(value).toContain('text-');
      expect(value).toContain('ring-');
    }
  });

  it('critical is red', () => {
    expect(SEVERITY_COLOR.critical).toContain('red');
  });

  it('info is blue', () => {
    expect(SEVERITY_COLOR.info).toContain('blue');
  });
});
