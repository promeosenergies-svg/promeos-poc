/**
 * patrimoineV63.portfoliofix.test.js — Guards correction race condition portfolio
 *
 * Bug corrigé : "Impossible de charger le résumé portfolio." apparaissait
 * lorsque PatrimoinePortfolioHealthBar (composant enfant) fire son useEffect
 * AVANT que ScopeContext (parent) appelle setApiScope. Résultat : requête sans
 * header X-Org-Id → backend résout avec DemoState ou first active org → si ni
 * l'un ni l'autre n'est disponible (après reset) → 403 → catch → message d'erreur.
 *
 * Correctif en 3 points :
 *   A. ScopeContext appelle setApiScope SYNCHRONEMENT pendant le render (belt-and-suspenders)
 *   B. PatrimoinePortfolioHealthBar accepte prop orgId, gate le fetch sur orgId != null
 *   C. Patrimoine.jsx passe scope.orgId à PatrimoinePortfolioHealthBar
 *
 * Source guards (AST-free, regex-based) :
 *   - PatrimoinePortfolioHealthBar.jsx
 *   - Patrimoine.jsx
 *   - contexts/ScopeContext.jsx
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import path from 'path';

const src = (rel) => readFileSync(path.resolve(__dirname, '..', '..', rel), 'utf8');

const HEALTH_BAR  = src('components/PatrimoinePortfolioHealthBar.jsx');
const PATRIMOINE  = src('pages/Patrimoine.jsx');
const SCOPE_CTX   = src('contexts/ScopeContext.jsx');

// ── A. ScopeContext — appel synchrone de setApiScope ─────────────────────

describe('ScopeContext — setApiScope synchrone (anti-race)', () => {
  test('setApiScope appelé hors useEffect (synchrone dans le render)', () => {
    // Le correctif ajoute un appel direct à setApiScope dans le corps du composant,
    // AVANT le useEffect. On vérifie que setApiScope apparaît au moins deux fois
    // (une fois synchrone, une fois dans le useEffect).
    const count = (SCOPE_CTX.match(/setApiScope\s*\(/g) || []).length;
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('useEffect setApiScope toujours présent pour les changements futurs', () => {
    expect(SCOPE_CTX).toMatch(/useEffect\s*\(\s*\(\s*\)\s*=>\s*\{[\s\S]*?setApiScope/);
  });

  test('appel synchrone documenté (commentaire anti-race ou belt-and-suspenders)', () => {
    expect(SCOPE_CTX).toMatch(/synchron|belt-and-suspenders|avant.*child|child.*avant|child.*effect/i);
  });

  test('setApiScope importé depuis api.js', () => {
    expect(SCOPE_CTX).toMatch(/import.*setApiScope.*from|setApiScope.*import/);
  });
});

// ── B. PatrimoinePortfolioHealthBar — prop orgId + guard ─────────────────

describe('PatrimoinePortfolioHealthBar — prop orgId (anti-race)', () => {
  test('prop orgId acceptée dans la signature', () => {
    expect(HEALTH_BAR).toMatch(/PatrimoinePortfolioHealthBar\s*\(\s*\{[^}]*orgId/);
  });

  test('orgId a une valeur par défaut null', () => {
    expect(HEALTH_BAR).toMatch(/orgId\s*=\s*null/);
  });

  test('guard if (!orgId) return dans useEffect', () => {
    expect(HEALTH_BAR).toMatch(/if\s*\(\s*!orgId\s*\)\s*return/);
  });

  test('useEffect dépend de orgId (pas de [] vide)', () => {
    // Le useEffect doit avoir [orgId] comme dépendance
    expect(HEALTH_BAR).toMatch(/\[\s*orgId\s*\]/);
  });

  test('skeleton affiché quand orgId est null (!orgId)', () => {
    // Guard avant le loading state : if (!orgId) return <skeleton>
    expect(HEALTH_BAR).toMatch(/if\s*\(\s*!orgId\s*\)[\s\S]{0,200}animate-pulse/);
  });

  test('fetchSummary toujours appelé (n\'a pas disparu)', () => {
    expect(HEALTH_BAR).toMatch(/fetchSummary\s*\(/);
  });

  test('getPatrimoinePortfolioSummary toujours importé', () => {
    expect(HEALTH_BAR).toMatch(/getPatrimoinePortfolioSummary/);
  });
});

// ── C. Patrimoine.jsx — scope.orgId passé au composant ───────────────────

describe('Patrimoine.jsx — passage de scope.orgId', () => {
  test('scope extrait de useScope()', () => {
    expect(PATRIMOINE).toMatch(/scope\s*[,}].*useScope\s*\(\s*\)|useScope[\s\S]{0,200}scope/);
  });

  test('orgId={scope.orgId} passé à PatrimoinePortfolioHealthBar', () => {
    expect(PATRIMOINE).toMatch(/PatrimoinePortfolioHealthBar[\s\S]{0,200}orgId\s*=\s*\{scope\.orgId\}/);
  });

  test('PatrimoinePortfolioHealthBar toujours rendu dans Patrimoine.jsx', () => {
    expect(PATRIMOINE).toMatch(/<PatrimoinePortfolioHealthBar/);
  });

  test('onSiteClick toujours passé à PatrimoinePortfolioHealthBar', () => {
    expect(PATRIMOINE).toMatch(/<PatrimoinePortfolioHealthBar[\s\S]{0,200}onSiteClick/);
  });
});

// ── Invariants V60/V61 toujours présents ────────────────────────────────

describe('Invariants V60/V61 — régressions', () => {
  test('états loading, error, vide (sites_count===0) toujours présents', () => {
    expect(HEALTH_BAR).toMatch(/loading/);
    expect(HEALTH_BAR).toMatch(/error/);
    expect(HEALTH_BAR).toMatch(/sites_count\s*===\s*0/);
  });

  test('TrendBadge toujours présent', () => {
    expect(HEALTH_BAR).toMatch(/<TrendBadge/);
  });

  test('HealthBar toujours présent', () => {
    expect(HEALTH_BAR).toMatch(/<HealthBar/);
  });

  test('CTA "Charger HELIOS" toujours présent dans état vide', () => {
    expect(HEALTH_BAR).toMatch(/Charger HELIOS/);
  });
});
