/**
 * grammar/index.js — source-guards namespace exports (Phase 1.2 grammaire Sol).
 *
 * Verifie que les 6 primitifs sont bien exportes depuis l'index canonique.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/index.js — exports des 6 primitifs', () => {
  const src = readGrammar('index.js');

  it('exporte SolPageFooter', () => {
    expect(src).toContain('SolPageFooter');
  });

  it('exporte SolHero', () => {
    expect(src).toContain('SolHero');
  });

  it('exporte KPISol', () => {
    expect(src).toContain('KPISol');
  });

  it('exporte Term', () => {
    expect(src).toContain('Term');
  });

  it('exporte WeekCard', () => {
    expect(src).toContain('WeekCard');
  });

  it('exporte DecisionEvidenceCard', () => {
    expect(src).toContain('DecisionEvidenceCard');
  });
});
