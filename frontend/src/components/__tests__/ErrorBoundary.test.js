/**
 * PROMEOS — ErrorBoundary tests
 * Source guards: retry button, page/orgId context logging.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'ErrorBoundary.jsx'), 'utf8');

describe('ErrorBoundary source guards', () => {
  it('logs page context from window.location.pathname', () => {
    expect(src).toContain('window.location.pathname');
  });

  it('reads orgId from localStorage promeos_scope', () => {
    expect(src).toContain('promeos_scope');
    expect(src).toContain('orgId');
  });

  it('passes page and orgId to logger.error', () => {
    expect(src).toContain('page,');
    expect(src).toContain('orgId,');
  });

  it('has a Reessayer (retry) button that resets error without navigating', () => {
    expect(src).toContain('Reessayer');
    // Retry resets state without changing window.location
    expect(src).toMatch(/onClick.*setState.*hasError:\s*false/);
  });

  it("has a Retour a l'accueil button that navigates home", () => {
    expect(src).toContain("Retour a l'accueil");
    expect(src).toContain("window.location.assign('/')");
  });
});
