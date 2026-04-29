/**
 * Source-guard Phase 3.1 — routes Cockpit dual sol2 + câblage SolKpiMonthlyVsN1.
 *
 * Verrouille :
 *   - /cockpit/jour   → CommandCenter (page Pilotage)
 *   - /cockpit/strategique → Cockpit (page Décision)
 *   - /cockpit → redirect /cockpit/jour (default mode)
 *   - /dashboard, /executive, /synthese → redirect /cockpit/strategique (CFO)
 *   - /tableau-de-bord → redirect /cockpit/jour
 *   - <SolKpiMonthlyVsN1Container> consomme useCockpitFacts → endpoint Phase 1.3.a
 *
 * Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §4.B Phase 3.1.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const APP_PATH = resolve(__dirname, '..', 'App.jsx');
const APP_SRC = readFileSync(APP_PATH, 'utf-8');

const HOOK_PATH = resolve(__dirname, '..', 'hooks', 'useCockpitFacts.js');
const HOOK_SRC = readFileSync(HOOK_PATH, 'utf-8');

const CONTAINER_PATH = resolve(
  __dirname,
  '..',
  'components',
  'cockpit',
  'SolKpiMonthlyVsN1Container.jsx'
);
const CONTAINER_SRC = readFileSync(CONTAINER_PATH, 'utf-8');

const API_PATH = resolve(__dirname, '..', 'services', 'api', 'cockpit.js');
const API_SRC = readFileSync(API_PATH, 'utf-8');

// ── Routes canoniques Phase 3.1 ──────────────────────────────────────

describe('Phase 3.1 — routes Cockpit dual sol2', () => {
  it('route /cockpit/jour exposée → CommandCenter (page Pilotage)', () => {
    expect(APP_SRC).toMatch(/path=["']\/cockpit\/jour["']/);
    // CommandCenter existe et est référencé pour cette route
    expect(APP_SRC).toMatch(/CommandCenter/);
  });

  it('route /cockpit/strategique exposée → Cockpit (page Décision)', () => {
    expect(APP_SRC).toMatch(/path=["']\/cockpit\/strategique["']/);
  });

  it('route /cockpit redirect vers /cockpit/jour (default mode)', () => {
    // Pattern : path="/cockpit" element={<Navigate to="/cockpit/jour" replace />}
    expect(APP_SRC).toMatch(
      /path=["']\/cockpit["']\s+element=\{\s*<Navigate\s+to=["']\/cockpit\/jour["']/
    );
  });

  it('route /dashboard redirect vers /cockpit/strategique (CFO mode)', () => {
    expect(APP_SRC).toMatch(
      /path=["']\/dashboard["']\s+element=\{\s*<Navigate\s+to=["']\/cockpit\/strategique["']/
    );
  });

  it('routes /executive et /synthese redirect vers /cockpit/strategique', () => {
    expect(APP_SRC).toMatch(
      /path=["']\/executive["']\s+element=\{\s*<Navigate\s+to=["']\/cockpit\/strategique["']/
    );
    expect(APP_SRC).toMatch(
      /path=["']\/synthese["']\s+element=\{\s*<Navigate\s+to=["']\/cockpit\/strategique["']/
    );
  });

  it('route /tableau-de-bord redirect vers /cockpit/jour (energy manager)', () => {
    expect(APP_SRC).toMatch(
      /path=["']\/tableau-de-bord["']\s+element=\{\s*<Navigate\s+to=["']\/cockpit\/jour["']/
    );
  });
});

// ── useCockpitFacts hook (Phase 1.3.a SoT) ──────────────────────────

describe('useCockpitFacts — wrapper Phase 1.3.a endpoint atomique', () => {
  it('expose useCockpitFacts comme default export', () => {
    expect(HOOK_SRC).toMatch(/export default useCockpitFacts/);
  });

  it('consomme getCockpitFacts depuis services/api', () => {
    expect(HOOK_SRC).toMatch(/import\s*\{\s*getCockpitFacts\s*\}/);
  });

  it('doctrine §8.1 zero business logic — fetch + setState uniquement', () => {
    const codeOnly = HOOK_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    // Pas de Math.round/.reduce/aggregate (anti-pattern §6.3 + §8.1)
    expect(codeOnly).not.toMatch(/Math\.round.*\.reduce|\.reduce.*\+.*0\)/);
  });

  it('getCockpitFacts API call est cachable (utilise cachedGet pattern)', () => {
    expect(API_SRC).toMatch(/export const getCockpitFacts/);
    expect(API_SRC).toMatch(/cachedGet\(`?\/cockpit\/_facts/);
  });
});

// ── SolKpiMonthlyVsN1Container ──────────────────────────────────────

describe('SolKpiMonthlyVsN1Container — câblage Phase 3.1', () => {
  it('importe SolKpiMonthlyVsN1 depuis ui/sol', () => {
    expect(CONTAINER_SRC).toMatch(
      /import\s+SolKpiMonthlyVsN1\s+from\s+['"]\.\.\/\.\.\/ui\/sol\/SolKpiMonthlyVsN1['"]/
    );
  });

  it("consomme useCockpitFacts avec period='current_month'", () => {
    expect(CONTAINER_SRC).toMatch(/useCockpitFacts\(['"]current_month['"]\)/);
  });

  it('extrait facts.consumption.monthly_vs_n1 et passe en prop data', () => {
    expect(CONTAINER_SRC).toMatch(/facts\?\.consumption\?\.monthly_vs_n1/);
    expect(CONTAINER_SRC).toMatch(/data=\{monthlyData\}/);
  });

  it('retourne null si loading ou monthly_vs_n1 absent (anti-pattern §6.1 empty state)', () => {
    expect(CONTAINER_SRC).toMatch(/return null/);
  });

  it('aucun calcul métier — display delegate uniquement (doctrine §8.1)', () => {
    const codeOnly = CONTAINER_SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    // Word-boundary pour éviter les faux positifs (ex: "consumption" contient "sum")
    expect(codeOnly).not.toMatch(/Math\.round|\.reduce\(|\baggregate\b|\bsum\s*=\s*0/);
  });
});
