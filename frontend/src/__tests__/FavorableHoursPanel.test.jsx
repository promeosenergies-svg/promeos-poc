// @vitest-environment jsdom
/**
 * PROMEOS — Tests FavorableHoursPanel (Sprint P1.S6).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import FavorableHoursPanel from '../ui/energy/FavorableHoursPanel';

const PROV = {
  source: 'PROMEOS energy_orchestration',
  service: 'market_exposure._compute_favorable_hours',
};

const HOURS = [
  {
    timestamp: '2026-03-02T03:00:00+01:00',
    spot_price_eur_mwh: 12.5,
    kwh: 14.0,
    reason: 'prix bas',
    provenance: PROV,
  },
  {
    timestamp: '2026-03-15T13:00:00+01:00',
    spot_price_eur_mwh: -5.0,
    kwh: 22.0,
    reason: 'prix négatif',
    provenance: PROV,
  },
  {
    timestamp: '2026-04-10T13:00:00+02:00',
    spot_price_eur_mwh: 8.0,
    kwh: 30.0,
    reason: 'heure solaire',
    provenance: PROV,
  },
];

afterEach(() => cleanup());

describe('FavorableHoursPanel', () => {
  it('rend les 3 groupes catégorisés backend', () => {
    render(<FavorableHoursPanel favorableHours={HOURS} />);
    expect(screen.getByTestId('favorable-group-prix-bas')).toBeTruthy();
    expect(screen.getByTestId('favorable-group-prix-négatif')).toBeTruthy();
    expect(screen.getByTestId('favorable-group-heure-solaire')).toBeTruthy();
  });

  it('chaque heure exposée via data-reason', () => {
    render(<FavorableHoursPanel favorableHours={HOURS} />);
    const rows = document.querySelectorAll('[data-reason]');
    expect(rows.length).toBe(3);
    const reasons = Array.from(rows).map((r) => r.getAttribute('data-reason'));
    expect(reasons).toContain('prix bas');
    expect(reasons).toContain('prix négatif');
    expect(reasons).toContain('heure solaire');
  });

  it('retourne null si pas de données', () => {
    const { container } = render(<FavorableHoursPanel favorableHours={[]} />);
    expect(container.textContent).toBe('');
  });

  it('groupe vide masqué', () => {
    const onlyBas = HOURS.filter((h) => h.reason === 'prix bas');
    render(<FavorableHoursPanel favorableHours={onlyBas} />);
    expect(screen.getByTestId('favorable-group-prix-bas')).toBeTruthy();
    expect(screen.queryByTestId('favorable-group-prix-négatif')).toBeNull();
    expect(screen.queryByTestId('favorable-group-heure-solaire')).toBeNull();
  });
});

describe('FavorableHoursPanel — doctrine zéro calcul métier', () => {
  it('ne contient pas de détection prix négatif ni de tri solaire FE', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/FavorableHoursPanel.jsx'), 'utf8');
    // Pas de détection prix négatif FE
    expect(src).not.toMatch(/spot_price_eur_mwh\s*<\s*0/);
    // Pas de détection solaire FE (heure du jour, mois, etc.)
    expect(src).not.toMatch(/getMonth\s*\(\s*\)/);
    expect(src).not.toMatch(/getHours\s*\(\s*\)\s*[<>=]/);
  });
});
