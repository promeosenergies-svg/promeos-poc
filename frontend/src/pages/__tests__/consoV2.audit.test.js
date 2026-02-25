/**
 * PROMEOS — Conso V2 Audit — Source-guard tests
 * Verify consumption/performance/diagnostic pages have required constructs.
 * Tests 100% readFileSync / regex — no DOM mock needed.
 */
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');
const readBackend = (...parts) => readFileSync(resolve(root, '..', 'backend', ...parts), 'utf-8');
const srcExists = (...parts) => existsSync(resolve(root, 'src', ...parts));

// ============================================================
// AH. ConsumptionExplorerPage — filters & panels
// ============================================================
describe('AH · ConsumptionExplorerPage structure', () => {
  const code = readSrc('pages', 'ConsumptionExplorerPage.jsx');

  it('has site filter (useScope or site selector)', () => {
    expect(code).toMatch(/useScope|StickyFilterBar|selectedSites/);
  });

  it('has period filter (days/dateRange)', () => {
    expect(code).toMatch(/days|dateRange|date_from|date_to/);
  });

  it('has granularity selector', () => {
    expect(code).toMatch(/granularity|granularite/i);
  });

  it('has energy type selector', () => {
    expect(code).toMatch(/energyType|energy_type|electricity|gas/);
  });

  it('renders TimeseriesPanel', () => {
    expect(code).toMatch(/TimeseriesPanel/);
  });

  it('renders TunnelPanel', () => {
    expect(code).toMatch(/TunnelPanel/);
  });

  it('renders TargetsPanel', () => {
    expect(code).toMatch(/TargetsPanel/);
  });

  it('renders HPHCPanel', () => {
    expect(code).toMatch(/HPHCPanel/);
  });

  it('handles availability data (has_data check)', () => {
    expect(code).toMatch(/has_data|availability/);
  });
});

// ============================================================
// AI. ConsumptionDiagPage — diagnostic capabilities
// ============================================================
describe('AI · ConsumptionDiagPage structure', () => {
  const code = readSrc('pages', 'ConsumptionDiagPage.jsx');

  it('calls getConsumptionInsights', () => {
    expect(code).toMatch(/getConsumptionInsights/);
  });

  it('calls runConsumptionDiagnose', () => {
    expect(code).toMatch(/runConsumptionDiagnose/);
  });

  it('has insight type filter (hors_horaires, base_load, etc.)', () => {
    expect(code).toMatch(/hors_horaires|base_load|pointe|derive|data_gap/);
  });

  it('has EvidenceDrawer component', () => {
    expect(code).toMatch(/EvidenceDrawer|evidence/i);
  });

  it('has workflow status management (patchConsumptionInsight)', () => {
    expect(code).toMatch(/patchConsumptionInsight|insight_status/);
  });

  it('renders summary KPI cards', () => {
    expect(code).toMatch(/SummaryCard|estimated_loss/);
  });
});

// ============================================================
// AJ. MonitoringPage — performance capabilities
// ============================================================
describe('AJ · MonitoringPage structure', () => {
  const code = readSrc('pages', 'MonitoringPage.jsx');

  it('calls getMonitoringKpis', () => {
    expect(code).toMatch(/getMonitoringKpis/);
  });

  it('has HeatmapGrid component', () => {
    expect(code).toMatch(/HeatmapGrid|heatmap/i);
  });

  it('has comparison mode (N-1)', () => {
    expect(code).toMatch(/compare|getMonitoringKpisCompare|n-1|previous/i);
  });

  it('has emissions data', () => {
    expect(code).toMatch(/emissions|co2|CO2/);
  });

  it('has off-hours analysis', () => {
    expect(code).toMatch(/off.?hours|hors.?horaires|OffHoursDrawer/i);
  });

  it('has climate/weather correlation', () => {
    expect(code).toMatch(/climate|ClimateScatter|weather|meteo/i);
  });

  it('has alert workflow (ack/resolve)', () => {
    expect(code).toMatch(/ackMonitoringAlert|resolveMonitoringAlert/);
  });
});

// ============================================================
// AK. Backend — consumption endpoints exist
// ============================================================
describe('AK · Backend consumption routes', () => {
  const diag = readBackend('routes', 'consumption_diagnostic.py');
  const ems = readBackend('routes', 'ems.py');
  const monitoring = readBackend('routes', 'monitoring.py');

  it('consumption_diagnostic has /availability endpoint', () => {
    expect(diag).toMatch(/@router\.(get|post).*availability/i);
  });

  it('consumption_diagnostic has /tunnel_v2 endpoint', () => {
    expect(diag).toMatch(/tunnel_v2/);
  });

  it('consumption_diagnostic has /targets endpoint', () => {
    expect(diag).toMatch(/@router\.(get|post).*targets/i);
  });

  it('consumption_diagnostic has /diagnose endpoint', () => {
    expect(diag).toMatch(/@router\.post.*diagnose/i);
  });

  it('consumption_diagnostic has /hphc_breakdown_v2 endpoint', () => {
    expect(diag).toMatch(/hphc_breakdown_v2/);
  });

  it('EMS has /timeseries endpoint', () => {
    expect(ems).toMatch(/@router\.get.*timeseries/i);
  });

  it('EMS has /signature/run endpoint', () => {
    expect(ems).toMatch(/signature.*run/i);
  });

  it('EMS has /weather endpoint', () => {
    expect(ems).toMatch(/@router\.get.*weather/i);
  });

  it('monitoring has /kpis endpoint', () => {
    expect(monitoring).toMatch(/@router\.get.*kpis/i);
  });

  it('monitoring has /kpis/compare endpoint', () => {
    expect(monitoring).toMatch(/kpis.*compare/i);
  });

  it('monitoring has /alerts endpoint', () => {
    expect(monitoring).toMatch(/@router\.get.*alerts/i);
  });

  it('monitoring has /emissions endpoint', () => {
    expect(monitoring).toMatch(/emissions/i);
  });
});

// ============================================================
// AL. Backend — diagnostic service capabilities
// ============================================================
describe('AL · Diagnostic service detectors', () => {
  const svc = readBackend('services', 'consumption_diagnostic.py');

  it('has hors_horaires detector', () => {
    expect(svc).toMatch(/_detect_hors_horaires/);
  });

  it('has base_load detector', () => {
    expect(svc).toMatch(/_detect_base_load/);
  });

  it('has pointe detector', () => {
    expect(svc).toMatch(/_detect_pointe/);
  });

  it('has derive detector', () => {
    expect(svc).toMatch(/_detect_derive/);
  });

  it('has data_gap detector', () => {
    expect(svc).toMatch(/_detect_data_gap/);
  });

  it('generates recommended actions per detector', () => {
    expect(svc).toMatch(/_actions_hors_horaires|_actions_base_load/);
  });
});

// ============================================================
// AM. api.js — consumption API functions
// ============================================================
describe('AM · api.js consumption functions', () => {
  const api = readSrc('services', 'api.js');

  const required = [
    'getConsumptionAvailability',
    'getConsumptionTunnelV2',
    'getConsumptionTargets',
    'getTargetsProgressionV2',
    'getHPHCBreakdownV2',
    'getConsumptionInsights',
    'runConsumptionDiagnose',
    'getMonitoringKpis',
    'getMonitoringAlerts',
    'getEmsTimeseries',
  ];

  required.forEach(fn => {
    it(`exports ${fn}`, () => {
      expect(api).toMatch(new RegExp(`export (const|function) ${fn}`));
    });
  });
});

// ============================================================
// AN. Data quality — backend granularity support
// ============================================================
describe('AN · Granularity & data quality', () => {
  const ems = readBackend('routes', 'ems.py');
  const tsService = readBackend('services', 'ems', 'timeseries_service.py');

  it('EMS supports multiple granularities', () => {
    expect(ems).toMatch(/granularity/);
  });

  it('timeseries service enforces point cap', () => {
    expect(tsService).toMatch(/5000|MAX_POINTS|cap/i);
  });

  it('timeseries service has availability/gaps detection', () => {
    expect(tsService).toMatch(/availability|gaps|coverage/i);
  });

  it('consumption_diagnostic detects data gaps', () => {
    const svc = readBackend('services', 'consumption_diagnostic.py');
    expect(svc).toMatch(/_detect_data_gap/);
  });
});
