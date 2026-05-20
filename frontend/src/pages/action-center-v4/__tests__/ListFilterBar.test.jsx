// @vitest-environment jsdom
/**
 * M2-5.10.A — Tests du composant ListFilterBar (maquette §8.3 lignes 740-783).
 *
 * Row 1 : 8 chips de Classement (Tous + 7 kinds, MV3 client-side).
 * Row 2 : dropdown lifecycle. Reset visible si filtre actif.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { ListFilterBar } from '../components/ListFilterBar';

afterEach(cleanup);

const noop = () => {};

function setup(overrides = {}) {
  const props = {
    stateFilter: null,
    onStateFilterChange: noop,
    kindFilter: null,
    onKindFilterChange: noop,
    onReset: noop,
    ...overrides,
  };
  return render(<ListFilterBar {...props} />);
}

describe('ListFilterBar', () => {
  test('renders both row labels (Classement + Priorisation)', () => {
    setup();
    expect(screen.getByText('Classement')).toBeInTheDocument();
    expect(screen.getByText('Priorisation')).toBeInTheDocument();
  });

  test('renders 8 kind chips (Tous + 7 kinds)', () => {
    setup();
    expect(screen.getByRole('button', { name: /filtrer par tous les types/i })).toBeInTheDocument();
    [
      'Anomalie',
      'Action',
      'Décision',
      'Signal',
      'Demande de preuve',
      'Échéance',
      'Recommandation',
    ].forEach((label) => {
      expect(
        screen.getByRole('button', { name: new RegExp(`filtrer par ${label}`, 'i') })
      ).toBeInTheDocument();
    });
  });

  test('"Tous les types" is active when kindFilter is null', () => {
    setup();
    expect(screen.getByRole('button', { name: /filtrer par tous les types/i })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });

  test('clicking a kind chip calls onKindFilterChange with the kind value', () => {
    const onKindFilterChange = vi.fn();
    setup({ onKindFilterChange });
    fireEvent.click(screen.getByRole('button', { name: /filtrer par anomalie/i }));
    expect(onKindFilterChange).toHaveBeenCalledWith('anomaly');
  });

  test('clicking "Tous les types" calls onKindFilterChange with null', () => {
    const onKindFilterChange = vi.fn();
    setup({ kindFilter: 'anomaly', onKindFilterChange });
    fireEvent.click(screen.getByRole('button', { name: /filtrer par tous les types/i }));
    expect(onKindFilterChange).toHaveBeenCalledWith(null);
  });

  test('the lifecycle dropdown calls onStateFilterChange with the chosen state', () => {
    const onStateFilterChange = vi.fn();
    setup({ onStateFilterChange });
    fireEvent.change(screen.getByLabelText(/état/i), { target: { value: 'triaged' } });
    expect(onStateFilterChange).toHaveBeenCalledWith('triaged');
  });

  test('the lifecycle dropdown calls onStateFilterChange with null when set to "Tous"', () => {
    const onStateFilterChange = vi.fn();
    setup({ stateFilter: 'triaged', onStateFilterChange });
    fireEvent.change(screen.getByLabelText(/état/i), { target: { value: '' } });
    expect(onStateFilterChange).toHaveBeenCalledWith(null);
  });

  test('the Réinitialiser button only appears when at least one filter is active', () => {
    const { rerender } = setup();
    expect(
      screen.queryByRole('button', { name: /réinitialiser les filtres/i })
    ).not.toBeInTheDocument();

    rerender(
      <ListFilterBar
        stateFilter="triaged"
        onStateFilterChange={noop}
        kindFilter={null}
        onKindFilterChange={noop}
        onReset={noop}
      />
    );
    expect(screen.getByRole('button', { name: /réinitialiser les filtres/i })).toBeInTheDocument();
  });

  test('clicking Réinitialiser calls onReset', () => {
    const onReset = vi.fn();
    setup({ stateFilter: 'triaged', onReset });
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser les filtres/i }));
    expect(onReset).toHaveBeenCalled();
  });

  test('the filter scope note appears only when a filter is active', () => {
    const { rerender } = setup();
    expect(screen.queryByText(/page courante/i)).not.toBeInTheDocument();

    rerender(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={noop}
        kindFilter="anomaly"
        onKindFilterChange={noop}
        onReset={noop}
      />
    );
    expect(screen.getByText(/page courante/i)).toBeInTheDocument();
  });
});
