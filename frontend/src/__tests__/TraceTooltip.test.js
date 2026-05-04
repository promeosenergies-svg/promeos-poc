/**
 * TraceTooltip.test.js — Sprint C-3 Phase 3.5
 *
 * Tests structurels (env=node, pas de DOM) :
 * - Composition via Explain.content
 * - Consommation hook useRegulatorySource
 * - Fallback graceful term inconnu
 * - Contenu tooltip (valeur, source, URL, formule, notes)
 *
 * Pattern repo : readFileSync + regex (cohérent avec EmissionFactorsContext.test.js
 * + RegulatoryRatesContext.test.js Phase 3.3).
 */
import { readFileSync } from 'fs';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

import TraceTooltip from '../ui/TraceTooltip';

const __dirname = dirname(fileURLToPath(import.meta.url));
const componentSrc = readFileSync(resolve(__dirname, '../ui/TraceTooltip.jsx'), 'utf8');

describe('TraceTooltip — structure', () => {
  it('exports default un composant React', () => {
    expect(TraceTooltip).toBeDefined();
    expect(typeof TraceTooltip).toBe('function');
  });

  it('compose via Explain (ADR Phase 3.1 — pas de refactor Explain)', () => {
    expect(componentSrc).toContain("import Explain from './Explain'");
    // Rendu final = <Explain content={tooltipContent}> wrappant children
    expect(componentSrc).toMatch(/<Explain\s+content=\{tooltipContent\}/);
  });

  it('consomme hook useRegulatorySource(termId) — pas de fetch direct', () => {
    expect(componentSrc).toContain('import { useRegulatorySource }');
    expect(componentSrc).toContain("from '../contexts/RegulatoryRatesContext'");
    expect(componentSrc).toMatch(/useRegulatorySource\(termId\)/);
  });

  it('accepte 4 props : termId | children | position | className', () => {
    expect(componentSrc).toMatch(/\(\s*\{\s*termId\s*,\s*children\s*,\s*position[^}]+\}\s*\)/);
    // position default 'top' (cohérent avec Explain)
    expect(componentSrc).toMatch(/position\s*=\s*['"]top['"]/);
  });
});

describe('TraceTooltip — fallback graceful', () => {
  it('term inconnu → enfants seuls (no crash, no tooltip)', () => {
    // Pattern : if (!trace) return <span>{children}</span>
    expect(componentSrc).toMatch(/if\s*\(!trace\)\s*\{\s*return\s+<span/);
  });
});

describe('TraceTooltip — contenu tooltip', () => {
  it('affiche valeur + unité (font-mono pour audit lisible)', () => {
    expect(componentSrc).toMatch(/font-mono/);
    expect(componentSrc).toMatch(/trace\.value/);
    expect(componentSrc).toMatch(/trace\.unit/);
  });

  it('affiche source.label (audit trail légal)', () => {
    expect(componentSrc).toContain('trace.source.label');
  });

  it('affiche source.url avec target="_blank" + rel sécurité', () => {
    expect(componentSrc).toContain('trace.source.url');
    expect(componentSrc).toMatch(/target="_blank"/);
    expect(componentSrc).toMatch(/rel="noopener noreferrer"/);
  });

  it('affiche source.version + effective_date', () => {
    expect(componentSrc).toContain('trace.source.version');
    expect(componentSrc).toContain('trace.source.effective_date');
  });

  it('affiche formula uniquement si présente (graceful null)', () => {
    expect(componentSrc).toMatch(/trace\.formula\s*&&/);
    expect(componentSrc).toMatch(/<code[^>]*>\{trace\.formula\}<\/code>/);
  });

  it('affiche notes uniquement si présentes (graceful null)', () => {
    expect(componentSrc).toMatch(/trace\.notes\s*&&/);
  });
});
