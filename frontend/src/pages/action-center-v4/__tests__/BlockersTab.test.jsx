// @vitest-environment jsdom
/**
 * M2-5.3.B / M2-5.6 — Tests du composant BlockersTab (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Blockers: vi.fn(),
  useAddBlocker: vi.fn(),
  useResolveBlocker: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import { useActionCenterV4Blockers, useAddBlocker, useResolveBlocker } from '../../../hooks/v4';
import { BlockersTab } from '../components/drawer/BlockersTab';

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
  useAddBlocker.mockReturnValue(idleMutation);
  useResolveBlocker.mockReturnValue(idleMutation);
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

  test('shows the "Ajouter un blocage" button', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    expect(screen.getByRole('button', { name: /ajouter un blocage/i })).toBeInTheDocument();
  });

  test('clicking "Ajouter un blocage" opens the add modal', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    fireEvent.click(screen.getByRole('button', { name: /ajouter un blocage/i }));
    expect(screen.getByText(/signaler un blocage/i)).toBeInTheDocument();
  });

  // ── M2-5.10.B.bis — CTA inline dans l'empty state (audit CS P1-3) ──
  test('the empty state exposes an inline « Signaler le premier blocage » CTA', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" />);
    expect(
      screen.getByRole('button', { name: /signaler le premier blocage/i })
    ).toBeInTheDocument();
  });

  test('the inline empty CTA is hidden when the item is closed', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" itemClosed />);
    expect(
      screen.queryByRole('button', { name: /signaler le premier blocage/i })
    ).not.toBeInTheDocument();
  });

  test('hides "Ajouter un blocage" when the item is closed (M2-5.9.bis)', () => {
    useActionCenterV4Blockers.mockReturnValue({
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<BlockersTab itemId="x" itemClosed />);
    expect(screen.queryByRole('button', { name: /ajouter un blocage/i })).not.toBeInTheDocument();
  });
});
