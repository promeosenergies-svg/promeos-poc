// @vitest-environment jsdom
/**
 * M2-5.10.A — Tests du composant DomainChip (maquette §8.3 lignes 507-521).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { DomainChip } from '../components/DomainChip';

afterEach(cleanup);

describe('DomainChip', () => {
  test.each([
    ['conformite', 'Conformité'],
    ['facturation', 'Facturation'],
    ['maintenance', 'Maintenance'],
    ['optimisation', 'Optimisation énergétique'],
    ['purchase', "Achat d'énergie"],
    ['flexibilite', 'Flexibilité'],
    ['data_quality', 'Qualité des données'],
  ])('renders the FR label for %s', (domain, expected) => {
    render(<DomainChip domain={domain} />);
    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  test('falls back to "Domaine inconnu" for an unknown domain', () => {
    render(<DomainChip domain="invented_xyz" />);
    expect(screen.getByText('Domaine inconnu')).toBeInTheDocument();
  });

  test('renders nothing when domain is null', () => {
    const { container } = render(<DomainChip domain={null} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders nothing when domain is undefined', () => {
    const { container } = render(<DomainChip domain={undefined} />);
    expect(container.firstChild).toBeNull();
  });
});
