// @vitest-environment jsdom
/**
 * M2-5.11.C — Tests du composant NarrativeBar (5 tuiles CFO).
 *
 * Couvre :
 * - États loading / error / data (visibles à l'utilisateur)
 * - Les 5 valeurs s'affichent dans l'ordre canonique
 * - Le bouton « Réessayer » appelle `refetch`
 * - L'a11y (`role="list"` + `aria-label` sur le groupe, `role="listitem"`
 *   sur les tuiles, `role="alert"` sur erreur)
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render as rtlRender, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Summary: vi.fn(),
}));

import { useActionCenterV4Summary } from '../../../hooks/v4';
import { NarrativeBar } from '../components/narrative/NarrativeBar';

// M2-6.C.2 — wrapper Router pour `useNavigate()` dans la tuile « Sans
// responsable » cliquable. MemoryRouter évite la dépendance window.location
// en environnement jsdom + permet d'inspecter les navigations via test.
function render(ui, { initialEntries = ['/'] } = {}) {
  return rtlRender(<MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe('NarrativeBar', () => {
  test('renders the loading skeleton (5 placeholders, aria-busy)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Skeleton : 5 div animées + un wrapper aria-busy.
    const wrapper = container.querySelector('[aria-busy="true"]');
    expect(wrapper).toBeTruthy();
    expect(container.querySelectorAll('.animate-pulse').length).toBe(5);
  });

  test('renders the error banner with retry button', () => {
    const refetch = vi.fn();
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      error: { code: 'INTERNAL', message: 'Server fault' },
      refetch,
    });
    render(<NarrativeBar />);
    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/impossible de charger la synthèse/i);
    expect(alert).toHaveTextContent(/server fault/i);

    fireEvent.click(screen.getByText(/réessayer/i));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  test('renders all 5 tiles in canonical order when data is loaded (M2-5.12 maquette)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 3,
        count_p1: 7,
        count_without_owner: 12,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 2,
        count_secured: 9,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // M2-5.11.G — sémantique role="list" (5 tuiles = liste de stats).
    const list = screen.getByRole('list', { name: /synthèse du centre d'action/i });
    expect(list).toBeInTheDocument();

    // M2-5.12 — ordre canonique nouvelle maquette : Décisions P0/P1 (= 3+7=10)
    // · Sans responsable (12) · Bloqués (2) · Preuvés (9) · SLA en retard (—).
    const values = screen.getAllByTestId('stat-tile-value').map((n) => n.textContent);
    expect(values).toEqual(['10', '12', '2', '9', '—']);

    // M2-5.12 — libellés alignés maquette Sophie Marin 2026-05-22.
    expect(screen.getByText(/décisions p0\/p1/i)).toBeInTheDocument();
    expect(screen.getByText(/sans responsable/i)).toBeInTheDocument();
    expect(screen.getByText(/bloqués/i)).toBeInTheDocument();
    expect(screen.getByText(/preuvés/i)).toBeInTheDocument();
    expect(screen.getByText(/sla en retard/i)).toBeInTheDocument();
  });

  test('renders zero values without crashing (empty org)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 0,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // M2-5.12 — 4 zéros (Décisions/Sans responsable/Bloqués/Preuvés) + SLA placeholder.
    const values = screen.getAllByTestId('stat-tile-value').map((n) => n.textContent);
    expect(values).toEqual(['0', '0', '0', '0', '—']);
  });

  // ── M2-5.11.J — Breakdown CFO sous « Sans pilote » ─────────────────
  test('renders the P0/P1 breakdown under « Sans pilote » when both > 0', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 3,
        count_p1: 7,
        count_without_owner: 5,
        count_p0_without_owner: 2,
        count_p1_without_owner: 3,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // « Sans pilote » porte la sous-ligne « 2 P0 · 3 P1 ».
    const breakdowns = screen.getAllByTestId('stat-tile-breakdown').map((n) => n.textContent);
    expect(breakdowns).toEqual(['2 P0 · 3 P1']);
  });

  test('renders only P1 breakdown when count_p0_without_owner = 0', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 4,
        count_without_owner: 3,
        count_p0_without_owner: 0,
        count_p1_without_owner: 3,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    const breakdowns = screen.getAllByTestId('stat-tile-breakdown').map((n) => n.textContent);
    expect(breakdowns).toEqual(['3 P1']);
  });

  // ── M2-6.C.2 — Tuile « Sans responsable » cliquable (Q32=A) ──────

  test('M2-6.C.2 — tuile « Sans responsable » devient bouton cliquable si count > 0', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 3,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // La tuile cliquable est rendue comme <button> (vs <div> pour les autres).
    // Recherche par text « Sans responsable » + vérif tag/role.
    const tuile = screen
      .getByText(/sans responsable/i)
      .closest('[data-testid="stat-tile-clickable"]');
    expect(tuile).toBeInTheDocument();
    expect(tuile?.tagName).toBe('BUTTON');
    expect(tuile).toHaveAttribute('type', 'button');
  });

  // ── M2-6.C audit a11y — aria-label + structure ul/li ────────────────

  test("M2-6.C audit a11y — la tuile interactive porte un aria-label explicite (lecteur d'écran)", () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 3,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // aria-label complet incluant label + value + action — le screen reader
    // annonce « Sans responsable : 3. Voir la liste filtrée. » (CFO Marie).
    const tuile = screen.getByRole('button', {
      name: /sans responsable.*3.*voir la liste filtrée/i,
    });
    expect(tuile).toBeInTheDocument();
    expect(tuile).toHaveAttribute('data-testid', 'stat-tile-clickable');
  });

  test("M2-6.C audit a11y — les tuiles non-interactives n'ont pas d'aria-label parasite", () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 1,
        count_p1: 2,
        count_without_owner: 0, // tuile inerte
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Aucun bouton dans la barre (la tuile « Sans responsable » est inerte ici).
    expect(screen.queryByTestId('stat-tile-clickable')).toBeNull();
    // Les tuiles non-interactives ne doivent pas porter d'aria-label (le texte
    // visible suffit aux lecteurs d'écran via la sémantique listitem du parent).
    const tiles = container.querySelectorAll('[data-testid="stat-tile-value"]');
    tiles.forEach((valueNode) => {
      const tile = valueNode.parentElement;
      expect(tile).not.toHaveAttribute('aria-label');
    });
  });

  test('M2-6.C audit a11y — structure sémantique ul + 5 li (rôle list/listitem natif)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 1,
        count_p1: 2,
        count_without_owner: 0,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Le parent est un <ul> (rôle list implicite), pas un <div role="list">
    // (la spec ARIA interdit role="listitem" sur <button> — § audit M2-6.C).
    const ul = container.querySelector('ul[data-testid="narrative-bar"]');
    expect(ul).toBeInTheDocument();
    expect(ul?.tagName).toBe('UL');
    // 5 enfants <li> directs (rôle listitem implicite).
    const lis = ul?.querySelectorAll(':scope > li');
    expect(lis?.length).toBe(5);
  });

  // ── M2-6.C audit sécu — sanitization message erreur (CWE-209) ─────

  test("M2-6.C audit sécu — l'erreur strippe les caractères de contrôle (\\n, \\r, \\t)", () => {
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      // Simule un message serveur avec stack trace multi-ligne (CWE-209).
      error: { code: 'INTERNAL', message: 'Server fault\n  at /app/api.py:42\r\n  in resolve_org' },
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    const alert = screen.getByRole('alert');
    // Les sauts de ligne sont collapsés en espace unique — pas de retour à
    // la ligne brut qui casserait la barre + révèlerait la structure interne.
    expect(alert.textContent).not.toMatch(/[\r\n\t]/);
    expect(alert).toHaveTextContent(/server fault/i);
  });

  test("M2-6.C audit sécu — l'erreur tronque les messages > 200 caractères", () => {
    const longMsg = 'A'.repeat(300);
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      error: { code: 'INTERNAL', message: longMsg },
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    const alert = screen.getByRole('alert');
    // 200 'A' + ellipse Unicode + autres copies de la barre (titre fixe).
    expect(alert.textContent).toMatch(/A{200}…/);
    expect(alert.textContent).not.toMatch(/A{201}/);
  });

  test('M2-6.C.2 — tuile « Sans responsable » reste non-cliquable si count = 0 (anti-bruit)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 0, // pas d'item sans owner → tuile inerte
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // Aucune tuile cliquable dans cet état.
    expect(screen.queryByTestId('stat-tile-clickable')).toBeNull();
  });

  test('hides the breakdown when no P0/P1 are unassigned (anti-bruit)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 5, // que des P2/P3 sans pilote
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // Aucune sous-ligne breakdown rendue.
    expect(screen.queryAllByTestId('stat-tile-breakdown')).toHaveLength(0);
  });

  test('returns null silently when data is missing without loading or error', () => {
    // Cas défensif : si jamais le hook renvoie data=null sans loading/error.
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    const { container } = render(<NarrativeBar />);
    // Aucun rendu — pas de tuile, pas de placeholder, pas d'alerte.
    expect(container.firstChild).toBeNull();
  });

  // ── M2-6.B.frontend — sum € compact sous tuile Décisions P0/P1 (Q16) ──

  test('renders the P0/P1 sum € (compact) under Décisions tile from backend agg', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 1,
        count_p1: 3,
        count_without_owner: 0,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
        // M2-6.B.backend agrégat — source unique CFO (jamais recalculé FE).
        sums_eur_by_priority: { P0: 3200, P1: 44300, P2: 35000, P3: 1800 },
        sums_eur_total: 84300,
        items_with_impact_known: 4,
        items_total: 9,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // 3200 + 44300 = 47500 → format compact "47,5 k€" (Q16 NarrativeBar compact).
    const sumNode = screen.getByTestId('stat-tile-sum-eur');
    expect(sumNode).toBeInTheDocument();
    expect(sumNode.textContent).toMatch(/47,5\s?k€/);
  });

  test('hides the sum € sub-line when both P0+P1 = 0 (anti-bruit §6.6)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 0,
        count_p1: 0,
        count_without_owner: 5,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
        sums_eur_by_priority: { P0: 0, P1: 0 },
        sums_eur_total: 0,
        items_with_impact_known: 0,
        items_total: 5,
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    // Aucune sous-ligne sum € (pas '0 €' parasite — Q16).
    expect(screen.queryByTestId('stat-tile-sum-eur')).toBeNull();
  });

  test('hides the sum € sub-line when sums_eur_by_priority is undefined (rétro-compat pré-M2-6.B.backend)', () => {
    // Garde rétro-compat : si le backend ne renvoie pas encore les champs CFO
    // (mocks anciens, ou env sans la migration), la tuile décisions ne casse pas.
    useActionCenterV4Summary.mockReturnValue({
      data: {
        count_p0: 1,
        count_p1: 2,
        count_without_owner: 0,
        count_p0_without_owner: 0,
        count_p1_without_owner: 0,
        count_at_risk: 0,
        count_secured: 0,
        // sums_eur_by_priority absent volontairement
      },
      loading: false,
      error: null,
      refetch: vi.fn(),
    });
    render(<NarrativeBar />);
    expect(screen.queryByTestId('stat-tile-sum-eur')).toBeNull();
  });
});
