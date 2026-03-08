/**
 * portfolioV115.test.js — V115 Portfolio source-guard tests
 * 10 assertions verifying P95 peak, InfoTip tooltips, clickable cards,
 * date persistence, and centralized pricing.
 * No DOM, no mocks — readFileSync + regex.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
function src(relPath) {
  return readFileSync(resolve(root, relPath), 'utf-8');
}

const backendRoot = resolve(__dirname, '../../../../backend');
function backend(relPath) {
  return readFileSync(resolve(backendRoot, relPath), 'utf-8');
}

describe('V115 Portfolio 0-issues guard-rails', () => {
  const pageSrc = src('src/pages/ConsumptionPortfolioPage.jsx');
  const portfolioPy = backend('routes/portfolio.py');

  it('1. InfoTip is imported in ConsumptionPortfolioPage', () => {
    expect(pageSrc).toMatch(/import\s+InfoTip\s+from/);
  });

  it('2. 4 KPI cards have InfoTip tooltips', () => {
    const matches = pageSrc.match(/<InfoTip\s+content="/g);
    expect(matches).not.toBeNull();
    expect(matches.length).toBeGreaterThanOrEqual(4);
  });

  it('3. Table header uses "P95 kW" (not "Pic kW")', () => {
    expect(pageSrc).toMatch(/P95 kW/);
    expect(pageSrc).not.toMatch(/>\s*Pic kW\s*</);
  });

  it('4. Table headers Base nuit and Couverture have InfoTip', () => {
    // JSX may have {' '} + newline + indentation between text and <InfoTip
    expect(pageSrc).toMatch(/Base nuit[\s\S]{0,40}<InfoTip/);
    expect(pageSrc).toMatch(/Couverture[\s\S]{0,40}<InfoTip/);
  });

  it('5. "Ou agir" cards have onClick (4 clickable cards)', () => {
    const section = pageSrc.slice(
      pageSrc.indexOf('Ou agir en priorite'),
      pageSrc.indexOf('SITES TABLE')
    );
    const clicks = section.match(/onClick=\{/g);
    expect(clicks).not.toBeNull();
    // 4 Card onClick + grouped action button + TopListActions (many)
    expect(clicks.length).toBeGreaterThanOrEqual(4);
  });

  it('6. useSearchParams is imported (date persistence)', () => {
    expect(pageSrc).toMatch(/useSearchParams/);
    expect(pageSrc).toMatch(/searchParams\.get\(['"]from['"]\)/);
  });

  it('7. get_reference_price is imported in portfolio.py', () => {
    expect(portfolioPy).toMatch(/from services\.billing_service import get_reference_price/);
  });

  it('8. _site_peak_kw no longer uses func.max', () => {
    const fnBody = portfolioPy.slice(
      portfolioPy.indexOf('def _site_peak_kw'),
      portfolioPy.indexOf('def _base_night_pct')
    );
    expect(fnBody).not.toMatch(/func\.max/);
    expect(fnBody).toMatch(/0\.95/);
  });

  it('9. READINGS_PER_DAY dict is defined in portfolio.py', () => {
    expect(portfolioPy).toMatch(/READINGS_PER_DAY\s*=/);
    expect(portfolioPy).toMatch(/"15min":\s*96/);
    expect(portfolioPy).toMatch(/"hourly":\s*24/);
  });

  it('10. _confidence_for_readings accepts frequency parameter', () => {
    expect(portfolioPy).toMatch(/def _confidence_for_readings\(.*frequency/);
  });
});
