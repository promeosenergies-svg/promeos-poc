/**
 * PROMEOS — Lever → Action Mapping V34 tests
 *
 * 1) buildActionPayload: conformite, facturation, optimisation, null
 * 2) buildLeverDeepLink: URL correcte avec params
 * 3) LEVER_ACTION_TEMPLATES: 5 templates FR complets
 * 4) Guard: module pur, pas d'import React/API
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

import {
  buildActionPayload,
  buildLeverDeepLink,
  LEVER_ACTION_TEMPLATES,
} from '../../models/leverActionModel';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const makeLever = (overrides = {}) => ({
  type: 'conformite',
  actionKey: 'lev-conf-nc',
  label: 'Regulariser 2 sites non conformes',
  impactEur: 20000,
  ctaPath: '/conformite',
  ...overrides,
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 1: buildActionPayload — par type
// ══════════════════════════════════════════════════════════════════════════════

describe('buildActionPayload', () => {
  it('genere un payload conformite (non conforme)', () => {
    const payload = buildActionPayload(makeLever());

    expect(payload.title).toBe('Regulariser 2 sites non conformes');
    expect(payload.source_type).toBe('lever_engine');
    expect(payload.source_id).toBe('lev-conf-nc');
    expect(payload.severity).toBe('high');
    expect(payload.estimated_gain_eur).toBe(20000);
    expect(payload.priority).toBe(1);
    expect(payload.idempotency_key).toBe('lever-lev-conf-nc');
    expect(payload.rationale).toContain('non conformes');
    expect(payload.due_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(payload._meta.proof_expected).toContain('conformite');
  });

  it('genere un payload facturation (anomalies)', () => {
    const payload = buildActionPayload(makeLever({
      type: 'facturation',
      actionKey: 'lev-fact-anom',
      label: 'Corriger 5 anomalies facture',
      impactEur: 8000,
    }));

    expect(payload.severity).toBe('high');
    expect(payload.source_id).toBe('lev-fact-anom');
    expect(payload.estimated_gain_eur).toBe(8000);
    expect(payload.rationale).toContain('audit');
    expect(payload._meta.proof_owner).toContain('achat');
  });

  it('genere un payload optimisation', () => {
    const payload = buildActionPayload(makeLever({
      type: 'optimisation',
      actionKey: 'lev-optim-ener',
      label: 'Lancer l\'optimisation energetique',
      impactEur: 5000,
    }));

    expect(payload.severity).toBe('low');
    expect(payload.priority).toBe(3);
    expect(payload.rationale).toContain('optimisation');
  });

  it('retourne null si lever est null ou sans actionKey', () => {
    expect(buildActionPayload(null)).toBeNull();
    expect(buildActionPayload({})).toBeNull();
    expect(buildActionPayload({ type: 'conformite' })).toBeNull();
  });

  it('utilise le template fallback pour une actionKey inconnue', () => {
    const payload = buildActionPayload(makeLever({ actionKey: 'lev-unknown-xyz' }));

    expect(payload).not.toBeNull();
    expect(payload.severity).toBe('medium');
    expect(payload.priority).toBe(3);
    expect(payload._meta.proof_expected).toBe('A qualifier');
  });

  it('due_date est dans le futur (>= 60 jours)', () => {
    const payload = buildActionPayload(makeLever());
    const due = new Date(payload.due_date);
    const now = new Date();
    const diffDays = (due - now) / (1000 * 60 * 60 * 24);
    expect(diffDays).toBeGreaterThanOrEqual(59); // 90 jours pour conf-nc, marge 1j
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 2: buildLeverDeepLink
// ══════════════════════════════════════════════════════════════════════════════

describe('buildLeverDeepLink', () => {
  it('genere un deep-link avec type, key et impact', () => {
    const url = buildLeverDeepLink(makeLever());

    expect(url).toContain('/command-center?');
    expect(url).toContain('filter=leviers');
    expect(url).toContain('type=conformite');
    expect(url).toContain('key=lev-conf-nc');
    expect(url).toContain('impact=20000');
  });

  it('omet impact si null', () => {
    const url = buildLeverDeepLink(makeLever({ impactEur: null }));
    expect(url).not.toContain('impact=');
  });

  it('retourne /command-center si lever null', () => {
    expect(buildLeverDeepLink(null)).toBe('/command-center');
    expect(buildLeverDeepLink({})).toBe('/command-center');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// TEST 3: LEVER_ACTION_TEMPLATES — completude
// ══════════════════════════════════════════════════════════════════════════════

describe('LEVER_ACTION_TEMPLATES', () => {
  const EXPECTED_KEYS = ['lev-conf-nc', 'lev-conf-ar', 'lev-fact-anom', 'lev-fact-loss', 'lev-optim-ener'];

  it('contient les 5 templates attendus', () => {
    for (const key of EXPECTED_KEYS) {
      expect(LEVER_ACTION_TEMPLATES).toHaveProperty(key);
    }
  });

  it.each(EXPECTED_KEYS)('template %s a les champs requis', (key) => {
    const tpl = LEVER_ACTION_TEMPLATES[key];
    expect(tpl.source_type).toBe('lever_engine');
    expect(tpl.severity).toBeTruthy();
    expect(tpl.rationale).toBeInstanceOf(Array);
    expect(tpl.rationale.length).toBeGreaterThanOrEqual(2);
    expect(tpl.proof_expected).toBeTruthy();
    expect(tpl.proof_owner).toBeTruthy();
    expect(tpl.due_days).toBeGreaterThan(0);
    expect(tpl.priority).toBeGreaterThanOrEqual(1);
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// GUARD: module pur
// ══════════════════════════════════════════════════════════════════════════════

describe('GUARD: leverActionModel est un module pur', () => {
  const src = readFileSync(
    resolve(__dirname, '..', '..', 'models', 'leverActionModel.js'),
    'utf8',
  );

  it('n\'importe pas React', () => {
    expect(src).not.toContain("from 'react'");
  });

  it('n\'importe aucun service API', () => {
    expect(src).not.toContain('services/api');
    expect(src).not.toContain('fetch(');
  });

  it('exporte buildActionPayload et buildLeverDeepLink', () => {
    expect(src).toContain('export function buildActionPayload');
    expect(src).toContain('export function buildLeverDeepLink');
  });

  it('ne modifie pas impactDecisionModel (V30 intact)', () => {
    expect(src).not.toContain('computeImpactKpis');
  });
});
