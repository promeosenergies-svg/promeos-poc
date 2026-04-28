/**
 * PROMEOS — Pilotage archetypeLabels helpers — runtime unit tests.
 *
 * Couvre le comportement reel des helpers humanise* (pas juste source-guard).
 * Fix audit 17/04/2026 : helpers non testes runtime pouvaient driver sans
 * signal (ex : un nouveau code backend `DATA_CENTER` afficherait le SCREAMING
 * brut au lieu d'un label humain).
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
  ARCHETYPE_LABELS,
  humaniseArchetype,
  humaniseSiteId,
} from '../components/pilotage/archetypeLabels';

describe('humaniseArchetype', () => {
  it('humanise les 8 archetypes canoniques du Baromètre Flex 2026', () => {
    expect(humaniseArchetype('BUREAU_STANDARD')).toBe('Bureau standard');
    expect(humaniseArchetype('COMMERCE_ALIMENTAIRE')).toBe('Commerce alimentaire');
    expect(humaniseArchetype('COMMERCE_SPECIALISE')).toBe('Commerce spécialisé');
    expect(humaniseArchetype('LOGISTIQUE_FRIGO')).toBe('Logistique frigorifique');
    expect(humaniseArchetype('ENSEIGNEMENT')).toBe('Enseignement');
    expect(humaniseArchetype('SANTE')).toBe('Santé');
    expect(humaniseArchetype('HOTELLERIE')).toBe('Hôtellerie');
    expect(humaniseArchetype('INDUSTRIE_LEGERE')).toBe('Industrie légère');
  });

  it('retourne "Indéterminé" quand le code est null/undefined/""', () => {
    expect(humaniseArchetype(null)).toBe('Indéterminé');
    expect(humaniseArchetype(undefined)).toBe('Indéterminé');
    expect(humaniseArchetype('')).toBe('Indéterminé');
  });

  it("fallback au code brut si l'archetype est inconnu (drift doctrine)", () => {
    // Un code backend non encore mappe cote front reste visible tel quel --
    // c'est preferable a un "indetermine" silencieux qui masquerait le drift.
    expect(humaniseArchetype('DATA_CENTER')).toBe('DATA_CENTER');
    expect(humaniseArchetype('FUTUR_CODE')).toBe('FUTUR_CODE');
  });

  it('ARCHETYPE_LABELS expose les 8 cles canoniques attendues', () => {
    expect(Object.keys(ARCHETYPE_LABELS).sort()).toEqual([
      'BUREAU_STANDARD',
      'COMMERCE_ALIMENTAIRE',
      'COMMERCE_SPECIALISE',
      'ENSEIGNEMENT',
      'HOTELLERIE',
      'INDUSTRIE_LEGERE',
      'LOGISTIQUE_FRIGO',
      'SANTE',
    ]);
  });
});

describe('humaniseSiteId — Phase 0.7 (sans DEMO_SITE_LABELS)', () => {
  // Phase 0.7 : DEMO_SITE_LABELS supprimé pour fermer le leak Hypermarché
  // Montreuil en scope HELIOS. humaniseSiteId retourne désormais le siteId
  // brut. Le caller (RoiFlexReadyCard / NebcoSimulationCard) résout le nom
  // humain via scopedSites.find() depuis le scope HELIOS courant.

  it('retourne "" quand le siteId est absent', () => {
    expect(humaniseSiteId(null)).toBe('');
    expect(humaniseSiteId(undefined)).toBe('');
    expect(humaniseSiteId('')).toBe('');
  });

  it('retourne le siteId brut pour tout Site.id (laisse au caller résoudre via scopedSites)', () => {
    expect(humaniseSiteId('42')).toBe('42');
    expect(humaniseSiteId('unknown-key')).toBe('unknown-key');
  });

  it('Phase 0.7 : retail-001/bureau-001/entrepot-001 ne sont plus mappés en clair', () => {
    // Anti-régression : si quelqu'un re-introduit un mapping démo, ce test
    // casse. La résolution humaine doit passer par scopedSites du caller.
    expect(humaniseSiteId('retail-001')).toBe('retail-001');
    expect(humaniseSiteId('bureau-001')).toBe('bureau-001');
    expect(humaniseSiteId('entrepot-001')).toBe('entrepot-001');
  });
});

// ── Phase 0.7 source-guard : test_helios_no_demo_sites_leak ──────────
//
// Verrouille l'absence des 3 slugs démo legacy ('retail-001', 'bureau-001',
// 'entrepot-001') et de leurs labels FR ('Hypermarché Montreuil', 'Bureau
// Haussmann', 'Entrepôt Rungis') dans les composants Pilotage qui rendent
// du contenu pour le scope HELIOS.

describe('test_helios_no_demo_sites_leak (source-guard Phase 0.7)', () => {
  const DEMO_SLUGS = ['retail-001', 'bureau-001', 'entrepot-001'];
  const DEMO_LABELS = ['Hypermarché Montreuil', 'Bureau Haussmann', 'Entrepôt Rungis'];

  function readSrc(rel) {
    return readFileSync(resolve(__dirname, '..', rel), 'utf-8');
  }

  const FILES_TO_GUARD = [
    'components/pilotage/archetypeLabels.js',
    'components/pilotage/RoiFlexReadyCard.jsx',
    'components/pilotage/NebcoSimulationCard.jsx',
  ];

  it.each(FILES_TO_GUARD)("'%s' ne contient PAS de slug démo legacy", (file) => {
    const src = readSrc(file);
    DEMO_SLUGS.forEach((slug) => {
      // Tolère les mentions dans commentaires Phase 0.7 (le slug apparaît
      // pour expliquer pourquoi il a été retiré). Pattern interdit = code
      // qui assigne ou retourne le slug : `'retail-001'` dans une string
      // literal de code, en const/return/object value.
      const codeOccurrences = src.match(new RegExp(`['"]${slug}['"]`, 'g')) || [];
      const commentOccurrences = (src.match(new RegExp(`//.*${slug}|\\*.*${slug}`, 'g')) || [])
        .length;
      // Toute occurrence en string literal qui n'est PAS dans un commentaire
      // est un leak. Approximation simple : si codeOccurrences > 0 et qu'on
      // a aussi des commentOccurrences, on tolère seulement le cas où elles
      // matchent (le slug n'apparaît qu'en commentaire).
      // Pour ce test on lit le fichier et on s'assure que aucun match brut
      // n'apparaît hors d'un contexte commentaire.
      const lines = src.split('\n');
      const leakLines = lines.filter((line) => {
        if (line.trim().startsWith('//') || line.trim().startsWith('*')) return false;
        return new RegExp(`['"]${slug}['"]`).test(line);
      });
      expect(leakLines, `Slug démo "${slug}" leaké en code dans ${file}`).toHaveLength(0);
    });
    // Les labels FR (Hypermarché Montreuil etc.) sont aussi interdits hors
    // commentaires (ils étaient dans DEMO_SITE_LABELS supprimé Phase 0.7).
    DEMO_LABELS.forEach((label) => {
      const lines = src.split('\n');
      const leakLines = lines.filter((line) => {
        if (line.trim().startsWith('//') || line.trim().startsWith('*')) return false;
        return line.includes(label);
      });
      expect(leakLines, `Label démo "${label}" leaké en code dans ${file}`).toHaveLength(0);
    });
  });

  it("archetypeLabels.js n'exporte plus DEMO_SITE_LABELS", () => {
    const src = readSrc('components/pilotage/archetypeLabels.js');
    expect(src).not.toMatch(/export const DEMO_SITE_LABELS/);
  });

  it('humaniseSiteId retourne le siteId brut sans mapping (anti-régression)', () => {
    expect(humaniseSiteId('retail-001')).toBe('retail-001');
  });
});
