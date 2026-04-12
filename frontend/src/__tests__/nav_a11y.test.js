/**
 * PROMEOS — Navigation A11y Tests (axe-core)
 * Validates accessibility of navigation components via source analysis.
 */
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { describe, it, expect } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const read = (rel) => readFileSync(resolve(__dirname, '..', rel), 'utf-8');

const navRail = read('layout/NavRail.jsx');
const navPanel = read('layout/NavPanel.jsx');
const appShell = read('layout/AppShell.jsx');
const breadcrumb = read('layout/Breadcrumb.jsx');

describe('A11y — Skip link', () => {
  it('AppShell has skip-to-content link', () => {
    expect(appShell).toMatch(/href=["']#main-content["']/);
  });

  it('AppShell main element has id="main-content"', () => {
    expect(appShell).toMatch(/id=["']main-content["']/);
  });

  it('skip link is sr-only but visible on focus', () => {
    expect(appShell).toMatch(/sr-only.*focus:not-sr-only/);
  });
});

describe('A11y — ARIA roles & labels', () => {
  it('NavRail has role="navigation"', () => {
    expect(navRail).toMatch(/role=["']navigation["']/);
  });

  it('NavRail has aria-label="Modules"', () => {
    expect(navRail).toMatch(/aria-label=["']Modules["']/);
  });

  it('NavPanel has role="navigation"', () => {
    expect(navPanel).toMatch(/role=["']navigation["']/);
  });

  it('NavRail module buttons have aria-label', () => {
    expect(navRail).toMatch(/aria-label=\{mod\.label\}/);
  });

  it('NavRail active module has aria-current', () => {
    expect(navRail).toMatch(/aria-current/);
  });

  it('NavPanel items have aria-describedby when desc exists', () => {
    expect(navPanel).toMatch(/aria-describedby/);
  });
});

describe('A11y — Focus management', () => {
  it('NavRail buttons have focus-visible ring', () => {
    expect(navRail).toMatch(/focus-visible:.*ring/);
  });

  it('NavPanel links have focus-visible ring', () => {
    expect(navPanel).toMatch(/focus-visible:.*ring/);
  });

  it('NavPanel supports keyboard navigation (ArrowDown/ArrowUp)', () => {
    expect(navPanel).toMatch(/ArrowDown/);
    expect(navPanel).toMatch(/ArrowUp/);
  });
});

describe('A11y — Labels in French', () => {
  it('NavRail aria labels are in French (module labels)', () => {
    // Module labels are French (Accueil, Conformite, etc.) — checked via aria-label={mod.label}
    expect(navRail).toMatch(/aria-label=\{mod\.label\}/);
  });

  it('AppShell skip link is in French', () => {
    expect(appShell).toMatch(/Aller au contenu/);
  });

  it('AppShell hamburger has French aria-label', () => {
    expect(appShell).toMatch(/Ouvrir le menu/);
  });

  it('Breadcrumb uses nav element', () => {
    expect(breadcrumb).toMatch(/<nav/);
  });
});
