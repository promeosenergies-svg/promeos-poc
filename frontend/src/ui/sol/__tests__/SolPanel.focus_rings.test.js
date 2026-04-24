/**
 * SolPanel + SolRail focus rings — Sprint 1 Vague A phase A9
 * + refacto Sprint 1 Vague B : constante `FOCUS_RING_SOL` partagée.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

describe('FOCUS_RING_SOL constant (Vague B refacto)', () => {
  const src = readFileSync(join(__dirname, '..', 'focusRing.js'), 'utf-8');

  it('is exported from focusRing.js', () => {
    expect(src).toMatch(/export const FOCUS_RING_SOL/);
  });

  it('contains focus-visible:outline-none', () => {
    expect(src).toMatch(/focus-visible:outline-none/);
  });

  it('contains focus-visible:ring-2', () => {
    expect(src).toMatch(/focus-visible:ring-2/);
  });

  it('contains focus-visible:ring-blue-500', () => {
    expect(src).toMatch(/focus-visible:ring-blue-500/);
  });

  it('contains focus-visible:ring-offset-1', () => {
    expect(src).toMatch(/focus-visible:ring-offset-1/);
  });
});

describe('SolPanel focus rings (A9 + Vague B refacto)', () => {
  const src = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');

  it('imports FOCUS_RING_SOL from focusRing module', () => {
    expect(src).toMatch(/import\s*\{\s*FOCUS_RING_SOL\s*\}\s*from\s*['"]\.\/focusRing['"]/);
  });

  it('applies FOCUS_RING_SOL on panel items className', () => {
    expect(src).toMatch(/\$\{FOCUS_RING_SOL\}/);
  });

  it('no duplicated literal focus-visible:ring-blue-500 outside constant', () => {
    // Seules les occurrences légitimes sont via la constante ou dans les
    // commentaires — zéro string literal focus-visible dans le JSX.
    const literals = src.match(/'[^']*focus-visible:ring-blue-500[^']*'/g) || [];
    const doubleLiterals = src.match(/"[^"]*focus-visible:ring-blue-500[^"]*"/g) || [];
    expect(literals.length + doubleLiterals.length).toBe(0);
  });
});

describe('SolRail focus rings (A9 + Vague B refacto)', () => {
  const src = readFileSync(join(__dirname, '..', 'SolRail.jsx'), 'utf-8');

  it('imports FOCUS_RING_SOL', () => {
    expect(src).toMatch(/import\s*\{\s*FOCUS_RING_SOL\s*\}\s*from\s*['"]\.\/focusRing['"]/);
  });

  it('applies FOCUS_RING_SOL on rail icon className', () => {
    expect(src).toMatch(/\$\{FOCUS_RING_SOL\}/);
  });

  it('no duplicated literal focus-visible outside constant', () => {
    const literals = src.match(/'[^']*focus-visible:ring-blue-500[^']*'/g) || [];
    const doubleLiterals = src.match(/"[^"]*focus-visible:ring-blue-500[^"]*"/g) || [];
    expect(literals.length + doubleLiterals.length).toBe(0);
  });
});

describe('AperSol focus rings (Vague B refacto)', () => {
  const src = readFileSync(join(__dirname, '..', '..', '..', 'pages', 'AperSol.jsx'), 'utf-8');

  it('imports FOCUS_RING_SOL from ui/sol/focusRing', () => {
    expect(src).toMatch(
      /import\s*\{\s*FOCUS_RING_SOL\s*\}\s*from\s*['"]\.\.\/ui\/sol\/focusRing['"]/
    );
  });

  it('Reset button uses FOCUS_RING_SOL (not literal duplication)', () => {
    expect(src).toMatch(/className=\{FOCUS_RING_SOL\}/);
  });
});
