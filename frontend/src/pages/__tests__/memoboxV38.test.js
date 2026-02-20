/**
 * PROMEOS V38 — Memobox / Proof-link tests
 *
 * 1. proofLinkModel unit tests (buildProofLink, hasProofData, getProofLabel, constants)
 * 2. Source guards: ImpactDecisionPanel, NavRegistry, api.js, KBExplorerPage
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

import {
  buildProofLink,
  hasProofData,
  getProofLabel,
  DOC_STATUS_LABELS,
  DOC_STATUS_BADGE,
} from '../../models/proofLinkModel.js';

// ── Helper: read source file ────────────────────────────────────────────────
const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. buildProofLink
// ══════════════════════════════════════════════════════════════════════════════

describe('buildProofLink', () => {
  it('returns /kb for null lever', () => {
    expect(buildProofLink(null)).toBe('/kb');
  });

  it('returns /kb for undefined lever', () => {
    expect(buildProofLink(undefined)).toBe('/kb');
  });

  it('sets context=proof', () => {
    const url = buildProofLink({ type: 'conformite' });
    expect(url).toContain('context=proof');
  });

  it('maps conformite type to reglementaire domain', () => {
    const url = buildProofLink({ type: 'conformite' });
    expect(url).toContain('domain=reglementaire');
  });

  it('maps facturation type to facturation domain', () => {
    const url = buildProofLink({ type: 'facturation' });
    expect(url).toContain('domain=facturation');
  });

  it('maps achat type to facturation domain', () => {
    const url = buildProofLink({ type: 'achat' });
    expect(url).toContain('domain=facturation');
  });

  it('maps optimisation type to usages domain', () => {
    const url = buildProofLink({ type: 'optimisation' });
    expect(url).toContain('domain=usages');
  });

  it('omits domain for data_activation (null mapping)', () => {
    const url = buildProofLink({ type: 'data_activation' });
    expect(url).not.toContain('domain=');
  });

  it('includes actionKey as lever param', () => {
    const url = buildProofLink({ type: 'conformite', actionKey: 'dpe_check' });
    expect(url).toContain('lever=dpe_check');
  });

  it('includes proofHint truncated to 100 chars', () => {
    const hint = 'A'.repeat(150);
    const url = buildProofLink({ type: 'conformite', proofHint: hint });
    const params = new URLSearchParams(url.split('?')[1]);
    expect(params.get('hint')).toHaveLength(100);
  });

  it('returns a path starting with /kb?', () => {
    const url = buildProofLink({ type: 'conformite' });
    expect(url).toMatch(/^\/kb\?/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. hasProofData
// ══════════════════════════════════════════════════════════════════════════════

describe('hasProofData', () => {
  it('returns false for null', () => {
    expect(hasProofData(null)).toBe(false);
  });

  it('returns false for undefined', () => {
    expect(hasProofData(undefined)).toBe(false);
  });

  it('returns false for lever without proof fields', () => {
    expect(hasProofData({ type: 'conformite' })).toBe(false);
  });

  it('returns true when proofHint is present', () => {
    expect(hasProofData({ proofHint: 'DPE requis' })).toBe(true);
  });

  it('returns true when proofLinks is non-empty', () => {
    expect(hasProofData({ proofLinks: ['doc1'] })).toBe(true);
  });

  it('returns false when proofLinks is empty array', () => {
    expect(hasProofData({ proofLinks: [] })).toBe(false);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. getProofLabel
// ══════════════════════════════════════════════════════════════════════════════

describe('getProofLabel', () => {
  it('returns empty string for null', () => {
    expect(getProofLabel(null)).toBe('');
  });

  it('returns proofHint when present', () => {
    expect(getProofLabel({ proofHint: 'Attestation DPE' })).toBe('Attestation DPE');
  });

  it('returns count string for proofLinks', () => {
    expect(getProofLabel({ proofLinks: ['a', 'b'] })).toContain('2 preuves');
  });

  it('uses singular for single proofLink', () => {
    expect(getProofLabel({ proofLinks: ['a'] })).toContain('1 preuve');
    expect(getProofLabel({ proofLinks: ['a'] })).not.toContain('preuves');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. DOC_STATUS_LABELS
// ══════════════════════════════════════════════════════════════════════════════

describe('DOC_STATUS_LABELS', () => {
  it('has all 5 lifecycle states', () => {
    const keys = Object.keys(DOC_STATUS_LABELS);
    expect(keys).toContain('draft');
    expect(keys).toContain('review');
    expect(keys).toContain('validated');
    expect(keys).toContain('decisional');
    expect(keys).toContain('deprecated');
    expect(keys).toHaveLength(5);
  });

  it('values are FR strings', () => {
    expect(DOC_STATUS_LABELS.draft).toBe('Brouillon');
    expect(DOC_STATUS_LABELS.validated).toMatch(/Valid/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 5. DOC_STATUS_BADGE
// ══════════════════════════════════════════════════════════════════════════════

describe('DOC_STATUS_BADGE', () => {
  it('maps all 5 states to badge variants', () => {
    expect(Object.keys(DOC_STATUS_BADGE)).toHaveLength(5);
    expect(DOC_STATUS_BADGE.validated).toBe('ok');
    expect(DOC_STATUS_BADGE.draft).toBe('neutral');
    expect(DOC_STATUS_BADGE.decisional).toBe('crit');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 6. GUARD: proofLinkModel is pure (no React, no API)
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD proofLinkModel purity', () => {
  const source = src('models/proofLinkModel.js');

  it('does not import React', () => {
    expect(source).not.toMatch(/from\s+['"]react['"]/);
  });

  it('does not import react-router-dom', () => {
    expect(source).not.toMatch(/from\s+['"]react-router-dom['"]/);
  });

  it('does not import api.js', () => {
    expect(source).not.toMatch(/from\s+['"]\.\.\/services\/api['"]/);
  });

  it('exports buildProofLink', () => {
    expect(source).toMatch(/export\s+function\s+buildProofLink/);
  });

  it('exports hasProofData', () => {
    expect(source).toMatch(/export\s+function\s+hasProofData/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 7. GUARD: ImpactDecisionPanel uses proofLinkModel
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD ImpactDecisionPanel proof integration', () => {
  const source = src('pages/cockpit/ImpactDecisionPanel.jsx');

  it('imports from proofLinkModel', () => {
    expect(source).toMatch(/from\s+['"].*proofLinkModel['"]/);
  });

  it('imports hasProofData', () => {
    expect(source).toMatch(/hasProofData/);
  });

  it('imports buildProofLink', () => {
    expect(source).toMatch(/buildProofLink/);
  });

  it('contains proof CTA (Deposer)', () => {
    expect(source).toMatch(/D(?:é|\\u00e9|e)poser/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 8. GUARD: NavRegistry shows Memobox
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD NavRegistry Memobox', () => {
  const source = src('layout/NavRegistry.js');

  it('has Memobox label for /kb entry', () => {
    expect(source).toMatch(/M(?:é|\\u00e9|e)mobox/);
  });

  it('includes memobox keyword', () => {
    expect(source).toMatch(/['"]memobox['"]/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 9. GUARD: api.js has Memobox functions
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD api.js Memobox endpoints', () => {
  const source = src('services/api.js');

  it('exports uploadKBDoc', () => {
    expect(source).toMatch(/export\s+(const|function)\s+uploadKBDoc/);
  });

  it('exports changeKBDocStatus', () => {
    expect(source).toMatch(/export\s+(const|function)\s+changeKBDocStatus/);
  });

  it('exports getKBDocs', () => {
    expect(source).toMatch(/export\s+(const|function)\s+getKBDocs/);
  });

  it('uploadKBDoc uses FormData', () => {
    expect(source).toMatch(/new\s+FormData/);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 10. GUARD: KBExplorerPage — Memobox rename + deep-link + lifecycle
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD KBExplorerPage Memobox', () => {
  const source = src('pages/KBExplorerPage.jsx');

  it('title contains Memobox', () => {
    expect(source).toMatch(/M(?:é|\\u00e9|e)mobox/);
  });

  it('imports useSearchParams for deep-linking', () => {
    expect(source).toMatch(/useSearchParams/);
  });

  it('imports DOC_STATUS_LABELS from proofLinkModel', () => {
    expect(source).toMatch(/DOC_STATUS_LABELS/);
  });

  it('imports uploadKBDoc from api', () => {
    expect(source).toMatch(/uploadKBDoc/);
  });
});
