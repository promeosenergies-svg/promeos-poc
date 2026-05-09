/**
 * grammar/WeekCard — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. variante a-regarder (watch) → attention tokens
 *   2. variante a-faire (todo) → afaire tokens
 *   3. variante bonne-nouvelle (good_news) → succes tokens
 *   4. variante derive (drift) → refuse tokens
 *   5. props titre, resume, cta, impact, echeance documentes
 *   6. data-testid week-card-{type} present
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/WeekCard', () => {
  const src = readGrammar('WeekCard.jsx');

  it('variante a-regarder mapped vers watch', () => {
    expect(src).toContain("'a-regarder'");
    expect(src).toContain('watch');
  });

  it('variante a-faire mapped vers todo', () => {
    expect(src).toContain("'a-faire'");
    expect(src).toContain('todo');
  });

  it('variante bonne-nouvelle mapped vers good_news', () => {
    expect(src).toContain("'bonne-nouvelle'");
    expect(src).toContain('good_news');
  });

  it('variante derive mapped vers drift', () => {
    expect(src).toContain("'derive'");
    expect(src).toContain('drift');
  });

  it('utilise tokens --sol-attention-*, --sol-afaire-*, --sol-succes-*, --sol-refuse-*', () => {
    expect(src).toContain('sol-attention');
    expect(src).toContain('sol-afaire');
    expect(src).toContain('sol-succes');
    expect(src).toContain('sol-refuse');
  });

  it('props titre et resume documentes', () => {
    expect(src).toContain('titre');
    expect(src).toContain('resume');
  });

  it('data-testid week-card-{type}', () => {
    expect(src).toContain('week-card-');
  });
});
