// @vitest-environment jsdom
/**
 * Action Center V4 P0-2 fix (2026-05-25) — tests fallback drawer FR.
 *
 * Couvre les 3 variantes du composant ItemNotFoundState (not_found /
 * network_error / unexpected) + le câblage des CTAs (retry + retour hub).
 */
import '@testing-library/jest-dom/vitest';
import React from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';

import { ItemNotFoundState } from '../ItemNotFoundState';

afterEach(() => cleanup());

describe('ItemNotFoundState — 3 variantes FR (P0-2)', () => {
  it('variante par défaut « not_found » affiche le copy FR clair', () => {
    render(<ItemNotFoundState onClose={() => {}} />);
    const root = screen.getByTestId('drawer-item-not-found');
    expect(root).toHaveAttribute('data-variant', 'not_found');
    expect(root).toHaveTextContent("Cette action n'est plus disponible");
    expect(root).toHaveTextContent(/clôturée, supprimée ou déplacée/);
  });

  it('variante « network_error » affiche le copy réseau FR', () => {
    render(<ItemNotFoundState variant="network_error" onClose={() => {}} />);
    const root = screen.getByTestId('drawer-item-not-found');
    expect(root).toHaveAttribute('data-variant', 'network_error');
    expect(root).toHaveTextContent('Impossible de charger cette action');
    expect(root).toHaveTextContent(/erreur réseau/i);
  });

  it('variante « unexpected » affiche le copy générique FR', () => {
    render(<ItemNotFoundState variant="unexpected" onClose={() => {}} />);
    const root = screen.getByTestId('drawer-item-not-found');
    expect(root).toHaveAttribute('data-variant', 'unexpected');
    expect(root).toHaveTextContent('Erreur inattendue');
  });

  it("CTA « Retour au Centre d'Action » déclenche onClose", () => {
    const onClose = vi.fn();
    render(<ItemNotFoundState onClose={onClose} />);
    fireEvent.click(screen.getByTestId('drawer-item-not-found-cta'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('CTA « Réessayer » présent si onRetry fourni', () => {
    const onRetry = vi.fn();
    render(<ItemNotFoundState onClose={() => {}} onRetry={onRetry} />);
    const retry = screen.getByTestId('drawer-item-not-found-retry');
    fireEvent.click(retry);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('aucun retry button si onRetry absent (état unexpected)', () => {
    render(<ItemNotFoundState variant="unexpected" onClose={() => {}} />);
    expect(screen.queryByTestId('drawer-item-not-found-retry')).toBeNull();
  });

  it('role="alert" exposé pour assistive tech', () => {
    render(<ItemNotFoundState onClose={() => {}} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
