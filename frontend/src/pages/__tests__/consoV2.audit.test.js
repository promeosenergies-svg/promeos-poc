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

// ============================================================
// AO. QW6 — Toast errors + empty states + skeletons
// ============================================================
describe('AO · QW6 toast errors & empty states', () => {
  const explorer = readSrc('pages', 'ConsumptionExplorerPage.jsx');
  const diag = readSrc('pages', 'ConsumptionDiagPage.jsx');
  const monitoring = readSrc('pages', 'MonitoringPage.jsx');

  it('ConsumptionExplorerPage imports useToast', () => {
    expect(explorer).toMatch(/useToast/);
  });

  it('ConsumptionExplorerPage has no console.error', () => {
    expect(explorer).not.toMatch(/console\.error/);
  });

  it('ConsumptionExplorerPage passes toast prop to panels', () => {
    expect(explorer).toMatch(/toast=\{toast\}/);
  });

  it('ConsumptionExplorerPage SmartEmptyState has onGenerateDemo', () => {
    expect(explorer).toMatch(/onGenerateDemo/);
  });

  it('ConsumptionExplorerPage SmartEmptyState has isExpert debug', () => {
    expect(explorer).toMatch(/isExpert.*&&.*reasons/);
  });

  it('ConsumptionDiagPage has no console.error', () => {
    expect(diag).not.toMatch(/console\.error/);
  });

  it('ConsumptionDiagPage uses SkeletonCard for loading', () => {
    expect(diag).toMatch(/SkeletonCard/);
  });

  it('MonitoringPage has no console.error', () => {
    expect(monitoring).not.toMatch(/console\.error/);
  });

  it('MonitoringPage uses SkeletonCard', () => {
    expect(monitoring).toMatch(/SkeletonCard/);
  });
});

// ============================================================
// AP. QW2 — ConsoKpiHeader component
// ============================================================
describe('AP · QW2 ConsoKpiHeader', () => {
  it('ConsoKpiHeader.jsx exists', () => {
    expect(srcExists('components', 'ConsoKpiHeader.jsx')).toBe(true);
  });

  it('ConsoKpiHeader has 6 KPI tiles', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/kWh total/);
    expect(code).toMatch(/EUR total/);
    expect(code).toMatch(/EUR\/MWh/);
    expect(code).toMatch(/CO2e/);
    expect(code).toMatch(/Pic kW.*P95/);
    expect(code).toMatch(/Base nocturne/);
  });

  it('ConsoKpiHeader accepts tunnel + hphc + progression props', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/tunnel/);
    expect(code).toMatch(/hphc/);
    expect(code).toMatch(/progression/);
  });

  it('ConsoKpiHeader has confidence badge', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/TrustBadge|confidence/);
  });

  it('ConsumptionExplorerPage integrates ConsoKpiHeader', () => {
    const explorer = readSrc('pages', 'ConsumptionExplorerPage.jsx');
    expect(explorer).toMatch(/ConsoKpiHeader/);
  });
});

// ============================================================
// AQ. QW5 — Deep-link "Voir facture" from diagnostic
// ============================================================
describe('AQ · QW5 deep-link facture', () => {
  const diag = readSrc('pages', 'ConsumptionDiagPage.jsx');

  it('imports deepLinkWithContext', () => {
    expect(diag).toMatch(/deepLinkWithContext/);
  });

  it('has onViewInvoice handler', () => {
    expect(diag).toMatch(/handleViewInvoice|onViewInvoice/);
  });

  it('EvidenceDrawer has "Voir facture" CTA', () => {
    expect(diag).toMatch(/Voir facture/);
  });

  it('navigates to /bill-intel with context', () => {
    expect(diag).toMatch(/deepLinkWithContext/);
  });

  it('deepLink.js exports deepLinkWithContext and deepLinkNewAction', () => {
    const dl = readSrc('services', 'deepLink.js');
    expect(dl).toMatch(/export function deepLinkWithContext/);
    expect(dl).toMatch(/export function deepLinkNewAction/);
  });
});

// ============================================================
// AR. P1-1 — Benchmark reference curve
// ============================================================
describe('AR · P1-1 benchmark reference curve', () => {
  it('BenchmarkPanel.jsx exists', () => {
    expect(srcExists('pages', 'consumption', 'BenchmarkPanel.jsx')).toBe(true);
  });

  it('BenchmarkPanel has toggle checkbox', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/Comparer a la courbe moyenne/);
    expect(code).toMatch(/type="checkbox"/);
  });

  it('BenchmarkPanel has 3 famille options and 5 puissance options', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/habitat/);
    expect(code).toMatch(/petit_tertiaire/);
    expect(code).toMatch(/entreprise/);
    expect(code).toMatch(/0-6/);
    expect(code).toMatch(/6-9/);
    expect(code).toMatch(/9-12/);
    expect(code).toMatch(/12-36/);
    expect(code).toMatch(/>36/);
  });

  it('BenchmarkPanel has 4 KPI cards (actual, reference, ecart, couverture)', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/Votre consommation/);
    expect(code).toMatch(/Moyenne sites similaires/);
    expect(code).toMatch(/Ecart/);
    expect(code).toMatch(/Couverture/);
  });

  it('BenchmarkPanel has TrustBadge for confidence', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/TrustBadge/);
    expect(code).toMatch(/confidence/);
  });

  it('BenchmarkPanel calls getEmsReferenceProfile', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/getEmsReferenceProfile/);
  });

  it('BenchmarkPanel renders dual-area chart (actual + reference)', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/dataKey="actual"/);
    expect(code).toMatch(/dataKey="reference"/);
  });

  it('ConsumptionExplorerPage integrates BenchmarkPanel in both modes', () => {
    const explorer = readSrc('pages', 'ConsumptionExplorerPage.jsx');
    // Should appear at least twice (Classic + Expert)
    const matches = explorer.match(/BenchmarkPanel/g);
    expect(matches?.length).toBeGreaterThanOrEqual(3); // import + 2 usages
  });

  it('api.js exports getEmsReferenceProfile', () => {
    const api = readSrc('services', 'api.js');
    expect(api).toMatch(/export const getEmsReferenceProfile/);
  });

  it('backend has /reference_profile endpoint with REFERENCE_PROFILES', () => {
    const ems = readBackend('routes', 'ems.py');
    expect(ems).toMatch(/@router\.get.*reference_profile/);
    expect(ems).toMatch(/REFERENCE_PROFILES/);
  });
});

// ============================================================
// AS. P1-2 — Heatmap interactive (drill-down + filter)
// ============================================================
describe('AS · P1-2 heatmap interactive', () => {
  it('HeatmapChart accepts onCellClick and filter props', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/onCellClick/);
    expect(code).toMatch(/filter/);
  });

  it('HeatmapChart has cursor-pointer on clickable cells', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/cursor-pointer/);
  });

  it('HeatmapChart shows "Cliquez sur un creneau pour le detail" when clickable', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/Cliquez sur un creneau pour le detail/);
  });

  it('HeatmapChart has title attribute on cells for native tooltip', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/title=/);
  });

  it('HeatmapChart filters weekday/weekend via visibleDays', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/visibleDays/);
    expect(code).toMatch(/weekday/);
    expect(code).toMatch(/weekend/);
  });

  it('SignaturePanel has drill-down state and dayFilter', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/drillDown/);
    expect(code).toMatch(/dayFilter/);
  });

  it('SignaturePanel has filter pills (Semaine typique / Jours ouvres / Week-ends)', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/Semaine typique/);
    expect(code).toMatch(/Jours ouvres/);
    expect(code).toMatch(/Week-ends/);
  });

  it('SignaturePanel renders drill-down AreaChart for selected cell', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/drillDownData/);
    expect(code).toMatch(/AreaChart/);
    expect(code).toMatch(/Detail/);
  });

  it('SignaturePanel passes onCellClick to HeatmapChart', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/onCellClick/);
  });
});

// ============================================================
// AT. P1-3 — Overlay meteo UTC (DST-safe)
// ============================================================
describe('AT · P1-3 overlay meteo UTC', () => {
  it('MeteoPanel imports getEmsWeatherHourly', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/getEmsWeatherHourly/);
  });

  it('MeteoPanel has "Afficher la temperature" toggle', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/Afficher la temperature/);
    expect(code).toMatch(/showTemp/);
  });

  it('MeteoPanel has UTC weather fetch with fallback to synthetic', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/utcWeather/);
    expect(code).toMatch(/generateSyntheticTemp/);
  });

  it('MeteoPanel shows weather source in disclaimer', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/API UTC.*serveur.*DST-safe/);
    expect(code).toMatch(/synthetique/);
  });

  it('MeteoPanel conditionally renders temperature Line and YAxis', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/showTemp &&/);
    expect(code).toMatch(/yAxisId="temp"/);
  });

  it('api.js exports getEmsWeatherHourly', () => {
    const api = readSrc('services', 'api.js');
    expect(api).toMatch(/export const getEmsWeatherHourly/);
  });

  it('backend has /weather_hourly endpoint with UTC timestamps', () => {
    const ems = readBackend('routes', 'ems.py');
    expect(ems).toMatch(/@router\.get.*weather_hourly/);
    expect(ems).toMatch(/timezone.*UTC/);
  });

  it('backend weather_hourly uses sinusoidal interpolation', () => {
    const ems = readBackend('routes', 'ems.py');
    expect(ems).toMatch(/math\.sin/);
    expect(ems).toMatch(/phase/);
  });

  it('backend weather_hourly returns Z suffix timestamps', () => {
    const ems = readBackend('routes', 'ems.py');
    expect(ems).toMatch(/:00:00Z/);
  });
});

// ============================================================
// AU. P1.1 — Polish UX labels + tooltips + confidence
// ============================================================
describe('AU · P1.1 polish labels & tooltips', () => {
  it('BenchmarkPanel uses "courbe moyenne de sites similaires" label', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/courbe moyenne de sites similaires/);
  });

  it('BenchmarkPanel KPI shows "Votre consommation" and "Moyenne sites similaires"', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/Votre consommation/);
    expect(code).toMatch(/Moyenne sites similaires/);
  });

  it('BenchmarkPanel has confidence tooltip with HelpCircle', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/Comment calcule/);
    expect(code).toMatch(/HelpCircle/);
  });

  it('BenchmarkPanel KPI shows source (releves / profil statistique)', () => {
    const code = readSrc('pages', 'consumption', 'BenchmarkPanel.jsx');
    expect(code).toMatch(/Source : releves/);
    expect(code).toMatch(/Profil statistique/);
  });

  it('ConsoKpiHeader has EUR source (Estime HP/HC)', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/Estime HP\/HC/);
    expect(code).toMatch(/eurSource/);
  });

  it('ConsoKpiHeader has confidence tooltip with HelpCircle', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/Comment calcule/);
    expect(code).toMatch(/HelpCircle/);
  });

  it('ConsoKpiHeader KPI tiles have tooltip prop', () => {
    const code = readSrc('components', 'ConsoKpiHeader.jsx');
    expect(code).toMatch(/tooltip=/);
    // At least 6 tooltip props (one per tile) — some use template literals
    const matches = code.match(/tooltip[=]/g);
    expect(matches?.length).toBeGreaterThanOrEqual(6);
  });

  it('SignaturePanel uses "Jours ouvres" and "Week-ends" labels', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/Jours ouvres/);
    expect(code).toMatch(/Week-ends/);
  });

  it('HeatmapChart uses "consommation moyenne" label', () => {
    const code = readSrc('pages', 'consumption', 'HeatmapChart.jsx');
    expect(code).toMatch(/consommation moyenne/);
  });

  it('MeteoPanel has weather source badge (reelle vs synthetique)', () => {
    const code = readSrc('pages', 'consumption', 'MeteoPanel.jsx');
    expect(code).toMatch(/Meteo reelle/);
    expect(code).toMatch(/Meteo synthetique/);
    expect(code).toMatch(/isRealWeather/);
  });
});

// ============================================================
// AV. P1.1 — Drill-down CTAs (Analyser + Voir facture)
// ============================================================
describe('AV · P1.1 drill-down CTAs', () => {
  it('SignaturePanel imports deepLinkWithContext', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/deepLinkWithContext/);
  });

  it('SignaturePanel has "Analyser ce creneau" CTA linking to /diagnostic-conso', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/Analyser ce creneau/);
    expect(code).toMatch(/diagnostic-conso/);
  });

  it('SignaturePanel has "Voir facture" CTA with deepLinkWithContext', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/Voir facture/);
    expect(code).toMatch(/deepLinkWithContext.*primarySiteId/);
  });

  it('SignaturePanel uses primarySiteId from siteIds for CTAs', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/primarySiteId.*=.*siteIds/);
  });

  it('SignaturePanel passes site_id and hour to diagnostic link', () => {
    const code = readSrc('pages', 'consumption', 'SignaturePanel.jsx');
    expect(code).toMatch(/site_id=.*primarySiteId/);
    expect(code).toMatch(/hour=.*drillDown\.hour/);
  });

  it('ConsumptionExplorerPage passes siteIds to SignaturePanel (scope coherence)', () => {
    const explorer = readSrc('pages', 'ConsumptionExplorerPage.jsx');
    expect(explorer).toMatch(/SignaturePanel siteIds=\{siteIds\}/);
  });
});
