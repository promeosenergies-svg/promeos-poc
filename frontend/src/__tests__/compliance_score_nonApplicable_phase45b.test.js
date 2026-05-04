/**
 * compliance_score_nonApplicable_phase45b.test.js — Sprint C-2 Phase 4.5b
 *
 * Vérifie que les 3 fichiers ciblés Phase 4.5b distinguent désormais 3 cas
 * compliance_score :
 *   - Score valide       : affiche la valeur numérique (ScoreGauge / 3xl bold / 5xl bold)
 *   - confidence='non_applicable' : affiche <NonApplicableLabel /> (Phase 4.5a)
 *   - score=null + confidence non_applicable absent : fallback existant (— ou 0)
 *
 * Pattern repo : readFileSync + import + regex (env=node, pas de DOM).
 */
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = resolve(__dirname, '..');

const conformitePageSrc = readFileSync(resolve(SRC_ROOT, 'pages', 'ConformitePage.jsx'), 'utf8');
const obligationsTabSrc = readFileSync(
  resolve(SRC_ROOT, 'pages', 'conformite-tabs', 'ObligationsTab.jsx'),
  'utf8'
);
const headerSrc = readFileSync(
  resolve(SRC_ROOT, 'components', 'conformite', 'ComplianceScoreHeader.jsx'),
  'utf8'
);
const regOpsSrc = readFileSync(resolve(SRC_ROOT, 'pages', 'RegOps.jsx'), 'utf8');

// ─── Fix 1 : ConformitePage.jsx + ObligationsTab.jsx ────────────────────────

describe('Fix 1 — ConformitePage useMemo + ObligationsTab ScoreGauge', () => {
  it('ConformitePage useMemo expose pct_confidence sibling', () => {
    expect(conformitePageSrc).toContain('pct_confidence');
  });

  it("ConformitePage met pct=null quand confidence='non_applicable'", () => {
    // Pattern : isNonApplicable check + ternaire null
    expect(conformitePageSrc).toMatch(/isNonApplicable[\s\S]{0,80}null/);
    expect(conformitePageSrc).toMatch(/confidence\s*===\s*['"]non_applicable['"]/);
  });

  it('ObligationsTab importe NonApplicableLabel', () => {
    expect(obligationsTabSrc).toMatch(
      /import\s+NonApplicableLabel\s+from\s+['"]\.\.\/\.\.\/components\/NonApplicableLabel['"]/
    );
  });

  it('ObligationsTab branche sur score.pct_confidence avant ScoreGauge', () => {
    expect(obligationsTabSrc).toMatch(/score\.pct_confidence\s*===\s*['"]non_applicable['"]/);
    expect(obligationsTabSrc).toContain('<NonApplicableLabel');
  });
});

// ─── Fix 2 : ComplianceScoreHeader.jsx ─────────────────────────────────────

describe('Fix 2 — ComplianceScoreHeader.jsx score display', () => {
  it('importe NonApplicableLabel', () => {
    expect(headerSrc).toMatch(
      /import\s+NonApplicableLabel\s+from\s+['"]\.\.\/NonApplicableLabel['"]/
    );
  });

  it("détecte confidence='non_applicable' avant rendu Math.round", () => {
    expect(headerSrc).toMatch(/complianceScore\.confidence\s*===\s*['"]non_applicable['"]/);
  });

  it('rend NonApplicableLabel variant="large" quand non_applicable', () => {
    expect(headerSrc).toMatch(
      /isNonApplicable\s*\?[\s\S]{0,200}<NonApplicableLabel\s+variant="large"/
    );
  });
});

// ─── Fix 3 : RegOps.jsx compliance score display ───────────────────────────

describe('Fix 3 — RegOps.jsx compliance_score display', () => {
  it('importe NonApplicableLabel', () => {
    expect(regOpsSrc).toMatch(
      /import\s+NonApplicableLabel\s+from\s+['"]\.\.\/components\/NonApplicableLabel['"]/
    );
  });

  it("détecte assessment.compliance_score_confidence='non_applicable'", () => {
    expect(regOpsSrc).toMatch(
      /assessment\.compliance_score_confidence\s*===\s*['"]non_applicable['"]/
    );
  });

  it('rend NonApplicableLabel variant="large" quand non_applicable, fallback fmtNum sinon', () => {
    // Pattern : ternaire avec NonApplicableLabel d'abord, puis fmtNum dans else
    expect(regOpsSrc).toMatch(/non_applicable['"][\s\S]{0,200}<NonApplicableLabel/);
    expect(regOpsSrc).toContain('fmtNum(assessment.compliance_score, 1)');
  });
});
