/**
 * Cleanup sidebar Conformité (2026-05-24) — source-guard tests pour la
 * barre de chips réglementaires interne à /conformite.
 *
 * Doctrine §6.2 hub unique : la sidebar n'affiche plus que /conformite,
 * et la navigation entre obligations (DT / BACS / APER / SMÉ / BEGES) se
 * fait via les chips internes (?regulation=...). Aucun nouveau menu :
 * la barre de chips est inline (filtre), pas un second tab strip.
 *
 * Pattern source-guard (readFileSync + regex) aligné sur
 * conformiteUxUpgrade.test.js : pas de mock DOM nécessaire.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../');
const readSrc = (...parts) => readFileSync(resolve(root, 'src', ...parts), 'utf-8');

describe('ConformitePage — barre de chips réglementaires', () => {
  const code = readSrc('pages', 'ConformitePage.jsx');

  it("expose REGULATION_CHIPS avec 5 entrées (Vue d'ensemble + 4 obligations)", () => {
    expect(code).toMatch(/REGULATION_CHIPS\s*=\s*\[/);
    // 5 entrées attendues
    const block = code.match(/REGULATION_CHIPS\s*=\s*\[([\s\S]*?)\];/);
    expect(block).not.toBeNull();
    // chaque entrée commence par `{ key:`
    const entries = block[1].match(/\{\s*key:/g) || [];
    expect(entries.length).toBe(5);
  });

  it("inclut les labels Vue d'ensemble, Décret Tertiaire / OPERAT, BACS, APER, SMÉ / BEGES", () => {
    expect(code).toContain('label: "Vue d\'ensemble"');
    expect(code).toContain("label: 'Décret Tertiaire / OPERAT'");
    expect(code).toContain("label: 'BACS'");
    expect(code).toContain("label: 'APER'");
    expect(code).toContain("label: 'SMÉ / BEGES'");
  });

  it('rend une barre testable via data-testid="regulation-chips-bar"', () => {
    expect(code).toContain('data-testid="regulation-chips-bar"');
  });

  it('rend une chip par regulation via data-testid="regulation-chip-*"', () => {
    expect(code).toMatch(/data-testid=\{?\s*`regulation-chip-\$\{[^}]+\}`\s*\}?/);
  });

  it("utilise role=tablist/tab + aria-selected pour l'a11y", () => {
    expect(code).toContain('role="tablist"');
    expect(code).toContain('role="tab"');
    expect(code).toContain('aria-selected={isActive}');
  });

  it('binde le clic chip sur le query param ?regulation= (URL state, pas nouveau menu)', () => {
    // Pas de nouveau composant TabBar/Sidebar — juste setSearchParams.
    expect(code).toMatch(/setSearchParams\(\s*next/);
    expect(code).toMatch(/next\.set\('regulation'/);
    expect(code).toMatch(/next\.delete\('regulation'/);
  });

  it('étend REGULATION_FILTER_MAP audit-sme avec beges + bilan_ges', () => {
    expect(code).toMatch(/'audit-sme':\s*\[[^\]]*'beges'/);
    expect(code).toMatch(/'audit-sme':\s*\[[^\]]*'bilan_ges'/);
  });

  it('compte les obligations par chip (UI feedback)', () => {
    expect(code).toContain('obligations.filter((o)');
    expect(code).toMatch(/count\s*>\s*0\s*&&/);
  });

  it("track event analytics au clic chip (track('conformite_regulation_chip'))", () => {
    expect(code).toContain("track('conformite_regulation_chip'");
  });
});

describe('ConformitePage — sidebar reste un hub unique (anti-régression)', () => {
  // Ne pas réintroduire les sous-items /conformite/tertiaire et /conformite/aper
  // dans la sidebar : c'est exactement ce que ce sprint nettoie.
  const navReg = readSrc('layout', 'NavRegistry.js');

  it('NavRegistry conformite section ne contient PAS de bouton vers /conformite/tertiaire', () => {
    // Chercher le bloc NAV_SECTIONS conformite et vérifier qu'il n'a qu'un item
    // pointant sur /conformite (et pas /conformite/tertiaire ou /conformite/aper).
    const confoBlock = navReg.match(/module: 'conformite',[\s\S]*?items: \[([\s\S]*?)\],?\s*\},/);
    expect(confoBlock).not.toBeNull();
    const items = confoBlock[1];
    // /conformite/tertiaire et /conformite/aper ne doivent PAS apparaître dans la sidebar
    expect(items).not.toMatch(/to:\s*['"]\/conformite\/tertiaire['"]/);
    expect(items).not.toMatch(/to:\s*['"]\/conformite\/aper['"]/);
    // /conformite reste présent (hub)
    expect(items).toMatch(/to:\s*['"]\/conformite['"]/);
  });

  it('HIDDEN_PAGES indexe /conformite/tertiaire et /conformite/aper (deep-link)', () => {
    // Doctrine §6.2 : pages cachées de sidebar mais accessibles via ⌘K.
    expect(navReg).toMatch(/to:\s*['"]\/conformite\/tertiaire['"]/);
    expect(navReg).toMatch(/to:\s*['"]\/conformite\/aper['"]/);
  });

  it('aucun menu fantôme ACC / PMO / Partner Hub dans NavRegistry', () => {
    // Garde-fou doctrine cardinale : pas un hub Zapier, pas une PMO ACC.
    expect(navReg).not.toMatch(/label:\s*['"][^'"]*\bACC\b/);
    expect(navReg).not.toMatch(/label:\s*['"][^'"]*Partner Hub/i);
    expect(navReg).not.toMatch(/label:\s*['"][^'"]*PMO/);
  });
});
