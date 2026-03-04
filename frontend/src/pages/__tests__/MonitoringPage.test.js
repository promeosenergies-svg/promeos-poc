/**
 * PROMEOS — Tests for MonitoringPage helpers
 * Covers: buildHeatmapGrid, kpiStatus, computeConfidence, kpiStatusWithConfidence,
 *         LF thresholds, groupInsights, CLIMATE_REASONS, CLIMATE_LABEL_FR
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
  buildHeatmapGrid,
  kpiStatus,
  computeConfidence,
  kpiStatusWithConfidence,
  LF_THRESHOLDS_BY_ARCHETYPE,
  groupInsights,
  CLIMATE_REASONS,
  CLIMATE_LABEL_FR,
  USAGE_DAYS_FR,
  formatSchedule,
  computeOffHoursEstimate,
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
      expect.arrayContaining([
        'office',
        'hotel',
        'retail',
        'warehouse',
        'school',
        'hospital',
        'default',
      ])
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
    id,
    alert_type: type,
    meter_id: meterId,
    site_id: siteId,
    estimated_impact_eur: eur,
    estimated_impact_kwh: eur * 5,
    severity,
    status: 'open',
    explanation: `Alert ${id}`,
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
    const alerts = [mkAlert(1, 'A', 100), mkAlert(2, 'B', 500)];
    const grouped = groupInsights(alerts);
    expect(grouped[0].alert_type).toBe('B');
    expect(grouped[1].alert_type).toBe('A');
  });

  it('handles empty list', () => {
    expect(groupInsights([])).toEqual([]);
  });

  it('same type + different meters + same site = merged (site-level)', () => {
    const alerts = [mkAlert(1, 'X', 100, 'high', 1, 10), mkAlert(2, 'X', 200, 'critical', 2, 10)];
    const grouped = groupInsights(alerts);
    expect(grouped).toHaveLength(1);
    expect(grouped[0]._count).toBe(2);
    expect(grouped[0]._totalEur).toBe(300);
    expect(grouped[0]._maxSeverity).toBe('critical');
    expect(grouped[0]._meters.size).toBe(2);
  });

  it('same type + different sites = separate groups', () => {
    const alerts = [mkAlert(1, 'X', 100, 'high', 1, 10), mkAlert(2, 'X', 200, 'high', 2, 20)];
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
    const expected = [
      'no_meter',
      'no_weather',
      'meter_not_found',
      'insufficient_readings',
      'computation_error',
    ];
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

  it('unknown label uses proper French accent (déterminé)', () => {
    expect(CLIMATE_LABEL_FR.unknown).toBe('Non déterminé');
  });
});

describe('V9 FR copy — accents in exported constants', () => {
  it('CLIMATE_REASONS use proper French accents', () => {
    expect(CLIMATE_REASONS.no_meter).toContain('associé');
    expect(CLIMATE_REASONS.no_weather).toContain('météo');
    expect(CLIMATE_REASONS.no_weather).toContain('période');
    expect(CLIMATE_REASONS.insufficient_readings).toContain('données');
    expect(CLIMATE_REASONS.insufficient_readings).toContain('régression');
    expect(CLIMATE_REASONS.computation_error).toContain('Vérifiez');
    expect(CLIMATE_REASONS.computation_error).toContain('données');
  });

  it('computeConfidence reason text uses accents', () => {
    const c = computeConfidence({ r2: 0.9, nPoints: 20 });
    expect(c.reason).toContain('données');
  });

  it('computeConfidence default reason uses accents', () => {
    const c = computeConfidence({ r2: 0.9, nPoints: 60, coveragePct: 90 });
    expect(c.reason).toContain('Données suffisantes');
  });
});

describe('USAGE_DAYS_FR', () => {
  it('maps 0-6 to French day abbreviations', () => {
    expect(USAGE_DAYS_FR[0]).toBe('Lun');
    expect(USAGE_DAYS_FR[4]).toBe('Ven');
    expect(USAGE_DAYS_FR[6]).toBe('Dim');
  });

  it('has all 7 days', () => {
    expect(Object.keys(USAGE_DAYS_FR)).toHaveLength(7);
  });
});

describe('formatSchedule', () => {
  it('returns 24/7 for is_24_7 schedule', () => {
    expect(
      formatSchedule({
        open_days: '0,1,2,3,4,5,6',
        open_time: '00:00',
        close_time: '23:59',
        is_24_7: true,
      })
    ).toBe('24/7');
  });

  it('returns Lun-Ven for weekday-only schedule', () => {
    const result = formatSchedule({
      open_days: '0,1,2,3,4',
      open_time: '08:00',
      close_time: '19:00',
      is_24_7: false,
    });
    expect(result).toBe('Lun-Ven 08:00-19:00');
  });

  it('returns dash for null input', () => {
    expect(formatSchedule(null)).toBe('-');
  });

  it('handles custom day subsets', () => {
    const result = formatSchedule({
      open_days: '0,1,2,3,4,5',
      open_time: '09:00',
      close_time: '20:00',
      is_24_7: false,
    });
    expect(result).toBe('Lun, Mar, Mer, Jeu, Ven, Sam 09:00-20:00');
  });
});

describe('computeOffHoursEstimate', () => {
  it('returns zero for null input', () => {
    const r = computeOffHoursEstimate(null);
    expect(r.eur).toBe(0);
    expect(r.label).toBe('-');
  });

  it('returns zero for zero kWh', () => {
    expect(computeOffHoursEstimate(0).eur).toBe(0);
  });

  it('returns zero for negative kWh', () => {
    expect(computeOffHoursEstimate(-100).eur).toBe(0);
  });

  it('annualizes from 90d and applies price', () => {
    // 1000 kWh over 90 days → (1000 * 365/90) * 0.18 = ~730 EUR
    const r = computeOffHoursEstimate(1000, 0.18);
    const expected = Math.round(1000 * (365 / 90) * 0.18);
    expect(r.eur).toBe(expected);
    expect(r.label).toContain('EUR/an');
  });

  it('accepts custom price', () => {
    const r = computeOffHoursEstimate(1000, 0.25);
    const expected = Math.round(1000 * (365 / 90) * 0.25);
    expect(r.eur).toBe(expected);
    expect(r.price).toBe(0.25);
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
    const conf = computeConfidence({ r2: 0.9, nPoints: 20 });
    expect(conf.level).toBe('medium');
    expect(conf.reason).toContain('20 jours');
  });
});

describe('V9 CO2e: MonitoringPage includes Leaf import and CO2e KPI card', () => {
  const src = readFileSync(resolve(__dirname, '../MonitoringPage.jsx'), 'utf8');

  it('imports Leaf icon from lucide-react', () => {
    expect(src).toContain('Leaf');
    expect(src).toMatch(/import\s*\{[^}]*Leaf[^}]*\}\s*from\s*'lucide-react'/);
  });

  it('has CO2e KPI card with title', () => {
    expect(src).toContain('title="CO₂e"');
  });

  it('ExecutiveSummary has Empreinte CO2e card', () => {
    expect(src).toContain("'Empreinte CO₂e'");
  });

  it('passes emissions prop to ExecutiveSummary', () => {
    expect(src).toContain('emissions={emissions}');
  });

  it('passes emissions prop to OffHoursDrawer', () => {
    const drawerSection = src.slice(src.indexOf('<OffHoursDrawer'));
    expect(drawerSection).toContain('emissions={emissions}');
  });
});

describe('MonitoringPage: no TDZ on loadSiteActions', () => {
  const src = readFileSync(resolve(__dirname, '../MonitoringPage.jsx'), 'utf8');

  it('loadSiteActions is declared before any useEffect that references it', () => {
    const declLine = src.indexOf('const loadSiteActions = useCallback');
    const effectUseLine = src.indexOf('loadSiteActions()');
    expect(declLine).toBeGreaterThan(-1);
    expect(effectUseLine).toBeGreaterThan(-1);
    expect(declLine).toBeLessThan(effectUseLine);
  });

  it('loadSiteActions is declared before the useEffect dep array that references it', () => {
    const declLine = src.indexOf('const loadSiteActions = useCallback');
    const depLine = src.indexOf('loadSiteActions]');
    expect(declLine).toBeGreaterThan(-1);
    expect(depLine).toBeGreaterThan(-1);
    expect(declLine).toBeLessThan(depLine);
  });

  it('no duplicate loadSiteActions declarations', () => {
    const matches = src.match(/const loadSiteActions = useCallback/g);
    expect(matches).toHaveLength(1);
  });
});

// ── QW1 guard: MonitoringPage accent & cleanup ──────────────────────────────

describe('QW1 guard — MonitoringPage accents FR', () => {
  const src = readFileSync(resolve(__dirname, '../MonitoringPage.jsx'), 'utf8');

  it('PROFILE_OPTIONS: École avec accent', () => {
    expect(src).toContain("label: 'École'");
    expect(src).not.toContain("label: 'Ecole'");
  });

  it('PROFILE_OPTIONS: Hôpital avec accent', () => {
    expect(src).toContain("label: 'Hôpital'");
    expect(src).not.toContain("label: 'Hopital'");
  });

  it('Résolu / Résoudre / Résolus avec accents', () => {
    expect(src).not.toMatch(/['"]Resolu['"]/);
    expect(src).not.toMatch(/['"]Resolus['"]/);
    expect(src).not.toMatch(/>Resoudre</);
  });

  it('Sévérité avec accents dans le thead', () => {
    expect(src).toContain('Sévérité');
    expect(src).not.toMatch(/>Severite</);
  });

  it('détecter avec accent dans empty state', () => {
    expect(src).toContain('détecter');
    expect(src).not.toContain('detecter les anomalies');
  });

  it('résolution avec accent dans toast', () => {
    expect(src).toContain('résolution');
    expect(src).not.toContain("la resolution'");
  });

  it('défaut avec accent dans archetype fallback', () => {
    expect(src).toContain('(défaut)');
    expect(src).not.toContain('(defaut)');
  });

  it('useMemo inutile sur mockSites supprimé', () => {
    expect(src).not.toMatch(/useMemo\(\(\)\s*=>\s*mockSites/);
  });
});
