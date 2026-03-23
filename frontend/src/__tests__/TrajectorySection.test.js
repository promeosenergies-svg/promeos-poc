/**
 * PROMEOS — TrajectorySection — Source Guards + Structure Tests
 * Vérifie Recharts, no-calc-as-KPI, et structure du composant.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const trajPath = join(__dirname, '..', 'pages', 'cockpit', 'TrajectorySection.jsx');
const trajSrc = readFileSync(trajPath, 'utf-8');

// ── Source Guards ────────────────────────────────────────────────────

describe('TrajectorySection — source guard (no-calc KPI)', () => {
  it('utilise Recharts (pas Chart.js)', () => {
    expect(trajSrc).toMatch(/from 'recharts'/);
    expect(trajSrc).not.toMatch(/Chart\.js|new Chart/);
  });

  it('ne reassigne pas reductionPct comme KPI', () => {
    expect(trajSrc).not.toMatch(/reductionPct\s*=\s*\(1\s*-/);
  });

  it('ne contient pas de formule CO2 (* 0.0569)', () => {
    expect(trajSrc).not.toMatch(/\*\s*0\.0569/);
  });

  it('ne contient pas de formule risque (* 7500 ou * 3750)', () => {
    expect(trajSrc).not.toMatch(/\*\s*7500/);
    expect(trajSrc).not.toMatch(/\*\s*3750/);
  });

  it('documente l exception de presentation pour le toggle %', () => {
    expect(trajSrc).toMatch(/transformation de pr[eé]sentation/i);
  });
});

// ── Structure ────────────────────────────────────────────────────────

describe('TrajectorySection — structure', () => {
  it('contient data-testid trajectory-section', () => {
    expect(trajSrc).toContain('data-testid="trajectory-section"');
  });

  it('utilise ComposedChart de Recharts', () => {
    expect(trajSrc).toMatch(/ComposedChart/);
  });

  it('utilise ResponsiveContainer', () => {
    expect(trajSrc).toMatch(/ResponsiveContainer/);
  });

  it('a 3 series : reel, objectif, projection', () => {
    expect(trajSrc).toMatch(/dataKey=.*reel/);
    expect(trajSrc).toMatch(/dataKey=.*objectif/);
    expect(trajSrc).toMatch(/dataKey=.*projection/);
  });

  it('a une ReferenceLine pour annee courante', () => {
    expect(trajSrc).toMatch(/ReferenceLine/);
  });

  it('affiche les jalons depuis trajectoire.jalons', () => {
    expect(trajSrc).toMatch(/jalons\?\.map/);
  });

  it('a un toggle kWh / % reduction', () => {
    expect(trajSrc).toMatch(/setMode\('kwh'\)/);
    expect(trajSrc).toMatch(/setMode\('pct'\)/);
  });

  it('importe Skeleton et EmptyState', () => {
    expect(trajSrc).toMatch(/Skeleton/);
    expect(trajSrc).toMatch(/EmptyState/);
  });

  it('contient SiteBar pour les barres kWh/m2', () => {
    expect(trajSrc).toMatch(/SiteBar/);
  });

  it('a des focus-visible rings', () => {
    expect(trajSrc).toMatch(/focus-visible:ring/);
  });
});

// ── Légende et contexte ──────────────────────────────────────────────

describe('TrajectorySection — legende et contexte', () => {
  it('affiche une legende custom (Reel, Objectif DT, Projection)', () => {
    expect(trajSrc).toMatch(/Réel/);
    expect(trajSrc).toMatch(/Objectif DT/);
    expect(trajSrc).toMatch(/Projection \+ actions/);
  });

  it('affiche la reference annee et surface', () => {
    expect(trajSrc).toMatch(/trajectoire\.refYear/);
    expect(trajSrc).toMatch(/surfaceM2Total/);
  });
});
