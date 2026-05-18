// @vitest-environment jsdom
/**
 * M2-5.5 — Tests du confirm dialog de vérification (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useVerifyEvidence: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useVerifyEvidence } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { EvidenceVerifyDialog } from '../components/EvidenceVerifyDialog';

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useVerifyEvidence.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('EvidenceVerifyDialog', () => {
  test('renders the confirmation message mentioning 90 jours', () => {
    render(<EvidenceVerifyDialog open onClose={vi.fn()} evidenceId="e1" />);
    expect(screen.getByText(/90 jours/i)).toBeInTheDocument();
  });

  test('confirm calls execute with an empty payload', async () => {
    const execute = vi.fn().mockResolvedValue({});
    useVerifyEvidence.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });

    render(<EvidenceVerifyDialog open onClose={vi.fn()} evidenceId="e1" />);
    fireEvent.click(screen.getByRole('button', { name: /^vérifier$/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('e1', {});
    });
  });

  test('on success: toasts, calls onSuccess and closes', async () => {
    const toast = vi.fn();
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    useToast.mockReturnValue({ toast });

    render(<EvidenceVerifyDialog open onClose={onClose} evidenceId="e1" onSuccess={onSuccess} />);
    fireEvent.click(screen.getByRole('button', { name: /^vérifier$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/vérifiée/i), 'success');
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('cancel closes without calling execute', () => {
    const execute = vi.fn();
    useVerifyEvidence.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const onClose = vi.fn();

    render(<EvidenceVerifyDialog open onClose={onClose} evidenceId="e1" />);
    fireEvent.click(screen.getByRole('button', { name: /annuler/i }));

    expect(execute).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  test('an error always toasts and closes the dialog', async () => {
    const err = new Error('Already');
    err.promeos = {
      code: 'EVIDENCE_ALREADY_VERIFIED',
      message: 'Déjà vérifiée',
      status: 409,
    };
    const toast = vi.fn();
    const onClose = vi.fn();
    useVerifyEvidence.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<EvidenceVerifyDialog open onClose={onClose} evidenceId="e1" />);
    fireEvent.click(screen.getByRole('button', { name: /^vérifier$/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('the loading state changes the confirm label', () => {
    useVerifyEvidence.mockReturnValue({
      execute: vi.fn(),
      loading: true,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<EvidenceVerifyDialog open onClose={vi.fn()} evidenceId="e1" />);
    expect(screen.getByRole('button', { name: /vérification/i })).toBeInTheDocument();
  });
});
