/**
 * PROMEOS — AsyncState guard tests (Playbook 2.3)
 * Verifies: AsyncState component exists, EmptyState/ErrorState are available,
 * and key pages handle loading/error states.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const ui = (f) => resolve(__dirname, '../../ui', f);
const pages = (f) => resolve(__dirname, '..', f);
const read = (p) => readFileSync(p, 'utf-8');

describe('AsyncState component', () => {
  it('AsyncState.jsx exists and exports default', () => {
    const src = read(ui('AsyncState.jsx'));
    expect(src).toContain('export default function AsyncState');
  });

  it('AsyncState handles loading state with skeleton', () => {
    const src = read(ui('AsyncState.jsx'));
    expect(src).toContain('loading');
    expect(src).toContain('animate-pulse');
  });

  it('AsyncState handles error state', () => {
    const src = read(ui('AsyncState.jsx'));
    expect(src).toContain('error');
    expect(src).toContain('ErrorState');
  });

  it('AsyncState handles empty state', () => {
    const src = read(ui('AsyncState.jsx'));
    expect(src).toContain('empty');
    expect(src).toContain('EmptyState');
  });

  it('AsyncState has retry support', () => {
    const src = read(ui('AsyncState.jsx'));
    expect(src).toContain('onRetry');
  });
});

describe('EmptyState component', () => {
  it('exists with CTA support', () => {
    const src = read(ui('EmptyState.jsx'));
    expect(src).toContain('export default function EmptyState');
    expect(src).toContain('ctaLabel');
    expect(src).toContain('onCta');
  });
});

describe('ErrorState component', () => {
  it('exists with retry button in French', () => {
    const src = read(ui('ErrorState.jsx'));
    expect(src).toContain('export default function ErrorState');
    expect(src).toContain('Réessayer');
    expect(src).toContain('debug');
  });
});

describe('Key pages handle async states', () => {
  const criticalPages = [
    { name: 'Cockpit', file: 'Cockpit.jsx' },
    { name: 'Patrimoine', file: 'Patrimoine.jsx' },
    { name: 'BillIntelPage', file: 'BillIntelPage.jsx' },
  ];

  criticalPages.forEach(({ name, file }) => {
    it(`${name} has loading state handling`, () => {
      const src = read(pages(file));
      // Should have some form of loading indicator
      const hasLoading = src.includes('loading') || src.includes('isLoading') ||
                         src.includes('Chargement') || src.includes('skeleton') ||
                         src.includes('Skeleton') || src.includes('animate-pulse');
      expect(hasLoading).toBe(true);
    });
  });

  it('Dashboard handles empty/loading', () => {
    // Dashboard is at cockpit or root
    const src = read(pages('Cockpit.jsx'));
    expect(src).toMatch(/loading|isLoading|Chargement/);
  });
});
