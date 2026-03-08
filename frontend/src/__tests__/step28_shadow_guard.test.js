/**
 * Step 28 — Shadow Breakdown par composante (source guards)
 */
import { describe, test, expect } from 'vitest';
import fs from 'fs';

const readFront = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. ShadowBreakdownCard exists ───────────────────────────────────────────
describe('A. ShadowBreakdownCard', () => {
  test('file exists', () => {
    expect(fs.existsSync('src/components/billing/ShadowBreakdownCard.jsx')).toBe(true);
  });

  test('renders component breakdown', () => {
    const src = readFront('components', 'billing', 'ShadowBreakdownCard.jsx');
    // Component renders breakdown.components dynamically
    expect(src).toContain('components');
    expect(src).toContain('expected_eur');
    expect(src).toContain('invoice_eur');
    expect(src).toContain('gap_eur');
  });

  test('has TURPE and fourniture in comments or labels', () => {
    const src = readFront('components', 'billing', 'ShadowBreakdownCard.jsx');
    // File comment mentions all component types
    expect(src).toContain('TURPE');
    expect(src).toContain('fourniture');
  });

  test('has status colors (ok, warn, alert)', () => {
    const src = readFront('components', 'billing', 'ShadowBreakdownCard.jsx');
    expect(src).toContain('ok:');
    expect(src).toContain('warn:');
    expect(src).toContain('alert:');
  });

  test('has confidence badge', () => {
    const src = readFront('components', 'billing', 'ShadowBreakdownCard.jsx');
    expect(src).toContain('confidence');
    expect(src).toContain('Confiance');
  });
});

// ── B. InsightDrawer integration ────────────────────────────────────────────
describe('B. InsightDrawer integration', () => {
  test('imports ShadowBreakdownCard', () => {
    const src = readFront('components', 'InsightDrawer.jsx');
    expect(src).toContain('ShadowBreakdownCard');
  });

  test('imports getInvoiceShadowBreakdown', () => {
    const src = readFront('components', 'InsightDrawer.jsx');
    expect(src).toContain('getInvoiceShadowBreakdown');
  });

  test('renders breakdown component', () => {
    const src = readFront('components', 'InsightDrawer.jsx');
    expect(src).toContain('<ShadowBreakdownCard');
  });
});

// ── C. api.js has the endpoint ──────────────────────────────────────────────
describe('C. API function', () => {
  test('getInvoiceShadowBreakdown exists in api.js', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('getInvoiceShadowBreakdown');
  });

  test('calls shadow-breakdown endpoint', () => {
    const src = readFront('services', 'api.js');
    expect(src).toContain('shadow-breakdown');
  });
});

// ── D. Glossary ─────────────────────────────────────────────────────────────
describe('D. Glossary entry', () => {
  test('shadow_breakdown in glossary', () => {
    const src = readFront('ui', 'glossary.js');
    expect(src).toContain('shadow_breakdown');
  });

  test('glossary has decomposition label', () => {
    const src = readFront('ui', 'glossary.js');
    expect(src).toContain('Décomposition shadow');
  });
});
