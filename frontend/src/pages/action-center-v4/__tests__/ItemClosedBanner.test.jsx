// @vitest-environment jsdom
/**
 * M2-5.10.B.bis — Tests d'`ItemClosedBanner` (audit UX P0-3 + CS P0-2).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ItemClosedBanner } from '../components/ItemClosedBanner';

afterEach(cleanup);

describe('ItemClosedBanner', () => {
  test('renders nothing for a null item', () => {
    const { container } = render(<ItemClosedBanner item={null} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders nothing for a non-closed item', () => {
    const { container } = render(
      <ItemClosedBanner item={{ id: 'x', lifecycle_state: 'in_progress' }} />
    );
    expect(container.firstChild).toBeNull();
  });

  test('renders the banner for a closed item with closure date', () => {
    render(
      <ItemClosedBanner
        item={{
          id: 'x',
          lifecycle_state: 'closed',
          updated_at: '2026-05-19T10:00:00Z',
        }}
      />
    );
    expect(screen.getByText('Action clôturée')).toBeInTheDocument();
    expect(screen.getByText(/lecture seule/i)).toBeInTheDocument();
    expect(screen.getByText(/administrateur/i)).toBeInTheDocument();
  });

  test('renders status role for assistive technologies', () => {
    render(
      <ItemClosedBanner
        item={{ id: 'x', lifecycle_state: 'closed', updated_at: '2026-05-19T00:00:00Z' }}
      />
    );
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  test('prefers closed_at over updated_at when both are present', () => {
    render(
      <ItemClosedBanner
        item={{
          id: 'x',
          lifecycle_state: 'closed',
          closed_at: '2026-04-01T10:00:00Z',
          updated_at: '2026-05-19T10:00:00Z',
        }}
      />
    );
    // Date affichée doit refléter closed_at (04/01 vs 05/19).
    expect(screen.getByText(/01\/04/)).toBeInTheDocument();
  });
});
