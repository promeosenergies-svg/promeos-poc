// @vitest-environment jsdom
/**
 * M2-5.2 — Tests du composant LifecycleBadge (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { LifecycleBadge } from '../components/items/LifecycleBadge';

// Pas de `globals: true` dans vite.config → l'auto-cleanup de RTL ne
// s'enregistre pas seul ; on le branche explicitement (anti-DOM accumulé).
afterEach(cleanup);

describe('LifecycleBadge', () => {
  test('renders "Nouveau" for the new state', () => {
    render(<LifecycleBadge state="new" />);
    expect(screen.getByText('Nouveau')).toBeInTheDocument();
  });

  test('renders "Clôturé" for the closed state', () => {
    render(<LifecycleBadge state="closed" />);
    expect(screen.getByText('Clôturé')).toBeInTheDocument();
  });

  test('falls back to the raw value for an unknown state', () => {
    render(<LifecycleBadge state="unknown_xyz" />);
    expect(screen.getByText('unknown_xyz')).toBeInTheDocument();
  });
});
