// @vitest-environment jsdom
/**
 * M2-5.3.A/B — Tests d'intégration du ItemDetailDrawer (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
  useActionCenterV4Evidences: vi.fn(),
  useActionCenterV4Blockers: vi.fn(),
  useActionCenterV4Links: vi.fn(),
  // M2-5.10.C — ImpactSection est rendue dans le drawer entre ItemHeader et Tabs.
  useActionCenterV4Impact: vi.fn(),
}));

import {
  useActionCenterV4Item,
  useActionCenterV4Events,
  useActionCenterV4Evidences,
  useActionCenterV4Blockers,
  useActionCenterV4Links,
  useActionCenterV4Impact,
} from '../../../hooks/v4';
import { ItemDetailDrawer } from '../components/ItemDetailDrawer';

const emptyList = {
  data: { items: [], total: 0 },
  loading: false,
  error: null,
  refetch: vi.fn(),
};

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  useActionCenterV4Item.mockReturnValue({
    data: {
      id: 'x',
      title: 'Action X',
      lifecycle_state: 'triaged',
      domain: 'energy',
      kind: 'audit',
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
  });
  useActionCenterV4Events.mockReturnValue(emptyList);
  useActionCenterV4Evidences.mockReturnValue(emptyList);
  useActionCenterV4Blockers.mockReturnValue(emptyList);
  useActionCenterV4Links.mockReturnValue(emptyList);
  // ImpactSection loading par défaut → skeleton (n'interfère pas avec les
  // assertions sur tabs/titre/onglets).
  useActionCenterV4Impact.mockReturnValue({
    data: null,
    loading: true,
    error: null,
    refetch: vi.fn(),
  });
});

describe('ItemDetailDrawer', () => {
  test('renders nothing when closed', () => {
    const { container } = render(
      <ItemDetailDrawer itemId={null} open={false} onClose={() => {}} />
    );
    expect(container.querySelector('header')).toBeNull();
  });

  test('renders the header with the item title when open', () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    expect(screen.getByText('Action X')).toBeInTheDocument();
  });

  test('Preuves tab is active by default and fetches evidences (M2-5.10.B.bis ordre onglets)', () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    // M2-5.10.B.bis — l'onglet par défaut est désormais Preuves (action
    // prioritaire utilisateur), pas Historique (audit a posteriori).
    expect(useActionCenterV4Evidences).toHaveBeenCalledWith('x', {
      offset: 0,
      limit: 20,
    });
  });

  test('clicking the Preuves tab activates EvidencesTab (no more placeholder)', async () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Preuves'));
    expect(await screen.findByText(/aucune preuve/i)).toBeInTheDocument();
    expect(screen.queryByText(/disponible prochainement/i)).not.toBeInTheDocument();
  });

  test('clicking the Blocages tab activates BlockersTab', async () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Blocages'));
    expect(await screen.findByText(/aucun blocage/i)).toBeInTheDocument();
  });

  test('clicking the Liens tab activates LinksTab', async () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Liens'));
    expect(await screen.findByText(/aucun lien/i)).toBeInTheDocument();
  });

  test('switching tab does not trigger a Timeline refetch', () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    const initialCalls = useActionCenterV4Events.mock.calls.length;
    fireEvent.click(screen.getByText('Blocages'));
    expect(useActionCenterV4Events.mock.calls.length).toBe(initialCalls);
  });

  test('resets to the default tab (Preuves) after a close / reopen cycle (M2-5.10.B.bis)', () => {
    const { rerender } = render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Liens'));
    expect(screen.getByText(/aucun lien/i)).toBeInTheDocument();

    rerender(<ItemDetailDrawer itemId={null} open={false} onClose={() => {}} />);
    rerender(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);

    // M2-5.10.B.bis — l'onglet par défaut est Preuves (pas Historique).
    expect(screen.getByText(/aucune preuve/i)).toBeInTheDocument();
    expect(screen.queryByText(/aucun lien/i)).not.toBeInTheDocument();
  });
});
