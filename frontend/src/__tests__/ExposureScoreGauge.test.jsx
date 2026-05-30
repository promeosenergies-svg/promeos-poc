// @vitest-environment jsdom
/**
 * PROMEOS — Tests ExposureScoreGauge (Sprint P1.S6).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import ExposureScoreGauge from '../ui/energy/ExposureScoreGauge';

const PROV = {
  source: 'PROMEOS energy_orchestration',
  service: 'market_exposure._compute_exposure_score',
  formula: 'clamp_score_0_100(top10pct_share + neg_share*0.5)',
  period: '12 mois glissants',
  confidence: 0.78,
};

afterEach(() => cleanup());

describe('ExposureScoreGauge', () => {
  it('rend le score et le state propagé via data-state', () => {
    render(<ExposureScoreGauge score={42} state="vigilance" provenance={PROV} />);
    const gauge = screen.getByTestId('exposure-score-gauge');
    expect(gauge.getAttribute('data-state')).toBe('vigilance');
    expect(screen.getByTestId('exposure-score-value').textContent).toContain('42');
  });

  it('rend les 4 states canoniques', () => {
    const states = ['sain', 'vigilance', 'critique', 'inactif'];
    for (const s of states) {
      cleanup();
      render(<ExposureScoreGauge score={50} state={s} provenance={PROV} />);
      expect(screen.getByTestId('exposure-score-gauge').getAttribute('data-state')).toBe(s);
    }
  });

  it('état inactif par défaut si score null', () => {
    render(<ExposureScoreGauge score={null} provenance={PROV} />);
    expect(screen.getByTestId('exposure-score-gauge').getAttribute('data-state')).toBe('inactif');
    expect(screen.getByTestId('exposure-score-value').textContent).toContain('—');
  });

  it('provenance backend exposée', () => {
    render(<ExposureScoreGauge score={67} state="sain" provenance={PROV} />);
    expect(screen.getByTestId('exposure-score-provenance')).toBeTruthy();
  });

  it('label state affiché', () => {
    render(<ExposureScoreGauge score={80} state="critique" provenance={PROV} />);
    expect(screen.getByTestId('exposure-score-state-label').textContent).toContain('Critique');
  });
});

describe('ExposureScoreGauge — doctrine zéro calcul métier', () => {
  it('ne contient aucun recalcul du state ni du score', () => {
    const { readFileSync } = require('fs');
    const { resolve } = require('path');
    const src = readFileSync(resolve(__dirname, '../ui/energy/ExposureScoreGauge.jsx'), 'utf8');
    // Pas de calcul state = (score > X ? ...)
    expect(src).not.toMatch(/state\s*=\s*\(\s*\w+\s*[<>]/);
    // Pas de clamp manuel score
    expect(src).not.toMatch(/Math\.min\s*\(\s*100\s*,\s*Math\.max/);
    // Pas de CO₂
    expect(src).not.toMatch(/kwhToCo2|emission_factor/);
  });
});
