// @vitest-environment jsdom
/**
 * M2-5.3.A — Tests du composant ItemsTable (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { ItemsTable } from '../components/ItemsTable';

// Pas de `globals: true` dans vite.config → cleanup RTL explicite obligatoire.
afterEach(cleanup);

const noop = () => {};

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
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    expect(screen.getByText('Vérifier consommation HP/HC Q3')).toBeInTheDocument();
    expect(screen.getByText('Déclaration OPERAT 2026')).toBeInTheDocument();
  });

  test('renders a lifecycle badge per row', () => {
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
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
        onOpenItem={noop}
      />
    );
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  test('falls back to created_at when updated_at is null', () => {
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    expect(screen.getByText('hier')).toBeInTheDocument();
  });

  test('renders no body row for an empty array', () => {
    const { container } = render(<ItemsTable items={[]} onOpenItem={noop} />);
    expect(container.querySelectorAll('tbody tr').length).toBe(0);
  });

  test('rows carry cursor-pointer (clickable affordance in M2-5.3.A)', () => {
    const { container } = render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    rows.forEach((tr) => {
      expect(tr.className).toContain('cursor-pointer');
    });
  });

  test('clicking a row calls onOpenItem with the item', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sampleItems} onOpenItem={onOpenItem} />);
    fireEvent.click(screen.getByText('Vérifier consommation HP/HC Q3').closest('tr'));
    expect(onOpenItem).toHaveBeenCalledWith(sampleItems[0]);
  });
});
