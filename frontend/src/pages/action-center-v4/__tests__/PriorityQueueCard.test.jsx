// @vitest-environment jsdom
/**
 * M2-5.10.D — Tests d'`PriorityQueueCard` (item de la file prioritaire).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { PriorityQueueCard } from '../components/narrative/PriorityQueueCard';

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

  // ── M2-5.10.bis clôture — opacity-60 si lifecycle_state === closed ──
  test('opacifies the card visually when the item is closed (audit CS P1-3)', () => {
    render(
      <PriorityQueueCard item={{ ...sampleItem, lifecycle_state: 'closed' }} onOpenItem={vi.fn()} />
    );
    const card = screen.getByRole('button', { name: /ouvrir l'action/i });
    expect(card.className).toMatch(/opacity-60/);
  });

  test('keeps the card at full opacity for non-closed items', () => {
    render(<PriorityQueueCard item={sampleItem} onOpenItem={vi.fn()} />);
    const card = screen.getByRole('button', { name: /ouvrir l'action/i });
    expect(card.className).not.toMatch(/opacity-60/);
  });

  // ── M2-5.11.D — libellé € sous le titre (maquette pilotage v031 §917) ─
  test('renders the € amount under the title when impact_at_risk_eur is set', () => {
    const { container } = render(
      <PriorityQueueCard item={{ ...sampleItem, impact_at_risk_eur: 3400 }} onOpenItem={vi.fn()} />
    );
    // fmtEurShort(3400) → "3,4 k€". `\s` matche aussi U+00A0 (espace
    // insécable produit par toLocaleString fr-FR sur certains builds ICU).
    expect(container.textContent).toMatch(/3,4\s?k€/);
  });

  test('hides the € block when impact_at_risk_eur is null (no menteur tiret)', () => {
    const { container } = render(
      <PriorityQueueCard item={{ ...sampleItem, impact_at_risk_eur: null }} onOpenItem={vi.fn()} />
    );
    // Aucune occurrence de " k€" ni " M€" ni " €" — la doctrine v0.3 §6.6
    // refuse le « 0 € » ou « — € » menteur sur les cartes pilotage.
    expect(container.textContent).not.toMatch(/k€|M€/);
  });

  // ── M2-5.11.E — libellé pilote sous le titre ──────────────────────────
  test('renders the owner display name when item.owner_display_name is set', () => {
    render(
      <PriorityQueueCard
        item={{ ...sampleItem, owner_display_name: 'M. Dupont' }}
        onOpenItem={vi.fn()}
      />
    );
    expect(screen.getByText('M. Dupont')).toBeInTheDocument();
  });

  test('renders « Non assigné » when owner_display_name is null', () => {
    render(
      <PriorityQueueCard item={{ ...sampleItem, owner_display_name: null }} onOpenItem={vi.fn()} />
    );
    expect(screen.getByText(/non assigné/i)).toBeInTheDocument();
  });
});
