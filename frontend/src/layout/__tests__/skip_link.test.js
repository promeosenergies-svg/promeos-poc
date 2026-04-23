/**
 * SolAppShell skip link — Sprint 1 Vague A phase A7
 *
 * Audit fresh §1 : skip link `sr-only` + style inline `left:-9999` sans
 * focus-visible reveal → régression a11y vs shell legacy. Fix : classes
 * Tailwind `sr-only focus:not-sr-only focus:...` qui révèlent le lien
 * au focus clavier.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'SolAppShell.jsx'), 'utf-8');

describe('SolAppShell skip link (A7)', () => {
  it('targets #main-content', () => {
    expect(src).toMatch(/href=["']#main-content["']/);
  });

  it('uses sr-only class (hidden by default)', () => {
    expect(src).toMatch(/sol-skip-link[^"]*sr-only/);
  });

  it('reveals itself on focus via focus:not-sr-only', () => {
    expect(src).toMatch(/focus:not-sr-only/);
  });

  it('F2 fix P1-9 : positions visibly on focus avoiding rail (fixed top-3 left-[68px])', () => {
    expect(src).toMatch(/focus:fixed/);
    expect(src).toMatch(/focus:top-3/);
    // left-[68px] = rail 56px + gutter 12px (rail ne recouvre plus skip link sur mobile)
    expect(src).toMatch(/focus:left-\[68px\]/);
    expect(src).not.toMatch(/focus:left-3[^0-9]/);
  });

  it('has focus-visible ring (keyboard users)', () => {
    expect(src).toMatch(/focus-visible:ring-2/);
    expect(src).toMatch(/focus-visible:ring-blue-/);
  });

  it('z-index above rail and panel (z-[300])', () => {
    expect(src).toMatch(/focus:z-\[300\]/);
  });

  it('does NOT use the old broken pattern (left:-9999 inline)', () => {
    // The broken style was: style={{ position:'absolute', left:-9999, top:0 }}
    expect(src).not.toMatch(/left:\s*-9999/);
  });

  it('text en français', () => {
    expect(src).toMatch(/Aller au contenu principal/);
  });

  it('#main-content anchor exists on the main element', () => {
    expect(src).toMatch(/id=["']main-content["']/);
  });
});
