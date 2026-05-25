/**
 * PROMEOS — Source guards FE traçabilité KPI (Vague 3B EPIC #274).
 *
 * Règle cardinale 03/05/2026 : chaque KPI exposé doit lire confidence + source_ref
 * depuis le backend — jamais de constante hardcodée.
 *
 * SG_TRACE_FE_01 — CockpitDecision.jsx lit leviers_kpi depuis potential_recoverable (pas hardcodé)
 * SG_TRACE_FE_02 — CockpitDecision.jsx n'hardcode pas 25500 ni 8500 comme valeur KPI
 * SG_TRACE_FE_03 — CockpitDecision.jsx consomme projection_tracability depuis trajectory
 * SG_TRACE_FE_04 — KpiCard.jsx ne calcule pas gain MWh → € inline
 * SG_TRACE_FE_05 — CockpitDecision.jsx affiche confidence_label depuis backend (pas de map inline)
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC_ROOT = join(__dirname, '..', '..');

const COCKPIT_DECISION = join(SRC_ROOT, 'pages', 'CockpitDecision.jsx');
const KPI_CARD = join(SRC_ROOT, 'components', 'cockpit', 'KpiCard.jsx');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
}

// ── SG_TRACE_FE_01 — leviers_kpi lu depuis backend ───────────────────────

// P0 cleanup cockpit (2026-05-25) — CockpitDecision.jsx supprimé (orphelin
// post M2-5.11). Les SG ciblent maintenant uniquement les fichiers vivants
// (CockpitStrategique remplace CockpitDecision pour la grammaire L11).
describe('SG_TRACE_FE_01 — CockpitDecision lit leviers_kpi depuis potential_recoverable', () => {
  it.skipIf(!existsSync(COCKPIT_DECISION))('CockpitDecision.jsx existe (skip si supprimé)', () => {
    expect(existsSync(COCKPIT_DECISION)).toBe(true);
  });

  it('référence potential?.leviers_kpi depuis backend', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    // Doit consommer leviers_kpi du payload backend
    expect(src).toMatch(/leviers_kpi/);
    expect(src).toMatch(/potential[\s\S]{0,20}leviers_kpi/);
  });

  it('consomme confidence et source_ref depuis leviers_kpi', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    expect(src).toMatch(/leviersKpi[\s\S]{0,50}confidence/);
  });
});

// ── SG_TRACE_FE_02 — pas de 25500 ni 8500 hardcodé ───────────────────────

describe('SG_TRACE_FE_02 — CockpitDecision.jsx sans constante € hardcodée', () => {
  it('ne contient pas 25500 comme valeur KPI leviers hardcodée', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const cleaned = stripComments(readFileSync(COCKPIT_DECISION, 'utf-8'));
    // 25500 ne doit pas apparaître comme littéral standalone (valeur magique)
    expect(cleaned).not.toMatch(/=\s*25500\b/);
    expect(cleaned).not.toMatch(/\b25500\s*[;,)]/);
  });

  it('ne contient pas 8500 multiplié comme gain inline', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const cleaned = stripComments(readFileSync(COCKPIT_DECISION, 'utf-8'));
    expect(cleaned).not.toMatch(/\*\s*8500\b/);
    expect(cleaned).not.toMatch(/=\s*8500\b/);
  });
});

// ── SG_TRACE_FE_03 — projection_tracability consommé ─────────────────────

describe('SG_TRACE_FE_03 — CockpitDecision consomme projection_tracability depuis trajectory', () => {
  it('référence projection_tracability dans TrajectoryDTSmoothed', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    expect(src).toMatch(/projection_tracability/);
  });

  it('affiche le tooltip depuis projection_tracability.tooltip', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    expect(src).toMatch(/projection_tracability\?\.tooltip/);
  });
});

// ── SG_TRACE_FE_04 — KpiCard ne calcule pas gain inline ──────────────────

describe('SG_TRACE_FE_04 — KpiCard ne calcule pas MWh → € inline', () => {
  it('KpiCard.jsx existe', () => {
    expect(existsSync(KPI_CARD)).toBe(true);
  });

  it('KpiCard ne multiplie pas par un prix énergie inline', () => {
    if (!existsSync(KPI_CARD)) return;
    const cleaned = stripComments(readFileSync(KPI_CARD, 'utf-8'));
    // Anti-pattern : prix EPEX / 1000 inline dans KpiCard
    expect(cleaned).not.toMatch(/\*\s*0\.068\b/);
    expect(cleaned).not.toMatch(/\*\s*0\.130\b/);
    expect(cleaned).not.toMatch(/\*\s*130\b/); // PRICE_ELEC_ETI_2026 hardcodé
  });
});

// ── SG_TRACE_FE_05 — confidence_label lu depuis backend ──────────────────

describe('SG_TRACE_FE_05 — CockpitDecision affiche confidence_label/tooltip depuis backend', () => {
  it('ne mappe pas les confidence levels avec un objet inline', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const cleaned = stripComments(readFileSync(COCKPIT_DECISION, 'utf-8'));
    // Anti-pattern : mapper les confidence values inline plutôt que de lire confidence_label backend
    // On tolère les références à la clé mais pas un objet complet de mapping
    const FORBIDDEN_INLINE_MAP = /calculated_regulatory.*:.*Calculé.*calculated_contractual/s;
    expect(cleaned).not.toMatch(FORBIDDEN_INLINE_MAP);
  });

  it('utilise leviersKpi.confidence_label (champ backend) pour le badge', () => {
    if (!existsSync(COCKPIT_DECISION)) return;
    const src = readFileSync(COCKPIT_DECISION, 'utf-8');
    expect(src).toMatch(/confidence_label/);
  });
});
