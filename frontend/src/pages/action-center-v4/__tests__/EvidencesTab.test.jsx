// @vitest-environment jsdom
/**
 * M2-5.3.B / M2-5.5 — Tests du composant EvidencesTab (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Evidences: vi.fn(),
  useUploadEvidence: vi.fn(),
  useVerifyEvidence: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import {
  useActionCenterV4Evidences,
  useUploadEvidence,
  useVerifyEvidence,
} from '../../../hooks/v4';
import { EvidencesTab } from '../components/EvidencesTab';

const idleMutation = {
  execute: vi.fn(),
  loading: false,
  error: null,
  data: null,
  reset: vi.fn(),
};

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useUploadEvidence.mockReturnValue(idleMutation);
  useVerifyEvidence.mockReturnValue(idleMutation);
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

  test('shows the "Ajouter une preuve" button', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" />);
    expect(screen.getByRole('button', { name: /ajouter une preuve/i })).toBeInTheDocument();
  });

  test('clicking "Ajouter une preuve" opens the upload modal', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" />);
    fireEvent.click(screen.getByRole('button', { name: /ajouter une preuve/i }));
    expect(screen.getByRole('button', { name: /ajouter la preuve/i })).toBeInTheDocument();
  });

  test('hides "Ajouter une preuve" when the item is closed (M2-5.9.bis)', () => {
    useActionCenterV4Evidences.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<EvidencesTab itemId="x" itemClosed />);
    expect(screen.queryByRole('button', { name: /ajouter une preuve/i })).not.toBeInTheDocument();
  });
});
