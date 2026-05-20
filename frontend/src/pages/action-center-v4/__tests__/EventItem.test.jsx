// @vitest-environment jsdom
/**
 * M2-5.3.A — Tests du composant EventItem (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { EventItem } from '../components/EventItem';

afterEach(cleanup);

const baseEvent = {
  id: '1',
  event_type: 'state_changed',
  occurred_at: new Date().toISOString(),
};

describe('EventItem', () => {
  test('renders the FR label for a known event_type', () => {
    render(<EventItem event={{ ...baseEvent, actor_name: 'Alice' }} />);
    expect(screen.getByText("Transition d'état")).toBeInTheDocument();
  });

  test('falls back to the raw event_type when unknown', () => {
    render(<EventItem event={{ ...baseEvent, event_type: 'unknown_xyz' }} />);
    expect(screen.getByText('unknown_xyz')).toBeInTheDocument();
  });

  test('renders actor_name when present', () => {
    render(<EventItem event={{ ...baseEvent, actor_name: 'Alice' }} />);
    expect(screen.getByText('Alice')).toBeInTheDocument();
  });

  test('falls back to actor_role then to "Système"', () => {
    const { rerender } = render(
      <EventItem event={{ ...baseEvent, actor_role: 'admin', actor_name: null }} />
    );
    expect(screen.getByText('admin')).toBeInTheDocument();

    rerender(<EventItem event={{ ...baseEvent, actor_role: null, actor_name: null }} />);
    expect(screen.getByText('Système')).toBeInTheDocument();
  });

  test('renders the summary when present', () => {
    render(<EventItem event={{ ...baseEvent, summary: 'new → triaged' }} />);
    expect(screen.getByText('new → triaged')).toBeInTheDocument();
  });
});
