/**
 * PROMEOS — P0 Purchase Fixes
 * Tests for:
 *   P0-1: No hardcoded org_id=1 in PurchasePage
 *   P0-2: Deep-link ?filter= maps to correct tab
 *   P0-3: PurchaseAssistantPage triggers API call
 */
import { describe, it, expect } from 'vitest';
import * as fs from 'node:fs';
import * as path from 'node:path';

const SRC = path.resolve(__dirname, '../..');

function readSrc(relPath) {
  return fs.readFileSync(path.join(SRC, relPath), 'utf-8');
}

// ════════════════════════════════════════════════════════════════════
// P0-1: org_id must NOT be hardcoded in PurchasePage
// ════════════════════════════════════════════════════════════════════

describe('P0-1: PurchasePage — dynamic org_id', () => {
  const src = readSrc('pages/PurchasePage.jsx');

  it('does not contain computePortfolio(1) — hardcoded org_id', () => {
    expect(src).not.toContain('computePortfolio(1)');
  });

  it('does not contain getPortfolioResults(1) — hardcoded org_id', () => {
    expect(src).not.toContain('getPortfolioResults(1)');
  });

  it('uses scope.orgId for computePortfolio', () => {
    expect(src).toContain('computePortfolio(scope.orgId)');
  });

  it('uses scope.orgId for getPortfolioResults', () => {
    expect(src).toContain('getPortfolioResults(scope.orgId)');
  });

  it('destructures scope from useScope()', () => {
    expect(src).toMatch(/const\s*\{[^}]*scope[^}]*\}\s*=\s*useScope\(\)/);
  });
});

// ════════════════════════════════════════════════════════════════════
// P0-2: Deep-link ?filter= is read and mapped to correct tab
// ════════════════════════════════════════════════════════════════════

describe('P0-2: PurchasePage — deep-link filter support', () => {
  const src = readSrc('pages/PurchasePage.jsx');

  it('imports useSearchParams from react-router-dom', () => {
    expect(src).toContain('useSearchParams');
    expect(src).toContain('react-router-dom');
  });

  it('defines FILTER_TO_TAB mapping', () => {
    expect(src).toContain('FILTER_TO_TAB');
  });

  it('maps filter=renewal to echeances tab', () => {
    expect(src).toContain("renewal: 'echeances'");
  });

  it('maps filter=missing to portefeuille tab', () => {
    expect(src).toContain("missing: 'portefeuille'");
  });

  it('reads filter from searchParams on init', () => {
    expect(src).toContain("searchParams.get('filter')");
  });

  it('syncs tab changes back to URL', () => {
    expect(src).toContain('setSearchParams');
  });
});

// ════════════════════════════════════════════════════════════════════
// P0-3: PurchaseAssistantPage calls the API
// ════════════════════════════════════════════════════════════════════

describe('P0-3: PurchaseAssistantPage — API integration', () => {
  const src = readSrc('pages/PurchaseAssistantPage.jsx');

  it('imports getPurchaseAssistantData from api', () => {
    expect(src).toContain('getPurchaseAssistantData');
    expect(src).toContain("from '../services/api'");
  });

  it('imports useScope for dynamic org context', () => {
    expect(src).toContain('useScope');
    expect(src).toContain("from '../contexts/ScopeContext'");
  });

  it('calls getPurchaseAssistantData in useEffect', () => {
    expect(src).toContain('getPurchaseAssistantData(');
  });

  it('sets isDemo from API response', () => {
    expect(src).toContain('data.is_demo');
  });

  it('uses apiAssistantData when available', () => {
    expect(src).toContain('apiAssistantData');
  });

  it('falls back to getAllDemoSites when API fails', () => {
    expect(src).toContain('getAllDemoSites()');
  });
});

// ════════════════════════════════════════════════════════════════════
// P0-3: API service exports the assistant endpoint
// ════════════════════════════════════════════════════════════════════

describe('P0-3: services/api.js — getPurchaseAssistantData', () => {
  const src = readSrc('services/api.js');

  it('exports getPurchaseAssistantData', () => {
    expect(src).toContain('export const getPurchaseAssistantData');
  });

  it('calls /purchase/assistant endpoint', () => {
    expect(src).toContain("'/purchase/assistant'");
  });
});
