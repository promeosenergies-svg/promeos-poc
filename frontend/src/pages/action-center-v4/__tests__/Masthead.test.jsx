// @vitest-environment jsdom
/**
 * M2-5.10.A.bis — Tests du composant Masthead (maquette §8.3 lignes 703-707).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { Masthead } from '../components/Masthead';

afterEach(cleanup);

describe('Masthead', () => {
  test('renders the title and subtitle', () => {
    render(<Masthead total={0} />);
    expect(screen.getByText("Centre d'action")).toBeInTheDocument();
    expect(screen.getByText(/référentiel complet/i)).toBeInTheDocument();
  });

  test('injects the items count when total > 0 (audit UI Sol P0-2)', () => {
    render(<Masthead total={9} />);
    expect(screen.getByText('9 items')).toBeInTheDocument();
  });

  test('singularises the items count when total = 1', () => {
    render(<Masthead total={1} />);
    expect(screen.getByText('1 item')).toBeInTheDocument();
  });

  test('hides the items count when total = 0', () => {
    render(<Masthead total={0} />);
    expect(screen.queryByText(/\d+ items?/)).not.toBeInTheDocument();
  });

  test('renders the « MAJ live » tag', () => {
    render(<Masthead total={1} liveDate="lundi 1 janvier 2026" />);
    expect(screen.getByText(/MAJ live/)).toBeInTheDocument();
    expect(screen.getByText(/lundi 1 janvier 2026/i)).toBeInTheDocument();
  });

  test('derives the current date when liveDate is not provided', () => {
    render(<Masthead total={1} />);
    // Pattern FR : « jour Xnumber month year ». Test souple : on vérifie
    // juste que la date a été rendue (n'importe quelle date courante).
    expect(screen.getByText(/\d{4}/)).toBeInTheDocument();
  });
});
