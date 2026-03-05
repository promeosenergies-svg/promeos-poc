/**
 * PROMEOS — C.4: Tests KPI Messaging
 * Tests unitaires du service + source-guard intégration.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { getKpiMessage, SUPPORTED_KPIS } from '../services/kpiMessaging';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. Service kpiMessaging — structure ──────────────────────────────────────

describe('A. kpiMessaging — structure', () => {
  it('exporte getKpiMessage', () => {
    expect(typeof getKpiMessage).toBe('function');
  });

  it('exporte SUPPORTED_KPIS', () => {
    expect(Array.isArray(SUPPORTED_KPIS)).toBe(true);
    expect(SUPPORTED_KPIS.length).toBeGreaterThanOrEqual(8);
  });

  it('contient les 4 KPIs executive', () => {
    expect(SUPPORTED_KPIS).toContain('conformite');
    expect(SUPPORTED_KPIS).toContain('risque');
    expect(SUPPORTED_KPIS).toContain('maturite');
    expect(SUPPORTED_KPIS).toContain('couverture');
  });

  it('contient les KPIs billing', () => {
    expect(SUPPORTED_KPIS).toContain('anomalies');
    expect(SUPPORTED_KPIS).toContain('billing_coverage');
  });

  it('contient les KPIs monitoring', () => {
    expect(SUPPORTED_KPIS).toContain('data_quality_score');
    expect(SUPPORTED_KPIS).toContain('off_hours_ratio');
  });

  it('retourne null pour un KPI inconnu', () => {
    expect(getKpiMessage('unknown_kpi', 42)).toBeNull();
  });
});

// ── B. Messages conformité ──────────────────────────────────────────────────

describe('B. Conformité — messages contextuels', () => {
  it('score élevé (80+) → severity ok', () => {
    const msg = getKpiMessage('conformite', 85, { totalSites: 100 });
    expect(msg.severity).toBe('ok');
    expect(msg.simple).toBeTruthy();
    expect(msg.expert).toBeTruthy();
  });

  it('score moyen (50-79) → severity warn', () => {
    const msg = getKpiMessage('conformite', 60, { totalSites: 50, sitesAtRisk: 5 });
    expect(msg.severity).toBe('warn');
    expect(msg.simple).toContain('5');
    expect(msg.action).toBeDefined();
  });

  it('score faible (<50) → severity crit', () => {
    const msg = getKpiMessage('conformite', 30, { sitesAtRisk: 12, sitesNonConformes: 8 });
    expect(msg.severity).toBe('crit');
    expect(msg.action).toBeDefined();
  });

  it('valeur null → severity neutral', () => {
    const msg = getKpiMessage('conformite', null);
    expect(msg.severity).toBe('neutral');
  });

  it('valeur NaN → severity neutral', () => {
    const msg = getKpiMessage('conformite', NaN);
    expect(msg.severity).toBe('neutral');
  });
});

// ── C. Messages risque ──────────────────────────────────────────────────────

describe('C. Risque — messages contextuels', () => {
  it('risque 0 → ok', () => {
    const msg = getKpiMessage('risque', 0);
    expect(msg.severity).toBe('ok');
  });

  it('risque modéré (<10000) → warn', () => {
    const msg = getKpiMessage('risque', 5000, { sitesAtRisk: 2 });
    expect(msg.severity).toBe('warn');
  });

  it('risque élevé (≥10000) → crit', () => {
    const msg = getKpiMessage('risque', 90000, { sitesAtRisk: 12 });
    expect(msg.severity).toBe('crit');
    expect(msg.action).toBeDefined();
  });
});

// ── D. Messages anomalies ───────────────────────────────────────────────────

describe('D. Anomalies — messages contextuels', () => {
  it('0 anomalies → ok', () => {
    const msg = getKpiMessage('anomalies', 0);
    expect(msg.severity).toBe('ok');
  });

  it('1-3 anomalies → warn', () => {
    const msg = getKpiMessage('anomalies', 2, { totalLoss: 1500 });
    expect(msg.severity).toBe('warn');
    expect(msg.expert).toMatch(/1.500/);
  });

  it('4+ anomalies → crit', () => {
    const msg = getKpiMessage('anomalies', 7, { totalLoss: 4200 });
    expect(msg.severity).toBe('crit');
    expect(msg.action).toBeDefined();
  });
});

// ── E. Messages qualité données ─────────────────────────────────────────────

describe('E. Qualité données — messages', () => {
  it('score élevé → ok', () => {
    const msg = getKpiMessage('data_quality_score', 90);
    expect(msg.severity).toBe('ok');
  });

  it('score moyen → warn', () => {
    const msg = getKpiMessage('data_quality_score', 60);
    expect(msg.severity).toBe('warn');
  });

  it('score faible → crit', () => {
    const msg = getKpiMessage('data_quality_score', 30);
    expect(msg.severity).toBe('crit');
  });
});

// ── F. Messages kWh/m² ──────────────────────────────────────────────────────

describe('F. kWh/m² — benchmark comparisons', () => {
  it('sous la moyenne → ok', () => {
    const msg = getKpiMessage('kwh_m2', 120, { benchmark: 145, usage: 'bureaux' });
    expect(msg.severity).toBe('ok');
    expect(msg.simple).toContain('sous');
  });

  it('au-dessus modéré → warn', () => {
    const msg = getKpiMessage('kwh_m2', 170, { benchmark: 145 });
    expect(msg.severity).toBe('warn');
    expect(msg.simple).toContain('au-dessus');
  });

  it('très au-dessus (>30%) → crit', () => {
    const msg = getKpiMessage('kwh_m2', 210, { benchmark: 145 });
    expect(msg.severity).toBe('crit');
    expect(msg.action).toBeDefined();
  });
});

// ── G. Format du message ────────────────────────────────────────────────────

describe('G. Format — structure du message', () => {
  for (const kpiId of SUPPORTED_KPIS) {
    it(`${kpiId} retourne simple + expert + severity`, () => {
      const msg = getKpiMessage(kpiId, 50);
      expect(msg).toBeDefined();
      expect(typeof msg.simple).toBe('string');
      expect(typeof msg.expert).toBe('string');
      expect(['ok', 'warn', 'crit', 'neutral']).toContain(msg.severity);
      expect(msg.simple.length).toBeGreaterThan(0);
      expect(msg.expert.length).toBeGreaterThan(0);
    });
  }
});

// ── H. Intégration source-guard ─────────────────────────────────────────────

describe('H. Intégration — source-guard', () => {
  it('ExecutiveKpiRow importe getKpiMessage', () => {
    const src = readSrc('pages/cockpit/ExecutiveKpiRow.jsx');
    expect(src).toContain('getKpiMessage');
  });

  it('ExecutiveKpiRow a data-testid kpi-message', () => {
    const src = readSrc('pages/cockpit/ExecutiveKpiRow.jsx');
    expect(src).toContain('kpi-message');
  });

  it('dashboardEssentials fournit rawValue', () => {
    const src = readSrc('models/dashboardEssentials.js');
    expect(src).toContain('rawValue');
  });

  it('dashboardEssentials fournit messageCtx', () => {
    const src = readSrc('models/dashboardEssentials.js');
    expect(src).toContain('messageCtx');
  });

  it('BillIntelPage utilise getKpiMessage', () => {
    const src = readSrc('pages/BillIntelPage.jsx');
    expect(src).toContain('getKpiMessage');
  });

  it('MonitoringPage utilise getKpiMessage', () => {
    const src = readSrc('pages/MonitoringPage.jsx');
    expect(src).toContain('getKpiMessage');
  });
});
