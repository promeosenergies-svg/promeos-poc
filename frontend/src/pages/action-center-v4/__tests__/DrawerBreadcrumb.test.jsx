// @vitest-environment jsdom
/**
 * M2-6.C.3 (commit 4/4) — Tests DrawerBreadcrumb patrimonial.
 *
 * Couvre :
 * - Rendu segments présents (cas BE M3+ futur)
 * - Filtrage défensif segments manquants (pas de "undefined" parasite)
 * - Retour null si tous les champs absents (cas MV3 — BE actuel)
 * - Sémantique a11y (nav + aria-label)
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { DrawerBreadcrumb } from '../components/drawer/DrawerBreadcrumb';

afterEach(cleanup);

describe('DrawerBreadcrumb', () => {
  test('affiche tous les segments quand les 4 champs sont présents', () => {
    const item = {
      organisation_name: 'GROUPE HELIOS',
      site_name: 'Paris — Bureaux',
      building_name: 'Bâtiment A',
      meter_id: 'PRM-12345678',
    };
    render(<DrawerBreadcrumb item={item} />);
    expect(screen.getByText('GROUPE HELIOS')).toBeInTheDocument();
    expect(screen.getByText('Paris — Bureaux')).toBeInTheDocument();
    expect(screen.getByText('Bâtiment A')).toBeInTheDocument();
    expect(screen.getByText('PRM-12345678')).toBeInTheDocument();
    const segments = screen.getAllByTestId('drawer-breadcrumb-segment');
    expect(segments).toHaveLength(4);
  });

  test('filtre silencieusement les segments null/undefined (anti-bruit)', () => {
    const item = {
      organisation_name: 'GROUPE HELIOS',
      site_name: null,
      building_name: undefined,
      meter_id: 'PRM-99',
    };
    render(<DrawerBreadcrumb item={item} />);
    expect(screen.getByText('GROUPE HELIOS')).toBeInTheDocument();
    expect(screen.getByText('PRM-99')).toBeInTheDocument();
    expect(screen.queryByText(/undefined|null/)).not.toBeInTheDocument();
    const segments = screen.getAllByTestId('drawer-breadcrumb-segment');
    expect(segments).toHaveLength(2);
  });

  // M2-6.C.3 cardinal — cas MV3 où le BE n'expose pas encore les snapshots
  // patrimoniaux. Le composant retourne null silencieusement (conforme
  // doctrine §6.6 — pas de breadcrumb fantôme « — › — › — »).
  test('retourne null si aucun champ patrimonial (cas MV3 — BE actuel)', () => {
    const { container } = render(<DrawerBreadcrumb item={{}} />);
    expect(container.firstChild).toBeNull();
    expect(screen.queryByTestId('drawer-breadcrumb')).not.toBeInTheDocument();
  });

  test('retourne null si item est null/undefined', () => {
    const { container, rerender } = render(<DrawerBreadcrumb item={null} />);
    expect(container.firstChild).toBeNull();
    rerender(<DrawerBreadcrumb item={undefined} />);
    expect(container.firstChild).toBeNull();
  });

  test('expose une sémantique a11y nav + aria-label', () => {
    const item = { organisation_name: 'HELIOS', site_name: 'Paris' };
    render(<DrawerBreadcrumb item={item} />);
    const nav = screen.getByRole('navigation', { name: /chemin patrimoine/i });
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveAttribute('data-testid', 'drawer-breadcrumb');
  });

  test('le dernier segment est mis en emphase (font-semibold + ink-900)', () => {
    const item = { organisation_name: 'HELIOS', site_name: 'Paris' };
    render(<DrawerBreadcrumb item={item} />);
    const segments = screen.getAllByTestId('drawer-breadcrumb-segment');
    const last = segments[segments.length - 1];
    expect(last).toHaveClass('font-semibold');
    expect(last).toHaveStyle({ color: 'var(--sol-ink-900)' });
  });
});
