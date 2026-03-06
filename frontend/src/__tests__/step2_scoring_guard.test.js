/**
 * PROMEOS — Step 2: Scoring Unified Source Guards
 * Vérifie que le frontend ne calcule pas de score conformité inline.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. RegOps.jsx — no inline score computation ─────────────────────────────

describe('Step2 — RegOps.jsx no inline scoring', () => {
  const src = readSrc('pages/RegOps.jsx');

  it('does not contain "100 -" scoring pattern', () => {
    // Should not compute scores client-side
    expect(src).not.toMatch(/100\s*-\s*.*severity/);
  });

  it('does not contain "severity * urgency" computation', () => {
    expect(src).not.toMatch(/severity\s*\*\s*urgency/);
  });

  it('reads compliance_score from API response', () => {
    // The score is read from assessment object (from API), not computed
    expect(src).toContain('compliance_score');
  });

  it('does not import scoring utilities', () => {
    // No scoring computation imports
    expect(src).not.toMatch(/import.*compute.*[Ss]core/);
  });
});

// ── B. No scoring computation in frontend services ──────────────────────────

describe('Step2 — api.js scoring endpoints', () => {
  const src = readSrc('services/api.js');

  it('has getRegOpsSiteAssessment endpoint', () => {
    expect(src).toContain('/regops/site/');
  });

  it('has getScoreExplain endpoint', () => {
    expect(src).toContain('/regops/score_explain');
  });

  it('has getRegOpsDashboard endpoint', () => {
    expect(src).toContain('/regops/dashboard');
  });

  it('does not compute scores inline', () => {
    // api.js should only fetch scores, not compute them
    expect(src).not.toMatch(/100\s*-\s*.*severity/);
    expect(src).not.toMatch(/severity\s*\*\s*urgency/);
  });
});
