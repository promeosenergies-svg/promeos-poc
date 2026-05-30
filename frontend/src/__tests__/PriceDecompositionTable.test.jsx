// @vitest-environment jsdom
/**
 * PROMEOS — Tests PriceDecompositionTable (Sprint P1.S5).
 *
 * Vérifie :
 * - rendu des composantes supply / network / taxes ;
 * - share_pct, amount_eur, price_eur_mwh affichés directement depuis API
 *   (jamais recalculés FE) ;
 * - ordre canonique (supply → network → taxes → capacity → other) ;
 * - aucun calcul métier interdit.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import PriceDecompositionTable from '../ui/energy/PriceDecompositionTable';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'price_decomposition_service.compute',
  period: '12m glissant',
});

const SAMPLE = [
  {
    key: 'supply',
    label: 'Fourniture',
    amount_eur: 18500,
    price_eur_mwh: 92.5,
    share_pct: 54.4,
    provenance: PROV('price_decomposition_service.supply'),
  },
  {
    key: 'network',
    label: 'Acheminement TURPE',
    amount_eur: 9800,
    price_eur_mwh: 49.0,
    share_pct: 28.8,
    provenance: PROV('price_decomposition_service.turpe'),
  },
  {
    key: 'taxes',
    label: 'Taxes et contributions',
    amount_eur: 5700,
    price_eur_mwh: 28.5,
    share_pct: 16.8,
    provenance: PROV('price_decomposition_service.taxes'),
  },
];

afterEach(() => cleanup());

describe('PriceDecompositionTable', () => {
  it('rend les 3 composantes du payload', () => {
    render(<PriceDecompositionTable priceDecomposition={SAMPLE} />);
    expect(screen.getByTestId('price-component-supply')).toBeTruthy();
    expect(screen.getByTestId('price-component-network')).toBeTruthy();
    expect(screen.getByTestId('price-component-taxes')).toBeTruthy();
  });

  it('affiche labels backend (Fourniture, Acheminement TURPE, Taxes)', () => {
    render(<PriceDecompositionTable priceDecomposition={SAMPLE} />);
    expect(screen.getByText('Fourniture')).toBeTruthy();
    expect(screen.getByText('Acheminement TURPE')).toBeTruthy();
    expect(screen.getByText('Taxes et contributions')).toBeTruthy();
  });

  it('affiche share_pct directement depuis API (jamais recalculé)', () => {
    render(<PriceDecompositionTable priceDecomposition={SAMPLE} />);
    const supplyRow = screen.getByTestId('price-component-supply');
    expect(supplyRow.textContent).toContain('54,4');
    const networkRow = screen.getByTestId('price-component-network');
    expect(networkRow.textContent).toContain('28,8');
  });

  it('affiche price_eur_mwh directement depuis API', () => {
    render(<PriceDecompositionTable priceDecomposition={SAMPLE} />);
    const supplyRow = screen.getByTestId('price-component-supply');
    expect(supplyRow.textContent).toMatch(/92,5.*€\/MWh/);
  });

  it('ordre canonique : supply avant network avant taxes', () => {
    // payload inversé → tri visuel canonique
    const reversed = [...SAMPLE].reverse();
    render(<PriceDecompositionTable priceDecomposition={reversed} />);
    const rows = document.querySelectorAll('[data-component-key]');
    expect(rows[0].getAttribute('data-component-key')).toBe('supply');
    expect(rows[1].getAttribute('data-component-key')).toBe('network');
    expect(rows[2].getAttribute('data-component-key')).toBe('taxes');
  });

  it('retourne null si pas de données', () => {
    const { container } = render(<PriceDecompositionTable priceDecomposition={[]} />);
    expect(container.textContent).toBe('');
  });

  it('provenance backend exposée par composante', () => {
    render(<PriceDecompositionTable priceDecomposition={SAMPLE} />);
    const tooltips = screen.getAllByTestId('price-component-provenance');
    expect(tooltips.length).toBe(3);
  });
});

describe('PriceDecompositionTable — doctrine zéro calcul métier', () => {
  it('le composant ne contient aucun calcul de share_pct / total / €/MWh', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(
      resolve(__dirname, '../ui/energy/PriceDecompositionTable.jsx'),
      'utf8'
    );
    // Pas de calcul share_pct = amount/total
    expect(src).not.toMatch(/share_pct\s*=\s*\w+\s*\/\s*\w+/);
    expect(src).not.toMatch(/sharePct\s*=\s*\w+\s*\/\s*\w+/);
    // Pas de calcul total = reduce sur amount_eur
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\w+\.amount_eur/);
    // Pas de calcul €/MWh = amount_eur / consumption
    expect(src).not.toMatch(/price_eur_mwh\s*=\s*\w+\s*\/\s*\w+/);
    // Pas de calcul CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
