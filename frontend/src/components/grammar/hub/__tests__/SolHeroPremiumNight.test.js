/**
 * grammar/hub/SolHeroPremiumNight — source-guards Vitest (Sprint Grammaire v1.2)
 *
 * Tests pure-grep : contrat visuel hero bleu nuit + illustration filaire SVG.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../SolHeroPremiumNight.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/SolHeroPremiumNight', () => {
  it('data-component SolHeroPremiumNight + data-hero (L1 source-guard)', () => {
    const src = read();
    expect(src).toContain('data-component="SolHeroPremiumNight"');
    expect(src).toContain('data-hero');
  });

  it('gradient premium-night utilise tokens sol-night-bg et sol-night-bg-alt', () => {
    const src = read();
    expect(src).toContain('var(--sol-night-bg)');
    expect(src).toContain('var(--sol-night-bg-alt)');
    expect(src).toContain('linear-gradient');
  });

  it('illustration filaire SVG presente avec WireframeSvg ou SVG inline', () => {
    const src = read();
    expect(src).toMatch(/WireframeSvg|<svg/);
    expect(src).toContain('sol-night-line');
    expect(src).toContain('sol-night-dot');
  });

  it('dot anomalie sol-night-dot-hot present (8 buildings architecture)', () => {
    expect(read()).toContain('sol-night-dot-hot');
  });

  it('font display Fraunces via sol-font-display pour le titre', () => {
    expect(read()).toContain('var(--sol-font-display)');
  });

  it('pilule alertes rendue conditionnellement (alerts.count > 0)', () => {
    const src = read();
    expect(src).toMatch(/alerts\?\.count > 0|alerts\.count > 0/);
    expect(src).toContain('criticalCount');
  });

  it('bouton primaire blanc avec fleche SVG inline', () => {
    const src = read();
    expect(src).toContain('primaryCta');
    expect(src).toContain("background: 'white'");
  });

  it('meta footer avec quality / confidence / period / scope', () => {
    const src = read();
    expect(src).toContain('quality');
    expect(src).toContain('confidence');
    expect(src).toContain('period');
    expect(src).toContain('scope');
    expect(src).toContain('var(--sol-night-fg-meta)');
  });
});
