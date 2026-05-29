/**
 * Source-guards FE S4 (2026-05-29) — extensions du bloc « Groupe de
 * structures » dans MutualisationSection : PDF + bandeau échéance +
 * CTA demande validation RL.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const root = resolve(__dirname, '../../../../');
const readSrc = (p) => readFileSync(resolve(root, 'src', p), 'utf-8');

describe('S4 · MutualisationSection — export PDF', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('expose CSV + PDF Table 1B (conditionnels sur allRlOk)', () => {
    expect(ui).toContain('CSV Table 1B');
    expect(ui).toContain('PDF Table 1B');
  });

  it('utilise buildExportTable1bPdfUrl du wrapper API', () => {
    expect(ui).toContain('buildExportTable1bPdfUrl');
  });

  it('lien PDF avec testid stable', () => {
    expect(ui).toContain('data-testid={`groupe-export-pdf-${g.id}`}');
  });
});

describe('S4 · MutualisationSection — bandeau échéance R.174-31', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('composant GroupeDeadlineBanner défini', () => {
    expect(ui).toContain('function GroupeDeadlineBanner');
  });

  it('appelle getMutualisationDeadlineStatus', () => {
    expect(ui).toContain('getMutualisationDeadlineStatus');
  });

  it('affiche « Vérification ADEME » avec icône CalendarClock', () => {
    expect(ui).toContain('Vérification ADEME');
    expect(ui).toContain('CalendarClock');
  });

  it('testid stable par groupe', () => {
    expect(ui).toContain('data-testid={`groupe-deadline-${groupId}`}');
  });
});

describe('S4 · MutualisationSection — CTA demande validation RL', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('appelle requestRlValidation depuis le wrapper API', () => {
    expect(ui).toContain('requestRlValidation');
  });

  it('bouton « Demander validation RL » par EFA pending', () => {
    expect(ui).toContain('Demander validation RL');
  });

  it('testid stable par EFA membre', () => {
    expect(ui).toContain('data-testid={`groupe-request-rl-${g.id}-${m.efa_id}`}');
  });

  it('gère 409 RL_ALREADY_VALIDATED + EXTERNAL_REF_CLOSED', () => {
    expect(ui).toContain('RL_ALREADY_VALIDATED');
    expect(ui).toContain('EXTERNAL_REF_CLOSED');
  });
});

describe('S4 · wrappers API mutualisation avancée', () => {
  const api = readSrc('services/api/conformite.js');

  it('expose buildExportTable1bPdfUrl', () => {
    expect(api).toContain('export const buildExportTable1bPdfUrl');
    expect(api).toContain('export-table-1b.pdf');
  });

  it('expose requestRlValidation', () => {
    expect(api).toContain('export const requestRlValidation');
    expect(api).toContain('request-validation');
  });

  it('expose getMutualisationDeadlineStatus', () => {
    expect(api).toContain('export const getMutualisationDeadlineStatus');
    expect(api).toContain('deadline-status');
  });
});

describe('S4 · anti-doublon — pas de concurrent dans UI', () => {
  const ui = readSrc('components/conformite/MutualisationSection.jsx');

  it('aucun nom de concurrent dans le rendu S4', () => {
    for (const concurrent of ['Advizeo', 'Deepki', 'Metron', 'Citron', 'Energisme']) {
      expect(ui).not.toContain(concurrent);
    }
  });
});
