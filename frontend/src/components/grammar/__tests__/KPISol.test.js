/**
 * grammar/KPISol — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. contrat KpiResult descriptor documente (kpi_id, label, value, unit, source, formula_ref, period, status, computed_at, confidence)
 *   2. tooltip "Details {label}" present (aria-label)
 *   3. badge statut mini present (data-testid kpi-sol-status-badge)
 *   4. tabular-nums pour valeur numerique
 *   5. variants hero/inline/compact documentes
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/KPISol', () => {
  const src = readGrammar('KPISol.jsx');

  it('documente le contrat KpiResult (label, value, unit, source, formula_ref, status, confidence)', () => {
    expect(src).toContain('label');
    expect(src).toContain('value');
    expect(src).toContain('unit');
    expect(src).toContain('source');
    expect(src).toContain('formula_ref');
    expect(src).toContain('status');
    expect(src).toContain('confidence');
  });

  it('aria-label "Details {label}" pour le bouton tooltip', () => {
    expect(src).toContain('Details ${label}');
  });

  it('badge statut data-testid kpi-sol-status-badge', () => {
    expect(src).toContain('data-testid="kpi-sol-status-badge"');
  });

  it('tabular-nums sur la valeur numerique', () => {
    expect(src).toContain('tabular-nums');
  });

  it('variants hero, inline, compact documentes', () => {
    expect(src).toContain('hero');
    expect(src).toContain('inline');
    expect(src).toContain('compact');
  });

  it('mapping status : calculated, real, modeled, estimated, demo', () => {
    expect(src).toContain('calculated');
    expect(src).toContain('real');
    expect(src).toContain('modeled');
    expect(src).toContain('estimated');
    expect(src).toContain('demo');
  });
});
