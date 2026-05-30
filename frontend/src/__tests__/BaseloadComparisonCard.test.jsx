// @vitest-environment jsdom
/**
 * PROMEOS — Tests BaseloadComparisonCard (Sprint P1.S6).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import BaseloadComparisonCard from '../ui/energy/BaseloadComparisonCard';

const PROV = {
  source: 'PROMEOS energy_orchestration',
  service: 'market_exposure._compute_baseload_comparison',
};

afterEach(() => cleanup());

describe('BaseloadComparisonCard', () => {
  it('rend les 3 cellules : profil réel, baseload, écart', () => {
    render(
      <BaseloadComparisonCard
        baseloadComparison={{
          real_profile_cost_eur: 34000,
          baseload_cost_eur: 31200,
          delta_eur: 2800,
          delta_eur_mwh: 14.5,
          formula: 'coût spot pondéré réel - consommation plate équivalente',
          provenance: PROV,
        }}
      />
    );
    expect(screen.getByTestId('baseload-real-profile')).toBeTruthy();
    expect(screen.getByTestId('baseload-cost')).toBeTruthy();
    expect(screen.getByTestId('baseload-delta')).toBeTruthy();
  });

  it('delta positif rendu en rouge (profil plus coûteux)', () => {
    render(
      <BaseloadComparisonCard
        baseloadComparison={{
          real_profile_cost_eur: 34000,
          baseload_cost_eur: 31200,
          delta_eur: 2800,
          delta_eur_mwh: 14.5,
          formula: '...',
          provenance: PROV,
        }}
      />
    );
    const delta = screen.getByTestId('baseload-delta-eur');
    expect(delta.getAttribute('data-sign')).toBe('positive');
    expect(delta.textContent).toMatch(/\+2\s?800/);
  });

  it('delta négatif rendu en vert (profil moins coûteux)', () => {
    render(
      <BaseloadComparisonCard
        baseloadComparison={{
          real_profile_cost_eur: 28000,
          baseload_cost_eur: 31200,
          delta_eur: -3200,
          delta_eur_mwh: -16.5,
          formula: '...',
          provenance: PROV,
        }}
      />
    );
    const delta = screen.getByTestId('baseload-delta-eur');
    expect(delta.getAttribute('data-sign')).toBe('negative');
    expect(delta.textContent).toMatch(/-3\s?200/);
  });

  it('formule backend affichée', () => {
    render(
      <BaseloadComparisonCard
        baseloadComparison={{
          real_profile_cost_eur: 100,
          baseload_cost_eur: 90,
          delta_eur: 10,
          delta_eur_mwh: 1,
          formula: 'coût spot pondéré profil réel vs ruban baseload équivalent',
          provenance: PROV,
        }}
      />
    );
    expect(screen.getByTestId('baseload-formula').textContent).toContain(
      'coût spot pondéré profil réel'
    );
  });

  it('retourne null si baseloadComparison absent', () => {
    const { container } = render(<BaseloadComparisonCard baseloadComparison={null} />);
    expect(container.textContent).toBe('');
  });
});

describe('BaseloadComparisonCard — doctrine zéro calcul métier', () => {
  it('ne contient aucun calcul de delta ni de baseload FE', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/BaseloadComparisonCard.jsx'), 'utf8');
    // Pas de calcul delta = real - baseload
    expect(src).not.toMatch(/delta_eur\s*=\s*\w+\.real_profile_cost_eur\s*-/);
    // Pas de calcul ruban baseload (total_kwh / nb_hours * spot_avg)
    expect(src).not.toMatch(/baseload_cost_eur\s*=\s*\w+\s*[*/]/);
  });
});
