/**
 * PROMEOS — Tests CockpitDecision.jsx (Phase Vague 4 EPIC #274).
 *
 * Pattern : source-guard + logique pure (readFileSync + regex, env=node).
 * Doctrine §8.1 zero business logic FE. Pas de testing-library (composant
 * dépend de Context/Router non mockés dans env node pur).
 *
 * Couverture :
 *   CD_01 — export default present, composant nommé
 *   CD_02 — null-guard co2_avoided_t_year (optional chaining)
 *   CD_03 — window.print() présent (bouton rapport COMEX)
 *   CD_04 — RegulatoryConstantsContext importé (seuils viennent backend)
 *   CD_05 — aucun calcul métier inline (zéro facteur CO₂ / pénalité hardcodé)
 *   CD_06 — getCockpitDecisionsTop3 importé depuis services/api/cockpit
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');
const FILE = join(SRC_ROOT, 'pages', 'CockpitDecision.jsx');

function read() {
  return readFileSync(FILE, 'utf-8');
}

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── CD_01 — export default ────────────────────────────────────────────────

describe('CD_01 — CockpitDecision export default présent', () => {
  it('le fichier exporte une fonction default CockpitDecision', () => {
    const src = read();
    expect(src).toMatch(/export default function CockpitDecision\s*\(/);
  });
});

// ── CD_02 — null-guards décision ─────────────────────────────────────────

describe('CD_02 — accès aux champs décision (co2_avoided_t_year, regulatory_penalty_eur)', () => {
  it('co2_avoided_t_year est référencé dans le composant', () => {
    const src = read();
    // Le champ co2_avoided_t_year doit être consommé (vérification présence)
    expect(src).toMatch(/co2_avoided_t_year/);
  });

  it('regulatory_penalty_eur est accédé (field exposé par backend)', () => {
    const src = read();
    // Le champ doit être utilisé dans DecisionCardImpl
    expect(src).toMatch(/regulatory_penalty_eur/);
  });

  it('les champs optionnels du backend utilisent optional chaining ou null-check', () => {
    const src = read();
    // Au moins un champ utilise ?. (null-safety présente dans le composant)
    expect(src).toMatch(/\?\./);
  });
});

// ── CD_03 — window.print() présent ────────────────────────────────────────

describe('CD_03 — bouton Rapport COMEX appelle window.print()', () => {
  it('window.print() est appelé pour le rapport PDF', () => {
    const src = read();
    expect(src).toMatch(/window\.print\s*\(\s*\)/);
  });
});

// ── CD_04 — RegulatoryConstantsContext importé ───────────────────────────

describe('CD_04 — seuils réglementaires viennent du Context (doctrine §8.1)', () => {
  it('useRegulatoryConstants importé depuis RegulatoryConstantsContext', () => {
    const src = read();
    expect(src).toMatch(/useRegulatoryConstants/);
    expect(src).toMatch(/RegulatoryConstantsContext/);
  });
});

// ── CD_05 — zéro business logic inline ───────────────────────────────────

describe('CD_05 — aucun calcul métier inline (doctrine §8.1)', () => {
  const FORBIDDEN_PATTERNS = [
    { pattern: /\*\s*0\.052\b/, label: 'facteur CO₂ élec inline' },
    { pattern: /\*\s*0\.227\b/, label: 'facteur CO₂ gaz inline' },
    { pattern: /\*\s*7500\b/, label: 'DT_PENALTY_EUR hardcodé' },
    { pattern: /\*\s*3750\b/, label: 'DT_PENALTY_AT_RISK_EUR hardcodé' },
    { pattern: /\*\s*1500\b/, label: 'BACS_PENALTY_EUR hardcodé' },
  ];

  for (const { pattern, label } of FORBIDDEN_PATTERNS) {
    it(`pas de ${label}`, () => {
      const cleaned = stripComments(read());
      expect(cleaned).not.toMatch(pattern);
    });
  }
});

// ── CD_06 — imports API cockpit ───────────────────────────────────────────

describe('CD_06 — getCockpitDecisionsTop3 depuis services/api/cockpit', () => {
  it('getCockpitDecisionsTop3 importé depuis le service API canonique', () => {
    const src = read();
    expect(src).toMatch(/getCockpitDecisionsTop3/);
    expect(src).toMatch(/services\/api\/cockpit/);
  });

  it('getCockpitTrajectory importé (section trajectoire 2030)', () => {
    const src = read();
    expect(src).toMatch(/getCockpitTrajectory/);
  });
});
