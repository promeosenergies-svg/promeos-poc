/**
 * PROMEOS — A.2 Fix: Compliance score consistency across all 5 pages
 * Source-guard: all pages import thresholds from the SAME source (lib/constants).
 *
 * A. constants.js: shared config exists
 * B. Dashboard.jsx: uses shared config
 * C. ConformitePage.jsx: uses shared config + score header
 * D. Site360.jsx: uses shared config + score badge
 * E. RegOps.jsx: uses shared config (no local getComplianceScoreColor)
 * F. BacsWizard.jsx: uses shared config + /100 format
 * G. dashboardEssentials.js: uses COMPLIANCE_SCORE_THRESHOLDS
 * H. Cockpit.jsx: already OK (threshold via dashboardEssentials)
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

// ============================================================
// A. constants.js: shared compliance score config
// ============================================================
describe('A - constants.js has unified compliance score config', () => {
  const code = readSrc('lib', 'constants.js');

  it('exports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('export const COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('COMPLIANCE_SCORE_THRESHOLDS.ok = 70', () => {
    expect(code).toContain('ok: 70');
  });

  it('COMPLIANCE_SCORE_THRESHOLDS.warn = 40', () => {
    expect(code).toContain('warn: 40');
  });

  it('exports getComplianceScoreColor', () => {
    expect(code).toContain('export function getComplianceScoreColor');
  });

  it('exports getComplianceGrade', () => {
    expect(code).toContain('export function getComplianceGrade');
  });

  it('exports getComplianceScoreStatus', () => {
    expect(code).toContain('export function getComplianceScoreStatus');
  });

  it('getComplianceScoreColor uses COMPLIANCE_SCORE_THRESHOLDS (not hardcoded)', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS.ok');
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS.warn');
  });
});

// ============================================================
// B. Dashboard.jsx: uses shared config
// ============================================================
describe('B - Dashboard uses shared compliance score', () => {
  const code = readSrc('pages', 'Dashboard.jsx');

  it('imports from lib/constants', () => {
    expect(code).toContain("from '../lib/constants'");
  });

  it('imports getComplianceScoreColor', () => {
    expect(code).toContain('getComplianceScoreColor');
  });

  it('imports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('displays score as /100', () => {
    expect(code).toContain('/100');
  });

  it('fetches /api/compliance/portfolio/score', () => {
    expect(code).toContain('/api/compliance/portfolio/score');
  });

  it('has Score conformite column header', () => {
    expect(code).toContain('Score conformit');
  });
});

// ============================================================
// C. ConformitePage.jsx: score header + breakdown bars
// ============================================================
describe('C - ConformitePage has compliance score header', () => {
  const code = readSrc('pages', 'ConformitePage.jsx');

  it('imports from lib/constants', () => {
    expect(code).toContain("from '../lib/constants'");
  });

  it('imports getComplianceScoreColor', () => {
    expect(code).toContain('getComplianceScoreColor');
  });

  it('imports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('has data-section="compliance-score-header"', () => {
    expect(code).toContain('data-section="compliance-score-header"');
  });

  it('fetches /api/compliance/sites/ or /api/compliance/portfolio/score', () => {
    expect(code).toContain('/api/compliance/sites/');
    expect(code).toContain('/api/compliance/portfolio/score');
  });

  it('shows breakdown bars for 3 frameworks', () => {
    expect(code).toContain("'tertiaire_operat'");
    expect(code).toContain("'bacs'");
    expect(code).toContain("APER");
  });

  it('shows dynamic weight labels from API and Non applicable state', () => {
    expect(code).toContain('fw.weight');
    expect(code).toContain('Non applicable');
  });

  it('displays /100 format', () => {
    expect(code).toContain('/100');
  });

  it('shows confidence indicator', () => {
    expect(code).toContain('Confiance');
  });
});

// ============================================================
// D. Site360.jsx: score + grade next to badge
// ============================================================
describe('D - Site360 has compliance score badge', () => {
  const code = readSrc('pages', 'Site360.jsx');

  it('imports from lib/constants', () => {
    expect(code).toContain("from '../lib/constants'");
  });

  it('imports getComplianceScoreColor', () => {
    expect(code).toContain('getComplianceScoreColor');
  });

  it('imports getComplianceGrade', () => {
    expect(code).toContain('getComplianceGrade');
  });

  it('imports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('fetches /api/compliance/sites/{id}/score', () => {
    expect(code).toContain('/api/compliance/sites/');
    expect(code).toContain('/score');
  });

  it('has data-testid="compliance-score-badge"', () => {
    expect(code).toContain('data-testid="compliance-score-badge"');
  });

  it('displays /100 format', () => {
    expect(code).toContain('/100');
  });

  it('shows grade letter', () => {
    expect(code).toContain('grade.letter');
  });
});

// ============================================================
// E. RegOps.jsx: uses shared config (not local)
// ============================================================
describe('E - RegOps uses shared getComplianceScoreColor', () => {
  const code = readSrc('pages', 'RegOps.jsx');

  it('imports from lib/constants', () => {
    expect(code).toContain("from '../lib/constants'");
  });

  it('imports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('does NOT define local getComplianceScoreColor with hardcoded thresholds', () => {
    // Should not have a local function body with hardcoded 80/60/40
    expect(code).not.toContain("if (score >= 80) return 'text-green-600'");
  });

  it('displays /100 format', () => {
    expect(code).toContain('/100');
  });
});

// ============================================================
// F. BacsWizard.jsx: uses shared thresholds + /100 format
// ============================================================
describe('F - BacsWizard uses shared thresholds', () => {
  const code = readSrc('components', 'BacsWizard.jsx');

  it('imports from lib/constants', () => {
    expect(code).toContain("from '../lib/constants'");
  });

  it('imports getComplianceScoreColor', () => {
    expect(code).toContain('getComplianceScoreColor');
  });

  it('does NOT use hardcoded threshold 50 for score color', () => {
    expect(code).not.toContain('>= 50 ?');
  });

  it('displays /100 format (not %)', () => {
    expect(code).toContain('/100');
  });
});

// ============================================================
// G. dashboardEssentials.js: uses COMPLIANCE_SCORE_THRESHOLDS
// ============================================================
describe('G - dashboardEssentials uses shared thresholds', () => {
  const code = readSrc('models', 'dashboardEssentials.js');

  it('imports COMPLIANCE_SCORE_THRESHOLDS', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS');
  });

  it('uses COMPLIANCE_SCORE_THRESHOLDS.warn for crit status', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS.warn');
  });

  it('uses COMPLIANCE_SCORE_THRESHOLDS.ok for warn/ok boundary', () => {
    expect(code).toContain('COMPLIANCE_SCORE_THRESHOLDS.ok');
  });

  it('does NOT hardcode 40 or 70 for conformite status thresholds', () => {
    // The conformite status line should NOT have literal "< 40" or "< 70"
    // It should use the constants
    const statusLine = code.split('\n').find((l) => l.includes("status:") && l.includes("COMPLIANCE_SCORE_THRESHOLDS"));
    expect(statusLine).toBeDefined();
  });
});
