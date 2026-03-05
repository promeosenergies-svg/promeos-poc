/**
 * billingTrustGate.page.test.js — Phase 1 ELEC Trust Gate
 * Source-guard tests (readFileSync + regex) — no DOM, no mocks needed.
 * 6 groups.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');

function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

/* ── A. Tax labels propres ── */
describe('A. Tax labels — no CSPE/TICGN on ELEC', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('does NOT have hardcoded "CSPE/TICGN" literal', () => {
    expect(drawer).not.toMatch(/CSPE\/TICGN/);
  });

  it('has energy_type check for dynamic tax label', () => {
    expect(drawer).toMatch(/energy_type/);
    expect(drawer).toMatch(/Accise.*électricité/s);
    expect(drawer).toMatch(/Accise.*gaz.*TICGN/s);
  });

  it('taxes_mismatch label says "accise" not "CSPE"', () => {
    expect(drawer).toMatch(/taxes_mismatch.*accise|accise.*taxes_mismatch/s);
    expect(drawer).not.toMatch(/taxes_mismatch.*CSPE/s);
  });

  it('CAUSE_LABELS taxes_mismatch uses "accise"', () => {
    expect(drawer).toMatch(/taxes.*accise/s);
  });
});

/* ── B. TVA handling ── */
describe('B. TVA — never "— €" when TTC is calculated', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('has "TVA non disponible" fallback', () => {
    expect(drawer).toMatch(/TVA.*non disponible/s);
  });

  it('checks actual_ttc before showing TVA fallback', () => {
    expect(drawer).toMatch(/actual_ttc/);
  });
});

/* ── C. Delta TTC cohérence ── */
describe('C. Delta TTC — single reference', () => {
  const drawer = src('src/components/InsightDrawer.jsx');

  it('uses delta_ttc in Total TTC row', () => {
    expect(drawer).toMatch(/delta_ttc/);
  });

  it('displays estimated_loss_eur', () => {
    expect(drawer).toMatch(/estimated_loss_eur/);
  });
});

/* ── D. Status exclusif ── */
describe('D. Status exclusif — 4 valid statuses with guard', () => {
  const page = src('src/pages/BillIntelPage.jsx');

  it('has all 4 statuses defined', () => {
    expect(page).toMatch(/open/);
    expect(page).toMatch(/ack/);
    expect(page).toMatch(/resolved/);
    expect(page).toMatch(/false_positive/);
  });

  it('has VALID_STATUSES guard', () => {
    expect(page).toMatch(/VALID_STATUSES/);
  });

  it('uses includes() for status validation', () => {
    expect(page).toMatch(/VALID_STATUSES\.includes/);
  });
});

/* ── E. KPI pertes filtrées ── */
describe('E. KPI — pertes estimées only active', () => {
  const page = src('src/pages/BillIntelPage.jsx');

  it('imports isActiveInsight', () => {
    expect(page).toMatch(/isActiveInsight/);
  });

  it('computes activeLoss from filtered insights', () => {
    expect(page).toMatch(/activeLoss/);
  });

  it('uses activeLoss in KPI (not summary.total_estimated_loss_eur)', () => {
    expect(page).not.toMatch(/summary\.total_estimated_loss_eur/);
  });

  it('isActiveInsight is exported from billingHealthModel', () => {
    const model = src('src/models/billingHealthModel.js');
    expect(model).toMatch(/export function isActiveInsight/);
  });
});

/* ── F. TYPE_LABELS 14 types ── */
describe('F. TYPE_LABELS — all 14 types present', () => {
  const page = src('src/pages/BillIntelPage.jsx');

  it('has ttc_coherence', () => {
    expect(page).toMatch(/ttc_coherence/);
  });

  it('has contract_expiry', () => {
    expect(page).toMatch(/contract_expiry/);
  });

  it('has reseau_mismatch', () => {
    expect(page).toMatch(/reseau_mismatch/);
  });

  it('has taxes_mismatch', () => {
    expect(page).toMatch(/taxes_mismatch/);
  });

  it('has all original 10 types', () => {
    expect(page).toMatch(/shadow_gap/);
    expect(page).toMatch(/unit_price_high/);
    expect(page).toMatch(/duplicate_invoice/);
    expect(page).toMatch(/missing_period/);
    expect(page).toMatch(/period_too_long/);
    expect(page).toMatch(/negative_kwh/);
    expect(page).toMatch(/zero_amount/);
    expect(page).toMatch(/lines_sum_mismatch/);
    expect(page).toMatch(/consumption_spike/);
    expect(page).toMatch(/price_drift/);
  });
});
