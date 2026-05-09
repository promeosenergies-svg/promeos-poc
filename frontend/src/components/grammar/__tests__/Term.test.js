/**
 * grammar/Term — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. acronyme connu : rendu via SolTooltip (inline-tooltip)
 *   2. acronyme inconnu : fallback brut + console.warn
 *   3. variant narrative : texte narratif expose
 *   4. variant short : forme courte seulement
 *   5. consomme utils/acronyms.js et domain/glossary.js
 *   6. documente le contrat prop acronyme + variant
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/Term', () => {
  const src = readGrammar('Term.jsx');

  it('importe SolTooltip pour le variant inline-tooltip', () => {
    expect(src).toContain('SolTooltip');
  });

  it('importe utils/acronyms.js (isKnownAcronym + acronymTooltip)', () => {
    expect(src).toContain('isKnownAcronym');
    expect(src).toContain('acronymTooltip');
  });

  it('importe domain/glossary.js (GLOSSARY)', () => {
    expect(src).toContain('GLOSSARY');
  });

  it('console.warn pour acronyme inconnu', () => {
    expect(src).toContain('console.warn');
  });

  it('variant narrative rendu', () => {
    expect(src).toContain("'narrative'");
  });

  it('variant short rendu', () => {
    expect(src).toContain("'short'");
  });

  it('variant inline-tooltip par defaut', () => {
    expect(src).toContain('inline-tooltip');
  });

  it('data-testid pour les 3 etats (term-inline, term-narrative, term-short, term-unknown)', () => {
    expect(src).toContain('term-inline');
    expect(src).toContain('term-narrative');
    expect(src).toContain('term-short');
    expect(src).toContain('term-unknown');
  });
});
