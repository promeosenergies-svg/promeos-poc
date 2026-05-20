// @vitest-environment jsdom
/**
 * M2-5.3.A / M2-5.8.B / M2-5.10.A — Tests d'`ItemsTable` (rendu jsdom).
 *
 * Restyle Sol M2-5.10.A : 5 colonnes (Classement · Item · État · Domaine ·
 * Priorité). La colonne « Mis à jour » est retirée (absente de la maquette
 * §8.3) — la date reste dans le drawer détail. Le `kind` est rendu en MONO
 * uppercase (ANOMALIE / ACTION / DÉCISION / SIGNAL / PREUVE / ÉCHÉANCE /
 * RECO).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { ItemsTable } from '../components/ItemsTable';

afterEach(cleanup);

const noop = () => {};

const sampleItems = [
  {
    id: 'item-1',
    title: 'Vérifier consommation HP/HC Q3',
    kind: 'anomaly',
    priority_bracket: 'P1',
    priority_score: 73,
    lifecycle_state: 'triaged',
    domain: 'conformite',
  },
  {
    id: 'item-2',
    title: 'Déclaration OPERAT 2026',
    kind: 'deadline',
    priority_bracket: 'P2',
    priority_score: 55,
    lifecycle_state: 'planned',
    domain: 'facturation',
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

  // ── M2-5.10.A — 5 colonnes maquette + masquage « Mis à jour » ─────
  test('renders exactly 5 column headers (maquette §8.3)', () => {
    const { container } = render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    const ths = container.querySelectorAll('thead th');
    expect(ths.length).toBe(5);
    // « Mis à jour » a été retirée (drawer détail le porte).
    expect(container.querySelector('thead')).not.toHaveTextContent('Mis à jour');
  });
});

describe('ItemsTable — a11y clavier + priorité + kind FR (M2-5.8.B)', () => {
  const sample = [
    {
      id: 'a',
      title: 'Vérifier HP/HC',
      kind: 'anomaly',
      priority_bracket: 'P0',
      priority_score: 92,
      lifecycle_state: 'new',
      domain: 'optimisation',
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

  test('renders the priority bracket and score (M2-5.10.A)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(screen.getByText('P0')).toBeInTheDocument();
    expect(screen.getByText('92')).toBeInTheDocument();
  });

  test('renders the kind label in FR uppercase (M2-5.10.A)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    // KindCell affiche le label MONO uppercase via KIND_LABELS_UPPER.
    expect(screen.getByText('ANOMALIE')).toBeInTheDocument();
    expect(screen.queryByText('anomaly')).not.toBeInTheDocument();
  });

  test('renders the domain in FR, not the raw backend value (M2-5.9.bis)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    // DomainChip rend la valeur en mixed-case via DOMAIN_LABELS (chip MONO).
    expect(screen.getByText('Optimisation énergétique')).toBeInTheDocument();
    expect(screen.queryByText('optimisation')).not.toBeInTheDocument();
  });

  test('renders the upper FR label for all 7 backend kinds (M2-5.10.A)', () => {
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
    }));
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    ['ANOMALIE', 'ACTION', 'DÉCISION', 'SIGNAL', 'PREUVE', 'ÉCHÉANCE', 'RECO'].forEach((label) =>
      expect(screen.getByText(label)).toBeInTheDocument()
    );
  });

  test('falls back to "TYPE INCONNU" for an unknown kind (M2-5.10.A)', () => {
    const items = [
      {
        id: 'x',
        title: 'T',
        kind: 'invented_kind',
        priority_bracket: 'P2',
        lifecycle_state: 'new',
      },
    ];
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    expect(screen.getByText('TYPE INCONNU')).toBeInTheDocument();
  });

  // ── M2-5.10.A — strip vertical 3px couleur priorité (signature maquette) ──
  test('the row carries data-priority for the left strip rendering', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('data-priority', 'P0');
  });
});
