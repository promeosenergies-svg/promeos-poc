// @vitest-environment jsdom
/**
 * M2-5.10.C — Tests d'`ImpactSection` (drawer détail § 8.5).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Impact: vi.fn(),
}));

import { useActionCenterV4Impact } from '../../../hooks/v4';
import { ImpactSection } from '../components/drawer/ImpactSection';
import { setupHooksV4Mock } from './testUtils/v4Mocks';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

const emptyImpact = {
  item_id: 'x',
  period: '12m',
  estimated: { value_eur: null, detail: null, formula: null, source: null },
  at_risk: { value_eur: null, detail: null, formula: null, source: null },
  secured: { value_eur: null, detail: null, formula: null, source: null },
  realized: { value_eur: null, detail: null, formula: null, source: null },
  dominant_dimension: null,
  has_data: false,
};

const richImpact = {
  item_id: 'x',
  period: '12m',
  estimated: {
    value_eur: 49000,
    detail: 'gain si audit + plan pilotage',
    formula: '320 MWh × 153 €/MWh',
    source: 'Modèle V4 · scénario B',
  },
  at_risk: {
    value_eur: 7500,
    detail: 'pénalité OPERAT',
    formula: '15 €/m² × 500 m²',
    source: 'Décret 2014-1393',
  },
  secured: { value_eur: null, detail: 'à activer après démarrage', formula: null, source: null },
  realized: { value_eur: null, detail: 'à constater après clôture', formula: null, source: null },
  dominant_dimension: 'at_risk',
  has_data: true,
};

describe('ImpactSection', () => {
  // M2-6.C.3 (commit 1/4) pilote — `setupHooksV4Mock` pour les 2 premiers
  // tests skeleton/error. Validation pattern avant migration globale M3+.
  test('renders a skeleton while loading', () => {
    setupHooksV4Mock({ useActionCenterV4Impact }, { impact: null, impactState: { loading: true } });
    const { container } = render(<ImpactSection itemId="x" />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders an error banner on error', () => {
    setupHooksV4Mock(
      { useActionCenterV4Impact },
      { impact: null, impactState: { error: { message: 'fail' } } }
    );
    render(<ImpactSection itemId="x" />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/impossible de charger l'impact/i)).toBeInTheDocument();
  });

  test('renders the empty state when has_data is false', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: emptyImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ImpactSection itemId="x" />);
    expect(screen.getByText(/impact non encore calculé/i)).toBeInTheDocument();
    expect(screen.getByText(/BACKLOG_M3/)).toBeInTheDocument();
  });

  test('renders the 4 dimension labels when data is populated', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: richImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ImpactSection itemId="x" />);
    expect(screen.getByText('Estimé')).toBeInTheDocument();
    expect(screen.getByText('À risque')).toBeInTheDocument();
    expect(screen.getByText('Sécurisable')).toBeInTheDocument();
    expect(screen.getByText('Réalisé')).toBeInTheDocument();
  });

  test('formats values in k€ for large amounts (≥ 1000)', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: richImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ImpactSection itemId="x" />);
    expect(screen.getByText(/49.*k€/)).toBeInTheDocument();
    expect(screen.getByText(/7,5.*k€/)).toBeInTheDocument();
  });

  test('renders « — » for null value_eur (cardinal doctrine §8.5)', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: richImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ImpactSection itemId="x" />);
    // 2 dimensions sont à null (secured + realized) → 2 dashes.
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBe(2);
  });

  test('renders Source and Formule when present (CFO traceability)', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: richImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ImpactSection itemId="x" />);
    expect(screen.getByText('Modèle V4 · scénario B')).toBeInTheDocument();
    expect(screen.getByText('320 MWh × 153 €/MWh')).toBeInTheDocument();
    expect(screen.getByText('Décret 2014-1393')).toBeInTheDocument();
  });

  test('exposes the dimension labels with help tooltips (cursor-help)', () => {
    useActionCenterV4Impact.mockReturnValue({
      data: richImpact,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<ImpactSection itemId="x" />);
    const labels = container.querySelectorAll('.cursor-help');
    expect(labels.length).toBe(4); // 1 par dimension
  });
});
