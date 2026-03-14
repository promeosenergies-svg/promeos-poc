/**
 * PROMEOS — V1.4+V1.5 Questionnaire x Conformite source-guard tests
 * Verifie que les reponses questionnaire impactent l'affichage conformite.
 * V1.5: q_gtb → BACS, q_operat → DT
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

  // ── V1.5 additions ──

  it('has BACS_GTB_RULES with GTB answers', () => {
    expect(src).toContain('BACS_GTB_RULES');
    expect(src).toContain('oui_centralisee');
    expect(src).toContain('oui_partielle');
  });

  it('has DT_OPERAT_RULES with OPERAT answers', () => {
    expect(src).toContain('DT_OPERAT_RULES');
    expect(src).toContain('oui_a_jour');
    expect(src).toContain('oui_retard');
    expect(src).toContain('non_concerne');
  });

  it('has prudent GTB labels', () => {
    expect(src).toContain('GTB centralis');
    expect(src).toContain('Sans GTB');
    expect(src).toContain('BACS');
  });

  it('has prudent OPERAT labels', () => {
    expect(src).toContain('OPERAT');
    expect(src).toContain('jour');
    expect(src).toContain('retard');
  });

  it('reads q_gtb and q_operat from answers', () => {
    expect(src).toContain('answers.q_gtb');
    expect(src).toContain('answers.q_operat');
  });

  it('applies BACS_GTB_RULES only to bacs obligations', () => {
    expect(src).toMatch(/code\.includes\('bacs'\).*BACS_GTB_RULES/s);
  });

  it('applies DT_OPERAT_RULES only to tertiaire obligations', () => {
    expect(src).toMatch(/code\.includes\('tertiaire'\).*DT_OPERAT_RULES/s);
  });

  it('clamps boost to [-3, +3]', () => {
    expect(src).toMatch(/Math\.max\(-3.*Math\.min\(3/);
  });

  it('never masks obligations (no filter/hide logic in code)', () => {
    // The function body should not filter/remove obligations — only tag/boost
    expect(src).not.toMatch(/obligations\.filter\(/);
    expect(src).not.toMatch(/\.splice\(/);
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
