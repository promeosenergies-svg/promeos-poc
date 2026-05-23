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
import { DrawerActions } from '../components/drawer/DrawerActions';

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
    expect(screen.getByRole('button', { name: /qualifier/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /assigner/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /plus d'actions/i })).toBeInTheDocument();
  });

  // M2-5.11.E — l'endpoint /assign est livré, le bouton est désormais actif.
  test('the Assigner button is enabled (M2-5.11.E — endpoint /assign livré)', () => {
    render(<DrawerActions item={item} />);
    expect(screen.getByRole('button', { name: /assigner/i })).toBeEnabled();
  });

  test('the Transitionner button is enabled for a non-terminal item', () => {
    render(<DrawerActions item={item} />);
    expect(screen.getByRole('button', { name: /qualifier/i })).toBeEnabled();
  });

  test('the primary button is disabled for a closed item (label = Rouvrir, M3+)', () => {
    render(<DrawerActions item={{ ...item, lifecycle_state: 'closed' }} />);
    // closed → label « Rouvrir » mais le bouton reste désactivé (réservé admins).
    expect(screen.getByRole('button', { name: /rouvrir/i })).toBeDisabled();
  });

  test('clicking the primary button opens the lifecycle transition modal', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /qualifier/i }));
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
    // M2-5.10.B.bis — chaque MenuItem porte role="menuitem" (audit
    // code-reviewer P1-1 — a11y WAI-ARIA 1.1).
    expect(screen.getByRole('menuitem', { name: /signaler un blocage/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /ajouter une preuve/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /clôturer/i })).toBeInTheDocument();
  });

  test('the Fusionner item is always disabled (no merger engine MV3)', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('menuitem', { name: /fusionner/i })).toBeDisabled();
  });

  test('clicking "Signaler un blocage" closes the menu and opens the blocker modal', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: /signaler un blocage/i }));
    // Menu fermé.
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    // Modal blocker ouverte (titre maquette « Signaler un blocage »).
    expect(screen.getAllByText(/signaler un blocage/i).length).toBeGreaterThan(0);
  });

  test('the menu items are disabled when the item is closed', () => {
    render(<DrawerActions item={{ ...item, lifecycle_state: 'closed' }} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('menuitem', { name: /signaler un blocage/i })).toBeDisabled();
    expect(screen.getByRole('menuitem', { name: /ajouter une preuve/i })).toBeDisabled();
    expect(screen.getByRole('menuitem', { name: /clôturer/i })).toBeDisabled();
  });

  // ── M2-5.10.B.bis — verbe dynamique selon lifecycle_state ──────────
  test('primary label is dynamic per lifecycle state (doctrine v0.3 §7.3)', () => {
    const { rerender } = render(<DrawerActions item={{ ...item, lifecycle_state: 'new' }} />);
    expect(screen.getByRole('button', { name: /qualifier/i })).toBeInTheDocument();

    rerender(<DrawerActions item={{ ...item, lifecycle_state: 'triaged' }} />);
    expect(screen.getByRole('button', { name: /planifier/i })).toBeInTheDocument();

    rerender(<DrawerActions item={{ ...item, lifecycle_state: 'planned' }} />);
    expect(screen.getByRole('button', { name: /démarrer/i })).toBeInTheDocument();

    rerender(<DrawerActions item={{ ...item, lifecycle_state: 'in_progress' }} />);
    expect(screen.getByRole('button', { name: /marquer comme fait/i })).toBeInTheDocument();
  });

  test('pressing Escape closes the more menu (a11y)', () => {
    render(<DrawerActions item={item} />);
    fireEvent.click(screen.getByRole('button', { name: /plus d'actions/i }));
    expect(screen.getByRole('menu')).toBeInTheDocument();
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });
});
