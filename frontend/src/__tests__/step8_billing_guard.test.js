/**
 * PROMEOS — Step 8: Billing seed 5 sites source-guard tests
 * Verifie que billing_seed.py couvre 5 sites et 3 fournisseurs.
 */

import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readBackend(relPath) {
  return readFileSync(join(__dirname, '..', '..', '..', 'backend', relPath), 'utf-8');
}

// ── A. Billing seed couvre 5 sites ───────────────────────────────────────────

describe('A. Billing seed covers 5 sites', () => {
  const src = readBackend('services/billing_seed.py');

  test('A1. has site_a through site_e', () => {
    expect(src).toMatch(/site_a/);
    expect(src).toMatch(/site_b/);
    expect(src).toMatch(/site_c/);
    expect(src).toMatch(/site_d/);
    expect(src).toMatch(/site_e/);
  });

  test('A2. queries at least 5 sites', () => {
    expect(src).toMatch(/\.limit\(5\)/);
  });

  test('A3. has invoice generators for 3 new sites', () => {
    expect(src).toMatch(/_add_marseille_invoice/);
    expect(src).toMatch(/_add_nice_elec_invoice/);
    expect(src).toMatch(/_add_nice_gaz_invoice/);
    expect(src).toMatch(/_add_toulouse_invoice/);
  });

  test('A4. generates invoices for all 5 sites in seed_billing_demo', () => {
    // Verify all generators are called in seed_billing_demo
    const seedFn = src.split('def seed_billing_demo')[1];
    expect(seedFn).toMatch(/_add_elec_invoice/);
    expect(seedFn).toMatch(/_add_gaz_invoice/);
    expect(seedFn).toMatch(/_add_marseille_invoice/);
    expect(seedFn).toMatch(/_add_nice_elec_invoice/);
    expect(seedFn).toMatch(/_add_nice_gaz_invoice/);
    expect(seedFn).toMatch(/_add_toulouse_invoice/);
  });
});

// ── B. 3 fournisseurs distincts ──────────────────────────────────────────────

describe('B. 3 distinct suppliers', () => {
  const src = readBackend('services/billing_seed.py');

  test('B1. EDF supplier present', () => {
    expect(src).toMatch(/"EDF"/);
  });

  test('B2. ENGIE supplier present', () => {
    expect(src).toMatch(/"ENGIE"/);
  });

  test('B3. TotalEnergies supplier present', () => {
    expect(src).toMatch(/"TotalEnergies"/);
  });
});

// ── C. Anomalies variees ─────────────────────────────────────────────────────

describe('C. Varied anomalies', () => {
  const src = readBackend('services/billing_seed.py');

  test('C1. Marseille R1 surfacturation 35%', () => {
    expect(src).toMatch(/ANOMALY_MARSEILLE_R1/);
    expect(src).toMatch(/1\.35/);
  });

  test('C2. Marseille R3 spike x2.7', () => {
    expect(src).toMatch(/ANOMALY_MARSEILLE_R3/);
    expect(src).toMatch(/2\.7/);
  });

  test('C3. Nice R11 TTC mismatch', () => {
    expect(src).toMatch(/ANOMALY_NICE_R11/);
    expect(src).toMatch(/1\.035/);
  });

  test('C4. Toulouse R1 implied price 0.24', () => {
    expect(src).toMatch(/ANOMALY_TOULOUSE_R1/);
    expect(src).toMatch(/0\.24/);
  });

  test('C5. Nice contract expires in 30 days (R12)', () => {
    expect(src).toMatch(/days=30/);
  });
});

// ── D. Idempotent et source tag ──────────────────────────────────────────────

describe('D. Idempotent seed', () => {
  const src = readBackend('services/billing_seed.py');

  test('D1. uses seed_36m source tag', () => {
    expect(src).toMatch(/SOURCE_TAG\s*=\s*"seed_36m"/);
  });

  test('D2. checks for existing invoices before seeding', () => {
    expect(src).toMatch(/existing/);
    expect(src).toMatch(/skipped/);
  });
});

// ── E. Unique invoice number patterns ────────────────────────────────────────

describe('E. Unique invoice numbers', () => {
  const src = readBackend('services/billing_seed.py');

  test('E1. distinct invoice_number prefixes per site', () => {
    expect(src).toMatch(/EDF-TLS-/);
    expect(src).toMatch(/ENGIE-MAR-/);
    expect(src).toMatch(/TOTAL-NIC-/);
    expect(src).toMatch(/ENGIE-NIC-G-/);
  });
});
