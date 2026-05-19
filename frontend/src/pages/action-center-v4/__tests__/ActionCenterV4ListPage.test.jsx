// @vitest-environment jsdom
/**
 * M2-5.2 — Tests d'intégration de la page liste (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Items: vi.fn(),
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
}));

import {
  useActionCenterV4Items,
  useActionCenterV4Item,
  useActionCenterV4Events,
} from '../../../hooks/v4';
import { ActionCenterV4ListPage } from '../ActionCenterV4ListPage';

function mockHook(value) {
  useActionCenterV4Items.mockReturnValue({
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  });
}

describe('ActionCenterV4ListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Le drawer est rendu en permanence (fermé tant que selectedItemId est
    // null) ; ItemDetailDrawer appelle useActionCenterV4Item dès le rendu.
    useActionCenterV4Item.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    useActionCenterV4Events.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  // Pas de `globals: true` dans vite.config → cleanup RTL explicite.
  afterEach(cleanup);

  test('renders a loading skeleton while loading', () => {
    mockHook({ loading: true });
    const { container } = render(<ActionCenterV4ListPage />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the page title and subtitle', () => {
    mockHook({ data: { items: [], total: 0, offset: 0, limit: 20 } });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText("Centre d'action")).toBeInTheDocument();
    expect(screen.getByText('Nouveau (V4) — Pilote')).toBeInTheDocument();
  });

  test('renders the empty state when there is no item', () => {
    mockHook({ data: { items: [], total: 0, offset: 0, limit: 20 } });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText(/aucune action à afficher/i)).toBeInTheDocument();
  });

  test('renders the items when data is loaded', () => {
    mockHook({
      data: {
        items: [
          {
            id: '1',
            title: 'Test action',
            lifecycle_state: 'new',
            domain: 'energy',
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText('Test action')).toBeInTheDocument();
  });

  test('renders the error state with a retry that calls refetch', () => {
    const refetch = vi.fn();
    mockHook({
      error: { code: 'INTERNAL', message: 'Server error', status: 500 },
      refetch,
    });
    render(<ActionCenterV4ListPage />);
    const retry = screen.getByText('Réessayer');
    expect(retry).toBeInTheDocument();
    fireEvent.click(retry);
    expect(refetch).toHaveBeenCalled();
  });

  test('filters items client-side by lifecycle state', () => {
    mockHook({
      data: {
        items: [
          { id: '1', title: 'Action A', lifecycle_state: 'new' },
          { id: '2', title: 'Action B', lifecycle_state: 'triaged' },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText('Action A')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'triaged' },
    });

    expect(screen.queryByText('Action A')).not.toBeInTheDocument();
    expect(screen.getByText('Action B')).toBeInTheDocument();
  });

  test('shows the page-scope note only once a filter is active', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.queryByText(/page courante/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'triaged' },
    });
    expect(screen.getByText(/page courante/i)).toBeInTheDocument();
  });

  test('a filter that empties the page shows a distinct message and keeps pagination', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 50,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'closed' },
    });

    expect(screen.getByText(/aucune action pour ce filtre/i)).toBeInTheDocument();
    // Pagination reste visible (total serveur 50) → pas de cul-de-sac navigation.
    expect(screen.getByLabelText('Page suivante')).toBeInTheDocument();
  });

  test('pagination "next" is disabled on a single page', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByLabelText('Page suivante')).toBeDisabled();
  });

  test('clicking a row opens the detail drawer', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: { id: '1', title: 'Action A', lifecycle_state: 'new' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByText('Action A').closest('tr'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  test('closing the drawer removes it from the DOM', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: { id: '1', title: 'Action A', lifecycle_state: 'new' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4ListPage />);
    fireEvent.click(screen.getByText('Action A').closest('tr'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Fermer'));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  // ── M2-5.9.bis — changement de filtre → retour page 1 ─────────────
  test('changing the lifecycle filter resets pagination to page 1', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 50,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);

    // Aller en page 2 → le hook est appelé avec offset 20.
    fireEvent.click(screen.getByLabelText('Page suivante'));
    expect(useActionCenterV4Items).toHaveBeenLastCalledWith({ offset: 20, limit: 20 });

    // Changer le filtre → la pagination repart en page 1 (offset 0).
    fireEvent.change(screen.getByLabelText(/état/i), { target: { value: 'closed' } });
    expect(useActionCenterV4Items).toHaveBeenLastCalledWith({ offset: 0, limit: 20 });
  });
});
