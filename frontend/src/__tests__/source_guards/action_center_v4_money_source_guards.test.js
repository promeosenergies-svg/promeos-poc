/**
 * PROMEOS — Source guards FE Action Center V4 mode CFO (M2-6.B.frontend).
 *
 * Pin la doctrine cardinale « zéro recalcul de somme € côté frontend » :
 * les agrégats €/MWh affichés (NarrativeBar, EditorialNarrativeBlock,
 * colonne ItemsTable) viennent EXCLUSIVEMENT du backend `/api/v4/action-
 * center/summary` (champs `sums_eur_total`, `sums_eur_by_priority`,
 * `items_with_impact_known`, `items_total`).
 *
 * Anti-pattern visé : un dev ajoute `items.reduce((s, i) => s + (i.
 * estimated_impact_euros || 0), 0)` pour afficher un total local — duplique
 * la logique backend, dérive silencieusement, casse la cohérence CFO.
 *
 * SG_AC_V4_MONEY_01 — aucun `.reduce(*estimated_impact_euros*)` dans les
 *   pages V4 (ou composants liés). Le check tolère le mot dans les
 *   commentaires (filtre lignes commençant par `//` ou `*`).
 *
 * Pattern repo : readFileSync + regex (env=node). Pas de glob (overkill MV3).
 */

import { existsSync, readdirSync, readFileSync, statSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');
const V4_ROOT = join(SRC_ROOT, 'pages', 'action-center-v4');

function walkJsxFiles(dir, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const entry of readdirSync(dir)) {
    if (entry === '__tests__' || entry === 'node_modules') continue;
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      walkJsxFiles(fullPath, acc);
    } else if (/\.(js|jsx|ts|tsx)$/.test(entry)) {
      acc.push(fullPath);
    }
  }
  return acc;
}

function stripCommentsLines(src) {
  // Supprime les lignes qui commencent par // ou * (commentaires multilignes)
  // ET les commentaires JS inline /* ... */ multi-lignes.
  return src
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .filter((line) => !/^\s*(\/\/|\*)/.test(line))
    .join('\n');
}

// ── SG_AC_V4_MONEY_01 ────────────────────────────────────────────────

describe('SG_AC_V4_MONEY_01 — pas de recalcul de sommes € côté FE', () => {
  it('aucun fichier action-center-v4 ne fait `.reduce(*estimated_impact_euros*)`', () => {
    const files = walkJsxFiles(V4_ROOT);
    const violations = [];

    // Pattern interdit : reduce() sur une liste d'items avec `estimated_impact_euros`
    // OU `sums_eur_total` accumulé manuellement.
    const REDUCE_IMPACT = /\.reduce\([^)]*\b(estimated_impact_euros|sums_eur)\b/;

    for (const file of files) {
      const src = stripCommentsLines(readFileSync(file, 'utf-8'));
      if (REDUCE_IMPACT.test(src)) {
        violations.push(file.replace(SRC_ROOT, 'src'));
      }
    }

    expect(violations).toEqual([]);
  });

  it('aucun fichier action-center-v4 ne calcule un total € via boucle for sur items', () => {
    const files = walkJsxFiles(V4_ROOT);
    const violations = [];

    // Pattern : `total += item.estimated_impact_euros` (anti-pattern boucle
    // imperative qui duplique la logique backend).
    const FOR_LOOP_IMPACT = /\+=\s*\w+\.estimated_impact_euros/;

    for (const file of files) {
      const src = stripCommentsLines(readFileSync(file, 'utf-8'));
      if (FOR_LOOP_IMPACT.test(src)) {
        violations.push(file.replace(SRC_ROOT, 'src'));
      }
    }

    expect(violations).toEqual([]);
  });
});
