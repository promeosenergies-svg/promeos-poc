// @vitest-environment jsdom
/**
 * M2-5.10.E — Tests de `PilotageViewToggle` (Décisions / Journal).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { PilotageViewToggle } from '../components/narrative/PilotageViewToggle';

afterEach(cleanup);

function mount(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <PilotageViewToggle />
    </MemoryRouter>
  );
}

describe('PilotageViewToggle', () => {
  test('renders both options as tabs', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /décisions/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /journal/i })).toBeInTheDocument();
  });

  test('marks Décisions active on /pilotage', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /décisions/i })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getByRole('tab', { name: /journal/i })).toHaveAttribute('aria-selected', 'false');
  });

  test('marks Journal active on /pilotage/journal', () => {
    mount('/action-center-v4/pilotage/journal');
    expect(screen.getByRole('tab', { name: /journal/i })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: /décisions/i })).toHaveAttribute(
      'aria-selected',
      'false'
    );
  });

  test('Décisions tab href points to /action-center-v4/pilotage', () => {
    mount('/action-center-v4/pilotage/journal');
    expect(screen.getByRole('tab', { name: /décisions/i })).toHaveAttribute(
      'href',
      '/action-center-v4/pilotage'
    );
  });

  test('Journal tab href points to /action-center-v4/pilotage/journal', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tab', { name: /journal/i })).toHaveAttribute(
      'href',
      '/action-center-v4/pilotage/journal'
    );
  });

  test('exposes a French aria-label on the tablist', () => {
    mount('/action-center-v4/pilotage');
    expect(screen.getByRole('tablist', { name: /vue pilotage/i })).toBeInTheDocument();
  });
});
