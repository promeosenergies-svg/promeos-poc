/**
 * PROMEOS — C.2: Tests Mode Simple / Expert
 * Source-guard : contexte, toggle, persistance, sections conditionnelles.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// Recursively collect .jsx files from a directory
function collectJsx(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const st = statSync(full);
    if (st.isDirectory() && !entry.startsWith('__')) {
      files.push(...collectJsx(full));
    } else if (entry.endsWith('.jsx')) {
      files.push(full);
    }
  }
  return files;
}

// ── A. ExpertModeContext ─────────────────────────────────────────────────────

describe('A. ExpertModeContext — infrastructure', () => {
  const src = readSrc('contexts/ExpertModeContext.jsx');

  it('exporte ExpertModeProvider', () => {
    expect(src).toContain('export function ExpertModeProvider');
  });

  it('exporte useExpertMode hook', () => {
    expect(src).toContain('export function useExpertMode');
  });

  it('persiste dans localStorage', () => {
    expect(src).toContain('localStorage');
    expect(src).toContain('promeos_expert');
  });

  it('retourne isExpert et toggleExpert', () => {
    expect(src).toContain('isExpert');
    expect(src).toContain('toggleExpert');
  });

  it('utilise createContext', () => {
    expect(src).toContain('createContext');
  });

  it('throw si utilisé hors provider', () => {
    expect(src).toMatch(/throw.*Error/);
  });
});

// ── B. Toggle dans le layout ────────────────────────────────────────────────

describe('B. Toggle — visible dans le header', () => {
  const shell = readSrc('layout/AppShell.jsx');

  it('AppShell importe useExpertMode', () => {
    expect(shell).toContain('useExpertMode');
  });

  it('AppShell a un Toggle pour le mode expert', () => {
    expect(shell).toContain('toggleExpert');
    expect(shell).toMatch(/Toggle|toggle/);
  });

  it('AppShell affiche le label "Expert"', () => {
    expect(shell).toContain('Expert');
  });
});

// ── C. Provider dans App.jsx ────────────────────────────────────────────────

describe('C. Provider — wraps entire app', () => {
  const app = readSrc('App.jsx');

  it('App importe ExpertModeProvider', () => {
    expect(app).toContain('ExpertModeProvider');
  });

  it('App wraps children avec ExpertModeProvider', () => {
    expect(app).toMatch(/<ExpertModeProvider/);
  });
});

// ── D. Navigation filtre par expert ─────────────────────────────────────────

describe('D. Navigation — expert-only filtering', () => {
  it('NavPanel filtre les items expertOnly', () => {
    const src = readSrc('layout/NavPanel.jsx');
    expect(src).toContain('expertOnly');
    expect(src).toContain('isExpert');
  });

  it('NavRail uses getOrderedModules (role-based + expert filtering)', () => {
    const src = readSrc('layout/NavRail.jsx');
    expect(src).toContain('getOrderedModules');
    expect(src).toContain('isExpert');
  });

  it('NavRegistry a des items expertOnly', () => {
    const src = readSrc('layout/NavRegistry.js');
    expect(src).toContain('expertOnly');
  });
});

// ── E. Pages critiques — sections expert ────────────────────────────────────

describe('E. Pages critiques — isExpert conditionnel', () => {
  const CRITICAL_PAGES = [
    { file: 'pages/Cockpit.jsx', name: 'Cockpit' },
    // Patrimoine V2 : conso toujours visible (plus de gate isExpert)
    { file: 'pages/ConformitePage.jsx', name: 'ConformitePage' },
    { file: 'pages/BillIntelPage.jsx', name: 'BillIntelPage' },
    { file: 'pages/MonitoringPage.jsx', name: 'MonitoringPage' },
  ];

  for (const { file, name } of CRITICAL_PAGES) {
    it(`${name} importe useExpertMode`, () => {
      const src = readSrc(file);
      expect(src).toContain('useExpertMode');
    });

    it(`${name} a des sections conditionnelles isExpert`, () => {
      const src = readSrc(file);
      // Must have at least one {isExpert && pattern
      expect(src).toMatch(/isExpert\s*&&/);
    });
  }
});

// ── F. Adoption large ───────────────────────────────────────────────────────

describe('F. Adoption — expert mode utilisé largement', () => {
  it('au moins 10 fichiers utilisent useExpertMode', () => {
    const pages = collectJsx(join(SRC, 'pages'));
    const components = collectJsx(join(SRC, 'components'));
    const layout = collectJsx(join(SRC, 'layout'));
    const all = [...pages, ...components, ...layout];

    let count = 0;
    for (const f of all) {
      const content = readFileSync(f, 'utf-8');
      if (content.includes('useExpertMode') || content.includes('isExpert')) {
        count++;
      }
    }
    expect(count).toBeGreaterThanOrEqual(10);
  });

  it('InsightDrawer a des sections expert', () => {
    const src = readSrc('components/InsightDrawer.jsx');
    expect(src).toContain('isExpert');
    expect(src).toMatch(/isExpert\s*&&/);
  });
});

// ── G. Pas de régression — mode simple fonctionnel ──────────────────────────

describe('G. Mode simple — contenu de base toujours présent', () => {
  it('Cockpit a du contenu hors isExpert', () => {
    const src = readSrc('pages/Cockpit.jsx');
    // Page has content outside of isExpert blocks
    expect(src).toContain('PageShell');
    expect(src).toContain('Card');
  });

  it('BillIntelPage a du contenu hors isExpert', () => {
    const src = readSrc('pages/BillIntelPage.jsx');
    expect(src).toContain('PageShell');
    expect(src).toContain('Anomalies');
  });

  it('Patrimoine a du contenu hors isExpert', () => {
    const src = readSrc('pages/Patrimoine.jsx');
    expect(src).toContain('PageShell');
  });
});
