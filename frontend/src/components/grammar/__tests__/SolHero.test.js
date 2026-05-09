/**
 * grammar/SolHero — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. kicker prop documentee
 *   2. titre prop documentee
 *   3. narrative prop documentee
 *   4. delegue vers SolNarrative (pas de duplication logique)
 *   5. data-testid "sol-hero" present pour tests E2E
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/SolHero', () => {
  const src = readGrammar('SolHero.jsx');

  it('documente la prop kicker', () => {
    expect(src).toContain('kicker');
  });

  it('documente la prop titre', () => {
    expect(src).toContain('titre');
  });

  it('documente la prop narrative', () => {
    expect(src).toContain('narrative');
  });

  it('delegue vers SolNarrative (pas de reimplementation)', () => {
    expect(src).toContain('SolNarrative');
  });

  it('expose data-testid "sol-hero" pour Playwright', () => {
    expect(src).toContain('data-testid="sol-hero"');
  });
});
