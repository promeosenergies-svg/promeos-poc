/**
 * M2-6.B.frontend — Tests du helper money.js (CFO mode).
 *
 * Sémantique distincte de `utils/format.js::fmtEur` (qui retourne `'—'` pour 0).
 * Ici 0 est une mesure valide → `'0 €'`. NULL → `'—'`.
 *
 * NB : `toLocaleString('fr-FR')` insère un narrow no-break space U+202F entre
 * milliers (pas un espace régulier U+0020). Les assertions utilisent NBSP pour
 * matcher la vraie sortie navigateur.
 */
import { describe, expect, test } from 'vitest';

import { formatEuros, formatEurosColumn } from '../money';

// U+202F — narrow no-break space (séparateur milliers FR)
const NBSP = ' ';

describe('formatEuros — mode "full"', () => {
  test('3200 → "3 200 €" (NBSP milliers)', () => {
    expect(formatEuros(3200, 'full')).toBe(`3${NBSP}200 €`);
  });
  test('47500 → "47 500 €"', () => {
    expect(formatEuros(47500, 'full')).toBe(`47${NBSP}500 €`);
  });
  test('1800 → "1 800 €"', () => {
    expect(formatEuros(1800, 'full')).toBe(`1${NBSP}800 €`);
  });
  test('null → "—"', () => {
    expect(formatEuros(null, 'full')).toBe('—');
  });
  test('undefined → "—"', () => {
    expect(formatEuros(undefined, 'full')).toBe('—');
  });
  test('0 → "0 €" (zéro est valide, ≠ NULL)', () => {
    expect(formatEuros(0, 'full')).toBe('0 €');
  });
  test('NaN → "—"', () => {
    expect(formatEuros(NaN, 'full')).toBe('—');
  });
  test('string numérique "7500.00" → "7 500 €"', () => {
    expect(formatEuros('7500.00', 'full')).toBe(`7${NBSP}500 €`);
  });
});

describe('formatEuros — mode "compact"', () => {
  test('12500 → "12,5 k€"', () => {
    expect(formatEuros(12500, 'compact')).toBe('12,5 k€');
  });
  test('35000 → "35 k€" (entier, sans décimale)', () => {
    expect(formatEuros(35000, 'compact')).toBe('35 k€');
  });
  test('47500 → "47,5 k€"', () => {
    expect(formatEuros(47500, 'compact')).toBe('47,5 k€');
  });
  test('999 → "999 €" (sous seuil k, retombe en full)', () => {
    expect(formatEuros(999, 'compact')).toBe('999 €');
  });
  test('1000 → "1 k€"', () => {
    expect(formatEuros(1000, 'compact')).toBe('1 k€');
  });
  test('null → "—"', () => {
    expect(formatEuros(null, 'compact')).toBe('—');
  });
  test('0 → "0 €" (mode compact, 0 reste full <1000)', () => {
    expect(formatEuros(0, 'compact')).toBe('0 €');
  });
});

describe('formatEurosColumn — bascule auto seuil 10 000', () => {
  test('3200 → "3 200 €" (full, < 10k)', () => {
    expect(formatEurosColumn(3200)).toBe(`3${NBSP}200 €`);
  });
  test('7500 → "7 500 €" (full, < 10k)', () => {
    expect(formatEurosColumn(7500)).toBe(`7${NBSP}500 €`);
  });
  test('9999 → "9 999 €" (full, juste sous 10k)', () => {
    expect(formatEurosColumn(9999)).toBe(`9${NBSP}999 €`);
  });
  test('10000 → "10 k€" (compact, seuil pile)', () => {
    expect(formatEurosColumn(10000)).toBe('10 k€');
  });
  test('35000 → "35 k€" (compact, ≥ 10k)', () => {
    expect(formatEurosColumn(35000)).toBe('35 k€');
  });
  test('null → "—"', () => {
    expect(formatEurosColumn(null)).toBe('—');
  });
});
