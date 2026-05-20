// @vitest-environment jsdom
/**
 * M2-5.10.A — Tests du composant KindCell (maquette §8.3 lignes 422-454).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { KindCell } from '../components/KindCell';

afterEach(cleanup);

describe('KindCell', () => {
  test.each([
    ['anomaly', 'ANOMALIE'],
    ['action', 'ACTION'],
    ['decision', 'DÉCISION'],
    ['signal', 'SIGNAL'],
    ['evidence_request', 'PREUVE'],
    ['deadline', 'ÉCHÉANCE'],
    ['recommendation', 'RECO'],
  ])('renders the upper FR label for kind %s', (kind, expectedLabel) => {
    render(<KindCell kind={kind} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  test('exposes the kind in a data attribute for CSS targeting', () => {
    const { container } = render(<KindCell kind="anomaly" />);
    expect(container.querySelector('[data-kind="anomaly"]')).toBeTruthy();
  });

  test('falls back to "TYPE INCONNU" + neutral icon shell for an unknown kind', () => {
    render(<KindCell kind="invented_xyz" />);
    expect(screen.getByText('TYPE INCONNU')).toBeInTheDocument();
  });

  test('the label exposes the mixed-case FR label as tooltip', () => {
    const { container } = render(<KindCell kind="recommendation" />);
    expect(container.querySelector('[title="Recommandation"]')).toBeTruthy();
  });
});
