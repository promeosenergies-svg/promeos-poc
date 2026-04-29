/**
 * Source-guard Phase 1.5 — SolTrajectoryDT.
 *
 * Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.5 : verrouille
 * le contrat du composant SVG trajectoire Décret Tertiaire 2030 utilisé
 * par la page Synthèse stratégique.
 *
 * Endpoint backend cible : `/api/cockpit/trajectory` existant — contrat
 * `routes/cockpit.py:393` retourne {annees, reel_mwh, objectif_mwh,
 * projection_mwh, ref_year, jalons}. Le composant est props-driven et
 * ne fait AUCUN fetch (doctrine §8.1 zero business logic frontend).
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const COMPONENT_PATH = resolve(__dirname, '..', 'ui', 'sol', 'SolTrajectoryDT.jsx');
const SRC = readFileSync(COMPONENT_PATH, 'utf-8');

describe('SolTrajectoryDT — contrat Phase 1.5', () => {
  it('exporte un composant React par défaut', () => {
    expect(SRC).toMatch(/export default function SolTrajectoryDT/);
  });

  it('accepte les props canoniques alignées contrat backend', () => {
    expect(SRC).toMatch(/annees\s*=\s*\[\]/);
    expect(SRC).toMatch(/reelMwh\s*=\s*\[\]/);
    expect(SRC).toMatch(/objectifMwh\s*=\s*\[\]/);
    expect(SRC).toMatch(/projectionMwh\s*=\s*\[\]/);
    expect(SRC).toMatch(/todayYear\s*=\s*new Date\(\)\.getFullYear\(\)/);
    expect(SRC).toMatch(/yMin\s*=\s*2000/);
    expect(SRC).toMatch(/yMax\s*=\s*5000/);
  });

  it('retourne null si annees < 2 (anti-pattern §6.1 empty state pleine largeur)', () => {
    expect(SRC).toMatch(/annees\.length\s*<\s*2/);
    expect(SRC).toMatch(/return null/);
  });

  it('utilise un viewBox SVG figé 800×240 (cohérence maquettes)', () => {
    expect(SRC).toMatch(/viewBox=["']0 0 800 240["']/);
  });

  it('rend les 3 séries canoniques via paths (objectif + réel + projection)', () => {
    expect(SRC).toMatch(/data-testid=["']sol-trajectory-objectif-path["']/);
    expect(SRC).toMatch(/data-testid=["']sol-trajectory-reel-path["']/);
    expect(SRC).toMatch(/data-testid=["']sol-trajectory-projection-path["']/);
  });

  it('utilise les tokens Sol pour les 3 couleurs (refuse/info/succes)', () => {
    expect(SRC).toMatch(/var\(--sol-refuse-fg/);
    expect(SRC).toMatch(/var\(--sol-info-fg/);
    expect(SRC).toMatch(/var\(--sol-succes-fg/);
  });

  it('cible DT (objectif) est dashed (réglementaire = ligne pointillée canonique)', () => {
    expect(SRC).toMatch(/strokeDasharray=["']4,4["']/);
  });

  it('marker "aujourd\'hui" rendu si todayYear ∈ annees', () => {
    expect(SRC).toMatch(/todayIdx\s*=\s*annees\.indexOf\(todayYear\)/);
    expect(SRC).toMatch(/aujourd/);
  });

  it('aria-label généré dynamiquement à partir des données (a11y WCAG 2.2 §13)', () => {
    expect(SRC).toMatch(/role=["']img["']/);
    expect(SRC).toMatch(/aria-label=\{generatedAriaLabel\}/);
    expect(SRC).toMatch(/Trajectoire Décret Tertiaire/);
  });

  it('override aria-label possible via prop ariaLabel', () => {
    expect(SRC).toMatch(/ariaLabel\s*\|\|/);
  });

  it('data-testid racine stable pour Playwright', () => {
    expect(SRC).toMatch(/data-testid=["']sol-trajectory-dt["']/);
  });

  it('pas de hex hardcodé hors var() (tokens Sol obligatoires)', () => {
    const codeOnly = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    const hexOutsideVar = codeOnly.match(/(?<!var\([^)]*)#[0-9a-fA-F]{3,6}(?![^()]*\))/g);
    expect(hexOutsideVar, 'Hex hardcodés hors var() détectés — utiliser tokens Sol').toBeNull();
  });

  it('zero business logic frontend (doctrine §8.1) — pas de fetch ni state data', () => {
    const codeOnly = SRC.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(codeOnly).not.toMatch(/useEffect|useState|fetch\(|axios/);
  });

  it('pas de Recharts (cohérence maquettes SVG natif + perf TTFV)', () => {
    expect(SRC).not.toMatch(/from\s+['"]recharts['"]/);
  });

  it('format MWh utilise locale fr-FR avec espace insécable normalisé', () => {
    expect(SRC).toMatch(/toLocaleString\(['"]fr-FR['"]\)/);
    // Normalisation espace insécable U+202F vers espace standard
    expect(SRC).toMatch(/replace\(\/\\u202f\/g/);
  });

  it('buildPath filtre les valeurs null (séries partielles : passé reel, futur projection)', () => {
    expect(SRC).toMatch(/p\.y\s*!=\s*null/);
    expect(SRC).toMatch(/Number\.isFinite/);
  });

  it('labels axe X années paires uniquement (lisibilité)', () => {
    expect(SRC).toMatch(/year\s*%\s*2\s*!==\s*0/);
  });

  it('axe Y : 4 ticks équirépartis dynamiques (top, 2/3, 1/3, bottom)', () => {
    expect(SRC).toMatch(/yTicks\s*=\s*\[yMax/);
  });
});
