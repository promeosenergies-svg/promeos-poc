/**
 * grammar/hub/HubPageFooter — source-guards Vitest (Sprint Grammaire v1.2)
 *
 * Tests pure-grep : alias SolPageFooter, pass-through props, zero duplication.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../HubPageFooter.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/HubPageFooter', () => {
  it('re-export de SolPageFooter (alias — zero logique propre)', () => {
    expect(read()).toContain("export { default } from '../../../ui/sol/SolPageFooter'");
  });

  it('mention doctrine L11.5 en JSDoc', () => {
    expect(read()).toContain('L11.5');
  });

  it('mention des props pass-through (source, confidence, updatedAt, methodologyUrl)', () => {
    const src = read();
    expect(src).toContain('source');
    expect(src).toContain('confidence');
    expect(src).toContain('updatedAt');
    expect(src).toContain('methodologyUrl');
  });

  it('zero logique metier — fichier ne contient pas de useState ou useEffect', () => {
    const src = read();
    expect(src).not.toContain('useState');
    expect(src).not.toContain('useEffect');
    expect(src).not.toContain('import React');
  });

  it('JSDoc PROMEOS present (marque correcte — jamais Promeos/Promeos)', () => {
    expect(read()).toContain('PROMEOS');
  });
});
