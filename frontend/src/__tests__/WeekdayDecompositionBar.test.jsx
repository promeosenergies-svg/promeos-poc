// @vitest-environment jsdom
/**
 * PROMEOS — Tests WeekdayDecompositionBar (Sprint P3.1).
 */
import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import WeekdayDecompositionBar from '../ui/energy/WeekdayDecompositionBar';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'total_kwh par jour ÷ total_global × 100',
  period: 'custom',
});

const DECOMPOSITION = [
  {
    day_of_week: 0,
    label: 'Lundi',
    total_kwh: 1500,
    avg_kwh_per_day: 750,
    share_pct: 18.0,
    n_days: 2,
    state: 'sain',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 1,
    label: 'Mardi',
    total_kwh: 1700,
    avg_kwh_per_day: 850,
    share_pct: 20.4,
    n_days: 2,
    state: 'vigilance',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 2,
    label: 'Mercredi',
    total_kwh: 1600,
    avg_kwh_per_day: 800,
    share_pct: 19.2,
    n_days: 2,
    state: 'sain',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 3,
    label: 'Jeudi',
    total_kwh: 2100,
    avg_kwh_per_day: 1050,
    share_pct: 25.2,
    n_days: 2,
    state: 'critique',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 4,
    label: 'Vendredi',
    total_kwh: 1800,
    avg_kwh_per_day: 900,
    share_pct: 21.6,
    n_days: 2,
    state: 'vigilance',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 5,
    label: 'Samedi',
    total_kwh: 700,
    avg_kwh_per_day: 350,
    share_pct: 8.4,
    n_days: 2,
    state: 'sain',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
  {
    day_of_week: 6,
    label: 'Dimanche',
    total_kwh: 600,
    avg_kwh_per_day: 300,
    share_pct: 7.2,
    n_days: 2,
    state: 'sain',
    provenance: PROV('loadcurve._compute_weekday_decomposition'),
  },
];

const COMPARISON = {
  weekday_kwh: 8700,
  weekend_kwh: 1300,
  weekend_share_pct: 13.0,
  provenance: PROV('loadcurve._compute_weekday_weekend_comparison'),
};

afterEach(() => cleanup());

describe('WeekdayDecompositionBar', () => {
  it('rend 7 barres si décomposition complète', () => {
    render(<WeekdayDecompositionBar decomposition={DECOMPOSITION} />);
    for (let d = 0; d < 7; d++) {
      expect(screen.getByTestId(`weekday-decomp-row-${d}`)).toBeTruthy();
    }
  });

  it('propage les states (data-state)', () => {
    render(<WeekdayDecompositionBar decomposition={DECOMPOSITION} />);
    expect(screen.getByTestId('weekday-decomp-row-3').getAttribute('data-state')).toBe('critique');
    expect(screen.getByTestId('weekday-decomp-row-1').getAttribute('data-state')).toBe('vigilance');
    expect(screen.getByTestId('weekday-decomp-row-0').getAttribute('data-state')).toBe('sain');
  });

  it('affiche total_kwh et share_pct backend', () => {
    render(<WeekdayDecompositionBar decomposition={DECOMPOSITION} />);
    const lundi = screen.getByTestId('weekday-decomp-row-0').textContent;
    expect(lundi).toMatch(/1\s500\s?kWh/);
    expect(lundi).toMatch(/18\s?%/);
  });

  it('rend la comparaison jours ouvrés vs week-end si fournie', () => {
    render(<WeekdayDecompositionBar decomposition={DECOMPOSITION} comparison={COMPARISON} />);
    const cmp = screen.getByTestId('weekday-weekend-comparison');
    expect(cmp.textContent).toContain('Jours ouvrés');
    expect(cmp.textContent).toContain('Week-end');
    expect(cmp.textContent).toMatch(/13\s?%/);
  });

  it('expose data-testid provenance', () => {
    render(<WeekdayDecompositionBar decomposition={DECOMPOSITION} />);
    expect(screen.getByTestId('weekday-decomposition-provenance')).toBeTruthy();
  });

  it('retourne null si décomposition vide', () => {
    const { container } = render(<WeekdayDecompositionBar decomposition={[]} />);
    expect(container.textContent).toBe('');
  });
});

describe('WeekdayDecompositionBar — doctrine zéro calcul métier', () => {
  it('ne contient aucun calcul de share_pct / state', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../ui/energy/WeekdayDecompositionBar.jsx'),
      'utf8'
    );
    expect(src).not.toMatch(/share_pct\s*=\s*\w+\s*\/\s*\w+\s*\*/);
    expect(src).not.toMatch(/state\s*=\s*\(\s*share_pct\s*[<>]/);
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
