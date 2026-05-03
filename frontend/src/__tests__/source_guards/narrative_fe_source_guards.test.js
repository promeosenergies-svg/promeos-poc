/**
 * PROMEOS — Source guards FE Narrative/Briefing (Vague 4 EPIC #274).
 *
 * Surveille les composants briefing et narrative (SolNarrative, usePageBriefing).
 * Doctrine §8.1 : pas de calcul forecasting inline, narrative vient du backend
 * via /api/pages/<key>/briefing (ou /api/cockpit/_facts).
 *
 * SG_NARR_FE_01 — pas de calcul forecasting inline dans SolNarrative
 * SG_NARR_FE_02 — usePageBriefing consomme uniquement l'endpoint canonique
 * SG_NARR_FE_03 — CockpitDecision utilise usePageBriefing (pas de narrative FE)
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const SOL_NARRATIVE = join(SRC_ROOT, 'ui', 'sol', 'SolNarrative.jsx');
const USE_PAGE_BRIEFING = join(SRC_ROOT, 'hooks', 'usePageBriefing.js');
const COCKPIT_DECISION = join(SRC_ROOT, 'pages', 'CockpitDecision.jsx');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_NARR_FE_01 — SolNarrative : pas de calcul forecasting inline ─────

describe('SG_NARR_FE_01 — SolNarrative ne contient pas de calcul forecasting', () => {
  it('SolNarrative.jsx existe (composant narratif canonique)', () => {
    expect(existsSync(SOL_NARRATIVE)).toBe(true);
  });

  it('SolNarrative ne contient pas de coefficient CO₂ inline', () => {
    if (!existsSync(SOL_NARRATIVE)) return;
    const cleaned = stripComments(readFileSync(SOL_NARRATIVE, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*0\.052\b/);
    expect(cleaned).not.toMatch(/\*\s*0\.227\b/);
  });

  it('SolNarrative ne contient pas de logique de forecast (pas de .reduce ou * 12 mois)', () => {
    if (!existsSync(SOL_NARRATIVE)) return;
    const cleaned = stripComments(readFileSync(SOL_NARRATIVE, 'utf-8'));
    // Pas de projection annuelle inline (ex: monthly * 12)
    expect(cleaned).not.toMatch(/\*\s*12\b.*[Mm][Ww][Hh]|[Mm][Ww][Hh].*\*\s*12\b/);
  });

  it('SolNarrative ne fait pas de fetch() natif', () => {
    if (!existsSync(SOL_NARRATIVE)) return;
    const cleaned = stripComments(readFileSync(SOL_NARRATIVE, 'utf-8'));
    expect(cleaned).not.toMatch(/\bfetch\s*\(/);
  });
});

// ── SG_NARR_FE_02 — usePageBriefing consomme l'endpoint canonique ─────────

describe('SG_NARR_FE_02 — usePageBriefing consomme /api/pages/<key>/briefing', () => {
  it('usePageBriefing.js existe (hook canonique narrative)', () => {
    expect(existsSync(USE_PAGE_BRIEFING)).toBe(true);
  });

  it('usePageBriefing appelle un endpoint briefing ou cockpit/_facts', () => {
    if (!existsSync(USE_PAGE_BRIEFING)) return;
    const src = readFileSync(USE_PAGE_BRIEFING, 'utf-8');
    const usesCanonicalEndpoint =
      /pages.*briefing|cockpit.*_facts|\/briefing|briefing.*endpoint/i.test(src);
    expect(usesCanonicalEndpoint).toBe(true);
  });

  it('usePageBriefing ne contient pas de calcul de narrative inline', () => {
    if (!existsSync(USE_PAGE_BRIEFING)) return;
    const cleaned = stripComments(readFileSync(USE_PAGE_BRIEFING, 'utf-8'));
    // Pas de composition de phrase narrative directement dans le hook
    expect(cleaned).not.toMatch(/\b(Votre|Vos|Ce mois|Cette semaine)\b.*score.*=\s*['"`]/i);
  });
});

// ── SG_NARR_FE_03 — CockpitDecision utilise usePageBriefing ──────────────

describe('SG_NARR_FE_03 — CockpitDecision délègue la narrative à usePageBriefing', () => {
  it('CockpitDecision importe usePageBriefing (délégation backend)', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    expect(src).toMatch(/usePageBriefing/);
  });

  it('CockpitDecision ne construit pas de string narrative inline (template literals complexes)', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const cleaned = stripComments(readFileSync(COCKPIT_DECISION, 'utf-8'));
    // Anti-pattern : `Votre score est ${score}/100...` inline dans JSX
    // On détecte les template literals multi-mots ressemblant à une narrative
    expect(cleaned).not.toMatch(/`Votre\s+\w+\s+est\s+\${/);
    expect(cleaned).not.toMatch(/`Vos\s+\w+\s+sites?\s+\${/);
  });
});
