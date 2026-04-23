/**
 * SolPanel keyboard navigation — Sprint 1 Vague A phase A8
 *
 * Audit fresh §3 : SolPanel n'avait aucun `onKeyDown` pour ArrowUp/Down,
 * régression vs NavPanel main (L463). Fix : handler panel-level qui gère
 * Up/Down/Home/End + skip les items lockés (disabled).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');

describe('SolPanel keyboard navigation (A8)', () => {
  it('declares handlePanelKeyDown callback', () => {
    expect(src).toMatch(/const\s+handlePanelKeyDown\s*=\s*React\.useCallback/);
  });

  it('handles ArrowDown, ArrowUp, Home, End (4 keys)', () => {
    expect(src).toMatch(/ArrowDown/);
    expect(src).toMatch(/ArrowUp/);
    expect(src).toMatch(/['"]Home['"]/);
    expect(src).toMatch(/['"]End['"]/);
  });

  it('wires handler via onKeyDown on <aside>', () => {
    expect(src).toMatch(/onKeyDown=\{handlePanelKeyDown\}/);
  });

  it('F1 fix P0-B : queries ALL sol-panel-item buttons (locked items stay reachable)', () => {
    expect(src).toMatch(/button\.sol-panel-item['"]\)/);
    expect(src).not.toMatch(/button\.sol-panel-item:not\(\[disabled\]\)/);
  });

  it('F1 fix P1-4 : scrollIntoView({block:"nearest"}) after focus shift', () => {
    expect(src).toMatch(/scrollIntoView\(\s*\{\s*block:\s*['"]nearest['"]/);
  });

  it('uses Array.from + querySelectorAll (DOM flat list)', () => {
    expect(src).toMatch(/Array\.from\(\s*e\.currentTarget\.querySelectorAll/);
  });

  it('calls preventDefault on matched keys', () => {
    expect(src).toMatch(/e\.preventDefault\(\)/);
  });

  it('ArrowDown : clamp to buttons.length - 1', () => {
    expect(src).toMatch(/Math\.min\(idx \+ 1,\s*buttons\.length - 1\)/);
  });

  it('ArrowUp : clamp to 0', () => {
    expect(src).toMatch(/Math\.max\(idx - 1,\s*0\)/);
  });

  it('Home : focus first item', () => {
    expect(src).toMatch(/Home/);
    expect(src).toMatch(/next = 0/);
  });

  it('End : focus last item', () => {
    expect(src).toMatch(/buttons\.length - 1/);
  });

  it('no focus when empty list (guard `buttons.length === 0`)', () => {
    expect(src).toMatch(/buttons\.length === 0/);
  });
});
