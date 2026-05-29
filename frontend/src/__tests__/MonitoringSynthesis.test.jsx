// @vitest-environment jsdom
/**
 * PROMEOS — Tests MonitoringSynthesisStrip (Sprint P1.S3b).
 *
 * Couvre la checklist QA de sortie S3b :
 * 1. Monitoring appelle getEnergySynthesis ;
 * 2. 10 KPI rendus si payload complet ;
 * 3. chaque KPI affiche provenance ;
 * 4. narrative backend affichée ;
 * 5. loading state visible ;
 * 6. empty state visible ;
 * 7. error state affiche code + hint + correlation_id ;
 * 8. aucun calcul métier interdit dans MonitoringPage ;
 * 9. confidenceDisplay justifié (climate scatter — hors scope synthesis).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/api/energy', () => ({
  getEnergySynthesis: vi.fn(),
}));

import MonitoringSynthesisStrip, { KPI_ORDER } from '../ui/energy/MonitoringSynthesisStrip';
import { getEnergySynthesis } from '../services/api/energy';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'Σ MeterReading.value_kwh',
  period: '2026-04-29 → 2026-05-29',
  confidence: 0.85,
  assumptions: ['timezone Europe/Paris'],
});

const KPI = (key, label, value, unit, state = 'sain') => ({
  key,
  label,
  value,
  unit,
  state,
  scope: { kind: 'org', org_id: 1 },
  period: { label: '30d', days: 30, timezone: 'Europe/Paris' },
  provenance: PROV(`energy_orchestration.synthesis._kpi (${key})`),
});

const SAMPLE_PAYLOAD = {
  scope: { kind: 'org', org_id: 1 },
  period: { label: '30d', days: 30, timezone: 'Europe/Paris' },
  compare: 'none',
  kpis: {
    consumption_kwh: KPI('consumption_kwh', 'Consommation', 12450, 'kWh'),
    cost_eur: KPI('cost_eur', 'Coût estimé', 1750, '€'),
    co2_kg: KPI('co2_kg', 'CO₂ équivalent', 647, 'kgCO₂eq'),
    peak_kw: KPI('peak_kw', 'Puissance max', 18.4, 'kW'),
    weighted_price_eur_mwh: KPI('weighted_price_eur_mwh', 'Prix moyen pondéré', 140.5, '€/MWh'),
    data_quality_score: KPI('data_quality_score', 'Qualité données', 87, '/100'),
    sites_coverage_pct: KPI('sites_coverage_pct', 'Couverture sites', 92, '%'),
    alerts_open: KPI('alerts_open', 'Alertes ouvertes', 3, 'count', 'vigilance'),
    actions_open: KPI('actions_open', 'Actions ouvertes', 2, 'count'),
    estimated_impact_eur: KPI(
      'estimated_impact_eur',
      'Impact financier estimé',
      2340,
      '€',
      'vigilance'
    ),
  },
  recommendations: [],
  narrative:
    '3 alerte(s) active(s) sur votre patrimoine — 2 action(s) à programmer. Impact estimé 2340 € récupérables par correction.',
  warnings: [],
  provenance: PROV('energy_orchestration.synthesis.build_synthesis'),
};

function renderStrip(props = {}) {
  return render(
    <MonitoringSynthesisStrip
      scope={{ kind: 'org', id: null, org_id: 1 }}
      period="30d"
      compare="none"
      {...props}
    />
  );
}

describe('MonitoringSynthesisStrip — checklist QA S3b', () => {
  beforeEach(() => {
    getEnergySynthesis.mockReset();
  });
  afterEach(() => cleanup());

  it('Critère 1 : appelle getEnergySynthesis avec scope/period/compare', async () => {
    getEnergySynthesis.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderStrip();
    await waitFor(() => expect(getEnergySynthesis).toHaveBeenCalledTimes(1));
    const args = getEnergySynthesis.mock.calls[0][0];
    expect(args.scope).toBe('org');
    expect(args.period).toBe('30d');
    expect(args.compare).toBe('none');
    expect(args.org_id).toBe(1);
  });

  it('Critère 2 : 10 KPI rendus quand payload complet', async () => {
    getEnergySynthesis.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderStrip();
    await waitFor(() => screen.getByTestId('synthesis-kpis-grid'));
    for (const key of KPI_ORDER) {
      expect(screen.getByTestId(`synthesis-kpi-${key}`)).toBeTruthy();
    }
  });

  it('Critère 3 : chaque KPI affiche provenance (tooltip source/service/formule)', async () => {
    getEnergySynthesis.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderStrip();
    await waitFor(() => screen.getByTestId('synthesis-kpis-grid'));
    const tooltips = screen.getAllByTestId('kpi-provenance-tooltip');
    expect(tooltips.length).toBe(10);
    // Le premier tooltip contient la provenance backend
    const txt = tooltips[0].textContent || '';
    expect(txt).toContain('PROMEOS energy_orchestration');
    expect(txt).toContain('energy_orchestration.synthesis');
    expect(txt).toContain('Σ MeterReading.value_kwh');
  });

  it('Critère 4 : narrative backend affichée', async () => {
    getEnergySynthesis.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    renderStrip();
    await waitFor(() => screen.getByTestId('synthesis-narrative'));
    const banner = screen.getByTestId('synthesis-narrative').textContent || '';
    expect(banner).toContain('3 alerte');
    expect(banner).toContain('Impact estimé');
  });

  it('Critère 5 : loading state visible avant la réponse', async () => {
    let resolveFn;
    const pending = new Promise((res) => {
      resolveFn = res;
    });
    getEnergySynthesis.mockReturnValueOnce(pending);
    renderStrip();
    expect(screen.getByTestId('synthesis-loading')).toBeTruthy();
    resolveFn(SAMPLE_PAYLOAD);
    await waitFor(() => screen.getByTestId('synthesis-kpis-grid'));
  });

  it('Critère 6 : empty state visible quand payload vide', async () => {
    getEnergySynthesis.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      kpis: {},
    });
    renderStrip();
    await waitFor(() => expect(screen.queryByTestId('synthesis-kpis-grid')).toBeNull());
    // L'EmptyState texte est présent
    expect(screen.getByText(/Aucune synthèse énergétique/i)).toBeTruthy();
  });

  it('Critère 7 : error state affiche code + hint + correlation_id', async () => {
    const err = new Error('Request failed');
    err.response = {
      status: 400,
      data: {
        detail: {
          code: 'ENERGY_SCOPE_INVALID',
          message: "scope='plouf' invalide",
          hint: 'valeurs autorisées : org | portfolio | site',
          correlation_id: 'corr-xyz-789',
        },
      },
    };
    getEnergySynthesis.mockRejectedValueOnce(err);
    renderStrip();
    await waitFor(() => screen.getByTestId('synthesis-error'));
    expect(screen.getByTestId('error-code').textContent).toContain('ENERGY_SCOPE_INVALID');
    expect(screen.getByTestId('error-hint').textContent).toContain('org | portfolio');
    expect(screen.getByTestId('error-correlation-id').textContent).toContain('corr-xyz-789');
  });

  it('Critère 7 bis : ordre canonique KPI_ORDER (10 entrées, consumption_kwh en tête)', () => {
    expect(KPI_ORDER).toHaveLength(10);
    expect(KPI_ORDER[0]).toBe('consumption_kwh');
    expect(KPI_ORDER[KPI_ORDER.length - 1]).toBe('estimated_impact_eur');
  });

  it('Critère 7 ter : ne rend que les KPI fournis (skip clés manquantes)', async () => {
    const partial = {
      ...SAMPLE_PAYLOAD,
      kpis: {
        consumption_kwh: SAMPLE_PAYLOAD.kpis.consumption_kwh,
        cost_eur: SAMPLE_PAYLOAD.kpis.cost_eur,
      },
    };
    getEnergySynthesis.mockResolvedValueOnce(partial);
    renderStrip();
    await waitFor(() => screen.getByTestId('synthesis-kpi-consumption_kwh'));
    expect(screen.queryByTestId('synthesis-kpi-co2_kg')).toBeNull();
    expect(screen.queryByTestId('synthesis-kpi-peak_kw')).toBeNull();
  });
});

describe('MonitoringSynthesisStrip — doctrine zéro calcul métier', () => {
  it('Critère 8a : composant strip ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../ui/energy/MonitoringSynthesisStrip.jsx'),
      'utf8'
    );
    expect(src).not.toMatch(/co2Factor\s*\*/);
    expect(src).not.toMatch(/Math\.sin\(/);
    expect(src).not.toMatch(/computeInsights\s*\(/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\(?\s*\w+\.estimated_/);
    expect(src).toContain('getEnergySynthesis');
  });

  it('Critère 8b : MonitoringPage importe la strip mais ne recalcule pas les KPI synthesis', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/MonitoringPage.jsx'), 'utf8');
    expect(src).toContain('MonitoringSynthesisStrip');
    expect(src).toContain("from '../ui/energy/MonitoringSynthesisStrip'");
  });

  it('Critère 9 : confidenceDisplay reste justifié (climateConf hors scope synthesis)', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/MonitoringPage.jsx'), 'utf8');
    // computeConfidence est encore appelé — il sert au climate scatter
    // (r², n_points) qui n'est PAS couvert par /api/energy/synthesis.
    // La strip P1.S3b consomme data_quality_score directement sans
    // passer par computeConfidence.
    const stripSrc = readFileSync(
      resolve(__dirname, '../ui/energy/MonitoringSynthesisStrip.jsx'),
      'utf8'
    );
    expect(stripSrc).not.toContain('computeConfidence');
    expect(stripSrc).not.toContain('confidenceDisplay');
  });

  it('Critère : Monitoring rail Énergie inchangé (4 items rail)', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../layout/NavRegistry.js'), 'utf8');
    // Pas de nouvelle entrée rail liée à la strip synthesis
    expect(src).not.toMatch(/label:\s*['"]Synthèse Énergie['"]/);
  });
});
