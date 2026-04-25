/**
 * PROMEOS — Step 6: CEE Separation Source Guards
 * Vérifie que RegOps.jsx et ConformitePage.jsx séparent
 * obligations réglementaires et financements CEE.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. RegOps/Sol — obligations vs incentives separation (Lot 3 P3) ─────────
//
// Depuis Pattern C Lot 3, RegOps.jsx est un loader thin ; la séparation
// obligations/incentives vit dans regops/sol_presenters.js (filtre
// `category !== 'incentive'` dans computeCompletion, sumPenalties,
// buildRegOpsEntityCardFields, buildRegOpsTimelineEvents). Les « data-section »
// CSS du legacy sont remplacés par la structure sémantique SolDetailPage +
// SolKpiRow + SolTimeline.

describe('Step6 — RegOps presenters preserve obligations/incentives filter', () => {
  const presenterSrc = readSrc('pages/regops/sol_presenters.js');

  it('filters findings by category !== incentive (obligations)', () => {
    expect(presenterSrc).toMatch(/category\s*!==\s*['"]incentive['"]/);
  });

  it('computeCompletion + sumPenalties + buildTimeline honor the filter', () => {
    // Le filtre doit apparaître plusieurs fois (au moins 3 call-sites)
    const matches = presenterSrc.match(/category\s*!==\s*['"]incentive['"]/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(3);
  });
});

// ── B. ConformitePage.jsx — CEE filtered from obligations ───────────────────

describe('Step6 — ConformitePage.jsx CEE separation', () => {
  const src = readSrc('pages/ConformitePage.jsx');

  it('sitesToObligations skips CEE findings', () => {
    // Logique extraite vers conformiteUtils.js (refactoring V101)
    const utilsSrc = readSrc('components/conformite/conformiteUtils.js');
    expect(utilsSrc).toMatch(/category\s*===\s*['"]incentive['"]/);
    expect(src).toMatch(/cee/i);
  });

  it('has sitesToIncentives function', () => {
    expect(src).toContain('sitesToIncentives');
  });

  it('has "Financements mobilisables" section', () => {
    expect(src).toContain('Financements mobilisables');
  });

  it('has data-section="incentives"', () => {
    expect(src).toContain('data-section="incentives"');
  });

  it('imports Coins icon', () => {
    expect(src).toContain('Coins');
  });

  it("mentions Certificats d'Économies d'Énergie", () => {
    expect(src).toMatch(/Certificats d'Économies d'Énergie/i);
  });
});

// ── C. Backend — category field exists ──────────────────────────────────────

describe('Step6 — Backend category field', () => {
  const backendRoot = join(__dirname, '..', '..', '..', 'backend');

  it('Finding schema has category field', () => {
    const src = readFileSync(join(backendRoot, 'regops', 'schemas.py'), 'utf-8');
    expect(src).toContain('category');
    expect(src).toContain('obligation');
    expect(src).toContain('incentive');
  });

  it('cee_p6.py sets category=incentive', () => {
    const src = readFileSync(join(backendRoot, 'regops', 'rules', 'cee_p6.py'), 'utf-8');
    expect(src).toContain('category="incentive"');
  });

  it('regops route includes category in response', () => {
    const src = readFileSync(join(backendRoot, 'routes', 'regops.py'), 'utf-8');
    expect(src).toContain('"category"');
  });

  it('compliance route includes category in response', () => {
    const src = readFileSync(join(backendRoot, 'routes', 'compliance.py'), 'utf-8');
    expect(src).toContain('"category"');
  });

  it('compliance route has category filter param', () => {
    const src = readFileSync(join(backendRoot, 'routes', 'compliance.py'), 'utf-8');
    expect(src).toMatch(/category.*Query/);
  });

  it('score A.2 excludes CEE', () => {
    const src = readFileSync(join(backendRoot, 'services', 'compliance_score_service.py'), 'utf-8');
    expect(src).toMatch(/CEE/i);
    // Only 3 frameworks: tertiaire, bacs, aper
    expect(src).not.toMatch(/FRAMEWORK_WEIGHTS\s*=\s*\{[^}]*cee/i);
  });
});
