/**
 * PROMEOS — Source guards transversaux : no business calc in frontend.
 *
 * Scanne TOUT src/ (hors __tests__, mocks, node_modules) pour bloquer :
 * 1. 0.0569 (TURPE 7 HPH tarif ≠ facteur CO₂)
 * 2. * 7500 / * 3750 (pénalités réglementaires)
 * 3. pctConf recalculé depuis ratio conformes/total
 * 4. * 0.052 / * 0.227 (CO₂ brut) hors constants.js
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'fs';
import { resolve, join } from 'path';

const SRC_DIR = resolve(__dirname, '..');

function scanProductionFiles(dir) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return results;
  }
  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === '__tests__' || entry.name === 'mocks')
      continue;
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...scanProductionFiles(fullPath));
      continue;
    }
    if (
      !entry.name.endsWith('.js') &&
      !entry.name.endsWith('.jsx') &&
      !entry.name.endsWith('.ts') &&
      !entry.name.endsWith('.tsx')
    )
      continue;
    results.push(fullPath);
  }
  return results;
}

const files = scanProductionFiles(SRC_DIR);
// Cache file contents once — avoids 4× redundant readFileSync per file
const fileCache = new Map(files.map((f) => [f, readFileSync(f, 'utf-8')]));

function findViolations(predicate) {
  const violations = [];
  for (const [f, content] of fileCache) {
    if (predicate(f, content)) {
      violations.push(f.replace(SRC_DIR + '\\', '').replace(SRC_DIR + '/', ''));
    }
  }
  return violations;
}

describe('Source guards — no business calc in frontend', () => {
  it('aucun fichier source ne contient 0.0569 (TURPE ≠ CO₂)', () => {
    expect(findViolations((_f, c) => /0\.0569/.test(c))).toEqual([]);
  });

  it('aucun fichier source ne calcule * 7500 ou * 3750 (pénalités)', () => {
    expect(
      findViolations((f, c) => /\*\s*(7500|3750)/.test(c) && !f.includes('constants'))
    ).toEqual([]);
  });

  it('aucun fichier source ne recalcule pctConf depuis un ratio', () => {
    expect(
      findViolations(
        (_f, c) =>
          /\bconformes\s*\/\s*(?:total|count)\s*\)\s*\*\s*100/.test(c) ||
          /pctConf\s*[:=]\s*(?:Math\.round|parseInt)\s*\(\s*\(?\s*conformes/.test(c)
      )
    ).toEqual([]);
  });

  it('CO₂ brut (* 0.052 ou * 0.227) absent hors constants/', () => {
    expect(
      findViolations(
        (f, c) => !f.includes('constants') && (/\*\s*0\.052\b/.test(c) || /\*\s*0\.227\b/.test(c))
      )
    ).toEqual([]);
  });
});
