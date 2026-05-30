// @vitest-environment jsdom
/**
 * PROMEOS — Tests CostContractTab (Sprint P1.S5).
 *
 * Couvre la checklist QA S5 :
 * 1. onglet « Coût & contrat » visible dans /consommations (cf. test
 *    intégration ConsommationsPage : TABS contient `cout-contrat`) ;
 * 2. getCostVsContract appelé avec scope_id + period=12m + scenarios=fixed,
 *    indexed,mixed,ths ;
 * 3. loading state visible ;
 * 4. empty state visible (pas de KPI, pas de contrat, pas de scénarios) ;
 * 5. error state code + hint + correlation_id ;
 * 6. 6 KPI affichés avec provenance ;
 * 7. 4 scénarios affichés ;
 * 8. warning « Simulation indicative » visible ;
 * 9. décomposition prix affiche fourniture / TURPE / taxes ;
 * 10. aucun calcul métier interdit.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

vi.mock('../services/api/energy', () => ({
  getCostVsContract: vi.fn(),
}));

const mockSetSite = vi.fn();
let _mockScopeOverride = null;

vi.mock('../contexts/ScopeContext', () => ({
  useScope: () =>
    _mockScopeOverride
      ? { ...{ setSite: mockSetSite }, ..._mockScopeOverride }
      : {
          selectedSiteId: 42,
          scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: 42 },
          setSite: mockSetSite,
        },
}));

function setScope(next) {
  _mockScopeOverride = next;
}

import CostContractTab, {
  KPI_ORDER,
  DEFAULT_PERIOD,
  DEFAULT_SCENARIOS,
} from '../pages/consumption/CostContractTab';
import { getCostVsContract } from '../services/api/energy';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'cost_by_period_service + cdc_contract_simulator',
  period: '12 mois glissants',
  confidence: 0.82,
  assumptions: ['TURPE 7 voie A', 'TVA 20 %'],
});

const KPI = (key, label, value, unit, state = 'sain') => ({
  key,
  label,
  value,
  unit,
  state,
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '12m', days: 365, timezone: 'Europe/Paris' },
  provenance: PROV(`energy_orchestration.cost_vs_contract._kpi (${key})`),
});

const SCENARIO = (key, label, cost, price, risk, status, delta) => ({
  key,
  label,
  estimated_cost_eur: cost,
  weighted_price_eur_mwh: price,
  risk_level: risk,
  status,
  delta_vs_current_eur: delta,
  provenance: PROV(`cdc_contract_simulator.${key}`),
  assumptions: [],
});

const PRICE_COMP = (key, label, amount, eurMwh, share) => ({
  key,
  label,
  amount_eur: amount,
  price_eur_mwh: eurMwh,
  share_pct: share,
  provenance: PROV(`price_decomposition_service.${key}`),
});

const SAMPLE_PAYLOAD = {
  scope: { kind: 'site', scope_id: 42, org_id: 1 },
  period: { label: '12m', days: 365, timezone: 'Europe/Paris' },
  active_contract: {
    contract_id: 'CTR-X-001',
    supplier_name: 'TotalEnergies',
    contract_type: 'mixed',
    start_date: '2025-01-01',
    end_date: '2027-12-31',
    subscribed_power_kva: 250,
    provenance: PROV('contract_repository.get_active'),
  },
  kpis: {
    total_cost_eur: KPI('total_cost_eur', 'Coût total', 34000, '€'),
    consumption_kwh: KPI('consumption_kwh', 'Consommation', 198_000, 'kWh'),
    weighted_price_eur_mwh: KPI('weighted_price_eur_mwh', 'Prix moyen pondéré', 171.7, '€/MWh'),
    supply_cost_eur: KPI('supply_cost_eur', 'Fourniture', 18500, '€'),
    network_cost_eur: KPI('network_cost_eur', 'Acheminement TURPE', 9800, '€'),
    taxes_cost_eur: KPI('taxes_cost_eur', 'Taxes et contributions', 5700, '€'),
  },
  price_decomposition: [
    PRICE_COMP('supply', 'Fourniture', 18500, 92.5, 54.4),
    PRICE_COMP('network', 'Acheminement TURPE', 9800, 49.0, 28.8),
    PRICE_COMP('taxes', 'Taxes et contributions', 5700, 28.5, 16.8),
  ],
  scenarios: [
    SCENARIO('fixed', 'Fixe 12 mois', 34500, 172.5, 'faible', 'simulation', -1200),
    SCENARIO('indexed', 'Indexé spot', 32800, 164.0, 'élevé', 'simulation', -2900),
    SCENARIO('mixed', 'Mixte 50/50', 33700, 168.5, 'modéré', 'current', 0),
    SCENARIO('ths', 'THS', 35900, 179.5, 'modéré', 'simulation', 2200),
  ],
  recommendation: {
    recommended_scenario: 'indexed',
    message: 'Le scénario indexé offre le coût estimé le plus bas.',
    confidence: 0.72,
    warning: "Simulation indicative — ne constitue pas une promesse d'économie.",
    provenance: PROV('cdc_contract_simulator.recommend'),
  },
  assumptions: { fallback_price_used: false, notes: [] },
  warnings: [],
  provenance: PROV('energy_orchestration.cost_vs_contract.build'),
};

describe('CostContractTab — checklist QA S5', () => {
  beforeEach(() => {
    getCostVsContract.mockReset();
    mockSetSite.mockReset();
    setScope(null);
  });
  afterEach(() => cleanup());

  it('Critère 2 : appelle getCostVsContract avec scope_id + period=12m + scenarios canoniques', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => expect(getCostVsContract).toHaveBeenCalledTimes(1));
    const args = getCostVsContract.mock.calls[0][0];
    expect(args.scope).toBe('site');
    expect(args.scope_id).toBe(42);
    expect(args.period).toBe(DEFAULT_PERIOD);
    expect(DEFAULT_PERIOD).toBe('12m');
    expect(args.scenarios).toBe(DEFAULT_SCENARIOS);
    expect(DEFAULT_SCENARIOS).toBe('fixed,indexed,mixed,ths');
    expect(args.org_id).toBe(1);
  });

  it('Critère 3 : loading state visible avant la réponse', async () => {
    let resolveFn;
    const pending = new Promise((res) => {
      resolveFn = res;
    });
    getCostVsContract.mockReturnValueOnce(pending);
    render(<CostContractTab />);
    expect(screen.getByTestId('cost-contract-loading')).toBeTruthy();
    resolveFn(SAMPLE_PAYLOAD);
    await waitFor(() => screen.getByTestId('cost-contract-kpis-grid'));
  });

  it('Critère 4 : empty state visible quand pas de KPI ni scénario ni contrat', async () => {
    getCostVsContract.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      kpis: {},
      scenarios: [],
      price_decomposition: [],
      active_contract: null,
    });
    render(<CostContractTab />);
    await waitFor(() => expect(screen.queryByTestId('cost-contract-kpis-grid')).toBeNull());
    expect(screen.getByText(/Aucun contrat actif disponible/i)).toBeTruthy();
  });

  it('Critère 5 : error state code + hint + correlation_id', async () => {
    const err = new Error('Request failed');
    err.response = {
      status: 404,
      data: {
        detail: {
          code: 'ENERGY_CONTRACT_NOT_FOUND',
          message: 'Aucun contrat actif trouvé pour le site 42',
          hint: 'importer un contrat via /admin/contracts ou sélectionner un autre site',
          correlation_id: 'corr-cost-9876',
        },
      },
    };
    getCostVsContract.mockRejectedValueOnce(err);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('cost-contract-error'));
    expect(screen.getByTestId('error-code').textContent).toContain('ENERGY_CONTRACT_NOT_FOUND');
    expect(screen.getByTestId('error-hint').textContent).toContain('importer un contrat');
    expect(screen.getByTestId('error-correlation-id').textContent).toContain('corr-cost-9876');
  });

  it('Critère 6 : 6 KPI affichés avec provenance backend', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('cost-contract-kpis-grid'));
    for (const key of KPI_ORDER) {
      expect(screen.getByTestId(`cost-contract-kpi-${key}`)).toBeTruthy();
    }
    const tooltips = screen.getAllByTestId('kpi-provenance-tooltip');
    expect(tooltips.length).toBe(6);
    expect(tooltips[0].textContent).toContain('energy_orchestration.cost_vs_contract');
  });

  it("Critère 6 bis : KPI_ORDER canonique (6 entrées dans l'ordre)", () => {
    expect(KPI_ORDER).toEqual([
      'total_cost_eur',
      'consumption_kwh',
      'weighted_price_eur_mwh',
      'supply_cost_eur',
      'network_cost_eur',
      'taxes_cost_eur',
    ]);
  });

  it('Critère 7 : 4 scénarios affichés via CostVsContractCard', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('scenarios-grid'));
    expect(screen.getByTestId('scenario-card-fixed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-indexed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-mixed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-ths')).toBeTruthy();
  });

  it('Critère 8 : warning « Simulation indicative » visible', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('simulation-warning'));
    const warning = screen.getByTestId('simulation-warning').textContent || '';
    expect(warning).toContain('Simulation indicative');
    expect(warning).toContain("ne constitue pas une promesse d'économie");
  });

  it('Critère 9 : décomposition prix affiche fourniture, TURPE, taxes', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('price-decomposition-table'));
    expect(screen.getByTestId('price-component-supply')).toBeTruthy();
    expect(screen.getByTestId('price-component-network')).toBeTruthy();
    expect(screen.getByTestId('price-component-taxes')).toBeTruthy();
  });

  it('Critère partial : bandeau warnings affiché si backend renvoie warnings', async () => {
    getCostVsContract.mockResolvedValueOnce({
      ...SAMPLE_PAYLOAD,
      warnings: ['prix spot fallback utilisé', 'TURPE version mise à jour'],
    });
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('cost-contract-partial'));
    const banner = screen.getByTestId('cost-contract-partial').textContent || '';
    expect(banner).toContain('Simulation partielle');
    expect(banner).toContain('prix spot fallback');
  });

  it('Sprint P1.S6 — scope=org (pas de site) : SiteRequiredState rendu, aucun appel API', () => {
    setScope({
      selectedSiteId: null,
      scope: { orgId: 1, entiteId: null, portefeuilleId: null, siteId: null },
    });
    render(<CostContractTab />);
    expect(screen.getByTestId('site-required-state')).toBeTruthy();
    expect(screen.getByText(/Sélectionnez un site/i)).toBeTruthy();
    expect(getCostVsContract).not.toHaveBeenCalled();
  });

  it('Header microcopy FR conforme brief', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('cost-contract-header'));
    const header = screen.getByTestId('cost-contract-header').textContent || '';
    expect(header).toContain('Coût & contrat');
    expect(header).toContain('Votre coût réel selon le contrat actif');
    expect(header).toContain('Comparez le coût estimé');
  });

  it('Contrat actif affiché si fourni', async () => {
    getCostVsContract.mockResolvedValueOnce(SAMPLE_PAYLOAD);
    render(<CostContractTab />);
    await waitFor(() => screen.getByTestId('active-contract-summary'));
    const summary = screen.getByTestId('active-contract-summary').textContent || '';
    expect(summary).toContain('TotalEnergies');
  });
});

describe('CostContractTab — doctrine zéro calcul métier (critère 10)', () => {
  it('CostContractTab.jsx ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../pages/consumption/CostContractTab.jsx'),
      'utf8'
    );
    // Pas de calcul delta = current - simulation FE
    expect(src).not.toMatch(/delta\s*=\s*\w+\.estimated_cost_eur\s*-\s*\w+/);
    // Pas de calcul share_pct FE
    expect(src).not.toMatch(/share_pct\s*=\s*\w+\s*\/\s*\w+/);
    // Pas de calcul €/MWh FE
    expect(src).not.toMatch(/price_eur_mwh\s*=\s*\w+\s*\/\s*\w+/);
    // Pas de scénario gagnant choisi FE
    expect(src).not.toMatch(/Math\.min\s*\(\s*\.{3}\s*scenarios/);
    expect(src).not.toMatch(/winningScenario\s*=/);
    // Pas de calcul risk_level / TURPE / TVA FE
    expect(src).not.toMatch(/risk_level\s*=\s*\(\s*\w+\s*[<>]/);
    expect(src).not.toMatch(/turpe\s*=\s*\w+\s*\*/);
    expect(src).not.toMatch(/tva\s*=\s*\w+\s*\*/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor|co2Factor/);
    // L'appel API et le rendu KPI fournis backend sont OK
    expect(src).toContain('getCostVsContract');
    expect(src).toContain('KpiCardWithProvenance');
  });

  it('ConsommationsPage déclare le tab cout-contrat dans TABS', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../pages/ConsommationsPage.jsx'), 'utf8');
    expect(src).toContain('/consommations/cout-contrat');
    expect(src).toContain("'Coût & contrat'");
  });

  it('App.jsx déclare la route nested cout-contrat avec lazy import', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../App.jsx'), 'utf8');
    expect(src).toMatch(/lazy\(\(\) =>\s*import\(['"]\.\/pages\/consumption\/CostContractTab['"]/);
    expect(src).toMatch(/path="cout-contrat"/);
  });

  it('Rail NavRegistry inchangé (pas de top-level Coût & contrat)', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../layout/NavRegistry.js'), 'utf8');
    expect(src).not.toMatch(/['"]Coût & contrat['"]/);
    expect(src).not.toMatch(/['"]cout-contrat['"]/);
  });
});
