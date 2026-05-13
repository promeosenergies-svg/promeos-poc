/**
 * PROMEOS — Source guards FE Synthèse Stratégique (Phase 3.5 Vague D.7).
 *
 * Verrous structurels pour la nouvelle page from-scratch CockpitStrategique.jsx
 * (clarif. user 2026-05-13 : « on ne crée pas au-dessus, on part from scratch »).
 *
 * Guards :
 *   SG_STRATEGIQUE_01 — page-≤-250-lignes :
 *       pages/CockpitStrategique.jsx doit rester ≤ 250 lignes pour garantir
 *       composition pure + lisibilité (anti-dérive vs Cockpit.jsx 1337 l).
 *
 *   SG_STRATEGIQUE_02 — no-import-cockpit-legacy :
 *       pages/CockpitStrategique.jsx NE DOIT JAMAIS importer pages/Cockpit.jsx
 *       (ni Cockpit, ni CockpitDecision, ni CockpitJour). Composition uniquement
 *       via grammar/hub/*.
 *
 *   SG_STRATEGIQUE_03 — uses-canonical-grammar :
 *       importe HubPage + SolHeroPremiumNight + CadreApplicable +
 *       StrategicModeBanner + VerdictFinal + DossierP1 + HubKpiCard +
 *       HubPageFooter depuis grammar/hub.
 *
 *   SG_STRATEGIQUE_04 — no-mode-hardcoded :
 *       aucun strategic_mode hardcodé (regulatory_driven / performance_driven /
 *       data_insufficient en string literal) dans le code de la page.
 *       Le mode vient du backend (payload.strategic_mode).
 *
 *   SG_STRATEGIQUE_05 — api-client-from-scratch :
 *       la page utilise getCockpitStrategique (et pas getCockpitDecision ni
 *       getCockpitJour pour le même endpoint).
 *
 * Pattern repo : readFileSync + regex (env=node).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..', '..', '..');
const PAGE = join(REPO_ROOT, 'src', 'pages', 'CockpitStrategique.jsx');

describe('Source guards FE — Synthèse Stratégique (Phase 3.5)', () => {
  it('SG_STRATEGIQUE_01 — pages/CockpitStrategique.jsx existe', () => {
    expect(existsSync(PAGE)).toBe(true);
  });

  it('SG_STRATEGIQUE_01 — page ≤ 250 lignes', () => {
    const text = readFileSync(PAGE, 'utf8');
    const lineCount = text.split('\n').length;
    expect(lineCount).toBeLessThanOrEqual(250);
  });

  it('SG_STRATEGIQUE_02 — no import from pages/Cockpit.jsx', () => {
    const text = readFileSync(PAGE, 'utf8');
    // Interdit : import * from './Cockpit', import Cockpit from './Cockpit',
    // import { ... } from './Cockpit', '../pages/Cockpit'
    const forbidden = [
      /from\s+['"]\.\/Cockpit['"]/,
      /from\s+['"]\.\.\/pages\/Cockpit['"]/,
      /import\s+CockpitDecision/,
      /import\s+CockpitJour/,
      /from\s+['"]\.\/CockpitDecision['"]/,
      /from\s+['"]\.\/CockpitJour['"]/,
    ];
    for (const re of forbidden) {
      expect(text).not.toMatch(re);
    }
  });

  it('SG_STRATEGIQUE_03 — uses canonical grammar/hub primitives', () => {
    const text = readFileSync(PAGE, 'utf8');
    const requiredImports = [
      'HubPage',
      'SolHeroPremiumNight',
      'StrategicModeBanner',
      'CadreApplicable',
      'VerdictFinal',
      'DossierP1',
      'HubKpiCard',
      'HubPageFooter',
      'ChartFrameTrajectoryLine',
      'ChartFrameBenchSites',
    ];
    for (const name of requiredImports) {
      expect(text).toContain(name);
    }
  });

  it('SG_STRATEGIQUE_04 — no strategic_mode hardcoded as string literal', () => {
    const text = readFileSync(PAGE, 'utf8');
    // Pattern interdit : === 'regulatory_driven' / mode = 'performance_driven'
    // Mais on tolère les commentaires (// 'regulatory_driven' ...).
    const forbidden = [
      /=\s*['"]regulatory_driven['"]/,
      /=\s*['"]performance_driven['"]/,
      /=\s*['"]procurement_driven['"]/,
      /=\s*['"]opportunity_driven['"]/,
      /=\s*['"]data_insufficient['"]/,
      /return\s+['"]regulatory_driven['"]/,
      /return\s+['"]performance_driven['"]/,
      /return\s+['"]data_insufficient['"]/,
    ];
    for (const re of forbidden) {
      expect(text).not.toMatch(re);
    }
  });

  it('SG_STRATEGIQUE_05 — uses getCockpitStrategique API client', () => {
    const text = readFileSync(PAGE, 'utf8');
    expect(text).toContain('getCockpitStrategique');
    // Confirme qu'on n'utilise pas l'API legacy pour cette page
    expect(text).not.toContain('getCockpitDecision(');
    expect(text).not.toContain('getCockpitJour(');
  });

  it('SG_STRATEGIQUE_06 — data-attributes for source-guards downstream', () => {
    const text = readFileSync(PAGE, 'utf8');
    expect(text).toContain('data-page="cockpit-strategique"');
    expect(text).toContain('data-doctrine="L11"');
    expect(text).toContain('data-mode');
  });
});
