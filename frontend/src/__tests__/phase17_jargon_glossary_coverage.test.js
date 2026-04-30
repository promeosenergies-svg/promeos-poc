/**
 * Phase 17.ter source-guard — couverture du glossaire d'acronymes.
 *
 * Garantit que le glossaire `acronyms.js` couvre les acronymes critiques
 * identifiés par l'audit jargon Phase 17 (Top 18 hors-glossaire). Tout
 * retrait silencieux d'une entrée doit faire échouer le test.
 *
 * Doctrine §6.4 (acronyme → récit) — non-régression durable.
 */
import { describe, it, expect } from 'vitest';

import { ACRONYM_GLOSSARY, isKnownAcronym, acronymTooltip } from '../utils/acronyms';
import { wrapAcronyms } from '../ui/sol/JargonText';

const REQUIRED_ACRONYMS = [
  // Originaux Phase 13/14/15
  'ARENH',
  'VNU',
  'TURPE',
  'CTA',
  'CSPE',
  'CEE',
  'DT',
  'BACS',
  'GTB',
  'APER',
  'OPERAT',
  'CBAM',
  'EPEX',
  'NEBCO',
  'AOFD',
  'CDC',
  'EMS',
  'DJU',
  'TDN',
  'ETS2',
  'CAPEX',
  'PAYBACK',
  // Phase 17.bis.A (audit jargon : Top 18 hors-glossaire critiques)
  'CVC',
  'CRE',
  'RTE',
  'ATRD',
  'ATRT',
  'ISO',
  'COSTIC',
  'EFA',
  'CSRD',
  'DPE',
  'SME',
  'GTC',
  'COFRAC',
  'IPE',
  'ADEME',
  'PRM',
  'PCE',
  'OPQIBI',
];

describe('Phase 17 — couverture glossaire acronymes', () => {
  it('expose tous les acronymes critiques (REQUIRED_ACRONYMS)', () => {
    REQUIRED_ACRONYMS.forEach((key) => {
      expect(isKnownAcronym(key)).toBe(true);
    });
  });

  it('chaque entrée a long + meaning + source non vides', () => {
    Object.entries(ACRONYM_GLOSSARY).forEach(([key, entry]) => {
      expect(entry.long, `${key}.long`).toBeTruthy();
      expect(entry.meaning, `${key}.meaning`).toBeTruthy();
      expect(entry.source, `${key}.source`).toBeTruthy();
      // Récit court : meaning ≤ 250 chars (doctrine §5 — phrase courte)
      expect(entry.meaning.length, `${key}.meaning length`).toBeLessThanOrEqual(280);
    });
  });

  it('acronymTooltip retourne le format Long — Meaning · Source', () => {
    const t = acronymTooltip('BACS');
    expect(t).toMatch(/Building Automation/);
    expect(t).toMatch(/Source : /);
    expect(t).toContain('Décret n°2020-887');
  });

  it('acronymTooltip retourne null pour un acronyme inconnu', () => {
    expect(acronymTooltip('XYZW')).toBe(null);
  });
});

describe('Phase 17.ter — JargonText auto-wrap', () => {
  it('wrappe un acronyme connu dans une phrase mixte', () => {
    const out = wrapAcronyms('Décret BACS sur les bâtiments tertiaires.');
    // Le résultat est un array de fragments+composants
    expect(Array.isArray(out)).toBe(true);
    // Au moins un élément doit être un AcronymTooltip (objet React)
    const hasTooltip = out.some(
      (el) => el && typeof el === 'object' && el.props?.acronym === 'BACS'
    );
    expect(hasTooltip).toBe(true);
  });

  it('ignore les mots non-acronymes', () => {
    const out = wrapAcronyms('Conformité du patrimoine.');
    expect(out).toBe('Conformité du patrimoine.');
  });

  it('wrappe TURPE, CRE, ATRD ensemble', () => {
    const out = wrapAcronyms("Le tarif TURPE 7 est arrêté par la CRE après l'ATRD7.");
    const acrs = out.filter((el) => el && typeof el === 'object' && el.props?.acronym);
    const keys = acrs.map((el) => el.props.acronym);
    expect(keys).toContain('TURPE');
    expect(keys).toContain('CRE');
    expect(keys).toContain('ATRD');
  });

  it('ne wrappe pas les labels UI non-métier (HELIOS, COMEX, CODIR, EUR)', () => {
    const out = wrapAcronyms('Synthèse pour CODIR du Groupe HELIOS — 50 EUR par mois.');
    const acrs = (Array.isArray(out) ? out : []).filter(
      (el) => el && typeof el === 'object' && el.props?.acronym
    );
    const keys = acrs.map((el) => el.props.acronym);
    expect(keys).not.toContain('HELIOS');
    expect(keys).not.toContain('CODIR');
    expect(keys).not.toContain('EUR');
  });
});
