/**
 * PROMEOS — Pilotage archetypeLabels helpers — runtime unit tests.
 *
 * Couvre le comportement reel des helpers humanise* (pas juste source-guard).
 * Fix audit 17/04/2026 : helpers non testes runtime pouvaient driver sans
 * signal (ex : un nouveau code backend `DATA_CENTER` afficherait le SCREAMING
 * brut au lieu d'un label humain).
 */
import { describe, it, expect } from 'vitest';
import {
  ARCHETYPE_LABELS,
  DEMO_SITE_LABELS,
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

describe('humaniseSiteId', () => {
  it('humanise les 3 cles DEMO_SITES canoniques', () => {
    expect(humaniseSiteId('retail-001')).toBe('Hypermarché Montreuil');
    expect(humaniseSiteId('bureau-001')).toBe('Bureau Haussmann');
    expect(humaniseSiteId('entrepot-001')).toBe('Entrepôt Rungis');
  });

  it('retourne "" quand le siteId est absent', () => {
    expect(humaniseSiteId(null)).toBe('');
    expect(humaniseSiteId(undefined)).toBe('');
    expect(humaniseSiteId('')).toBe('');
  });

  it('fallback au siteId brut pour un Site.id reel (numerique) ou cle inconnue', () => {
    // Un Site.id reel de prod (ex: "42") passe tel quel -- le caller
    // RoiFlexReadyCard resoud le nom humain via scopedSites.find() separement.
    expect(humaniseSiteId('42')).toBe('42');
    expect(humaniseSiteId('unknown-key')).toBe('unknown-key');
  });
});
