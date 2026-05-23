// @vitest-environment jsdom
/**
 * M2-5.3.B — Tests du composant LinkItem (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { LinkItem } from '../components/drawer/LinkItem';

afterEach(cleanup);

describe('LinkItem', () => {
  test('renders action_center_item without the disabled style', () => {
    const { container } = render(
      <LinkItem
        link={{
          id: '1',
          target_module: 'action_center_item',
          target_id: 'abc-123',
          relation: 'duplicate_of',
        }}
      />
    );
    expect(screen.getByText('Action')).toBeInTheDocument();
    expect(container.querySelector('.opacity-60')).toBeNull();
  });

  test('renders site with the disabled style', () => {
    const { container } = render(
      <LinkItem link={{ id: '1', target_module: 'site', target_id: 'site-xyz' }} />
    );
    expect(screen.getByText('Site')).toBeInTheDocument();
    expect(container.querySelector('.opacity-60')).toBeTruthy();
  });

  test.each([
    ['building', 'Bâtiment'],
    ['meter', 'Compteur'],
    ['invoice', 'Facture'],
    ['contract', 'Contrat'],
    ['regulatory_obligation', 'Obligation réglementaire'],
  ])('renders %s disabled with the FR label %s', (module, label) => {
    const { container } = render(
      <LinkItem link={{ id: '1', target_module: module, target_id: 'xyz' }} />
    );
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.querySelector('.opacity-60')).toBeTruthy();
  });

  test('renders the target_id', () => {
    render(
      <LinkItem
        link={{
          id: '1',
          target_module: 'action_center_item',
          target_id: 'uuid-abc-123',
        }}
      />
    );
    expect(screen.getByText('uuid-abc-123')).toBeInTheDocument();
  });

  test('renders the relation when present', () => {
    render(
      <LinkItem
        link={{
          id: '1',
          target_module: 'action_center_item',
          target_id: 'x',
          relation: 'duplicate_of',
        }}
      />
    );
    expect(screen.getByText(/duplicate_of/)).toBeInTheDocument();
  });

  test('falls back to the raw target_module for unknown values', () => {
    render(<LinkItem link={{ id: '1', target_module: 'unknown_xyz', target_id: 'x' }} />);
    expect(screen.getByText('unknown_xyz')).toBeInTheDocument();
  });
});
