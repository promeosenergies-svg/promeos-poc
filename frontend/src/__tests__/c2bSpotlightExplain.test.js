/**
 * PROMEOS — C.2b: Tests DemoSpotlight + Explain 12 termes + smoke
 * Source-guard : readFileSync + regex.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { GLOSSARY } from '../ui/glossary';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. Glossaire : 12 termes C.2b présents ──────────────────────────────────

const C2B_TERMS = [
  'risque_financier',
  'worst_sites',
  'off_hours_ratio',
  'gaspillage_estime',
  'ths_adoption',
  'severite',
  'finding',
  'report_pct',
  'effort_score',
  'data_confidence',
  'statut_conformite',
  'distribution_sites',
];

describe('A. Glossaire — 12 termes C.2b', () => {
  for (const key of C2B_TERMS) {
    it(`GLOSSARY contient "${key}"`, () => {
      expect(GLOSSARY[key]).toBeDefined();
      expect(GLOSSARY[key].term).toBeTruthy();
      expect(GLOSSARY[key].short).toBeTruthy();
    });
  }
});

// ── B. Explain présent dans les 5 fichiers cibles ────────────────────────────

const EXPLAIN_FILES = [
  {
    file: 'pages/Cockpit.jsx',
    name: 'Cockpit',
    terms: ['risque_financier', 'statut_conformite', 'distribution_sites', 'effort_score'],
  },
  {
    file: 'pages/MonitoringPage.jsx',
    name: 'MonitoringPage',
    terms: ['off_hours_ratio', 'gaspillage_estime', 'data_confidence', 'severite'],
  },
  {
    file: 'pages/ConformitePage.jsx',
    name: 'ConformitePage',
    terms: ['statut_conformite', 'finding', 'report_pct', 'severite'],
  },
  {
    file: 'pages/PurchasePage.jsx',
    name: 'PurchasePage',
    terms: ['ths_adoption', 'effort_score', 'data_confidence'],
  },
  {
    file: 'pages/Dashboard.jsx',
    name: 'Dashboard',
    terms: ['patrimoine', 'worst_sites'],
  },
];

describe('B. Explain — intégration dans 5 fichiers', () => {
  for (const { file, name, terms } of EXPLAIN_FILES) {
    it(`${name} importe Explain`, () => {
      const src = readSrc(file);
      expect(src).toContain('Explain');
    });

    for (const term of terms) {
      it(`${name} a term="${term}"`, () => {
        const src = readSrc(file);
        expect(src).toContain(`term="${term}"`);
      });
    }
  }
});

// ── C. Chaque term="x" dans les fichiers existe dans GLOSSARY ────────────────

describe('C. Guard — chaque term="x" existe dans GLOSSARY', () => {
  for (const { file, name } of EXPLAIN_FILES) {
    it(`${name} — tous les term="x" sont valides`, () => {
      const src = readSrc(file);
      const matches = src.matchAll(/term="([^"]+)"/g);
      for (const m of matches) {
        expect(GLOSSARY[m[1]], `GLOSSARY["${m[1]}"] manquant pour ${name}`).toBeDefined();
      }
    });
  }
});

// ── D. DemoSpotlight — structure ─────────────────────────────────────────────

describe('D. DemoSpotlight — composant', () => {
  const src = readSrc('components/onboarding/DemoSpotlight.jsx');

  it('exporte default DemoSpotlight', () => {
    expect(src).toContain('export default function DemoSpotlight');
  });

  it('a 3 étapes (STEPS)', () => {
    const matches = src.match(/target:\s*'/g);
    expect(matches).toHaveLength(3);
  });

  it('cible step-1, step-2, step-3', () => {
    expect(src).toContain("target: 'step-1'");
    expect(src).toContain("target: 'step-2'");
    expect(src).toContain("target: 'step-3'");
  });

  it('persiste dans localStorage', () => {
    expect(src).toContain('localStorage');
    expect(src).toContain('promeos_spotlight_seen');
  });

  it('a un bouton Suivant', () => {
    expect(src).toContain('Suivant');
  });

  it('a un bouton Passer', () => {
    expect(src).toContain('Passer');
  });

  it('a un bouton Terminer', () => {
    expect(src).toContain('Terminer');
  });

  it('utilise createPortal', () => {
    expect(src).toContain('createPortal');
  });

  it('a data-testid demo-spotlight', () => {
    expect(src).toContain('data-testid="demo-spotlight"');
  });

  it('a data-testid spotlight-next', () => {
    expect(src).toContain('data-testid="spotlight-next"');
  });

  it('a data-testid spotlight-skip', () => {
    expect(src).toContain('data-testid="spotlight-skip"');
  });
});

// ── E. DemoSpotlight — intégré dans Cockpit ──────────────────────────────────

describe('E. DemoSpotlight — intégration Cockpit', () => {
  const src = readSrc('pages/Cockpit.jsx');

  it('Cockpit importe DemoSpotlight', () => {
    expect(src).toContain('DemoSpotlight');
  });

  it('Cockpit rend <DemoSpotlight />', () => {
    expect(src).toContain('<DemoSpotlight');
  });

  it('Cockpit a data-tour="step-1"', () => {
    expect(src).toContain('data-tour="step-1"');
  });

  it('Cockpit a data-tour="step-2"', () => {
    expect(src).toContain('data-tour="step-2"');
  });

  it('Cockpit a data-tour="step-3"', () => {
    expect(src).toContain('data-tour="step-3"');
  });
});

// ── F. Smoke — les 5 fichiers sont parsables ─────────────────────────────────

describe('F. Smoke — 5 fichiers parsables', () => {
  for (const { file, name } of EXPLAIN_FILES) {
    it(`${name} ne contient pas d'erreur de syntaxe JSX évidente`, () => {
      const src = readSrc(file);
      // Basic checks: balanced Explain tags
      const opens = (src.match(/<Explain /g) || []).length;
      const closes = (src.match(/<\/Explain>/g) || []).length;
      expect(opens).toBe(closes);
    });
  }
});
