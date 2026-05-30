// @vitest-environment jsdom
/**
 * PROMEOS — Tests TopExpensiveHoursTable (Sprint P1.S6).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import TopExpensiveHoursTable from '../ui/energy/TopExpensiveHoursTable';

const PROV = {
  source: 'PROMEOS energy_orchestration',
  service: 'market_exposure._compute_top_expensive_hours',
  formula: 'Q90 via compute_quantiles',
};

const HOURS = [
  {
    timestamp: '2026-01-15T19:00:00+01:00',
    spot_price_eur_mwh: 420.5,
    kwh: 85.4,
    cost_eur: 35.91,
    rank: 1,
    recommended_action: 'Éviter démarrage cycle process intensif.',
    provenance: PROV,
  },
  {
    timestamp: '2026-02-08T08:00:00+01:00',
    spot_price_eur_mwh: 380.0,
    kwh: 72.1,
    cost_eur: 27.4,
    rank: 2,
    recommended_action: 'Décaler chauffage électrique vers 10h.',
    provenance: PROV,
  },
  {
    timestamp: '2026-01-22T18:00:00+01:00',
    spot_price_eur_mwh: 365.5,
    kwh: 68.0,
    cost_eur: 24.85,
    rank: 3,
    recommended_action: 'Surveiller pic récurrent (-1h).',
    provenance: PROV,
  },
];

afterEach(() => cleanup());

describe('TopExpensiveHoursTable', () => {
  it('rend les 3 lignes', () => {
    render(<TopExpensiveHoursTable topExpensiveHours={HOURS} />);
    expect(screen.getByTestId('top-hour-row-1')).toBeTruthy();
    expect(screen.getByTestId('top-hour-row-2')).toBeTruthy();
    expect(screen.getByTestId('top-hour-row-3')).toBeTruthy();
  });

  it('tri visuel par rank si fourni par API (ordre 1→3 préservé)', () => {
    // Backend renvoie potentiellement dans le désordre.
    const shuffled = [HOURS[2], HOURS[0], HOURS[1]];
    render(<TopExpensiveHoursTable topExpensiveHours={shuffled} />);
    const rows = document.querySelectorAll('[data-rank]');
    expect(rows[0].getAttribute('data-rank')).toBe('1');
    expect(rows[1].getAttribute('data-rank')).toBe('2');
    expect(rows[2].getAttribute('data-rank')).toBe('3');
  });

  it('affiche recommended_action backend (jamais générée FE)', () => {
    render(<TopExpensiveHoursTable topExpensiveHours={HOURS} />);
    expect(screen.getByText('Éviter démarrage cycle process intensif.')).toBeTruthy();
    expect(screen.getByText('Décaler chauffage électrique vers 10h.')).toBeTruthy();
  });

  it('affiche spot_price_eur_mwh et cost_eur depuis API', () => {
    render(<TopExpensiveHoursTable topExpensiveHours={HOURS} />);
    const row1 = screen.getByTestId('top-hour-row-1');
    expect(row1.textContent).toContain('420,5');
    expect(row1.textContent).toMatch(/35,?91|36/);
  });

  it('retourne null si pas de données', () => {
    const { container } = render(<TopExpensiveHoursTable topExpensiveHours={[]} />);
    expect(container.textContent).toBe('');
  });

  it('provenance par ligne exposée', () => {
    render(<TopExpensiveHoursTable topExpensiveHours={HOURS} />);
    expect(screen.getAllByTestId('top-hour-provenance').length).toBe(3);
  });
});

describe('TopExpensiveHoursTable — doctrine zéro calcul métier', () => {
  it('ne contient pas de calcul de cost ni de tri métier sans rank', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/TopExpensiveHoursTable.jsx'), 'utf8');
    // Pas de calcul cost_eur = kwh * price/1000
    expect(src).not.toMatch(/cost_eur\s*=\s*\w+\.kwh\s*\*/);
    // Pas de Q90/quantiles FE
    expect(src).not.toMatch(/quantile|percentile/i);
    // Pas de recommended_action générée FE
    expect(src).not.toMatch(/recommended_action\s*=\s*['"`]/);
  });
});
