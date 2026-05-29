// @vitest-environment jsdom
/**
 * PROMEOS — Tests KpiCardWithProvenance (Sprint P1.S3a UI Courbe de charge).
 *
 * Couvre : rendu valeur+unité, état dérivé, tooltip provenance, doctrine
 * « ne recalcule pas la valeur ».
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import KpiCardWithProvenance from '../ui/energy/KpiCardWithProvenance';

const baseProvenance = {
  source: 'PROMEOS energy_orchestration',
  service: 'energy_orchestration.synthesis.build_synthesis',
  formula: 'Σ MeterReading.value_kwh',
  period: '2026-04-01 → 2026-05-01',
  confidence: 0.85,
  assumptions: ['seuil 80 % couverture metered', 'energy_vector=ELECTRICITY'],
};

describe('KpiCardWithProvenance', () => {
  afterEach(() => cleanup());

  it('affiche la valeur et l’unité fournies sans recalcul', () => {
    render(
      <KpiCardWithProvenance
        label="Consommation"
        value={12450.7}
        unit="kWh"
        state="sain"
        provenance={baseProvenance}
      />
    );
    // Le séparateur des milliers en fr-FR est un NBSP étroit (U+202F) — on
    // teste sur les chiffres et la virgule décimale, sans dépendre du whitespace.
    const value = screen.getByTestId('kpi-value').textContent;
    expect(value).toMatch(/12\s?450,7/);
    expect(screen.getByTestId('kpi-unit').textContent).toBe('kWh');
  });

  it('valeur null → état inactif auto + placeholder —', () => {
    render(<KpiCardWithProvenance label="Coût" value={null} unit="€" />);
    const card = screen.getByTestId('kpi-card-with-provenance');
    expect(card.getAttribute('data-state')).toBe('inactif');
    expect(screen.getByTestId('kpi-value').textContent).toBe('—');
  });

  it('rend les 4 états (sain/vigilance/critique/inactif)', () => {
    for (const state of ['sain', 'vigilance', 'critique', 'inactif']) {
      const { unmount } = render(
        <KpiCardWithProvenance label="x" value={1} unit="kW" state={state} />
      );
      const card = screen.getByTestId('kpi-card-with-provenance');
      expect(card.getAttribute('data-state')).toBe(state);
      unmount();
    }
  });

  it('affiche le tooltip provenance avec source, service, formule', () => {
    render(<KpiCardWithProvenance label="x" value={1} unit="kWh" provenance={baseProvenance} />);
    const tooltip = screen.getByTestId('kpi-provenance-tooltip').textContent;
    expect(tooltip).toContain('PROMEOS energy_orchestration');
    expect(tooltip).toContain('build_synthesis');
    expect(tooltip).toContain('Σ MeterReading.value_kwh');
    expect(tooltip).toContain('85%');
  });

  it('tronque la liste d’assumptions à 4 entrées', () => {
    const many = { ...baseProvenance, assumptions: ['a', 'b', 'c', 'd', 'e', 'f'] };
    render(<KpiCardWithProvenance label="x" value={1} unit="kWh" provenance={many} />);
    const tooltip = screen.getByTestId('kpi-provenance-tooltip').textContent;
    expect(tooltip).toContain('+2 autres');
  });

  it('le fichier composant ne contient aucun calcul métier interdit', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/KpiCardWithProvenance.jsx'), 'utf8');
    expect(src).not.toMatch(/co2Factor\s*\*/);
    expect(src).not.toMatch(/Math\.sin\(/);
    expect(src).not.toMatch(/computeInsights\s*\(/);
    expect(src).not.toMatch(/\.reduce\s*\(\s*\([\w,\s]*\)\s*=>\s*\w+\s*\+\s*\(?\s*\w+\.estimated_/);
  });
});
