// @vitest-environment jsdom
/**
 * M2-5.8.B — Tests du composant PriorityBadge (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { PriorityBadge } from '../components/PriorityBadge';

afterEach(cleanup);

describe('PriorityBadge', () => {
  test.each([
    ['P0', 'Critique'],
    ['P1', 'Élevée'],
    ['P2', 'Standard'],
    ['P3', 'Faible'],
  ])('renders the FR label for %s', (bracket, expectedLabel) => {
    render(<PriorityBadge bracket={bracket} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  test('falls back to the raw bracket value when unknown', () => {
    render(<PriorityBadge bracket="unknown_xyz" />);
    expect(screen.getByText('unknown_xyz')).toBeInTheDocument();
  });

  test('renders nothing when bracket is null', () => {
    const { container } = render(<PriorityBadge bracket={null} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders nothing when bracket is undefined', () => {
    const { container } = render(<PriorityBadge bracket={undefined} />);
    expect(container.firstChild).toBeNull();
  });
});
