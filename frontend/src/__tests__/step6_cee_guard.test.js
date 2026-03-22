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

// ── A. RegOps.jsx — obligations vs incentives separation ────────────────────

describe('Step6 — RegOps.jsx CEE separation', () => {
  const src = readSrc('pages/RegOps.jsx');

  it('has "Obligations réglementaires" section', () => {
    expect(src).toContain('Obligations réglementaires');
  });

  it('has "Financements & opportunités" section', () => {
    expect(src).toContain('Financements & opportunités');
  });

  it('filters findings by category for obligations', () => {
    expect(src).toMatch(/category\s*!==\s*['"]incentive['"]/);
  });

  it.skip('filters findings by category for incentives — CEE masqué V1.2', () => {
    expect(src).toMatch(/category\s*===\s*['"]incentive['"]/);
  });

  it('uses Coins icon from lucide-react', () => {
    expect(src).toContain('Coins');
  });

  it.skip('shows "Éligible CEE" badge for incentives — CEE masqué V1.2', () => {
    expect(src).toContain('Éligible CEE');
  });

  it('has data-section="obligations" and data-section="incentives"', () => {
    expect(src).toContain('data-section="obligations"');
    // data-section="incentives" masqué V1.2 — CEE prévu évolution future
  });

  it('does NOT show severity badge for incentive findings', () => {
    // Incentive section should use neutral CEE badges, not getSeverityBadgeColor
    // The incentive block should not call getSeverityBadgeColor
    const incentiveBlock = src.split('data-section="incentives"')[1]?.split('</div>')[0] || '';
    expect(incentiveBlock).not.toContain('getSeverityBadgeColor');
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
