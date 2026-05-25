// @vitest-environment jsdom
/**
 * PROMEOS — Bill Intelligence P2-B C1 (2026-05-24) :
 * `ListFilterBar` expose un dropdown Domaine permettant de filtrer
 * les items par `Facturation`, `Conformité`, etc.
 *
 * Doctrine : sans nouveau menu — extension du FilterBar V4 existant.
 * Rétro-compat stricte : si `onDomainFilterChange` absent, dropdown caché
 * (comportement pré-P2-B inchangé).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, it, expect, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { ListFilterBar } from '../components/narrative/ListFilterBar';

afterEach(() => cleanup());

describe('ListFilterBar — filtre Domaine (P2-B C1)', () => {
  it('rend le dropdown Domaine si onDomainFilterChange est fourni', () => {
    const onDomainFilterChange = vi.fn();
    render(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={() => {}}
        kindFilter={null}
        onKindFilterChange={() => {}}
        domainFilter={null}
        onDomainFilterChange={onDomainFilterChange}
        onReset={() => {}}
      />
    );
    expect(screen.getByLabelText('Filtrer par domaine')).toBeInTheDocument();
    // Doit afficher Facturation dans les options
    expect(screen.getByRole('option', { name: 'Facturation' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Conformité' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Tous les domaines' })).toBeInTheDocument();
  });

  it('appelle onDomainFilterChange("facturation") quand l\'utilisateur sélectionne Facturation', () => {
    const onDomainFilterChange = vi.fn();
    render(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={() => {}}
        kindFilter={null}
        onKindFilterChange={() => {}}
        domainFilter={null}
        onDomainFilterChange={onDomainFilterChange}
        onReset={() => {}}
      />
    );
    const select = screen.getByLabelText('Filtrer par domaine');
    fireEvent.change(select, { target: { value: 'facturation' } });
    expect(onDomainFilterChange).toHaveBeenCalledWith('facturation');
  });

  it("appelle onDomainFilterChange(null) quand l'utilisateur sélectionne 'Tous les domaines'", () => {
    const onDomainFilterChange = vi.fn();
    render(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={() => {}}
        kindFilter={null}
        onKindFilterChange={() => {}}
        domainFilter="facturation"
        onDomainFilterChange={onDomainFilterChange}
        onReset={() => {}}
      />
    );
    const select = screen.getByLabelText('Filtrer par domaine');
    fireEvent.change(select, { target: { value: '' } });
    expect(onDomainFilterChange).toHaveBeenCalledWith(null);
  });

  it('CACHE le dropdown Domaine si onDomainFilterChange est absent (rétro-compat pré-P2-B)', () => {
    render(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={() => {}}
        kindFilter={null}
        onKindFilterChange={() => {}}
        onReset={() => {}}
      />
    );
    expect(screen.queryByLabelText('Filtrer par domaine')).not.toBeInTheDocument();
  });

  it('bouton Réinitialiser apparaît quand domainFilter actif', () => {
    const onReset = vi.fn();
    render(
      <ListFilterBar
        stateFilter={null}
        onStateFilterChange={() => {}}
        kindFilter={null}
        onKindFilterChange={() => {}}
        domainFilter="facturation"
        onDomainFilterChange={() => {}}
        onReset={onReset}
      />
    );
    // Le label exact dépend de SOL_COPY.filterReset — on cherche le bouton avec aria-label de reset
    const resetButton = screen.getByRole('button', { name: /réinitialis/i });
    expect(resetButton).toBeInTheDocument();
    fireEvent.click(resetButton);
    expect(onReset).toHaveBeenCalled();
  });
});
