// @vitest-environment jsdom
/**
 * M2-5.10.D — Tests d'intégration de la page Pilotage / File prioritaire.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render as rtlRender, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../hooks/v4', () => ({
  usePilotageFilePrioritaire: vi.fn(),
  useActionCenterV4Items: vi.fn(),
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
  useActionCenterV4Evidences: vi.fn(),
  useActionCenterV4Blockers: vi.fn(),
  useActionCenterV4Links: vi.fn(),
  useActionCenterV4Impact: vi.fn(),
  // M2-5.11.C — NarrativeBar consomme useActionCenterV4Summary au montage.
  useActionCenterV4Summary: vi.fn(),
}));

// M2-5.12 — la page consomme useAuth pour le persona du Masthead enrichi.
// On mock pour éviter d'avoir à wrapper chaque test dans AuthProvider.
vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, prenom: 'Sophie', nom: 'Marin', email: 'sophie@helios.fr' },
    org: { id: 1, nom: 'Groupe HELIOS' },
    role: 'energy_manager',
  }),
}));

import {
  usePilotageFilePrioritaire,
  useActionCenterV4Items,
  useActionCenterV4Item,
  useActionCenterV4Events,
  useActionCenterV4Evidences,
  useActionCenterV4Blockers,
  useActionCenterV4Links,
  useActionCenterV4Impact,
  useActionCenterV4Summary,
} from '../../../hooks/v4';
import { ActionCenterV4PilotagePage } from '../ActionCenterV4PilotagePage';
import { setupV4HooksDefault } from './testUtils/v4Mocks';

function render(ui) {
  return rtlRender(
    <MemoryRouter initialEntries={['/action-center-v4/pilotage']}>{ui}</MemoryRouter>
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
    useActionCenterV4Summary,
  });
});

afterEach(cleanup);

function mockPilotage(value) {
  usePilotageFilePrioritaire.mockReturnValue({
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  });
}

describe('ActionCenterV4PilotagePage', () => {
  test('renders the masthead title', () => {
    mockPilotage({ data: { items: [], limit: 5 } });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByText(/centre d'action/i)).toBeInTheDocument();
  });

  test('renders the tabs (Pilotage active, Référentiel inactive)', () => {
    mockPilotage({ data: { items: [], limit: 5 } });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByRole('tab', { name: /pilotage/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /référentiel/i })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  test('renders the file prioritaire section title and subtitle', () => {
    mockPilotage({ data: { items: [], limit: 5 } });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByText('File prioritaire')).toBeInTheDocument();
    expect(screen.getByText(/risques, décisions et actions/i)).toBeInTheDocument();
  });

  test('renders a loading skeleton (5 rows)', () => {
    mockPilotage({ loading: true });
    const { container } = render(<ActionCenterV4PilotagePage />);
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThanOrEqual(5);
  });

  test('renders the empty state when no P0/P1 active', () => {
    mockPilotage({ data: { items: [], limit: 5 } });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByText(/aucune action prioritaire aujourd'hui/i)).toBeInTheDocument();
  });

  test('renders an error state with retry', () => {
    const refetch = vi.fn();
    mockPilotage({
      error: { code: 'INTERNAL', message: 'Server error' },
      refetch,
    });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByText(/impossible de charger la file prioritaire/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText('Réessayer'));
    expect(refetch).toHaveBeenCalled();
  });

  test('renders the priority queue cards when data is loaded', () => {
    mockPilotage({
      data: {
        items: [
          {
            id: '1',
            title: 'Anomalie Lyon facture',
            kind: 'anomaly',
            priority_bracket: 'P0',
            priority_score: 92,
            lifecycle_state: 'new',
            domain: 'facturation',
          },
          {
            id: '2',
            title: 'Audit SMÉ Toulouse',
            kind: 'action',
            priority_bracket: 'P0',
            priority_score: 88,
            lifecycle_state: 'triaged',
            domain: 'conformite',
          },
        ],
        limit: 5,
      },
    });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.getByText('Anomalie Lyon facture')).toBeInTheDocument();
    expect(screen.getByText('Audit SMÉ Toulouse')).toBeInTheDocument();
    // Le compteur de la section affiche le total d'items.
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  test('clicking a card opens the detail drawer', () => {
    mockPilotage({
      data: {
        items: [
          {
            id: '1',
            title: 'Anomalie X',
            kind: 'anomaly',
            priority_bracket: 'P0',
            priority_score: 90,
            lifecycle_state: 'new',
          },
        ],
        limit: 5,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: {
        id: '1',
        title: 'Anomalie X',
        kind: 'anomaly',
        lifecycle_state: 'new',
        priority_bracket: 'P0',
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4PilotagePage />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /ouvrir l'action : anomalie x/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  test('requests the file prioritaire with limit=5', () => {
    mockPilotage({ data: { items: [], limit: 5 } });
    render(<ActionCenterV4PilotagePage />);
    expect(usePilotageFilePrioritaire).toHaveBeenCalledWith({ limit: 5 });
  });
});
