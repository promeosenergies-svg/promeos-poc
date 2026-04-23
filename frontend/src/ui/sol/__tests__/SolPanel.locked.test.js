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

  it('button is disabled + aria-disabled when locked', () => {
    expect(src).toMatch(/disabled=\{locked\}/);
    expect(src).toMatch(/aria-disabled=\{locked \|\| undefined\}/);
  });

  it('button onClick is guarded : undefined when locked', () => {
    // A10 : onClick délègue à handleItemClick pour tracking deep_link.
    expect(src).toMatch(/onClick=\{locked \? undefined : \(\) => handleItemClick/);
  });

  it('button has title={LOCKED_TOOLTIP} when locked', () => {
    expect(src).toMatch(/title=\{locked \? LOCKED_TOOLTIP : undefined\}/);
  });

  it('button aria-label includes label + tooltip when locked', () => {
    expect(src).toMatch(
      /aria-label=\{locked \? `\$\{item\.label\} — \$\{LOCKED_TOOLTIP\}` : undefined\}/
    );
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

  it('locked items use cursor not-allowed + reduced opacity', () => {
    expect(src).toMatch(/cursor:\s*locked \? 'not-allowed' : 'pointer'/);
    expect(src).toMatch(/opacity:\s*locked \? 0\.55 : 1/);
  });

  it('unauthenticated users see items with locked: false (no filtering)', () => {
    expect(src).toMatch(
      /items:\s*\(section\.items \|\| \[\]\)\.map\(\(item\) => \(\{ \.\.\.item, locked: false \}\)\)/
    );
  });
});
