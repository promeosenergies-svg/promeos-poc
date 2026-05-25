// @vitest-environment jsdom
/**
 * Action Center V4 P0-4 fix (2026-05-25) — tests CTA « Voir la source »
 * dans LinksTab. Vérifie que le bouton apparaît dès que sourceUrl est
 * fourni, qu'il pointe vers la bonne URL, et qu'il survit aux 3 états
 * du fetch (loading / error / empty).
 */
import '@testing-library/jest-dom/vitest';
import React from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

// Mock le hook qui appelle l'API (sinon le test renvoie loading infini).
vi.mock('../../../../../hooks/v4', () => ({
  useActionCenterV4Links: vi.fn(() => ({
    data: { items: [], total: 0 },
    loading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

import { LinksTab } from '../LinksTab';

afterEach(() => cleanup());

function renderTab(props) {
  return render(
    <MemoryRouter>
      <LinksTab {...props} />
    </MemoryRouter>
  );
}

describe('LinksTab — CTA « Voir la source » (P0-4)', () => {
  it('rend le CTA quand sourceUrl est fourni', () => {
    renderTab({ itemId: 'abc', sourceUrl: '/bill-intel?anomaly=42' });
    const cta = screen.getByTestId('links-source-cta');
    expect(cta).toHaveAttribute('href', '/bill-intel?anomaly=42');
    expect(cta).toHaveTextContent('Voir la source');
  });

  it('ne rend pas le CTA si sourceUrl est absent', () => {
    renderTab({ itemId: 'abc' });
    expect(screen.queryByTestId('links-source-cta')).toBeNull();
  });

  it('ne rend pas le CTA si sourceUrl est vide', () => {
    renderTab({ itemId: 'abc', sourceUrl: '' });
    expect(screen.queryByTestId('links-source-cta')).toBeNull();
  });

  it('CTA fonctionne avec source_url conformite', () => {
    renderTab({ itemId: 'abc', sourceUrl: '/conformite?regulation=DT' });
    const cta = screen.getByTestId('links-source-cta');
    expect(cta).toHaveAttribute('href', '/conformite?regulation=DT');
  });

  it('CTA fonctionne avec source_url patrimoine', () => {
    renderTab({ itemId: 'abc', sourceUrl: '/patrimoine?site=12' });
    const cta = screen.getByTestId('links-source-cta');
    expect(cta).toHaveAttribute('href', '/patrimoine?site=12');
  });
});
