/**
 * contractRadarV99.test.js — V99 "Contract Renewal Radar" source guards
 *
 * Verifies:
 *   A. ContractRadarPage.jsx exists with correct content
 *   B. api.js has all V99 functions
 *   C. NavRegistry + App.jsx wired for /renouvellements
 *   D. Backend contract_radar_service has compute_contract_radar
 *   E. Backend purchase_scenarios_service has compute_purchase_scenarios
 *   F. Backend routes contracts_radar.py has 4 endpoints
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) => readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');
const backendExists = (rel) => existsSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel));

const PAGE = src('pages/ContractRadarPage.jsx');
const API_JS = src('services/api.js');
const NAV_REG = src('layout/NavRegistry.js');
const APP_JSX = src('App.jsx');

// ── A. ContractRadarPage ─────────────────────────────────────────────

describe('A. ContractRadarPage', () => {
  test('exports default', () => {
    expect(PAGE).toMatch(/export default function ContractRadarPage/);
  });

  test('imports PageShell', () => {
    expect(PAGE).toMatch(/PageShell/);
  });

  test('imports Table', () => {
    expect(PAGE).toMatch(/Table/);
  });

  test('imports Drawer', () => {
    expect(PAGE).toMatch(/Drawer/);
  });

  test('imports Badge', () => {
    expect(PAGE).toMatch(/Badge/);
  });

  test('calls getContractRadar', () => {
    expect(PAGE).toMatch(/getContractRadar/);
  });

  test('calls getContractPurchaseScenarios', () => {
    expect(PAGE).toMatch(/getContractPurchaseScenarios/);
  });

  test('calls createActionsFromScenario', () => {
    expect(PAGE).toMatch(/createActionsFromScenario/);
  });

  test('calls getContractScenarioSummary', () => {
    expect(PAGE).toMatch(/getContractScenarioSummary/);
  });

  test('has window.print', () => {
    expect(PAGE).toMatch(/window\.print/);
  });

  test('has ScenarioDrawer', () => {
    expect(PAGE).toMatch(/ScenarioDrawer/);
  });

  test('has ScenarioSummaryModal', () => {
    expect(PAGE).toMatch(/ScenarioSummaryModal/);
  });

  test('has ScenarioCard', () => {
    expect(PAGE).toMatch(/ScenarioCard/);
  });

  test('has CalendarRange icon', () => {
    expect(PAGE).toMatch(/CalendarRange/);
  });

  test('has horizon filter', () => {
    expect(PAGE).toMatch(/HORIZON_OPTIONS/);
  });
});

// ── B. api.js V99 functions ──────────────────────────────────────────

describe('B. api.js V99', () => {
  test('getContractRadar', () => {
    expect(API_JS).toMatch(/getContractRadar/);
  });

  test('getContractPurchaseScenarios', () => {
    expect(API_JS).toMatch(/getContractPurchaseScenarios/);
  });

  test('createActionsFromScenario', () => {
    expect(API_JS).toMatch(/createActionsFromScenario/);
  });

  test('getContractScenarioSummary', () => {
    expect(API_JS).toMatch(/getContractScenarioSummary/);
  });
});

// ── C. NavRegistry + App.jsx wiring ──────────────────────────────────

describe('C. NavRegistry + App wiring', () => {
  test('NavRegistry has /renouvellements', () => {
    expect(NAV_REG).toMatch(/\/renouvellements/);
  });

  test('NavRegistry maps to operations module', () => {
    expect(NAV_REG).toMatch(/renouvellements.*operations|operations.*renouvellements/s);
  });

  test('NavRegistry has Renouvellements label', () => {
    expect(NAV_REG).toMatch(/Renouvellements/);
  });

  test('NavRegistry has CalendarRange icon', () => {
    expect(NAV_REG).toMatch(/CalendarRange/);
  });

  test('App.jsx has ContractRadarPage', () => {
    expect(APP_JSX).toMatch(/ContractRadarPage/);
  });

  test('App.jsx has /renouvellements route', () => {
    expect(APP_JSX).toMatch(/\/renouvellements/);
  });
});

// ── D. Backend contract_radar_service ────────────────────────────────

describe('D. Backend contract_radar_service', () => {
  test('file exists', () => {
    expect(backendExists('services/contract_radar_service.py')).toBe(true);
  });

  test('has compute_contract_radar', () => {
    const svc = backend('services/contract_radar_service.py');
    expect(svc).toMatch(/compute_contract_radar/);
  });

  test('has _compute_urgency', () => {
    const svc = backend('services/contract_radar_service.py');
    expect(svc).toMatch(/_compute_urgency/);
  });

  test('has _compute_status', () => {
    const svc = backend('services/contract_radar_service.py');
    expect(svc).toMatch(/_compute_status/);
  });

  test('has INDEXATION_LABELS', () => {
    const svc = backend('services/contract_radar_service.py');
    expect(svc).toMatch(/INDEXATION_LABELS/);
  });
});

// ── E. Backend purchase_scenarios_service ─────────────────────────────

describe('E. Backend purchase_scenarios_service', () => {
  test('file exists', () => {
    expect(backendExists('services/purchase_scenarios_service.py')).toBe(true);
  });

  test('has compute_purchase_scenarios', () => {
    const svc = backend('services/purchase_scenarios_service.py');
    expect(svc).toMatch(/compute_purchase_scenarios/);
  });

  test('has SCENARIO_TEMPLATES', () => {
    const svc = backend('services/purchase_scenarios_service.py');
    expect(svc).toMatch(/SCENARIO_TEMPLATES/);
  });

  test('has _estimate_annual_volume', () => {
    const svc = backend('services/purchase_scenarios_service.py');
    expect(svc).toMatch(/_estimate_annual_volume/);
  });

  test('has 3 scenario IDs (A, B, C)', () => {
    const svc = backend('services/purchase_scenarios_service.py');
    expect(svc).toMatch(/"A"/);
    expect(svc).toMatch(/"B"/);
    expect(svc).toMatch(/"C"/);
  });
});

// ── F. Backend routes contracts_radar.py ──────────────────────────────

describe('F. Backend routes contracts_radar', () => {
  test('file exists', () => {
    expect(backendExists('routes/contracts_radar.py')).toBe(true);
  });

  test('has /radar endpoint', () => {
    const routes = backend('routes/contracts_radar.py');
    expect(routes).toMatch(/\/radar/);
  });

  test('has /purchase-scenarios endpoint', () => {
    const routes = backend('routes/contracts_radar.py');
    expect(routes).toMatch(/purchase-scenarios/);
  });

  test('has /actions/from-scenario endpoint', () => {
    const routes = backend('routes/contracts_radar.py');
    expect(routes).toMatch(/actions\/from-scenario/);
  });

  test('has /scenario-summary endpoint', () => {
    const routes = backend('routes/contracts_radar.py');
    expect(routes).toMatch(/scenario-summary/);
  });

  test('has ScenarioActionCreate schema', () => {
    const routes = backend('routes/contracts_radar.py');
    expect(routes).toMatch(/ScenarioActionCreate/);
  });
});
