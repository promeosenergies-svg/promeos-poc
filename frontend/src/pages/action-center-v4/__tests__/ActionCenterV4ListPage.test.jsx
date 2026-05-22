// @vitest-environment jsdom
/**
 * M2-5.2 — Tests d'intégration de la page liste (rendu jsdom, hook mocké).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render as rtlRender, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// M2-5.10.D — la page Référentiel intègre `PilotageTabs` qui utilise
// `useLocation` (react-router-dom) → tous les renders doivent être wrappés
// dans un Router. Helper local pour ne pas répéter ça à chaque test.
function render(ui, { route = '/action-center-v4' } = {}) {
  return rtlRender(<MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>);
}

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Items: vi.fn(),
  useActionCenterV4Item: vi.fn(),
  useActionCenterV4Events: vi.fn(),
  // M2-5.10.B.bis — l'onglet par défaut du drawer est désormais « Preuves »
  // (au lieu de « Historique »), donc tous les tests qui ouvrent le drawer
  // doivent mocker aussi les hooks evidences/blockers/links.
  useActionCenterV4Evidences: vi.fn(),
  useActionCenterV4Blockers: vi.fn(),
  useActionCenterV4Links: vi.fn(),
  // M2-5.10.C — ImpactSection consomme useActionCenterV4Impact dès l'ouverture
  // du drawer (section affichée entre ItemHeader et Tabs).
  useActionCenterV4Impact: vi.fn(),
  // M2-5.11.C — NarrativeBar consomme useActionCenterV4Summary au montage.
  useActionCenterV4Summary: vi.fn(),
}));

import {
  useActionCenterV4Items,
  useActionCenterV4Item,
  useActionCenterV4Events,
  useActionCenterV4Evidences,
  useActionCenterV4Blockers,
  useActionCenterV4Links,
  useActionCenterV4Impact,
  useActionCenterV4Summary,
} from '../../../hooks/v4';
import { ActionCenterV4ListPage } from '../ActionCenterV4ListPage';
import { emptySummary } from './testUtils/v4Mocks';

function mockHook(value) {
  useActionCenterV4Items.mockReturnValue({
    data: null,
    loading: false,
    error: null,
    refetch: vi.fn(),
    ...value,
  });
}

describe('ActionCenterV4ListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Le drawer est rendu en permanence (fermé tant que selectedItemId est
    // null) ; ItemDetailDrawer appelle useActionCenterV4Item dès le rendu.
    useActionCenterV4Item.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const emptyList = {
      data: { items: [], total: 0 },
      loading: false,
      error: null,
      refetch: vi.fn(),
    };
    useActionCenterV4Events.mockReturnValue(emptyList);
    useActionCenterV4Evidences.mockReturnValue(emptyList);
    useActionCenterV4Blockers.mockReturnValue(emptyList);
    useActionCenterV4Links.mockReturnValue(emptyList);
    // M2-5.10.C — ImpactSection se neutralise dès loading (skeleton inoffensif).
    useActionCenterV4Impact.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    // M2-5.11.C — NarrativeBar : 5 compteurs à 0 par défaut (cf. v4Mocks).
    useActionCenterV4Summary.mockReturnValue(emptySummary);
  });

  // Pas de `globals: true` dans vite.config → cleanup RTL explicite.
  afterEach(cleanup);

  test('renders a loading skeleton while loading', () => {
    mockHook({ loading: true });
    const { container } = render(<ActionCenterV4ListPage />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders the page title via the Sol masthead (no PageShell H1)', () => {
    mockHook({ data: { items: [], total: 0, offset: 0, limit: 20 } });
    render(<ActionCenterV4ListPage />);
    // M2-5.10.A.bis — le PageShell est monté en `editorialHeader` mode, le H1
    // Tailwind par défaut est supprimé. Seul le masthead Sol porte le titre
    // (1 occurrence). Le sous-titre PageShell « Nouveau (V4) — Pilote » a
    // disparu (hors-doctrine §6.1, audit UI Sol).
    expect(screen.getAllByText("Centre d'action").length).toBe(1);
  });

  // ── M2-5.10.A — masthead Sol au-dessus des filtres ────────────────
  test('renders the Sol masthead with subtitle and "MAJ live" tag', () => {
    mockHook({ data: { items: [], total: 0, offset: 0, limit: 20 } });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText(/référentiel complet/i)).toBeInTheDocument();
    expect(screen.getByText(/MAJ live/)).toBeInTheDocument();
  });

  // ── M2-5.10.A — filtre kind chips + composition AND avec lifecycle ──
  test('filters items by kind via the Row 1 chips', () => {
    mockHook({
      data: {
        items: [
          { id: '1', title: 'A', kind: 'anomaly', lifecycle_state: 'new' },
          { id: '2', title: 'B', kind: 'action', lifecycle_state: 'new' },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('B')).toBeInTheDocument();

    // Clic sur le chip « Anomalie » → seul A reste.
    fireEvent.click(screen.getByRole('button', { name: /filtrer par anomalie/i }));
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.queryByText('B')).not.toBeInTheDocument();
  });

  test('the kind reset chip "Tous les types" clears the filter', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'A', kind: 'anomaly', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    fireEvent.click(screen.getByRole('button', { name: /filtrer par anomalie/i }));
    fireEvent.click(screen.getByRole('button', { name: /filtrer par tous les types/i }));
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  test('the global "Réinitialiser" button clears both filters and returns to page 1', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'A', kind: 'anomaly', lifecycle_state: 'new' }],
        total: 50,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    fireEvent.click(screen.getByRole('button', { name: /filtrer par anomalie/i }));
    // Le bouton Réinitialiser ne s'affiche que filtre actif.
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser les filtres/i }));
    // Plus de filtre actif → la note de scope n'est plus visible.
    expect(screen.queryByText(/page courante/i)).not.toBeInTheDocument();
  });

  test('renders the empty state when there is no item', () => {
    mockHook({ data: { items: [], total: 0, offset: 0, limit: 20 } });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText(/aucune action à afficher/i)).toBeInTheDocument();
  });

  test('renders the items when data is loaded', () => {
    mockHook({
      data: {
        items: [
          {
            id: '1',
            title: 'Test action',
            lifecycle_state: 'new',
            domain: 'energy',
            updated_at: new Date().toISOString(),
          },
        ],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText('Test action')).toBeInTheDocument();
  });

  test('renders the error state with a retry that calls refetch', () => {
    const refetch = vi.fn();
    mockHook({
      error: { code: 'INTERNAL', message: 'Server error', status: 500 },
      refetch,
    });
    render(<ActionCenterV4ListPage />);
    const retry = screen.getByText('Réessayer');
    expect(retry).toBeInTheDocument();
    fireEvent.click(retry);
    expect(refetch).toHaveBeenCalled();
  });

  test('filters items client-side by lifecycle state', () => {
    mockHook({
      data: {
        items: [
          { id: '1', title: 'Action A', lifecycle_state: 'new' },
          { id: '2', title: 'Action B', lifecycle_state: 'triaged' },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByText('Action A')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'triaged' },
    });

    expect(screen.queryByText('Action A')).not.toBeInTheDocument();
    expect(screen.getByText('Action B')).toBeInTheDocument();
  });

  test('shows the page-scope note only once a filter is active', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    // M2-5.11.H — copy reformulée pour lever l'ambiguïté CS.
    expect(screen.queryByText(/20 items de cette page/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'triaged' },
    });
    expect(screen.getByText(/20 items de cette page/i)).toBeInTheDocument();
  });

  test('a filter that empties the page shows a distinct message and keeps pagination', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 50,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);

    fireEvent.change(screen.getByLabelText(/état/i), {
      target: { value: 'closed' },
    });

    // M2-5.10.A.bis — copy reformulée (audit CS P0-2 ambiguïté "page courante").
    expect(screen.getByText(/aucun résultat sur cette page/i)).toBeInTheDocument();
    // Pagination reste visible (total serveur 50) → pas de cul-de-sac navigation.
    expect(screen.getByLabelText('Page suivante')).toBeInTheDocument();
  });

  test('pagination "next" is disabled on a single page', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.getByLabelText('Page suivante')).toBeDisabled();
  });

  test('clicking a row opens the detail drawer', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: { id: '1', title: 'Action A', lifecycle_state: 'new' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4ListPage />);
    expect(screen.queryByRole('dialog')).toBeNull();

    fireEvent.click(screen.getByText('Action A').closest('tr'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  test('closing the drawer removes it from the DOM', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    useActionCenterV4Item.mockReturnValue({
      data: { id: '1', title: 'Action A', lifecycle_state: 'new' },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<ActionCenterV4ListPage />);
    fireEvent.click(screen.getByText('Action A').closest('tr'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Fermer'));
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  // ── M2-5.9.bis — changement de filtre → retour page 1 ─────────────
  test('changing the lifecycle filter resets pagination to page 1', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Action A', lifecycle_state: 'new' }],
        total: 50,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />);

    // Aller en page 2 → le hook est appelé avec offset 20.
    fireEvent.click(screen.getByLabelText('Page suivante'));
    expect(useActionCenterV4Items).toHaveBeenLastCalledWith({ offset: 20, limit: 20 });

    // Changer le filtre → la pagination repart en page 1 (offset 0).
    fireEvent.change(screen.getByLabelText(/état/i), { target: { value: 'closed' } });
    expect(useActionCenterV4Items).toHaveBeenLastCalledWith({ offset: 0, limit: 20 });
  });

  // ── M2-5.11.K — URL filter persistence (CX +0.3 backlog) ──────────
  test('hydrates filters from URL query params on initial render', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Filtré', lifecycle_state: 'triaged', kind: 'anomaly' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, {
      route: '/action-center-v4?state=triaged&kind=anomaly',
    });
    // Les chips sont initialisés depuis l'URL : on doit voir l'item après filtre.
    expect(screen.getByText('Filtré')).toBeInTheDocument();
    // Le hook a bien été appelé avec offset 0 (page 1 par défaut).
    expect(useActionCenterV4Items).toHaveBeenCalledWith({ offset: 0, limit: 20 });
  });

  test('hydrates page from URL ?page=N (deep link partagé)', () => {
    mockHook({
      data: {
        items: [{ id: '21', title: 'Item page 2', lifecycle_state: 'new' }],
        total: 50,
        offset: 20,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, { route: '/action-center-v4?page=2' });
    // Le hook est appelé avec offset 20 (page=2 → offset (2-1)*20).
    expect(useActionCenterV4Items).toHaveBeenCalledWith({ offset: 20, limit: 20 });
  });

  test('ignores invalid URL params (sanity check anti-injection)', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Tous', lifecycle_state: 'new' }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, {
      route: '/action-center-v4?state=invalid_state&kind=evil_kind&page=-99',
    });
    // L'item est rendu (les filtres invalides sont ignorés, pas de crash).
    expect(screen.getByText('Tous')).toBeInTheDocument();
    // page=-99 invalide → fallback page=1 → offset=0.
    expect(useActionCenterV4Items).toHaveBeenCalledWith({ offset: 0, limit: 20 });
  });

  // ── M2-6.C.2 — URL filter `without_owner` + banner (Q32=A) ────────

  test('M2-6.C.2 — filtre URL ?without_owner=true exclut items avec owner_id', () => {
    mockHook({
      data: {
        items: [
          // Item avec owner — doit être exclu par le filtre
          {
            id: '1',
            title: 'Avec owner',
            lifecycle_state: 'new',
            owner_id: 'aaaa-1111',
            owner_display_name: 'Marie Leclerc',
          },
          // Item sans owner — doit rester visible
          {
            id: '2',
            title: 'Sans owner',
            lifecycle_state: 'new',
            owner_id: null,
            owner_display_name: null,
          },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, {
      route: '/action-center-v4?without_owner=true',
    });
    // Seul l'item sans owner est rendu dans la table filtrée.
    expect(screen.queryByText('Avec owner')).not.toBeInTheDocument();
    expect(screen.getByText('Sans owner')).toBeInTheDocument();
  });

  test('M2-6.C.2 — banner « Filtre actif » visible quand ?without_owner=true', () => {
    mockHook({
      data: {
        items: [
          { id: '1', title: 'Item A', lifecycle_state: 'new', owner_id: null },
          { id: '2', title: 'Item B', lifecycle_state: 'new', owner_id: null },
        ],
        total: 2,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, {
      route: '/action-center-v4?without_owner=true',
    });
    const banner = screen.getByTestId('filter-without-owner-banner');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent(/items sans responsable/i);
    // Compteur résultats au pluriel pour ≥ 2 items.
    expect(banner).toHaveTextContent(/2\s*résultats/);
    // Bouton effacer présent + aria-label.
    const clearBtn = screen.getByTestId('filter-without-owner-clear');
    expect(clearBtn).toHaveAttribute('aria-label', 'Effacer le filtre Sans responsable');
  });

  test('M2-6.C.2 — banner absent quand pas de filtre URL', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'A', lifecycle_state: 'new', owner_id: null }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, { route: '/action-center-v4' });
    expect(screen.queryByTestId('filter-without-owner-banner')).toBeNull();
  });

  test('M2-6.C.2 — banner singulier « 1 résultat » si 1 seul item', () => {
    mockHook({
      data: {
        items: [{ id: '1', title: 'Solo', lifecycle_state: 'new', owner_id: null }],
        total: 1,
        offset: 0,
        limit: 20,
      },
    });
    render(<ActionCenterV4ListPage />, {
      route: '/action-center-v4?without_owner=true',
    });
    const banner = screen.getByTestId('filter-without-owner-banner');
    expect(banner).toHaveTextContent(/1\s*résultat[^s]/);
    expect(banner).not.toHaveTextContent(/résultats/);
  });
});
