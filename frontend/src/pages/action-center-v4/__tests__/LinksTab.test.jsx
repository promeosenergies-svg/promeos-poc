// @vitest-environment jsdom
/**
 * M2-5.3.B — Tests du composant LinksTab (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Links: vi.fn(),
}));

import { useActionCenterV4Links } from '../../../hooks/v4';
import { LinksTab } from '../components/drawer/LinksTab';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe('LinksTab', () => {
  test('renders a skeleton while loading', () => {
    useActionCenterV4Links.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<LinksTab itemId="x" />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the empty state when there is no link', () => {
    useActionCenterV4Links.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<LinksTab itemId="x" />);
    expect(screen.getByText(/aucun lien/i)).toBeInTheDocument();
  });

  test('renders the error state with a retry', () => {
    useActionCenterV4Links.mockReturnValue({
      data: null,
      loading: false,
      error: { message: 'fail' },
      refetch: vi.fn(),
    });
    render(<LinksTab itemId="x" />);
    expect(screen.getByText(/impossible de charger les liens/i)).toBeInTheDocument();
    expect(screen.getByText('Réessayer')).toBeInTheDocument();
  });

  test('renders the links list when data is loaded', () => {
    useActionCenterV4Links.mockReturnValue({
      data: {
        items: [
          { id: 'l1', target_module: 'action_center_item', target_id: 't1' },
          { id: 'l2', target_module: 'site', target_id: 't2' },
        ],
        total: 2,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<LinksTab itemId="x" />);
    expect(screen.getByText('t1')).toBeInTheDocument();
    expect(screen.getByText('t2')).toBeInTheDocument();
  });

  test('calls the hook with the itemId and limit 20', () => {
    useActionCenterV4Links.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<LinksTab itemId="item-xyz" />);
    expect(useActionCenterV4Links).toHaveBeenCalledWith('item-xyz', {
      offset: 0,
      limit: 20,
    });
  });
});
