// @vitest-environment jsdom
/**
 * M2-5.5 — Tests de la modal d'upload evidence (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useUploadEvidence: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useUploadEvidence } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { EvidenceUploadModal } from '../components/modals/EvidenceUploadModal';

const pdfFile = () => new File(['x'], 'doc.pdf', { type: 'application/pdf' });

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useUploadEvidence.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('EvidenceUploadModal', () => {
  test('renders the file input, description field and a disabled submit', () => {
    render(<EvidenceUploadModal open onClose={vi.fn()} itemId="x" />);
    expect(screen.getByLabelText(/fichier/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ajouter la preuve/i })).toBeDisabled();
  });

  test('rejects a DOCX with a client validation message', () => {
    render(<EvidenceUploadModal open onClose={vi.fn()} itemId="x" />);
    const file = new File(['x'], 'doc.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [file] },
    });
    expect(screen.getByText(/format non accepté/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ajouter la preuve/i })).toBeDisabled();
  });

  test('accepts a PDF and enables submit', () => {
    render(<EvidenceUploadModal open onClose={vi.fn()} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [pdfFile()] },
    });
    expect(screen.queryByText(/format non accepté/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ajouter la preuve/i })).toBeEnabled();
  });

  test('on success: calls execute, toasts, calls onSuccess and closes', async () => {
    const execute = vi.fn().mockResolvedValue({});
    const toast = vi.fn();
    const onSuccess = vi.fn();
    const onClose = vi.fn();
    useUploadEvidence.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<EvidenceUploadModal open onClose={onClose} itemId="x" onSuccess={onSuccess} />);
    const file = pdfFile();
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [file] },
    });
    fireEvent.click(screen.getByRole('button', { name: /ajouter la preuve/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('x', file, { description: undefined });
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/ajoutée/i), 'success');
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('trims the description and passes it to execute', async () => {
    const execute = vi.fn().mockResolvedValue({});
    useUploadEvidence.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });

    render(<EvidenceUploadModal open onClose={vi.fn()} itemId="x" />);
    const file = pdfFile();
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [file] },
    });
    fireEvent.change(screen.getByLabelText(/description/i), {
      target: { value: '  facture Engie  ' },
    });
    fireEvent.click(screen.getByRole('button', { name: /ajouter la preuve/i }));

    await waitFor(() => {
      expect(execute).toHaveBeenCalledWith('x', file, {
        description: 'facture Engie',
      });
    });
  });

  test('a corrigeable 415 (magic bytes) shows an inline error, modal stays open', async () => {
    const err = new Error('Invalid');
    err.promeos = {
      code: 'MAGIC_BYTES_MISMATCH',
      message: 'Signature de fichier invalide',
      status: 415,
    };
    useUploadEvidence.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    const onClose = vi.fn();

    render(<EvidenceUploadModal open onClose={onClose} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [pdfFile()] },
    });
    fireEvent.click(screen.getByRole('button', { name: /ajouter la preuve/i }));

    await waitFor(() => {
      expect(screen.getByText(/signature de fichier invalide/i)).toBeInTheDocument();
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  test('a 429 error shows a toast and closes the modal', async () => {
    const err = new Error('Rate limit');
    err.promeos = { status: 429 };
    const toast = vi.fn();
    const onClose = vi.fn();
    useUploadEvidence.mockReturnValue({
      execute: vi.fn().mockRejectedValue(err),
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<EvidenceUploadModal open onClose={onClose} itemId="x" />);
    fireEvent.change(screen.getByLabelText(/fichier/i), {
      target: { files: [pdfFile()] },
    });
    fireEvent.click(screen.getByRole('button', { name: /ajouter la preuve/i }));

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith(expect.stringMatching(/trop de requêtes/i), 'error');
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('the loading state changes the submit label', () => {
    useUploadEvidence.mockReturnValue({
      execute: vi.fn(),
      loading: true,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<EvidenceUploadModal open onClose={vi.fn()} itemId="x" />);
    expect(screen.getByText(/upload en cours/i)).toBeInTheDocument();
  });
});
