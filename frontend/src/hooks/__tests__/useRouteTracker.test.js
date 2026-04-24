/**
 * useRouteTracker — source-guard tests (Sprint 1 Vague B · B2.3)
 *
 * Test runtime DOM impossible (env node sans jsdom). Guards vérifient
 * l'intégration correcte : import addRecent, useLocation, exclusions,
 * useEffect avec dep pathname.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'useRouteTracker.js'), 'utf-8');

describe('useRouteTracker (B2.1)', () => {
  it('imports useEffect from react', () => {
    expect(src).toMatch(/import\s*\{\s*useEffect\s*\}\s*from\s*['"]react['"]/);
  });

  it('imports useLocation from react-router-dom', () => {
    expect(src).toMatch(/import\s*\{\s*useLocation\s*\}\s*from\s*['"]react-router-dom['"]/);
  });

  it('imports addRecent from utils/navRecent', () => {
    expect(src).toMatch(/import\s*\{\s*addRecent\s*\}\s*from\s*['"]\.\.\/utils\/navRecent['"]/);
  });

  it('default-exports a function named useRouteTracker', () => {
    expect(src).toMatch(/export default function useRouteTracker/);
  });

  it('excludes technical routes from tracking (/, /login, /_sol_showcase)', () => {
    expect(src).toMatch(/EXCLUDED_PATHS.*new Set/);
    expect(src).toMatch(/['"]\/['"]/);
    expect(src).toMatch(/['"]\/login['"]/);
    expect(src).toMatch(/['"]\/_sol_showcase['"]/);
  });

  it('useEffect depends on pathname + getLabel', () => {
    expect(src).toMatch(/\[pathname,\s*getLabel\]/);
  });

  it('calls addRecent only when pathname NOT in EXCLUDED_PATHS', () => {
    expect(src).toMatch(/if\s*\(EXCLUDED_PATHS\.has\(pathname\)\)\s*return/);
  });

  it('guards addRecent call (not invoked at module load)', () => {
    // Assure que addRecent est appelée DANS useEffect, pas au top-level
    expect(src).toMatch(/useEffect\([\s\S]*?addRecent\(pathname/);
  });
});
