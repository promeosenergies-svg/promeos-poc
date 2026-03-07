/**
 * v97ResolutionEngine.test.js — V97 "Resolution Engine" source guards
 *
 * Verifies:
 *   A. Site360 TabReconciliation has fix CTAs, toast, journal, evidence CSV
 *   B. PortfolioReconciliationPage exists with correct content
 *   C. api.js has all V97 functions
 *   D. NavRegistry + App.jsx wired for portfolio-reconciliation
 *   E. Backend reconciliation_service has fixer functions + evidence pack
 *   F. Backend routes have V97 endpoints
 *   G. ReconciliationFixLog model exists
 *   H. Migration has V97 function
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');
const backendExists = (rel) =>
  existsSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel));

const SITE360 = src('pages/Site360.jsx');
const PORTFOLIO_RECON = src('pages/PortfolioReconciliationPage.jsx');
const API_JS = src('services/api.js');
const NAV_REG = src('layout/NavRegistry.js');
const APP_JSX = src('App.jsx');

// ── A. Site360 TabReconciliation V97 ──────────────────────────────────

describe('A. Site360 TabReconciliation V97', () => {
  test('imports applyReconciliationFix', () => {
    expect(SITE360).toMatch(/applyReconciliationFix/);
  });

  test('imports getReconciliationHistory', () => {
    expect(SITE360).toMatch(/getReconciliationHistory/);
  });

  test('imports getReconciliationEvidenceCsv', () => {
    expect(SITE360).toMatch(/getReconciliationEvidenceCsv/);
  });

  test('has fix_actions rendering', () => {
    expect(SITE360).toMatch(/fix_actions/);
  });

  test('has toast state', () => {
    expect(SITE360).toMatch(/setToast/);
  });

  test('has handleFix function', () => {
    expect(SITE360).toMatch(/handleFix/);
  });

  test('has CSV download button', () => {
    expect(SITE360).toMatch(/CSV/);
  });

  test('has Journal button', () => {
    expect(SITE360).toMatch(/Journal/);
  });

  test('has fix history journal section', () => {
    expect(SITE360).toMatch(/Journal des corrections/);
  });

  test('has Wrench icon import', () => {
    expect(SITE360).toMatch(/Wrench/);
  });

  test('has Download icon import', () => {
    expect(SITE360).toMatch(/Download/);
  });

  test('has History icon import', () => {
    expect(SITE360).toMatch(/History/);
  });
});

// ── B. PortfolioReconciliationPage ────────────────────────────────────

describe('B. PortfolioReconciliationPage', () => {
  test('exists', () => {
    expect(PORTFOLIO_RECON).toBeTruthy();
  });

  test('contains "Réconciliation Portefeuille"', () => {
    expect(PORTFOLIO_RECON).toMatch(/Réconciliation Portefeuille/);
  });

  test('imports getPortfolioReconciliation', () => {
    expect(PORTFOLIO_RECON).toMatch(/getPortfolioReconciliation/);
  });

  test('imports getPortfolioReconciliationCsv', () => {
    expect(PORTFOLIO_RECON).toMatch(/getPortfolioReconciliationCsv/);
  });

  test('has status filter buttons', () => {
    expect(PORTFOLIO_RECON).toMatch(/setFilter/);
  });

  test('has search input', () => {
    expect(PORTFOLIO_RECON).toMatch(/setSearch/);
  });

  test('has Exporter CSV button', () => {
    expect(PORTFOLIO_RECON).toMatch(/Exporter CSV/);
  });

  test('has Résoudre CTA', () => {
    expect(PORTFOLIO_RECON).toMatch(/Résoudre/);
  });
});

// ── C. api.js V97 functions ──────────────────────────────────────────

describe('C. api.js V97', () => {
  test('applyReconciliationFix', () => {
    expect(API_JS).toMatch(/applyReconciliationFix/);
  });
  test('getReconciliationHistory', () => {
    expect(API_JS).toMatch(/getReconciliationHistory/);
  });
  test('getReconciliationEvidence', () => {
    expect(API_JS).toMatch(/getReconciliationEvidence/);
  });
  test('getReconciliationEvidenceCsv', () => {
    expect(API_JS).toMatch(/getReconciliationEvidenceCsv/);
  });
  test('getPortfolioReconciliationCsv', () => {
    expect(API_JS).toMatch(/getPortfolioReconciliationCsv/);
  });
});

// ── D. NavRegistry + App.jsx wiring ──────────────────────────────────

describe('D. NavRegistry + App wiring', () => {
  test('NavRegistry has /portfolio-reconciliation', () => {
    expect(NAV_REG).toMatch(/\/portfolio-reconciliation/);
  });

  test('NavRegistry has /portfolio-reconciliation in ROUTE_MODULE_MAP', () => {
    expect(NAV_REG).toMatch(/portfolio-reconciliation/);
  });

  test('App.jsx has PortfolioReconciliationPage', () => {
    expect(APP_JSX).toMatch(/PortfolioReconciliationPage/);
  });
});

// ── E. Backend reconciliation_service V97 ────────────────────────────

describe('E. Backend reconciliation_service V97', () => {
  const SVC = backend('services/reconciliation_service.py');

  test('has fix_create_delivery_point', () => {
    expect(SVC).toMatch(/fix_create_delivery_point/);
  });

  test('has fix_extend_contract', () => {
    expect(SVC).toMatch(/fix_extend_contract/);
  });

  test('has fix_adjust_contract_dates', () => {
    expect(SVC).toMatch(/fix_adjust_contract_dates/);
  });

  test('has fix_align_energy_type', () => {
    expect(SVC).toMatch(/fix_align_energy_type/);
  });

  test('has fix_create_payment_rule', () => {
    expect(SVC).toMatch(/fix_create_payment_rule/);
  });

  test('has get_fix_logs', () => {
    expect(SVC).toMatch(/get_fix_logs/);
  });

  test('has get_evidence_pack', () => {
    expect(SVC).toMatch(/get_evidence_pack/);
  });

  test('has _log_fix audit trail', () => {
    expect(SVC).toMatch(/_log_fix/);
  });

  test('has fix_actions in checks', () => {
    expect(SVC).toMatch(/fix_actions/);
  });
});

// ── F. Backend routes V97 endpoints ──────────────────────────────────

describe('F. Backend routes V97', () => {
  const ROUTES = backend('routes/patrimoine.py');

  test('has /reconciliation/fix endpoint', () => {
    expect(ROUTES).toMatch(/reconciliation\/fix/);
  });

  test('has /reconciliation/history endpoint', () => {
    expect(ROUTES).toMatch(/reconciliation\/history/);
  });

  test('has /reconciliation/evidence endpoint', () => {
    expect(ROUTES).toMatch(/reconciliation\/evidence/);
  });

  test('has /reconciliation/evidence/csv endpoint', () => {
    expect(ROUTES).toMatch(/reconciliation\/evidence\/csv/);
  });

  test('has portfolio evidence csv endpoint', () => {
    expect(ROUTES).toMatch(/portfolio\/reconciliation\/evidence\/csv/);
  });

  test('has ReconciliationFixRequest schema', () => {
    expect(ROUTES).toMatch(/ReconciliationFixRequest/);
  });
});

// ── G. ReconciliationFixLog model ────────────────────────────────────

describe('G. ReconciliationFixLog model', () => {
  test('reconciliation_fix_log.py exists', () => {
    expect(backendExists('models/reconciliation_fix_log.py')).toBe(true);
  });

  test('model has correct tablename', () => {
    const model = backend('models/reconciliation_fix_log.py');
    expect(model).toMatch(/reconciliation_fix_logs/);
  });

  test('model has check_id column', () => {
    const model = backend('models/reconciliation_fix_log.py');
    expect(model).toMatch(/check_id/);
  });

  test('model has status_before column', () => {
    const model = backend('models/reconciliation_fix_log.py');
    expect(model).toMatch(/status_before/);
  });

  test('model has applied_by column', () => {
    const model = backend('models/reconciliation_fix_log.py');
    expect(model).toMatch(/applied_by/);
  });

  test('__init__.py exports ReconciliationFixLog', () => {
    const init = backend('models/__init__.py');
    expect(init).toMatch(/ReconciliationFixLog/);
  });
});

// ── H. Migration V97 ────────────────────────────────────────────────

describe('H. Migration V97', () => {
  test('migrations.py has _create_reconciliation_fix_logs_table', () => {
    expect(backend('database/migrations.py')).toMatch(/_create_reconciliation_fix_logs_table/);
  });

  test('run_migrations calls V97 migration', () => {
    expect(backend('database/migrations.py')).toMatch(/reconciliation_fix_logs/);
  });
});
