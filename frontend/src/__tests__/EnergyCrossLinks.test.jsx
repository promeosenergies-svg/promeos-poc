// @vitest-environment jsdom
/**
 * PROMEOS — Tests EnergyCrossLinks (Sprint P1.S7 polish).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import EnergyCrossLinks from '../ui/energy/EnergyCrossLinks';

const LINKS = [
  { kind: 'bill', to: '/bill-intel', label: 'Comparer à la facture' },
  { kind: 'achat', to: '/achat-energie', label: 'Simuler une offre alternative' },
  { kind: 'action', to: '/action-center-v4', label: 'Créer une action' },
  { kind: 'conformite', to: '/conformite/tertiaire', label: 'Voir trajectoire' },
];

afterEach(() => cleanup());

describe('EnergyCrossLinks', () => {
  it('rend les liens fournis', () => {
    render(
      <MemoryRouter>
        <EnergyCrossLinks links={LINKS} />
      </MemoryRouter>
    );
    expect(screen.getByTestId('energy-cross-links')).toBeTruthy();
    expect(screen.getByTestId('cross-link-bill')).toBeTruthy();
    expect(screen.getByTestId('cross-link-achat')).toBeTruthy();
    expect(screen.getByTestId('cross-link-action')).toBeTruthy();
    expect(screen.getByTestId('cross-link-conformite')).toBeTruthy();
  });

  it('chaque link pointe vers la bonne route', () => {
    render(
      <MemoryRouter>
        <EnergyCrossLinks links={LINKS} />
      </MemoryRouter>
    );
    expect(screen.getByTestId('cross-link-bill').getAttribute('href')).toBe('/bill-intel');
    expect(screen.getByTestId('cross-link-achat').getAttribute('href')).toBe('/achat-energie');
    expect(screen.getByTestId('cross-link-action').getAttribute('href')).toBe('/action-center-v4');
  });

  it('affiche "Aller plus loin :"', () => {
    render(
      <MemoryRouter>
        <EnergyCrossLinks links={LINKS} />
      </MemoryRouter>
    );
    expect(screen.getByText(/Aller plus loin/i)).toBeTruthy();
  });

  it('retourne null si liste vide', () => {
    const { container } = render(
      <MemoryRouter>
        <EnergyCrossLinks links={[]} />
      </MemoryRouter>
    );
    expect(container.textContent).toBe('');
  });

  it('filtre les links sans `to` ou sans `label`', () => {
    const partial = [
      { kind: 'bill', to: '/bill-intel', label: 'OK' },
      { kind: 'achat', to: null, label: 'Sans to' },
      { kind: 'action', to: '/action-center-v4' },
    ];
    render(
      <MemoryRouter>
        <EnergyCrossLinks links={partial} />
      </MemoryRouter>
    );
    expect(screen.getByTestId('cross-link-bill')).toBeTruthy();
    expect(screen.queryByTestId('cross-link-achat')).toBeNull();
    expect(screen.queryByTestId('cross-link-action')).toBeNull();
  });
});

describe('EnergyCrossLinks — doctrine', () => {
  it("ne contient pas de promesse d'économie affirmative ni de chiffre €", () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/EnergyCrossLinks.jsx'), 'utf8');
    // Interdire les constructions AFFIRMATIVES uniquement (le commentaire
    // « Pas de promesse d'économie certaine » est de la doctrine, pas une
    // affirmation produit).
    expect(src).not.toMatch(/économisez\s+\w+/i);
    expect(src).not.toMatch(/économie\s+garantie/i);
    expect(src).not.toMatch(/gain\s+garanti/i);
    expect(src).not.toMatch(/réduction\s+certaine/i);
    // Pas de chiffres € en dur dans le composant
    expect(src).not.toMatch(/€\s*[0-9]/);
  });
});
