/**
 * Step 24 — M6 : Message contextuel marché
 * kpiMessaging handler tests + source-guard tests.
 */
import { describe, it, expect } from 'vitest';
import fs from 'fs';
import { getKpiMessage } from '../services/kpiMessaging';

const readSrc = (...parts) => fs.readFileSync(`src/${parts.join('/')}`, 'utf8');

// ── A. kpiMessaging: market_spot_price handler ──────────────────────────────

describe('A. market_spot_price handler', () => {
  it('null → neutral', () => {
    expect(getKpiMessage('market_spot_price', null).severity).toBe('neutral');
  });

  it('NaN → neutral', () => {
    expect(getKpiMessage('market_spot_price', NaN).severity).toBe('neutral');
  });

  it('bas (trend < -5) → ok', () => {
    const msg = getKpiMessage('market_spot_price', 60, { avg12m: 72, trendPct: -8 });
    expect(msg.severity).toBe('ok');
  });

  it('haut (trend > 5) → warn', () => {
    const msg = getKpiMessage('market_spot_price', 85, { avg12m: 72, trendPct: 10 });
    expect(msg.severity).toBe('warn');
  });

  it('stable (|trend| < 5) → neutral', () => {
    const msg = getKpiMessage('market_spot_price', 70, { avg12m: 72, trendPct: -2 });
    expect(msg.severity).toBe('neutral');
  });

  it('bas has action', () => {
    const msg = getKpiMessage('market_spot_price', 60, { avg12m: 72, trendPct: -8 });
    expect(msg.action).toBeDefined();
    expect(msg.action.path).toContain('achat');
  });

  it('haut has action', () => {
    const msg = getKpiMessage('market_spot_price', 85, { avg12m: 72, trendPct: 10 });
    expect(msg.action).toBeDefined();
  });

  it('stable has no action', () => {
    const msg = getKpiMessage('market_spot_price', 70, { avg12m: 72, trendPct: -2 });
    expect(msg.action).toBeUndefined();
  });

  it('message contains EUR/MWh', () => {
    const msg = getKpiMessage('market_spot_price', 65, { trendPct: -3 });
    expect(msg.simple).toContain('EUR/MWh');
  });

  it('expert message contains EPEX', () => {
    const msg = getKpiMessage('market_spot_price', 65, { avg12m: 70, trendPct: -3 });
    expect(msg.expert).toContain('EPEX');
  });
});

// ── B. MarketContextBanner source guards ────────────────────────────────────

describe('B. MarketContextBanner component', () => {
  it('file exists', () => {
    const candidates = [
      'src/components/purchase/MarketContextBanner.jsx',
      'src/components/MarketContextBanner.jsx',
      'src/pages/purchase/MarketContextBanner.jsx',
    ];
    expect(candidates.some((f) => fs.existsSync(f))).toBe(true);
  });

  it('has 3 states (favorable, stable, cap/exposition)', () => {
    const src = readSrc('components', 'purchase', 'MarketContextBanner.jsx');
    expect(src.includes('favorable') || src.includes('Moment')).toBe(true);
    expect(src.includes('stable')).toBe(true);
    expect(src.includes('cap') || src.includes('dessus') || src.includes('exposition')).toBe(true);
  });

  it('exports MarketContextCompact', () => {
    const src = readSrc('components', 'purchase', 'MarketContextBanner.jsx');
    expect(src).toContain('MarketContextCompact');
  });

  it('renders EUR/MWh', () => {
    const src = readSrc('components', 'purchase', 'MarketContextBanner.jsx');
    expect(src).toContain('EUR/MWh');
  });
});

// ── C. PurchasePage integration ─────────────────────────────────────────────

describe('C. PurchasePage integration', () => {
  const src = readSrc('pages', 'PurchasePage.jsx');

  it('imports MarketContextBanner or getMarketContext', () => {
    expect(src.includes('MarketContextBanner') || src.includes('getMarketContext')).toBe(true);
  });

  it('uses marketContext state', () => {
    expect(src).toContain('marketContext');
  });
});

// ── D. Cockpit integration ──────────────────────────────────────────────────

describe('D. Cockpit compact market info', () => {
  const src = readSrc('pages', 'Cockpit.jsx');

  it('has market reference', () => {
    expect(
      src.includes('market') ||
        src.includes('marché') ||
        src.includes('EUR/MWh') ||
        src.includes('spot')
    ).toBe(true);
  });

  it('imports market or executive V2 data (V1+ refactor)', () => {
    expect(
      src.includes('MarketContextCompact') ||
        src.includes('getMarketContext') ||
        src.includes('useExecutiveV2')
    ).toBe(true);
  });
});

// ── E. kpiMessaging file ────────────────────────────────────────────────────

describe('E. kpiMessaging has market_spot_price', () => {
  const src = readSrc('services', 'kpiMessaging.js');

  it('contains market_spot_price handler', () => {
    expect(src).toContain('market_spot_price');
  });
});
