/**
 * grammar/DecisionEvidenceCard — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. grille evidence data-testid "decision-evidence-grid" presente
 *   2. validation 4-8 cellules (throw si hors plage — doctrine §5.6 L9)
 *   3. severity → tokens CSS correctement mappe
 *   4. methodologyRef data-testid "decision-evidence-methodology"
 *   5. rang affiche en font-mono tabular (data-testid "decision-evidence-rang")
 *   6. category data-testid "decision-evidence-category"
 *   7. JSDoc contrat complet (@param rang, category, scope, severity, titre, lead, evidence, primaryCta, methodologyRef)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/DecisionEvidenceCard', () => {
  const src = readGrammar('DecisionEvidenceCard.jsx');

  it('grille evidence avec data-testid decision-evidence-grid', () => {
    expect(src).toContain('decision-evidence-grid');
  });

  it('validation runtime : evidence.length doit être dans [4, 8] (doctrine §5.6)', () => {
    expect(src).toContain('4-8 cellules evidence');
    // Audit Phase 1.7 P1 : ancien `throw new Error` remplacé par
    // validation safe qui retourne null + console.error (évite crash page).
    expect(src).toContain('validateEvidence');
    expect(src).toContain('return null');
  });

  it('severity → tokens CSS (sol-refuse, sol-attention, sol-succes)', () => {
    expect(src).toContain('sol-refuse');
    expect(src).toContain('sol-attention');
    expect(src).toContain('sol-succes');
  });

  it('methodologyRef avec data-testid decision-evidence-methodology', () => {
    expect(src).toContain('decision-evidence-methodology');
  });

  it('rang affiche avec data-testid decision-evidence-rang', () => {
    expect(src).toContain('decision-evidence-rang');
  });

  it('category avec data-testid decision-evidence-category', () => {
    expect(src).toContain('decision-evidence-category');
  });

  it('JSDoc contrat : rang, category, scope, severity, titre, lead, evidence, primaryCta', () => {
    expect(src).toContain('rang');
    expect(src).toContain('category');
    expect(src).toContain('scope');
    expect(src).toContain('severity');
    expect(src).toContain('titre');
    expect(src).toContain('lead');
    expect(src).toContain('evidence');
    expect(src).toContain('primaryCta');
  });

  it('tonalite par defaut neutral (calme — produit murmure la decision)', () => {
    expect(src).toContain("severity = 'neutral'");
  });
});
