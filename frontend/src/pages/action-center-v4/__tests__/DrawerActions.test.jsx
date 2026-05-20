// @vitest-environment jsdom
/**
 * M2-5.10.B — Tests du composant DrawerActions (3 boutons header maquette
 * §8.4 lignes 689-732).
 *
 * Hooks v4 mockés : le composant rend les 3 boutons + Plus ▾ menu et ouvre
 * les modals (LifecycleTransitionModal / BlockerAddModal / EvidenceUploadModal).
 * Les modals elles-mêmes consomment useTransitionLifecycle / useAddBlocker /
 * useUploadEvidence — on les neutralise.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useTransitionLifecycle: vi.fn(),
  useAddBlocker: vi.fn(),
  useUploadEvidence: vi.fn(),
}));
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import { useAddBlocker, useTransitionLifecycle, useUploadEvidence } from '../../../hooks/v4';
import { DrawerActions } from '../components/DrawerActions';

const idle = { execute: vi.fn(), loading: false, error: null, data: null, reset: vi.fn() };

beforeEach(() => {
  vi.clearAllMocks();
  useTransitionLifecycle.mockReturnValue(idle);
  useAddBlocker.mockReturnValue(idle);
  useUploadEvidence.mockReturnValue(idle);
});

afterEach(cleanup);

const item = { id: 'x', lifecycle_state: 'new', title: 'A' };

describe('DrawerActions', () => {
  test('renders nothing when item is null', () => {
    const { container } = render(<DrawerActions item={null} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders the 3 cardinal buttons (Transitionner + Réassigner + Plus)', () => {
    render(<DrawerActions item={item} />);
    expect(screen.getByRole('button', { name: /transitionner/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /réassigner/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /plus d'actions/i })).toBeInTheDocument();
  });

  test('the Réassigner button is permanently disabled (M3+ owner endpoint)', () => {
    render(<DrawerActions item={item} />);
    expect(screen.getByRole('button', { name: /réassigner/i })).toBeDisabled();
  });

  test('the Transitionner button is enabled for a non-terminal item', () => {
    render(<DrawerActions item={item} />);
    expect(screen.getByRole('button', { name: /transitionner/i })).toBeEnabled();
  });

  test('the Transitionner button is disabled for a closed item', () => {
    render(<DrawerActions item={{ ...item, lifecycle_state: 'closed' }} />);
    expect(screen.getByRole('button', { name: /transitionner/i })).toBeDisabled();
  });

  test('clicking Transitionner opens the lifecycle transition modal', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /transitionner/i }));
    expect(screen.getByText(/transitionner l'action/i)).toBeInTheDocument();
  });

  test('clicking "Plus" opens the more menu', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('menu')).toBeInTheDocument();
  });

  test('the more menu exposes Bloquer / Ajouter preuve / Clôturer items', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('button', { name: /signaler un blocage/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ajouter une preuve/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clôturer/i })).toBeInTheDocument();
  });

  test('the Fusionner item is always disabled (no merger engine MV3)', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('button', { name: /fusionner/i })).toBeDisabled();
  });

  test('clicking "Signaler un blocage" closes the menu and opens the blocker modal', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    fireEvent.click(screen.getByRole('button', { name: /signaler un blocage/i }));
    // Menu fermé.
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    // Modal blocker ouverte (titre maquette « Signaler un blocage »).
    expect(screen.getAllByText(/signaler un blocage/i).length).toBeGreaterThan(0);
  });

  test('the menu items are disabled when the item is closed', () => {
    render(<DrawerActions item={{ ...item, lifecycle_state: 'closed' }} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('button', { name: /signaler un blocage/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /ajouter une preuve/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /clôturer/i })).toBeDisabled();
  });

  test('pressing Escape closes the more menu (a11y)', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
