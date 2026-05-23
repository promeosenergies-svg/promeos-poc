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

import { ListFilterBar } from '../components/narrative/ListFilterBar';

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
    // M2-5.11.H — copy reformulée : « 20 items de cette page » + « d'autres
    // pages peuvent contenir des résultats » (audit CS clarté +0.15).
    expect(screen.queryByText(/20 items de cette page/i)).not.toBeInTheDocument();

    rerender(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={noop}
        kindFilter="anomaly"
        onKindFilterChange={noop}
        onReset={noop}
      />
    );
    expect(screen.getByText(/20 items de cette page/i)).toBeInTheDocument();
  });

  // ── M2-5.10.A.bis — chip-count par kind (audit UI Sol P1-1) ────────
  test('renders the per-kind count on each chip when kindCounts is provided', () => {
    setup({ kindCounts: { anomaly: 3, action: 5, decision: 1 } });
    // Le compteur est rendu adjacent au label dans le bouton chip.
    const anomalyBtn = screen.getByRole('button', { name: /filtrer par anomalie/i });
    expect(anomalyBtn.textContent).toMatch(/3/);
    const actionBtn = screen.getByRole('button', { name: /filtrer par action/i });
    expect(actionBtn.textContent).toMatch(/5/);
  });

  test('renders the total count on "Tous les types" chip', () => {
    setup({ kindCounts: { anomaly: 3, action: 5 } });
    const allBtn = screen.getByRole('button', { name: /filtrer par tous les types/i });
    expect(allBtn.textContent).toMatch(/8/);
  });

  test('hides the chip count when no kindCounts data is provided', () => {
    setup();
    const anomalyBtn = screen.getByRole('button', { name: /filtrer par anomalie/i });
    // Pas de chiffre dans le bouton sans `kindCounts`.
    expect(anomalyBtn.textContent).not.toMatch(/\d/);
  });

  // ── M2-5.10.A.bis — Réinitialiser promu chip 12px (audit CS P1-1) ──
  test('the Réinitialiser button is rendered as a chip with rotate-ccw icon (sub-WCAG fix)', () => {
    const { container } = setup({ stateFilter: 'triaged' });
    const btn = screen.getByRole('button', { name: /réinitialiser les filtres/i });
    // Au moins 12px de taille de police (audit CS — sub-WCAG 9.5px corrigé).
    expect(btn.className).toMatch(/text-\[12px\]/);
    // Icône lucide rotate-ccw rendue dans le bouton (svg enfant).
    expect(container.querySelector('button[aria-label*="éinitialiser"] svg')).toBeTruthy();
  });
});
