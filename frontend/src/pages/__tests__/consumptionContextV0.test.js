/**
 * PROMEOS — Consumption Context V0 — Source-guard tests
 * Vérifie la présence des constructs V0 dans les fichiers sources.
 * Tests 100% readFileSync / regex — aucun mock DOM requis.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');  // → frontend/

const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');
const readBackend = (...parts) => readFileSync(resolve(root, '..', 'backend', ...parts), 'utf-8');

// ============================================================
// A. Page structure — ConsumptionContextPage.jsx
// ============================================================
describe('ConsumptionContextPage — structure', () => {
  const code = readSrc('pages', 'ConsumptionContextPage.jsx');

  it('uses PageShell with Activity icon', () => {
    expect(code).toMatch(/PageShell/);
    expect(code).toMatch(/icon=\{?Activity\}?/);
  });

  it('title includes Usages & Horaires', () => {
    expect(code).toMatch(/Usages & Horaires/);
  });

  it('defines 2 tabs: profile and horaires', () => {
    expect(code).toMatch(/id:\s*['"]profile['"]/);
    expect(code).toMatch(/id:\s*['"]horaires['"]/);
  });

  it('imports ProfileHeatmapTab', () => {
    expect(code).toMatch(/ProfileHeatmapTab/);
  });

  it('imports HorairesAnomaliesTab', () => {
    expect(code).toMatch(/HorairesAnomaliesTab/);
  });

  it('uses getConsumptionContext from api', () => {
    expect(code).toMatch(/getConsumptionContext/);
  });

  it('uses refreshConsumptionDiagnose from api', () => {
    expect(code).toMatch(/refreshConsumptionDiagnose/);
  });

  it('displays behavior_score KpiCard', () => {
    expect(code).toMatch(/behavior_score/);
    expect(code).toMatch(/KpiCard/);
  });
});

// ============================================================
// B. API imports — api.js
// ============================================================
describe('api.js — Consumption Context V0', () => {
  const code = readSrc('services', 'api.js');

  it('exports getConsumptionContext', () => {
    expect(code).toMatch(/export const getConsumptionContext/);
  });

  it('exports getConsumptionProfile', () => {
    expect(code).toMatch(/export const getConsumptionProfile/);
  });

  it('exports getConsumptionActivity', () => {
    expect(code).toMatch(/export const getConsumptionActivity/);
  });

  it('exports getConsumptionAnomalies', () => {
    expect(code).toMatch(/export const getConsumptionAnomalies/);
  });

  it('exports refreshConsumptionDiagnose', () => {
    expect(code).toMatch(/export const refreshConsumptionDiagnose/);
  });

  it('exports suggestSchedule', () => {
    expect(code).toMatch(/export const suggestSchedule/);
  });

  it('calls /consumption-context/site/ endpoints', () => {
    expect(code).toMatch(/\/consumption-context\/site\//);
  });
});

// ============================================================
// C. Route helper — routes.js
// ============================================================
describe('routes.js — toUsagesHoraires', () => {
  const code = readSrc('services', 'routes.js');

  it('exports toUsagesHoraires', () => {
    expect(code).toMatch(/export function toUsagesHoraires/);
  });

  it('returns /usages-horaires path', () => {
    expect(code).toMatch(/\/usages-horaires/);
  });

  it('accepts site_id and tab params', () => {
    expect(code).toMatch(/opts\.site_id/);
    expect(code).toMatch(/opts\.tab/);
  });
});

// ============================================================
// D. Heatmap — ProfileHeatmapTab.jsx
// ============================================================
describe('ProfileHeatmapTab — heatmap & profile', () => {
  const code = readSrc('pages', 'consumption', 'ProfileHeatmapTab.jsx');

  it('renders HeatmapGrid component', () => {
    expect(code).toMatch(/HeatmapGrid/);
  });

  it('has 7 day labels (Lun-Dim)', () => {
    expect(code).toMatch(/Lun.*Dim/);
  });

  it('renders DailyProfileChart', () => {
    expect(code).toMatch(/DailyProfileChart/);
  });

  it('uses Recharts AreaChart', () => {
    expect(code).toMatch(/AreaChart/);
  });

  it('displays baseload_kw and peak_kw', () => {
    expect(code).toMatch(/baseload_kw/);
    expect(code).toMatch(/peak_kw/);
  });

  it('displays load_factor', () => {
    expect(code).toMatch(/load_factor/);
  });
});

// ============================================================
// E. Score — HorairesAnomaliesTab.jsx
// ============================================================
describe('HorairesAnomaliesTab — score & breakdown', () => {
  const code = readSrc('pages', 'consumption', 'HorairesAnomaliesTab.jsx');

  it('renders behavior_score display', () => {
    expect(code).toMatch(/behavior_score/);
  });

  it('renders ScoreBadge with breakdown', () => {
    expect(code).toMatch(/ScoreBadge/);
    expect(code).toMatch(/breakdown/);
  });

  it('displays offhours_penalty', () => {
    expect(code).toMatch(/offhours_penalty/);
  });

  it('displays baseload_penalty', () => {
    expect(code).toMatch(/baseload_penalty/);
  });
});

// ============================================================
// F. Anomalies — AnomalyList
// ============================================================
describe('HorairesAnomaliesTab — anomalies', () => {
  const code = readSrc('pages', 'consumption', 'HorairesAnomaliesTab.jsx');

  it('renders AnomalyList', () => {
    expect(code).toMatch(/AnomalyList/);
  });

  it('limits to max 5 insights', () => {
    expect(code).toMatch(/slice\(0,\s*5\)/);
  });

  it('shows severity badges', () => {
    expect(code).toMatch(/severity/);
    expect(code).toMatch(/Badge/);
  });

  it('shows estimated_loss_eur', () => {
    expect(code).toMatch(/estimated_loss_eur/);
  });
});

// ============================================================
// G. Schedule display
// ============================================================
describe('HorairesAnomaliesTab — schedule', () => {
  const code = readSrc('pages', 'consumption', 'HorairesAnomaliesTab.jsx');

  it('renders ScheduleDisplay', () => {
    expect(code).toMatch(/ScheduleDisplay/);
  });

  it('shows open/close blocks per day', () => {
    expect(code).toMatch(/openDays/);
    expect(code).toMatch(/isOpen/);
  });

  it('renders WeekendActiveAlert', () => {
    expect(code).toMatch(/WeekendActiveAlert/);
  });
});

// ============================================================
// H. App.jsx route + NavRegistry
// ============================================================
describe('App.jsx — /usages-horaires route', () => {
  const code = readSrc('App.jsx');

  it('lazy-imports ConsumptionContextPage', () => {
    expect(code).toMatch(/ConsumptionContextPage/);
  });

  it('registers /usages-horaires route', () => {
    expect(code).toMatch(/\/usages-horaires/);
  });
});

describe('NavRegistry — usages-horaires entry', () => {
  const code = readSrc('layout', 'NavRegistry.js');

  it('adds /usages-horaires to nav items', () => {
    expect(code).toMatch(/\/usages-horaires/);
  });

  it('labels as Usages & Horaires', () => {
    expect(code).toMatch(/Usages & Horaires/);
  });

  it('maps /usages-horaires to analyse module', () => {
    expect(code).toMatch(/['"]\/usages-horaires['"]\s*:\s*['"]analyse['"]/);
  });
});

// ============================================================
// I. Backend service exists
// ============================================================
describe('Backend — consumption_context_service.py', () => {
  const code = readBackend('services', 'consumption_context_service.py');

  it('defines compute_behavior_score', () => {
    expect(code).toMatch(/def compute_behavior_score/);
  });

  it('defines detect_weekend_active', () => {
    expect(code).toMatch(/def detect_weekend_active/);
  });

  it('defines get_full_context', () => {
    expect(code).toMatch(/def get_full_context/);
  });

  it('defines suggest_schedule_from_naf', () => {
    expect(code).toMatch(/def suggest_schedule_from_naf/);
  });
});
