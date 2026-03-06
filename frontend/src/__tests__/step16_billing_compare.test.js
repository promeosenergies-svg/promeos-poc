/**
 * Step 16 — B7 : Comparaison factures N vs N-1
 * Source-guard tests + component structure checks.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

describe('Step 16 — BillingCompareChart component', () => {
  it('BillingCompareChart exists', () => {
    const src = fs.readFileSync('src/components/BillingCompareChart.jsx', 'utf8');
    expect(src).toContain('BillingCompareChart');
  });

  it('uses Recharts BarChart', () => {
    const src = fs.readFileSync('src/components/BillingCompareChart.jsx', 'utf8');
    expect(src).toContain('BarChart');
  });

  it('uses ResponsiveContainer', () => {
    const src = fs.readFileSync('src/components/BillingCompareChart.jsx', 'utf8');
    expect(src).toContain('ResponsiveContainer');
  });

  it('has data-testid billing-compare-chart', () => {
    const src = fs.readFileSync('src/components/BillingCompareChart.jsx', 'utf8');
    expect(src).toContain('billing-compare-chart');
  });

  it('renders current and previous bars', () => {
    const src = fs.readFileSync('src/components/BillingCompareChart.jsx', 'utf8');
    expect(src).toContain('dataKey="current"');
    expect(src).toContain('dataKey="previous"');
  });
});

describe('Step 16 — BillingPage integration', () => {
  it('BillingPage imports BillingCompareChart', () => {
    const src = fs.readFileSync('src/pages/BillingPage.jsx', 'utf8');
    expect(src).toContain('BillingCompareChart');
  });

  it('BillingPage imports getBillingCompareMonthly', () => {
    const src = fs.readFileSync('src/pages/BillingPage.jsx', 'utf8');
    expect(src).toContain('getBillingCompareMonthly');
  });

  it('BillingPage has compareData state', () => {
    const src = fs.readFileSync('src/pages/BillingPage.jsx', 'utf8');
    expect(src).toContain('compareData');
  });
});

describe('Step 16 — API function', () => {
  it('api.js exports getBillingCompareMonthly', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('getBillingCompareMonthly');
  });

  it('api.js calls /billing/compare-monthly', () => {
    const src = fs.readFileSync('src/services/api.js', 'utf8');
    expect(src).toContain('/billing/compare-monthly');
  });
});
