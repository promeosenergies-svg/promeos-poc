/**
 * PROMEOS — V23: Demo Data Consistency
 * Ensures all views use ScopeContext as single source of truth.
 * Source-level guards: no direct getSites() or getOnboardingStatus() calls
 * for site counts in the guarded components.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const readPage = (name) => readFileSync(resolve(__dirname, '..', name), 'utf8');
const readComponent = (name) => readFileSync(resolve(__dirname, '..', '..', 'components', name), 'utf8');

// ── 1. Dashboard uses useScope(), not getSites() ──────────────────────────

describe('Dashboard scope discipline', () => {
  const src = readPage('Dashboard.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(src).toContain("import { useScope } from '../contexts/ScopeContext'");
  });

  it('does NOT call getSites() directly', () => {
    // getSites should not appear in the source (was removed)
    expect(src).not.toMatch(/getSites\s*\(/);
  });

  it('does NOT import getSites from api', () => {
    expect(src).not.toMatch(/import\s+.*getSites.*from\s+['"]\.\.\/services\/api['"]/);
  });

  it('uses sitesCount from scope for KPI', () => {
    expect(src).toContain('sitesCount');
  });

  it('uses orgSites from scope for table', () => {
    expect(src).toContain('orgSites');
  });
});

// ── 2. ConsommationsUsages uses useScope(), not getSites() ────────────────

describe('ConsommationsUsages (ImportWizard) scope discipline', () => {
  const src = readPage('ConsommationsUsages.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(src).toContain("import { useScope } from '../contexts/ScopeContext'");
  });

  it('does NOT call getSites() in ImportWizard', () => {
    // The old `getSites({ limit: 200 })` should be gone
    expect(src).not.toMatch(/getSites\s*\(\s*\{/);
  });

  it('uses orgSites from scope', () => {
    expect(src).toContain('orgSites');
  });
});

// ── 3. DemoBanner uses useScope(), not getOnboardingStatus() ──────────────

describe('DemoBanner scope discipline', () => {
  const src = readComponent('DemoBanner.jsx');

  it('imports useScope from ScopeContext', () => {
    expect(src).toContain("import { useScope } from '../contexts/ScopeContext'");
  });

  it('does NOT call getOnboardingStatus()', () => {
    expect(src).not.toMatch(/getOnboardingStatus\s*\(/);
  });

  it('does NOT import getOnboardingStatus from api', () => {
    expect(src).not.toMatch(/import\s+.*getOnboardingStatus.*from\s+['"]\.\.\/services\/api['"]/);
  });

  it('uses sitesCount from scope', () => {
    expect(src).toContain('sitesCount');
  });

  it('has HELIOS reload button (V55: single pack)', () => {
    expect(src).toContain('handleReloadHelios');
    expect(src).toContain('seedDemoPack');
  });
});

// ── 4. api.js exports getDemoManifest ─────────────────────────────────────

describe('API layer: getDemoManifest', () => {
  const src = readFileSync(resolve(__dirname, '..', '..', 'services', 'api.js'), 'utf8');

  it('exports getDemoManifest function', () => {
    expect(src).toMatch(/export\s+const\s+getDemoManifest/);
  });

  it('calls /demo/manifest endpoint', () => {
    expect(src).toContain('/demo/manifest');
  });
});
