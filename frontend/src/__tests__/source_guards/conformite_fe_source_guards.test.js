/**
 * PROMEOS — Source guards FE Conformité (Vague 4 EPIC #274).
 *
 * Surveille ConformitePage.jsx et composants DT/BACS/APER.
 * Doctrine §8.1 : seuils décret et deadlines viennent du backend uniquement.
 *
 * SG_CONF_FE_01 — pas de seuils décret hardcodés (7500/3750/1500 EUR penalty)
 * SG_CONF_FE_02 — deadlines réglementaires viennent du backend (pas de date ISO hardcodée)
 * SG_CONF_FE_03 — pas de calcul conformité inline FE
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync, readdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const CONFORMITE_PAGE = join(SRC_ROOT, 'pages', 'ConformitePage.jsx');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_CONF_FE_01 — pas de seuils décret hardcodés comme calculs ─────────

describe('SG_CONF_FE_01 — pas de multiplication par les seuils décret dans ConformitePage', () => {
  it('pas de * 7500 (DT_PENALTY_EUR) en calcul inline', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*7500\b/);
  });

  it('pas de * 3750 (DT_PENALTY_AT_RISK) en calcul inline', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*3750\b/);
  });

  it('pas de * 1500 (BACS_PENALTY) en calcul inline', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*1500\b/);
  });

  it('ConformitePage importe useRegulatoryConstants ou consomme Context (seuils viennent backend)', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const src = readFileSync(CONFORMITE_PAGE, 'utf-8');
    // Soit via RegulatoryConstantsContext, soit via useEvents qui porte les events
    const usesContext = /useRegulatoryConstants|RegulatoryConstantsContext|useEvents/.test(src);
    expect(usesContext).toBe(true);
  });
});

// ── SG_CONF_FE_02 — deadlines viennent du backend ─────────────────────────

describe('SG_CONF_FE_02 — deadlines réglementaires non hardcodées dans ConformitePage', () => {
  it("pas de date deadline DT '2026-01-01' hardcodée comme littéral de comparaison", () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    // On interdit les comparaisons avec dates deadline hardcodées
    // ex: new Date('2026-01-01') dans un if()
    expect(cleaned).not.toMatch(/new Date\s*\(\s*['"]2026-01-01['"]\s*\)/);
    expect(cleaned).not.toMatch(/new Date\s*\(\s*['"]2028-01-01['"]\s*\)/);
  });

  it("pas de deadline BACS '2025-01-01' hardcodée", () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    expect(cleaned).not.toMatch(/new Date\s*\(\s*['"]2025-01-01['"]\s*\)/);
  });
});

// ── SG_CONF_FE_03 — pas de calcul score conformité inline ─────────────────

describe('SG_CONF_FE_03 — pas de calcul de score conformité inline dans ConformitePage', () => {
  it('pas de calcul score = sites_nc / total * 100 inline FE', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    // Heuristique : formule de scoring inline (division par total × 100)
    // ex: (nc / sites.length) * 100
    expect(cleaned).not.toMatch(/\/\s*sites\.length\s*\*\s*100/);
    expect(cleaned).not.toMatch(/\/\s*total\s*\*\s*100.*score/i);
  });

  it('ConformitePage ne contient pas de logique de pondération DT/BACS/APER inline', () => {
    if (!existsSync(CONFORMITE_PAGE)) return;
    const cleaned = stripComments(readFileSync(CONFORMITE_PAGE, 'utf-8'));
    // Les pondérations du scoring (ex: DT=0.5, BACS=0.3, APER=0.2) appartiennent
    // au backend regops/scoring.py (SoT canonique)
    expect(cleaned).not.toMatch(/dt.*0\.[3-9]\s*[+\-*].*bacs|bacs.*0\.[2-9]\s*[+\-*].*aper/i);
  });
});
