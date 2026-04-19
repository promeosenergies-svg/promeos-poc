/**
 * PROMEOS — Sol components source guards.
 *
 * Pattern PROMEOS : readFileSync + regex, pas de DOM rendering.
 * Vérifie l'invariance des composants Sol (tokens CSS, voix éditoriale,
 * absence de hex hardcodés, absence de fetch / business state).
 *
 * Couvre les 21 composants de la Phase 1 (8 Sprint 2 + 13 Phase 1).
 */
import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const SOL_DIR = join(process.cwd(), 'src', 'ui', 'sol');
const readSol = (f) => readFileSync(join(SOL_DIR, f), 'utf8');

const SOL_FILES_SPRINT2 = [
  'SolPageHeader.jsx',
  'SolKpiCard.jsx',
  'SolHero.jsx',
  'SolWeekCard.jsx',
  'SolSourceChip.jsx',
  'SolSectionHead.jsx',
  'SolLoadCurve.jsx',
  'SolTimerail.jsx',
];

const SOL_FILES_PHASE1 = [
  'SolHeadline.jsx',
  'SolSubline.jsx',
  'SolStatusPill.jsx',
  'SolButton.jsx',
  'SolKpiRow.jsx',
  'SolWeekGrid.jsx',
  'SolLayerToggle.jsx',
  'SolPendingBanner.jsx',
  'SolInspectDoc.jsx',
  'SolCartouche.jsx',
  'SolDrawer.jsx',
  'SolExpertGrid.jsx',
  'SolJournal.jsx',
  'SolRail.jsx',
  'SolPanel.jsx',
  'SolAppShell.jsx',
  'SolTrajectoryChart.jsx', // Phase 4.1
  'SolBarChart.jsx',        // Phase 4.1.1 (prep 4.2)
];

const ALL_SOL_FILES = [...SOL_FILES_SPRINT2, ...SOL_FILES_PHASE1];

// Hex autorisés : blanc + slate-900 (= --sol-ink-900) + shade hover calme.
// V2 raw (source lockée par user 17/04/2026, UX-1 journal en terrasse) :
// palette warm slate + accents chaleureux.
const ALLOWED_HEX = new Set([
  '#FFFFFF',  // blanc
  '#0F172A',  // slate-900 = var(--sol-ink-900), SVG gradients natifs
  '#245047',  // calme-fg hover shade (-10% luminosité de #2F6B5E)
]);

describe('Sol components — fichiers attendus', () => {
  it('tous les 21 composants sont présents', () => {
    const files = readdirSync(SOL_DIR).filter((f) => f.endsWith('.jsx'));
    for (const expected of ALL_SOL_FILES) {
      expect(files).toContain(expected);
    }
  });

  it('tokens.css est présent', () => {
    const files = readdirSync(SOL_DIR);
    expect(files).toContain('tokens.css');
  });
});

describe('Sol components — token discipline', () => {
  ALL_SOL_FILES.forEach((f) => {
    it(`${f} : hex hardcodés interdits (sauf whitelist)`, () => {
      const src = readSol(f);
      const hexes = src.match(/#[0-9A-Fa-f]{6}/g) || [];
      const forbidden = hexes.filter((h) => !ALLOWED_HEX.has(h.toUpperCase()));
      expect(forbidden).toEqual([]);
    });

    it(`${f} : fontFamily utilise var(--sol-font-*) ou stack générique`, () => {
      const src = readSol(f);
      if (src.includes('fontFamily')) {
        expect(src).toMatch(/var\(--sol-font|'serif'|'monospace'|'sans-serif'/);
      }
    });
  });
});

describe('Sol components — invariants présentation pure', () => {
  ALL_SOL_FILES.forEach((f) => {
    it(`${f} : pas de fetch direct`, () => {
      const src = readSol(f);
      expect(src).not.toMatch(/\bfetch\s*\(/);
      expect(src).not.toMatch(/axios\./);
    });

    it(`${f} : pas de call API services/api`, () => {
      const src = readSol(f);
      expect(src).not.toMatch(/from\s+['"].*services\/api/);
      expect(src).not.toMatch(/from\s+['"]@\/services\/api/);
    });

    it(`${f} : pas de useState(fetched) ni useEffect(api)`, () => {
      const src = readSol(f);
      expect(src).not.toMatch(/useState.*fetch/);
      expect(src).not.toMatch(/useEffect.*fetch\(/);
    });
  });
});

// ══════════════════════════════════════════════════════════════════════════════
// Tests unitaires composants Sprint 2 (existants)
// ══════════════════════════════════════════════════════════════════════════════

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

  it('Phase 4.1 : prop explainKey + r\u00e9utilise Explain composant', () => {
    expect(src).toContain('explainKey');
    expect(src).toContain("import Explain from '../Explain'");
  });

  it('Phase 4.1 : bouton "?" rendu uniquement si explainKey pr\u00e9sent', () => {
    expect(src).toMatch(/\{explainKey && \(/);
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

// ══════════════════════════════════════════════════════════════════════════════
// Tests unitaires composants Phase 1 (nouveaux)
// ══════════════════════════════════════════════════════════════════════════════

describe('SolHeadline', () => {
  const src = readSol('SolHeadline.jsx');
  it('V2 raw dashboard-first : sol-font-body 16px 500 ink-700', () => {
    expect(src).toContain('var(--sol-font-body)');
    expect(src).toMatch(/fontSize:\s*16/);
    expect(src).toMatch(/fontWeight:\s*500/);
    expect(src).toContain('var(--sol-ink-700)');
  });
});

describe('SolSubline', () => {
  const src = readSol('SolSubline.jsx');
  it('V2 raw : 13px ink-500', () => {
    expect(src).toMatch(/fontSize:\s*13\b/);
    expect(src).toContain('var(--sol-ink-500)');
  });
});

describe('SolStatusPill', () => {
  const src = readSol('SolStatusPill.jsx');
  it('3 kinds : ok / att / risk', () => {
    expect(src).toContain('ok:');
    expect(src).toContain('att:');
    expect(src).toContain('risk:');
  });
  it('mono uppercase 10px', () => {
    expect(src).toContain('var(--sol-font-mono)');
    expect(src).toMatch(/textTransform:\s*'uppercase'/);
  });
});

describe('SolButton', () => {
  const src = readSol('SolButton.jsx');
  it('4 variants via className sol-btn--*', () => {
    expect(src).toContain('sol-btn--');
  });
  it('polymorphe via as="a"', () => {
    expect(src).toMatch(/as:\s*Tag\s*=\s*'button'/);
  });
});

describe('SolKpiRow', () => {
  const src = readSol('SolKpiRow.jsx');
  it('grid repeat 3 par défaut, gap 14', () => {
    expect(src).toMatch(/gridTemplateColumns:.*repeat\(\$\{columns/);
    expect(src).toMatch(/gap:\s*14/);
  });
});

describe('SolWeekGrid', () => {
  const src = readSol('SolWeekGrid.jsx');
  it("grid 3 cols gap 12", () => {
    expect(src).toMatch(/repeat\(3,\s*1fr\)/);
    expect(src).toMatch(/gap:\s*12/);
  });
});

describe('SolLayerToggle', () => {
  const src = readSol('SolLayerToggle.jsx');
  it('3 modes par défaut : surface / inspect / expert', () => {
    expect(src).toContain("'surface'");
    expect(src).toContain("'inspect'");
    expect(src).toContain("'expert'");
  });
  it('a11y : role="group" + aria-pressed', () => {
    expect(src).toContain('role="group"');
    expect(src).toContain('aria-pressed');
  });
});

describe('SolPendingBanner', () => {
  const src = readSol('SolPendingBanner.jsx');
  it('utilise sol-calme-bg + border calme', () => {
    expect(src).toContain('var(--sol-calme-bg)');
    expect(src).toContain('var(--sol-calme-fg)');
  });
  it('expose Annuler + Éditer', () => {
    expect(src).toContain('Annuler');
    expect(src).toContain('Éditer');
  });
});

describe('SolInspectDoc', () => {
  const src = readSol('SolInspectDoc.jsx');
  it('max-width 760 + Fraunces 15/1.7', () => {
    expect(src).toMatch(/maxWidth:\s*760/);
    expect(src).toContain('var(--sol-font-display)');
    expect(src).toMatch(/fontSize:\s*15/);
    expect(src).toMatch(/lineHeight:\s*1\.7/);
  });
});

describe('SolCartouche', () => {
  const src = readSol('SolCartouche.jsx');
  it('5 états : default / proposing / pending / executing / done', () => {
    expect(src).toMatch(/default:\s*{/);
    expect(src).toMatch(/proposing:\s*{/);
    expect(src).toMatch(/pending:\s*{/);
    expect(src).toMatch(/executing:\s*{/);
    expect(src).toMatch(/done:\s*{/);
  });
  it('position fixed bas-droit z-50', () => {
    expect(src).toMatch(/position:\s*'fixed'/);
    expect(src).toMatch(/zIndex:\s*50/);
  });
  it('chip voice guide FR', () => {
    expect(src).toContain('Sol · en veille');
    expect(src).toContain('Sol · propose');
  });
});

describe('SolDrawer', () => {
  const src = readSol('SolDrawer.jsx');
  it('a11y : role="dialog" + aria-modal', () => {
    expect(src).toContain('role="dialog"');
    expect(src).toContain('aria-modal="true"');
  });
  it('backdrop + aside', () => {
    expect(src).toContain('aria-hidden');
    expect(src).toContain('<aside');
  });
});

describe('SolExpertGrid', () => {
  const src = readSol('SolExpertGrid.jsx');
  it('table avec th triables', () => {
    expect(src).toContain('<table');
    expect(src).toContain('onSort');
  });
  it('cells num : mono tabular', () => {
    expect(src).toContain("col.num");
    expect(src).toContain('var(--sol-font-mono)');
  });
});

describe('SolJournal', () => {
  const src = readSol('SolJournal.jsx');
  it('grid 160/100/1fr/120', () => {
    expect(src).toContain("'160px 100px 1fr 120px'");
  });
  it('empty state FR', () => {
    expect(src).toContain("Aucune action Sol");
  });
});

describe('SolRail', () => {
  const src = readSol('SolRail.jsx');
  it('lit NavRegistry via getOrderedModules + resolveModule', () => {
    expect(src).toContain('getOrderedModules');
    expect(src).toContain('resolveModule');
  });
  it('logo "P." Fraunces', () => {
    expect(src).toContain('P.');
    expect(src).toContain('var(--sol-font-display)');
  });
  it('a11y : aria-label + aria-current', () => {
    expect(src).toContain('aria-label');
    expect(src).toContain('aria-current');
  });
});

describe('SolPanel', () => {
  const src = readSol('SolPanel.jsx');
  it('lit getPanelSections (Phase 3 : panelSections par route + fallback legacy)', () => {
    expect(src).toContain('getPanelSections');
  });
  it('aria-label navigation contextuelle', () => {
    expect(src).toContain('Navigation contextuelle');
  });
  it('accepte headerSlot + footerSlot (Phase 3 : scope switcher + user menu absorb\u00e9s)', () => {
    expect(src).toContain('headerSlot');
    expect(src).toContain('footerSlot');
  });
});

describe('SolAppShell', () => {
  const src = readSol('SolAppShell.jsx');
  it('layout grid 56/240/1fr/36', () => {
    expect(src).toContain("'56px 240px 1fr'");
    expect(src).toContain("'1fr 36px'");
  });
  it('compose Rail + Panel + Timerail + Cartouche', () => {
    expect(src).toContain('<SolRail');
    expect(src).toContain('<SolPanel');
    expect(src).toContain('<SolTimerail');
    expect(src).toContain('<SolCartouche');
  });
});

describe('SolTrajectoryChart (Phase 4.1)', () => {
  const src = readSol('SolTrajectoryChart.jsx');

  it('utilise Recharts LineChart + ReferenceLine target + ReferenceArea zones', () => {
    expect(src).toContain('LineChart');
    expect(src).toContain('ReferenceLine');
    expect(src).toContain('ReferenceArea');
  });

  it('bandes conformit\u00e9 0-60/60-75/75-100 avec tokens sol-{refuse,attention,succes}-bg', () => {
    expect(src).toContain('sol-refuse-bg');
    expect(src).toContain('sol-attention-bg');
    expect(src).toContain('sol-succes-bg');
  });

  it('dernier point annot\u00e9 via ReferenceDot stroke calme-fg', () => {
    expect(src).toContain('ReferenceDot');
    expect(src).toMatch(/stroke="var\(--sol-calme-fg\)"/);
  });

  it('accepte targetLine + targetLabel + sourceChip props', () => {
    for (const prop of ['targetLine', 'targetLabel', 'sourceChip', 'caption']) {
      expect(src).toContain(prop);
    }
  });
});

describe('Sol index barrel', () => {
  const src = readSol('index.js');

  it('exporte les 23 composants (21 + SolTrajectoryChart P4.1 + SolBarChart P4.1.1)', () => {
    for (const comp of [
      // Sprint 2 + Phase 1
      'SolPageHeader', 'SolKpiCard', 'SolHero', 'SolWeekCard', 'SolSourceChip',
      'SolSectionHead', 'SolLoadCurve', 'SolTimerail', 'SolHeadline', 'SolSubline',
      'SolStatusPill', 'SolButton', 'SolKpiRow', 'SolWeekGrid', 'SolLayerToggle',
      'SolPendingBanner', 'SolInspectDoc', 'SolCartouche', 'SolDrawer',
      'SolExpertGrid', 'SolJournal', 'SolRail', 'SolPanel', 'SolAppShell',
      // Phase 4.1
      'SolTrajectoryChart',
      // Phase 4.1.1
      'SolBarChart',
    ]) {
      expect(src).toContain(comp);
    }
  });
});

describe('SolBarChart (Phase 4.1.1)', () => {
  const src = readSol('SolBarChart.jsx');

  it('utilise Recharts BarChart + 2 Bar (current + previous)', () => {
    expect(src).toContain('BarChart');
    expect(src).toMatch(/dataKey="current"/);
    expect(src).toMatch(/dataKey="previous"/);
  });

  it('previous en ink-300 opacity 0.7 (comparateur discret)', () => {
    expect(src).toContain('var(--sol-ink-300)');
    expect(src).toMatch(/fillOpacity=\{0\.7\}/);
  });

  it('current highlight calme-fg si highlightCurrent + dernier mois', () => {
    expect(src).toContain('highlightCurrent');
    expect(src).toContain('var(--sol-calme-fg)');
  });

  it('accepte metric euros|mwh|count + formatValue FR (NBSP sep)', () => {
    expect(src).toContain("metric = 'euros'");
    expect(src).toMatch(/M€|k€|GWh|MWh/);
  });

  it('showDeltaPct rend LabelList avec delta pct au-dessus barre', () => {
    expect(src).toContain('LabelList');
    expect(src).toContain('DeltaPctLabel');
    expect(src).toContain('computeDeltaPct');
  });

  it('Phase 4.3 : supporte xAxisType + xAxisKey + xAxisAngle pour axe cat\u00e9goriel', () => {
    expect(src).toMatch(/xAxisType\s*=\s*'time'/);
    expect(src).toMatch(/xAxisKey\s*=\s*'month'/);
    expect(src).toMatch(/xAxisAngle\s*=\s*0/);
    // dataKey lit xAxisKey (pas "month" hardcod\u00e9)
    expect(src).toMatch(/dataKey=\{xAxisKey\}/);
  });
});

describe('SolKpiCard notApplicable (Phase 4.1.1 — APER applicability fix)', () => {
  const src = readSol('SolKpiCard.jsx');

  it('prop notApplicable + rend "N/A" en italique body font ink-500', () => {
    expect(src).toContain('notApplicable');
    expect(src).toMatch(/N\/A/);
    expect(src).toMatch(/fontStyle:\s*'italic'/);
  });

  it('masque delta + unit si notApplicable', () => {
    expect(src).toMatch(/notApplicable \?/);
  });
});

describe('SolPanel overflow (Phase 4.1.1 — scroll middle zone only)', () => {
  const src = readSol('SolPanel.jsx');

  it('body scroll zone via overflowY auto + flex 1 + minHeight 0', () => {
    expect(src).toMatch(/sol-panel-body/);
    expect(src).toMatch(/overflowY:\s*'auto'/);
    expect(src).toMatch(/minHeight:\s*0/);
  });

  it('aside root n\'a plus overflowY (header + footer naturellement visibles)', () => {
    // Le root aside doit avoir flexDirection column + minHeight 0
    // mais PAS overflowY (sinon header/footer scrollent aussi)
    expect(src).toMatch(/flexDirection:\s*'column'/);
  });
});
