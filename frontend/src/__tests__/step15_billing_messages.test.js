/**
 * Step 15 — B6 : Messages contextuels billing
 * Tests unitaires pour les handlers kpiMessaging billing + source guards.
 */
import { describe, it, expect } from 'vitest';
import { getKpiMessage } from '../services/kpiMessaging';
import fs from 'fs';

// ── billing_total_cost ──────────────────────────────────────────────────

describe('Step 15 — billing_total_cost handler', () => {
  it('null → neutral', () => {
    expect(getKpiMessage('billing_total_cost', null).severity).toBe('neutral');
  });

  it('50000 without prev → neutral', () => {
    expect(getKpiMessage('billing_total_cost', 50000).severity).toBe('neutral');
  });

  it('hausse 15% → crit', () => {
    expect(getKpiMessage('billing_total_cost', 115000, { previousYearCost: 100000 }).severity).toBe(
      'crit'
    );
  });

  it('stable → ok', () => {
    expect(getKpiMessage('billing_total_cost', 101000, { previousYearCost: 100000 }).severity).toBe(
      'ok'
    );
  });

  it('hausse 5% → warn', () => {
    expect(getKpiMessage('billing_total_cost', 105000, { previousYearCost: 100000 }).severity).toBe(
      'warn'
    );
  });

  it('baisse → ok', () => {
    expect(getKpiMessage('billing_total_cost', 90000, { previousYearCost: 100000 }).severity).toBe(
      'ok'
    );
  });

  it('formats k€ for large values', () => {
    const msg = getKpiMessage('billing_total_cost', 50000);
    expect(msg.simple).toContain('50 k€');
  });
});

// ── billing_anomalies_count ─────────────────────────────────────────────

describe('Step 15 — billing_anomalies_count handler', () => {
  it('0 → ok', () => {
    expect(getKpiMessage('billing_anomalies_count', 0).severity).toBe('ok');
  });

  it('1 → warn', () => {
    expect(getKpiMessage('billing_anomalies_count', 1, { totalLossEur: 500 }).severity).toBe(
      'warn'
    );
  });

  it('5 → crit', () => {
    expect(getKpiMessage('billing_anomalies_count', 5, { totalLossEur: 8000 }).severity).toBe(
      'crit'
    );
  });

  it('has action when anomalies exist', () => {
    expect(
      getKpiMessage('billing_anomalies_count', 3, { totalLossEur: 4000 }).action
    ).toBeDefined();
  });

  it('no action when 0', () => {
    expect(getKpiMessage('billing_anomalies_count', 0).action).toBeUndefined();
  });

  it('formats loss in k€', () => {
    const msg = getKpiMessage('billing_anomalies_count', 2, { totalLossEur: 5000 });
    expect(msg.simple).toContain('5.0 k€');
  });
});

// ── billing_reconciliation ──────────────────────────────────────────────

describe('Step 15 — billing_reconciliation handler', () => {
  it('0 → ok', () => {
    expect(getKpiMessage('billing_reconciliation', 0).severity).toBe('ok');
  });

  it('2 → warn', () => {
    expect(getKpiMessage('billing_reconciliation', 2).severity).toBe('warn');
  });

  it('4 → crit', () => {
    expect(getKpiMessage('billing_reconciliation', 4).severity).toBe('crit');
  });

  it('has action when sites in error', () => {
    expect(getKpiMessage('billing_reconciliation', 2).action).toBeDefined();
  });
});

// ── Source guards ────────────────────────────────────────────────────────

describe('Step 15 — BillIntelPage integration', () => {
  it('BillIntelPage uses getKpiMessage', () => {
    const src = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf8');
    expect(src).toContain('getKpiMessage');
  });

  it('BillIntelPage uses billing_total_cost', () => {
    const src = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf8');
    expect(src).toContain('billing_total_cost');
  });

  it('BillIntelPage uses billing_anomalies_count', () => {
    const src = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf8');
    expect(src).toContain('billing_anomalies_count');
  });

  it('BillIntelPage has summary phrase', () => {
    const src = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf8');
    expect(src).toContain('billing-summary-phrase');
  });

  it('BillIntelPage summary has cohérentes message', () => {
    const src = fs.readFileSync('src/pages/BillIntelPage.jsx', 'utf8');
    expect(src).toContain('cohérentes');
  });
});

describe('Step 15 — BillingPage integration', () => {
  it('BillingPage uses getKpiMessage', () => {
    const src = fs.readFileSync('src/pages/BillingPage.jsx', 'utf8');
    expect(src).toContain('getKpiMessage');
  });

  it('BillingPage uses billing_coverage', () => {
    const src = fs.readFileSync('src/pages/BillingPage.jsx', 'utf8');
    expect(src).toContain('billing_coverage');
  });
});
