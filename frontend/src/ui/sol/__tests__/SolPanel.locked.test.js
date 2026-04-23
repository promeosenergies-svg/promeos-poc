/**
 * SolPanel — badge cadenas sur items 403 (Sprint 1 Vague A phase A3)
 *
 * Au lieu de masquer les items pour les rôles restreints, SolPanel
 * affiche un cadenas + tooltip → UX transparente et potentiel upsell.
 *
 * Source-guard : vérifie le rendu conditionnel locked/unlocked et le
 * a11y associé (disabled, aria-disabled, title, aria-label).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');

describe('SolPanel — locked badge on restricted items (A3)', () => {
  it('imports Lock icon from lucide-react', () => {
    expect(src).toMatch(/import\s*\{\s*Lock\s*\}\s*from\s*['"]lucide-react['"]/);
  });

  it('declares LOCKED_TOOLTIP constant (FR)', () => {
    expect(src).toMatch(/const\s+LOCKED_TOOLTIP\s*=\s*['"]Module non inclus dans votre rôle\./);
  });

  it('builds items with `locked: boolean` flag instead of filtering them out', () => {
    // Map returns {...item, locked: ...} — no longer .filter()
    expect(src).toMatch(/locked:\s*!\s*hasPermission\('admin'\)/);
    expect(src).toMatch(/locked:\s*!allowed/);
    expect(src).toMatch(/locked:\s*false/); // fallback for items without module
  });

  it('still filters out empty sections after locked mapping', () => {
    expect(src).toMatch(/section\.items\.length\s*>\s*0/);
  });

  it('button is NOT HTML-disabled (F1 fix : stays focusable)', () => {
    expect(src).not.toMatch(/disabled=\{locked\}/);
  });

  it('button uses aria-disabled for ARIA state (WAI-ARIA canonical pattern)', () => {
    expect(src).toMatch(/aria-disabled=\{locked \|\| undefined\}/);
  });

  it('button onClick is guarded : undefined when locked', () => {
    // A10 : onClick délègue à handleItemClick pour tracking deep_link.
    expect(src).toMatch(/onClick=\{locked \? undefined : \(\) => handleItemClick/);
  });

  it('button has title={LOCKED_TOOLTIP} when locked (mouse hover tooltip)', () => {
    expect(src).toMatch(/title=\{locked \? LOCKED_TOOLTIP : undefined\}/);
  });

  it('sr-only span provides context to screen readers (why locked)', () => {
    expect(src).toMatch(/<span className="sr-only">— \{LOCKED_TOOLTIP\}<\/span>/);
  });

  it('aria-current is cleared when locked (not misleading)', () => {
    expect(src).toMatch(/aria-current=\{isActive && !locked \? 'page' : undefined\}/);
  });

  it('button has data-locked attribute (testability hook)', () => {
    expect(src).toMatch(/data-locked=\{locked \|\| undefined\}/);
  });

  it('button has is-locked class modifier when locked', () => {
    expect(src).toMatch(/\$\{locked \? ' is-locked' : ''\}/);
  });

  it('renders Lock icon only when locked, with data-testid hook', () => {
    expect(src).toMatch(/\{locked && \(/);
    expect(src).toMatch(/<Lock\s+size=\{12\}/);
    expect(src).toMatch(/data-testid=["']sol-panel-item-lock["']/);
    expect(src).toMatch(/aria-hidden=["']true["']/);
  });

  it('locked items use cursor not-allowed (mouse visual hint)', () => {
    expect(src).toMatch(/cursor:\s*['"]not-allowed['"]/);
  });

  it('no opacity:0.55 on locked items (WCAG 1.4.3 FAIL at 1.6:1 contrast)', () => {
    expect(src).not.toMatch(/opacity:\s*locked \? 0\.55/);
  });

  it('locked text uses --sol-ink-500 via getItemVisuals (4.6:1 WCAG AA)', () => {
    expect(src).toMatch(/getItemVisuals/);
    expect(src).toMatch(/color:\s*['"]var\(--sol-ink-500\)['"]/);
  });

  it('Lock icon uses --sol-ink-500 (WCAG 1.4.11 non-text 3:1 min)', () => {
    expect(src).toMatch(/<Lock[\s\S]*?color:\s*'var\(--sol-ink-500\)'/);
  });

  it('unauthenticated users see items with locked: false (no filtering)', () => {
    expect(src).toMatch(
      /items:\s*\(section\.items \|\| \[\]\)\.map\(\(item\) => \(\{ \.\.\.item, locked: false \}\)\)/
    );
  });
});
