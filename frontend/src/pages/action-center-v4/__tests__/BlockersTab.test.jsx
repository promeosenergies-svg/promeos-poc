// @vitest-environment jsdom
/**
 * M2-5.3.B — Tests du composant BlockersTab (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Blockers: vi.fn(),
}));

import { useActionCenterV4Blockers } from '../../../hooks/v4';
import { BlockersTab } from '../components/BlockersTab';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe('BlockersTab', () => {
  test('renders a skeleton while loading', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<BlockersTab itemId="x" />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the empty state when there is no blocker', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    expect(screen.getByText(/aucun blocage/i)).toBeInTheDocument();
  });

  test('renders the error state with a retry', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: null,
      loading: false,
      error: { message: 'fail' },
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    expect(screen.getByText(/impossible de charger les blocages/i)).toBeInTheDocument();
    expect(screen.getByText('Réessayer')).toBeInTheDocument();
  });

  test('renders the blockers list when data is loaded', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: {
        items: [
          { id: 'b1', blocker_type: 'waiting_evidence', added_at: '2026-05-01T00:00:00Z' },
          { id: 'b2', blocker_type: 'waiting_budget', added_at: '2026-05-01T00:00:00Z' },
        ],
        total: 2,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    expect(screen.getByText('Preuve attendue')).toBeInTheDocument();
    expect(screen.getByText('Budget attendu')).toBeInTheDocument();
  });

  test('calls the hook with the itemId and limit 20', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="item-xyz" />);
    expect(useActionCenterV4Blockers).toHaveBeenCalledWith('item-xyz', {
      offset: 0,
      limit: 20,
    });
  });
});
