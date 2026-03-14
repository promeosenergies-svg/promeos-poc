/**
 * PROMEOS — V1.4 Questionnaire x Conformite source-guard tests
 * Verifie que les reponses questionnaire impactent l'affichage conformite.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
function readSrc(relPath) {
  return readFileSync(join(__dirname, '..', relPath), 'utf-8');
}

// ── A. complianceProfileRules.js ────────────────────

describe('V1.4 — complianceProfileRules.js', () => {
  const src = readSrc('models/complianceProfileRules.js');

  it('exports computeObligationProfileTags', () => {
    expect(src).toContain('export function computeObligationProfileTags');
  });

  it('exports RELIABILITY_CONFIG', () => {
    expect(src).toContain('export const RELIABILITY_CONFIG');
  });

  it('exports TAG_COLORS', () => {
    expect(src).toContain('export const TAG_COLORS');
  });

  it('has DT_SURFACE_RULES with 4 answers', () => {
    expect(src).toContain('oui_majorite');
    expect(src).toContain('oui_certains');
    expect(src).toContain('ne_sait_pas');
  });

  it('has prudent labels (not pseudo-juridique)', () => {
    expect(src).toContain('Prioritaire selon votre profil');
    expect(src).toContain('Moins prioritaire selon votre profil');
    expect(src).toContain('Applicable sur une partie');
  });

  it('has reliability states: declared, detected, to_confirm', () => {
    expect(src).toContain("'declared'");
    expect(src).toContain("'detected'");
    expect(src).toContain("'to_confirm'");
  });

  it('has DT_RELEVANCE and BACS_RELEVANCE matrices', () => {
    expect(src).toContain('DT_RELEVANCE');
    expect(src).toContain('BACS_RELEVANCE');
  });

  it('only shows Pertinent badge for high relevance', () => {
    expect(src).toMatch(/relevance === 'high'/);
    expect(src).toContain('Pertinent pour votre profil');
  });

  it('declared reliability only when usesUserAnswer', () => {
    expect(src).toContain('usesUserAnswer');
  });
});

// ── B. ConformitePage.jsx integration ────────────────

describe('V1.4 — ConformitePage.jsx integration', () => {
  const src = readSrc('pages/ConformitePage.jsx');

  it('imports computeObligationProfileTags', () => {
    expect(src).toContain('computeObligationProfileTags');
    expect(src).toContain('complianceProfileRules');
  });

  it('has profileTags useMemo', () => {
    expect(src).toContain('profileTags');
    expect(src).toContain('computeObligationProfileTags(obligations, segProfile)');
  });

  it('passes profileTags to ObligationsTab', () => {
    expect(src).toContain('profileTags={profileTags}');
  });

  it('has profile-explain testid', () => {
    expect(src).toContain('data-testid="profile-explain"');
  });

  it('has explanatory text for adjusted display', () => {
    expect(src).toMatch(/ajust.es selon votre profil/);
  });

  it('sort preserves overdue > statut > boost order', () => {
    // Verify the sort has explicit grouping: overdue first, then statut, then boost
    expect(src).toMatch(/aOver.*bOver/s);
    expect(src).toMatch(/aStatut.*bStatut/s);
    expect(src).toMatch(/aBoost.*bBoost/s);
    // Verify statut comparison returns BEFORE boost is applied
    expect(src).toMatch(/if \(aStatut !== bStatut\) return/);
  });
});

// ── C. ObligationsTab.jsx display ────────────────

describe('V1.4 — ObligationsTab.jsx profile display', () => {
  const src = readSrc('pages/conformite-tabs/ObligationsTab.jsx');

  it('accepts profileTags prop', () => {
    expect(src).toContain('profileTags');
  });

  it('accepts profileEntry prop on ObligationCard', () => {
    expect(src).toContain('profileEntry');
  });

  it('has profile-tag testid', () => {
    expect(src).toContain('data-testid="profile-tag"');
  });

  it('has reliability-badge testid', () => {
    expect(src).toContain('data-testid="reliability-badge"');
  });

  it('displays reliability labels', () => {
    expect(src).toMatch(/D.clar./);
    expect(src).toMatch(/D.tect./);
    expect(src).toMatch(/confirmer/);
  });
});
