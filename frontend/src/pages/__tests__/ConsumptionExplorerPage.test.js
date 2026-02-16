/**
 * PROMEOS — Tests for Consumption Explorer helpers
 * V11: computeGranularity, computeAutoRange, classifyEmptyReason
 */
import { describe, it, expect } from 'vitest';
import { computeGranularity, computeAutoRange, classifyEmptyReason } from '../consumption/helpers';

describe('computeGranularity', () => {
  it('7 days => 30min', () => {
    expect(computeGranularity(7)).toBe('30min');
  });
  it('30 days => 1h', () => {
    expect(computeGranularity(30)).toBe('1h');
  });
  it('90 days => jour', () => {
    expect(computeGranularity(90)).toBe('jour');
  });
  it('365 days => semaine', () => {
    expect(computeGranularity(365)).toBe('semaine');
  });
  it('1 day => 30min', () => {
    expect(computeGranularity(1)).toBe('30min');
  });
  it('180 days => jour', () => {
    expect(computeGranularity(180)).toBe('jour');
  });
  it('181 days => semaine', () => {
    expect(computeGranularity(181)).toBe('semaine');
  });
});

describe('computeAutoRange', () => {
  it('null dates => 90', () => {
    expect(computeAutoRange(null, null)).toBe(90);
  });
  it('null firstTs => 90', () => {
    expect(computeAutoRange(null, '2026-01-15T00:00:00')).toBe(90);
  });
  it('<30 days span => 30', () => {
    expect(computeAutoRange('2026-01-01T00:00:00', '2026-01-20T00:00:00')).toBe(30);
  });
  it('45 days span => 45 (capped at 60)', () => {
    expect(computeAutoRange('2026-01-01T00:00:00', '2026-02-15T00:00:00')).toBe(45);
  });
  it('120 days span => 90', () => {
    expect(computeAutoRange('2025-09-01T00:00:00', '2025-12-30T00:00:00')).toBe(90);
  });
  it('60 days span => 60', () => {
    expect(computeAutoRange('2026-01-01T00:00:00', '2026-03-02T00:00:00')).toBe(60);
  });
});

describe('classifyEmptyReason', () => {
  it('null availability => loading', () => {
    expect(classifyEmptyReason(null)).toBe('loading');
  });
  it('has_data: true => has_data', () => {
    expect(classifyEmptyReason({ has_data: true })).toBe('has_data');
  });
  it('reasons: [no_meter] => no_meter', () => {
    expect(classifyEmptyReason({ has_data: false, reasons: ['no_meter'] })).toBe('no_meter');
  });
  it('empty reasons => unknown', () => {
    expect(classifyEmptyReason({ has_data: false, reasons: [] })).toBe('unknown');
  });
  it('multiple reasons => returns first', () => {
    expect(classifyEmptyReason({ has_data: false, reasons: ['no_readings', 'insufficient_readings'] })).toBe('no_readings');
  });
});
