// @vitest-environment jsdom
/**
 * PROMEOS — Tests OffHoursSlotsTable (Sprint Énergie P3.2).
 */
import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import OffHoursSlotsTable from '../ui/energy/OffHoursSlotsTable';

const PROV = (service) => ({
  source: 'PROMEOS energy_orchestration',
  service,
  formula: 'rank desc kwh',
});

const SLOTS = [
  {
    day_of_week: 5,
    label: 'Samedi',
    hour: 14,
    kwh: 120.5,
    kw_avg: 120.5,
    status: 'critique',
    reason: 'Week-end fermé selon horaires déclarés',
    provenance: PROV('energy_orchestration.opening_hours_analysis._compute_slots'),
  },
  {
    day_of_week: 0,
    label: 'Lundi',
    hour: 22,
    kwh: 80.0,
    kw_avg: 80.0,
    status: 'vigilance',
    reason: "Hors plage d'ouverture déclarée",
    provenance: PROV('energy_orchestration.opening_hours_analysis._compute_slots'),
  },
];

afterEach(() => cleanup());

describe('OffHoursSlotsTable', () => {
  it('rend le titre métier « Top créneaux hors horaires »', () => {
    render(<OffHoursSlotsTable slots={SLOTS} />);
    expect(screen.getByText('Top créneaux hors horaires')).toBeTruthy();
  });

  it('rend une ligne par slot backend avec status et motif', () => {
    render(<OffHoursSlotsTable slots={SLOTS} />);
    expect(screen.getByTestId('off-hours-slot-row-0')).toBeTruthy();
    expect(screen.getByTestId('off-hours-slot-row-1')).toBeTruthy();
    const row0 = screen.getByTestId('off-hours-slot-row-0');
    expect(row0.textContent).toContain('Samedi');
    expect(row0.textContent).toContain('14h');
    expect(row0.textContent).toContain('Critique');
    expect(row0.textContent).toContain('Week-end fermé selon horaires déclarés');
    expect(row0.getAttribute('data-status')).toBe('critique');
  });

  it('propage les data-day pour chaque slot', () => {
    render(<OffHoursSlotsTable slots={SLOTS} />);
    expect(screen.getByTestId('off-hours-slot-row-0').getAttribute('data-day')).toBe('5');
    expect(screen.getByTestId('off-hours-slot-row-1').getAttribute('data-day')).toBe('0');
  });

  it('expose une provenance par slot', () => {
    render(<OffHoursSlotsTable slots={SLOTS} />);
    expect(screen.getAllByTestId('off-hours-slot-provenance').length).toBe(2);
  });

  it('rend loading state', () => {
    render(<OffHoursSlotsTable slots={null} loading />);
    expect(screen.getByTestId('off-hours-slots-loading')).toBeTruthy();
  });

  it('retourne null si slots vide', () => {
    const { container } = render(<OffHoursSlotsTable slots={[]} />);
    expect(container.textContent).toBe('');
  });
});

describe('OffHoursSlotsTable — doctrine zéro calcul métier', () => {
  it('ne contient aucun calcul de ranking / status / cost', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/OffHoursSlotsTable.jsx'), 'utf8');
    // Pas de ranking FE (Math.max sur kwh)
    expect(src).not.toMatch(/Math\.max\s*\(\s*\.{3}\s*\w+\.map\(\s*\(\s*\w+\s*\)\s*=>\s*\w+\.kwh/);
    // Pas de cost = kwh * price
    expect(src).not.toMatch(/cost\s*=\s*\w+\.kwh\s*\*/);
    // Pas de classification status FE
    expect(src).not.toMatch(/status\s*=\s*\(\s*\w+\s*[<>]/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
