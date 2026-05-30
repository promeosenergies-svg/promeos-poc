// @vitest-environment jsdom
/**
 * PROMEOS — Tests MarketExposureTab (Sprint P1.S6).
 *
 * Couvre la checklist QA :
 * 1. onglet visible dans /consommations ;
 * 2. scope=org → SiteRequiredState + aucun appel API ;
 * 3. getMarketExposure appelé si site sélectionné ;
 * 4. loading ;
 * 5. empty ;
 * 6. error code + hint + correlation_id ;
 * 7. 8 KPI + provenance ;
 * 8. exposure score visible ;
 * 9. top heures chères visibles ;
 * 10. prix négatifs / heures favorables visibles ;
 * 11. baseload comparison visible ;
 * 12. warning simulation indicative visible ;
 * 13. zéro calcul métier interdit.
 */
import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/api/energy', () => ({
  getMarketExposure: vi.fn(),
}));

// Sprint P1.S7 — EnergyCrossLinks utilise <Link> de react-router-dom.
// Préserve MemoryRouter et override seulement Link (évite cross-pollution
// avec EnergyCrossLinks.test.jsx qui utilise MemoryRouter pour de vrai).
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    Link: ({ to, children, replace: _replace, state: _state, ...rest }) => (
      <a href={to} {...rest}>
        {children}
      </a>
    ),
  };
});

const mockSetSite = vi.fn();
let _scopeOverride = null;

vi.mock('../contexts/ScopeContext', () => ({
  useScope: () =>
    _scopeOverride
      ? { ...{ setSite: mockSetSite }, ..._scopeOverride }
      : {
          selectedSiteId: 42,
          scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: 42 },
          setSite: mockSetSite,
        },
}));

function setScope(next) {
  _scopeOverride = next;
}

import MarketExposureTab, {
  KPI_ORDER,
  DEFAULT_PERIOD,
  DEFAULT_MARKET,
  DEFAULT_ZONE,
} from '../pages/consumption/MarketExposureTab';
import { getMarketExposure } from '../services/api/energy';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'spot_cost = Σ(kwh × spot_price / 1000)',
  period: '12 mois glissants',
  confidence: 0.78,
  assumptions: ['EPEX day-ahead FR', 'timezone Europe/Paris'],
});

const KPI = (key, label, value, unit, state = 'sain') => ({
  key,
  label,
  value,
  unit,
  state,
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '12m', days: 365, timezone: 'Europe/Paris' },
  provenance: PROV(`market_exposure._kpi (${key})`),
});

const TOP_HOUR = (rank, ts, price, kwh, cost, action) => ({
  timestamp: ts,
  spot_price_eur_mwh: price,
  kwh,
  cost_eur: cost,
  rank,
  recommended_action: action,
  provenance: PROV(`market_exposure._compute_top_expensive_hours`),
});

const FAV_HOUR = (ts, price, reason) => ({
  timestamp: ts,
  spot_price_eur_mwh: price,
  kwh: 20.0,
  reason,
  provenance: PROV(`market_exposure._compute_favorable_hours`),
});

const SAMPLE_PAYLOAD = {
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '12m', days: 365, timezone: 'Europe/Paris' },
  market: {
    type: 'day_ahead',
    zone: 'FR',
    source: 'MktPrice canonique',
    price_unit: '€/MWh',
    provenance: PROV('mkt_price.canonical'),
  },
  kpis: {
    spot_cost_theoretical_eur: KPI('spot_cost_theoretical_eur', 'Coût spot théorique', 33200, '€'),
    spot_avg_simple_eur_mwh: KPI('spot_avg_simple_eur_mwh', 'Spot moyen simple', 168.0, '€/MWh'),
    spot_avg_weighted_eur_mwh: KPI(
      'spot_avg_weighted_eur_mwh',
      'Spot moyen pondéré',
      176.4,
      '€/MWh'
    ),
    baseload_cost_eur: KPI('baseload_cost_eur', 'Coût ruban baseload', 31200, '€'),
    delta_vs_baseload_eur: KPI(
      'delta_vs_baseload_eur',
      'Écart vs baseload',
      2000,
      '€',
      'vigilance'
    ),
    top_10pct_expensive_hours_cost_pct: KPI(
      'top_10pct_expensive_hours_cost_pct',
      'Top 10 % heures chères',
      27.5,
      '%',
      'vigilance'
    ),
    negative_price_consumption_pct: KPI(
      'negative_price_consumption_pct',
      'Conso heures prix négatif',
      2.1,
      '%'
    ),
    exposure_score: KPI('exposure_score', "Score d'exposition spot", 58, '/100', 'vigilance'),
  },
  series: [],
  top_expensive_hours: [
    TOP_HOUR(
      1,
      '2026-01-15T19:00:00+01:00',
      420.5,
      85.4,
      35.91,
      'Éviter démarrage cycle process intensif.'
    ),
    TOP_HOUR(
      2,
      '2026-02-08T08:00:00+01:00',
      380.0,
      72.1,
      27.4,
      'Décaler chauffage électrique vers 10h.'
    ),
  ],
  favorable_hours: [
    FAV_HOUR('2026-03-02T03:00:00+01:00', 12.5, 'prix bas'),
    FAV_HOUR('2026-03-15T13:00:00+01:00', -5.0, 'prix négatif'),
    FAV_HOUR('2026-04-10T13:00:00+02:00', 8.0, 'heure solaire'),
  ],
  baseload_comparison: {
    real_profile_cost_eur: 33200,
    baseload_cost_eur: 31200,
    delta_eur: 2000,
    delta_eur_mwh: 10.2,
    formula: 'coût spot pondéré profil réel vs consommation plate équivalente',
    provenance: PROV('market_exposure._compute_baseload_comparison'),
  },
  simulation: {
    label: 'Déplacement indicatif',
    flexible_share_pct: 20.0,
    estimated_delta_eur: -850,
    warning: "Simulation indicative — ne constitue pas une promesse d'économie.",
    provenance: PROV('market_exposure._simulate_displacement'),
  },
  warnings: [],
  provenance: PROV('market_exposure.build_market_exposure'),
};

describe('MarketExposureTab — checklist QA S6', () => {
  beforeEach(() => {
    getMarketExposure.mockReset();
    mockSetSite.mockReset();
    setScope(null);
  });
  afterEach(() => cleanup());

  it('Critère 2 : scope=org (pas de site) → SiteRequiredState, aucun appel API', () => {
    setScope({
      selectedSiteId: null,
      scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: null },
    });
    render(<MarketExposureTab />);
    expect(screen.getByTestId('site-required-state')).toBeTruthy();
    expect(screen.getByText(/Sélectionnez un site/i)).toBeTruthy();
    expect(getMarketExposure).not.toHaveBeenCalled();
  });

  it('Critère 3 : appelle getMarketExposure avec scope=site + period=12m + market=day_ahead + zone=FR + baseload=true', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => expect(getMarketExposure).toHaveBeenCalledTimes(1));
    const args = getMarketExposure.mock.calls[0][0];
    expect(args.scope).toBe('site');
    expect(args.scope_id).toBe(42);
    expect(args.period).toBe(DEFAULT_PERIOD);
    expect(DEFAULT_PERIOD).toBe('12m');
    expect(args.market).toBe(DEFAULT_MARKET);
    expect(DEFAULT_MARKET).toBe('day_ahead');
    expect(args.zone).toBe(DEFAULT_ZONE);
    expect(DEFAULT_ZONE).toBe('FR');
    expect(args.baseload).toBe(true);
    expect(args.org_id).toBe(1);
  });

  it('Critère 4 : loading state visible avant la réponse', async () => {
    let resolveFn;
    const pending = new Promise((res) => {
      resolveFn = res;
    });
    getMarketExposure.mockReturnValueOnce(pending);
    render(<MarketExposureTab />);
    expect(screen.getByTestId('market-exposure-loading')).toBeTruthy();
    resolveFn(SAMPLE_PAYLOAD);
    await waitFor(() => screen.getByTestId('market-exposure-kpis-grid'));
  });

  it('Critère 5 : empty state si pas de KPI/scénarios/baseload/heures', async () => {
    getMarketExposure.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      kpis: {},
      top_expensive_hours: [],
      favorable_hours: [],
      baseload_comparison: null,
      simulation: null,
    });
    render(<MarketExposureTab />);
    await waitFor(() => expect(screen.queryByTestId('market-exposure-kpis-grid')).toBeNull());
    expect(screen.getByText(/Aucune exposition marché disponible/i)).toBeTruthy();
    expect(screen.getByText('Élargir la période')).toBeTruthy();
  });

  it('Critère 6 : error state code + hint + correlation_id', async () => {
    const err = new Error('Request failed');
    err.response = {
      status: 400,
      data: {
        detail: {
          code: 'ENERGY_MARKET_UNKNOWN',
          message: "market='lol' inconnu",
          hint: 'valeurs : day_ahead | intraday | future_baseload | future_peakload',
          correlation_id: 'corr-mkt-9876',
        },
      },
    };
    getMarketExposure.mockRejectedValueOnce(err);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('market-exposure-error'));
    expect(screen.getByTestId('error-code').textContent).toContain('ENERGY_MARKET_UNKNOWN');
    expect(screen.getByTestId('error-hint').textContent).toContain('day_ahead');
    expect(screen.getByTestId('error-correlation-id').textContent).toContain('corr-mkt-9876');
  });

  it('Critère 7 : 8 KPI rendus avec provenance', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('market-exposure-kpis-grid'));
    for (const key of KPI_ORDER) {
      expect(screen.getByTestId(`market-exposure-kpi-${key}`)).toBeTruthy();
    }
    // 8 tooltips de cartes KPI (KpiCardWithProvenance) + 1 tooltip
    // ExposureScoreGauge (qui ré-affiche exposure_score) + tooltips
    // BaseloadComparisonCard / TopExpensiveHoursTable autres.
    const tooltips = screen.getAllByTestId('kpi-provenance-tooltip');
    expect(tooltips.length).toBe(8);
  });

  it('Critère 7 bis : KPI_ORDER canonique (8 entrées)', () => {
    expect(KPI_ORDER).toEqual([
      'spot_cost_theoretical_eur',
      'spot_avg_simple_eur_mwh',
      'spot_avg_weighted_eur_mwh',
      'baseload_cost_eur',
      'delta_vs_baseload_eur',
      'top_10pct_expensive_hours_cost_pct',
      'negative_price_consumption_pct',
      'exposure_score',
    ]);
  });

  it('Critère 8 : ExposureScoreGauge rendue avec score+state backend', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('exposure-score-gauge'));
    const gauge = screen.getByTestId('exposure-score-gauge');
    expect(gauge.getAttribute('data-state')).toBe('vigilance');
    expect(gauge.getAttribute('data-score')).toBe('58');
  });

  it('Critère 9 : top heures chères visibles', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('top-expensive-hours-table'));
    expect(screen.getByTestId('top-hour-row-1')).toBeTruthy();
    expect(screen.getByTestId('top-hour-row-2')).toBeTruthy();
  });

  it('Critère 10 : prix négatif + heures favorables visibles', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('favorable-hours-panel'));
    expect(screen.getByTestId('favorable-group-prix-bas')).toBeTruthy();
    expect(screen.getByTestId('favorable-group-prix-négatif')).toBeTruthy();
    expect(screen.getByTestId('favorable-group-heure-solaire')).toBeTruthy();
  });

  it('Critère 11 : baseload comparison visible', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('baseload-comparison-card'));
    expect(screen.getByTestId('baseload-real-profile')).toBeTruthy();
    expect(screen.getByTestId('baseload-cost')).toBeTruthy();
    expect(screen.getByTestId('baseload-delta')).toBeTruthy();
  });

  it('Critère 12 : warning « Simulation indicative » visible si simulation fournie', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('simulation-warning'));
    const warning = screen.getByTestId('simulation-warning').textContent || '';
    expect(warning).toContain('Simulation indicative');
    expect(warning).toContain("ne constitue pas une promesse d'économie");
  });

  it('Partial : bandeau warnings affiché si backend renvoie warnings', async () => {
    getMarketExposure.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      warnings: ['12 heures sans prix spot', 'fallback day_ahead utilisé'],
    });
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('market-exposure-partial'));
    const banner = screen.getByTestId('market-exposure-partial').textContent || '';
    expect(banner).toContain('Analyse partielle');
    expect(banner).toContain('12 heures sans prix spot');
  });

  it('Header microcopy + market context affichés', async () => {
    getMarketExposure.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<MarketExposureTab />);
    await waitFor(() => screen.getByTestId('market-exposure-header'));
    const header = screen.getByTestId('market-exposure-header').textContent || '';
    expect(header).toContain('Marché & exposition');
    expect(header).toContain('Votre profil face aux prix spot');
    expect(header).toContain('Repérez les heures chères');
    expect(header).toContain('day_ahead');
    expect(header).toContain('FR');
    expect(header).toContain('MktPrice canonique');
  });
});

describe('MarketExposureTab — doctrine zéro calcul métier (critère 13)', () => {
  it('MarketExposureTab.jsx ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../pages/consumption/MarketExposureTab.jsx'),
      'utf8'
    );
    // Pas de calcul spot_cost = kwh * spot / 1000
    expect(src).not.toMatch(/spot_cost\s*=\s*\w+\.kwh\s*\*/);
    // Pas de calcul baseload FE
    expect(src).not.toMatch(/baseload_cost_eur\s*=\s*\w+\s*[*/]/);
    // Pas de calcul delta FE
    expect(src).not.toMatch(/delta_eur\s*=\s*\w+\s*-\s*\w+/);
    // Pas de calcul score expo FE
    expect(src).not.toMatch(/exposure_score\s*=\s*Math\./);
    // Pas de calcul top 10 % FE
    expect(src).not.toMatch(/quantile|percentile/i);
    // Pas de détection prix négatif FE
    expect(src).not.toMatch(/spot_price_eur_mwh\s*<\s*0/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
    // L'appel API et le rendu KPI fournis backend sont OK
    expect(src).toContain('getMarketExposure');
    expect(src).toContain('KpiCardWithProvenance');
  });

  it('ConsommationsPage déclare le tab marche', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/ConsommationsPage.jsx'), 'utf8');
    expect(src).toContain('/consommations/marche');
    expect(src).toContain("'Marché & exposition'");
  });

  it('App.jsx déclare la route nested marche avec lazy import', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../App.jsx'), 'utf8');
    expect(src).toMatch(
      /lazy\(\(\) =>\s*import\(['"]\.\/pages\/consumption\/MarketExposureTab['"]/
    );
    expect(src).toMatch(/path="marche"/);
  });

  it('Rail NavRegistry inchangé (pas de top-level Marché & exposition)', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../layout/NavRegistry.js'), 'utf8');
    expect(src).not.toMatch(/label:\s*['"]Marché & exposition['"]/);
    expect(src).not.toMatch(/path:\s*['"]marche['"]/);
    expect(src).not.toMatch(/to:\s*['"]\/?marche['"]/);
  });
});
