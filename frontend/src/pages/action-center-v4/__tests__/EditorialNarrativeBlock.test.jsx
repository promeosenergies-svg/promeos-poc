// @vitest-environment jsdom
/**
 * M2-6.B.frontend.bis — Tests EditorialNarrativeBlock complétude CFO.
 *
 * Pin le format cardinal Q19=C : « X actions sur Y portent un impact estimé : Z k€ »
 * avec grammaire FR singulier/pluriel + total compact + transparence 0/N.
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

vi.mock('../../../hooks/v4', () => ({
  useActionCenterV4Summary: vi.fn(),
}));

import { useActionCenterV4Summary } from '../../../hooks/v4';
import { EditorialNarrativeBlock } from '../components/EditorialNarrativeBlock';

const BASE_DATA = {
  count_p0: 1,
  count_p1: 3,
  count_without_owner: 3,
  count_p0_without_owner: 0,
  count_p1_without_owner: 0,
  count_at_risk: 1,
  count_secured: 1,
};

function mockSummary(overrides) {
  useActionCenterV4Summary.mockReturnValue({
    data: { ...BASE_DATA, ...overrides },
    loading: false,
    error: null,
    refetch: vi.fn(),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});
afterEach(cleanup);

describe('EditorialNarrativeBlock — complétude CFO Q19=C', () => {
  test('cas nominal HELIOS : 4 actions sur 9 portent un impact estimé : 47,5 k€', () => {
    mockSummary({
      items_with_impact_known: 4,
      items_total: 9,
      sums_eur_total: 47500,
    });
    render(<EditorialNarrativeBlock orgName="GROUPE HELIOS" sitesCount={5} />);

    const completude = screen.getByTestId('editorial-completude');
    // Concaténer le textContent pour matcher la phrase complète (les chiffres
    // sont dans des <span> séparés, le regex doit tolérer le NBSP éventuel).
    const txt = completude.textContent;
    expect(txt).toMatch(/4\s*actions sur\s*9\s*portent un impact estimé/i);

    // Total compact 47500 → "47,5 k€" (NBSP U+202F entre "5" et "k").
    const sumNode = screen.getByTestId('editorial-completude-sum');
    expect(sumNode.textContent).toMatch(/47,5\s?k€/);
  });

  test('singulier strict : 1 action sur 9 porte un impact estimé : 3 200 €', () => {
    mockSummary({
      items_with_impact_known: 1,
      items_total: 9,
      sums_eur_total: 3200,
    });
    render(<EditorialNarrativeBlock orgName="ORG" sitesCount={1} />);
    const txt = screen.getByTestId('editorial-completude').textContent;
    expect(txt).toMatch(/1\s*action sur\s*9\s*porte un impact estimé/i);
    expect(txt).not.toMatch(/actions sur/i);
    expect(txt).not.toMatch(/portent/i);
    // 3200 < 1000 ? non → compact actif → "3,2 k€" (formatEuros compact ≥1000)
    const sumNode = screen.getByTestId('editorial-completude-sum');
    expect(sumNode.textContent).toMatch(/3,2\s?k€/);
  });

  test('transparence 0/N : 0 action sur 9 porte un impact estimé : 0 €', () => {
    mockSummary({
      items_with_impact_known: 0,
      items_total: 9,
      sums_eur_total: 0,
    });
    render(<EditorialNarrativeBlock orgName="ORG" sitesCount={1} />);
    const txt = screen.getByTestId('editorial-completude').textContent;
    // 0 = singulier en FR strict (« 0 action » + « porte »).
    expect(txt).toMatch(/0\s*action sur\s*9\s*porte un impact estimé/i);
    expect(txt).not.toMatch(/actions sur/i);
    expect(txt).not.toMatch(/portent/i);
    // 0 = mesure valide → "0 €" (pas "—") — sémantique CFO money.js.
    const sumNode = screen.getByTestId('editorial-completude-sum');
    expect(sumNode.textContent).toMatch(/^0\s*€$/);
  });

  test('formatEuros compact appliqué sur sums_eur_total (100000 → 100 k€)', () => {
    mockSummary({
      items_with_impact_known: 7,
      items_total: 9,
      sums_eur_total: 100000,
    });
    render(<EditorialNarrativeBlock orgName="ORG" sitesCount={1} />);
    const sumNode = screen.getByTestId('editorial-completude-sum');
    // 100000 / 1000 = 100 (entier, pas de décimale).
    expect(sumNode.textContent).toMatch(/100\s?k€/);
    // Vérifier qu'on a bien le compact (pas le full "100 000 €").
    expect(sumNode.textContent).not.toMatch(/100[\s ]?000\s?€/);
  });

  test('ne rend rien quand le hook charge (skeleton compact)', () => {
    useActionCenterV4Summary.mockReturnValue({
      data: null,
      loading: true,
      error: null,
      refetch: vi.fn(),
    });
    render(<EditorialNarrativeBlock orgName="ORG" sitesCount={1} />);
    // En loading le composant rend EditorialSkeleton (aria-busy) — pas le testid completude.
    expect(screen.queryByTestId('editorial-completude')).toBeNull();
  });

  test('ne rend pas la ligne complétude si items_total absent (rétro-compat)', () => {
    mockSummary({
      // items_total volontairement absent — garde anti-régression pré-M2-6.B.backend
      items_with_impact_known: 4,
      sums_eur_total: 47500,
    });
    render(<EditorialNarrativeBlock orgName="ORG" sitesCount={1} />);
    expect(screen.queryByTestId('editorial-completude')).toBeNull();
  });
});
