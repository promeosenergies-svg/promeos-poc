// @vitest-environment jsdom
/**
 * PROMEOS — Tests OffHoursAnalysisCard (Sprint Énergie P3.2).
 */
import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import OffHoursAnalysisCard from '../ui/energy/OffHoursAnalysisCard';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'helper backend',
  period: '2026-04-01 → 2026-05-01',
  confidence: 0.9,
  assumptions: ['timezone Europe/Paris'],
});

function buildKpi(key, label, value, unit, state = 'sain') {
  return {
    key,
    label,
    value,
    unit,
    state,
    provenance: PROV(`energy_orchestration.opening_hours_analysis._compute_kpis`),
  };
}

function buildPayload(overrides = {}) {
  return {
    scope: { kind: 'site', id: 1, org_id: 1 },
    period: { label: 'custom', timezone: 'Europe/Paris' },
    schedule: {
      timezone: 'Europe/Paris',
      source: 'declared',
      weekly_schedule: Array.from({ length: 7 }, (_, d) => ({
        day_of_week: d,
        label: ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'][d],
        is_open: d < 5,
        ranges: d < 5 ? [{ start_time: '08:00', end_time: '19:00' }] : [],
      })),
      exceptions: [],
      provenance: PROV('energy_orchestration.opening_hours_analysis._load_opening_schedule'),
    },
    kpis: {
      off_hours_kwh: buildKpi('off_hours_kwh', 'Conso hors horaires', 2048.46, 'kWh', 'critique'),
      off_hours_share_pct: buildKpi(
        'off_hours_share_pct',
        'Part hors horaires',
        27.1,
        '%',
        'critique'
      ),
      weekend_off_hours_kwh: buildKpi(
        'weekend_off_hours_kwh',
        'Week-end hors horaires',
        1500,
        'kWh',
        'vigilance'
      ),
      night_baseload_kw: buildKpi('night_baseload_kw', 'Talon nuit', 4.0, 'kW', 'sain'),
    },
    slots: [],
    top_off_hours: [],
    recommendations: [
      {
        title: 'Consommation hors horaires critique',
        description: 'Sur la période, 27,1 % de la consommation est hors horaires.',
        severity: 'critical',
        cta_label: "Créer une action d'analyse",
        cta_to: '/action-center-v4',
        provenance: PROV('energy_orchestration.opening_hours_analysis._compute_recommendations'),
      },
    ],
    warnings: [],
    empty_state: null,
    provenance: PROV('energy_orchestration.opening_hours_analysis.build_off_hours_analysis'),
    ...overrides,
  };
}

afterEach(() => cleanup());

describe('OffHoursAnalysisCard', () => {
  it('rend le titre métier « Consommation hors horaires »', () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    expect(screen.getByText('Consommation hors horaires')).toBeTruthy();
  });

  it('affiche la sous-ligne FR métier', () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    expect(screen.getByText(/Comparez la consommation mesurée aux horaires déclarés/)).toBeTruthy();
  });

  it('expose les 4 KPI backend (data-testid)', () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    expect(screen.getByTestId('kpi-off-hours-kwh')).toBeTruthy();
    expect(screen.getByTestId('kpi-off-hours-share-pct')).toBeTruthy();
    expect(screen.getByTestId('kpi-weekend-off-hours-kwh')).toBeTruthy();
    expect(screen.getByTestId('kpi-night-baseload-kw')).toBeTruthy();
  });

  it('rend la grille hebdomadaire avec les 7 jours', () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    for (let d = 0; d < 7; d++) {
      expect(screen.getByTestId(`off-hours-day-${d}`)).toBeTruthy();
    }
  });

  it('expose le badge horaires déclarés', () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    const summary = screen.getByTestId('off-hours-schedule-summary');
    expect(summary.textContent).toContain('Horaires déclarés');
    expect(summary.querySelector('[data-source="declared"]')).toBeTruthy();
  });

  it("rend les recommandations avec CTA Centre d'action", () => {
    render(<OffHoursAnalysisCard payload={buildPayload()} />);
    expect(screen.getByTestId('off-hours-recommendations')).toBeTruthy();
    const cta = screen.getByTestId('off-hours-recommendation-cta');
    expect(cta.getAttribute('href')).toBe('/action-center-v4');
  });

  it('affiche empty_state si horaires manquants', () => {
    const payload = buildPayload({
      schedule: {
        timezone: 'Europe/Paris',
        source: 'missing',
        weekly_schedule: [],
        exceptions: [],
        provenance: PROV('energy_orchestration.opening_hours_analysis._missing_schedule'),
      },
      empty_state: "Horaires d'ouverture non renseignés pour ce site.",
      kpis: {},
      recommendations: [],
    });
    render(<OffHoursAnalysisCard payload={payload} />);
    expect(screen.getByTestId('off-hours-empty-state')).toBeTruthy();
    expect(screen.getByText(/Horaires d'ouverture non renseignés/)).toBeTruthy();
  });

  it('rend loading state', () => {
    render(<OffHoursAnalysisCard payload={null} loading />);
    expect(screen.getByTestId('off-hours-loading')).toBeTruthy();
  });

  it('retourne null si payload manquant et non-loading', () => {
    const { container } = render(<OffHoursAnalysisCard payload={null} />);
    expect(container.textContent).toBe('');
  });
});

describe('OffHoursAnalysisCard — doctrine zéro calcul métier', () => {
  it('ne contient aucun calcul share / cost / status', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/OffHoursAnalysisCard.jsx'), 'utf8');
    // Pas de calcul share = a / b * 100
    expect(src).not.toMatch(/share\s*=\s*\w+\s*\/\s*\w+\s*\*/);
    // Pas de cost = kwh * price
    expect(src).not.toMatch(/cost\s*=\s*\w+\.kwh\s*\*/);
    // Pas de classification status FE
    expect(src).not.toMatch(/status\s*=\s*\(\s*\w+\s*[<>]/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
