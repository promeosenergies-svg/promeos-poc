// @vitest-environment jsdom
/**
 * M2-5.3.B — Tests du composant EvidencesTab (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Evidences: vi.fn(),
}));

import { useActionCenterV4Evidences } from '../../../hooks/v4';
import { EvidencesTab } from '../components/EvidencesTab';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
});

describe('EvidencesTab', () => {
  test('renders a skeleton while loading', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<EvidencesTab itemId="x" />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the empty state when there is no evidence', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" />);
    expect(screen.getByText(/aucune preuve/i)).toBeInTheDocument();
  });

  test('renders the error state with a retry', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: null,
      loading: false,
      error: { message: 'fail' },
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" />);
    expect(screen.getByText(/impossible de charger les preuves/i)).toBeInTheDocument();
    expect(screen.getByText('Réessayer')).toBeInTheDocument();
  });

  test('renders the evidences list when data is loaded', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: {
        items: [
          {
            id: 'e1',
            original_filename: 'a.pdf',
            verified_at: null,
            uploaded_at: '2026-05-01T00:00:00Z',
          },
          {
            id: 'e2',
            original_filename: 'b.pdf',
            verified_at: null,
            uploaded_at: '2026-05-01T00:00:00Z',
          },
        ],
        total: 2,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" />);
    expect(screen.getByText('a.pdf')).toBeInTheDocument();
    expect(screen.getByText('b.pdf')).toBeInTheDocument();
  });

  test('calls the hook with the itemId and limit 20', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="item-xyz" />);
    expect(useActionCenterV4Evidences).toHaveBeenCalledWith('item-xyz', {
      offset: 0,
      limit: 20,
    });
  });
});
