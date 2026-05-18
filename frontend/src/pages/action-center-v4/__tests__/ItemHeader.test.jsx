// @vitest-environment jsdom
/**
 * M2-5.3.A / M2-5.4 — Tests du composant ItemHeader (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

// La modal de transition (montée au clic sur « Transitionner ») consomme
// useToast → ToastProvider mocké pour ne pas exiger le Provider en test.
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import { ItemHeader } from '../components/ItemHeader';

afterEach(cleanup);

describe('ItemHeader', () => {
  test('renders a skeleton while loading', () => {
    const { container } = render(<ItemHeader loading />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders an error message on error', () => {
    render(<ItemHeader error={{ message: 'fail' }} />);
    expect(screen.getByText(/impossible de charger/i)).toBeInTheDocument();
  });

  test('renders the title and the state badge', () => {
    render(
      <ItemHeader
        item={{
          title: 'Vérifier conso Q3',
          lifecycle_state: 'triaged',
          domain: 'energy',
        }}
      />
    );
    expect(screen.getByText('Vérifier conso Q3')).toBeInTheDocument();
    expect(screen.getByText('Trié')).toBeInTheDocument();
  });

  test('shows an em dash for each null metadata field', () => {
    render(
      <ItemHeader
        item={{
          title: 'X',
          lifecycle_state: 'new',
          domain: null,
          kind: null,
          created_at: null,
          updated_at: null,
        }}
      />
    );
    expect(screen.getAllByText('—').length).toBe(4);
  });

  test('shows the description when present, hides it when null', () => {
    const { rerender } = render(
      <ItemHeader item={{ title: 'X', lifecycle_state: 'new', description: 'desc1' }} />
    );
    expect(screen.getByText('desc1')).toBeInTheDocument();

    rerender(<ItemHeader item={{ title: 'X', lifecycle_state: 'new', description: null }} />);
    expect(screen.queryByText('desc1')).not.toBeInTheDocument();
  });

  test('shows the Transitionner button enabled for a non-terminal item', () => {
    render(<ItemHeader item={{ id: 'x', title: 'A', lifecycle_state: 'new' }} />);
    expect(screen.getByRole('button', { name: /transitionner/i })).toBeEnabled();
  });

  test('disables the Transitionner button for a closed item', () => {
    render(<ItemHeader item={{ id: 'x', title: 'A', lifecycle_state: 'closed' }} />);
    expect(screen.getByRole('button', { name: /transitionner/i })).toBeDisabled();
  });

  test('clicking Transitionner opens the transition modal', () => {
    render(<ItemHeader item={{ id: 'x', title: 'A', lifecycle_state: 'new' }} />);
    fireEvent.click(screen.getByRole('button', { name: /transitionner/i }));
    expect(screen.getByText(/transitionner l'action/i)).toBeInTheDocument();
  });
});
