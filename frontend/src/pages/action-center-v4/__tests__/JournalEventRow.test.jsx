// @vitest-environment jsdom
/**
 * M2-5.10.E — Tests de `JournalEventRow` (ligne d'event dans la timeline).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { JournalEventRow } from '../components/JournalEventRow';

afterEach(cleanup);

const baseEvent = {
  id: 'e1',
  action_item_id: 'item-1',
  action_item_title: 'Audit SMÉ Toulouse',
  event_type: 'state_changed',
  actor_type: 'system',
  actor_id: null,
  actor_name: null,
  actor_role: null,
  occurred_at: '2026-05-20T07:18:00Z',
};

describe('JournalEventRow', () => {
  test('renders the FR label for known event_type', () => {
    render(<JournalEventRow event={baseEvent} onOpenItem={vi.fn()} />);
    expect(screen.getByText("Transition d'état")).toBeInTheDocument();
  });

  test('renders the action_item_title as a clickable button', () => {
    render(<JournalEventRow event={baseEvent} onOpenItem={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Audit SMÉ Toulouse' })).toBeInTheDocument();
  });

  test('clicking the item title calls onOpenItem with the item id', () => {
    const onOpenItem = vi.fn();
    render(<JournalEventRow event={baseEvent} onOpenItem={onOpenItem} />);
    fireEvent.click(screen.getByRole('button', { name: 'Audit SMÉ Toulouse' }));
    expect(onOpenItem).toHaveBeenCalledWith('item-1');
  });

  test('renders the PROMEOS pill for system actor', () => {
    render(<JournalEventRow event={baseEvent} onOpenItem={vi.fn()} />);
    expect(screen.getByText('PROMEOS')).toBeInTheDocument();
  });

  test('renders the actor name for user actor', () => {
    render(
      <JournalEventRow
        event={{
          ...baseEvent,
          actor_type: 'user',
          actor_id: 'a',
          actor_name: 'Sophie Marin',
        }}
        onOpenItem={vi.fn()}
      />
    );
    expect(screen.getByText('Sophie Marin')).toBeInTheDocument();
    expect(screen.queryByText('PROMEOS')).not.toBeInTheDocument();
  });

  test('falls back to actor_role when actor_name is null for user', () => {
    render(
      <JournalEventRow
        event={{
          ...baseEvent,
          actor_type: 'user',
          actor_id: 'a',
          actor_name: null,
          actor_role: 'energy_manager',
        }}
        onOpenItem={vi.fn()}
      />
    );
    expect(screen.getByText('energy_manager')).toBeInTheDocument();
  });

  test('falls back to raw event_type when unknown', () => {
    render(
      <JournalEventRow event={{ ...baseEvent, event_type: 'invented_xyz' }} onOpenItem={vi.fn()} />
    );
    expect(screen.getByText('invented_xyz')).toBeInTheDocument();
  });

  test('renders the occurred_at time in HH:MM FR format', () => {
    render(<JournalEventRow event={baseEvent} onOpenItem={vi.fn()} />);
    // Format navigateur 2-digit FR — accepte la fenêtre de timezone locale.
    expect(screen.getByText(/^\d{2}:\d{2}$/)).toBeInTheDocument();
  });
});
