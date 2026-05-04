/**
 * PROMEOS — Source guard FE regulatory_rates.js no new consumers (Sprint C-3 Phase 3.3).
 *
 * Sprint C-3 Phase 3.3 a livré l'endpoint backend `GET /api/regulatory/rates` +
 * hook FE `useRegulatoryRates` (RegulatoryRatesContext). Le module legacy
 * `frontend/src/domain/regulatory_rates.js` est désormais @deprecated et
 * conservé uniquement comme **fallback offline**.
 *
 * Anti-régression : interdit toute NOUVELLE consommation depuis regulatory_rates.js.
 * Allowlist : 2 fichiers seulement (le module lui-même + glossary.js fallback existant).
 *
 * Patterns vérifiés :
 * - SG_REG_RATES_FE_01 : aucun nouveau fichier source FE n'importe REGULATORY_RATES
 *   (allowlist : regulatory_rates.js + glossary.js)
 * - SG_REG_RATES_FE_02 : RegulatoryRatesContext.jsx existe avec API attendue
 * - SG_REG_RATES_FE_03 : regulatory_rates.js docstring mentionne @deprecated
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'fs';
import { dirname, join, relative } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const REGULATORY_RATES_PATH = join(SRC_ROOT, 'domain', 'regulatory_rates.js');
const GLOSSARY_PATH = join(SRC_ROOT, 'ui', 'glossary.js');
const CONTEXT_PATH = join(SRC_ROOT, 'contexts', 'RegulatoryRatesContext.jsx');

// Allowlist : fichiers autorisés à importer / référencer REGULATORY_RATES
const ALLOWED_CONSUMERS = new Set([
  REGULATORY_RATES_PATH, // self
  GLOSSARY_PATH, // fallback existant pré-Phase 3.3
]);

function walkSourceFiles(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      if (
        entry === 'node_modules' ||
        entry === 'dist' ||
        entry === 'build' ||
        entry === '__tests__'
      ) {
        continue;
      }
      walkSourceFiles(full, acc);
    } else if (/\.(jsx?|tsx?)$/.test(entry)) {
      acc.push(full);
    }
  }
  return acc;
}

describe('SG_REG_RATES_FE — regulatory_rates.js no new consumers', () => {
  it('SG_REG_RATES_FE_01 — no new FE source file imports REGULATORY_RATES outside allowlist', () => {
    const files = walkSourceFiles(SRC_ROOT);
    const offenders = [];

    // Pattern : import { REGULATORY_RATES } | import { ..., REGULATORY_RATES } |
    //           formatRate | rateTooltip from '...regulatory_rates'
    const FORBIDDEN_IMPORT =
      /import\s*(?:\{[^}]*\}|\*\s+as\s+\w+)\s*from\s*['"][^'"]*regulatory_rates['"]/;

    for (const file of files) {
      if (ALLOWED_CONSUMERS.has(file)) continue;
      const content = readFileSync(file, 'utf-8');
      if (FORBIDDEN_IMPORT.test(content)) {
        offenders.push(relative(SRC_ROOT, file));
      }
    }

    expect(
      offenders,
      `Nouveau import depuis regulatory_rates.js détecté (Sprint C-3 Phase 3.3 a déprécié ce module).\n` +
        `Utiliser le hook useRegulatoryRates() depuis RegulatoryRatesContext à la place.\n` +
        `Allowlist : regulatory_rates.js (self) + glossary.js (fallback pré-Phase 3.3).\n` +
        `Offenders:\n  - ` +
        offenders.join('\n  - ')
    ).toEqual([]);
  });

  it('SG_REG_RATES_FE_02 — RegulatoryRatesContext exposes Provider + 2 hooks', () => {
    const content = readFileSync(CONTEXT_PATH, 'utf-8');
    expect(content).toContain('export function RegulatoryRatesProvider');
    expect(content).toContain('export function useRegulatoryRates');
    expect(content).toContain('export function useRegulatorySource');
    expect(content).toContain("fetch('/api/regulatory/rates')");
  });

  it('SG_REG_RATES_FE_03 — regulatory_rates.js docstring mentions @deprecated Sprint C-3 Phase 3.3', () => {
    const content = readFileSync(REGULATORY_RATES_PATH, 'utf-8');
    expect(
      content,
      'regulatory_rates.js doit mentionner @deprecated Sprint C-3 Phase 3.3 dans sa docstring.'
    ).toMatch(/@deprecated[\s\S]{0,200}Sprint C-3 Phase 3\.3/);
  });
});
