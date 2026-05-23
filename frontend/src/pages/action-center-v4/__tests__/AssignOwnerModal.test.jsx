// @vitest-environment jsdom
/**
 * M2-5.11.E — Tests de la modal d'assignation pilote (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useAssignOwner: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: vi.fn(),
}));

import { useAssignOwner } from '../../../hooks/v4';
import { useToast } from '../../../ui/ToastProvider';
import { AssignOwnerModal } from '../components/modals/AssignOwnerModal';

const UNASSIGNED_ITEM = {
  id: 'item-1',
  title: 'Sans pilote',
  owner_id: null,
  owner_display_name: null,
};

const ASSIGNED_ITEM = {
  id: 'item-2',
  title: 'Déjà assigné',
  owner_id: '11111111-2222-3333-4444-555555555555',
  owner_display_name: 'J. Martin',
};

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useToast.mockReturnValue({ toast: vi.fn() });
  useAssignOwner.mockReturnValue({
    execute: vi.fn().mockResolvedValue({}),
    loading: false,
    error: null,
    data: null,
    reset: vi.fn(),
  });
});

describe('AssignOwnerModal', () => {
  test('renders the two fields (display name + UUID) with hints', () => {
    render(<AssignOwnerModal open onClose={vi.fn()} item={UNASSIGNED_ITEM} />);
    expect(screen.getByLabelText(/^pilote$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/identifiant pilote/i)).toBeInTheDocument();
    // Hints italiques (sol-font-display).
    expect(screen.getByText(/nom court/i)).toBeInTheDocument();
    expect(screen.getByText(/identifiant utilisateur/i)).toBeInTheDocument();
  });

  test('shows « Assigner » submit + no « Désassigner » when item is unassigned', () => {
    render(<AssignOwnerModal open onClose={vi.fn()} item={UNASSIGNED_ITEM} />);
    expect(screen.getByRole('button', { name: /^assigner$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^désassigner$/i })).toBeNull();
  });

  test('shows « Réassigner » submit + « Désassigner » when item is already assigned', () => {
    render(<AssignOwnerModal open onClose={vi.fn()} item={ASSIGNED_ITEM} />);
    expect(screen.getByRole('button', { name: /^réassigner$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^désassigner$/i })).toBeInTheDocument();
  });

  test('pre-fills fields with the current owner when item is already assigned', () => {
    render(<AssignOwnerModal open onClose={vi.fn()} item={ASSIGNED_ITEM} />);
    expect(screen.getByLabelText(/^pilote$/i)).toHaveValue('J. Martin');
    expect(screen.getByLabelText(/identifiant pilote/i)).toHaveValue(
      '11111111-2222-3333-4444-555555555555'
    );
  });

  test('client-side validation blocks submit when UUID is invalid', async () => {
    const execute = vi.fn();
    useAssignOwner.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<AssignOwnerModal open onClose={vi.fn()} item={UNASSIGNED_ITEM} />);
    fireEvent.change(screen.getByLabelText(/^pilote$/i), { target: { value: 'X. Test' } });
    fireEvent.change(screen.getByLabelText(/identifiant pilote/i), {
      target: { value: 'not-a-uuid' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^assigner$/i }));
    // SolInlineError affiche un message, execute n'est jamais appelé.
    expect(await screen.findByText(/identifiant invalide/i)).toBeInTheDocument();
    expect(execute).not.toHaveBeenCalled();
  });

  test('client-side validation blocks submit when display name is missing', async () => {
    const execute = vi.fn();
    useAssignOwner.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    render(<AssignOwnerModal open onClose={vi.fn()} item={UNASSIGNED_ITEM} />);
    fireEvent.change(screen.getByLabelText(/identifiant pilote/i), {
      target: { value: '11111111-2222-3333-4444-555555555555' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^assigner$/i }));
    expect(await screen.findByText(/nom du pilote est requis/i)).toBeInTheDocument();
    expect(execute).not.toHaveBeenCalled();
  });

  test('valid submit posts the payload + shows success toast + closes', async () => {
    const execute = vi.fn().mockResolvedValue({});
    const toast = vi.fn();
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    useAssignOwner.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(
      <AssignOwnerModal open onClose={onClose} item={UNASSIGNED_ITEM} onSuccess={onSuccess} />
    );
    fireEvent.change(screen.getByLabelText(/^pilote$/i), { target: { value: 'A. Nouveau' } });
    fireEvent.change(screen.getByLabelText(/identifiant pilote/i), {
      target: { value: '11111111-2222-3333-4444-555555555555' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^assigner$/i }));

    await waitFor(() => expect(execute).toHaveBeenCalled());
    expect(execute).toHaveBeenCalledWith('item-1', {
      owner_id: '11111111-2222-3333-4444-555555555555',
      owner_display_name: 'A. Nouveau',
    });
    expect(toast).toHaveBeenCalledWith('Pilote assigné', 'success');
    expect(onSuccess).toHaveBeenCalledTimes(1);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  test('« Désassigner » sends owner_id=null and shows the unassigned toast', async () => {
    const execute = vi.fn().mockResolvedValue({});
    const toast = vi.fn();
    useAssignOwner.mockReturnValue({
      execute,
      loading: false,
      error: null,
      data: null,
      reset: vi.fn(),
    });
    useToast.mockReturnValue({ toast });

    render(<AssignOwnerModal open onClose={vi.fn()} item={ASSIGNED_ITEM} />);
    fireEvent.click(screen.getByRole('button', { name: /^désassigner$/i }));

    await waitFor(() => expect(execute).toHaveBeenCalled());
    expect(execute).toHaveBeenCalledWith('item-2', { owner_id: null });
    expect(toast).toHaveBeenCalledWith('Pilote retiré', 'success');
  });
});
