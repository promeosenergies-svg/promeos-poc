// @vitest-environment jsdom
/**
 * M2-5.8.B / M2-5.10.A — Tests du composant PriorityBadge (rendu jsdom).
 *
 * Format restylé Sol : tag plein `P0 · 92` (bracket + score visible).
 * Le label FR (Critique / Élevée / …) est conservé dans le `title=`
 * (tooltip natif) pour rester accessible aux lecteurs d'écran.
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
  ])('renders the bracket %s with the FR label as tooltip', (bracket, expectedLabel) => {
    const { container } = render(<PriorityBadge bracket={bracket} />);
    expect(screen.getByText(bracket)).toBeInTheDocument();
    expect(container.querySelector(`[title="${expectedLabel}"]`)).toBeTruthy();
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

  // ── M2-5.10.A — score visible (P0 · 92, maquette §8.3) ────────────
  test('renders the priority_score next to the bracket', () => {
    render(<PriorityBadge bracket="P0" score={92} />);
    expect(screen.getByText('P0')).toBeInTheDocument();
    expect(screen.getByText('92')).toBeInTheDocument();
  });

  test('rounds the score to an integer (no decimal noise)', () => {
    render(<PriorityBadge bracket="P1" score={73.6} />);
    expect(screen.getByText('74')).toBeInTheDocument();
  });

  test('hides the score when absent or invalid', () => {
    const { rerender, container } = render(<PriorityBadge bracket="P2" />);
    // Pas de séparateur · si pas de score.
    expect(container.querySelectorAll('span span').length).toBe(1);

    rerender(<PriorityBadge bracket="P2" score={NaN} />);
    expect(container.querySelectorAll('span span').length).toBe(1);

    rerender(<PriorityBadge bracket="P2" score={-1} />);
    expect(container.querySelectorAll('span span').length).toBe(1);

    rerender(<PriorityBadge bracket="P2" score={101} />);
    expect(container.querySelectorAll('span span').length).toBe(1);
  });
});
