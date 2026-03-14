/**
 * Step 12 — F6 : KPI Labels Simple/Expert
 * Tests unitaires + source-guard pour la reformulation des KPIs.
 */
import { describe, it, expect } from 'vitest';
import { getKpiLabel, getKpiUnit, KPI_LABELS } from '../shared/kpiLabels';
import fs from 'fs';

describe('Step 12 — kpiLabels service', () => {
  it('getKpiLabel returns simple by default', () => {
    expect(getKpiLabel('pmax_kw')).toBe('Pic de puissance');
  });

  it('getKpiLabel returns expert when flag true', () => {
    expect(getKpiLabel('pmax_kw', true)).toBe('Puissance maximale (Pmax)');
  });

  it('getKpiLabel returns kpiId for unknown', () => {
    expect(getKpiLabel('unknown_kpi')).toBe('unknown_kpi');
  });

  it('getKpiUnit returns unit', () => {
    expect(getKpiUnit('pmax_kw')).toBe('kW');
  });

  it('getKpiUnit returns empty for unknown', () => {
    expect(getKpiUnit('unknown_kpi')).toBe('');
  });

  it('all KPI_LABELS have simple and expert', () => {
    Object.entries(KPI_LABELS).forEach(([_key, val]) => {
      expect(val.simple).toBeTruthy();
      expect(val.expert).toBeTruthy();
    });
  });

  it('at least 15 KPIs defined', () => {
    expect(Object.keys(KPI_LABELS).length).toBeGreaterThanOrEqual(15);
  });

  it('no English in simple labels', () => {
    const english = [
      'Load Factor',
      'Off-hours',
      'Baseload',
      'Night ratio',
      'Weekend ratio',
      'Power',
      'Score',
    ];
    Object.values(KPI_LABELS).forEach((val) => {
      english.forEach((en) => {
        expect(val.simple).not.toBe(en);
      });
    });
  });

  it('simple and expert differ for technical KPIs', () => {
    const technicalIds = ['pmax_kw', 'load_factor', 'off_hours_ratio'];
    technicalIds.forEach((id) => {
      const entry = KPI_LABELS[id];
      expect(entry.simple).not.toBe(entry.expert);
    });
  });
});

describe('Step 12 — Pages use getKpiLabel', () => {
  it('MonitoringPage uses getKpiLabel', () => {
    const src = fs.readFileSync('src/pages/MonitoringPage.jsx', 'utf8');
    expect(src).toContain('getKpiLabel');
    expect(src).toContain("from '../shared/kpiLabels'");
  });

  it('MonitoringPage no longer has hardcoded Pmax / P95 title', () => {
    const src = fs.readFileSync('src/pages/MonitoringPage.jsx', 'utf8');
    expect(src).not.toMatch(/title="Pmax \/ P95"/);
    expect(src).not.toMatch(/title="Talon \/ Base"/);
    expect(src).not.toMatch(/title="Facteur de charge"/);
    expect(src).not.toMatch(/title="Risque Puissance"/);
  });

  it('ConsoKpiHeader uses getKpiLabel', () => {
    const src = fs.readFileSync('src/components/ConsoKpiHeader.jsx', 'utf8');
    expect(src).toContain('getKpiLabel');
    expect(src).toContain('useExpertMode');
  });

  it('ConsoKpiHeader no longer has hardcoded Pic kW (P95)', () => {
    const src = fs.readFileSync('src/components/ConsoKpiHeader.jsx', 'utf8');
    expect(src).not.toMatch(/label="Pic kW \(P95\)"/);
    expect(src).not.toMatch(/label="Base nocturne"/);
    expect(src).not.toMatch(/label="kWh total"/);
  });

  it('InsightsPanel uses getKpiLabel', () => {
    const src = fs.readFileSync('src/pages/consumption/InsightsPanel.jsx', 'utf8');
    expect(src).toContain('getKpiLabel');
    expect(src).toContain('labelId');
  });

  it('InsightsPanel no longer has hardcoded label strings', () => {
    const src = fs.readFileSync('src/pages/consumption/InsightsPanel.jsx', 'utf8');
    expect(src).not.toMatch(/label: 'Pic P95'/);
    expect(src).not.toMatch(/label: 'Facteur de charge'/);
    expect(src).not.toMatch(/label: 'Talon P05'/);
  });
});
