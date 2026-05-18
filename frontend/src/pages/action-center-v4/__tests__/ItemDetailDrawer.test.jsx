// @vitest-environment jsdom
/**
 * M2-5.3.A — Tests d'intégration du ItemDetailDrawer (rendu jsdom, hooks mockés).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
}));

import { useActionCenterV4Item, useActionCenterV4Events } from '../../../hooks/v4';
import { ItemDetailDrawer } from '../components/ItemDetailDrawer';

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
  useActionCenterV4Events.mockReturnValue({
    data: { items: [], total: 0 },
    loading: false,
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

  test('Timeline tab is active by default and fetches events', () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    expect(useActionCenterV4Events).toHaveBeenCalledWith('x', {
      offset: 0,
      limit: 20,
    });
  });

  test('clicking the Preuves tab shows the placeholder in M2-5.3.A', async () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Preuves'));
    expect(await screen.findByText(/disponible prochainement/i)).toBeInTheDocument();
  });

  test('switching tab does not trigger a Timeline refetch', () => {
    render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    const initialCalls = useActionCenterV4Events.mock.calls.length;
    fireEvent.click(screen.getByText('Blocages'));
    expect(useActionCenterV4Events.mock.calls.length).toBe(initialCalls);
  });

  test('resets to the Timeline tab after a close / reopen cycle', () => {
    const { rerender } = render(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);
    fireEvent.click(screen.getByText('Liens'));
    expect(screen.getByText(/disponible prochainement/i)).toBeInTheDocument();

    rerender(<ItemDetailDrawer itemId={null} open={false} onClose={() => {}} />);
    rerender(<ItemDetailDrawer itemId="x" open onClose={() => {}} />);

    // Timeline réactif → son état vide s'affiche, plus le placeholder « Liens ».
    expect(screen.getByText(/aucun événement/i)).toBeInTheDocument();
    expect(screen.queryByText(/disponible prochainement/i)).not.toBeInTheDocument();
  });
});
