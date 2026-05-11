/**
 * grammar/hub/states/HubSkeleton — source-guards Vitest (Phase F.3)
 *
 * Pattern pure-grep readFileSync (env=node, aligne sur HubKpiCard.test.js).
 *
 * 6 tests couvrent :
 *   1. data-component="HubSkeleton" + data-skeleton-variant + data-skeleton-index
 *   2. 4 variants (hero/kpi/chart/highlight) avec hauteurs en pixels
 *   3. count prop default=1, support N (DRY pour triptyques)
 *   4. animate-pulse class Tailwind (respecte prefers-reduced-motion)
 *   5. JSDoc @typedef HubSkeletonProps + HubSkeletonVariant
 *   6. zero hex hardcoded (tokens-only)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../states/HubSkeleton.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/states/HubSkeleton', () => {
  it('data-component="HubSkeleton" + data-skeleton-variant + data-skeleton-index', () => {
    const src = read();
    expect(src).toContain('data-component="HubSkeleton"');
    expect(src).toContain('data-skeleton-variant={variant}');
    expect(src).toContain('data-skeleton-index={i}');
  });

  it('4 variants enumeres avec hauteurs en pixels (hero/kpi/chart/highlight)', () => {
    const src = read();
    expect(src).toContain('VARIANT_HEIGHT');
    expect(src).toContain('Object.freeze');
    expect(src).toMatch(/hero:\s*180/);
    expect(src).toMatch(/kpi:\s*128/);
    expect(src).toMatch(/chart:\s*220/);
    expect(src).toMatch(/highlight:\s*70/);
  });

  it('count prop default=1 + support N (DRY triptyques)', () => {
    const src = read();
    expect(src).toContain('count = 1');
    expect(src).toMatch(/Array\.from\(\{\s*length:\s*safeCount\s*\}/);
    expect(src).toMatch(/Math\.max\(1,\s*Math\.floor\(count\)\)/);
  });

  it('animate-pulse Tailwind (respecte prefers-reduced-motion via index.css)', () => {
    const src = read();
    // animate-pulse Tailwind est globalement neutralise par @media
    // prefers-reduced-motion: reduce (cf tokens.css ligne 107-113).
    expect(src).toContain('animate-pulse');
    expect(src).toContain('role="status"');
    expect(src).toContain('aria-busy="true"');
  });

  it('JSDoc @typedef HubSkeletonProps + HubSkeletonVariant', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} HubSkeletonProps');
    expect(src).toMatch(
      /@typedef\s+\{['"]hero['"]\|['"]kpi['"]\|['"]chart['"]\|['"]highlight['"]\}\s+HubSkeletonVariant/
    );
    expect(src).toContain('@param {HubSkeletonProps} props');
  });

  it('zero hex hardcoded (tokens-only doctrine §6.5)', () => {
    const src = read();
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
