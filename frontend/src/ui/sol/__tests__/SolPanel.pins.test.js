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

  it('imports pin API from utils/navPins', () => {
    expect(panelSrc).toMatch(
      /import\s*\{[^}]*\bgetPins\b[^}]*\}\s*from\s*['"]\.\.\/\.\.\/utils\/navPins['"]/
    );
    expect(panelSrc).toMatch(/togglePin/);
    expect(panelSrc).toMatch(/isPinned/);
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

  it('handleTogglePin calls preventDefault + stopPropagation', () => {
    expect(panelSrc).toMatch(/event\.preventDefault\(\)/);
    expect(panelSrc).toMatch(/event\.stopPropagation\(\)/);
  });

  it('resolves pinnedItems from current sections flatMap', () => {
    expect(panelSrc).toMatch(/pinnedItems/);
    expect(panelSrc).toMatch(/sections\.flatMap\(\(s\)\s*=>\s*s\.items/);
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
