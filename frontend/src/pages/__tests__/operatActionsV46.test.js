/**
 * PROMEOS V46 — OPERAT Actions Bridge (source guards)
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const src = (rel) =>
  fs.readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf-8');

// ══════════════════════════════════════════════════════════════════════════════
// 1. operatActionModel exports
// ══════════════════════════════════════════════════════════════════════════════

describe('operatActionModel exports', () => {
  const model = src('models/operatActionModel.js');

  it('exports buildOperatActionKey', () => {
    expect(model).toContain('export function buildOperatActionKey');
  });

  it('exports buildOperatActionPayload', () => {
    expect(model).toContain('export function buildOperatActionPayload');
  });

  it('exports buildOperatActionDeepLink', () => {
    expect(model).toContain('export function buildOperatActionDeepLink');
  });

  it('exports OPERAT_DUE_DAYS', () => {
    expect(model).toContain('export const OPERAT_DUE_DAYS');
  });

  it('uses source_type insight', () => {
    expect(model).toContain("'insight'");
  });

  it('generates idempotency_key with operat prefix', () => {
    expect(model).toContain('operat-');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 2. EFA Detail Page — V46 action bridge
// ══════════════════════════════════════════════════════════════════════════════

describe('EFA Detail Page has V46 action bridge', () => {
  const detail = src('pages/tertiaire/TertiaireEfaDetailPage.jsx');

  it('imports createAction from api', () => {
    expect(detail).toContain('createAction');
  });

  it('imports buildOperatActionPayload', () => {
    expect(detail).toContain('buildOperatActionPayload');
  });

  it('imports buildOperatActionDeepLink', () => {
    expect(detail).toContain('buildOperatActionDeepLink');
  });

  it('has btn-create-action per issue', () => {
    expect(detail).toContain('btn-create-action');
    expect(detail).toContain('Créer une action');
  });

  it('has action-feedback toast', () => {
    expect(detail).toContain('action-feedback');
  });

  it('handles dedup (existing action)', () => {
    expect(detail).toContain("'existing'");
    expect(detail).toContain('Action déjà existante');
  });

  it('has operat-actions-bloc section', () => {
    expect(detail).toContain('operat-actions-bloc');
  });

  it('has btn-view-action-plan CTA', () => {
    expect(detail).toContain('btn-view-action-plan');
    expect(detail).toContain('Voir dans le plan');
  });

  it('links to /actions with source=operat filter', () => {
    expect(detail).toContain('source=operat');
  });

  it('shows "Ouvrir le plan d\'actions" after creation', () => {
    expect(detail).toContain('Ouvrir le plan');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 3. Anomalies Page — V46 action bridge
// ══════════════════════════════════════════════════════════════════════════════

describe('Anomalies Page has V46 action bridge', () => {
  const anomalies = src('pages/tertiaire/TertiaireAnomaliesPage.jsx');

  it('imports createAction from api', () => {
    expect(anomalies).toContain('createAction');
  });

  it('imports buildOperatActionPayload', () => {
    expect(anomalies).toContain('buildOperatActionPayload');
  });

  it('has btn-create-action per issue', () => {
    expect(anomalies).toContain('btn-create-action');
    expect(anomalies).toContain('Créer une action');
  });

  it('has action-feedback toast', () => {
    expect(anomalies).toContain('action-feedback');
  });

  it('handles dedup (existing action)', () => {
    expect(anomalies).toContain("'existing'");
  });

  it('has Plus icon import', () => {
    expect(anomalies).toContain('Plus');
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// 4. API service — createAction
// ══════════════════════════════════════════════════════════════════════════════

describe('API service has createAction', () => {
  const api = src('services/api.js');

  it('exports createAction function', () => {
    expect(api).toContain('createAction');
  });

  it('calls POST /actions', () => {
    expect(api).toContain("'/actions'");
  });
});
