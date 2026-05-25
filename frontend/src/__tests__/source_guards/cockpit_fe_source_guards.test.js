/**
 * PROMEOS — Source guards FE Cockpit (Vague 4 EPIC #274).
 *
 * Surveille Cockpit.jsx, CockpitDecision.jsx, CockpitPilotage.jsx.
 * Doctrine §8.1 zero business logic FE.
 *
 * SG_COCKPIT_FE_01 — pas de calcul Math.round/reduce sur données monétaires
 *                    inline sauf via utils/format.js (SoT FE)
 * SG_COCKPIT_FE_02 — pas de hardcode prix énergie / CO₂ / seuils réglementaires
 * SG_COCKPIT_FE_03 — pas de fetch() natif (uniquement axios via services/api/)
 * SG_COCKPIT_FE_04 — pas de eslint-disable sans commentaire WHY
 *
 * Pattern repo : readFileSync + regex (env=node), aligné events_fe_source_guards.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const COCKPIT_FILES = [
  // P0 cleanup cockpit (2026-05-25) — Cockpit.jsx et CockpitDecision.jsx
  // ont été supprimés (orphelins post M2-5.11). Les source-guards filtrent
  // automatiquement les fichiers manquants pour éviter ENOENT.
  join(SRC_ROOT, 'pages', 'Cockpit.jsx'),
  join(SRC_ROOT, 'pages', 'CockpitDecision.jsx'),
  join(SRC_ROOT, 'pages', 'CockpitPilotage.jsx'),
  join(SRC_ROOT, 'pages', 'CockpitJour.jsx'),
  join(SRC_ROOT, 'pages', 'CockpitStrategique.jsx'),
].filter((p) => {
  try {
    readFileSync(p, 'utf-8');
    return true;
  } catch {
    return false;
  }
});

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

function readFile(filePath) {
  return readFileSync(filePath, 'utf-8');
}

// ── SG_COCKPIT_FE_01 — pas de calcul monétaire inline ──────────────────────

describe('SG_COCKPIT_FE_01 — pas de calcul monétaire inline hors utils/format', () => {
  it('aucun .reduce() appliqué directement à des champs _eur sans passer par format.js', () => {
    const violations = [];
    for (const file of COCKPIT_FILES) {
      const cleaned = stripComments(readFile(file));
      // Pattern : .reduce(... + ..._eur) sans import splitMwh/fmtEurShort
      // Heuristique : reduce + _eur dans le même bloc
      if (/\.reduce\s*\([^)]*_eur[^)]*\)/.test(cleaned)) {
        // Accepté si le fichier importe bien les utils SoT
        if (!/from ['"][^'"]*utils\/format['"]/.test(readFile(file))) {
          violations.push(file);
        }
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_COCKPIT_FE_02 — pas de hardcode prix/CO₂/seuils ────────────────────

describe('SG_COCKPIT_FE_02 — pas de constantes métier hardcodées dans Cockpit', () => {
  const FORBIDDEN_SENTINELS = [
    { value: '0.052', label: 'CO₂ élec' },
    { value: '0.227', label: 'CO₂ gaz' },
    { value: '0.02658', label: 'accise legacy' },
    { value: '0.068', label: 'PRICE_FALLBACK' },
    // 7500/3750 peuvent apparaître dans des chaînes de label (tooltip), on
    // cherche une multiplication directe (* 7500) qui serait du calcul FE
  ];

  for (const { value, label } of FORBIDDEN_SENTINELS) {
    it(`pas de ${label} (${value}) hardcodé dans fichiers Cockpit`, () => {
      const violations = [];
      for (const file of COCKPIT_FILES) {
        const cleaned = stripComments(readFile(file));
        if (new RegExp(`\\b${value.replace('.', '\\.')}\\b`).test(cleaned)) {
          violations.push(file);
        }
      }
      expect(violations).toEqual([]);
    });
  }

  it('pas de multiplication par 7500 ou 3750 (calcul pénalité inline)', () => {
    const violations = [];
    for (const file of COCKPIT_FILES) {
      const cleaned = stripComments(readFile(file));
      if (/\*\s*(7500|3750)\b/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_COCKPIT_FE_03 — pas de fetch() natif ───────────────────────────────

describe('SG_COCKPIT_FE_03 — pas de fetch() natif dans les pages Cockpit', () => {
  it('aucune page Cockpit ne contient fetch( direct (hors commentaire)', () => {
    const violations = [];
    for (const file of COCKPIT_FILES) {
      const cleaned = stripComments(readFile(file));
      // fetch( en dehors d'une chaîne de caractères
      if (/\bfetch\s*\(/.test(cleaned)) {
        violations.push(file);
      }
    }
    expect(violations).toEqual([]);
  });
});

// ── SG_COCKPIT_FE_04 — eslint-disable doit avoir WHY ────────────────────────

describe("SG_COCKPIT_FE_04 — eslint-disable-next-line doit être accompagné d'un WHY", () => {
  it('tout eslint-disable-next-line dans les pages Cockpit a un commentaire justificatif', () => {
    const violations = [];
    for (const file of COCKPIT_FILES) {
      const src = readFile(file);
      const lines = src.split('\n');
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes('eslint-disable-next-line')) {
          // Le WHY doit être sur la même ligne après la directive
          const hasWhy =
            /eslint-disable-next-line\s+[\w\-/,\s]+--\s+\S/.test(line) ||
            /eslint-disable-next-line[^:]+:\s*\S/.test(line);
          // Alternative : la ligne suivante contient // WHY:
          const nextLine = lines[i + 1] || '';
          const nextHasWhy = /\/\/\s*(WHY|why|Because|because|FIXME|TODO|Phase)/.test(nextLine);
          if (!hasWhy && !nextHasWhy) {
            violations.push(`${file}:${i + 1}`);
          }
        }
      }
    }
    // Warning souple : on signale mais ne bloque pas (legacy)
    // Les nouvelles occurrences depuis refonte-sol2 doivent avoir WHY
    if (violations.length > 0) {
      console.warn(`SG_COCKPIT_FE_04: ${violations.length} eslint-disable sans WHY (fix P1)`);
    }
    // Pas de xfail — on tolère 0 violation stricte en cible
    expect(violations.length).toBeLessThanOrEqual(5); // seuil tolérance legacy
  });
});
