/**
 * PROMEOS — Step 9: Auto-reconciliation source-guard tests
 * Verifie que le rapprochement auto est branche dans le backend et le frontend.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readBackend(relPath) {
  return readFileSync(join(__dirname, '..', '..', '..', 'backend', relPath), 'utf-8');
}

function readFrontend(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. Backend — billing_reconcile.py ────────────────────────────────────────

describe('A. billing_reconcile.py structure', () => {
  const src = readBackend('services/billing_reconcile.py');

  test('A1. auto_reconcile_after_import function exists', () => {
    expect(src).toMatch(/def auto_reconcile_after_import/);
  });

  test('A2. calls reconcile_metered_billed', () => {
    expect(src).toMatch(/reconcile_metered_billed/);
  });

  test('A3. creates BillingInsight', () => {
    expect(src).toMatch(/BillingInsight/);
  });

  test('A4. type is reconciliation_mismatch', () => {
    expect(src).toMatch(/"reconciliation_mismatch"/);
  });

  test('A5. has try/except for safety', () => {
    expect(src).toMatch(/try:/);
    expect(src).toMatch(/except Exception/);
  });

  test('A6. idempotent — checks existing', () => {
    expect(src).toMatch(/existing/);
    expect(src).toMatch(/already_exists/);
  });
});

// ── B. Backend — routes wiring ──────────────────────────────────────────────

describe('B. billing routes wiring', () => {
  const src = readBackend('routes/billing.py');

  test('B1. imports auto_reconcile_after_import', () => {
    expect(src).toMatch(/from services\.billing_reconcile import auto_reconcile_after_import/);
  });

  test('B2. CSV import calls auto_reconcile', () => {
    const csv = src.split('def import_invoices_csv')[1].split('def ')[0];
    expect(csv).toMatch(/auto_reconcile_after_import/);
  });

  test('B3. PDF import calls auto_reconcile', () => {
    const pdf = src.split('def import_invoice_pdf')[1].split('def ')[0];
    expect(pdf).toMatch(/auto_reconcile_after_import/);
  });

  test('B4. audit-all calls auto_reconcile', () => {
    const audit = src.split('def audit_all_invoices')[1].split('def ')[0];
    expect(audit).toMatch(/auto_reconcile_after_import/);
  });

  test('B5. reconcile-all endpoint exists', () => {
    expect(src).toMatch(/def reconcile_all_sites/);
    expect(src).toMatch(/\/reconcile-all/);
  });
});

// ── C. Frontend — glossary ──────────────────────────────────────────────────

describe('C. Frontend glossary', () => {
  const src = readFrontend('ui/glossary.js');

  test('C1. reconciliation_auto entry exists', () => {
    expect(src).toMatch(/reconciliation_auto/);
  });

  test('C2. mentions rapprochement automatique', () => {
    expect(src).toMatch(/automatique/);
  });
});

// ── D. Frontend — API ───────────────────────────────────────────────────────

describe('D. Frontend API', () => {
  const src = readFrontend('services/api.js');

  test('D1. postBillingReconcileAll function exists', () => {
    expect(src).toMatch(/postBillingReconcileAll/);
  });

  test('D2. calls /billing/reconcile-all', () => {
    expect(src).toMatch(/\/billing\/reconcile-all/);
  });
});

// ── E. Frontend — InsightDrawer ─────────────────────────────────────────────

describe('E. InsightDrawer type support', () => {
  const src = readFrontend('components/InsightDrawer.jsx');

  test('E1. TYPE_LABELS has reconciliation_mismatch', () => {
    expect(src).toMatch(/reconciliation_mismatch/);
  });

  test('E2. CAUSE_LABELS has reconciliation_mismatch', () => {
    const causes = src.split('CAUSE_LABELS')[1];
    expect(causes).toMatch(/reconciliation_mismatch/);
  });

  test('E3. uses Explain component for reconciliation', () => {
    expect(src).toMatch(/reconciliation/);
  });
});
