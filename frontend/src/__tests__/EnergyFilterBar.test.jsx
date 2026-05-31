// @vitest-environment jsdom
/**
 * PROMEOS — Tests EnergyFilterBar (Sprint P1.S3a UI Courbe de charge).
 *
 * Couvre : rendu des 5 groupes, émission onChange, options conformes
 * au contrat API loadcurve, pas de calcul métier.
 */
import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import EnergyFilterBar, {
  GRANULARITY_OPTIONS,
  PERIOD_OPTIONS,
  COMPARE_OPTIONS,
  DISPLAY_OPTIONS,
} from '../ui/energy/EnergyFilterBar';

describe('EnergyFilterBar', () => {
  afterEach(() => cleanup());

  it('rend les 5 groupes (site / période / granularité / comparer / affichage)', () => {
    render(<EnergyFilterBar scope={{ kind: 'site', id: 42, label: 'HQ Paris' }} />);
    expect(screen.getByTestId('energy-filter-bar')).toBeTruthy();
    expect(screen.getByText('Site')).toBeTruthy();
    expect(screen.getByText('Période')).toBeTruthy();
    expect(screen.getByText('Granularité')).toBeTruthy();
    expect(screen.getByText('Comparer')).toBeTruthy();
    expect(screen.getByText('Affichage')).toBeTruthy();
  });

  it('affiche le label du scope sélectionné', () => {
    render(<EnergyFilterBar scope={{ kind: 'site', id: 42, label: 'HQ Paris' }} />);
    expect(screen.getByTestId('filter-scope-label').textContent).toContain('HQ Paris');
  });

  it('expose les granularités contrat API (15min, 30min, hour, day, month, year)', () => {
    expect(GRANULARITY_OPTIONS.map((o) => o.value)).toEqual([
      '15min',
      '30min',
      'hour',
      'day',
      'month',
      'year',
    ]);
  });

  it('expose les périodes 7d / 30d / 90d', () => {
    expect(PERIOD_OPTIONS.map((o) => o.value)).toEqual(['7d', '30d', '90d']);
  });

  it('expose compare none / n-1 / baseline conforme contrat', () => {
    expect(COMPARE_OPTIONS.map((o) => o.value)).toEqual(['none', 'n-1', 'baseline']);
  });

  it('expose display kwh / kw', () => {
    expect(DISPLAY_OPTIONS.map((o) => o.value)).toEqual(['kwh', 'kw']);
  });

  it('émet onChange avec patch period au clic', () => {
    const onChange = vi.fn();
    render(
      <EnergyFilterBar
        scope={{ kind: 'site', id: 1 }}
        period="30d"
        granularity="hour"
        compare="none"
        display="kwh"
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByText('7 jours'));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ period: '7d', granularity: 'hour' })
    );
  });

  it('émet onChange avec patch granularity au clic', () => {
    const onChange = vi.fn();
    render(
      <EnergyFilterBar
        scope={{ kind: 'site', id: 1 }}
        period="30d"
        granularity="hour"
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getByText('1 j'));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ granularity: 'day' }));
  });

  it('ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/EnergyFilterBar.jsx'), 'utf8');
    expect(src).not.toMatch(/co2Factor\s*\*/);
    expect(src).not.toMatch(/Math\.sin\(/);
    expect(src).not.toMatch(/computeInsights\s*\(/);
  });
});

describe('Hotfix Énergie 2026-05-31 — EnergyFilterBar rendu site sans fallback technique', () => {
  afterEach(() => cleanup());

  it('affiche le nom métier du site si fourni via scope.label', () => {
    render(
      <EnergyFilterBar
        scope={{ kind: 'site', id: 1, label: 'Siège HELIOS Paris' }}
        period="30d"
        granularity="hour"
        compare="none"
        display="kwh"
        onChange={() => {}}
      />
    );
    const label = screen.getByTestId('filter-scope-label');
    expect(label.textContent).toBe('Siège HELIOS Paris');
    expect(label.textContent).not.toMatch(/^Site Site/);
  });

  it('affiche « Sélectionner un site » si aucun id ni label', () => {
    render(
      <EnergyFilterBar
        scope={{}}
        period="30d"
        granularity="hour"
        compare="none"
        display="kwh"
        onChange={() => {}}
      />
    );
    expect(screen.getByTestId('filter-scope-label').textContent).toBe('Sélectionner un site');
  });

  it("affiche « Site sélectionné » si seul l'id est connu (fallback FR)", () => {
    render(
      <EnergyFilterBar
        scope={{ kind: 'site', id: 42 }}
        period="30d"
        granularity="hour"
        compare="none"
        display="kwh"
        onChange={() => {}}
      />
    );
    expect(screen.getByTestId('filter-scope-label').textContent).toBe('Site sélectionné');
  });

  it('ne contient JAMAIS la chaîne « Site # » dans le rendu', () => {
    render(
      <EnergyFilterBar
        scope={{ kind: 'site', id: 1 }}
        period="30d"
        granularity="hour"
        compare="none"
        display="kwh"
        onChange={() => {}}
      />
    );
    const label = screen.getByTestId('filter-scope-label');
    expect(label.textContent).not.toMatch(/Site #/);
    expect(label.textContent).not.toMatch(/#\d/);
    expect(label.textContent).not.toContain('#');
  });
});
