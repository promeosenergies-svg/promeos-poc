/**
 * PROMEOS — Tests for TooltipPortal
 * Covers: computePosition helper for all 4 directions.
 */
import { describe, it, expect } from 'vitest';
import { computePosition, clampCoords, TOOLTIP_DELAY_MS } from '../TooltipPortal';

const OFFSET = 8;

const mockRect = { top: 100, left: 200, width: 40, height: 40 };

describe('computePosition', () => {
  it('right: tooltip left of trigger right edge + offset', () => {
    const pos = computePosition(mockRect, 'right');
    expect(pos.left).toBe(200 + 40 + OFFSET);
    expect(pos.top).toBe(100 + 20); // vertically centered
    expect(pos.transform).toBe('translateY(-50%)');
  });

  it('left: tooltip right-aligned to trigger left edge', () => {
    const pos = computePosition(mockRect, 'left');
    expect(pos.left).toBe(200 - OFFSET);
    expect(pos.top).toBe(100 + 20);
    expect(pos.transform).toContain('translate');
  });

  it('top: tooltip above trigger', () => {
    const pos = computePosition(mockRect, 'top');
    expect(pos.top).toBe(100 - OFFSET);
    expect(pos.left).toBe(200 + 20); // horizontally centered
    expect(pos.transform).toContain('-100%');
  });

  it('bottom: tooltip below trigger', () => {
    const pos = computePosition(mockRect, 'bottom');
    expect(pos.top).toBe(100 + 40 + OFFSET);
    expect(pos.left).toBe(200 + 20);
    expect(pos.transform).toBe('translateX(-50%)');
  });

  it('defaults to top when position is unknown', () => {
    const pos = computePosition(mockRect, 'invalid');
    expect(pos.top).toBe(100 - OFFSET);
  });

  it('returns 0,0 for null rect', () => {
    const pos = computePosition(null);
    expect(pos.top).toBe(0);
    expect(pos.left).toBe(0);
  });
});

// ── Sprint WOW 6.6 additions ──────────────────────────────────────────────────

describe('TOOLTIP_DELAY_MS', () => {
  it('hover delay is between 80ms and 200ms (anti-flicker range)', () => {
    expect(TOOLTIP_DELAY_MS).toBeGreaterThanOrEqual(80);
    expect(TOOLTIP_DELAY_MS).toBeLessThanOrEqual(200);
  });
});

describe('clampCoords', () => {
  it('left is clamped when tooltip would overflow right edge of viewport', () => {
    const coords = { top: 100, left: 1100, transform: 'translateY(-50%)' };
    const clamped = clampCoords(coords, 1024, 768);
    expect(clamped.left).toBeLessThanOrEqual(1024 - 180 - 4);
  });

  it('top is clamped when tooltip would overflow bottom edge of viewport', () => {
    const coords = { top: 760, left: 72, transform: 'translateY(-50%)' };
    const clamped = clampCoords(coords, 1024, 768);
    expect(clamped.top).toBeLessThanOrEqual(768 - 28 - 4);
  });

  it('coords already within viewport are returned unchanged', () => {
    const coords = { top: 100, left: 72, transform: 'translateY(-50%)' };
    const clamped = clampCoords(coords, 1024, 768);
    expect(clamped.left).toBe(72);
    expect(clamped.top).toBe(100);
    expect(clamped.transform).toBe('translateY(-50%)');
  });
});
