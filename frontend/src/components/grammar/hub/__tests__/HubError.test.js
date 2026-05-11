/**
 * grammar/hub/states/HubError — source-guards Vitest (Phase F.3)
 *
 * Pattern pure-grep readFileSync (env=node, aligne sur HubKpiCard.test.js).
 *
 * 6 tests couvrent :
 *   1. data-component="HubError" + data-correlation-id pose au root
 *   2. role="alert" + aria-live="polite" (accessibilite)
 *   3. icone lucide-react AlertTriangle utilisee
 *   4. correlationId copyable via navigator.clipboard + state "Copié ✓"
 *   5. onRetry optional avec bouton "Réessayer"
 *   6. JSDoc @typedef HubErrorProps + zero hex hardcoded
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '../states/HubError.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/hub/states/HubError', () => {
  it('data-component="HubError" + data-correlation-id pose au root', () => {
    const src = read();
    expect(src).toContain('data-component="HubError"');
    expect(src).toContain('data-correlation-id={correlationId}');
  });

  it('role="alert" + aria-live="polite" (accessibilite WCAG)', () => {
    const src = read();
    expect(src).toContain('role="alert"');
    expect(src).toContain('aria-live="polite"');
  });

  it('icone lucide-react AlertTriangle utilisee (pas Tabler, projet utilise lucide)', () => {
    const src = read();
    expect(src).toContain("import { AlertTriangle } from 'lucide-react'");
    expect(src).toMatch(/<AlertTriangle\b/);
  });

  it('correlationId copyable via navigator.clipboard + state "Copié ✓"', () => {
    const src = read();
    expect(src).toContain('navigator?.clipboard?.writeText');
    expect(src).toContain('setCopied(true)');
    expect(src).toContain("'Copié ✓'");
    // Reset apres 1.5s (toast UX)
    expect(src).toMatch(/setTimeout\(\(\)\s*=>\s*setCopied\(false\),\s*1500\)/);
  });

  it('onRetry optional avec bouton "Réessayer"', () => {
    const src = read();
    expect(src).toContain('{onRetry && (');
    expect(src).toContain('Réessayer');
    // Bouton type="button" (anti-form-submit default)
    expect(src).toMatch(/type="button"/);
  });

  it('JSDoc @typedef HubErrorProps + zero hex hardcoded', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} HubErrorProps');
    expect(src).toContain('@param {HubErrorProps} props');
    // Aucune couleur hex
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
