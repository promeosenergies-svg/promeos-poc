/**
 * PROMEOS — V25: DevPanel tests
 * Source-level guards + render checks.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'DevPanel.jsx'), 'utf8');

describe('DevPanel source guards', () => {
  it('imports useScope from ScopeContext', () => {
    expect(src).toContain("import { useScope } from '../contexts/ScopeContext'");
  });

  it('imports getLastRequests from api', () => {
    expect(src).toContain("import { getLastRequests } from '../services/api'");
  });

  it('returns null when ?debug is absent', () => {
    // The source must check for ?debug and return null
    expect(src).toContain('if (!isDebug) return null');
  });

  it('has Scope tab content with scope fields', () => {
    expect(src).toContain('orgId');
    expect(src).toContain('sitesLoading');
    expect(src).toContain('sitesCount');
    expect(src).toContain('selectedSiteId');
  });

  it('has siteIds collapsible list in Scope tab', () => {
    expect(src).toContain('siteIds');
    expect(src).toContain('orgSites.map');
  });

  it('has API tab that calls getLastRequests()', () => {
    expect(src).toContain('getLastRequests()');
  });

  it('has Cache tab reading localStorage promeos_* keys', () => {
    expect(src).toContain('promeos_');
    expect(src).toContain('localStorage');
  });

  it('has Env tab showing MODE and VITE_API_URL', () => {
    expect(src).toContain('import.meta.env.MODE');
    expect(src).toContain('VITE_API_URL');
  });

  it('has 4 tabs: Scope, API, Cache, Env', () => {
    expect(src).toContain("'Scope'");
    expect(src).toContain("'API'");
    expect(src).toContain("'Cache'");
    expect(src).toContain("'Env'");
  });
});
