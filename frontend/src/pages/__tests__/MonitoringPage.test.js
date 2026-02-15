/**
 * PROMEOS — Tests for MonitoringPage helpers
 * Covers: buildHeatmapGrid, kpiStatus, computeConfidence, kpiStatusWithConfidence,
 *         LF thresholds, groupInsights, CLIMATE_REASONS, CLIMATE_LABEL_FR
 */
import { describe, it, expect } from 'vitest';
import {
  buildHeatmapGrid, kpiStatus, computeConfidence,
  kpiStatusWithConfidence, LF_THRESHOLDS_BY_ARCHETYPE,
  groupInsights, CLIMATE_REASONS, CLIMATE_LABEL_FR,
} from '../MonitoringPage';

describe('buildHeatmapGrid', () => {
  const weekday = Array.from({ length: 24 }, (_, i) => 10 + i);
  const weekend = Array.from({ length: 24 }, (_, i) => 5 + i * 0.5);

  it('returns 7x24 grid', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    expect(grid).toHaveLength(7);
    for (const row of grid) {
      expect(row).toHaveLength(24);
    }
  });

  it('Mon-Fri use weekday, Sat-Sun use weekend', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    // Monday (index 0) should match weekday
    expect(grid[0][0]).toBe(Number(weekday[0].toFixed(1)));
    expect(grid[4][12]).toBe(Number(weekday[12].toFixed(1)));
    // Saturday (index 5) should match weekend
    expect(grid[5][0]).toBe(Number(weekend[0].toFixed(1)));
    expect(grid[6][12]).toBe(Number(weekend[12].toFixed(1)));
  });

  it('returns null for null input', () => {
    expect(buildHeatmapGrid(null, null)).toBeNull();
    expect(buildHeatmapGrid(undefined, weekend)).toBeNull();
  });

  it('falls back to weekday when weekend is null', () => {
    const grid = buildHeatmapGrid(weekday, null);
    expect(grid[5][0]).toBe(Number(weekday[0].toFixed(1)));
    expect(grid[6][0]).toBe(Number(weekday[0].toFixed(1)));
  });

  it('all values are numbers', () => {
    const grid = buildHeatmapGrid(weekday, weekend);
    for (const row of grid) {
      for (const val of row) {
        expect(typeof val).toBe('number');
      }
    }
  });
});

describe('kpiStatus', () => {
  const thresholds = { ok: 80, warn: 60 };

  it('ok for high scores', () => {
    expect(kpiStatus(90, thresholds)).toBe('ok');
    expect(kpiStatus(80, thresholds)).toBe('ok');
  });

  it('surveiller for medium', () => {
    expect(kpiStatus(70, thresholds)).toBe('surveiller');
    expect(kpiStatus(60, thresholds)).toBe('surveiller');
  });

  it('critique for low', () => {
    expect(kpiStatus(50, thresholds)).toBe('critique');
    expect(kpiStatus(0, thresholds)).toBe('critique');
  });

  it('invert mode (risk: low=ok)', () => {
    const riskThresholds = { ok: 35, warn: 60 };
    expect(kpiStatus(20, riskThresholds, true)).toBe('ok');
    expect(kpiStatus(50, riskThresholds, true)).toBe('surveiller');
    expect(kpiStatus(80, riskThresholds, true)).toBe('critique');
  });

  it('null value returns no_data', () => {
    expect(kpiStatus(null, thresholds)).toBe('no_data');
    expect(kpiStatus(undefined, thresholds)).toBe('no_data');
  });

  it('zero is a real value (not no_data)', () => {
    expect(kpiStatus(0, thresholds)).toBe('critique');
    expect(kpiStatus(0, { ok: 35, warn: 60 }, true)).toBe('ok');
  });
});

describe('computeConfidence', () => {
  it('high confidence when R² >= 0.6', () => {
    const c = computeConfidence({ r2: 0.85 });
    expect(c.level).toBe('high');
    expect(c.pct).toBeGreaterThanOrEqual(60);
  });

  it('low confidence when R² < 0.3', () => {
    const c = computeConfidence({ r2: 0.12 });
    expect(c.level).toBe('low');
    expect(c.reason).toMatch(/R²/);
  });

  it('low confidence when reason code present', () => {
    const c = computeConfidence({ reason: 'no_weather' });
    expect(c.level).toBe('low');
    expect(c.pct).toBe(0);
  });

  it('low when nPoints < 10', () => {
    const c = computeConfidence({ r2: 0.9, nPoints: 5 });
    expect(c.level).toBe('low');
  });

  it('medium when coverage between 30 and 60', () => {
    const c = computeConfidence({ coveragePct: 45 });
    expect(c.level).toBe('medium');
  });

  it('pct bounded 0-100', () => {
    expect(computeConfidence({ r2: 1.5 }).pct).toBeLessThanOrEqual(100);
    expect(computeConfidence({ r2: -0.5 }).pct).toBeGreaterThanOrEqual(0);
  });
});

describe('kpiStatusWithConfidence', () => {
  const thresholds = { ok: 2, warn: 4 };

  it('critique with high confidence stays critique', () => {
    expect(kpiStatusWithConfidence(6, thresholds, true, { level: 'high' })).toBe('critique');
  });

  it('critique with low confidence becomes a_confirmer', () => {
    expect(kpiStatusWithConfidence(6, thresholds, true, { level: 'low' })).toBe('a_confirmer');
  });

  it('R² faible => slope high but status a_confirmer', () => {
    const conf = computeConfidence({ r2: 0.12 });
    const status = kpiStatusWithConfidence(6, thresholds, true, conf);
    expect(status).toBe('a_confirmer');
  });

  it('ok unaffected by low confidence', () => {
    expect(kpiStatusWithConfidence(1, thresholds, true, { level: 'low' })).toBe('ok');
  });

  it('surveiller with low confidence becomes a_confirmer', () => {
    expect(kpiStatusWithConfidence(3, thresholds, true, { level: 'low' })).toBe('a_confirmer');
  });

  it('surveiller with high confidence stays surveiller', () => {
    expect(kpiStatusWithConfidence(3, thresholds, true, { level: 'high' })).toBe('surveiller');
  });

  it('surveiller with medium confidence stays surveiller', () => {
    expect(kpiStatusWithConfidence(3, thresholds, true, { level: 'medium' })).toBe('surveiller');
  });

  it('works without confidence (fallback)', () => {
    expect(kpiStatusWithConfidence(6, thresholds, true, null)).toBe('critique');
  });
});

describe('LF_THRESHOLDS_BY_ARCHETYPE', () => {
  it('has entries for 6 profiles + default', () => {
    expect(Object.keys(LF_THRESHOLDS_BY_ARCHETYPE)).toEqual(
      expect.arrayContaining(['office', 'hotel', 'retail', 'warehouse', 'school', 'hospital', 'default'])
    );
  });

  it('office ok threshold is higher than default', () => {
    expect(LF_THRESHOLDS_BY_ARCHETYPE.office.ok).toBeGreaterThan(
      LF_THRESHOLDS_BY_ARCHETYPE.default.ok
    );
  });

  it('all thresholds have ok > warn', () => {
    for (const [, t] of Object.entries(LF_THRESHOLDS_BY_ARCHETYPE)) {
      expect(t.ok).toBeGreaterThan(t.warn);
    }
  });

  it('load factor 33% is NOT critique for office (was the bug)', () => {
    const t = LF_THRESHOLDS_BY_ARCHETYPE.office;
    expect(kpiStatus(33, t)).toBe('surveiller');
  });

  it('load factor 33% is NOT critique for default', () => {
    const t = LF_THRESHOLDS_BY_ARCHETYPE.default;
    expect(kpiStatus(33, t)).toBe('surveiller');
  });
});

describe('groupInsights', () => {
  const mkAlert = (id, type, eur, severity = 'high', meterId = 1, siteId = 10) => ({
    id, alert_type: type, meter_id: meterId, site_id: siteId,
    estimated_impact_eur: eur, estimated_impact_kwh: eur * 5,
    severity, status: 'open', explanation: `Alert ${id}`,
  });

  it('groups duplicates by alert_type + site_id', () => {
    const alerts = [
      mkAlert(1, 'DEPASSEMENT_PUISSANCE', 500),
      mkAlert(2, 'DEPASSEMENT_PUISSANCE', 300),
      mkAlert(3, 'BASE_NUIT_ELEVEE', 200),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped).toHaveLength(2);
    const dep = grouped.find((g) => g.alert_type === 'DEPASSEMENT_PUISSANCE');
    expect(dep._count).toBe(2);
    expect(dep._totalEur).toBe(800);
    expect(dep._ids).toEqual([1, 2]);
  });

  it('keeps worst severity', () => {
    const alerts = [
      mkAlert(1, 'PIC_ANORMAL', 100, 'warning'),
      mkAlert(2, 'PIC_ANORMAL', 200, 'critical'),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped[0]._maxSeverity).toBe('critical');
  });

  it('sorted by total impact desc', () => {
    const alerts = [
      mkAlert(1, 'A', 100),
      mkAlert(2, 'B', 500),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped[0].alert_type).toBe('B');
    expect(grouped[1].alert_type).toBe('A');
  });

  it('handles empty list', () => {
    expect(groupInsights([])).toEqual([]);
  });

  it('same type + different meters + same site = merged (site-level)', () => {
    const alerts = [
      mkAlert(1, 'X', 100, 'high', 1, 10),
      mkAlert(2, 'X', 200, 'critical', 2, 10),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped).toHaveLength(1);
    expect(grouped[0]._count).toBe(2);
    expect(grouped[0]._totalEur).toBe(300);
    expect(grouped[0]._maxSeverity).toBe('critical');
    expect(grouped[0]._meters.size).toBe(2);
  });

  it('same type + different sites = separate groups', () => {
    const alerts = [
      mkAlert(1, 'X', 100, 'high', 1, 10),
      mkAlert(2, 'X', 200, 'high', 2, 20),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped).toHaveLength(2);
  });

  it('tracks unique meters across group', () => {
    const alerts = [
      mkAlert(1, 'Y', 100, 'warning', 1, 10),
      mkAlert(2, 'Y', 50, 'warning', 1, 10),
      mkAlert(3, 'Y', 200, 'high', 2, 10),
    ];
    const grouped = groupInsights(alerts);
    expect(grouped).toHaveLength(1);
    expect(grouped[0]._meters.size).toBe(2);
    expect(grouped[0]._count).toBe(3);
  });
});

describe('CLIMATE_REASONS', () => {
  it('has 5 reason codes', () => {
    expect(Object.keys(CLIMATE_REASONS)).toHaveLength(5);
  });

  it('covers all backend reason codes', () => {
    const expected = ['no_meter', 'no_weather', 'meter_not_found', 'insufficient_readings', 'computation_error'];
    for (const key of expected) {
      expect(CLIMATE_REASONS).toHaveProperty(key);
      expect(typeof CLIMATE_REASONS[key]).toBe('string');
      expect(CLIMATE_REASONS[key].length).toBeGreaterThan(5);
    }
  });
});

describe('CLIMATE_LABEL_FR', () => {
  it('has French labels for all climate types', () => {
    const expected = ['heating_dominant', 'cooling_dominant', 'mixed', 'flat', 'unknown'];
    for (const key of expected) {
      expect(CLIMATE_LABEL_FR).toHaveProperty(key);
      expect(typeof CLIMATE_LABEL_FR[key]).toBe('string');
    }
  });

  it('does not contain English text', () => {
    for (const label of Object.values(CLIMATE_LABEL_FR)) {
      expect(label).not.toMatch(/dominant|cooling|heating|mixed|unknown/i);
    }
  });
});

describe('computeConfidence with climate reason codes', () => {
  it('reason code yields low confidence', () => {
    const conf = computeConfidence({ reason: 'no_weather' });
    expect(conf.level).toBe('low');
    expect(conf.pct).toBe(0);
  });

  it('R² < 0.3 yields low confidence', () => {
    const conf = computeConfidence({ r2: 0.15 });
    expect(conf.level).toBe('low');
    expect(conf.reason).toContain('R²');
  });

  it('R² >= 0.6 yields high confidence', () => {
    const conf = computeConfidence({ r2: 0.85 });
    expect(conf.level).toBe('high');
  });

  it('few data points cap confidence at medium', () => {
    const conf = computeConfidence({ r2: 0.90, nPoints: 20 });
    expect(conf.level).toBe('medium');
    expect(conf.reason).toContain('20 jours');
  });
});
