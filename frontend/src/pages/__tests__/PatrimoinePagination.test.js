/**
 * PROMEOS — PatrimoinePagination.test.js
 * Source-code guards for V2: pagination replaces virtualization.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const pagesDir = join(__dirname, '..');
const ctxDir = join(__dirname, '..', '..', 'contexts');

function readSrc(dir, file) {
  return readFileSync(join(dir, file), 'utf-8');
}

// ── Guard: Patrimoine uses Pagination (not virtual scroll) ─────────────────

describe('Patrimoine — V2 pagination guards', () => {
  const src = readSrc(pagesDir, 'Patrimoine.jsx');

  it('does NOT import useVirtualizer (virtual scroll removed)', () => {
    expect(src).not.toMatch(/import\s+.*useVirtualizer.*from/);
  });

  it('uses PAGE_SIZE constant for pagination', () => {
    expect(src).toMatch(/const\s+PAGE_SIZE\s*=/);
  });

  it('imports Pagination component', () => {
    expect(src).toMatch(/import\s+.*Pagination.*from/);
  });

  it('does NOT use getVirtualItems (virtual scroll removed)', () => {
    expect(src).not.toContain('getVirtualItems');
  });

  it('uses paginatedSites for table rendering', () => {
    expect(src).toContain('paginatedSites');
  });

  it('still imports RISK_THRESHOLDS (no regression)', () => {
    expect(src).toContain('RISK_THRESHOLDS');
  });

  it('still imports ANOMALY_THRESHOLDS (no regression)', () => {
    expect(src).toContain('ANOMALY_THRESHOLDS');
  });

  it('still imports getStatusBadgeProps (no regression)', () => {
    expect(src).toContain('getStatusBadgeProps');
  });
});

// ── Guard: V2 layout — KPI strip, no HealthBar in flow ─────────────────────

describe('Patrimoine — V2 layout guards', () => {
  const src = readSrc(pagesDir, 'Patrimoine.jsx');

  it('has KpiStripItem component', () => {
    expect(src).toContain('KpiStripItem');
  });

  it('PatrimoinePortfolioHealthBar is not in the render flow', () => {
    const lines = src
      .split('\n')
      .filter((l) => l.includes('PatrimoinePortfolioHealthBar') && !l.startsWith('//'));
    // Only commented import lines should remain
    expect(lines.every((l) => l.trimStart().startsWith('//'))).toBe(true);
  });

  it('PatrimoineHeatmap is not in the render flow', () => {
    const lines = src
      .split('\n')
      .filter((l) => l.includes('PatrimoineHeatmap') && !l.startsWith('//'));
    expect(lines.every((l) => l.trimStart().startsWith('//'))).toBe(true);
  });

  it('has Tableau/Carte view toggle', () => {
    expect(src).toMatch(/viewMode/);
    expect(src).toMatch(/Tableau|table/);
    expect(src).toMatch(/Carte|map/);
  });
});

// ── Guard: ScopeContext increased fetch limit ──────────────────────────────

describe('ScopeContext — increased fetch limit', () => {
  const src = readSrc(ctxDir, 'ScopeContext.jsx');

  it('fetches with limit >= 2000', () => {
    const match = src.match(/limit:\s*(\d+)/);
    expect(match).toBeTruthy();
    expect(Number(match[1])).toBeGreaterThanOrEqual(2000);
  });
});
