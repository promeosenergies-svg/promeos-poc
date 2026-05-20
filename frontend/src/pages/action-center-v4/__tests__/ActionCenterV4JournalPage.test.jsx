// @vitest-environment jsdom
/**
 * M2-5.10.E — Tests d'intégration de la page Journal (flux org-wide 7j).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render as rtlRender, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../hooks/v4', () => ({
  usePilotageJournal: vi.fn(),
  useActionCenterV4Items: vi.fn(),
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
  useActionCenterV4Evidences: vi.fn(),
  useActionCenterV4Blockers: vi.fn(),
  useActionCenterV4Links: vi.fn(),
  useActionCenterV4Impact: vi.fn(),
}));

import {
  usePilotageJournal,
  useActionCenterV4Items,
  useActionCenterV4Item,
  useActionCenterV4Events,
  useActionCenterV4Evidences,
  useActionCenterV4Blockers,
  useActionCenterV4Links,
  useActionCenterV4Impact,
} from '../../../hooks/v4';
import { ActionCenterV4JournalPage } from '../ActionCenterV4JournalPage';
import { setupV4HooksDefault } from './testUtils/v4Mocks';

function render(ui) {
  return rtlRender(
    <MemoryRouter initialEntries={['/action-center-v4/pilotage/journal']}>{ui}</MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  // M2-5.11.B — défauts partagés (cf. testUtils/v4Mocks.js).
  setupV4HooksDefault({
    useActionCenterV4Items,
    useActionCenterV4Item,
    useActionCenterV4Events,
    useActionCenterV4Evidences,
    useActionCenterV4Blockers,
    useActionCenterV4Links,
    useActionCenterV4Impact,
  });
});

afterEach(cleanup);

function mockJournal(value) {
  usePilotageJournal.mockReturnValue({
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  });
}

describe('ActionCenterV4JournalPage', () => {
  test('renders the masthead title (multiple occurrences allowed: masthead + tab)', () => {
    mockJournal({ data: { items: [], total: 0, since_days: 7, limit: 100 } });
    render(<ActionCenterV4JournalPage />);
    // « Centre d'action » apparaît dans le masthead Sol et probablement dans
    // un éventuel composant nav — getAllByText accepte multi-occurrences.
    expect(screen.getAllByText(/centre d'action/i).length).toBeGreaterThanOrEqual(1);
  });

  test('renders the tabs with Pilotage active', () => {
    mockJournal({ data: { items: [], total: 0, since_days: 7, limit: 100 } });
    render(<ActionCenterV4JournalPage />);
    // PilotageTabs : « Pilotage » est l'onglet principal actif sur cette
    // route. PilotageViewToggle « Décisions/Journal » porte d'autres tabs.
    const pilotageTabs = screen.getAllByRole('tab', { name: /^pilotage$/i });
    expect(pilotageTabs.length).toBeGreaterThanOrEqual(1);
    expect(pilotageTabs[0]).toHaveAttribute('aria-selected', 'true');
  });

  test('renders the view toggle with Journal active', () => {
    mockJournal({ data: { items: [], total: 0, since_days: 7, limit: 100 } });
    render(<ActionCenterV4JournalPage />);
    expect(screen.getByRole('tab', { name: /^journal$/i })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: /^décisions$/i })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  test('renders a loading skeleton (3 placeholders)', () => {
    mockJournal({ loading: true });
    const { container } = render(<ActionCenterV4JournalPage />);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThanOrEqual(3);
  });

  test('renders the empty state when no events', () => {
    mockJournal({ data: { items: [], total: 0, since_days: 7, limit: 100 } });
    render(<ActionCenterV4JournalPage />);
    expect(screen.getByText(/aucun événement récent/i)).toBeInTheDocument();
  });

  test('renders an error state with retry', () => {
    const refetch = vi.fn();
    mockJournal({ error: { code: 'INTERNAL', message: 'fail' }, refetch });
    render(<ActionCenterV4JournalPage />);
    expect(screen.getByText(/impossible de charger le journal/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Réessayer'));
    expect(refetch).toHaveBeenCalled();
  });

  test('renders day-groups when events are loaded', () => {
    const today = new Date().toISOString();
    const yesterday = new Date(Date.now() - 86400000).toISOString();
    mockJournal({
      data: {
        items: [
          {
            id: 'e1',
            action_item_id: 'i1',
            action_item_title: 'Audit SMÉ',
            event_type: 'state_changed',
            actor_type: 'system',
            occurred_at: today,
          },
          {
            id: 'e2',
            action_item_id: 'i2',
            action_item_title: 'Anomalie R20',
            event_type: 'created',
            actor_type: 'system',
            occurred_at: yesterday,
          },
        ],
        total: 2,
        since_days: 7,
        limit: 100,
      },
    });
    render(<ActionCenterV4JournalPage />);
    expect(screen.getByText("Aujourd'hui")).toBeInTheDocument();
    expect(screen.getByText('Hier')).toBeInTheDocument();
    expect(screen.getByText('Audit SMÉ')).toBeInTheDocument();
    expect(screen.getByText('Anomalie R20')).toBeInTheDocument();
  });

  test('clicking an event item title opens the drawer', () => {
    const today = new Date().toISOString();
    mockJournal({
      data: {
        items: [
          {
            id: 'e1',
            action_item_id: 'i1',
            action_item_title: 'Audit SMÉ',
            event_type: 'state_changed',
            actor_type: 'system',
            occurred_at: today,
          },
        ],
        total: 1,
        since_days: 7,
        limit: 100,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: {
        id: 'i1',
        title: 'Audit SMÉ',
        kind: 'action',
        lifecycle_state: 'triaged',
        priority_bracket: 'P0',
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4JournalPage />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: 'Audit SMÉ' }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  test('requests the journal with sinceDays=7 and limit=100', () => {
    mockJournal({ data: { items: [], total: 0, since_days: 7, limit: 100 } });
    render(<ActionCenterV4JournalPage />);
    expect(usePilotageJournal).toHaveBeenCalledWith({ sinceDays: 7, limit: 100 });
  });
});
