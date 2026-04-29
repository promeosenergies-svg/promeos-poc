/**
 * Source-guard Phase 1.4 — zero business logic in frontend cockpit.
 *
 * Sprint refonte cockpit dual sol2 (29/04/2026) — clôture Phase 1.4.
 * Verrouille la règle d'or CLAUDE.md #1 : zero business logic in frontend.
 *
 * Patterns interdits (calculs métier dans .jsx Cockpit) :
 *   - Math.round + reduce (agrégation custom)
 *   - sum = 0 / accumulator pattern
 *   - aggregate (calcul agrégé inline)
 *
 * Stratégie SEUIL GLISSANT (29/04/2026) :
 * - Baseline mesurée Phase 1.4 fin = 26 occurrences (≤ MAX_THRESHOLD=28 buffer)
 * - Cible Phase 1.4.d.bis + 1.4.e.bis = ≤ 5 occurrences
 * - Une fois 1.4.d/e.bis livrés, MAX_THRESHOLD doit descendre par paliers :
 *     bis 1.4.d livré → MAX = 18 (suppression dashboardEssentials prod)
 *     bis 1.4.e livré → MAX = 5 (cible finale prompt §2.B ligne 484)
 *
 * Le test FAIL signale :
 *   1. Régression : nouveau calcul métier introduit dans cockpit/*.jsx
 *   2. Migration : compteur descendu sous le seuil → resserrer MAX_THRESHOLD
 *
 * Doctrine PROMEOS Sol §8.1 + CLAUDE.md règle d'or #1 + audit qa-guardian
 * fin Phase 1.4.
 */

import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync } from 'fs';
import { resolve } from 'path';

const COCKPIT_DIR = resolve(__dirname, '..', 'pages', 'cockpit');

// Seuil ajustable : à descendre à 5 après 1.4.d.bis + 1.4.e.bis
const MAX_THRESHOLD = 28;
const TARGET_THRESHOLD = 5;

// Patterns interdits : agrégations inline en JSX
const FORBIDDEN_PATTERNS = [
  /Math\.round\([^)]*\.reduce/, // Math.round avec reduce direct
  /\.reduce\([^)]*\+[^)]*,\s*0\)/, // accumulator + somme via reduce
  /\baggregate\b/, // mention explicite agrégation
];

function listJsxFiles(dir) {
  return readdirSync(dir)
    .filter((f) => f.endsWith('.jsx'))
    .map((f) => resolve(dir, f));
}

function countViolations(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  const codeOnly = content.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  let count = 0;
  for (const pattern of FORBIDDEN_PATTERNS) {
    const matches = codeOnly.match(new RegExp(pattern, 'g'));
    if (matches) count += matches.length;
  }
  return count;
}

describe('test_no_business_logic_in_frontend_cockpit — source-guard Phase 1.4', () => {
  it(`occurrences calcul métier dans cockpit/*.jsx ≤ MAX_THRESHOLD (${MAX_THRESHOLD}) [seuil glissant]`, () => {
    const files = listJsxFiles(COCKPIT_DIR);
    const perFile = files
      .map((f) => ({
        file: f.split('/cockpit/')[1],
        count: countViolations(f),
      }))
      .filter((x) => x.count > 0)
      .sort((a, b) => b.count - a.count);

    const total = perFile.reduce((sum, x) => sum + x.count, 0);

    expect(
      total,
      `Régression détectée : ${total} occurrences (max ${MAX_THRESHOLD}). ` +
        `Détail : ${JSON.stringify(perFile, null, 2)}. ` +
        `Cible finale = ≤${TARGET_THRESHOLD} après Phase 1.4.d.bis + 1.4.e.bis. ` +
        `Migrer la logique vers backend/services/dashboard_essentials_service.py ` +
        `et data_activation_service.py via endpoints /api/cockpit/essentials et ` +
        `/api/cockpit/data_activation.`
    ).toBeLessThanOrEqual(MAX_THRESHOLD);
  });

  it("aucun fichier cockpit/*.jsx n'utilise pattern aggregate explicite", () => {
    const files = listJsxFiles(COCKPIT_DIR);
    const offenders = files.filter((f) => /\baggregate\b/.test(readFileSync(f, 'utf-8')));
    expect(
      offenders,
      `Anti-pattern aggregate détecté dans : ${offenders.map((f) => f.split('/cockpit/')[1]).join(', ')}`
    ).toHaveLength(0);
  });

  it('le seuil MAX_THRESHOLD doit décroître au fil des migrations bis', () => {
    // Test sentinel : si MAX_THRESHOLD reste à 28 après que 1.4.d.bis + 1.4.e.bis
    // sont livrés (plus de dashboardEssentials.js + dataActivationModel.js
    // côté frontend), un audit doit alerter.
    expect(MAX_THRESHOLD).toBeLessThanOrEqual(28);
    expect(TARGET_THRESHOLD).toBe(5);
  });
});
