/**
 * grammar/SolPageFooter — source-guards (Phase 1.2 grammaire Sol).
 *
 * Tests :
 *   1. alias re-export correct vers ui/sol/SolPageFooter
 *   2. contrat props JSDoc present (source, confidence, updatedAt, methodologyUrl)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const GRAMMAR = join(__dirname, '..');
const readGrammar = (rel) => readFileSync(join(GRAMMAR, rel), 'utf-8');

describe('grammar/SolPageFooter', () => {
  const src = readGrammar('SolPageFooter.jsx');

  it('re-exporte depuis ui/sol/SolPageFooter (alias)', () => {
    expect(src).toContain("from '../../ui/sol/SolPageFooter'");
  });

  it('contrat props documente : source, confidence, updatedAt, methodologyUrl', () => {
    expect(src).toContain('source');
    expect(src).toContain('confidence');
    expect(src).toContain('updatedAt');
    expect(src).toContain('methodologyUrl');
  });
});
