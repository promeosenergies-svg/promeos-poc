/**
 * Tests structurels PriceReferenceContext (queue 2 QA Guardian 2026-04-15).
 * Source unique prix de référence (fallback) côté frontend.
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const contextSrc = readFileSync(resolve(__dirname, '../PriceReferenceContext.jsx'), 'utf8');

describe('PriceReferenceContext — structure', () => {
  it('exporte Provider + 2 hooks', () => {
    expect(contextSrc).toContain('export function PriceReferenceProvider');
    expect(contextSrc).toContain('export function useElecPriceReference');
    expect(contextSrc).toContain('export function usePriceReferences');
  });

  it('fetch /api/config/price-references au mount', () => {
    expect(contextSrc).toContain("fetch('/api/config/price-references')");
  });

  it('a un FALLBACK_PRICES avec elec et gaz', () => {
    expect(contextSrc).toContain('FALLBACK_PRICES');
    expect(contextSrc).toContain('elec_eur_kwh');
    expect(contextSrc).toContain('gaz_eur_kwh');
  });

  it('gère les erreurs fetch silencieusement (console.warn + fallback)', () => {
    expect(contextSrc).toContain('.catch(');
    expect(contextSrc).toContain('console.warn');
  });
});

describe('PriceReferenceContext — doctrine non-réglementaire', () => {
  it('signale is_regulatory: false dans le fallback', () => {
    expect(contextSrc).toContain('is_regulatory: false');
  });

  it("documente que ce fallback N'EST PAS une source réglementaire", () => {
    expect(contextSrc).toMatch(/non-?r[ée]glementaire/i);
  });

  it('fallback elec = 0.068 aligné sur YAML prix_reference', () => {
    expect(contextSrc).toContain('0.068');
  });

  it('fallback gaz = 0.045 aligné sur YAML prix_reference', () => {
    expect(contextSrc).toContain('0.045');
  });
});

describe('PriceReferenceContext — read-only', () => {
  it("n'expose aucun setter depuis le Context.Provider value", () => {
    const providerValueMatch = contextSrc.match(
      /PriceReferenceContext\.Provider[\s\S]*?value=\{([^}]+)\}/
    );
    expect(providerValueMatch).not.toBeNull();
    const valueBlock = providerValueMatch[1];
    expect(valueBlock).not.toContain('setPrices');
    expect(valueBlock).toContain('prices');
    expect(valueBlock).toContain('loading');
    expect(valueBlock).toContain('error');
  });
});
