// @vitest-environment jsdom
/**
 * PROMEOS — Tests MonitoringClimateScatter (Sprint P2.1).
 *
 * Vérifie le comportement du composant extrait de MonitoringPage.jsx
 * (`ClimateScatter` inline ligne 1321) :
 * - rendu de l'empty state avec reason backend
 * - rendu du scatter quand données présentes
 * - propagation des stats backend (pente, Tb, R², label)
 * - affichage du compteur outliers masqués
 * - aucun calcul métier interdit (filtre = filtre d'affichage pur)
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import MonitoringClimateScatter from '../pages/monitoring/MonitoringClimateScatter';

afterEach(() => cleanup());

describe('MonitoringClimateScatter — empty state', () => {
  it("rend l'empty state si climate null", () => {
    render(<MonitoringClimateScatter climate={null} />);
    expect(screen.getByTestId('monitoring-climate-scatter-empty')).toBeTruthy();
    expect(screen.getByText(/Pas de données climatiques/i)).toBeTruthy();
  });

  it("rend l'empty state si scatter vide avec reason backend", () => {
    render(<MonitoringClimateScatter climate={{ scatter: [], reason: 'no_weather' }} />);
    expect(screen.getByTestId('monitoring-climate-scatter-empty')).toBeTruthy();
    expect(screen.getByText(/Données météo indisponibles/i)).toBeTruthy();
    expect(screen.getByText(/code: no_weather/)).toBeTruthy();
  });

  it('affiche le reason brut si pas dans CLIMATE_REASONS', () => {
    render(<MonitoringClimateScatter climate={{ scatter: [], reason: 'custom_reason' }} />);
    const empty = screen.getByTestId('monitoring-climate-scatter-empty');
    expect(empty.textContent).toContain('custom_reason');
    expect(empty.textContent).toContain('code: custom_reason');
  });
});

describe('MonitoringClimateScatter — rendu scatter', () => {
  const baseClimate = {
    scatter: Array.from({ length: 30 }, (_, i) => ({ T: 5 + i * 0.5, kwh: 100 - i * 1.5 })),
    fit_line: [
      { T: 5, kwh: 100 },
      { T: 20, kwh: 60 },
    ],
    slope_kw_per_c: -2.5,
    balance_point_c: 16.5,
    r_squared: 0.78,
    label: 'heating_dominant',
  };

  it('rend le scatter principal + stats backend', () => {
    render(<MonitoringClimateScatter climate={baseClimate} />);
    expect(screen.getByTestId('monitoring-climate-scatter')).toBeTruthy();
    const stats = screen.getByTestId('monitoring-climate-scatter-stats');
    expect(stats.textContent).toContain('Pente');
    expect(stats.textContent).toContain('Tb');
    expect(stats.textContent).toContain('R²');
    expect(stats.textContent).toContain('Chauffage majoritaire');
  });

  it('masque les outliers via outlier_bounds backend (doctrine P0.S1c)', () => {
    const withOutliers = {
      ...baseClimate,
      scatter: [
        ...baseClimate.scatter,
        { T: 30, kwh: 5000 }, // outlier
        { T: 35, kwh: 6000 }, // outlier
      ],
      outlier_bounds: { lower: 0, upper: 200 },
    };
    render(<MonitoringClimateScatter climate={withOutliers} />);
    const removed = screen.getByTestId('monitoring-climate-scatter-outliers-removed');
    expect(removed).toBeTruthy();
    expect(removed.textContent).toMatch(/2 outliers masqués/);
  });

  it('rend tous les points si outlier_bounds absent (pas de fallback FE)', () => {
    render(<MonitoringClimateScatter climate={baseClimate} />);
    // Aucun compteur outliers affiché
    expect(screen.queryByTestId('monitoring-climate-scatter-outliers-removed')).toBeNull();
  });

  it('rend le label backend canonique (CLIMATE_LABEL_FR map)', () => {
    const cooling = { ...baseClimate, label: 'cooling_dominant' };
    render(<MonitoringClimateScatter climate={cooling} />);
    expect(screen.getByTestId('monitoring-climate-scatter-stats').textContent).toContain(
      'Climatisation majoritaire'
    );
  });
});

describe('MonitoringClimateScatter — doctrine zéro calcul métier', () => {
  it('ne contient aucun calcul de quantile / régression FE', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../pages/monitoring/MonitoringClimateScatter.jsx'),
      'utf8'
    );
    // Pas de calcul quantile FE (utilise outlier_bounds backend)
    expect(src).not.toMatch(/Math\.floor\s*\(\s*\w+\.length\s*\*\s*0\.(25|5|75)\s*\)/);
    // Pas de calcul R² FE (vient du backend)
    expect(src).not.toMatch(/r_squared\s*=\s*\w+\s*\*\s*\w+/);
    // Pas de calcul pente FE
    expect(src).not.toMatch(/slope\s*=\s*\(\s*\w+\.kwh\s*-/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
