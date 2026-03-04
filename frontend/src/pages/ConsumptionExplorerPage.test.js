/**
 * PROMEOS - ConsumptionExplorerPage V10 Tests
 * Smoke tests for the Consumption Explorer page.
 */
import { describe, test, expect, vi } from 'vitest';

// Mock the API calls
vi.mock('../services/api', () => ({
  getConsumptionTunnel: vi.fn().mockResolvedValue({
    site_id: 1,
    energy_type: 'electricity',
    days: 90,
    readings_count: 500,
    envelope: {
      weekday: Array.from({ length: 24 }, (_, h) => ({
        hour: h,
        p10: 5,
        p25: 8,
        p50: 12,
        p75: 16,
        p90: 20,
        count: 10,
      })),
      weekend: [],
    },
    outside_pct: 8.5,
    outside_count: 3,
    total_evaluated: 35,
    confidence: 'medium',
    confidence_score: 65,
  }),
  getConsumptionTargets: vi.fn().mockResolvedValue([]),
  createConsumptionTarget: vi.fn().mockResolvedValue({ id: 1 }),
  patchConsumptionTarget: vi.fn().mockResolvedValue({ id: 1 }),
  deleteConsumptionTarget: vi.fn().mockResolvedValue({ status: 'deleted' }),
  getTargetsProgression: vi.fn().mockResolvedValue({
    site_id: 1,
    year: 2026,
    yearly_target_kwh: 60000,
    ytd_actual_kwh: 9600,
    ytd_target_kwh: 10000,
    progress_pct: 96,
    forecast_year_kwh: 57600,
    forecast_vs_target_pct: -4,
    alert: 'on_track',
    months: Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      target_kwh: 5000,
      actual_kwh: i < 2 ? 4800 : null,
      delta_pct: i < 2 ? -4 : null,
    })),
  }),
  getTOUSchedules: vi.fn().mockResolvedValue([]),
  getActiveTOUSchedule: vi.fn().mockResolvedValue({
    id: null,
    name: 'HC/HP Standard (defaut)',
    is_default: true,
    windows: [
      { day_types: ['weekday'], start: '06:00', end: '22:00', period: 'HP', price_eur_kwh: 0.18 },
      { day_types: ['weekday'], start: '22:00', end: '06:00', period: 'HC', price_eur_kwh: 0.13 },
    ],
    price_hp_eur_kwh: 0.18,
    price_hc_eur_kwh: 0.13,
  }),
  createTOUSchedule: vi.fn().mockResolvedValue({ id: 1 }),
  getHPHCRatio: vi.fn().mockResolvedValue({
    site_id: 1,
    hp_kwh: 3500,
    hc_kwh: 1500,
    total_kwh: 5000,
    hp_ratio: 0.7,
    hp_cost_eur: 630,
    hc_cost_eur: 195,
    total_cost_eur: 825,
    schedule_name: 'HC/HP Standard',
    confidence: 'medium',
  }),
  getGasSummary: vi.fn().mockResolvedValue({
    site_id: 1,
    energy_type: 'gas',
    days: 90,
    readings_count: 0,
    daily_kwh: [],
    total_kwh: 0,
    avg_daily_kwh: 0,
    summer_base_kwh: 0,
    confidence: 'low',
  }),
}));

vi.mock('../services/tracker', () => ({
  track: vi.fn(),
}));

vi.mock('../contexts/ScopeContext', () => ({
  useScope: () => ({ selectedSiteId: 1, sites: [{ id: 1, nom: 'Site Test' }] }),
}));

describe('ConsumptionExplorerPage', () => {
  test('module imports without errors', async () => {
    const mod = await import('./ConsumptionExplorerPage');
    expect(mod.default).toBeDefined();
    expect(typeof mod.default).toBe('function');
  });
});

describe('API mock contracts', () => {
  test('tunnel response has expected shape', async () => {
    const { getConsumptionTunnel } = await import('../services/api');
    const result = await getConsumptionTunnel(1, 90);
    expect(result).toHaveProperty('envelope');
    expect(result).toHaveProperty('outside_pct');
    expect(result).toHaveProperty('confidence');
    expect(result.envelope).toHaveProperty('weekday');
    expect(result.envelope.weekday).toHaveLength(24);
  });

  test('HP/HC ratio response has expected shape', async () => {
    const { getHPHCRatio } = await import('../services/api');
    const result = await getHPHCRatio(1, null, 30);
    expect(result).toHaveProperty('hp_kwh');
    expect(result).toHaveProperty('hc_kwh');
    expect(result).toHaveProperty('hp_ratio');
    expect(result).toHaveProperty('total_cost_eur');
    expect(result.hp_ratio).toBeGreaterThanOrEqual(0);
    expect(result.hp_ratio).toBeLessThanOrEqual(1);
  });

  test('progression response has 12 months', async () => {
    const { getTargetsProgression } = await import('../services/api');
    const result = await getTargetsProgression(1, 'electricity', 2026);
    expect(result.months).toHaveLength(12);
    expect(result).toHaveProperty('alert');
    expect(['on_track', 'at_risk', 'over_budget']).toContain(result.alert);
  });

  test('gas summary response has expected shape', async () => {
    const { getGasSummary } = await import('../services/api');
    const result = await getGasSummary(1, 90);
    expect(result).toHaveProperty('total_kwh');
    expect(result).toHaveProperty('avg_daily_kwh');
    expect(result).toHaveProperty('summer_base_kwh');
    expect(result).toHaveProperty('confidence');
  });

  test('TOU schedule active response has windows', async () => {
    const { getActiveTOUSchedule } = await import('../services/api');
    const result = await getActiveTOUSchedule(1);
    expect(result).toHaveProperty('windows');
    expect(result).toHaveProperty('is_default');
    expect(result.windows.length).toBeGreaterThan(0);
    expect(result.windows[0]).toHaveProperty('period');
  });
});
