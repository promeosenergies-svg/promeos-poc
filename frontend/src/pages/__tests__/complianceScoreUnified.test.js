/**
 * PROMEOS — A.2: Unified compliance score — Source-guard tests
 * Tests 100% readFileSync / regex — no DOM mock needed.
 *
 * A. dashboardEssentials: unified score integration
 * B. Cockpit.jsx: API fetch + injection
 * C. kpiMessaging: thresholds 40/70
 * D. glossary: compliance_score entry
 * E. API: score endpoints
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. dashboardEssentials: unified score
// ============================================================
describe('A - dashboardEssentials unified compliance score', () => {
  const code = readSrc('models', 'dashboardEssentials.js');

  it('reads compliance_score from kpis', () => {
    expect(code).toContain('compliance_score');
  });

  it('displays score as X/100 format', () => {
    expect(code).toContain('/100');
  });

  it('uses threshold 40 for crit', () => {
    expect(code).toContain('< 40');
  });

  it('uses threshold 70 for warn', () => {
    expect(code).toContain('< 70');
  });

  it('label is Score conformite', () => {
    expect(code).toContain('Score conformit');
  });

  it('has explain: compliance_score for glossary link', () => {
    expect(code).toContain("explain: 'compliance_score'");
  });

  it('shows DT/BACS/APER breakdown in sub text', () => {
    expect(code).toContain('DT 45%');
    expect(code).toContain('BACS 30%');
    expect(code).toContain('APER 25%');
  });

  it('handles compliance_confidence for partial data indicator', () => {
    expect(code).toContain('compliance_confidence');
  });
});

// ============================================================
// B. Cockpit.jsx: API fetch + injection
// ============================================================
describe('B - Cockpit fetches unified compliance score', () => {
  const code = readSrc('pages', 'Cockpit.jsx');

  it('fetches /api/compliance/portfolio/score', () => {
    expect(code).toContain('/api/compliance/portfolio/score');
  });

  it('stores complianceApi state', () => {
    expect(code).toContain('complianceApi');
  });

  it('injects compliance_score into kpis useMemo', () => {
    expect(code).toContain('compliance_score:');
  });

  it('injects compliance_confidence into kpis', () => {
    expect(code).toContain('compliance_confidence:');
  });

  it('uses avg_score from API response', () => {
    expect(code).toContain('avg_score');
  });
});

// ============================================================
// C. kpiMessaging: thresholds aligned with A.2
// ============================================================
describe('C - kpiMessaging conformite thresholds', () => {
  const code = readSrc('services', 'kpiMessaging.js');

  it('has conformite handler', () => {
    expect(code).toContain('conformite:');
  });

  it('uses threshold 70 for ok', () => {
    expect(code).toContain('v >= 70');
  });

  it('uses threshold 40 for warn', () => {
    expect(code).toContain('v >= 40');
  });

  it('expert message references DT 45% + BACS 30% + APER 25%', () => {
    expect(code).toContain('DT 45%');
    expect(code).toContain('BACS 30%');
    expect(code).toContain('APER 25%');
  });

  it('displays score as X/100 in messages', () => {
    expect(code).toContain('/100');
  });
});

// ============================================================
// D. Glossary: compliance_score entry
// ============================================================
describe('D - Glossary compliance_score', () => {
  const code = readSrc('ui', 'glossary.js');

  it('has compliance_score entry', () => {
    expect(code).toContain('compliance_score:');
  });

  it('mentions Decret Tertiaire in definition', () => {
    expect(code).toMatch(/[Dd][eé]cret [Tt]ertiaire/);
  });

  it('mentions BACS in definition', () => {
    expect(code).toContain('BACS');
  });

  it('mentions APER in definition', () => {
    expect(code).toContain('APER');
  });

  it('explicitly excludes CEE', () => {
    expect(code).toContain('CEE');
  });

  it('mentions the formula weights 45/30/25', () => {
    expect(code).toContain('45%');
    expect(code).toContain('30%');
    expect(code).toContain('25%');
  });
});

// ============================================================
// E. Cockpit fetches score endpoint directly
// ============================================================
describe('E - Score endpoint wiring', () => {
  const code = readSrc('pages', 'Cockpit.jsx');

  it('sends X-Org-Id header with score request', () => {
    expect(code).toContain('X-Org-Id');
  });

  it('handles fetch failure gracefully (sets null)', () => {
    expect(code).toContain('setComplianceApi(null)');
  });
});
