// @vitest-environment jsdom
/**
 * M2-5.3.A / M2-5.4 / M2-5.10.B — Tests du composant ItemHeader (rendu jsdom).
 *
 * Restyle Sol M2-5.10.B : ItemHeader est désormais le title block pur
 * (H1 Fraunces 25px + summary + status row + métadonnées). Le bouton
 * « Transitionner » est porté par DrawerActions (couvert par
 * `DrawerActions.test.jsx`).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { ItemHeader } from '../components/items/ItemHeader';

afterEach(cleanup);

describe('ItemHeader', () => {
  test('renders a skeleton while loading', () => {
    const { container } = render(<ItemHeader loading />);
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
  });

  test('renders an error message on error', () => {
    render(<ItemHeader error={{ message: 'fail' }} />);
    expect(screen.getByText(/impossible de charger/i)).toBeInTheDocument();
  });

  test('renders the title and the state badge', () => {
    render(
      <ItemHeader
        item={{
          title: 'Vérifier conso Q3',
          lifecycle_state: 'triaged',
          domain: 'optimisation',
        }}
      />
    );
    expect(screen.getByText('Vérifier conso Q3')).toBeInTheDocument();
    expect(screen.getByText('Trié')).toBeInTheDocument();
  });

  test('shows the description when present, hides it when null', () => {
    const { rerender } = render(
      <ItemHeader item={{ title: 'X', lifecycle_state: 'new', description: 'desc1' }} />
    );
    expect(screen.getByText('desc1')).toBeInTheDocument();

    rerender(<ItemHeader item={{ title: 'X', lifecycle_state: 'new', description: null }} />);
    expect(screen.queryByText('desc1')).not.toBeInTheDocument();
  });

  // ── M2-5.10.B — Sol status row (kind + priority + lifecycle + domain) ──
  test('renders the FR domain via DomainChip (M2-5.10.B Sol)', () => {
    render(
      <ItemHeader
        item={{ title: 'X', lifecycle_state: 'new', kind: 'anomaly', domain: 'conformite' }}
      />
    );
    // « Conformité » apparaît dans le DomainChip ET dans la dl métadonnées
    // (double rendu cardinal — chip header + label dl footer).
    expect(screen.getAllByText('Conformité').length).toBeGreaterThanOrEqual(1);
  });

  test('renders the kind badge with the FR label (Type : ...)', () => {
    render(
      <ItemHeader
        item={{ title: 'X', lifecycle_state: 'new', kind: 'anomaly', domain: 'conformite' }}
      />
    );
    // KindHeaderBadge rend « Type : Anomalie ».
    expect(screen.getByText(/type\s*:\s*anomalie/i)).toBeInTheDocument();
    // Le label brut backend n'est jamais visible (doctrine FR strict).
    expect(screen.queryByText('anomaly')).not.toBeInTheDocument();
    expect(screen.queryByText('conformite')).not.toBeInTheDocument();
  });

  test('falls back to "TYPE INCONNU" / "Domaine inconnu" for unknown values', () => {
    render(
      <ItemHeader item={{ title: 'X', lifecycle_state: 'new', kind: 'zzz', domain: 'yyy' }} />
    );
    // KindHeaderBadge unknown → coque neutre avec « TYPE INCONNU ».
    expect(screen.getByText('TYPE INCONNU')).toBeInTheDocument();
    // M2-5.10.B.bis — dl meta-grid dédupliquée (audit UI Sol P1-4) :
    // « Domaine inconnu » n'apparaît plus que via DomainChip (1 occurrence).
    expect(screen.getAllByText('Domaine inconnu').length).toBe(1);
  });

  test('meta-grid contains only Créé / MAJ (no kind/domain duplication)', () => {
    const { container } = render(
      <ItemHeader
        item={{ title: 'X', lifecycle_state: 'new', kind: 'anomaly', domain: 'conformite' }}
      />
    );
    // M2-5.10.B.bis — kind et domain sont dans le status row, plus dans la dl
    // (audit UI Sol P1-4 — duplication retirée).
    expect(container.querySelectorAll('dt').length).toBe(2);
  });
});
