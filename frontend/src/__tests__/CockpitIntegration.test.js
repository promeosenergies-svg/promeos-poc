/**
 * PROMEOS — Cockpit.jsx Integration Step 6 — Source Guards + Structure Tests
 * Vérifie que les composants Steps 1-5 sont intégrés et que l'existant est conservé.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cockpitPath = join(__dirname, '..', 'pages', 'Cockpit.jsx');
const cockpitSrc = readFileSync(cockpitPath, 'utf-8');

// ── Intégration Step 6 ──────────────────────────────────────────────

describe('Cockpit.jsx — intégration composants world-class', () => {
  it('importe useCockpitData', () => {
    expect(cockpitSrc).toMatch(/import.*useCockpitData/);
  });

  it('importe CockpitHero', () => {
    expect(cockpitSrc).toMatch(/import CockpitHero/);
  });

  it('importe TrajectorySection', () => {
    expect(cockpitSrc).toMatch(/import TrajectorySection/);
  });

  it('importe ActionsImpact', () => {
    expect(cockpitSrc).toMatch(/import ActionsImpact/);
  });

  it('appelle useCockpitData() dans le composant', () => {
    expect(cockpitSrc).toMatch(/useCockpitData\(\)/);
  });

  it('rend CockpitHero avec onEvidence', () => {
    expect(cockpitSrc).toMatch(/<CockpitHero/);
    expect(cockpitSrc).toMatch(/onEvidence=\{setEvidenceOpen\}/);
  });

  it('rend TrajectorySection', () => {
    expect(cockpitSrc).toMatch(/<TrajectorySection/);
  });

  it('rend ActionsImpact', () => {
    expect(cockpitSrc).toMatch(/<ActionsImpact/);
  });

  it('contient la banniere retard trajectoire conditionnelle', () => {
    expect(cockpitSrc).toContain('data-testid="banner-retard-trajectoire"');
  });
});

// ── Conservation existant ────────────────────────────────────────────

describe('Cockpit.jsx — sections existantes conservees', () => {
  it('conserve EvidenceDrawer', () => {
    expect(cockpitSrc).toMatch(/<EvidenceDrawer/);
  });

  it('conserve evidenceOpen state', () => {
    expect(cockpitSrc).toMatch(/useState\(null\).*KPI id or null|evidenceOpen/);
  });

  it('conserve HeroImpactBar (V1+ remplace ExecutiveKpiRow)', () => {
    expect(cockpitSrc).toMatch(/<HeroImpactBar/);
  });

  it('conserve SanteKpiGrid (V1+ remplace EssentialsRow)', () => {
    expect(cockpitSrc).toMatch(/<SanteKpiGrid/);
  });

  it('conserve ModuleLaunchers', () => {
    expect(cockpitSrc).toMatch(/<ModuleLaunchers/);
  });

  it('conserve la table des sites', () => {
    expect(cockpitSrc).toMatch(/<Table>/);
    expect(cockpitSrc).toMatch(/<Pagination/);
  });

  it('conserve DemoSpotlight', () => {
    expect(cockpitSrc).toMatch(/DemoSpotlight/);
  });
});

// ── Source Guards ────────────────────────────────────────────────────

describe('Cockpit.jsx — source guard (no-calc)', () => {
  it('ne recalcule pas conformiteScore (conformes/total*100)', () => {
    expect(cockpitSrc).not.toMatch(/conformes\s*\/\s*total\s*\*\s*100/);
  });

  it('ne contient pas de formule CO2 (* 0.0569)', () => {
    expect(cockpitSrc).not.toMatch(/\*\s*0\.0569/);
  });

  it('ne contient pas de formule risque (* 7500)', () => {
    expect(cockpitSrc).not.toMatch(/\*\s*7500/);
  });
});
