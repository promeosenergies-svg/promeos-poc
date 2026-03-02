/**
 * conformiteUxUpgrade.test.js — UX Upgrade source-guard tests
 * Tests 100% readFileSync + regex — no DOM mock needed.
 *
 * Sections:
 * A. GuidedModeBandeau — structure (~4 tests)
 * B. NextBestActionCard — structure (~4 tests)
 * C. Expert mode — ObligationsTab + ExecutionTab (~4 tests)
 * D. DonneesTab — KPIs + gaps (~4 tests)
 * E. Labels FR — guided mode + données (~2 tests)
 * F. ConformitePage wiring (~4 tests)
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. GuidedModeBandeau — structure
// ============================================================
describe('A · GuidedModeBandeau — structure', () => {
  const code = readSrc('pages', 'conformite-tabs', 'GuidedModeBandeau.jsx');

  it('exists and uses Card/Button from UI', () => {
    expect(code).toMatch(/import.*Card.*from/);
    expect(code).toMatch(/import.*Button.*from/);
  });

  it('has data-testid="guided-mode-bandeau"', () => {
    expect(code).toContain('data-testid="guided-mode-bandeau"');
  });

  it('has per-step data-testid guided-step-*', () => {
    expect(code).toMatch(/data-testid.*guided-step/);
  });

  it('renders CTAs via onStepClick prop', () => {
    expect(code).toContain('onStepClick');
  });

  it('imports GUIDED_MODE_LABELS from complianceLabels', () => {
    expect(code).toMatch(/import.*GUIDED_MODE_LABELS.*from/);
  });
});

// ============================================================
// B. NextBestActionCard — structure
// ============================================================
describe('B · NextBestActionCard — structure', () => {
  const code = readSrc('pages', 'conformite-tabs', 'NextBestActionCard.jsx');

  it('exists and uses Card/Badge/Button from UI', () => {
    expect(code).toMatch(/import.*Card.*from/);
    expect(code).toMatch(/import.*Badge.*from/);
    expect(code).toMatch(/import.*Button.*from/);
  });

  it('has data-testid="next-best-action"', () => {
    expect(code).toContain('data-testid="next-best-action"');
  });

  it('has data-testid="nba-cta" on CTA button', () => {
    expect(code).toContain('data-testid="nba-cta"');
  });

  it('has severity-based styling (critical/high/medium/low)', () => {
    expect(code).toContain('critical');
    expect(code).toContain('high');
    expect(code).toContain('medium');
    expect(code).toContain('low');
  });
});

// ============================================================
// C. Expert mode — ObligationsTab + ExecutionTab
// ============================================================
describe('C · Expert mode conditionals', () => {
  const oblCode = readSrc('pages', 'conformite-tabs', 'ObligationsTab.jsx');
  const exeCode = readSrc('pages', 'conformite-tabs', 'ExecutionTab.jsx');

  it('ObligationsTab passes isExpert to ObligationCard', () => {
    expect(oblCode).toMatch(/isExpert={isExpert}/);
  });

  it('ObligationsTab conditions rule_id display on isExpert', () => {
    expect(oblCode).toMatch(/isExpert.*rule_id/);
  });

  it('ObligationsTab has non-expert simplified status (STATUT_LABELS)', () => {
    expect(oblCode).toContain('STATUT_LABELS');
  });

  it('ExecutionTab has !isExpert branch (simplified view)', () => {
    expect(exeCode).toMatch(/!isExpert|isExpert\s*\?/);
  });

  it('ExecutionTab expert expanded section shows rule_id and inputs', () => {
    expect(exeCode).toMatch(/isExpert.*rule_id/s);
    expect(exeCode).toContain('finding.inputs');
  });
});

// ============================================================
// D. DonneesTab — KPIs + gaps
// ============================================================
describe('D · DonneesTab — enhanced KPIs', () => {
  const code = readSrc('pages', 'conformite-tabs', 'DonneesTab.jsx');

  it('accepts donneesMetrics prop', () => {
    expect(code).toContain('donneesMetrics');
  });

  it('contains Complétude / completude reference', () => {
    expect(code).toMatch(/[Cc]ompl[eé]tude/);
  });

  it('contains Confiance / confiance reference', () => {
    expect(code).toMatch(/[Cc]onfiance/);
  });

  it('contains couverture factures reference', () => {
    expect(code).toMatch(/couverture.*factures/i);
  });

  it('imports Progress component from UI', () => {
    expect(code).toMatch(/import.*Progress.*from.*ui/);
  });

  it('renders gaps with CTAs (navigate)', () => {
    expect(code).toContain('gap.ctaPath');
    expect(code).toContain('gap.ctaLabel');
  });

  it('imports DONNEES_ENHANCED_LABELS', () => {
    expect(code).toMatch(/import.*DONNEES_ENHANCED_LABELS.*from/);
  });
});

// ============================================================
// E. Labels FR — guided mode + données
// ============================================================
describe('E · Labels FR', () => {
  const code = readSrc('domain', 'compliance', 'complianceLabels.fr.js');

  it('exports GUIDED_MODE_LABELS', () => {
    expect(code).toMatch(/export const GUIDED_MODE_LABELS/);
  });

  it('exports DONNEES_ENHANCED_LABELS', () => {
    expect(code).toMatch(/export const DONNEES_ENHANCED_LABELS/);
  });
});

// ============================================================
// F. ConformitePage wiring
// ============================================================
describe('F · ConformitePage wiring', () => {
  const code = readSrc('pages', 'ConformitePage.jsx');

  it('imports GuidedModeBandeau', () => {
    expect(code).toMatch(/import GuidedModeBandeau/);
  });

  it('imports NextBestActionCard', () => {
    expect(code).toMatch(/import NextBestActionCard/);
  });

  it('imports computeGuidedSteps + computeNextBestAction + computeDonneesMetrics', () => {
    expect(code).toContain('computeGuidedSteps');
    expect(code).toContain('computeNextBestAction');
    expect(code).toContain('computeDonneesMetrics');
  });

  it('renders GuidedModeBandeau conditionally on !isExpert', () => {
    expect(code).toMatch(/!isExpert.*GuidedModeBandeau/s);
  });

  it('renders NextBestActionCard', () => {
    expect(code).toMatch(/<NextBestActionCard/);
  });

  it('passes donneesMetrics to DonneesTab', () => {
    expect(code).toContain('donneesMetrics={donneesMetrics}');
  });
});
