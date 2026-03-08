/**
 * PROMEOS — Conso V2 Audit — Source-guard tests
 * Verify consumption/performance/diagnostic pages have required constructs.
 * Tests 100% readFileSync / regex — no DOM mock needed.
 */
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect, beforeAll } from 'vitest';

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

  required.forEach((fn) => {
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
    expect(code).toMatch(/météo réelle UTC|UTC.*weather|utcWeather/);
    expect(code).toMatch(/synthétique|synthetique/);
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

// ============================================================
// AW. Portfolio V1 — Backend endpoints
// ============================================================
describe('AW · Portfolio V1 backend endpoints', () => {
  const code = readBackend('routes', 'portfolio.py');

  it('portfolio.py exists', () => {
    expect(code).toBeDefined();
  });

  it('has GET /summary endpoint', () => {
    expect(code).toMatch(/@router\.get\(["']\/summary["']\)/);
  });

  it('has GET /sites endpoint', () => {
    expect(code).toMatch(/@router\.get\(["']\/sites["']\)/);
  });

  it('returns totals with kwh, eur, co2', () => {
    expect(code).toMatch(/kwh_total/);
    expect(code).toMatch(/eur_total/);
    expect(code).toMatch(/co2_total/);
  });

  it('returns coverage with sites_total and sites_with_data', () => {
    expect(code).toMatch(/sites_total/);
    expect(code).toMatch(/sites_with_data/);
  });

  it('returns top_drift, top_base_night, top_peaks', () => {
    expect(code).toMatch(/top_drift/);
    expect(code).toMatch(/top_base_night/);
    expect(code).toMatch(/top_peaks/);
  });

  it('sites endpoint supports sort, confidence, search, pagination', () => {
    expect(code).toMatch(/sort.*kwh_desc/s);
    expect(code).toMatch(/confidence/);
    expect(code).toMatch(/search/);
    expect(code).toMatch(/limit.*Query/);
    expect(code).toMatch(/offset.*Query/);
  });

  it('portfolio router is registered in main.py', () => {
    const main = readBackend('main.py');
    expect(main).toMatch(/portfolio_router/);
  });
});

// ============================================================
// AX. Portfolio V1 — Frontend page
// ============================================================
describe('AX · ConsumptionPortfolioPage structure', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('ConsumptionPortfolioPage.jsx exists', () => {
    expect(code).toBeDefined();
  });

  it('calls getPortfolioSummary and getPortfolioSites', () => {
    expect(code).toMatch(/getPortfolioSummary/);
    expect(code).toMatch(/getPortfolioSites/);
  });

  it('has 4 KPI cards (kWh, EUR/Cout, CO2, Couverture)', () => {
    expect(code).toMatch(/kWh total/);
    expect(code).toMatch(/Cout estime|EUR total/);
    expect(code).toMatch(/CO2|Emissions/);
    expect(code).toMatch(/Couverture/);
  });

  it('has "Ou agir" section with 4 top-lists', () => {
    expect(code).toMatch(/Ou agir/);
    expect(code).toMatch(/Impact.*estim[eé]/);
    expect(code).toMatch(/Derives detectees/);
    expect(code).toMatch(/nocturne/i);
    expect(code).toMatch(/Pics de puissance/);
  });

  it('has site table with search, sort, confidence filters', () => {
    expect(code).toMatch(/Rechercher un site/);
    expect(code).toMatch(/setSort/);
    expect(code).toMatch(/confidenceFilter/);
    expect(code).toMatch(/anomalyFilter/);
  });

  it('has row actions (Explorer, Diagnostic, Voir facture, Creer action)', () => {
    expect(code).toMatch(/toConsoExplorer|\/consommations\/explorer/);
    expect(code).toMatch(/toConsoDiag|\/diagnostic-conso/);
    expect(code).toMatch(/toBillIntel|deepLinkWithContext/);
    expect(code).toMatch(/toActionNew|deepLinkNewAction/);
  });

  it('has loading skeletons and empty state', () => {
    expect(code).toMatch(/SkeletonCard/);
    expect(code).toMatch(/Aucun site ne correspond aux filtres/);
  });

  it('has toast error handling', () => {
    expect(code).toMatch(/useToast/);
    expect(code).toMatch(/addToast.*error/);
  });

  it('has pagination (Precedent/Suivant)', () => {
    expect(code).toMatch(/Precedent/);
    expect(code).toMatch(/Suivant/);
  });
});

// ============================================================
// AY. Portfolio V1 — Route & Tab integration
// ============================================================
describe('AY · Portfolio route & tab integration', () => {
  it('App.jsx has ConsumptionPortfolioPage lazy import', () => {
    const app = readSrc('App.jsx');
    expect(app).toMatch(/ConsumptionPortfolioPage/);
  });

  it('App.jsx has /consommations/portfolio route', () => {
    const app = readSrc('App.jsx');
    expect(app).toMatch(/path="portfolio".*ConsumptionPortfolioPage/s);
  });

  it('ConsommationsPage has Portefeuille tab', () => {
    const page = readSrc('pages', 'ConsommationsPage.jsx');
    expect(page).toMatch(/Portefeuille/);
    expect(page).toMatch(/\/consommations\/portfolio/);
  });

  it('api.js exports getPortfolioSummary and getPortfolioSites', () => {
    const api = readSrc('services', 'api.js');
    expect(api).toMatch(/export const getPortfolioSummary/);
    expect(api).toMatch(/export const getPortfolioSites/);
  });

  it('api.js calls /portfolio/consumption/ endpoints', () => {
    const api = readSrc('services', 'api.js');
    expect(api).toMatch(/\/portfolio\/consumption\/summary/);
    expect(api).toMatch(/\/portfolio\/consumption\/sites/);
  });
});

// ============================================================
// AZ. KPI Explorer coherence fix
// ============================================================
describe('AZ · KPI Explorer coherence — totalKwh from hphc', () => {
  const code = readSrc('components', 'ConsoKpiHeader.jsx');

  it('ConsoKpiHeader uses hphc?.total_kwh as primary kWh source', () => {
    expect(code).toMatch(/hphc\?\.total_kwh/);
  });

  it('ConsoKpiHeader fallback chain includes tunnel and progression', () => {
    // hphc?.total_kwh ?? tunnel?.total_kwh ?? progression?.ytd_actual_kwh
    expect(code).toMatch(/hphc\?\.total_kwh.*tunnel\?\.total_kwh.*progression\?\.ytd_actual_kwh/);
  });

  it('ConsoKpiHeader still uses hphc for EUR total', () => {
    expect(code).toMatch(/hphc\?\.total_cost_eur/);
  });
});

// ============================================================
// BA. Portfolio V1.1 — Impact EUR + Actions + CTA groupee
// ============================================================
describe('BA · Portfolio V1.1 backend enhancements', () => {
  const code = readBackend('routes', 'portfolio.py');

  it('imports ActionItem and ActionStatus', () => {
    expect(code).toMatch(/from models\.action_item import ActionItem/);
    expect(code).toMatch(/from models\.enums import ActionStatus/);
  });

  it('has impact_eur_estimated in site row', () => {
    expect(code).toMatch(/impact_eur_estimated/);
  });

  it('has open_actions_count in site row', () => {
    expect(code).toMatch(/open_actions_count/);
  });

  it('has top_impact list in summary', () => {
    expect(code).toMatch(/top_impact/);
  });

  it('has with_actions filter (with/without)', () => {
    expect(code).toMatch(/with_actions.*with/);
    expect(code).toMatch(/with_actions.*without/);
  });

  it('has impact_desc sort option', () => {
    expect(code).toMatch(/impact_desc/);
  });

  it('has impact_eur_total in summary totals', () => {
    expect(code).toMatch(/impact_eur_total/);
  });
});

describe('BB · Portfolio V1.1+ frontend enhancements', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('has Impact EUR column header', () => {
    expect(code).toMatch(/Impact EUR/);
  });

  it('has impact_eur_estimated display in table rows', () => {
    expect(code).toMatch(/impact_eur_estimated/);
  });

  it('has open_actions_count display in table rows', () => {
    expect(code).toMatch(/open_actions_count/);
  });

  it('has actionsFilter state (with/without)', () => {
    expect(code).toMatch(/actionsFilter/);
    expect(code).toMatch(/Avec actions/);
    expect(code).toMatch(/Sans action/);
  });

  it('default sort is impact_desc', () => {
    expect(code).toMatch(/useState\(['"]impact_desc['"]\)/);
  });

  it('has impact_desc sort option in select', () => {
    expect(code).toMatch(/value="impact_desc"/);
    expect(code).toMatch(/Impact EUR decroissant/);
  });

  it('has grouped action CTA button', () => {
    expect(code).toMatch(/handleGroupedAction/);
    expect(code).toMatch(/campaign_sites|site_ids/);
    expect(code).toMatch(/Lancer campagne/);
  });

  it('has top_impact section in "Ou agir"', () => {
    expect(code).toMatch(/top_impact/);
    expect(code).toMatch(/Impact.*estim[eé]/);
  });
});

// ============================================================
// BC. Route Registry — navigation sans surprise
// ============================================================
describe('BC · Route registry file exists and exports helpers', () => {
  const code = readSrc('services', 'routes.js');

  it('exports toConsoExplorer', () => {
    expect(code).toMatch(/export function toConsoExplorer/);
  });

  it('exports toConsoDiag', () => {
    expect(code).toMatch(/export function toConsoDiag/);
  });

  it('exports toBillIntel', () => {
    expect(code).toMatch(/export function toBillIntel/);
  });

  it('exports toActionNew', () => {
    expect(code).toMatch(/export function toActionNew/);
  });

  it('exports toAction', () => {
    expect(code).toMatch(/export function toAction/);
  });

  it('exports toConsoImport', () => {
    expect(code).toMatch(/export function toConsoImport/);
  });

  it('toConsoExplorer builds /consommations/explorer with sites param', () => {
    expect(code).toMatch(/\/consommations\/explorer/);
    expect(code).toMatch(/sites/);
  });

  it('toConsoDiag builds /diagnostic-conso with site_id param', () => {
    expect(code).toMatch(/\/diagnostic-conso/);
    expect(code).toMatch(/site_id/);
  });

  it('toBillIntel builds /bill-intel with site_id and month params', () => {
    expect(code).toMatch(/\/bill-intel/);
    expect(code).toMatch(/month/);
  });

  it('toActionNew builds /actions/new with type, source, campaign_sites', () => {
    expect(code).toMatch(/\/actions\/new/);
    expect(code).toMatch(/campaign_sites/);
  });
});

// ============================================================
// BD. Portfolio V1.3 — scope coherence + route registry usage
// ============================================================
describe('BD · Portfolio V1.3 scope coherence banner', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(code).toMatch(/useScope/);
    expect(code).toMatch(/ScopeContext/);
  });

  it('reads selectedSiteId, resetScope, scopeLabel from useScope', () => {
    expect(code).toMatch(/selectedSiteId/);
    expect(code).toMatch(/resetScope/);
    expect(code).toMatch(/scopeLabel/);
  });

  it('shows scope banner with user-friendly message', () => {
    expect(code).toMatch(/Portefeuille = vue multi-sites/);
    expect(code).toMatch(/scopeLabel/);
  });

  it('has "Passer a Tous les sites" button calling resetScope', () => {
    expect(code).toMatch(/Passer a Tous les sites/);
    expect(code).toMatch(/resetScope/);
  });

  it('does not use PageShell (nested inside ConsommationsPage)', () => {
    expect(code).not.toMatch(/PageShell/);
  });
});

describe('BE · Portfolio V1.3 uses route registry (no hardcoded routes)', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('imports route helpers from services/routes', () => {
    expect(code).toMatch(/from.*services\/routes/);
    expect(code).toMatch(/toConsoExplorer/);
    expect(code).toMatch(/toConsoDiag/);
    expect(code).toMatch(/toBillIntel/);
    expect(code).toMatch(/toActionNew/);
  });

  it('does NOT import deepLinkWithContext or deepLinkNewAction (replaced by registry)', () => {
    expect(code).not.toMatch(/deepLinkWithContext/);
    expect(code).not.toMatch(/deepLinkNewAction/);
  });

  it('TopListActions uses route registry helpers', () => {
    expect(code).toMatch(/toConsoExplorer.*site_id.*siteId/);
    expect(code).toMatch(/toConsoDiag.*site_id.*siteId/);
    expect(code).toMatch(/toBillIntel.*site_id.*siteId/);
    expect(code).toMatch(/toActionNew.*source.*portfolio_toplist/s);
  });

  it('table row actions use route registry helpers', () => {
    expect(code).toMatch(/toConsoExplorer.*site_id.*row\.site_id/);
    expect(code).toMatch(/toBillIntel.*site_id.*row\.site_id/);
  });

  it('has TopListActions with all 4 top-lists', () => {
    const matches = code.match(/TopListActions/g);
    expect(matches.length).toBeGreaterThanOrEqual(5);
  });
});

describe('BF · Portfolio V1.3 pilotage UX', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('has pilotage header with site count and period', () => {
    expect(code).toMatch(/Vous pilotez/);
    expect(code).toMatch(/sites_total/);
  });

  it('has coverage % with tooltip', () => {
    expect(code).toMatch(/coveragePct/);
    expect(code).toMatch(/Couverture/);
    expect(code).toMatch(/HelpCircle/);
  });

  it('has KPI card with "Cout estime" label and source explanation', () => {
    expect(code).toMatch(/Cout estime/);
    expect(code).toMatch(/0,18 EUR\/kWh/);
  });

  it('has KPI card with "Emissions CO2" and ADEME source', () => {
    expect(code).toMatch(/Emissions CO2/);
    expect(code).toMatch(/ADEME 2024/);
  });

  it('has row click handler navigating to Explorer', () => {
    expect(code).toMatch(/handleRowClick/);
    expect(code).toMatch(/cursor-pointer/);
    expect(code).toMatch(/Cliquez pour explorer/);
  });

  it('Actions column is smart: shows eye icon when actions exist, plus icon otherwise', () => {
    expect(code).toMatch(/Eye/);
    expect(code).toMatch(/open_actions_count > 0/);
    expect(code).toMatch(/Voir les actions en cours/);
    expect(code).toMatch(/Cr[eé]er une action/);
  });

  it('Diagnostics count is a clickable button linking to diag page', () => {
    expect(code).toMatch(/diagnostics_count > 0/);
    expect(code).toMatch(/Voir les diagnostics/);
    expect(code).toMatch(/toConsoDiag/);
  });
});

describe('BG · Portfolio V1.3 guided empty state', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('has handleResetFilters function', () => {
    expect(code).toMatch(/handleResetFilters/);
  });

  it('has hasActiveFilters computed flag', () => {
    expect(code).toMatch(/hasActiveFilters/);
  });

  it('has "Réinitialiser les filtres" button with RotateCcw icon', () => {
    expect(code).toMatch(/initialiser les filtres/);
    expect(code).toMatch(/RotateCcw/);
  });

  it('has "Importer des données" CTA using toConsoImport', () => {
    expect(code).toMatch(/Importer des donn/);
    expect(code).toMatch(/toConsoImport/);
  });

  it('shows contextual message based on hasActiveFilters', () => {
    expect(code).toMatch(/hasActiveFilters/);
    expect(code).toMatch(/initialiser les filtres/i);
    expect(code).toMatch(/Importez vos relevés|Importez des données|Importez vos relev/);
  });
});

// ============================================================
// BH. Explorer scope coherence — single-site banner
// ============================================================
describe('BH · Explorer scope coherence banner', () => {
  const code = readSrc('pages', 'ConsumptionExplorerPage.jsx');

  it('reads scopeLabel from useScope', () => {
    expect(code).toMatch(/scopeLabel/);
  });

  it('shows scope banner when selectedSiteId and single site', () => {
    expect(code).toMatch(/selectedSiteId && siteIds\.length === 1/);
    expect(code).toMatch(/Vous explorez/);
    expect(code).toMatch(/scopeLabel/);
  });

  it('mentions multi-selection is available', () => {
    expect(code).toMatch(/multi-selection/i);
  });
});

// ============================================================
// BI. Portfolio API — skipSiteHeader defense-in-depth
// ============================================================
describe('BI · Portfolio API skipSiteHeader', () => {
  const apiCode = readSrc('services', 'api.js');

  it('interceptor supports skipSiteHeader flag', () => {
    expect(apiCode).toMatch(/skipSiteHeader/);
    expect(apiCode).toMatch(/!config\.skipSiteHeader/);
  });

  it('getPortfolioSummary passes skipSiteHeader: true', () => {
    expect(apiCode).toMatch(/getPortfolioSummary[\s\S]*?skipSiteHeader:\s*true/);
  });

  it('getPortfolioSites passes skipSiteHeader: true', () => {
    expect(apiCode).toMatch(/getPortfolioSites[\s\S]*?skipSiteHeader:\s*true/);
  });
});

// ============================================================
// BJ. Portfolio empty state — Cas A (no data) vs Cas B (filters)
// ============================================================
describe('BJ · Portfolio empty state Cas A vs Cas B', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');

  it('has Cas A empty state for no data', () => {
    expect(code).toMatch(/Aucune donnée de consommation/);
  });

  it('has Cas B empty state for filters', () => {
    expect(code).toMatch(/Aucun site ne correspond aux filtres/);
  });

  it('Cas A shows import CTA via toConsoImport', () => {
    expect(code).toMatch(/toConsoImport/);
    expect(code).toMatch(/Importer des donn/);
  });

  it('Cas B shows reset filters button', () => {
    expect(code).toMatch(/initialiser les filtres/);
    expect(code).toMatch(/handleResetFilters/);
  });

  it('Cas B shows active filter chips (search, confidence, anomaly, actions)', () => {
    expect(code).toMatch(/confidenceFilter/);
    expect(code).toMatch(/anomalyFilter/);
    expect(code).toMatch(/actionsFilter/);
    expect(code).toMatch(/Anomalies uniquement/);
  });

  it('distinguishes Cas A vs Cas B via sites_total', () => {
    expect(code).toMatch(/sites_total/);
    expect(code).toMatch(/cov\?\.sites_total/);
  });
});

// ============================================================
// BK. Route registry — helpers return valid URLs, no undefined
// ============================================================
describe('BK · Route registry helpers', () => {
  // Dynamic import of route helpers (ESM)
  let routes;
  beforeAll(async () => {
    routes = await import('../../services/routes.js');
  });

  it('toConsoExplorer() returns /consommations/explorer', () => {
    expect(routes.toConsoExplorer()).toBe('/consommations/explorer');
  });

  it('toConsoExplorer({ site_id: 5 }) encodes site param', () => {
    const url = routes.toConsoExplorer({ site_id: 5 });
    expect(url).toMatch(/^\/consommations\/explorer\?/);
    expect(url).toContain('sites=5');
    expect(url).not.toContain('undefined');
  });

  it('toConsoExplorer supports date_from / date_to (mapped to period_start/period_end)', () => {
    const url = routes.toConsoExplorer({
      site_id: 1,
      date_from: '2025-01-01',
      date_to: '2025-01-31',
    });
    // Step 11: date_from/date_to are mapped to period_start/period_end for unified period
    expect(url).toContain('period_start=2025-01-01');
    expect(url).toContain('period_end=2025-01-31');
  });

  it('toConsoExplorer supports multi-site array', () => {
    const url = routes.toConsoExplorer({ site_id: [1, 2, 3] });
    expect(url).toContain('sites=1%2C2%2C3');
  });

  it('toConsoDiag() returns /diagnostic-conso', () => {
    expect(routes.toConsoDiag()).toBe('/diagnostic-conso');
  });

  it('toConsoDiag({ site_id: 7 }) encodes site_id', () => {
    const url = routes.toConsoDiag({ site_id: 7 });
    expect(url).toBe('/diagnostic-conso?site_id=7');
  });

  it('toBillIntel() returns /bill-intel', () => {
    expect(routes.toBillIntel()).toBe('/bill-intel');
  });

  it('toBillIntel({ site_id: 3, month: "2025-06" }) encodes params', () => {
    const url = routes.toBillIntel({ site_id: 3, month: '2025-06' });
    expect(url).toContain('site_id=3');
    expect(url).toContain('month=2025-06');
  });

  it('toActionNew() returns /actions/new', () => {
    expect(routes.toActionNew()).toBe('/actions/new');
  });

  it('toActionNew with campaign encodes site_ids', () => {
    const url = routes.toActionNew({ site_ids: [1, 2], source: 'portfolio', title: 'Test' });
    expect(url).toContain('campaign_sites=1%2C2');
    expect(url).toContain('source=portfolio');
    expect(url).toContain('titre=Test');
  });

  it('toAction(42) returns /actions/42', () => {
    expect(routes.toAction(42)).toBe('/actions/42');
  });

  it('toActionsList({ site_id: 5 }) returns /anomalies?tab=actions&site_id=5', () => {
    expect(routes.toActionsList({ site_id: 5 })).toBe('/anomalies?tab=actions&site_id=5');
  });

  it('toConsoImport() returns /consommations/import', () => {
    expect(routes.toConsoImport()).toBe('/consommations/import');
  });

  it('no helper returns a URL containing "undefined"', () => {
    const urls = [
      routes.toConsoExplorer(),
      routes.toConsoExplorer({ site_id: 1 }),
      routes.toConsoDiag(),
      routes.toBillIntel(),
      routes.toActionNew(),
      routes.toAction(1),
      routes.toActionsList(),
      routes.toConsoImport(),
    ];
    urls.forEach((url) => {
      expect(url).toMatch(/^\//);
      expect(url).not.toContain('undefined');
      expect(url).not.toContain('null');
    });
  });
});

// ============================================================
// BL. Conso pages — zero hardcoded URLs in conso scope
// ============================================================
describe('BL · No hardcoded navigation URLs in conso scope', () => {
  const portfolio = readSrc('pages', 'ConsumptionPortfolioPage.jsx');
  const diag = readSrc('pages', 'ConsumptionDiagPage.jsx');
  const usages = readSrc('pages', 'ConsommationsUsages.jsx');

  it('Portfolio uses toActionsList instead of hardcoded /actions?site_id', () => {
    expect(portfolio).toMatch(/toActionsList/);
    expect(portfolio).not.toMatch(/navigate\(`\/actions\?site_id=/);
  });

  it('DiagPage uses toConsoExplorer instead of hardcoded /consommations/explorer', () => {
    expect(diag).toMatch(/toConsoExplorer/);
    expect(diag).not.toMatch(/navigate\(`\/consommations\/explorer\?/);
  });

  it('ConsommationsUsages uses toConsoExplorer instead of hardcoded URL', () => {
    expect(usages).toMatch(/toConsoExplorer/);
    expect(usages).not.toMatch(/navigate\(`\/consommations\/explorer/);
  });
});

// ============================================================
// BM. Portfolio V2 — patrimoine-first features
// ============================================================
describe('BM · Portfolio V2 patrimoine-first', () => {
  const code = readSrc('pages', 'ConsumptionPortfolioPage.jsx');
  const backend = readBackend('routes', 'portfolio.py');

  it('frontend has DataStatusBadge component', () => {
    expect(code).toMatch(/DataStatusBadge/);
    expect(code).toMatch(/data_status/);
    expect(code).toMatch(/coverage_pct/);
  });

  it('frontend shows data_status badge per row', () => {
    expect(code).toMatch(/<DataStatusBadge/);
    expect(code).toMatch(/status=\{row\.data_status\}/);
  });

  it('frontend has Couverture column in table header', () => {
    expect(code).toMatch(/Couverture/);
  });

  it('frontend has "Sans donnees" filter chip', () => {
    expect(code).toMatch(/noDataFilter/);
    expect(code).toMatch(/Sans donnees/);
    expect(code).toMatch(/without_data/);
  });

  it('frontend has coverage sort option', () => {
    expect(code).toMatch(/coverage.*Couverture donnees/);
  });

  it('frontend row click navigates to import if data_status is none', () => {
    expect(code).toMatch(/data_status === 'none'/);
    expect(code).toMatch(/toConsoImport/);
  });

  it('frontend shows inline "Importer" CTA for sites without data', () => {
    expect(code).toMatch(/Importer/);
    expect(code).toMatch(/<Upload/);
  });

  it('frontend shows last_reading_date per site', () => {
    expect(code).toMatch(/last_reading_date/);
    expect(code).toMatch(/Dernier releve/);
  });

  it('frontend passes date_from/date_to to toConsoExplorer in row actions', () => {
    expect(code).toMatch(/toConsoExplorer\(\{.*date_from.*dates\.from/s);
  });

  it('frontend shows "X sans donnees" in header when applicable', () => {
    expect(code).toMatch(/sites_without_data/);
    expect(code).toMatch(/sans donnees/);
  });

  it('backend has data_status field (ok/partial/none)', () => {
    expect(backend).toMatch(/"data_status":\s*data_status/);
    expect(backend).toMatch(/data_status = "none"/);
    expect(backend).toMatch(/data_status = "ok"/);
    expect(backend).toMatch(/data_status = "partial"/);
  });

  it('backend has coverage_pct per site', () => {
    expect(backend).toMatch(/"coverage_pct":\s*coverage_pct/);
  });

  it('backend has without_data filter', () => {
    expect(backend).toMatch(/without_data/);
    expect(backend).toMatch(/data_status.*==.*"none"/);
  });

  it('backend has coverage sort option', () => {
    expect(backend).toMatch(/"coverage":/);
    expect(backend).toMatch(/coverage_pct/);
  });

  it('backend summary includes sites_without_data', () => {
    expect(backend).toMatch(/sites_without_data/);
  });
});
