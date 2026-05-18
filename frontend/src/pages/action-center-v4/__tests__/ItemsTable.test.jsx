// @vitest-environment jsdom
/**
 * M2-5.3.A / M2-5.8.B — Tests du composant ItemsTable (rendu jsdom).
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
    kind: 'anomaly',
    priority_bracket: 'P1',
    lifecycle_state: 'triaged',
    domain: 'energy',
    updated_at: new Date().toISOString(),
  },
  {
    id: 'item-2',
    title: 'Déclaration OPERAT 2026',
    kind: 'deadline',
    priority_bracket: 'P2',
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

  test('falls back to created_at when updated_at is null', () => {
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    expect(screen.getByText('hier')).toBeInTheDocument();
  });

  test('renders no body row for an empty array', () => {
    const { container } = render(<ItemsTable items={[]} onOpenItem={noop} />);
    expect(container.querySelectorAll('tbody tr').length).toBe(0);
  });

  test('rows carry cursor-pointer (clickable affordance)', () => {
    const { container } = render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    rows.forEach((tr) => expect(tr.className).toContain('cursor-pointer'));
  });

  test('clicking a row calls onOpenItem with the item', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sampleItems} onOpenItem={onOpenItem} />);
    fireEvent.click(screen.getByText('Vérifier consommation HP/HC Q3').closest('tr'));
    expect(onOpenItem).toHaveBeenCalledWith(sampleItems[0]);
  });
});

describe('ItemsTable — a11y clavier + priorité + kind FR (M2-5.8.B)', () => {
  const sample = [
    {
      id: 'a',
      title: 'Vérifier HP/HC',
      kind: 'anomaly',
      priority_bracket: 'P0',
      lifecycle_state: 'new',
      domain: 'energy',
      updated_at: new Date().toISOString(),
    },
  ];
  const rowOf = (text) => screen.getByText(text).closest('tr');

  test('a clickable row is focusable (tabindex=0)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('tabindex', '0');
  });

  test('a clickable row carries role="button"', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('role', 'button');
  });

  test('a clickable row carries an explicit aria-label', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC').getAttribute('aria-label')).toMatch(/ouvrir.*vérifier hp\/hc/i);
  });

  test('Enter on a row calls onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'Enter' });
    expect(onOpenItem).toHaveBeenCalledWith(sample[0]);
  });

  test('Space on a row calls onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: ' ' });
    expect(onOpenItem).toHaveBeenCalledWith(sample[0]);
  });

  test('other keys do not trigger onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'Escape' });
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'a' });
    expect(onOpenItem).not.toHaveBeenCalled();
  });

  test('a row carries the focus-visible ring class', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC').className).toMatch(/focus-visible:ring/);
  });

  test('renders the priority badge', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Critique')).toBeInTheDocument();
  });

  test('renders the kind in FR, not the raw backend value', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Anomalie')).toBeInTheDocument();
    expect(screen.queryByText('anomaly')).not.toBeInTheDocument();
  });

  test('renders the FR label for all 7 backend kinds', () => {
    const items = [
      'anomaly',
      'action',
      'decision',
      'signal',
      'evidence_request',
      'deadline',
      'recommendation',
    ].map((kind, i) => ({
      id: `i${i}`,
      title: `T${i}`,
      kind,
      priority_bracket: 'P2',
      lifecycle_state: 'new',
      updated_at: new Date().toISOString(),
    }));
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    [
      'Anomalie',
      'Action',
      'Décision',
      'Signal',
      'Demande de preuve',
      'Échéance',
      'Recommandation',
    ].forEach((label) => expect(screen.getByText(label)).toBeInTheDocument());
  });

  test('falls back to "Type inconnu" for an unknown kind', () => {
    const items = [
      {
        id: 'x',
        title: 'T',
        kind: 'invented_kind',
        priority_bracket: 'P2',
        lifecycle_state: 'new',
        updated_at: new Date().toISOString(),
      },
    ];
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Type inconnu')).toBeInTheDocument();
  });
});
