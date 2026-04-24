/**
 * SolPanel Recents — integration source-guards (Sprint 1 Vague B · B2.3)
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const panelSrc = readFileSync(join(__dirname, '..', 'SolPanel.jsx'), 'utf-8');
const shellSrc = readFileSync(
  join(__dirname, '..', '..', '..', 'layout', 'SolAppShell.jsx'),
  'utf-8'
);

describe('SolPanel — Recents integration (B2)', () => {
  it('imports getRecents from utils/navRecent', () => {
    expect(panelSrc).toMatch(
      /import\s*\{\s*getRecents\s*\}\s*from\s*['"]\.\.\/\.\.\/utils\/navRecent['"]/
    );
  });

  it('declares RECENTS_DISPLAY_LIMIT constant', () => {
    expect(panelSrc).toMatch(/RECENTS_DISPLAY_LIMIT\s*=\s*\d+/);
  });

  it('memoizes recentsItems with sections + pins + location.pathname deps', () => {
    expect(panelSrc).toMatch(/recentsItems/);
    expect(panelSrc).toMatch(/\[sections,\s*pins,\s*location\.pathname\]/);
  });

  it('excludes current path + pinned + already-visible-in-sections', () => {
    expect(panelSrc).toMatch(/r\.path !== currentPath/);
    expect(panelSrc).toMatch(/!pinnedSet\.has\(r\.path\)/);
    expect(panelSrc).toMatch(/!currentSectionPaths\.has/);
  });

  it('falls back to stored label when path not in NAV_SECTIONS', () => {
    // Un recent peut pointer vers une page hidden (pas dans nav), on crée
    // un item minimal avec le label stocké.
    expect(panelSrc).toMatch(/if\s*\(!r\.label\)\s*return null/);
  });

  it('renders Récents section only when recentsItems.length > 0', () => {
    expect(panelSrc).toMatch(/recentsItems\.length\s*>\s*0\s*&&/);
    expect(panelSrc).toMatch(/Récents/);
  });

  it('Récents section has aria-label for SR', () => {
    expect(panelSrc).toMatch(/aria-label=["']Récemment visité["']/);
  });

  it('tracker fires with section_key="recents" on recent item click', () => {
    expect(panelSrc).toMatch(/handleItemClick\(item,\s*['"]recents['"]\)/);
  });
});

describe('SolAppShell — route tracking wiring (B2)', () => {
  it('imports useRouteTracker hook', () => {
    expect(shellSrc).toMatch(
      /import\s+useRouteTracker\s+from\s+['"]\.\.\/hooks\/useRouteTracker['"]/
    );
  });

  it('calls useRouteTracker() inside SolAppShell component', () => {
    expect(shellSrc).toMatch(/useRouteTracker\(\)/);
  });
});
