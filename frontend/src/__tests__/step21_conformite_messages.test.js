/**
 * Step 21 — C6 : Messages actionnables ConformitePage
 * Source-guard tests.
 * V101: Updated to reflect extraction of ComplianceSummaryBanner to components/conformite/.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const readSrc = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. ComplianceSummaryBanner ─────────────────────────────────────────────

describe('Step 21 — ComplianceSummaryBanner', () => {
  const pageSrc = readSrc('pages', 'ConformitePage.jsx');
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('ConformitePage has ComplianceSummaryBanner component', () => {
    expect(pageSrc).toContain('ComplianceSummaryBanner');
  });

  it('banner has 3 states (green, amber, red)', () => {
    expect(bannerSrc).toContain("'green'");
    expect(bannerSrc).toContain("'amber'");
    expect(bannerSrc).toContain("'red'");
  });

  it('banner has data-testid', () => {
    expect(bannerSrc).toContain('compliance-summary-banner');
  });

  it('banner has data-state attribute', () => {
    expect(bannerSrc).toContain('data-state={state}');
  });
});

// ── B. kpiMessaging integration ────────────────────────────────────────────

describe('Step 21 — kpiMessaging integration', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');
  const obligationsSrc = readSrc('pages', 'conformite-tabs', 'ObligationsTab.jsx');

  it('ComplianceSummaryBanner imports getKpiMessage', () => {
    expect(bannerSrc).toContain('getKpiMessage');
  });

  it('ObligationsTab imports getKpiMessage', () => {
    expect(obligationsSrc).toContain('getKpiMessage');
  });

  it('banner uses getKpiMessage with conformite', () => {
    expect(bannerSrc).toContain("getKpiMessage('conformite'");
  });

  it('banner uses getKpiMessage with risque', () => {
    expect(bannerSrc).toContain("getKpiMessage('risque'");
  });

  it('ObligationsTab has kpi-message-conformite-tab testid', () => {
    expect(obligationsSrc).toContain('kpi-message-conformite-tab');
  });

  it('ObligationsTab has kpi-message-risque-tab testid', () => {
    expect(obligationsSrc).toContain('kpi-message-risque-tab');
  });
});

// ── C. Expert vs Simple mode ───────────────────────────────────────────────

describe('Step 21 — Expert vs Simple mode', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');
  const oblSrc = readSrc('pages', 'conformite-tabs', 'ObligationsTab.jsx');

  it('banner switches between expert and simple messages', () => {
    expect(bannerSrc).toContain('isExpert ? conformiteMsg.expert : conformiteMsg.simple');
  });

  it('ObligationsTab switches between expert and simple', () => {
    expect(oblSrc).toContain('isExpert ? msg.expert : msg.simple');
  });
});

// ── D. CTA buttons ────────────────────────────────────────────────────────

describe('Step 21 — CTA buttons', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('has "Voir le plan d\'action" CTA', () => {
    expect(bannerSrc).toContain('Voir le plan d');
    expect(bannerSrc).toContain('action');
  });

  it('has "Préparer les échéances" CTA', () => {
    // Unicode-escaped in source
    expect(bannerSrc).toMatch(/ch.ances/);
  });

  it('CTA navigates to /actions for red state', () => {
    expect(bannerSrc).toContain("navigate('/actions')");
  });

  it('CTA navigates to execution tab for amber state', () => {
    expect(bannerSrc).toContain("navigate('/conformite?tab=execution')");
  });
});

// ── E. Next deadline ──────────────────────────────────────────────────────

describe('Step 21 — Next deadline display', () => {
  const bannerSrc = readSrc('components', 'conformite', 'ComplianceSummaryBanner.jsx');

  it('banner displays next_deadline from timeline', () => {
    expect(bannerSrc).toContain('next_deadline');
  });

  it('banner has next-deadline testid', () => {
    expect(bannerSrc).toContain('next-deadline');
  });

  it('banner shows days_remaining', () => {
    expect(bannerSrc).toContain('days_remaining');
  });
});

// ── F. kpiMessaging.js not modified ───────────────────────────────────────

describe('Step 21 — kpiMessaging unchanged', () => {
  const src = readSrc('services', 'kpiMessaging.js');

  it('kpiMessaging still has conformite handler', () => {
    expect(src).toContain('conformite:');
  });

  it('kpiMessaging still has risque handler', () => {
    expect(src).toContain('risque:');
  });

  it('kpiMessaging exports getKpiMessage', () => {
    expect(src).toContain('export function getKpiMessage');
  });
});
