/**
 * PROMEOS — ActionsImpact — Source Guards + Structure Tests
 * Vérifie display-only, fmtEur, navigation, composants internes.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcPath = join(__dirname, '..', 'pages', 'cockpit', 'ActionsImpact.jsx');
const src = readFileSync(srcPath, 'utf-8');

// ── Source Guards ────────────────────────────────────────────────────

describe('ActionsImpact — source guard (no-calc)', () => {
  it('ne contient pas de formule CO2 (* 0.0569)', () => {
    expect(src).not.toMatch(/\*\s*0\.0569/);
  });

  it('ne contient pas de formule risque (* 7500 ou * 3750)', () => {
    expect(src).not.toMatch(/\*\s*7500/);
    expect(src).not.toMatch(/\*\s*3750/);
  });

  it('ne contient pas de calcul de reduction (1 - x/y * 100)', () => {
    expect(src).not.toMatch(/1\s*-\s*.*\/\s*.*\)\s*\*\s*100/);
  });

  it('ne reassigne pas savings_eur avec un calcul', () => {
    expect(src).not.toMatch(/savings_eur\s*=\s*.*\*/);
    expect(src).not.toMatch(/estimated_gain_eur\s*=\s*.*\*/);
  });
});

// ── Design System ────────────────────────────────────────────────────

describe('ActionsImpact — design system', () => {
  it('importe fmtEur pour les montants', () => {
    expect(src).toMatch(/import.*fmtEur/);
  });

  it('utilise fmtEur (pas de formatage EUR manuel)', () => {
    expect(src).not.toMatch(/toLocaleString.*EUR/);
  });

  it('navigue vers /actions', () => {
    expect(src).toMatch(/navigate\(['"]\/actions/);
  });
});

// ── Structure ────────────────────────────────────────────────────────

describe('ActionsImpact — structure', () => {
  it('contient data-testid actions-impact', () => {
    expect(src).toContain('data-testid="actions-impact"');
  });

  it('contient data-testid action-row', () => {
    expect(src).toContain('data-testid="action-row"');
  });

  it('contient PriorityBadge', () => {
    expect(src).toMatch(/PriorityBadge/);
  });

  it('contient SourceTag', () => {
    expect(src).toMatch(/SourceTag/);
  });

  it('importe getActionsList depuis api', () => {
    expect(src).toMatch(/import.*getActionsList/);
  });

  it('utilise les champs API reels (title, priority, source_type, estimated_gain_eur)', () => {
    expect(src).toMatch(/action\.title/);
    expect(src).toMatch(/action\.priority/);
    expect(src).toMatch(/action\.source_type/);
    expect(src).toMatch(/action\.estimated_gain_eur/);
  });

  it('a un etat loading avec skeleton', () => {
    expect(src).toMatch(/animate-pulse/);
  });

  it('a un message empty', () => {
    expect(src).toMatch(/Aucune action prioritaire/);
  });

  it('a focus-visible rings sur les boutons', () => {
    expect(src).toMatch(/focus-visible:ring/);
  });
});
