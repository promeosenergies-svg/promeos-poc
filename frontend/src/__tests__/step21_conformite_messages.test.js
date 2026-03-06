/**
 * Step 21 — C6 : Messages actionnables ConformitePage
 * Source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';

const readSrc = (...parts) =>
  fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. ComplianceSummaryBanner ─────────────────────────────────────────────

describe('Step 21 — ComplianceSummaryBanner', () => {
  const src = readSrc('pages', 'ConformitePage.jsx');

  it('ConformitePage has ComplianceSummaryBanner component', () => {
    expect(src).toContain('ComplianceSummaryBanner');
  });

  it('banner has 3 states (green, amber, red)', () => {
    expect(src).toContain("'green'");
    expect(src).toContain("'amber'");
    expect(src).toContain("'red'");
  });

  it('banner has data-testid', () => {
    expect(src).toContain('compliance-summary-banner');
  });

  it('banner has data-state attribute', () => {
    expect(src).toContain('data-state={state}');
  });
});

// ── B. kpiMessaging integration ────────────────────────────────────────────

describe('Step 21 — kpiMessaging integration', () => {
  const conformiteSrc = readSrc('pages', 'ConformitePage.jsx');
  const obligationsSrc = readSrc('pages', 'conformite-tabs', 'ObligationsTab.jsx');

  it('ConformitePage imports getKpiMessage', () => {
    expect(conformiteSrc).toContain('getKpiMessage');
  });

  it('ObligationsTab imports getKpiMessage', () => {
    expect(obligationsSrc).toContain('getKpiMessage');
  });

  it('banner uses getKpiMessage with conformite', () => {
    expect(conformiteSrc).toContain("getKpiMessage('conformite'");
  });

  it('banner uses getKpiMessage with risque', () => {
    expect(conformiteSrc).toContain("getKpiMessage('risque'");
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
  const src = readSrc('pages', 'ConformitePage.jsx');
  const oblSrc = readSrc('pages', 'conformite-tabs', 'ObligationsTab.jsx');

  it('banner switches between expert and simple messages', () => {
    expect(src).toContain('isExpert ? conformiteMsg.expert : conformiteMsg.simple');
  });

  it('ObligationsTab switches between expert and simple', () => {
    expect(oblSrc).toContain('isExpert ? msg.expert : msg.simple');
  });
});

// ── D. CTA buttons ────────────────────────────────────────────────────────

describe('Step 21 — CTA buttons', () => {
  const src = readSrc('pages', 'ConformitePage.jsx');

  it('has "Voir le plan d\'action" CTA', () => {
    expect(src).toContain("Voir le plan d");
    expect(src).toContain("action");
  });

  it('has "Préparer les échéances" CTA', () => {
    expect(src).toContain('Préparer les échéances');
  });

  it('CTA navigates to /actions for red state', () => {
    expect(src).toContain("navigate('/actions')");
  });

  it('CTA navigates to execution tab for amber state', () => {
    expect(src).toContain("navigate('/conformite?tab=execution')");
  });
});

// ── E. Next deadline ──────────────────────────────────────────────────────

describe('Step 21 — Next deadline display', () => {
  const src = readSrc('pages', 'ConformitePage.jsx');

  it('banner displays next_deadline from timeline', () => {
    expect(src).toContain('next_deadline');
  });

  it('banner has next-deadline testid', () => {
    expect(src).toContain('next-deadline');
  });

  it('banner shows days_remaining', () => {
    expect(src).toContain('days_remaining');
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
