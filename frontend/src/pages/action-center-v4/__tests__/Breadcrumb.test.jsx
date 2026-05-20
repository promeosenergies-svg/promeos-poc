// @vitest-environment jsdom
/**
 * M2-5.10.B.bis — Tests du Breadcrumb MONO Sol (maquette §8.4 lignes 678-682).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { Breadcrumb } from '../components/Breadcrumb';

afterEach(cleanup);

describe('Breadcrumb', () => {
  test("renders the default segments (PROMEOS › Centre d'action › Référentiel › Détail)", () => {
    render(<Breadcrumb />);
    expect(screen.getByText('PROMEOS')).toBeInTheDocument();
    expect(screen.getByText("Centre d'action")).toBeInTheDocument();
    expect(screen.getByText('Référentiel')).toBeInTheDocument();
    expect(screen.getByText('Détail')).toBeInTheDocument();
  });

  test('renders the strong segments as <b>', () => {
    const { container } = render(<Breadcrumb />);
    const bolds = container.querySelectorAll('b');
    // PROMEOS + Détail = 2 strong par défaut.
    expect(bolds.length).toBe(2);
  });

  test('renders a nav with aria-label', () => {
    render(<Breadcrumb />);
    expect(screen.getByRole('navigation', { name: /fil d'ariane/i })).toBeInTheDocument();
  });

  test('accepts a custom items array', () => {
    render(
      <Breadcrumb
        items={[{ label: 'A', strong: true }, { label: 'B' }, { label: 'C', strong: true }]}
      />
    );
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('B')).toBeInTheDocument();
    expect(screen.getByText('C')).toBeInTheDocument();
  });

  test('renders separators between segments (n-1 separators for n items)', () => {
    const { container } = render(<Breadcrumb />);
    const separators = container.querySelectorAll('[aria-hidden="true"]');
    expect(separators.length).toBe(3); // 4 segments → 3 separators
  });
});
