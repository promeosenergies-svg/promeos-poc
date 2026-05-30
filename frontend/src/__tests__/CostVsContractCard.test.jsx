// @vitest-environment jsdom
/**
 * PROMEOS — Tests CostVsContractCard (Sprint P1.S5).
 *
 * Vérifie :
 * - 4 scénarios affichés ;
 * - badge « Actuel » sur scenario.status='current', « Simulation » sinon ;
 * - badge « Recommandé » sur scenario dont la clé est recommended_scenario ;
 * - risk_level propagé via data-risk-level ;
 * - delta_vs_current_eur affiché tel que reçu (jamais recalculé FE) ;
 * - warning « Simulation indicative — ne constitue pas une promesse
 *   d'économie. » obligatoire et visible ;
 * - aucun calcul métier interdit.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import CostVsContractCard from '../ui/energy/CostVsContractCard';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'cdc_contract_simulator.simulate',
});

const SCENARIOS = [
  {
    key: 'fixed',
    label: 'Fixe 12 mois',
    estimated_cost_eur: 34500,
    weighted_price_eur_mwh: 172.5,
    risk_level: 'faible',
    status: 'simulation',
    delta_vs_current_eur: -1200,
    provenance: PROV('cdc_contract_simulator.fixed'),
    assumptions: ['prix forward 2026 EPEX', 'TURPE 7 voie A'],
  },
  {
    key: 'indexed',
    label: 'Indexé spot',
    estimated_cost_eur: 32800,
    weighted_price_eur_mwh: 164.0,
    risk_level: 'élevé',
    status: 'simulation',
    delta_vs_current_eur: -2900,
    provenance: PROV('cdc_contract_simulator.indexed'),
    assumptions: ['hypothèse spot moyen 2025'],
  },
  {
    key: 'mixed',
    label: 'Mixte 50/50',
    estimated_cost_eur: 33700,
    weighted_price_eur_mwh: 168.5,
    risk_level: 'modéré',
    status: 'current',
    delta_vs_current_eur: 0,
    provenance: PROV('cdc_contract_simulator.mixed'),
    assumptions: [],
  },
  {
    key: 'ths',
    label: 'THS (Tarif Heures Spéciales)',
    estimated_cost_eur: 35900,
    weighted_price_eur_mwh: 179.5,
    risk_level: 'modéré',
    status: 'simulation',
    delta_vs_current_eur: 2200,
    provenance: PROV('cdc_contract_simulator.ths'),
    assumptions: ['plage HC standard'],
  },
];

const RECOMMENDATION = {
  recommended_scenario: 'indexed',
  message: 'Le scénario indexé offre le coût estimé le plus bas.',
  confidence: 0.72,
  warning: "Simulation indicative — ne constitue pas une promesse d'économie.",
  provenance: PROV('cdc_contract_simulator.recommend'),
};

afterEach(() => cleanup());

describe('CostVsContractCard — rendu scénarios', () => {
  it('affiche les 4 scénarios fournis', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    expect(screen.getByTestId('scenario-card-fixed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-indexed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-mixed')).toBeTruthy();
    expect(screen.getByTestId('scenario-card-ths')).toBeTruthy();
  });

  it('badge « Actuel » sur scenario.status=current', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    const mixed = screen.getByTestId('scenario-card-mixed');
    expect(mixed.getAttribute('data-status')).toBe('current');
    expect(mixed.querySelector('[data-testid="scenario-badge-current"]')).toBeTruthy();
  });

  it('badge « Simulation » sur scenario.status=simulation', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    const fixed = screen.getByTestId('scenario-card-fixed');
    expect(fixed.getAttribute('data-status')).toBe('simulation');
    expect(fixed.querySelector('[data-testid="scenario-badge-simulation"]')).toBeTruthy();
  });

  it('badge « Recommandé » sur le scénario indexé (recommended_scenario)', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    const indexed = screen.getByTestId('scenario-card-indexed');
    expect(indexed.querySelector('[data-testid="scenario-badge-recommended"]')).toBeTruthy();
    // Le scénario fixed n'est pas recommandé
    const fixed = screen.getByTestId('scenario-card-fixed');
    expect(fixed.querySelector('[data-testid="scenario-badge-recommended"]')).toBeFalsy();
  });

  it('propage risk_level via data-risk-level', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    expect(screen.getByTestId('scenario-card-fixed').getAttribute('data-risk-level')).toBe(
      'faible'
    );
    expect(screen.getByTestId('scenario-card-indexed').getAttribute('data-risk-level')).toBe(
      'élevé'
    );
    expect(screen.getByTestId('scenario-card-mixed').getAttribute('data-risk-level')).toBe(
      'modéré'
    );
  });

  it('affiche delta_vs_current_eur tel que reçu (signe négatif = économie)', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    const indexed = screen.getByTestId('scenario-card-indexed');
    // -2900 € → "-2 900" présent
    expect(indexed.textContent).toMatch(/-2\s?900/);
    const ths = screen.getByTestId('scenario-card-ths');
    // +2200 € → "+2 200" (signe positif explicite)
    expect(ths.textContent).toMatch(/\+2\s?200/);
  });

  it('warning « Simulation indicative » OBLIGATOIRE et visible', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} recommendation={RECOMMENDATION} />);
    const warning = screen.getByTestId('simulation-warning');
    expect(warning).toBeTruthy();
    expect(warning.textContent).toContain('Simulation indicative');
    expect(warning.textContent).toContain("ne constitue pas une promesse d'économie");
  });

  it('warning par défaut affiché même si recommendation absente', () => {
    render(<CostVsContractCard scenarios={SCENARIOS} />);
    const warning = screen.getByTestId('simulation-warning');
    expect(warning.textContent).toContain('Simulation indicative');
  });

  it('contrat actif affiché si fourni', () => {
    render(
      <CostVsContractCard
        scenarios={SCENARIOS}
        activeContract={{
          contract_id: 'CTR-001',
          supplier_name: 'TotalEnergies',
          contract_type: 'mixed',
          end_date: '2027-12-31',
          provenance: PROV('contract_summary'),
        }}
      />
    );
    const summary = screen.getByTestId('active-contract-summary');
    expect(summary.textContent).toContain('TotalEnergies');
    expect(summary.textContent).toContain('mixed');
    expect(summary.textContent).toContain('2027-12-31');
  });

  it('retourne null si aucun scénario fourni', () => {
    const { container } = render(<CostVsContractCard scenarios={[]} />);
    expect(container.textContent).toBe('');
  });
});

describe('CostVsContractCard — doctrine zéro calcul métier', () => {
  it('le composant ne contient aucun calcul de delta / coût / risque', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/CostVsContractCard.jsx'), 'utf8');
    // Pas de calcul delta = current_cost - scenario_cost
    expect(src).not.toMatch(/delta\s*=\s*\w+\.estimated_cost_eur\s*-/);
    expect(src).not.toMatch(/delta_vs_current_eur\s*=\s*\w+\s*-\s*\w+/);
    // Pas de calcul scénario gagnant FE
    expect(src).not.toMatch(/winning\s*=\s*scenarios\./);
    expect(src).not.toMatch(/Math\.min\s*\(\s*\.{3}\s*scenarios/);
    // Pas de calcul risk_level FE
    expect(src).not.toMatch(/risk_level\s*=\s*\(\s*\w+\s*[<>]/);
    // Pas de calcul CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
    // Le warning par défaut est bien la phrase obligatoire
    expect(src).toContain("Simulation indicative — ne constitue pas une promesse d'économie.");
  });
});
