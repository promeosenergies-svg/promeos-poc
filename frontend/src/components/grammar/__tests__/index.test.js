/**
 * grammar/index.js — source-guards namespace exports.
 *
 * Audit Phase 3.0 P2 (simplify 09/05) : SolHero / KPISol / WeekCard retirés
 * du namespace (zéro consommateur, dette pure). Le namespace ne re-exporte
 * désormais que les 3 primitifs réellement consommés par les vues livrées
 * Lego (CockpitPilotage, ActionCenterSlideOver, ConformitePage).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/index.js — exports des 3 primitifs canoniques', () => {
  const src = readGrammar('index.js');

  it('exporte SolPageFooter (Loi L6)', () => {
    expect(src).toContain('SolPageFooter');
  });

  it('exporte Term (doctrine §6.4)', () => {
    expect(src).toContain('Term');
  });

  it('exporte DecisionEvidenceCard (doctrine §5.6 Loi L9)', () => {
    expect(src).toContain('DecisionEvidenceCard');
  });

  it('ne ré-exporte PAS SolHero / KPISol / WeekCard (retirés Phase 3.0 simplify)', () => {
    expect(src).not.toMatch(/from\s+['"]\.\/SolHero['"]/);
    expect(src).not.toMatch(/from\s+['"]\.\/KPISol['"]/);
    expect(src).not.toMatch(/from\s+['"]\.\/WeekCard['"]/);
  });
});
