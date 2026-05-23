// @vitest-environment jsdom
/**
 * M2-5.6 — Tests de la modal de résolution de blocage (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useResolveBlocker: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useResolveBlocker } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { BlockerResolveModal } from '../components/modals/BlockerResolveModal';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useResolveBlocker.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('BlockerResolveModal', () => {
  test('renders an optional resolution note field', () => {
    render(<BlockerResolveModal open onClose={vi.fn()} blockerId="b1" />);
    expect(screen.getByLabelText(/note de résolution/i)).toBeInTheDocument();
    expect(screen.getByText(/facultatif/i)).toBeInTheDocument();
  });

  test('submit without a note sends an empty payload', async () => {
    const execute = vi.fn().mockResolvedValue({});
    useResolveBlocker.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });

    render(<BlockerResolveModal open onClose={vi.fn()} blockerId="b1" />);
    fireEvent.click(screen.getByRole('button', { name: /^résoudre$/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('b1', {});
    });
  });

  test('submit with a note sends a trimmed resolution_comment', async () => {
    const execute = vi.fn().mockResolvedValue({});
    useResolveBlocker.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });

    render(<BlockerResolveModal open onClose={vi.fn()} blockerId="b1" />);
    fireEvent.change(screen.getByLabelText(/note de résolution/i), {
      target: { value: '  facture reçue  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^résoudre$/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('b1', {
        resolution_comment: 'facture reçue',
      });
    });
  });

  test('on success: toasts, calls onSuccess and closes', async () => {
    const toast = vi.fn();
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    useToast.mockReturnValue({ toast });

    render(<BlockerResolveModal open onClose={onClose} blockerId="b1" onSuccess={onSuccess} />);
    fireEvent.click(screen.getByRole('button', { name: /^résoudre$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/résolu/i), 'success');
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('an already-resolved error toasts and closes the modal', async () => {
    const err = new Error('Already');
    err.promeos = {
      code: 'BLOCKER_ALREADY_RESOLVED',
      message: 'Déjà résolu',
      status: 409,
    };
    const toast = vi.fn();
    const onClose = vi.fn();
    useResolveBlocker.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<BlockerResolveModal open onClose={onClose} blockerId="b1" />);
    fireEvent.click(screen.getByRole('button', { name: /^résoudre$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('the loading state changes the submit label', () => {
    useResolveBlocker.mockReturnValue({
      execute: vi.fn(),
      loading: true,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<BlockerResolveModal open onClose={vi.fn()} blockerId="b1" />);
    expect(screen.getByRole('button', { name: /résolution/i })).toBeInTheDocument();
  });
});
