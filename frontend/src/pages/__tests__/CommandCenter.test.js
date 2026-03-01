/**
 * PROMEOS — Tests for CommandCenter helpers (Phase 6)
 * Covers: normalizeDashboardModel, colorTokens integrity.
 */
import { describe, it, expect } from 'vitest';
import { normalizeDashboardModel } from '../CommandCenter';
import { KPI_ACCENTS, SEVERITY_TINT, ACCENT_BAR, HERO_ACCENTS } from '../../ui/colorTokens';

describe('normalizeDashboardModel', () => {
  const baseKpis = {
    total: 10, conformes: 10, nonConformes: 0, aRisque: 0,
    risque: 0, pctConf: 100, compStatus: 'ok', risqueStatus: 'ok',
  };

  it('isAllClear when 100% + 0 risk + 0 alerts', () => {
    const result = normalizeDashboardModel({
      kpis: baseKpis,
      topActions: [{ id: 1 }],
      alertsCount: 0,
    });
    expect(result.isAllClear).toBe(true);
    expect(result.topActions).toEqual([]);
    expect(result.kpis.risque).toBe(0);
  });

  it('not allClear when alerts > 0', () => {
    const result = normalizeDashboardModel({
      kpis: baseKpis,
      topActions: [],
      alertsCount: 3,
    });
    expect(result.isAllClear).toBe(false);
  });

  it('not allClear when risk > 0', () => {
    const result = normalizeDashboardModel({
      kpis: { ...baseKpis, pctConf: 80, nonConformes: 2, risque: 5000 },
      topActions: [{ id: 1 }],
      alertsCount: 0,
    });
    expect(result.isAllClear).toBe(false);
    expect(result.topActions).toHaveLength(1);
  });

  it('forces risque=0 when pctConf=100', () => {
    const result = normalizeDashboardModel({
      kpis: { ...baseKpis, risque: 500 },
      topActions: [],
      alertsCount: 0,
    });
    expect(result.kpis.risque).toBe(0);
    expect(result.kpis.nonConformes).toBe(0);
    expect(result.kpis.aRisque).toBe(0);
  });

  it('forces risque=0 when 0 risk sites', () => {
    const result = normalizeDashboardModel({
      kpis: { ...baseKpis, pctConf: 80, nonConformes: 0, aRisque: 0, risque: 1000 },
      topActions: [],
      alertsCount: 0,
    });
    expect(result.kpis.risque).toBe(0);
  });

  it('preserves alertsCount', () => {
    const result = normalizeDashboardModel({
      kpis: baseKpis,
      topActions: [],
      alertsCount: 7,
    });
    expect(result.alertsCount).toBe(7);
  });
});

describe('colorTokens integrity', () => {
  it('KPI_ACCENTS has all required keys', () => {
    expect(Object.keys(KPI_ACCENTS)).toEqual(
      expect.arrayContaining(['conformite', 'risque', 'alertes', 'sites', 'maturite', 'neutral'])
    );
  });

  it('each KPI accent has all required fields', () => {
    for (const [_key, cfg] of Object.entries(KPI_ACCENTS)) {
      expect(cfg).toHaveProperty('accent');
      expect(cfg).toHaveProperty('iconBg');
      expect(cfg).toHaveProperty('iconText');
      expect(cfg).toHaveProperty('border');
      expect(cfg).toHaveProperty('tintBg');
    }
  });

  it('SEVERITY_TINT has critical, warn, info, neutral', () => {
    expect(Object.keys(SEVERITY_TINT)).toEqual(
      expect.arrayContaining(['critical', 'warn', 'info', 'neutral'])
    );
  });

  it('each severity tint has dot + chipBg + chipText', () => {
    for (const [, sev] of Object.entries(SEVERITY_TINT)) {
      expect(sev).toHaveProperty('dot');
      expect(sev).toHaveProperty('chipBg');
      expect(sev).toHaveProperty('chipText');
      expect(sev).toHaveProperty('label');
    }
  });

  it('ACCENT_BAR has primary, amber, indigo, gray', () => {
    expect(Object.keys(ACCENT_BAR)).toEqual(
      expect.arrayContaining(['primary', 'amber', 'indigo', 'gray'])
    );
  });

  it('HERO_ACCENTS has priority, success, executive', () => {
    expect(Object.keys(HERO_ACCENTS)).toEqual(
      expect.arrayContaining(['priority', 'success', 'executive'])
    );
    for (const [, h] of Object.entries(HERO_ACCENTS)) {
      expect(h).toHaveProperty('bg');
      expect(h).toHaveProperty('border');
      expect(h).toHaveProperty('ring');
    }
  });

  it('no severity label is "medium" (must be FR)', () => {
    for (const [, sev] of Object.entries(SEVERITY_TINT)) {
      expect(sev.label).not.toBe('medium');
    }
  });
});
