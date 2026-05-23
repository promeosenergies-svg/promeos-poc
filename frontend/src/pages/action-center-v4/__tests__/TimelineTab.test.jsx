// @vitest-environment jsdom
/**
 * M2-5.3.A — Tests du composant TimelineTab (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Events: vi.fn(),
}));

import { useActionCenterV4Events } from '../../../hooks/v4';
import { TimelineTab } from '../components/drawer/TimelineTab';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe('TimelineTab', () => {
  test('renders a skeleton while loading', () => {
    useActionCenterV4Events.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<TimelineTab itemId="x" />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the empty state when there is no event', () => {
    useActionCenterV4Events.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<TimelineTab itemId="x" />);
    expect(screen.getByText(/aucun événement/i)).toBeInTheDocument();
  });

  test('renders the error state with a retry', () => {
    useActionCenterV4Events.mockReturnValue({
      data: null,
      loading: false,
      error: { code: 'INTERNAL', message: 'fail' },
      refetch: vi.fn(),
    });
    render(<TimelineTab itemId="x" />);
    expect(screen.getByText(/impossible de charger/i)).toBeInTheDocument();
    expect(screen.getByText('Réessayer')).toBeInTheDocument();
  });

  test('renders the events list when data is loaded', () => {
    useActionCenterV4Events.mockReturnValue({
      data: {
        items: [
          {
            id: 'e1',
            event_type: 'state_changed',
            occurred_at: new Date().toISOString(),
            summary: 'a→b',
          },
          {
            id: 'e2',
            event_type: 'evidence_added',
            occurred_at: new Date().toISOString(),
          },
        ],
        total: 2,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<TimelineTab itemId="x" />);
    expect(screen.getByText("Transition d'état")).toBeInTheDocument();
    expect(screen.getByText('Preuve ajoutée')).toBeInTheDocument();
  });

  test('calls the hook with the itemId and limit 20', () => {
    useActionCenterV4Events.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<TimelineTab itemId="item-xyz" />);
    expect(useActionCenterV4Events).toHaveBeenCalledWith('item-xyz', {
      offset: 0,
      limit: 20,
    });
  });
});
