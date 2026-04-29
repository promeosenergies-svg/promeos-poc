/**
 * PROMEOS — Lever Engine source-guard
 *
 * Phase 1.4.c (29/04/2026) : leverEngineModel.js migré vers
 * backend/services/lever_engine_service.py (CLAUDE.md règle d'or
 * zero business logic frontend). Tests logiques supprimés.
 *
 * Source-guard : vérifie que le service backend Python existe
 * et contient les fonctions attendues.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

describe('GUARD: lever_engine_service backend existe (Phase 1.4.c)', () => {
  const servicePath = resolve(
    __dirname,
    '..',
    '..',
    '..',
    '..',
    'backend',
    'services',
    'lever_engine_service.py'
  );

  it('le service Python existe', () => {
    expect(existsSync(servicePath)).toBe(true);
  });

  it('contient compute_actionable_levers', () => {
    const src = readFileSync(servicePath, 'utf8');
    expect(src).toContain('compute_actionable_levers');
  });

  it('contient la dataclass LeverResult', () => {
    const src = readFileSync(servicePath, 'utf8');
    expect(src).toContain('LeverResult');
  });

  it('contient la dataclass Lever', () => {
    const src = readFileSync(servicePath, 'utf8');
    expect(src).toContain('class Lever');
  });

  it('contient ACTIVATION_THRESHOLD', () => {
    const src = readFileSync(servicePath, 'utf8');
    expect(src).toContain('ACTIVATION_THRESHOLD');
  });

  it('contient les helpers signals (is_compliance_available, is_billing_insights_available, is_purchase_available)', () => {
    const src = readFileSync(servicePath, 'utf8');
    expect(src).toContain('is_compliance_available');
    expect(src).toContain('is_billing_insights_available');
    expect(src).toContain('is_purchase_available');
  });

  it('le fichier JS source leverEngineModel.js est supprimé', () => {
    const jsPath = resolve(__dirname, '..', '..', 'models', 'leverEngineModel.js');
    expect(existsSync(jsPath)).toBe(false);
  });
});
