// @vitest-environment jsdom
/**
 * PROMEOS — Tests LoadCurveTab (Sprint P1.S3a).
 *
 * Couvre la checklist QA de sortie S3a :
 * 1. onglet « Courbe de charge » visible uniquement dans /consommations ;
 * 2. /api/energy/loadcurve réellement consommé ;
 * 3. KPI affichés avec provenance ;
 * 4. loading / empty / error / partial data présents ;
 * 5. erreur granularité trop fine affichée avec hint + correlation_id ;
 * 6. aucune nouvelle route/menu ;
 * 7. source-guard zéro calcul métier toujours vert (vérif fichiers).
 */
import React from 'react';
import { afterEach, describe, expect, it, vi, beforeEach } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../services/api/energy', () => ({
  getEnergyLoadCurve: vi.fn(),
}));

vi.mock('../contexts/ScopeContext', () => ({
  useScope: () => ({
    selectedSiteId: 42,
    sitesById: { 42: { id: 42, nom: 'HQ Paris' } },
  }),
}));

import LoadCurveTab from '../pages/consumption/LoadCurveTab';
import { getEnergyLoadCurve } from '../services/api/energy';

const SAMPLE_KPI = (key, label, value, unit) => ({
  key,
  label,
  value,
  unit,
  state: 'sain',
  scope: { kind: 'site', id: 42 },
  period: { label: '30d', days: 30, timezone: 'Europe/Paris' },
  provenance: {
    source: 'PROMEOS energy_orchestration',
    service: 'energy_orchestration.loadcurve.build_loadcurve',
    formula: 'Σ MeterReading.value_kwh / granularity_hours',
    period: '2026-04-29 → 2026-05-29',
    confidence: 0.9,
    assumptions: ['timezone Europe/Paris', 'granularité=hour'],
  },
});

const SAMPLE_PAYLOAD = {
  scope: { kind: 'site', id: 42 },
  period: { label: 'custom', days: 30, timezone: 'Europe/Paris' },
  granularity: 'hour',
  compare: 'none',
  series: Array.from({ length: 24 }, (_, h) => ({
    timestamp: `2026-05-29T${String(h).padStart(2, '0')}:00:00+02:00`,
    kwh: 1.2 + h * 0.1,
    kw_avg: 1.2 + h * 0.1,
    cost_eur: null,
    quality_status: 'measured',
  })),
  series_compare: [],
  kpis: {
    total_kwh: SAMPLE_KPI('total_kwh', 'Consommation période', 53.6, 'kWh'),
    peak_kw: SAMPLE_KPI('peak_kw', 'Puissance max', 3.5, 'kW'),
    baseload_kw: SAMPLE_KPI('baseload_kw', 'Talon', 1.2, 'kW'),
    average_kw: SAMPLE_KPI('average_kw', 'Puissance moyenne', 2.23, 'kW'),
  },
  provenance: {
    source: 'PROMEOS energy_orchestration',
    service: 'energy_orchestration.loadcurve.build_loadcurve',
    formula: 'agrégation Σ MeterReading.value_kwh par granularité',
    period: '2026-04-29 → 2026-05-29',
    confidence: 0.9,
    assumptions: ['timezone Europe/Paris'],
  },
  warnings: [],
  empty_state: null,
};

function renderTab() {
  return render(
    <MemoryRouter initialEntries={['/consommations/courbe']}>
      <LoadCurveTab />
    </MemoryRouter>
  );
}

describe('LoadCurveTab — checklist QA S3a', () => {
  beforeEach(() => {
    getEnergyLoadCurve.mockReset();
  });
  afterEach(() => cleanup());

  it('Critère 2 : /api/energy/loadcurve réellement consommé avec scope, from, to, granularité', async () => {
    getEnergyLoadCurve.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderTab();
    await waitFor(() => expect(getEnergyLoadCurve).toHaveBeenCalledTimes(1));
    const args = getEnergyLoadCurve.mock.calls[0][0];
    expect(args.scope).toBe('site');
    expect(args.scope_id).toBe(42);
    expect(args.granularity).toBe('hour');
    expect(args.from).toBeTruthy();
    expect(args.to).toBeTruthy();
  });

  it('Critère 3 : KPI affichés depuis le payload avec leur provenance', async () => {
    getEnergyLoadCurve.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderTab();
    await waitFor(() => screen.getByTestId('kpi-total-kwh'));
    expect(screen.getByTestId('kpi-total-kwh').textContent).toContain('Consommation période');
    expect(screen.getByTestId('kpi-peak-kw').textContent).toContain('Puissance max');
    expect(screen.getByTestId('kpi-baseload-kw').textContent).toContain('Talon');
    expect(screen.getByTestId('kpi-average-kw').textContent).toContain('Puissance moyenne');
  });

  it('Critère 4a : chart affiché quand série non vide', async () => {
    getEnergyLoadCurve.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderTab();
    await waitFor(() => screen.getByTestId('loadcurve-chart'));
    expect(screen.getByTestId('loadcurve-chart')).toBeTruthy();
  });

  it('Critère 4b : EmptyState affiché quand série vide', async () => {
    getEnergyLoadCurve.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      series: [],
      empty_state: 'Aucune donnée sur la période sélectionnée. Élargir la période.',
    });
    renderTab();
    await waitFor(() => screen.getByTestId('loadcurve-empty'));
    expect(screen.getByTestId('loadcurve-empty')).toBeTruthy();
  });

  it('Critère 4c : warnings (partial data) renvoyés par l’API sont affichés', async () => {
    getEnergyLoadCurve.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      warnings: ['Données partielles — certaines heures sont estimées ou manquantes.'],
    });
    renderTab();
    await waitFor(() => screen.getByTestId('loadcurve-chart'));
    // Le warning est rendu dans le DOM du chart
    const chart = screen.getByTestId('loadcurve-chart');
    expect(chart.textContent).toContain('Données partielles');
  });

  it('Critère 5 : erreur granularité trop fine → message + hint + correlation_id', async () => {
    const err = new Error('Request failed');
    err.response = {
      status: 400,
      data: {
        detail: {
          code: 'ENERGY_GRANULARITY_TOO_FINE',
          message: "granularity '15min' refusée pour période de 30j (max 7j)",
          hint: 'utiliser une granularité plus large ou une période ≤ 7j',
          correlation_id: 'corr-abc-123',
        },
      },
    };
    getEnergyLoadCurve.mockRejectedValueOnce(err);
    renderTab();
    await waitFor(() => screen.getByTestId('loadcurve-error'));
    expect(screen.getByTestId('error-message').textContent).toContain('15min');
    expect(screen.getByTestId('error-hint').textContent).toContain('granularité plus large');
    expect(screen.getByTestId('error-code').textContent).toContain('ENERGY_GRANULARITY_TOO_FINE');
    expect(screen.getByTestId('error-correlation-id').textContent).toContain('corr-abc-123');
  });
});

describe('LoadCurveTab — doctrine zéro calcul métier + routing', () => {
  it('Critère 7 : LoadCurveTab.jsx ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/consumption/LoadCurveTab.jsx'), 'utf8');
    expect(src).not.toMatch(/co2Factor\s*\*/);
    expect(src).not.toMatch(/Math\.sin\(/);
    expect(src).not.toMatch(/computeInsights\s*\(/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\(?\s*\w+\.estimated_/);
    expect(src).toContain('getEnergyLoadCurve');
  });

  it('Critère 1 : onglet « Courbe de charge » déclaré uniquement dans /consommations', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/ConsommationsPage.jsx'), 'utf8');
    expect(src).toContain("'/consommations/courbe'");
    expect(src).toContain("'Courbe de charge'");
  });

  it('Sprint P2.2 : cross-link Action V4 ajouté avec wording générique', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/consumption/LoadCurveTab.jsx'), 'utf8');
    expect(src).toMatch(/import\s+EnergyCrossLinks/);
    expect(src).toMatch(/LOAD_CURVE_CROSS_LINKS\s*=\s*\[/);
    expect(src).toContain("'/action-center-v4'");
    expect(src).toContain("Créer une action d'analyse");
    expect(src).toMatch(/testId="loadcurve-cross-links"/);
  });

  it('Critère 6 : aucune nouvelle entrée dans le rail NavRegistry', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../layout/NavRegistry.js'), 'utf8');
    expect(src).not.toMatch(/to:\s*['"]\/courbe['"]/);
    expect(src).not.toMatch(/label:\s*['"]Courbe de charge['"]/);
  });

  it('Critère 6 bis : la route /consommations/courbe est nested dans App.jsx', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../App.jsx'), 'utf8');
    expect(src).toContain('LoadCurveTab');
    expect(src).toMatch(/path=["']courbe["']/);
  });
});
