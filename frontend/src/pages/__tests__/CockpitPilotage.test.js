/**
 * PROMEOS — Tests CockpitPilotage.jsx (Phase Vague 4 EPIC #274).
 *
 * Pattern : source-guard + logique pure (readFileSync + regex, env=node).
 * Doctrine §8.1 zero business logic FE.
 *
 * Couverture :
 *   CP_01 — export default présent
 *   CP_02 — _CONSO_7D_* PLACEHOLDER commenté + _projectBreakdownToBars data-driven
 *   CP_03 — confidenceLabel mapping complet (Calculé/Modélisé/Indicatif)
 *   CP_04 — previousYearLabel : regex parse year correct (non-hardcodé)
 *   CP_05 — zéro calcul métier inline (CO₂/pénalité/prix hardcodés)
 *   CP_06 — getCockpitPriorities importé depuis services/api/cockpit
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');
const FILE = join(SRC_ROOT, 'pages', 'CockpitPilotage.jsx');

function read() {
  return readFileSync(FILE, 'utf-8');
}

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── CP_01 — export default ────────────────────────────────────────────────

describe('CP_01 — CockpitPilotage export default présent', () => {
  it('le fichier exporte une fonction default CockpitPilotage', () => {
    const src = read();
    expect(src).toMatch(/export default function CockpitPilotage\s*\(/);
  });
});

// ── CP_02 — PLACEHOLDER vs data-driven ───────────────────────────────────

describe('CP_02 — _CONSO_7D_* PLACEHOLDER vs _projectBreakdownToBars data-driven', () => {
  it('_CONSO_7D_DAYS est défini comme PLACEHOLDER statique', () => {
    const src = read();
    expect(src).toMatch(/_CONSO_7D_DAYS/);
    // Doit être documenté comme PLACEHOLDER
    expect(src).toMatch(/PLACEHOLDER/);
  });

  it('_projectBreakdownToBars est la fonction data-driven prioritaire', () => {
    const src = read();
    expect(src).toMatch(/function _projectBreakdownToBars\s*\(/);
    // weeklyBreakdown doit être le paramètre d'entrée
    expect(src).toMatch(/_projectBreakdownToBars\s*\(\s*weeklyBreakdown\s*\)/);
  });

  it('ConsoSevenDaysBars préfère projected sur les données PLACEHOLDER', () => {
    const src = read();
    // Le composant utilise `projected || _CONSO_7D_DAYS` (fallback sûr)
    expect(src).toMatch(/projected\s*\|\|\s*_CONSO_7D_DAYS/);
  });
});

// ── CP_03 — confidenceLabel mapping ──────────────────────────────────────

describe('CP_03 — confidenceLabel mapping Calculé/Modélisé/Indicatif', () => {
  it("badge 'calculated_regulatory' ou 'calculated_contractual' → 'Calculé'", () => {
    const src = read();
    expect(src).toMatch(/calculated_regulatory/);
    expect(src).toMatch(/calculated_contractual/);
    expect(src).toMatch(/'Calculé'/);
  });

  it("badge 'modeled_cee' ou 'modeled' → 'Modélisé'", () => {
    const src = read();
    expect(src).toMatch(/modeled_cee/);
    expect(src).toMatch(/'Modélisé'/);
  });

  it("badge 'indicative' → 'Indicatif'", () => {
    const src = read();
    expect(src).toMatch(/'indicative'/);
    expect(src).toMatch(/'Indicatif'/);
  });
});

// ── CP_04 — previousYearLabel parse regex ────────────────────────────────

describe('CP_04 — previousYearLabel dérivé dynamiquement via regex (non hardcodé)', () => {
  it('previousYearLabel utilise un regex sur current_month_label', () => {
    const src = read();
    // Regex pour extraire mois + année et soustraire 1 an
    expect(src).toMatch(/previousYearLabel/);
    // Doit utiliser +m[2] - 1 (calcul année dynamique)
    expect(src).toMatch(/\+m\[2\]\s*-\s*1/);
  });

  it('fallback N−1 si label absent', () => {
    const src = read();
    expect(src).toMatch(/'N.1'/);
  });

  // Test logique pure (pas de DOM) : validation de la regex JS dans Node
  it('regex /^(\\w+)\\s+(\\d{4})/ extrait mois et année', () => {
    const RE = /^(\w+)\s+(\d{4})/;
    const label = 'avril 2026 (j 1-3)';
    const m = label.match(RE);
    expect(m).not.toBeNull();
    expect(m[1]).toBe('avril');
    expect(+m[2] - 1).toBe(2025);
  });
});

// ── CP_05 — zéro business logic inline ───────────────────────────────────

describe('CP_05 — aucun calcul métier inline dans CockpitPilotage (doctrine §8.1)', () => {
  const FORBIDDEN = [
    { pattern: /\*\s*0\.052\b/, label: 'facteur CO₂ élec' },
    { pattern: /\*\s*7500\b/, label: 'DT_PENALTY_EUR' },
    { pattern: /\*\s*0\.227\b/, label: 'facteur CO₂ gaz' },
    { pattern: /TURPE.*=.*\d+\.\d+/, label: 'tarif TURPE hardcodé' },
  ];

  for (const { pattern, label } of FORBIDDEN) {
    it(`pas de ${label}`, () => {
      const cleaned = stripComments(read());
      expect(cleaned).not.toMatch(pattern);
    });
  }
});

// ── CP_06 — imports API cockpit ───────────────────────────────────────────

describe('CP_06 — getCockpitPriorities depuis services/api/cockpit', () => {
  it('getCockpitPriorities importé depuis le service API canonique', () => {
    const src = read();
    expect(src).toMatch(/getCockpitPriorities/);
    expect(src).toMatch(/services\/api\/cockpit/);
  });

  it('useCockpitFacts importé (triptyque KPI + alertes)', () => {
    const src = read();
    expect(src).toMatch(/useCockpitFacts/);
  });
});
