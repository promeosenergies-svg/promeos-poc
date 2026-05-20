// @vitest-environment jsdom
/**
 * M2-5.10.D — Tests de `PilotageTabs` (navigation Pilotage / Référentiel).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { PilotageTabs } from '../components/PilotageTabs';

afterEach(cleanup);

function mount(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <PilotageTabs />
    </MemoryRouter>
  );
}

describe('PilotageTabs', () => {
  test('renders both tabs as links', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /pilotage/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /référentiel/i })).toBeInTheDocument();
  });

  test('marks Pilotage active on /pilotage', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /pilotage/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /référentiel/i })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  test('marks Référentiel active on /action-center-v4', () => {
    mount('/action-center-v4');
    expect(screen.getByRole('tab', { name: /référentiel/i })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: /pilotage/i })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  test('exposes role=tablist with a French aria-label', () => {
    mount('/action-center-v4');
    expect(
      screen.getByRole('tablist', { name: /sections du centre d'action/i })
    ).toBeInTheDocument();
  });

  test('Pilotage tab href points to /action-center-v4/pilotage', () => {
    mount('/action-center-v4');
    expect(screen.getByRole('tab', { name: /pilotage/i })).toHaveAttribute(
      'href',
      '/action-center-v4/pilotage'
    );
  });

  test('Référentiel tab href points to /action-center-v4', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /référentiel/i })).toHaveAttribute(
      'href',
      '/action-center-v4'
    );
  });
});
