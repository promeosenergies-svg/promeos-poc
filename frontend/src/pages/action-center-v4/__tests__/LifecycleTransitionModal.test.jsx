// @vitest-environment jsdom
/**
 * M2-5.4 — Tests de la modal de transition lifecycle (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useTransitionLifecycle: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useTransitionLifecycle } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { LifecycleTransitionModal } from '../components/LifecycleTransitionModal';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useTransitionLifecycle.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('LifecycleTransitionModal', () => {
  test('shows the no-transitions message when the state is terminal (closed)', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="closed" />);
    expect(screen.getByText(/aucune transition possible/i)).toBeInTheDocument();
  });

  test('offers the 2 target states reachable from new', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    expect(screen.getByText('Trié')).toBeInTheDocument();
    expect(screen.getByText('Clôturé')).toBeInTheDocument();
  });

  test('hides the closure_reason field when the target is not closed', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    expect(screen.queryByLabelText(/raison de clôture/i)).not.toBeInTheDocument();
  });

  test('shows closure_reason and disables submit when the target is closed', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'closed' },
    });
    expect(screen.getByLabelText(/raison de clôture/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^transitionner$/i })).toBeDisabled();
  });

  test('enables submit once closed and a closure_reason are chosen', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'closed' },
    });
    fireEvent.change(screen.getByLabelText(/raison de clôture/i), {
      target: { value: 'resolved' },
    });
    expect(screen.getByRole('button', { name: /^transitionner$/i })).toBeEnabled();
  });

  test('on success: calls execute, toasts, calls onSuccess and closes', async () => {
    const execute = vi.fn().mockResolvedValue({});
    useTransitionLifecycle.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const toast = vi.fn();
    useToast.mockReturnValue({ toast });
    const onClose = vi.fn();
    const onSuccess = vi.fn();

    render(
      <LifecycleTransitionModal
        open
        onClose={onClose}
        onSuccess={onSuccess}
        itemId="x"
        currentState="new"
      />
    );
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^transitionner$/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('x', { new_state: 'triaged' });
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/effectuée/i), 'success');
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('a corrigeable 422 shows an inline error and keeps the modal open', async () => {
    const err = new Error('Validation');
    err.promeos = {
      code: 'CLOSURE_REASON_REQUIRED',
      message: 'closure_reason requis',
      hint: 'Choisir une raison',
      status: 422,
    };
    useTransitionLifecycle.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const onClose = vi.fn();

    render(<LifecycleTransitionModal open onClose={onClose} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'closed' },
    });
    fireEvent.change(screen.getByLabelText(/raison de clôture/i), {
      target: { value: 'resolved' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^transitionner$/i }));

    await waitFor(() => {
      expect(screen.getByText(/closure_reason requis/i)).toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  test('a forbidden transition shows a toast and closes the modal', async () => {
    const err = new Error('Forbidden');
    err.promeos = {
      code: 'LIFECYCLE_TRANSITION_FORBIDDEN',
      message: 'Transition non permise',
      status: 422,
    };
    useTransitionLifecycle.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const toast = vi.fn();
    useToast.mockReturnValue({ toast });
    const onClose = vi.fn();

    render(<LifecycleTransitionModal open onClose={onClose} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^transitionner$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/transition non permise/i), 'error');
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('a 429 error shows a retry toast', async () => {
    const err = new Error('Rate limit');
    err.promeos = { code: 'RATE_LIMIT_EXCEEDED', status: 429 };
    useTransitionLifecycle.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const toast = vi.fn();
    useToast.mockReturnValue({ toast });

    render(<LifecycleTransitionModal open onClose={vi.fn()} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^transitionner$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/trop de requêtes/i), 'error');
    });
  });

  test('the loading state disables submit and changes its label', () => {
    useTransitionLifecycle.mockReturnValue({
      execute: vi.fn(),
      loading: true,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    expect(screen.getByText(/transition en cours/i)).toBeInTheDocument();
  });

  // ── M2-6.C.1-reduit (Q30=C) — variant warning câblé si newState='closed' ──

  test('variant="default" par défaut (aucun newState sélectionné)', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    const dialog = screen.getByTestId('v4-modal');
    expect(dialog).toHaveAttribute('data-variant', 'default');
  });

  test('variant="warning" quand newState="closed" est sélectionné (Q30=C)', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'closed' },
    });
    const dialog = screen.getByTestId('v4-modal');
    expect(dialog).toHaveAttribute('data-variant', 'warning');
  });

  test('variant="default" si newState non-closed (triaged depuis "new")', () => {
    render(<LifecycleTransitionModal open onClose={() => {}} itemId="x" currentState="new" />);
    fireEvent.change(screen.getByLabelText(/nouvel état/i), {
      target: { value: 'triaged' },
    });
    const dialog = screen.getByTestId('v4-modal');
    expect(dialog).toHaveAttribute('data-variant', 'default');
  });
});
