// @vitest-environment jsdom
/**
 * M2-5.6 — Tests de la modal d'ajout de blocage (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useAddBlocker: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useAddBlocker } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { BlockerAddModal } from '../components/BlockerAddModal';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useAddBlocker.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('BlockerAddModal', () => {
  test('renders the type Select with 7 options plus a placeholder', () => {
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    const select = screen.getByLabelText(/type de blocage/i);
    expect(select.querySelectorAll('option')).toHaveLength(8);
  });

  test('renders the canonical FR blocker-type labels', () => {
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    expect(screen.getByText('Preuve attendue')).toBeInTheDocument();
    expect(screen.getByText('Budget attendu')).toBeInTheDocument();
    expect(screen.getByText('Confirmation réglementaire attendue')).toBeInTheDocument();
  });

  test('keeps submit disabled until a type is selected', () => {
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    expect(screen.getByRole('button', { name: /^signaler$/i })).toBeDisabled();
  });

  test('keeps submit disabled while justification is shorter than 3 chars', () => {
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/type de blocage/i), {
      target: { value: 'waiting_evidence' },
    });
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: 'ab' },
    });
    expect(screen.getByRole('button', { name: /^signaler$/i })).toBeDisabled();
  });

  test('enables submit once a type and a 3+ char justification are set', () => {
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/type de blocage/i), {
      target: { value: 'waiting_evidence' },
    });
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: 'Attente facture Q4' },
    });
    expect(screen.getByRole('button', { name: /^signaler$/i })).toBeEnabled();
  });

  test('on success: calls execute with trimmed justification, toasts and closes', async () => {
    const execute = vi.fn().mockResolvedValue({});
    const toast = vi.fn();
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    useAddBlocker.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<BlockerAddModal open onClose={onClose} itemId="x" onSuccess={onSuccess} />);
    fireEvent.change(screen.getByLabelText(/type de blocage/i), {
      target: { value: 'waiting_budget' },
    });
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: '  En attente du Q4  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^signaler$/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('x', {
        blocker_type: 'waiting_budget',
        justification: 'En attente du Q4',
      });
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/signalé/i), 'success');
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('a 429 error shows a toast and closes the modal', async () => {
    const err = new Error('Rate');
    err.promeos = { status: 429 };
    const toast = vi.fn();
    const onClose = vi.fn();
    useAddBlocker.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<BlockerAddModal open onClose={onClose} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/type de blocage/i), {
      target: { value: 'waiting_evidence' },
    });
    fireEvent.change(screen.getByLabelText(/justification/i), {
      target: { value: 'Attente facture' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^signaler$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/trop de requêtes/i), 'error');
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('the loading state changes the submit label', () => {
    useAddBlocker.mockReturnValue({
      execute: vi.fn(),
      loading: true,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<BlockerAddModal open onClose={vi.fn()} itemId="x" />);
    expect(screen.getByText(/signalement/i)).toBeInTheDocument();
  });
});
