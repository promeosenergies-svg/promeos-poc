/**
 * grammar/hub/HubHighlight — source-guards Vitest (Sprint Grammaire v1.2)
 *
 * Tests pure-grep : contrat ligne action-card compacte L11.3.
 * Verbes d'invitation, tokens severity, data-attributes.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../HubHighlight.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/HubHighlight', () => {
  it('data-component HubHighlight + data-severity + data-rang (source-guards)', () => {
    const src = read();
    expect(src).toContain('data-component="HubHighlight"');
    expect(src).toContain('data-severity={severity}');
    expect(src).toContain('data-rang={rang}');
  });

  it('data-invitation sur le verbe (test L11.3)', () => {
    expect(read()).toContain('data-invitation={invitation?.verb}');
  });

  it("liste blanche verbes d'invitation L11.3 complete (12 verbes)", () => {
    const src = read();
    expect(src).toContain("'voir'");
    expect(src).toContain("'lancer'");
    expect(src).toContain("'comparer'");
    expect(src).toContain("'auditer'");
    expect(src).toContain("'ouvrir'");
    expect(src).toContain("'vérifier'");
    expect(src).toContain("'simuler'");
    expect(src).toContain("'arbitrer'");
    expect(src).toContain("'programmer'");
    expect(src).toContain("'activer'");
    expect(src).toContain("'préparer'");
    expect(src).toContain("'contester'");
  });

  it('validation verb console.error (jamais throw)', () => {
    const src = read();
    expect(src).toContain('INVITATION_VERBS');
    expect(src).toContain('console.error');
    expect(src).not.toContain('throw new Error');
  });

  it('bordure laterale gauche coloree par severity (sol-refuse-line / sol-attention-line / sol-succes-line)', () => {
    const src = read();
    expect(src).toContain('sol-refuse-line');
    expect(src).toContain('sol-attention-line');
    expect(src).toContain('sol-succes-line');
  });

  it('rang affiche badge P{rang} en font-mono', () => {
    const src = read();
    expect(src).toContain('P{rang}');
    expect(src).toContain('font-mono');
  });

  it('grille 4 colonnes : rang | corps | impact | CTA', () => {
    expect(read()).toContain('36px 1fr auto auto');
  });
});
