/**
 * PROMEOS — Source guards FE Consommation (Vague 4 EPIC #274).
 *
 * Surveille ConsommationsPage.jsx, ConsommationsUsages.jsx et
 * pages consommation/charge curve.
 * Doctrine §8.1 : zéro seuil MWh/kWh hardcodé, zéro calcul DJU/CUSUM inline.
 *
 * SG_CONSO_FE_01 — pas de seuils MWh/kWh hardcodés hors constants importées
 * SG_CONSO_FE_02 — pas de calcul DJU/CUSUM inline FE
 * SG_CONSO_FE_03 — pas de fetch() natif vers /consumption
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const CONSUMPTION_PAGES = [
  join(SRC_ROOT, 'pages', 'ConsommationsPage.jsx'),
  join(SRC_ROOT, 'pages', 'ConsommationsUsages.jsx'),
].filter(existsSync);

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_CONSO_FE_01 — pas de seuils MWh hardcodés ─────────────────────────

describe('SG_CONSO_FE_01 — pas de seuils MWh/kWh hardcodés hors constants', () => {
  it('pas de seuil OPERAT (> 1000 MWh) hardcodé comme littéral de comparaison', () => {
    const violations = [];
    // Pattern : "> 1000" ou "< 1000" en dehors d'une constante importée
    // OPERAT seuil = 1000 MWh/an (doit venir backend via RegulatoryConstants)
    const OPERAT_SEUIL = /[><]=?\s*1000\b.*[Mm][Ww][Hh]|[Mm][Ww][Hh].*[><]=?\s*1000\b/;
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (OPERAT_SEUIL.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });

  it('pas de coefficient kWh→MWh hardcodé comme 0.001 dans les pages conso', () => {
    // 0.001 peut être un coefficient ou un seuil — dans les pages conso
    // c'est toujours via splitMwh (utils/format.js SoT)
    // On tolère dans les commentaires
    const violations = [];
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (/\*\s*0\.001\b/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_CONSO_FE_02 — pas de calcul DJU/CUSUM inline ─────────────────────

describe('SG_CONSO_FE_02 — pas de calcul DJU/CUSUM inline FE', () => {
  it('pas de calcul DJU inline (ex: conso / dju * 20)', () => {
    const violations = [];
    // DJU normalisé = calcul backend — sur 20°C base temperature
    const DJU_INLINE = /\/\s*dju\b.*\*\s*\d+|\*\s*\d+.*\/\s*dju\b/i;
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (DJU_INLINE.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });

  it('pas de formule CUSUM inline (somme cumulative écarts)', () => {
    const violations = [];
    // CUSUM = calcul backend EMS — heuristique: 'cusum' dans un calcul
    const CUSUM_INLINE = /cusum\s*[+=\-*]/i;
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (CUSUM_INLINE.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_CONSO_FE_03 — pas de fetch natif vers /consumption ─────────────────

describe('SG_CONSO_FE_03 — pas de fetch() natif vers /consumption', () => {
  it('aucune page conso ne fait de fetch() natif vers /consumption', () => {
    const violations = [];
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (/\bfetch\s*\(\s*['"].*consumption/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });

  it('aucune page conso ne contient de fetch() natif non-axios', () => {
    const violations = [];
    for (const file of CONSUMPTION_PAGES) {
      const cleaned = stripComments(readFileSync(file, 'utf-8'));
      if (/\bfetch\s*\(/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});
