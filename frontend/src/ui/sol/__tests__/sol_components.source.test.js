/**
 * PROMEOS — Sol components source guards.
 *
 * Pattern PROMEOS : readFileSync + regex, pas de DOM rendering.
 * Vérifie l'invariance des composants Sol (tokens CSS, voix éditoriale,
 * absence de hex hardcodés sauf #FFFFFF).
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const SOL_DIR = join(process.cwd(), 'src', 'ui', 'sol');
const readSol = (f) => readFileSync(join(SOL_DIR, f), 'utf8');

const SOL_FILES = [
  'SolPageHeader.jsx',
  'SolKpiCard.jsx',
  'SolHero.jsx',
  'SolWeekCard.jsx',
  'SolSourceChip.jsx',
  'SolSectionHead.jsx',
  'SolLoadCurve.jsx',
  'SolTimerail.jsx',
];

// Shades derivatives tokens autorisés (SVG gradient stopColor qui n'accepte pas
// les CSS vars de manière fiable, + hover shades dérivés de calme-fg).
const ALLOWED_HEX = new Set([
  '#FFFFFF',  // white
  '#0F172A',  // slate-900 = var(--sol-ink-900) ; SVG gradients natifs
  '#245047',  // calme-fg hover shade (approx. -10% luminosité)
]);

describe('Sol components — token discipline', () => {
  SOL_FILES.forEach((f) => {
    it(`${f} uses only CSS vars sol-* or whitelisted hex`, () => {
      const src = readSol(f);
      const hexes = src.match(/#[0-9A-Fa-f]{6}/g) || [];
      const forbidden = hexes.filter((h) => !ALLOWED_HEX.has(h.toUpperCase()));
      expect(forbidden).toEqual([]);
    });

    it(`${f} uses font vars (Fraunces/DM Sans/JetBrains Mono) via --sol-font-*`, () => {
      const src = readSol(f);
      if (src.includes('fontFamily')) {
        // Accepte var CSS ou stack générique
        expect(src).toMatch(/var\(--sol-font|font-family:|'serif'|'monospace'|'sans-serif'/);
      }
    });
  });
});

describe('SolPageHeader', () => {
  const src = readSol('SolPageHeader.jsx');

  it('uses sol-page-kicker, sol-page-title, sol-headline, sol-subline classes', () => {
    expect(src).toContain('sol-page-kicker');
    expect(src).toContain('sol-page-title');
    expect(src).toContain('sol-headline');
    expect(src).toContain('sol-subline');
  });

  it('accepts kicker + title + titleEm + narrative + subNarrative + rightSlot props', () => {
    for (const prop of ['kicker', 'title', 'titleEm', 'narrative', 'subNarrative', 'rightSlot']) {
      expect(src).toContain(prop);
    }
  });
});

describe('SolKpiCard', () => {
  const src = readSol('SolKpiCard.jsx');

  it('renders value with tabular-nums + JetBrains Mono', () => {
    expect(src).toMatch(/fontVariantNumeric:\s*'tabular-nums'/);
    expect(src).toMatch(/var\(--sol-font-mono\)/);
  });

  it('label uppercase tracking wide', () => {
    expect(src).toMatch(/textTransform:\s*'uppercase'/);
    expect(src).toMatch(/letterSpacing:\s*'0\.1em'/);
  });

  it('delta colored by direction (up=afaire, down=succes)', () => {
    expect(src).toMatch(/sol-succes-fg/);
    expect(src).toMatch(/sol-afaire-fg/);
  });

  it('delegates source chip to SolSourceChip component', () => {
    expect(src).toContain('SolSourceChip');
  });
});

describe('SolHero', () => {
  const src = readSol('SolHero.jsx');

  it('has border-left 3px calme signature', () => {
    expect(src).toMatch(/borderLeft.*var\(--sol-calme-fg\)/);
  });

  it('chip includes pulse animation', () => {
    expect(src).toMatch(/sol-pulse/);
  });

  it('default primary label is "Voir ce que j\'enverrai" (voice guide)', () => {
    expect(src).toContain("Voir ce que j'enverrai");
  });

  it('default secondary label is "Plus tard" (voice guide)', () => {
    expect(src).toContain('Plus tard');
  });
});

describe('SolWeekCard', () => {
  const src = readSol('SolWeekCard.jsx');

  it('supports 3 tag kinds : attention / afaire / succes', () => {
    expect(src).toMatch(/attention.*sol-attention-fg/s);
    expect(src).toMatch(/afaire.*sol-afaire-fg/s);
    expect(src).toMatch(/succes.*sol-succes-fg/s);
  });

  it('accessible via role=button + keyboard when clickable', () => {
    expect(src).toMatch(/role={onClick/);
    expect(src).toMatch(/onKeyDown/);
  });
});

describe('SolSourceChip', () => {
  const src = readSol('SolSourceChip.jsx');

  it('starts with "Source"', () => {
    expect(src).toContain("['Source']");
  });

  it('uppercase + mono + tiny', () => {
    expect(src).toMatch(/textTransform:\s*'uppercase'/);
    expect(src).toMatch(/fontFamily:\s*'var\(--sol-font-mono\)'/);
  });
});

describe('SolLoadCurve', () => {
  const src = readSol('SolLoadCurve.jsx');

  it('uses Recharts AreaChart with ReferenceArea HP/HC bands', () => {
    expect(src).toContain('AreaChart');
    expect(src).toContain('ReferenceArea');
  });

  it('uses sol-hph-bg and sol-hch-bg for tariff bands', () => {
    expect(src).toContain('sol-hph-bg');
    expect(src).toContain('sol-hch-bg');
  });

  it('has gradient fill id solLoadCurveFill', () => {
    expect(src).toContain('solLoadCurveFill');
  });

  it('ReferenceDot peak point uses calme-fg emerald', () => {
    expect(src).toContain('ReferenceDot');
    expect(src).toMatch(/var\(--sol-calme-fg\)/);
  });
});

describe('SolTimerail', () => {
  const src = readSol('SolTimerail.jsx');

  it('is position fixed bottom', () => {
    expect(src).toMatch(/position:\s*'fixed'/);
    expect(src).toMatch(/bottom:\s*0/);
  });

  it('height 36px matches maquette', () => {
    expect(src).toMatch(/height:\s*36/);
  });

  it('uses useCurrentTime with 60s default', () => {
    expect(src).toContain('useCurrentTime');
    expect(src).toMatch(/intervalSec\s*=\s*60/);
  });

  it('detects HP/HC slot by hour', () => {
    expect(src).toContain('detectTariffSlot');
    expect(src).toMatch(/h >= 6 && h < 22/);
  });
});

describe('Sol index barrel', () => {
  const src = readSol('index.js');

  it('exports all 8 components', () => {
    for (const comp of [
      'SolPageHeader',
      'SolKpiCard',
      'SolHero',
      'SolWeekCard',
      'SolSourceChip',
      'SolSectionHead',
      'SolLoadCurve',
      'SolTimerail',
    ]) {
      expect(src).toContain(comp);
    }
  });
});
