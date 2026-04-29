/**
 * Source-guard Phase 1.1 — dictionnaire acronymToNarrative.
 *
 * Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.1 : verrouille
 * que la couverture des acronymes utilisés dans les 2 maquettes cibles
 * (cockpit-pilotage-briefing-jour.html + cockpit-synthese-strategique.html)
 * est complète et que les helpers exportés respectent leur contrat.
 *
 * Doctrine PROMEOS Sol §5 grammaire éditoriale + §6.3 anti-pattern
 * « acronyme brut en titre » + §430 critère « non-sachant comprend la
 * phrase principale sans glossaire externe ».
 */

import { describe, it, expect } from 'vitest';
import {
  ACRONYM_TO_NARRATIVE,
  narrativeFor,
  listNarratableAcronyms,
} from '../domain/acronymToNarrative';

// ── Couverture maquettes Cockpit dual sol2 ──────────────────────────
describe('acronymToNarrative — couverture maquettes Phase 1', () => {
  // Acronymes effectivement présents dans les 2 maquettes HTML
  // (extraits 29/04/2026 par grep). Toute nouvelle maquette doit
  // étendre cette liste si elle introduit un acronyme.
  const ACRONYMS_IN_MOCKUPS = [
    'ARENH',
    'BACS',
    'CBAM',
    'CDC',
    'CEE',
    'CTA',
    'DJU',
    'DT',
    'EMS',
    'EPEX',
    'GTB',
    'HC',
    'HP',
    'RTE',
    'SGE',
    'TURPE',
    'TVA',
    'VNU',
  ];

  it('couvre les 18 acronymes présents dans les 2 maquettes Cockpit dual sol2', () => {
    ACRONYMS_IN_MOCKUPS.forEach((code) => {
      expect(
        ACRONYM_TO_NARRATIVE[code],
        `acronyme ${code} manquant dans ACRONYM_TO_NARRATIVE — utilisé en maquette`
      ).toBeDefined();
    });
  });

  it('couvre aussi APER, OPERAT, NEBCO, AOFD (périmètre Conformité/Flex)', () => {
    ['APER', 'OPERAT', 'NEBCO', 'AOFD'].forEach((code) => {
      expect(ACRONYM_TO_NARRATIVE[code], `acronyme ${code} manquant`).toBeDefined();
    });
  });
});

// ── Forme + longueur ────────────────────────────────────────────────
describe('acronymToNarrative — contrat forme', () => {
  it('chaque entrée a un short ET un long non vides', () => {
    Object.entries(ACRONYM_TO_NARRATIVE).forEach(([code, entry]) => {
      expect(entry.short, `${code}.short vide`).toBeTruthy();
      expect(entry.long, `${code}.long vide`).toBeTruthy();
      expect(typeof entry.short).toBe('string');
      expect(typeof entry.long).toBe('string');
    });
  });

  it('short ≤ 50 chars (cible titres H1/H2)', () => {
    Object.entries(ACRONYM_TO_NARRATIVE).forEach(([code, { short }]) => {
      expect(
        short.length,
        `${code}.short trop long: "${short}" (${short.length})`
      ).toBeLessThanOrEqual(50);
    });
  });

  it('long ≤ 90 chars (cible intros narratives)', () => {
    Object.entries(ACRONYM_TO_NARRATIVE).forEach(([code, { long }]) => {
      expect(long.length, `${code}.long trop long: "${long}" (${long.length})`).toBeLessThanOrEqual(
        90
      );
    });
  });

  it("aucune forme short ne commence par l'acronyme brut (anti-pattern §6.3)", () => {
    // Cas tolérés : noms propres standalone (OPERAT en plateforme).
    // Le but est d'éviter "BACS — score" → "BACS — score" (no-op).
    const allowedNominalProperNoun = ['OPERAT'];
    Object.entries(ACRONYM_TO_NARRATIVE).forEach(([code, { short }]) => {
      if (allowedNominalProperNoun.includes(code)) return;
      const startsWithAcronymBrut = new RegExp(`^${code}\\b`);
      expect(
        short,
        `${code}.short commence par l'acronyme brut: "${short}" — anti-pattern §6.3`
      ).not.toMatch(startsWithAcronymBrut);
    });
  });
});

// ── narrativeFor : helper unitaire ──────────────────────────────────
describe('narrativeFor — helper unitaire', () => {
  it('retourne la forme short par défaut', () => {
    expect(narrativeFor('DT')).toBe('le décret tertiaire');
    expect(narrativeFor('BACS')).toBe('le décret BACS');
    expect(narrativeFor('TURPE')).toBe("le tarif d'acheminement");
  });

  it('retourne la forme long avec mode "long"', () => {
    expect(narrativeFor('DT', { mode: 'long' })).toContain('-40');
    expect(narrativeFor('BACS', { mode: 'long' })).toContain("d'automatisation");
  });

  it('retourne le code brut si acronyme inconnu (no-op safe)', () => {
    expect(narrativeFor('XYZ')).toBe('XYZ');
    expect(narrativeFor('FOOBAR')).toBe('FOOBAR');
  });

  it('gère valeurs vides/null/undefined sans throw', () => {
    expect(narrativeFor('')).toBe('');
    expect(narrativeFor(null)).toBe('');
    expect(narrativeFor(undefined)).toBe('');
  });

  it('insensible à la casse via uppercase fallback', () => {
    expect(narrativeFor('dt')).toBe('le décret tertiaire');
    expect(narrativeFor('bacs')).toBe('le décret BACS');
    expect(narrativeFor('turpe')).toBe("le tarif d'acheminement");
  });

  it('fallback sur short si mode long absent (entrée minimaliste)', () => {
    // Garde-fou si une entrée future oublie le long
    expect(narrativeFor('DT', { mode: 'inexistant' })).toBe('le décret tertiaire');
  });
});

// ── listNarratableAcronyms : pour audit ─────────────────────────────
describe('listNarratableAcronyms — audit / source-guard', () => {
  it('retourne ≥ 22 acronymes (couverture maquettes + Conformité/Flex)', () => {
    expect(listNarratableAcronyms().length).toBeGreaterThanOrEqual(22);
  });

  it('toutes les entrées sont en MAJUSCULES (convention canonique)', () => {
    listNarratableAcronyms().forEach((code) => {
      expect(code, `code ${code} pas en majuscules`).toBe(code.toUpperCase());
    });
  });

  it('aucun doublon dans les clés', () => {
    const codes = listNarratableAcronyms();
    expect(new Set(codes).size).toBe(codes.length);
  });
});

// ── Anti-pattern : pas de duplication avec glossary.js ──────────────
describe('acronymToNarrative — pas de duplication fonctionnelle avec glossary.js', () => {
  it('forme short ≠ définition longue type GLOSSARY (≤ 50 chars enforcé)', () => {
    // GLOSSARY entries vont jusqu'à 120 chars (tooltip). Notre dico vise
    // la substitution inline → contrainte plus serrée pour éviter de
    // glisser vers une copie redondante du glossary.
    Object.entries(ACRONYM_TO_NARRATIVE).forEach(([code, { short }]) => {
      expect(
        short.length,
        `${code}.short (${short.length} chars) sent la définition GLOSSARY (≤ 50 attendu)`
      ).toBeLessThanOrEqual(50);
    });
  });
});
