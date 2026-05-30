// @vitest-environment jsdom
/**
 * PROMEOS — Tests WeekProfileHeatmap (Sprint P1.S4).
 *
 * Couvre :
 * - rendu 168 cellules quand matrix complète (7 × 24)
 * - status normal/vigilance/critique/missing rendu via data-status
 * - cellules manquantes (matrix sparse) → status='missing' affiché
 * - loading state
 * - aucun calcul métier interdit dans le composant
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import WeekProfileHeatmap from '../ui/energy/WeekProfileHeatmap';

function buildFullMatrix(statusFor = () => 'normal') {
  const matrix = [];
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      matrix.push({
        day_of_week: d,
        hour: h,
        kwh: 10 + d + h * 0.1,
        kw_avg: 5 + h * 0.05,
        status: statusFor(d, h),
        quality_status: 'measured',
      });
    }
  }
  return matrix;
}

afterEach(() => cleanup());

describe('WeekProfileHeatmap — rendu heatmap 7×24', () => {
  it('rend 168 cellules quand matrix complète', () => {
    render(<WeekProfileHeatmap matrix={buildFullMatrix()} />);
    // Compter via testId pattern
    let count = 0;
    for (let d = 0; d < 7; d++) {
      for (let h = 0; h < 24; h++) {
        if (screen.queryByTestId(`heatmap-cell-${d}-${h}`)) count++;
      }
    }
    expect(count).toBe(168);
  });

  it('affiche les 4 status backend via data-status', () => {
    const matrix = [
      { day_of_week: 0, hour: 0, kwh: 5, kw_avg: 2, status: 'normal', quality_status: 'measured' },
      {
        day_of_week: 1,
        hour: 0,
        kwh: 50,
        kw_avg: 20,
        status: 'vigilance',
        quality_status: 'measured',
      },
      {
        day_of_week: 2,
        hour: 0,
        kwh: 100,
        kw_avg: 40,
        status: 'critique',
        quality_status: 'measured',
      },
      {
        day_of_week: 3,
        hour: 0,
        kwh: null,
        kw_avg: null,
        status: 'missing',
        quality_status: 'missing',
      },
    ];
    render(<WeekProfileHeatmap matrix={matrix} />);
    expect(screen.getByTestId('heatmap-cell-0-0').getAttribute('data-status')).toBe('normal');
    expect(screen.getByTestId('heatmap-cell-1-0').getAttribute('data-status')).toBe('vigilance');
    expect(screen.getByTestId('heatmap-cell-2-0').getAttribute('data-status')).toBe('critique');
    expect(screen.getByTestId('heatmap-cell-3-0').getAttribute('data-status')).toBe('missing');
  });

  it('matrix sparse : cellules absentes deviennent status=missing', () => {
    // Seules 2 cellules fournies — les 166 autres doivent rendre missing.
    const matrix = [
      { day_of_week: 0, hour: 12, kwh: 8, kw_avg: 3, status: 'normal', quality_status: 'measured' },
      {
        day_of_week: 6,
        hour: 23,
        kwh: 12,
        kw_avg: 5,
        status: 'vigilance',
        quality_status: 'measured',
      },
    ];
    render(<WeekProfileHeatmap matrix={matrix} />);
    expect(screen.getByTestId('heatmap-cell-0-12').getAttribute('data-status')).toBe('normal');
    expect(screen.getByTestId('heatmap-cell-6-23').getAttribute('data-status')).toBe('vigilance');
    // Cellule absente → missing
    expect(screen.getByTestId('heatmap-cell-0-0').getAttribute('data-status')).toBe('missing');
    expect(screen.getByTestId('heatmap-cell-3-15').getAttribute('data-status')).toBe('missing');
  });

  it('loading state visible', () => {
    render(<WeekProfileHeatmap matrix={[]} loading />);
    expect(screen.getByTestId('week-profile-heatmap-loading')).toBeTruthy();
  });

  it('compteur cellules affiché quand données présentes', () => {
    render(<WeekProfileHeatmap matrix={buildFullMatrix()} />);
    const counter = screen.getByTestId('heatmap-cell-count');
    expect(counter.textContent).toContain('168/168');
  });

  it('provenance backend affichée si fournie', () => {
    render(
      <WeekProfileHeatmap
        matrix={buildFullMatrix()}
        provenance={{ service: 'energy_orchestration.week_profile' }}
      />
    );
    const prov = screen.getByTestId('heatmap-provenance');
    expect(prov.textContent).toContain('energy_orchestration.week_profile');
  });

  it('jour=Lun (0) et jour=Dim (6) bien rendus comme rowheader', () => {
    render(<WeekProfileHeatmap matrix={buildFullMatrix()} />);
    expect(screen.getByTestId('heatmap-row-0')).toBeTruthy();
    expect(screen.getByTestId('heatmap-row-6')).toBeTruthy();
  });
});

describe('WeekProfileHeatmap — doctrine zéro calcul métier', () => {
  it('le composant ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/WeekProfileHeatmap.jsx'), 'utf8');
    // Pas d'agrégation métier sur kwh/kw_avg FE
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.kwh/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.kw_avg/);
    // Pas de calcul talon nuit / weekend / pic FE
    expect(src).not.toMatch(/const\s+nightBaseload\s*=/);
    expect(src).not.toMatch(/const\s+weekendPct\s*=/);
    expect(src).not.toMatch(/peakKw\s*=\s*Math\.max/);
    // Pas de détection de pic via Math.max sur arrays métier
    expect(src).not.toMatch(/Math\.max\s*\(\s*\.{3}\s*\w+\.map\s*\(/);
    // Pas de scoring qualité FE
    expect(src).not.toMatch(/score\s*=\s*\(\s*\w+\s*\/\s*\w+\s*\)\s*\*/);
    // Pas de CO₂/coût FE
    expect(src).not.toMatch(/kwhToCo2|emission_factor|co2Factor/);
    expect(src).not.toMatch(/cost_eur\s*=\s*\w+\s*\*/);
  });
});
