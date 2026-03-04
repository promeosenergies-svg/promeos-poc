/**
 * v96PatrimoineUnique.test.js — V96 "Patrimoine Unique Monde" source guards
 *
 * Verifies:
 *   A. PaymentRulesPage exists with correct content
 *   B. Site360 has payment-info, reconciliation tab, enriched contracts
 *   C. Patrimoine has reconciliation badge
 *   D. api.js has all V96 functions
 *   E. NavRegistry + App.jsx wired
 *   F. Backend models + service exist
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');
const backend = (rel) =>
  readFileSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel), 'utf8');
const backendExists = (rel) =>
  existsSync(path.resolve(__dirname, '..', '..', '..', '..', 'backend', rel));

const PAYMENT_PAGE = src('pages/PaymentRulesPage.jsx');
const SITE360 = src('pages/Site360.jsx');
const PATRIMOINE = src('pages/Patrimoine.jsx');
const API_JS = src('services/api.js');
const NAV_REG = src('layout/NavRegistry.js');
const APP_JSX = src('App.jsx');
const CONTRACTS_CMP = src('components/SiteContractsSummary.jsx');

// ── A. PaymentRulesPage ────────────────────────────────────────────────

describe('A. PaymentRulesPage', () => {
  test('exists and contains "Paiement"', () => {
    expect(PAYMENT_PAGE).toMatch(/Paiement/);
  });

  test('contains "Refacturation"', () => {
    expect(PAYMENT_PAGE).toMatch(/Refacturation/);
  });

  test('imports getPaymentRules', () => {
    expect(PAYMENT_PAGE).toMatch(/getPaymentRules/);
  });
});

// ── B. Site360 enrichments ──────────────────────────────────────────────

describe('B. Site360 V96', () => {
  test('has PaymentInfoCard or payment-info', () => {
    expect(SITE360).toMatch(/PaymentInfoCard|payment-info/);
  });

  test('TABS includes reconciliation', () => {
    expect(SITE360).toMatch(/reconciliation/);
  });

  test('imports getReconciliation', () => {
    expect(SITE360).toMatch(/getReconciliation/);
  });

  test('has TabReconciliation component', () => {
    expect(SITE360).toMatch(/TabReconciliation/);
  });

  test('imports SiteContractsSummary', () => {
    expect(SITE360).toMatch(/SiteContractsSummary/);
  });

  test('has scenario achat CTA', () => {
    expect(SITE360).toMatch(/scénario.*achat|scenario.*achat|achat-assistant/i);
  });
});

// ── C. Patrimoine reconciliation badge ──────────────────────────────────

describe('C. Patrimoine badge', () => {
  test('imports getPortfolioReconciliation', () => {
    expect(PATRIMOINE).toMatch(/getPortfolioReconciliation/);
  });

  test('has reconMap state', () => {
    expect(PATRIMOINE).toMatch(/reconMap/);
  });

  test('has Réconc column header', () => {
    expect(PATRIMOINE).toMatch(/Réconc/);
  });
});

// ── D. api.js V96 functions ─────────────────────────────────────────────

describe('D. api.js V96', () => {
  test('getPaymentRules', () => {
    expect(API_JS).toMatch(/getPaymentRules/);
  });
  test('getSitePaymentInfo', () => {
    expect(API_JS).toMatch(/getSitePaymentInfo/);
  });
  test('getReconciliation', () => {
    expect(API_JS).toMatch(/getReconciliation/);
  });
  test('getPortfolioReconciliation', () => {
    expect(API_JS).toMatch(/getPortfolioReconciliation/);
  });
  test('getPatrimoineContracts', () => {
    expect(API_JS).toMatch(/getPatrimoineContracts/);
  });
  test('applyPaymentRulesBulk', () => {
    expect(API_JS).toMatch(/applyPaymentRulesBulk/);
  });
});

// ── E. NavRegistry + App.jsx wiring ─────────────────────────────────────

describe('E. NavRegistry + App wiring', () => {
  test('NavRegistry has /payment-rules', () => {
    expect(NAV_REG).toMatch(/\/payment-rules/);
  });

  test('App.jsx has PaymentRulesPage', () => {
    expect(APP_JSX).toMatch(/PaymentRulesPage/);
  });
});

// ── F. Backend models + service ─────────────────────────────────────────

describe('F. Backend V96', () => {
  test('enums.py has PaymentRuleLevel', () => {
    expect(backend('models/enums.py')).toMatch(/PaymentRuleLevel/);
  });

  test('enums.py has ContractIndexation', () => {
    expect(backend('models/enums.py')).toMatch(/ContractIndexation/);
  });

  test('enums.py has ContractStatus', () => {
    expect(backend('models/enums.py')).toMatch(/ContractStatus/);
  });

  test('enums.py has ReconciliationStatus', () => {
    expect(backend('models/enums.py')).toMatch(/ReconciliationStatus/);
  });

  test('billing_models.py has offer_indexation', () => {
    expect(backend('models/billing_models.py')).toMatch(/offer_indexation/);
  });

  test('billing_models.py has contract_status', () => {
    expect(backend('models/billing_models.py')).toMatch(/contract_status/);
  });

  test('payment_rule.py exists', () => {
    expect(backendExists('models/payment_rule.py')).toBe(true);
  });

  test('reconciliation_service.py exists and has reconcile_site', () => {
    const svc = backend('services/reconciliation_service.py');
    expect(svc).toMatch(/reconcile_site/);
  });

  test('migrations.py has payment_rules', () => {
    expect(backend('database/migrations.py')).toMatch(/payment_rules/);
  });

  test('migrations.py has contract_v96', () => {
    expect(backend('database/migrations.py')).toMatch(/contract_v96/);
  });
});

// ── G. SiteContractsSummary component ───────────────────────────────────

describe('G. SiteContractsSummary', () => {
  test('exists and imports getPatrimoineContracts', () => {
    expect(CONTRACTS_CMP).toMatch(/getPatrimoineContracts/);
  });

  test('shows indexation badge', () => {
    expect(CONTRACTS_CMP).toMatch(/offer_indexation/);
  });

  test('shows renewal alert', () => {
    expect(CONTRACTS_CMP).toMatch(/renewal_alert_days/);
  });
});
