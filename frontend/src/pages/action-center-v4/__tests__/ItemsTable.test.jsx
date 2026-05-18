// @vitest-environment jsdom
/**
 * M2-5.2 — Tests du composant ItemsTable (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ItemsTable } from '../components/ItemsTable';

// Pas de `globals: true` dans vite.config → cleanup RTL explicite obligatoire.
afterEach(cleanup);

const sampleItems = [
  {
    id: 'item-1',
    title: 'Vérifier consommation HP/HC Q3',
    lifecycle_state: 'triaged',
    domain: 'energy',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'item-2',
    title: 'Déclaration OPERAT 2026',
    lifecycle_state: 'planned',
    domain: 'compliance',
    updated_at: null,
    created_at: new Date(Date.now() - 86400000).toISOString(), // hier
  },
];

describe('ItemsTable', () => {
  test('renders one row per item', () => {
    render(<ItemsTable items={sampleItems} />);
    expect(screen.getByText('Vérifier consommation HP/HC Q3')).toBeInTheDocument();
    expect(screen.getByText('Déclaration OPERAT 2026')).toBeInTheDocument();
  });

  test('renders a lifecycle badge per row', () => {
    render(<ItemsTable items={sampleItems} />);
    expect(screen.getByText('Trié')).toBeInTheDocument();
    expect(screen.getByText('Planifié')).toBeInTheDocument();
  });

  test('renders an em dash when domain is null', () => {
    render(
      <ItemsTable
        items={[
          {
            id: '1',
            title: 'x',
            lifecycle_state: 'new',
            domain: null,
            updated_at: new Date().toISOString(),
          },
        ]}
      />
    );
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  test('falls back to created_at when updated_at is null', () => {
    render(<ItemsTable items={sampleItems} />);
    expect(screen.getByText('hier')).toBeInTheDocument();
  });

  test('renders no body row for an empty array', () => {
    const { container } = render(<ItemsTable items={[]} />);
    expect(container.querySelectorAll('tbody tr').length).toBe(0);
  });

  test('rows carry no cursor-pointer (no false affordance in M2-5.2)', () => {
    const { container } = render(<ItemsTable items={sampleItems} />);
    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    rows.forEach((tr) => {
      expect(tr.className).not.toContain('cursor-pointer');
    });
  });
});
