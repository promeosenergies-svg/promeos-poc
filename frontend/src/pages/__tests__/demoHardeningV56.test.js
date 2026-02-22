/**
 * PROMEOS — V56: Demo Orchestration Hardening
 * Source-level guards for null-safety + HELIOS-only visibility.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const readPage = (name) => readFileSync(resolve(__dirname, '..', name), 'utf8');
const readComponent = (name) => readFileSync(resolve(__dirname, '..', '..', 'components', name), 'utf8');

// ── 1. ConformitePage null-safety ──────────────────────────

describe('ConformitePage null-safety (V56)', () => {
  const src = readPage('ConformitePage.jsx');

  it('uses org?.id (not org.id) in buildScopeParams', () => {
    expect(src).toContain('orgId: org?.id');
  });

  it('uses org?.id in useCallback dependency', () => {
    expect(src).toContain('org?.id, scope.portefeuilleId');
  });

  it('uses org?.id in recomputeComplianceRules call', () => {
    expect(src).toContain('recomputeComplianceRules(org?.id)');
  });

  it('uses org?.nom with fallback in error PageShell', () => {
    expect(src).toMatch(/org\?\.nom\s*\|\|\s*'Organisation'/);
  });

  it('uses org?.id in DevScopeBadge', () => {
    expect(src).toContain('orgId: org?.id, portefeuilleId: scope.portefeuilleId, siteId: scope.siteId');
  });

  it('has null-safe computeScopeLabel', () => {
    expect(src).toContain("org?.nom || 'Organisation'");
    expect(src).toContain('scopedSites?.[0]');
    expect(src).toContain('scopedSites?.length || 0');
  });
});

// ── 2. Cockpit null-safety ─────────────────────────────────

describe('Cockpit null-safety (V56)', () => {
  const src = readPage('Cockpit.jsx');

  it('uses org?.nom in scopeLabel', () => {
    expect(src).toContain("org?.nom || 'Organisation'");
  });

  it('does NOT have bare org.nom in scopeLabel', () => {
    // Ensure no unguarded org.nom in the scopeLabel computation
    const lines = src.split('\n');
    const scopeLabelLines = lines.filter(l => l.includes('scopeLabel') && l.includes('org.nom'));
    expect(scopeLabelLines.length).toBe(0);
  });
});

// ── 3. Site360 null-safety ─────────────────────────────────

describe('Site360 toLocaleString null-safety (V56)', () => {
  const src = readPage('Site360.jsx');

  it('guards risque_eur.toLocaleString with || 0', () => {
    expect(src).toContain('(site.risque_eur || 0).toLocaleString()');
  });

  it('guards surface_m2.toLocaleString with || 0', () => {
    expect(src).toContain('(site.surface_m2 || 0).toLocaleString()');
  });

  it('guards perte_eur.toLocaleString with || 0', () => {
    expect(src).toContain('(a.perte_eur || 0).toLocaleString()');
  });

  it('guards conso_kwh_an division with || 0', () => {
    expect(src).toContain('(site.conso_kwh_an || 0) / 1000');
  });
});

// ── 4. CommandCenter null-safety ───────────────────────────

describe('CommandCenter toLocaleString null-safety (V56)', () => {
  const src = readPage('CommandCenter.jsx');

  it('guards risque_eur.toLocaleString with || 0', () => {
    expect(src).toContain("(site.risque_eur || 0).toLocaleString('fr-FR')");
  });
});

// ── 5. TopSitesCard null-safety ────────────────────────────

describe('TopSitesCard toLocaleString null-safety (V56)', () => {
  const src = readFileSync(resolve(__dirname, '..', 'cockpit', 'TopSitesCard.jsx'), 'utf8');

  it('guards risque_eur.toLocaleString with || 0', () => {
    expect(src).toContain("(site.risque_eur || 0).toLocaleString('fr-FR')");
  });
});

// ── 6. DemoBanner HELIOS-only ──────────────────────────────

describe('DemoBanner HELIOS-only (V56)', () => {
  const src = readComponent('DemoBanner.jsx');

  it('calls seedDemoPack with helios', () => {
    expect(src).toContain("seedDemoPack('helios'");
  });

  it('has no casino references', () => {
    expect(src).not.toContain('casino');
  });

  it('has no tertiaire references', () => {
    expect(src).not.toContain('tertiaire');
  });
});

// ── 7. ImportPage dynamic packs from backend ───────────────

describe('ImportPage dynamic packs (V56)', () => {
  const src = readPage('ImportPage.jsx');

  it('fetches packs from backend (getDemoPacks)', () => {
    expect(src).toContain('getDemoPacks');
  });

  it('has no hardcoded DEMO_PACKS array', () => {
    expect(src).not.toMatch(/const\s+DEMO_PACKS\s*=/);
  });

  it('auto-selects default pack from backend', () => {
    expect(src).toContain('is_default');
  });
});
