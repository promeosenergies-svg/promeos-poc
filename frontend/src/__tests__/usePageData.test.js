/**
 * PROMEOS — Tests usePageData hook (Sprint QA S)
 * Vérifie la structure, les garanties et l'absence de logique métier.
 * Environnement : node (pas jsdom) — tests structurels uniquement.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const hookSrc = readFileSync(resolve(__dirname, '..', 'hooks', 'usePageData.js'), 'utf-8');

describe('usePageData — structure', () => {
  it('exports a default function', () => {
    expect(hookSrc).toContain('export default function usePageData');
  });

  it('accepts fetcher and deps parameters', () => {
    expect(hookSrc).toMatch(/function usePageData\(fetcher,\s*deps/);
  });

  it('returns data, loading, error, refetch', () => {
    expect(hookSrc).toContain('return { data, loading, error, refetch');
  });
});

describe('usePageData — guards', () => {
  it('has unmount guard (mountedRef)', () => {
    expect(hookSrc).toContain('mountedRef');
    expect(hookSrc).toContain('mountedRef.current = true');
    expect(hookSrc).toContain('mountedRef.current = false');
  });

  it('has stale response guard (fetchIdRef)', () => {
    expect(hookSrc).toContain('fetchIdRef');
    expect(hookSrc).toContain('fetchIdRef.current !== fetchId');
  });

  it('converts error to string message', () => {
    expect(hookSrc).toMatch(/err\?\.message\s*\|\|\s*err\?\.detail\s*\|\|\s*'Erreur/);
  });
});

describe('usePageData — no business logic', () => {
  it('does not import any API service', () => {
    expect(hookSrc).not.toContain("from '../services/api");
    expect(hookSrc).not.toContain("from '../models/");
    expect(hookSrc).not.toContain("from '../domain/");
  });

  it('does not contain Math operations', () => {
    expect(hookSrc).not.toContain('Math.');
  });

  it('does not contain EUR/kWh/MWh references', () => {
    expect(hookSrc).not.toMatch(/EUR|kWh|MWh/);
  });

  it('uses only React hooks (useState, useEffect, useCallback, useRef)', () => {
    expect(hookSrc).toContain('useState');
    expect(hookSrc).toContain('useEffect');
    expect(hookSrc).toContain('useCallback');
    expect(hookSrc).toContain('useRef');
  });
});

describe('usePageData — defaults', () => {
  it('initial loading state is true', () => {
    expect(hookSrc).toContain('useState(true)');
  });

  it('initial data is null', () => {
    expect(hookSrc).toContain('useState(null)');
  });

  it('deps defaults to empty array', () => {
    expect(hookSrc).toMatch(/deps\s*=\s*\[\]/);
  });
});
