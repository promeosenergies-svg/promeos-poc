/**
 * PROMEOS — Source guards FE CO₂ factor dédup (Sprint C-2 Phase 4.4).
 *
 * GAP audit Phase B anti-pattern dédup CO₂ comblé : la constante
 * CO2E_FACTOR_KG_PER_KWH = 0.052 a été retirée de pages/consumption/constants.js.
 *
 * SoT runtime = /api/config/emission-factors (consommé par EmissionFactorsContext).
 * Fallback = inline 0.052 dans EmissionFactorsContext.jsx (1 seul endroit).
 *
 * SG_CO2_FE_01 — pages/consumption/constants.js n'exporte plus CO2E_FACTOR_KG_PER_KWH
 * SG_CO2_FE_02 — EmissionFactorsContext.jsx n'importe plus depuis consumption/constants
 * SG_CO2_FE_03 — Aucun autre fichier FE n'importe CO2E_FACTOR_KG_PER_KWH
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const CONSTANTS_PATH = join(SRC_ROOT, 'pages', 'consumption', 'constants.js');
const CONTEXT_PATH = join(SRC_ROOT, 'contexts', 'EmissionFactorsContext.jsx');

function walkSourceFiles(dir, acc = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory()) {
      // Ignore node_modules + build artifacts
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

describe('SG_CO2_FE — CO₂ factor dédup guards', () => {
  it('SG_CO2_FE_01 — consumption/constants.js does not export CO2E_FACTOR_KG_PER_KWH', () => {
    const content = readFileSync(CONSTANTS_PATH, 'utf-8');
    expect(
      content,
      `pages/consumption/constants.js doit pas réexporter CO2E_FACTOR_KG_PER_KWH ` +
        `(retiré Phase 4.4, SoT = EmissionFactorsContext fallback inline).`
    ).not.toMatch(/export\s+const\s+CO2E_FACTOR_KG_PER_KWH/);
  });

  it('SG_CO2_FE_02 — EmissionFactorsContext.jsx no longer imports from consumption/constants', () => {
    const content = readFileSync(CONTEXT_PATH, 'utf-8');
    expect(
      content,
      `EmissionFactorsContext.jsx doit pas importer depuis pages/consumption/constants ` +
        `(chain retirée Phase 4.4, fallback 0.052 désormais inline).`
    ).not.toMatch(/from\s+['"]\.\.?\/pages\/consumption\/constants['"]/);
  });

  it('SG_CO2_FE_03 — no FE source file imports CO2E_FACTOR_KG_PER_KWH', () => {
    // Scan tous les fichiers FE source pour détecter import résiduel.
    // Les tests dans __tests__/ peuvent référencer la constante (anti-pattern check).
    const files = walkSourceFiles(SRC_ROOT);
    const offenders = [];
    for (const file of files) {
      const content = readFileSync(file, 'utf-8');
      // Pattern : import { CO2E_FACTOR_KG_PER_KWH } from '...'
      if (/import\s*\{[^}]*CO2E_FACTOR_KG_PER_KWH[^}]*\}/.test(content)) {
        offenders.push(file.replace(SRC_ROOT, '<src>'));
      }
    }
    expect(
      offenders,
      `Aucun fichier FE ne doit importer CO2E_FACTOR_KG_PER_KWH (retiré Phase 4.4). ` +
        `Utiliser useElecCo2Factor() depuis EmissionFactorsContext.`
    ).toEqual([]);
  });
});
