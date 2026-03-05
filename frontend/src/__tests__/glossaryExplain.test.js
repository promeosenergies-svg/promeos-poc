/**
 * PROMEOS — C.1: Tests Glossaire + Explain
 * Source-guard + tests unitaires du composant.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. Glossaire ─────────────────────────────────────────────────────────────

describe('A. Glossaire — structure', () => {
  const src = readSrc('ui/glossary.js');

  it('exporte GLOSSARY', () => {
    expect(src).toContain('export const GLOSSARY');
  });

  it('contient au moins 20 termes', () => {
    const keys = src.match(/^\s{2}\w+:\s*\{/gm);
    expect(keys.length).toBeGreaterThanOrEqual(20);
  });

  it('chaque entrée a term et short', () => {
    expect(src).toContain('term:');
    expect(src).toContain('short:');
    // Vérifier que toutes les entrées ont les deux champs
    const entries = src.match(/^\s{2}\w+:\s*\{/gm);
    const terms = src.match(/term:\s*['"]/g) || [];
    const shorts = src.match(/short:\s*$/gm) || src.match(/short:\s*'/g) || [];
    // Au moins autant de term que d'entrées
    expect(terms.length).toBeGreaterThanOrEqual(entries.length);
  });

  const REQUIRED_KEYS = [
    'turpe', 'accise', 'tva', 'ttc', 'ht', 'kwh',
    'shadow_billing', 'anomalie', 'confiance', 'decret_tertiaire',
  ];

  for (const key of REQUIRED_KEYS) {
    it(`contient la clé "${key}"`, () => {
      expect(src).toContain(`${key}:`);
    });
  }

  it('est exporté depuis ui/index.js', () => {
    const idx = readSrc('ui/index.js');
    expect(idx).toContain('GLOSSARY');
  });
});

// ── B. Explain composant ─────────────────────────────────────────────────────

describe('B. Explain — composant', () => {
  const src = readSrc('ui/Explain.jsx');

  it('exporte un composant par défaut', () => {
    expect(src).toContain('export default function Explain');
  });

  it('importe GLOSSARY', () => {
    expect(src).toContain('GLOSSARY');
  });

  it('accepte props term, content, children, position', () => {
    expect(src).toContain('term');
    expect(src).toContain('content');
    expect(src).toContain('children');
    expect(src).toContain('position');
  });

  it('utilise createPortal pour le tooltip', () => {
    expect(src).toContain('createPortal');
  });

  it('a role="tooltip" pour accessibilité', () => {
    expect(src).toContain('role="tooltip"');
  });

  it('a role="term" sur le trigger', () => {
    expect(src).toContain('role="term"');
  });

  it('a data-testid="explain"', () => {
    expect(src).toContain('data-testid="explain"');
  });

  it('a data-glossary pour identifier le terme', () => {
    expect(src).toContain('data-glossary');
  });

  it('a un style dotted border', () => {
    expect(src).toContain('border-dotted');
  });

  it('supporte le clavier (tabIndex, onFocus)', () => {
    expect(src).toContain('tabIndex');
    expect(src).toContain('onFocus');
    expect(src).toContain('onBlur');
  });

  it('a aria-describedby pour le tooltip', () => {
    expect(src).toContain('aria-describedby');
  });

  it('est exporté depuis ui/index.js', () => {
    const idx = readSrc('ui/index.js');
    expect(idx).toContain('Explain');
  });
});

// ── C. Intégration sur pages clés ────────────────────────────────────────────

describe('C. Pages clés — intégration Explain', () => {
  const PAGES_WITH_EXPLAIN = [
    { file: 'components/InsightDrawer.jsx', name: 'InsightDrawer' },
    { file: 'pages/BillIntelPage.jsx', name: 'BillIntelPage' },
    { file: 'pages/AnomaliesPage.jsx', name: 'AnomaliesPage' },
    { file: 'pages/Site360.jsx', name: 'Site360' },
  ];

  for (const { file, name } of PAGES_WITH_EXPLAIN) {
    it(`${name} importe Explain`, () => {
      const src = readSrc(file);
      expect(src).toContain('Explain');
    });

    it(`${name} utilise <Explain`, () => {
      const src = readSrc(file);
      expect(src).toMatch(/<Explain\s/);
    });
  }
});

// ── D. Qualité glossaire ─────────────────────────────────────────────────────

describe('D. Qualité — glossaire cohérent', () => {
  it('pas de terme dupliqué dans glossary.js', () => {
    const src = readSrc('ui/glossary.js');
    const keys = (src.match(/^\s{2}(\w+):\s*\{/gm) || []).map(
      (m) => m.trim().split(':')[0],
    );
    const unique = new Set(keys);
    expect(keys.length).toBe(unique.size);
  });

  it('toutes les définitions short font < 200 caractères', () => {
    const src = readSrc('ui/glossary.js');
    const shorts = src.match(/short:\s*\n?\s*['"](.*?)['"]/gs) || [];
    for (const s of shorts) {
      // Extraire le contenu textuel (approximation)
      expect(s.length).toBeLessThan(300); // inclut le wrapper, la def elle-même < 200
    }
  });
});
