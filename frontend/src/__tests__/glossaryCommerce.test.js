/**
 * Phase 13.D — BL-9 glossaire TURPE inline COMMERCE FE.
 *
 * Vérifie que `getDefinition(code, "commerce")` retourne une définition
 * vulgarisée Hervé-friendly au lieu du registre CFO standard.
 *
 * Convention `GLOSSARY_COMMERCE` : phrases courtes, vocabulaire concret,
 * pas de sigle technique dans la définition (anti-spirale).
 *
 * Ref : audit final BL-9 + sprint narrative-sol2 Phase 13.D.
 */

import { describe, it, expect } from 'vitest';
import { getDefinition, isGlossed, GLOSSARY_COMMERCE } from '../domain/glossary';

describe('Phase 13.D — GLOSSARY_COMMERCE structure', () => {
  it('exporte GLOSSARY_COMMERCE map', () => {
    expect(typeof GLOSSARY_COMMERCE).toBe('object');
    expect(Object.keys(GLOSSARY_COMMERCE).length).toBeGreaterThan(8);
  });

  it('contient TURPE vulgarisé', () => {
    expect(GLOSSARY_COMMERCE.TURPE).toBeDefined();
    expect(GLOSSARY_COMMERCE.TURPE).toMatch(/Enedis/);
    // Pas de "tarif d'utilisation des réseaux publics"
    expect(GLOSSARY_COMMERCE.TURPE.toLowerCase()).not.toContain("tarif d'utilisation");
  });

  it('contient HP/HC vulgarisés', () => {
    expect(GLOSSARY_COMMERCE.HP).toMatch(/Heures pleines/);
    expect(GLOSSARY_COMMERCE.HC).toMatch(/Heures creuses/);
  });

  it('contient CEE vulgarisé (subventions)', () => {
    expect(GLOSSARY_COMMERCE.CEE).toMatch(/[Ss]ubvention/);
  });
});

describe('Phase 13.D — getDefinition() avec typology', () => {
  it("typology='commerce' renvoie la version vulgarisée TURPE", () => {
    const def = getDefinition('TURPE', 'commerce');
    expect(def).toMatch(/Enedis/);
    expect(def).toContain('30 %');
  });

  it('typology=null renvoie la version standard CFO TURPE', () => {
    const defStd = getDefinition('TURPE', null);
    expect(defStd).toMatch(/Tarif d'Utilisation/);
  });

  it("typology='commerce' renvoie version vulgarisée OPERAT", () => {
    const def = getDefinition('OPERAT', 'commerce');
    expect(def).toMatch(/commerces/);
  });

  it('typology inconnue tombe sur GLOSSARY standard', () => {
    const def = getDefinition('TURPE', 'eti_tertiaire');
    // ETI utilise GLOSSARY standard (pas COMMERCE override)
    expect(def).toMatch(/Tarif d'Utilisation/);
  });

  it("typology='commerce' fallback GLOSSARY si pas d'override", () => {
    // BACS pas dans GLOSSARY_COMMERCE → tombe sur GLOSSARY standard
    const def = getDefinition('BACS', 'commerce');
    expect(def).toMatch(/BACS|Bâtiments/);
  });
});

describe('Phase 13.D — isGlossed() avec typology', () => {
  it("isGlossed('TURPE', 'commerce') retourne true", () => {
    expect(isGlossed('TURPE', 'commerce')).toBe(true);
  });

  it('isGlossed inconnu commerce retourne false', () => {
    expect(isGlossed('UNKNOWN_CODE_XYZ', 'commerce')).toBe(false);
  });
});
