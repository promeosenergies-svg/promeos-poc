// @vitest-environment jsdom
/**
 * PROMEOS — Tests WeekdayOverlayChart (Sprint P3.1).
 */
import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import WeekdayOverlayChart from '../ui/energy/WeekdayOverlayChart';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'moyenne arithmétique par (day_of_week, hour)',
  period: 'custom',
  confidence: 0.85,
  assumptions: ['timezone Europe/Paris'],
});

function buildCurves() {
  const labels = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
  return labels.map((label, d) => ({
    day_of_week: d,
    label,
    points: Array.from({ length: 24 }, (_, h) => ({
      hour: h,
      avg_kwh: 10 + h * 0.5,
      avg_kw: 10 + h * 0.5,
      n_points: 2,
      quality_status: 'measured',
    })),
    provenance: PROV(`energy_orchestration.loadcurve._compute_weekday_overlay`),
  }));
}

afterEach(() => cleanup());

describe('WeekdayOverlayChart — rendu 7 jours × 24h', () => {
  it('rend le chart quand 7 courbes fournies', () => {
    render(<WeekdayOverlayChart curves={buildCurves()} display="kwh" />);
    expect(screen.getByTestId('weekday-overlay-chart')).toBeTruthy();
  });

  it('affiche le titre « Profil moyen par jour »', () => {
    render(<WeekdayOverlayChart curves={buildCurves()} />);
    expect(screen.getByText(/Profil moyen par jour/)).toBeTruthy();
  });

  it('affiche le sous-titre microcopy P3.1', () => {
    render(<WeekdayOverlayChart curves={buildCurves()} />);
    expect(screen.getByText(/Courbe moyenne du lundi au dimanche/)).toBeTruthy();
  });

  it('expose data-testid provenance (visible source)', () => {
    render(<WeekdayOverlayChart curves={buildCurves()} />);
    expect(screen.getByTestId('weekday-overlay-provenance')).toBeTruthy();
  });

  it('retourne null si curves vide', () => {
    const { container } = render(<WeekdayOverlayChart curves={[]} />);
    expect(container.textContent).toBe('');
  });

  it('retourne null si curves null', () => {
    const { container } = render(<WeekdayOverlayChart curves={null} />);
    expect(container.textContent).toBe('');
  });

  it('bascule kwh → kw via prop display', () => {
    const { rerender } = render(<WeekdayOverlayChart curves={buildCurves()} display="kwh" />);
    expect(screen.getByTestId('weekday-overlay-chart')).toBeTruthy();
    rerender(<WeekdayOverlayChart curves={buildCurves()} display="kw" />);
    expect(screen.getByTestId('weekday-overlay-chart')).toBeTruthy();
  });
});

describe('WeekdayOverlayChart — doctrine zéro calcul métier', () => {
  it("ne contient aucun calcul d'agrégation FE", () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/WeekdayOverlayChart.jsx'), 'utf8');
    // Pas de moyenne calculée FE
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.avg_kwh/);
    expect(src).not.toMatch(/sum\s*=\s*\w+\s*\+\s*\w+\.kwh/);
    // Pas de calcul share / state
    expect(src).not.toMatch(/share\s*=\s*\w+\s*\/\s*\w+\s*\*/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
