/**
 * PROMEOS — Compliance Pipeline V68 — Source-guard + structure tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. Pipeline page: data-section markers
 * B. Site compliance page: 3 tabs + CTA
 * C. Route registry: helpers exist
 * D. App.jsx: routes registered
 * E. API: endpoint functions exported
 * F. "Créer action" CTA wiring (no blank page)
 */
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. Pipeline page: data-section markers
// ============================================================
describe('A · CompliancePipelinePage data-section markers', () => {
  const code = readSrc('pages', 'CompliancePipelinePage.jsx');

  it('has data-section="compliance-pipeline"', () => {
    expect(code).toContain('data-section="compliance-pipeline"');
  });

  it('has data-section="pipeline-kpis"', () => {
    expect(code).toContain('data-section="pipeline-kpis"');
  });

  it('has data-section="pipeline-blockers"', () => {
    expect(code).toContain('data-section="pipeline-blockers"');
  });

  it('has data-section="pipeline-deadlines"', () => {
    expect(code).toContain('data-section="pipeline-deadlines"');
  });

  it('has data-section="pipeline-untrusted"', () => {
    expect(code).toContain('data-section="pipeline-untrusted"');
  });

  it('has data-section="pipeline-sites-table"', () => {
    expect(code).toContain('data-section="pipeline-sites-table"');
  });

  it('renders 3 KPI cards (blocked, warning, ok)', () => {
    expect(code).toContain('sites_blocked');
    expect(code).toContain('sites_warning');
    expect(code).toContain('sites_ok');
  });

  it('shows deadlines in 30/90/180 buckets', () => {
    expect(code).toContain('d30');
    expect(code).toContain('d90');
    expect(code).toContain('d180');
  });
});

// ============================================================
// B. Site compliance page: 3 tabs + CTA
// ============================================================
describe('B · SiteCompliancePage tabs and CTAs', () => {
  const code = readSrc('pages', 'SiteCompliancePage.jsx');

  it('has 3 tabs: obligations, preuves, plan', () => {
    expect(code).toContain("'obligations'");
    expect(code).toContain("'preuves'");
    expect(code).toContain("'plan'");
  });

  it('has data-section="tab-obligations"', () => {
    expect(code).toContain('data-section="tab-obligations"');
  });

  it('has data-section="tab-preuves"', () => {
    expect(code).toContain('data-section="tab-preuves"');
  });

  it('has data-section="tab-plan"', () => {
    expect(code).toContain('data-section="tab-plan"');
  });

  it('has data-section="site-compliance"', () => {
    expect(code).toContain('data-section="site-compliance"');
  });

  it('has "Créer action" button with data-testid', () => {
    expect(code).toContain('data-testid="cta-creer-action-plan"');
  });

  it('has empty state "Créer action" CTA', () => {
    expect(code).toContain('data-testid="cta-creer-action-empty"');
  });

  it('uses useActionDrawer with compliance context', () => {
    expect(code).toContain('useActionDrawer');
    expect(code).toContain("sourceType: 'compliance'");
  });

  it('shows Data Readiness Gate section', () => {
    expect(code).toContain('Data Readiness Gate');
    expect(code).toContain('gate_status');
  });

  it('shows 3 regulation cards (tertiaire, bacs, aper)', () => {
    expect(code).toContain('tertiaire_operat');
    expect(code).toContain('bacs');
    expect(code).toContain('aper');
  });

  it('shows scores strip (4 metrics)', () => {
    expect(code).toContain('reg_risk');
    expect(code).toContain('evidence_risk');
    expect(code).toContain('financial_opportunity_eur');
    expect(code).toContain('trust_score');
  });
});

// ============================================================
// C. Route registry: helpers exist
// ============================================================
describe('C · Route registry compliance helpers', () => {
  const code = readSrc('services', 'routes.js');

  it('exports toCompliancePipeline()', () => {
    expect(code).toContain('export function toCompliancePipeline');
  });

  it('exports toSiteCompliance(siteId)', () => {
    expect(code).toContain('export function toSiteCompliance');
  });

  it('toCompliancePipeline returns /compliance/pipeline', () => {
    expect(code).toContain("'/compliance/pipeline'");
  });

  it('toSiteCompliance returns /compliance/sites/ path', () => {
    expect(code).toContain('/compliance/sites/');
  });
});

// ============================================================
// D. App.jsx: routes registered
// ============================================================
describe('D · App.jsx route registration', () => {
  const code = readSrc('App.jsx');

  it('lazy-loads CompliancePipelinePage', () => {
    expect(code).toContain('CompliancePipelinePage');
  });

  it('lazy-loads SiteCompliancePage', () => {
    expect(code).toContain('SiteCompliancePage');
  });

  it('registers /compliance/pipeline route', () => {
    expect(code).toContain('path="/compliance/pipeline"');
  });

  it('registers /compliance/sites/:siteId route', () => {
    expect(code).toContain('path="/compliance/sites/:siteId"');
  });

  it('/compliance root redirects to /conformite (V92)', () => {
    const line = code.split('\n').find((l) => l.includes('path="/compliance"'));
    expect(line).toBeDefined();
    expect(line).toContain('Navigate');
    expect(line).toContain('/conformite');
  });
});

// ============================================================
// E. API: endpoint functions exported
// ============================================================
describe('E · API compliance V68 endpoints', () => {
  const code = readSrc('services', 'api.js');

  it('exports getSiteComplianceSummary', () => {
    expect(code).toContain('export const getSiteComplianceSummary');
  });

  it('exports getPortfolioComplianceSummary', () => {
    expect(code).toContain('export const getPortfolioComplianceSummary');
  });

  it('calls /compliance/sites/{siteId}/summary', () => {
    expect(code).toContain('/compliance/sites/${siteId}/summary');
  });

  it('calls /compliance/portfolio/summary', () => {
    expect(code).toContain('/compliance/portfolio/summary');
  });
});

// ============================================================
// F. "Créer action" CTA: no blank page risk
// ============================================================
describe('F · Créer action — no blank page', () => {
  const pipeline = readSrc('pages', 'CompliancePipelinePage.jsx');
  const sitePage = readSrc('pages', 'SiteCompliancePage.jsx');

  it('pipeline: Créer action uses openActionDrawer (not navigate to blank)', () => {
    expect(pipeline).toContain('openActionDrawer');
    expect(pipeline).not.toContain('CreateActionModal');
    // Must NOT have a navigate('/actions/new') without context
    const rawNavToActionsNew = (pipeline.match(/navigate\(['"`]\/actions\/new/g) || []).length;
    expect(rawNavToActionsNew).toBe(0);
  });

  it('site page: Créer action uses openActionDrawer with siteId context', () => {
    expect(sitePage).toContain('openActionDrawer');
    expect(sitePage).toContain('siteId: parseInt(siteId)');
  });

  it('pipeline: CTA has data-testid for E2E targeting', () => {
    expect(pipeline).toContain('data-testid="cta-creer-action"');
  });

  it('pipeline: uses route registry (no hardcoded URLs)', () => {
    // Check that navigation uses route helpers
    expect(pipeline).toContain('toSiteCompliance');
    expect(pipeline).toContain('toPatrimoine');
    expect(pipeline).toContain('toBillIntel');
  });

  it('site page: uses route registry for back navigation', () => {
    expect(sitePage).toContain('toCompliancePipeline');
  });
});

// ============================================================
// G. File existence checks
// ============================================================
describe('G · V68 files exist', () => {
  it('CompliancePipelinePage.jsx exists', () => {
    expect(existsSync(resolve(root, 'src/pages/CompliancePipelinePage.jsx'))).toBe(true);
  });

  it('SiteCompliancePage.jsx exists', () => {
    expect(existsSync(resolve(root, 'src/pages/SiteCompliancePage.jsx'))).toBe(true);
  });
});
