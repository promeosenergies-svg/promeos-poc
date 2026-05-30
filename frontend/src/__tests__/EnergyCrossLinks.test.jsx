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

describe('EnergyCrossLinks — Sprint P2.2 microcopy harmonisée', () => {
  const ALLOWED_LABELS = [
    'Créer une action',
    "Créer une action d'analyse",
    'Voir trajectoire Décret Tertiaire',
    'Voir données réglementaires',
    'Comparer à la facture',
    'Simuler une offre alternative',
  ];

  const VIEWS_WITH_CROSS_LINKS = [
    {
      file: '../pages/MonitoringPage.jsx',
      labels: ['Créer une action', 'Voir trajectoire Décret Tertiaire'],
    },
    {
      file: '../pages/consumption/LoadCurveTab.jsx',
      labels: ["Créer une action d'analyse"],
    },
    {
      file: '../pages/usages/WeekProfileTab.jsx',
      labels: ['Voir données réglementaires'],
    },
    {
      file: '../pages/consumption/CostContractTab.jsx',
      labels: ['Comparer à la facture', 'Simuler une offre alternative'],
    },
    {
      file: '../pages/consumption/MarketExposureTab.jsx',
      labels: ['Simuler une offre alternative', 'Créer une action'],
    },
  ];

  for (const view of VIEWS_WITH_CROSS_LINKS) {
    it(`${view.file.split('/').pop()} contient les labels canoniques attendus`, () => {
      const { readFileSync } = require('fs');
      const { resolve } = require('path');
      const src = readFileSync(resolve(__dirname, view.file), 'utf8');
      for (const lbl of view.labels) {
        expect(src).toContain(lbl);
        expect(ALLOWED_LABELS).toContain(lbl);
      }
    });
  }

  it("aucune vue n'utilise un label jargon (« Voir plus », anglais)", () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const FORBIDDEN_PATTERNS = [
      /label:\s*["']Voir plus["']/i,
      /label:\s*["']See more["']/i,
      /label:\s*["']Learn more["']/i,
      /label:\s*["']Click here["']/i,
      /label:\s*["']Économisez/i,
    ];
    for (const view of VIEWS_WITH_CROSS_LINKS) {
      const src = readFileSync(resolve(__dirname, view.file), 'utf8');
      for (const pattern of FORBIDDEN_PATTERNS) {
        expect(src).not.toMatch(pattern);
      }
    }
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
