/**
 * PROMEOS — Source guards FE Leviers (Vague 4 EPIC #274).
 *
 * Surveille models/leverActionModel.js (modèle pur FE) et les pages
 * AnomaliesPage.jsx qui consomment les leviers.
 * Doctrine §8.1 : pas de calcul gain € inline, les gains viennent du backend.
 *
 * SG_LEVER_FE_01 — pas de constante 8500€/site hardcodée (gain annuel moyen)
 * SG_LEVER_FE_02 — leverActionModel.js n'implémente pas de calcul financier
 * SG_LEVER_FE_03 — pas de fetch() natif dans les pages leviers
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const LEVER_MODEL = join(SRC_ROOT, 'models', 'leverActionModel.js');
const ANOMALIES_PAGE = join(SRC_ROOT, 'pages', 'AnomaliesPage.jsx');

const LEVER_FILES = [LEVER_MODEL, ANOMALIES_PAGE].filter(existsSync);

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_LEVER_FE_01 — pas de 8500€/site hardcodé ─────────────────────────

describe('SG_LEVER_FE_01 — pas de constante gain 8500€/site hardcodée', () => {
  it('leverActionModel ne contient pas de 8500 comme gain par site', () => {
    if (!existsSync(LEVER_MODEL)) return;
    const cleaned = stripComments(readFileSync(LEVER_MODEL, 'utf-8'));
    // 8500 comme gain fixe par levier/site = business logic hardcodée
    expect(cleaned).not.toMatch(/=\s*8500\b/);
    expect(cleaned).not.toMatch(/8500\s*\/\s*site/i);
  });

  it('AnomaliesPage ne contient pas de 8500 comme gain calculé inline', () => {
    if (!existsSync(ANOMALIES_PAGE)) return;
    const cleaned = stripComments(readFileSync(ANOMALIES_PAGE, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*8500\b/);
    expect(cleaned).not.toMatch(/=\s*8500\b/);
  });
});

// ── SG_LEVER_FE_02 — leverActionModel ne calcule pas de gain financier ───

describe('SG_LEVER_FE_02 — leverActionModel.js ne calcule pas de gain € (lecture SoT backend)', () => {
  it('leverActionModel.js existe (modèle lever → action)', () => {
    expect(existsSync(LEVER_MODEL)).toBe(true);
  });

  it('leverActionModel ne multiplie pas par des coefficients financiers inline', () => {
    if (!existsSync(LEVER_MODEL)) return;
    const cleaned = stripComments(readFileSync(LEVER_MODEL, 'utf-8'));
    // Anti-pattern : calcul gain = mwh * prix_unitaire inline
    expect(cleaned).not.toMatch(/mwh\s*\*\s*\d+\.?\d*/i);
    expect(cleaned).not.toMatch(/\*\s*0\.052\b/); // CO₂ factor
    expect(cleaned).not.toMatch(/\*\s*0\.227\b/); // CO₂ gaz
  });

  it('leverActionModel expose les gains depuis le payload lever (pas de recalcul)', () => {
    if (!existsSync(LEVER_MODEL)) return;
    const src = readFileSync(LEVER_MODEL, 'utf-8');
    // Le modèle doit passer les valeurs lever.impactEur ou lever.gain_eur
    // sans les recalculer (pass-through)
    expect(src).toMatch(/lever\.(impactEur|impact_eur|gain_eur|estimated_gain)/);
  });
});

// ── SG_LEVER_FE_03 — pas de fetch() natif ─────────────────────────────────

describe('SG_LEVER_FE_03 — pas de fetch() natif dans les fichiers lever', () => {
  it('aucun fichier lever ne contient de fetch() natif', () => {
    const violations = [];
    for (const file of LEVER_FILES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (/\bfetch\s*\(/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});
