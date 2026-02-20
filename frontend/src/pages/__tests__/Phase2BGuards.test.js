/**
 * PROMEOS — Phase2BGuards.test.js
 * Source-code guards ensuring centralized constants are used,
 * no silent API errors, and no hardcoded duplications remain.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pagesDir = join(__dirname, '..');
const libDir = join(__dirname, '..', '..', 'lib');
const ctxDir = join(__dirname, '..', '..', 'contexts');
const compDir = join(__dirname, '..', '..', 'components');

function readSrc(dir, file) {
  return readFileSync(join(dir, file), 'utf-8');
}

// ── Guard: Site360 uses centralized constants ───────────────────────────────

describe('Site360 — centralized constants', () => {
  const src = readSrc(pagesDir, 'Site360.jsx');

  it('imports getStatusBadgeProps from lib/constants', () => {
    expect(src).toContain("from '../lib/constants'");
    expect(src).toContain('getStatusBadgeProps');
  });

  it('does not import getMockSite', () => {
    expect(src).not.toContain('getMockSite');
  });

  it('uses useScope for site data', () => {
    expect(src).toContain('useScope');
    expect(src).toContain('scopedSites');
  });

  it('has sitesLoading guard', () => {
    expect(src).toContain('sitesLoading');
  });

  it('no unaccented "A risque" or "A evaluer" labels', () => {
    // Match raw 'A risque' (without À) — skip occurrences inside object keys like a_risque
    const lines = src.split('\n');
    for (const line of lines) {
      // Skip lines that are just object keys (a_risque:, a_evaluer:)
      if (line.match(/^\s*(a_risque|a_evaluer)\s*[,:]/)) continue;
      expect(line).not.toMatch(/'A risque'/);
      expect(line).not.toMatch(/'A evaluer'/);
    }
  });

  it('imports SEV_BADGE from lib/constants (not defined locally)', () => {
    expect(src).toContain('SEV_BADGE');
    expect(src).toContain("from '../lib/constants'");
    // No local definition — should be imported
    expect(src).not.toMatch(/const SEV_BADGE\s*=/);
  });

  it('no inline severity ternary chains for badge status', () => {
    // Inline ternary: a.severity === 'critical' ? 'crit' : a.severity === 'high' ? ...
    expect(src).not.toMatch(/severity\s*===\s*'critical'\s*\?\s*'crit'/);
  });
});

// ── Guard: Patrimoine uses centralized constants ────────────────────────────

describe('Patrimoine — centralized constants', () => {
  const src = readSrc(pagesDir, 'Patrimoine.jsx');

  it('imports from lib/constants', () => {
    expect(src).toContain("from '../lib/constants'");
  });

  it('imports RISK_THRESHOLDS', () => {
    expect(src).toContain('RISK_THRESHOLDS');
  });

  it('imports ANOMALY_THRESHOLDS', () => {
    expect(src).toContain('ANOMALY_THRESHOLDS');
  });

  it('no unaccented "A risque" or "A evaluer" in labels', () => {
    const lines = src.split('\n');
    for (const line of lines) {
      if (line.match(/^\s*(a_risque|a_evaluer)\s*[,:]/)) continue;
      expect(line).not.toMatch(/'A risque'/);
      expect(line).not.toMatch(/'A evaluer'/);
    }
  });
});

// ── Guard: Cockpit uses centralized constants ───────────────────────────────

describe('Cockpit — centralized constants', () => {
  const src = readSrc(pagesDir, 'Cockpit.jsx');

  it('imports from lib/constants', () => {
    expect(src).toContain("from '../lib/constants'");
  });

  it('no "EUR" in display labels', () => {
    const lines = src.split('\n');
    for (const line of lines) {
      // Skip comments
      if (line.trim().startsWith('//') || line.trim().startsWith('*')) continue;
      expect(line).not.toMatch(/}\s*EUR/);
    }
  });

  it('weight display uses READINESS_WEIGHTS (no hardcoded "poids : 30%")', () => {
    expect(src).not.toMatch(/poids : 30%/);
    expect(src).not.toMatch(/poids : 40%/);
    expect(src).toContain('READINESS_WEIGHTS.data');
    expect(src).toContain('READINESS_WEIGHTS.conformity');
    expect(src).toContain('READINESS_WEIGHTS.actions');
  });
});

// ── Guard: CommandCenter uses centralized getRiskStatus ─────────────────────

describe('CommandCenter — centralized constants', () => {
  const src = readSrc(pagesDir, 'CommandCenter.jsx');

  it('imports getRiskStatus from lib/constants', () => {
    expect(src).toContain('getRiskStatus');
    expect(src).toContain("from '../lib/constants'");
  });

  it('no hardcoded 50000/10000 risk thresholds', () => {
    // Check there's no inline ternary with hardcoded risk values
    expect(src).not.toMatch(/risque\s*>\s*50000/);
    expect(src).not.toMatch(/risque\s*>\s*10000/);
  });

  it('no "EUR" in table display (uses €)', () => {
    const lines = src.split('\n');
    for (const line of lines) {
      if (line.trim().startsWith('//') || line.trim().startsWith('*')) continue;
      expect(line).not.toMatch(/}\s*EUR\s*</);
    }
  });
});

// ── Guard: dashboardEssentials uses centralized constants ───────────────────

describe('dashboardEssentials — centralized constants', () => {
  const modelsDir = join(__dirname, '..', '..', 'models');
  const src = readSrc(modelsDir, 'dashboardEssentials.js');

  it('imports from lib/constants', () => {
    expect(src).toContain("from '../lib/constants'");
  });

  it('imports COVERAGE_THRESHOLDS', () => {
    expect(src).toContain('COVERAGE_THRESHOLDS');
  });

  it('imports RISK_THRESHOLDS', () => {
    expect(src).toContain('RISK_THRESHOLDS');
  });

  it('imports READINESS_WEIGHTS', () => {
    expect(src).toContain('READINESS_WEIGHTS');
  });

  it('imports SEVERITY_RANK from lib/constants (not defined locally)', () => {
    expect(src).toContain('SEVERITY_RANK');
    // No local definition — should be imported
    expect(src).not.toMatch(/const SEVERITY_RANK\s*=/);
  });
});

// ── Guard: ScopeContext error handling ───────────────────────────────────────

describe('ScopeContext — error handling & refresh', () => {
  const src = readSrc(ctxDir, 'ScopeContext.jsx');

  it('exposes sitesError in context value', () => {
    expect(src).toContain('sitesError');
  });

  it('exposes refreshSites in context value', () => {
    expect(src).toContain('refreshSites');
  });

  it('sets error message on catch (not silent)', () => {
    // Must set sitesError with a meaningful message
    expect(src).toContain('setSitesError');
  });

  it('does not silently set apiSites to [] on error', () => {
    // The old pattern was: .catch(() => { setApiSites([]); })
    // After fix: error preserves previous apiSites
    const catchBlock = src.match(/\.catch\(\(.*?\)\s*=>\s*\{[\s\S]*?\}\)/g) || [];
    for (const block of catchBlock) {
      // If it has setSitesError, it's the new pattern (good)
      if (block.includes('setSitesError')) continue;
      // Old silent pattern should not exist
      expect(block).not.toMatch(/setApiSites\(\[\]\)/);
    }
  });
});

// ── Guard: PatrimoineWizard uses refreshSites (no window.location.reload) ──

describe('PatrimoineWizard — no page reload', () => {
  const src = readSrc(compDir, 'PatrimoineWizard.jsx');

  it('does not use window.location.reload()', () => {
    expect(src).not.toContain('window.location.reload');
  });

  it('imports useScope', () => {
    expect(src).toContain('useScope');
  });

  it('calls refreshSites', () => {
    expect(src).toContain('refreshSites');
  });
});

// ── Guard: constants.js exports all required symbols ─────────────────────

describe('constants.js — completeness', () => {
  const src = readSrc(libDir, 'constants.js');

  it('exports SEVERITY_RANK with correct keys', () => {
    expect(src).toContain('export const SEVERITY_RANK');
    expect(src).toContain('critical:');
    expect(src).toContain('high:');
    expect(src).toContain('warn:');
    expect(src).toContain('medium:');
    expect(src).toContain('info:');
  });

  it('exports SEV_BADGE with correct keys', () => {
    expect(src).toContain('export const SEV_BADGE');
    expect(src).toContain("critical: 'crit'");
    expect(src).toMatch(/high:\s+'warn'/);
    expect(src).toMatch(/low:\s+'neutral'/);
  });

  it('exports all threshold objects', () => {
    expect(src).toContain('export const RISK_THRESHOLDS');
    expect(src).toContain('export const COVERAGE_THRESHOLDS');
    expect(src).toContain('export const CONFORMITY_THRESHOLDS');
    expect(src).toContain('export const MATURITY_THRESHOLDS');
    expect(src).toContain('export const READINESS_WEIGHTS');
    expect(src).toContain('export const ACTIONS_SCORE');
    expect(src).toContain('export const ANOMALY_THRESHOLDS');
    expect(src).toContain('export const STATUS_CONFIG');
  });

  it('exports helper functions', () => {
    expect(src).toContain('export function getStatusBadgeProps');
    expect(src).toContain('export function getRiskStatus');
  });

  it('all labels are in French (accented)', () => {
    expect(src).toContain('Conforme');
    expect(src).toContain('Non conforme');
    expect(src).toContain('À risque');
    expect(src).toContain('À évaluer');
    expect(src).toContain('Dérogation');
  });
});
