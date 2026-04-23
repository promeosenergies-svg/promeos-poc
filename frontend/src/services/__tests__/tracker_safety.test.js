/**
 * Tracker safety — F4 fixes P2-1 + P2-2
 *
 * Source-guard (pas de DOM lib — jsdom/happy-dom non installé dans le
 * projet). Vérifie que le code expose les protections contre :
 *   - PII leak : sanitize `href` via whitelist query keys
 *   - Quota exceeded : try/catch autour de localStorage.setItem/removeItem
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'tracker.js'), 'utf-8');

describe('Tracker safety — PII anti-leak (F4 P2-1)', () => {
  it('declares SAFE_QUERY_KEYS whitelist', () => {
    expect(src).toMatch(/const\s+SAFE_QUERY_KEYS\s*=\s*new Set\(/);
  });

  it('whitelist includes Vague 1 deep-link keys (fw, filter, horizon, tab)', () => {
    expect(src).toMatch(/['"]fw['"]/);
    expect(src).toMatch(/['"]filter['"]/);
    expect(src).toMatch(/['"]horizon['"]/);
    expect(src).toMatch(/['"]tab['"]/);
  });

  it('exposes sanitizeHref helper that strips non-whitelisted keys', () => {
    expect(src).toMatch(/function\s+sanitizeHref/);
    expect(src).toMatch(/URLSearchParams/);
    expect(src).toMatch(/SAFE_QUERY_KEYS\.has/);
  });

  it('track() applies sanitizeHref when href field present', () => {
    expect(src).toMatch(/['"]href['"]\s+in\s+data/);
    expect(src).toMatch(/href:\s*sanitizeHref/);
  });

  it('safeData is used in console.log and persist (no unsanitized leak)', () => {
    expect(src).toMatch(/console\.log\(`\[tracker\] \$\{event\}`, safeData\)/);
    expect(src).toMatch(/\.\.\.safeData/);
  });
});

describe('Tracker safety — quota exceeded (F4 P2-2)', () => {
  it('persistEvents wraps setItem in try/catch', () => {
    expect(src).toMatch(/function\s+persistEvents[\s\S]*?try\s*\{[\s\S]*?setItem/);
  });

  it('clearTrackerEvents wraps removeItem in try/catch', () => {
    expect(src).toMatch(/clearTrackerEvents[\s\S]*?try\s*\{[\s\S]*?removeItem/);
  });

  it('no bare localStorage.setItem call (all wrapped)', () => {
    // Only setItem inside persistEvents (with try/catch wrapper above it).
    const setItemCalls = src.match(/localStorage\.setItem/g) || [];
    expect(setItemCalls.length).toBe(1); // single call, protected by try/catch
  });
});
