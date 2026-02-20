/**
 * PROMEOS — PatrimoineVirtualization.test.js
 * Source-code guards for PR2 Phase 3: virtualization of Patrimoine table.
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

// ── Guard: Patrimoine uses @tanstack/react-virtual ─────────────────────────

describe('Patrimoine — virtualization guards', () => {
  const src = readSrc(pagesDir, 'Patrimoine.jsx');

  it('imports useVirtualizer from @tanstack/react-virtual', () => {
    expect(src).toContain("from '@tanstack/react-virtual'");
    expect(src).toContain('useVirtualizer');
  });

  it('does NOT use PAGE_SIZE constant (pagination removed)', () => {
    expect(src).not.toMatch(/const\s+PAGE_SIZE\s*=/);
  });

  it('does NOT import Pagination component', () => {
    expect(src).not.toMatch(/import\s+.*Pagination.*from/);
  });

  it('uses scrollRef for virtual scroll container', () => {
    expect(src).toContain('scrollRef');
    expect(src).toContain('getScrollElement');
  });

  it('uses estimateSize for row height', () => {
    expect(src).toContain('estimateSize');
  });

  it('uses getVirtualItems for rendering', () => {
    expect(src).toContain('getVirtualItems');
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

// ── Guard: ScopeContext increased fetch limit ──────────────────────────────

describe('ScopeContext — increased fetch limit', () => {
  const src = readSrc(ctxDir, 'ScopeContext.jsx');

  it('fetches with limit >= 2000', () => {
    const match = src.match(/limit:\s*(\d+)/);
    expect(match).toBeTruthy();
    expect(Number(match[1])).toBeGreaterThanOrEqual(2000);
  });
});
