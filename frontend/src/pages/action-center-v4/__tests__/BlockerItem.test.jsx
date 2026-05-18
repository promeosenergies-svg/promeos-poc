// @vitest-environment jsdom
/**
 * M2-5.3.B / M2-5.6 — Tests du composant BlockerItem (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

// La modal de résolution (montée au clic) consomme useToast.
vi.mock('../../../ui/ToastProvider', () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import { BlockerItem } from '../components/BlockerItem';

afterEach(cleanup);

describe('BlockerItem', () => {
  test('renders an "Actif" badge when resolved_at is null', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_evidence',
          justification: 'Attente facture Q3',
          added_at: '2026-05-01T00:00:00Z',
          resolved_at: null,
        }}
      />
    );
    expect(screen.getByText('Preuve attendue')).toBeInTheDocument();
    expect(screen.getByText('Actif')).toBeInTheDocument();
  });

  test('renders a "Résolu" badge and resolution date when resolved', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_data',
          justification: 'X',
          added_at: '2026-05-01T00:00:00Z',
          resolved_at: '2026-05-10T00:00:00Z',
        }}
      />
    );
    expect(screen.getByText('Résolu')).toBeInTheDocument();
    expect(screen.getByText(/Résolu le/)).toBeInTheDocument();
  });

  test('renders the justification when present', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_evidence',
          justification: 'Détail spécifique',
          added_at: '2026-05-01T00:00:00Z',
        }}
      />
    );
    expect(screen.getByText('Détail spécifique')).toBeInTheDocument();
  });

  test('falls back to the raw blocker_type for unknown values', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'unknown_xyz',
          added_at: '2026-05-01T00:00:00Z',
        }}
      />
    );
    expect(screen.getByText('unknown_xyz')).toBeInTheDocument();
  });

  test('shows the "Résoudre" button for an active blocker', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_evidence',
          added_at: '2026-05-01T00:00:00Z',
          resolved_at: null,
        }}
      />
    );
    expect(screen.getByRole('button', { name: /résoudre/i })).toBeInTheDocument();
  });

  test('does not show the "Résoudre" button for a resolved blocker', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_evidence',
          added_at: '2026-05-01T00:00:00Z',
          resolved_at: '2026-05-10T00:00:00Z',
        }}
      />
    );
    expect(screen.queryByRole('button', { name: /résoudre/i })).not.toBeInTheDocument();
  });

  test('clicking "Résoudre" opens the resolution modal', () => {
    render(
      <BlockerItem
        blocker={{
          id: '1',
          blocker_type: 'waiting_evidence',
          added_at: '2026-05-01T00:00:00Z',
          resolved_at: null,
        }}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /résoudre/i }));
    expect(screen.getByText(/résoudre ce blocage/i)).toBeInTheDocument();
  });
});
