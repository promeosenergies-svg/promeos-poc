/**
 * Test suites invariant — F3 fix P2-5
 *
 * Détecte les doublons de `describe(helper)` qui testent la MÊME fonction
 * (même identifier importé depuis le MÊME path) dans plusieurs fichiers.
 *
 * Motivation : l'incident des 2 commits A1 (80d7121a + 75bc32c8) a vu
 * 2 implémenteurs ajouter des tests pour `normalizeAperFilter` +
 * `applyAperFilter` dans 2 fichiers différents sans se voir. Cet invariant
 * empêche la récidive.
 *
 * Deux fichiers qui testent des helpers de même nom mais importés de
 * modules différents (ex. chaque page Sol a son `buildKickerText`) ne
 * sont PAS considérés comme doublons.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = join(__dirname, '..');

function walkTestFiles(dir) {
  const entries = readdirSync(dir);
  return entries.flatMap((entry) => {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      return walkTestFiles(full);
    }
    return entry.endsWith('.test.js') || entry.endsWith('.test.jsx') ? [full] : [];
  });
}

// Normalise un import path relatif (ex. '../sol_presenters' vs
// '../../pages/aper/sol_presenters') en path absolu approximatif côté
// repo pour comparaison. Contournement naïf : last N segments après
// le dernier '..'.
function stableImportKey(importPath) {
  // Garde le chemin après le dernier `..` pour capturer l'identité du module.
  // Ex: '../../pages/aper/sol_presenters' → 'pages/aper/sol_presenters'
  const parts = importPath.split('/').filter((p) => p !== '..' && p !== '.');
  return parts.join('/');
}

// Doublons pré-existants avant Sprint 1 Vague A — dette technique
// documentée. Le test échoue uniquement si un NOUVEAU doublon apparaît.
// Pour résorber, fusionner les tests puis retirer la ligne de l'allowlist.
const LEGACY_DUPLICATES = new Set([
  'formatPercentFR@utils/format',
  'normalizeDashboardModel@CommandCenter',
  'buildWatchlist@models/dashboardEssentials',
  'buildOpportunities@models/dashboardEssentials',
  'buildBriefing@models/dashboardEssentials',
  'buildKickerText@sol_presenters',
  'buildEmptyState@sol_presenters',
  'resolveTooltipExplain@sol_presenters',
]);

describe('Test suites invariant — no duplicate describe(helper, same module)', () => {
  const files = walkTestFiles(srcRoot);

  it('same helper × same import path appears in at most 1 test file (new only)', () => {
    // helper+module → [files]
    const helperOwnership = new Map();

    for (const f of files) {
      const src = readFileSync(f, 'utf-8');
      // Extract imports : `import { A, B } from '../path'`
      const importMap = new Map(); // identifier → stableImportKey
      const importRe = /import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"]/g;
      for (const im of src.matchAll(importRe)) {
        const ids = im[1].split(',').map((s) =>
          s
            .trim()
            .replace(/\s+as\s+\w+/, '')
            .trim()
        );
        const key = stableImportKey(im[2]);
        for (const id of ids) {
          if (id) importMap.set(id, key);
        }
      }
      // Scan describe() block names
      const describeRe = /describe\(['"]([A-Za-z0-9]+)['"]/g;
      for (const m of src.matchAll(describeRe)) {
        const name = m[1];
        if (!importMap.has(name)) continue; // describe name n'est pas une fonction importée → skip
        const moduleKey = importMap.get(name);
        const composite = `${name}@${moduleKey}`;
        const prev = helperOwnership.get(composite) ?? [];
        prev.push(f.replace(srcRoot + '/', ''));
        helperOwnership.set(composite, prev);
      }
    }

    const duplicates = Array.from(helperOwnership.entries())
      .filter(([composite, fs]) => new Set(fs).size > 1 && !LEGACY_DUPLICATES.has(composite))
      .map(([composite, fs]) => `${composite} (in: ${[...new Set(fs)].join(', ')})`);

    expect(
      duplicates,
      `NEW duplicate helper tests (same function, same module, multiple files):\n${duplicates.join('\n')}`
    ).toEqual([]);
  });
});
