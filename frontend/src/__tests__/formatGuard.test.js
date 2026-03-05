/**
 * PROMEOS — Source Guard : formatters centralisés
 * Vérifie qu'aucune page/composant n'utilise .toFixed() directement
 * (sauf fichiers autorisés) et que les formatters ont des guards.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join, relative } from 'path';

const SRC = join(__dirname, '..');

// ── Helper : récupère tous les fichiers .jsx/.js récursivement ────────────
function walk(dir, ext = ['.jsx', '.js']) {
  let results = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory() && !entry.startsWith('.') && entry !== 'node_modules' && entry !== '__tests__') {
      results = results.concat(walk(full, ext));
    } else if (ext.some((e) => entry.endsWith(e))) {
      results.push(full);
    }
  }
  return results;
}

// Fichiers de pages et composants (là où l'utilisateur voit le rendu)
const PAGE_FILES = walk(join(SRC, 'pages')).filter((f) => !f.includes('__tests__'));
const COMPONENT_FILES = walk(join(SRC, 'components'));
const DISPLAY_FILES = [...PAGE_FILES, ...COMPONENT_FILES];

// Fichiers autorisés à utiliser .toFixed (logique métier, pas affichage)
const ALLOWED_TOFIXED = [
  'format.js',           // Le formatter lui-même
  'helpers.js',          // Logique de calcul conso
  'scoring.js',          // Domain model scoring
  'rfp.js',              // Domain model RFP
  'engine.js',           // Domain model engine
  'recommend.js',        // Domain model recommend
  'MonitoringPage.jsx',  // Local fmtFR helper (to be migrated later)
  'SignatureLayer.jsx',  // Computation, not display
  'useEmsTimeseries.js', // Computation
];

// ── Test A : format.js guards ──────────────────────────────────────────────

describe('A. format.js — guards anti-NaN/Infinity', () => {
  const src = readFileSync(join(SRC, 'utils', 'format.js'), 'utf-8');

  it('contient la fonction _safe avec isFinite', () => {
    expect(src).toContain('isFinite');
  });

  it('fmtEur utilise _safe', () => {
    expect(src).toMatch(/function fmtEur[\s\S]*?_safe/);
  });

  it('fmtKwh utilise _safe', () => {
    expect(src).toMatch(/function fmtKwh[\s\S]*?_safe/);
  });

  it('fmtNum utilise _safe', () => {
    expect(src).toMatch(/function fmtNum[\s\S]*?_safe/);
  });

  it('formatPercentFR utilise _safe', () => {
    expect(src).toMatch(/function formatPercentFR[\s\S]*?_safe/);
  });
});

// ── Test B : nouveaux formatters présents ────────────────────────────────────

describe('B. format.js — nouveaux formatters', () => {
  const src = readFileSync(join(SRC, 'utils', 'format.js'), 'utf-8');

  it('exporte fmtKw', () => expect(src).toContain('export function fmtKw'));
  it('exporte fmtNum', () => expect(src).toContain('export function fmtNum'));
  it('exporte fmtPct', () => expect(src).toContain('export function fmtPct'));
  it('exporte fmtDateLong', () => expect(src).toContain('export function fmtDateLong'));
  it('exporte fmtDateRange', () => expect(src).toContain('export function fmtDateRange'));
});

// ── Test C : réduction progressive de .toFixed dans pages/components ──────

describe('C. Source guard — .toFixed() dans pages et composants', () => {
  const violations = [];

  for (const file of DISPLAY_FILES) {
    const rel = relative(SRC, file);
    const base = file.split(/[/\\]/).pop();
    if (ALLOWED_TOFIXED.includes(base)) continue;

    const src = readFileSync(file, 'utf-8');
    const matches = src.match(/\.toFixed\(/g);
    if (matches) {
      violations.push({ file: rel, count: matches.length });
    }
  }

  it('moins de 40 fichiers avec .toFixed() (baseline avant migration complète)', () => {
    // Objectif: réduire progressivement. Baseline initiale permissive.
    expect(violations.length).toBeLessThan(40);
  });

  it('total .toFixed() < 120 occurrences dans pages+components (hors autorisés)', () => {
    const total = violations.reduce((s, v) => s + v.count, 0);
    expect(total).toBeLessThan(120);
  });
});

// ── Test D : pas de "NaN" / "Infinity" comme chaîne affichable ────────────

describe('D. Source guard — pas de NaN/Infinity affichable', () => {
  const issues = [];

  for (const file of DISPLAY_FILES) {
    const rel = relative(SRC, file);
    const src = readFileSync(file, 'utf-8');
    // Cherche les cas où NaN ou Infinity serait dans un template string ou JSX text
    // Exclut les guards (isNaN, !isNaN, isFinite, Number.isNaN, Infinity comme sentinel)
    const lines = src.split('\n');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Skip guards and comparisons
      if (/isNaN|isFinite|!==\s*Infinity|<\s*Infinity|===\s*Infinity|!=\s*Infinity/.test(line)) continue;
      // Flag raw "Infinity" or "NaN" in template literals or JSX
      if (/[`"'].*(?:NaN|Infinity).*[`"']/.test(line) && !/test|spec|guard|filter/i.test(rel)) {
        issues.push({ file: rel, line: i + 1 });
      }
    }
  }

  it('aucune chaîne affichable contenant NaN ou Infinity', () => {
    expect(issues).toEqual([]);
  });
});
