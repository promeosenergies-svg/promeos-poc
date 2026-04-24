/**
 * SolPanel + useRouteTracker + SolAppShell runtime guards — F4 fixes
 *
 * Agent tests Sprint 1 Vague B a identifié 4 P0 faux négatifs où un bug
 * runtime passerait les source-guards existants. Faute de RTL installé
 * dans le projet (convention source-guards stricte), on renforce les
 * regex pour verrouiller les patterns structurels complets plutôt que
 * la présence de chaînes.
 *
 * Références :
 *   - Agent tests P0.1 : 2 useEffect `[location.pathname]` non discriminés
 *   - Agent tests P0.2 : ordre DOM Épinglés/Récents (déjà fixé F1)
 *   - Agent tests P0.3 : useRouteTracker guard EXCLUDED_PATHS non-comportemental
 *   - Agent tests P0.4 : pinsVersion re-render non-comportemental
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

const read = (p) => readFileSync(join(root, p), 'utf-8');

describe('F4 P0.1 · SolAppShell — drawer close useEffect NOT confused with trackRouteChange', () => {
  const src = read('layout/SolAppShell.jsx');

  it('le useEffect drawer-close a setMobileDrawerOpen(false) dans le body + dep [location.pathname]', () => {
    // Regex atomique : le bloc useEffect complet doit contenir
    // setMobileDrawerOpen(false) et l'array de deps [location.pathname].
    // Un refacto qui supprimerait le useEffect drawer-close mais laisserait
    // trackRouteChange ferait échouer ce test.
    const useEffectBlocks = src.matchAll(
      /useEffect\(\s*\(\)\s*=>\s*\{[\s\S]*?\},\s*\[location\.pathname\]\)/g
    );
    const blocks = Array.from(useEffectBlocks, (m) => m[0]);
    // Il doit y avoir AU MOINS 2 useEffect avec ce dep (drawer-close + trackRouteChange)
    expect(blocks.length).toBeGreaterThanOrEqual(2);
    // Au moins un des deux doit appeler setMobileDrawerOpen(false)
    const hasDrawerClose = blocks.some((b) => /setMobileDrawerOpen\(false\)/.test(b));
    expect(hasDrawerClose).toBe(true);
    // Au moins un doit appeler trackRouteChange (analytics)
    const hasTracker = blocks.some((b) => /trackRouteChange/.test(b));
    expect(hasTracker).toBe(true);
  });

  it('drawer close useEffect dépend uniquement de [location.pathname] (pas de deps supplémentaires)', () => {
    const closeBlock = src.match(
      /useEffect\(\s*\(\)\s*=>\s*\{\s*setMobileDrawerOpen\(false\);?\s*\},\s*(\[[^\]]+\])\)/
    );
    expect(closeBlock).toBeTruthy();
    expect(closeBlock[1]).toBe('[location.pathname]');
  });
});

describe('F4 P0.3 · useRouteTracker — exclusion early-return comportementale', () => {
  const src = read('hooks/useRouteTracker.js');

  it('EXCLUDED_PATHS est un Set avec entrées strictes', () => {
    expect(src).toMatch(/const EXCLUDED_PATHS\s*=\s*new Set\(\[[^\]]+\]\)/);
    expect(src).toMatch(/['"]\/['"]/);
    expect(src).toMatch(/['"]\/login['"]/);
    expect(src).toMatch(/['"]\/_sol_showcase['"]/);
  });

  it("useEffect contient un early-return AVANT l'appel addRecent (comportement effectif)", () => {
    // Regex atomique : le useEffect doit avoir la séquence
    // if (EXCLUDED_PATHS.has(pathname)) return;  PUIS  addRecent(...)
    // Un bug du type `if (EXCLUDED_PATHS.has(pathname)) /* pas de return */`
    // ou `return null` au lieu de `return` serait détecté.
    const useEffectBlock = src.match(/useEffect\(\s*\(\)\s*=>\s*\{([\s\S]*?)\}\s*,\s*\[/);
    expect(useEffectBlock).toBeTruthy();
    const body = useEffectBlock[1];
    const guardIndex = body.search(/if\s*\(\s*EXCLUDED_PATHS\.has\(pathname\)\s*\)\s*return\s*;/);
    const addRecentIndex = body.search(/addRecent\(/);
    expect(guardIndex).toBeGreaterThan(-1);
    expect(addRecentIndex).toBeGreaterThan(-1);
    expect(guardIndex).toBeLessThan(addRecentIndex);
  });
});

describe('F4 P0.4 · SolPanel — pinsVersion incrément effectif', () => {
  const src = read('ui/sol/SolPanel.jsx');

  it('handleTogglePin appelle togglePin PUIS incrémente pinsVersion via updater function', () => {
    // Regex atomique : vérifie que l'updater est bien `(v) => v + 1`
    // (pas `0`, pas `v`, pas `v - 1`). Un bug du type `setPinsVersion(0)`
    // casserait le re-render forcé mais passerait un test trop laxe.
    const handler = src.match(
      /handleTogglePin\s*=\s*React\.useCallback\(\s*\([^)]*\)\s*=>\s*\{([\s\S]*?)\},\s*\[\]\)/
    );
    expect(handler).toBeTruthy();
    const body = handler[1];
    // 1. togglePin(itemKey) présent
    expect(body).toMatch(/togglePin\(itemKey\)/);
    // 2. setPinsVersion appelé AVEC une function qui fait v + 1 (pas constante)
    expect(body).toMatch(/setPinsVersion\(\s*\(\s*v\s*\)\s*=>\s*v\s*\+\s*1\s*\)/);
  });

  it('le memo pins dépend bien de pinsVersion (pas [] stable)', () => {
    const memo = src.match(
      /const pins = React\.useMemo\(\s*\(\)\s*=>\s*getPins\(\),\s*\n\s*\/\/[^\n]*\n\s*(\[[^\]]+\])\s*\)/
    );
    expect(memo).toBeTruthy();
    expect(memo[1]).toMatch(/\[pinsVersion\]/);
  });
});

describe('F4 · Drawer onClose invariant (3 vecteurs equivalents)', () => {
  const src = read('ui/Drawer.jsx');

  it('Escape handler appelle onClose()', () => {
    expect(src).toMatch(/e\.key\s*===\s*['"]Escape['"][\s\S]*?onClose\(\)/);
  });

  it('overlay click appelle onClose()', () => {
    // <div className="absolute inset-0 bg-black/40 ..." onClick={onClose} />
    expect(src).toMatch(/className="absolute inset-0 bg-black\/40[\s\S]*?onClick=\{onClose\}/);
  });

  it('close button (title ou no-title) appelle onClose()', () => {
    const closeButtons = src.match(/aria-label="Fermer"/g) || [];
    // Au moins 2 occurrences : une dans le header conditionnel (title truthy)
    // + une dans le bloc alternatif (title falsy, bouton absolute)
    expect(closeButtons.length).toBeGreaterThanOrEqual(2);
    // Les 2 boutons ont bien onClick={onClose}
    const closeBlocks = src.match(/onClick=\{onClose\}/g) || [];
    expect(closeBlocks.length).toBeGreaterThanOrEqual(3); // overlay + 2 X buttons
  });
});
