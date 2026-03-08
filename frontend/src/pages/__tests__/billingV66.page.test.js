/**
 * billingV66.page.test.js — V66 Billing Audit + Shadow-Billing V1
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 6 groups, ~25 tests.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. api.js — 3 new V66 wrappers ── */
describe('A. api.js — V66 billing wrappers', () => {
  const code = src('src/services/api.js');

  it('exports importInvoicesPdf', () => {
    expect(code).toMatch(/export const importInvoicesPdf/);
  });

  it('importInvoicesPdf calls /billing/import-pdf', () => {
    expect(code).toMatch(/\/billing\/import-pdf/);
  });

  it('exports createActionFromBillingInsight', () => {
    expect(code).toMatch(/export const createActionFromBillingInsight/);
  });

  it('createActionFromBillingInsight uses billing-insight idempotency_key', () => {
    expect(code).toMatch(/billing-insight/);
    expect(code).toMatch(/idempotency_key/);
  });

  it('exports getBillingAnomaliesScoped', () => {
    expect(code).toMatch(/export const getBillingAnomaliesScoped/);
  });

  it('getBillingAnomaliesScoped calls /billing/anomalies-scoped', () => {
    expect(code).toMatch(/\/billing\/anomalies-scoped/);
  });
});

/* ── B. BillIntelPage.jsx — PDF upload + "Créer action" CTA ── */
describe('B. BillIntelPage.jsx — PDF upload + action CTA', () => {
  const code = src('src/pages/BillIntelPage.jsx');

  it('imports importInvoicesPdf', () => {
    expect(code).toMatch(/importInvoicesPdf/);
  });

  it('imports useActionDrawer (Étape 4: replaced CreateActionModal)', () => {
    expect(code).toMatch(/useActionDrawer/);
  });

  it('has PDF import handler (handlePdfImport)', () => {
    expect(code).toMatch(/handlePdfImport/);
  });

  it('has "Créer une action" CTA in insight rows', () => {
    expect(code).toMatch(/Cr.*er une action/);
  });

  it('has actionMap state for tracking created actions (V68: renamed from createdActions)', () => {
    expect(code).toMatch(/actionMap/);
  });

  it('has pdfSiteId state for site selection', () => {
    expect(code).toMatch(/pdfSiteId/);
  });

  it('accepts .pdf file type', () => {
    expect(code).toMatch(/accept.*\.pdf|\.pdf.*accept/);
  });
});

/* ── C. SiteBillingMini.jsx — new component ── */
describe('C. SiteBillingMini.jsx — new billing mini component', () => {
  const code = src('src/components/SiteBillingMini.jsx');

  it('has default export', () => {
    expect(code).toMatch(/export default function SiteBillingMini/);
  });

  it('imports getSiteBilling', () => {
    expect(code).toMatch(/getSiteBilling/);
  });

  it('accepts siteId prop', () => {
    expect(code).toMatch(/siteId/);
  });

  it('has CTA to /bill-intel', () => {
    expect(code).toMatch(/\/bill-intel/);
  });

  it('shows invoice and anomaly counts (KPIs)', () => {
    expect(code).toMatch(/invoices\.length|nb.*factures|Factures/i);
    expect(code).toMatch(/openInsights|Anomalie/i);
  });
});

/* ── D. Site360.jsx — Factures tab no longer a TabStub ── */
describe('D. Site360.jsx — Factures tab wired up', () => {
  const code = src('src/pages/Site360.jsx');

  it('imports SiteBillingMini', () => {
    expect(code).toMatch(/import SiteBillingMini/);
  });

  it('factures tab renders SiteBillingMini (not TabStub)', () => {
    // V96: factures tab is now a block with SiteContractsSummary + SiteBillingMini
    const factureBlock = code.match(/activeTab\s*===\s*'factures'[\s\S]*?SiteBillingMini/);
    expect(factureBlock).not.toBeNull();
    // Ensure it's not a TabStub
    const factureLine = code
      .split('\n')
      .find((l) => l.includes('factures') && l.includes('activeTab'));
    expect(factureLine).toBeDefined();
    expect(factureLine).not.toMatch(/TabStub/);
  });
});

/* ── E. AnomaliesPage.jsx — billing anomalies integration ── */
describe('E. AnomaliesPage.jsx — billing anomalies integration', () => {
  const code = src('src/pages/AnomaliesPage.jsx');

  it('imports getBillingAnomaliesScoped', () => {
    expect(code).toMatch(/getBillingAnomaliesScoped/);
  });

  it('has FACTURATION in FW_LABEL or FW_COLOR', () => {
    expect(code).toMatch(/FACTURATION/);
  });

  it('merges billing anomalies (regulatory_impact FACTURATION)', () => {
    expect(code).toMatch(/regulatory_impact.*FACTURATION|FACTURATION.*regulatory_impact/);
  });

  it('billing anomalies navigate to /bill-intel', () => {
    expect(code).toMatch(/\/bill-intel/);
    expect(code).toMatch(/_isBilling/);
  });
});

/* ── F. Routing / nav sanity ── */
describe('F. NavRegistry.js — /bill-intel still registered', () => {
  const code = src('src/layout/NavRegistry.js');

  it('/bill-intel appears in nav config', () => {
    expect(code).toMatch(/bill-intel/);
  });
});
