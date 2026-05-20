// @vitest-environment jsdom
/**
 * M2-5.10.D — Tests d'`PriorityQueueCard` (item de la file prioritaire).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { PriorityQueueCard } from '../components/PriorityQueueCard';

afterEach(cleanup);

const sampleItem = {
  id: 'x',
  title: 'Vérifier consommation HP/HC Q3',
  description: 'Anomalie HP/HC détectée par Copilot',
  kind: 'anomaly',
  priority_bracket: 'P0',
  priority_score: 92,
  lifecycle_state: 'new',
  domain: 'optimisation',
};

describe('PriorityQueueCard', () => {
  test('renders the title and description', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Vérifier consommation HP/HC Q3')).toBeInTheDocument();
    expect(screen.getByText(/Anomalie HP\/HC/)).toBeInTheDocument();
  });

  test('renders the priority badge with score', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByText('P0')).toBeInTheDocument();
    expect(screen.getByText('92')).toBeInTheDocument();
  });

  test('renders the kind label uppercase', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByText('ANOMALIE')).toBeInTheDocument();
  });

  test('renders the lifecycle badge in FR', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Nouveau')).toBeInTheDocument();
  });

  test('renders the domain chip in FR', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByText('Optimisation énergétique')).toBeInTheDocument();
  });

  test('exposes data-priority on the article for CSS strip', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    expect(screen.getByRole('button', { name: /ouvrir l'action/i })).toHaveAttribute(
      'data-priority',
      'P0'
    );
  });

  test('is keyboard-accessible (tabIndex + role + aria-label)', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    const card = screen.getByRole('button', { name: /ouvrir l'action/i });
    expect(card).toHaveAttribute('tabindex', '0');
  });

  test('clicking calls onOpenItem with the item', () => {
    const onOpenItem = vi.fn();
    render(<PriorityQueueCard item={sampleItem} onOpenItem={onOpenItem} />);
    fireEvent.click(screen.getByRole('button', { name: /ouvrir l'action/i }));
    expect(onOpenItem).toHaveBeenCalledWith(sampleItem);
  });

  test('Enter / Space trigger onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<PriorityQueueCard item={sampleItem} onOpenItem={onOpenItem} />);
    const card = screen.getByRole('button', { name: /ouvrir l'action/i });
    fireEvent.keyDown(card, { key: 'Enter' });
    expect(onOpenItem).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(card, { key: ' ' });
    expect(onOpenItem).toHaveBeenCalledTimes(2);
  });

  test('hides description when absent', () => {
    render(<PriorityQueueCard item={{ ...sampleItem, description: null }} onOpenItem={vi.fn()} />);
    expect(screen.queryByText(/Anomalie HP\/HC/)).not.toBeInTheDocument();
  });
});
