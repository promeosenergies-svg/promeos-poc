/**
 * SolPanel Pins — intégration tests (Sprint 1 Vague B · B1.4)
 *
 * Source-guards sur SolPanel.jsx : wiring des imports, rendu
 * conditionnel section "Épinglés", helper PanelPinButton, CSS hover
 * reveal dans index.css.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const panelSrc = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');
const cssSrc = readFileSync(join(__dirname, '..', '..', '..', 'index.css'), 'utf-8');

describe('SolPanel — Pins integration (B1)', () => {
  it('imports Star icon from lucide-react', () => {
    expect(panelSrc).toMatch(/import\s*\{[^}]*\bStar\b[^}]*\}\s*from\s*['"]lucide-react['"]/);
  });

  it('imports pin API from utils/navPins (F3 : isPinned loop remplacé par pinnedSet)', () => {
    expect(panelSrc).toMatch(
      /import\s*\{[^}]*\bgetPins\b[^}]*\}\s*from\s*['"]\.\.\/\.\.\/utils\/navPins['"]/
    );
    expect(panelSrc).toMatch(/togglePin/);
    // F3 : isPinned n'est PLUS importé (remplacé par pinnedSet via useMemo)
    expect(panelSrc).not.toMatch(/\bisPinned\b/);
  });

  it('declares PanelPinButton helper component', () => {
    expect(panelSrc).toMatch(/function PanelPinButton\(/);
  });

  it('PanelPinButton has aria-label FR for both states (épingler/désépingler)', () => {
    expect(panelSrc).toMatch(/Épingler \$\{itemLabel\}/);
    expect(panelSrc).toMatch(/Désépingler \$\{itemLabel\}/);
  });

  it('PanelPinButton has aria-pressed + data-testid', () => {
    expect(panelSrc).toMatch(/aria-pressed=\{pinned\}/);
    // data-testid peut utiliser template literal OU string concat — check le motif
    expect(panelSrc).toMatch(/data-testid=\{[^}]*sol-panel-pin-[^}]*\}/);
  });

  it('PanelPinButton Star icon fills when pinned', () => {
    expect(panelSrc).toMatch(/fill=\{pinned \? 'currentColor' : 'none'\}/);
  });

  it('uses pinsVersion state to force re-render after toggle', () => {
    expect(panelSrc).toMatch(/\[pinsVersion,\s*setPinsVersion\]\s*=\s*React\.useState\(0\)/);
    expect(panelSrc).toMatch(/setPinsVersion\(\(v\)\s*=>\s*v\s*\+\s*1\)/);
  });

  it('handleTogglePin calls stopPropagation (F3 : preventDefault retiré — type="button" ne submit pas)', () => {
    expect(panelSrc).toMatch(/event\.stopPropagation\(\)/);
    // F3 : event.preventDefault retiré (redondant sur <button type="button">)
    expect(panelSrc).not.toMatch(/event\.preventDefault\(\)/);
  });

  it('F3 : allItems + pinnedSet memos extracted (DRY vs triple flatMap)', () => {
    expect(panelSrc).toMatch(/const allItems = React\.useMemo\(/);
    expect(panelSrc).toMatch(/const pinnedSet = React\.useMemo\(\s*\(\)\s*=>\s*new Set\(pins\)/);
    expect(panelSrc).toMatch(/pinnedItems/);
  });

  it('F3 : isPinned() loop remplacé par pinnedSet.has() (perf JSON.parse×N → 0)', () => {
    expect(panelSrc).toMatch(/pinnedSet\.has\(item\.to\)/);
    // Zéro appel direct à isPinned() dans le source (plus importé)
    expect(panelSrc).not.toMatch(/\bisPinned\(/);
  });

  it('renders Épinglés section only when pinnedItems.length > 0', () => {
    expect(panelSrc).toMatch(/pinnedItems\.length\s*>\s*0\s*&&/);
    // Le label "Épinglés" est rendu en JSX direct, sans quotes autour
    expect(panelSrc).toMatch(/Épinglés/);
  });

  it('Épinglés section has aria-label for SR', () => {
    expect(panelSrc).toMatch(/aria-label=["']Items épinglés["']/);
  });

  it('wraps item + pin button in .sol-panel-item-row (valid HTML, 2 sibling buttons)', () => {
    expect(panelSrc).toMatch(/className="sol-panel-item-row"/);
  });

  it('pin button rendered only when !locked (no pin on restricted items)', () => {
    expect(panelSrc).toMatch(/\{!locked && \(/);
  });

  it('button item has paddingRight: 32 to reserve space for absolute pin', () => {
    expect(panelSrc).toMatch(/paddingRight:\s*32/);
  });
});

describe('SolPanel — F1 fixes (a11y hit area + contraste + ordre)', () => {
  it('F1 : hit area PanelPinButton 24x24 (WCAG 2.5.5 AA, 44 AAA recommended)', () => {
    expect(panelSrc).toMatch(/width:\s*24\b/);
    expect(panelSrc).toMatch(/height:\s*24\b/);
  });

  it('F1 : icon Star size=14 (up from 12 pour lisibilité)', () => {
    expect(panelSrc).toMatch(/<Star\s+size=\{14\}/);
  });

  it('F1 : contraste non-pinné uses --sol-ink-500 (4.6:1 WCAG 1.4.11 pass)', () => {
    // Ancien : --sol-ink-400 (2.85:1 FAIL). Nouveau : --sol-ink-500 (4.6:1 OK).
    expect(panelSrc).toMatch(
      /color:\s*pinned\s*\?\s*['"]var\(--sol-attention-fg\)['"][\s\S]*?['"]var\(--sol-ink-500\)['"]/
    );
  });

  it('F1 : opacity 1 sur mobile OR pinned (découvrabilité tactile)', () => {
    expect(panelSrc).toMatch(/opacity:\s*pinned\s*\|\|\s*isMobile\s*\?\s*1\s*:\s*0/);
  });

  it('F1 : isMobile prop transmis aux 2 PanelPinButton', () => {
    const pinButtonUsages = panelSrc.match(/<PanelPinButton[\s\S]*?\/>/g) || [];
    expect(pinButtonUsages.length).toBeGreaterThanOrEqual(2);
    pinButtonUsages.forEach((usage) => {
      expect(usage).toMatch(/isMobile=\{isMobile\}/);
    });
  });

  it('F1 : data-testid slugifié (pas de / dans la valeur)', () => {
    expect(panelSrc).toMatch(/slugifyPin\(itemKey\)/);
    expect(panelSrc).toMatch(/function slugifyPin/);
  });

  it('F1 : ordre DOM Épinglés AVANT Récents AVANT NAV sections', () => {
    const idxPinned = panelSrc.indexOf('Section Épinglés');
    const idxRecents = panelSrc.indexOf('Section Récents');
    const idxNavMap = panelSrc.indexOf('{sections.map((section)');
    expect(idxPinned).toBeGreaterThan(0);
    expect(idxRecents).toBeGreaterThan(0);
    expect(idxNavMap).toBeGreaterThan(0);
    // Épinglés (fréquent) > Récents (récent) > NAV (structure)
    expect(idxPinned).toBeLessThan(idxRecents);
    expect(idxRecents).toBeLessThan(idxNavMap);
  });
});

describe('SolPanel pin CSS hover reveal (index.css)', () => {
  it('pin button is hidden (opacity:0) at rest, revealed on row hover/focus-within', () => {
    expect(cssSrc).toMatch(/\.sol-panel-item-row:hover\s+\.sol-panel-pin/);
    expect(cssSrc).toMatch(/\.sol-panel-item-row:focus-within\s+\.sol-panel-pin/);
  });

  it('pin button stays visible on its own hover/focus-visible', () => {
    expect(cssSrc).toMatch(/\.sol-panel-pin:hover/);
    expect(cssSrc).toMatch(/\.sol-panel-pin:focus-visible/);
  });

  it('reveal rule sets opacity to 1', () => {
    expect(cssSrc).toMatch(/opacity:\s*1\s*!important/);
  });
});
