// @vitest-environment jsdom
/**
 * M2-5.11.C — Tests du composant NarrativeBar (5 tuiles CFO).
 *
 * Couvre :
 * - États loading / error / data (visibles à l'utilisateur)
 * - Les 5 valeurs s'affichent dans l'ordre canonique
 * - Le bouton « Réessayer » appelle `refetch`
 * - L'a11y (`role="group"` + `aria-label`, role="alert" sur erreur)
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Summary: vi.fn(),
}));

import { useActionCenterV4Summary } from '../../../hooks/v4';
import { NarrativeBar } from '../components/NarrativeBar';

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe('NarrativeBar', () => {
  test('renders the loading skeleton (5 placeholders, aria-busy)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Skeleton : 5 div animées + un wrapper aria-busy.
    const wrapper = container.querySelector('[aria-busy="true"]');
    expect(wrapper).toBeTruthy();
    expect(container.querySelectorAll('.animate-pulse').length).toBe(5);
  });

  test('renders the error banner with retry button', () => {
    const refetch = vi.fn();
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      error: { code: 'INTERNAL', message: 'Server fault' },
      refetch,
    });
    render(<NarrativeBar />);
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/impossible de charger la synthèse/i);
    expect(alert).toHaveTextContent(/server fault/i);

    fireEvent.click(screen.getByText(/réessayer/i));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  test('renders all 5 tiles in canonical order when data is loaded', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 3,
        count_p1: 7,
        count_without_owner: 12,
        count_at_risk: 2,
        count_secured: 9,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // Le groupe est annoncé via role="group" + aria-label.
    const group = screen.getByRole('group', { name: /synthèse du centre d'action/i });
    expect(group).toBeInTheDocument();

    // Les 5 valeurs apparaissent dans l'ordre canonique du tableau ci-dessus.
    const values = screen.getAllByTestId('stat-tile-value').map((n) => n.textContent);
    expect(values).toEqual(['3', '7', '12', '2', '9']);

    // Les libellés FR sont rendus en MAJUSCULE par la CSS (uppercase) mais le
    // contenu DOM reste "P0 actifs" etc. — on vérifie le contenu DOM.
    expect(screen.getByText(/p0 actifs/i)).toBeInTheDocument();
    expect(screen.getByText(/p1 actifs/i)).toBeInTheDocument();
    expect(screen.getByText(/sans pilote/i)).toBeInTheDocument();
    expect(screen.getByText(/à risque/i)).toBeInTheDocument();
    expect(screen.getByText(/sécurisés/i)).toBeInTheDocument();
  });

  test('renders zero values without crashing (empty org)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    const values = screen.getAllByTestId('stat-tile-value').map((n) => n.textContent);
    expect(values).toEqual(['0', '0', '0', '0', '0']);
  });

  test('returns null silently when data is missing without loading or error', () => {
    // Cas défensif : si jamais le hook renvoie data=null sans loading/error.
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Aucun rendu — pas de tuile, pas de placeholder, pas d'alerte.
    expect(container.firstChild).toBeNull();
  });
});
