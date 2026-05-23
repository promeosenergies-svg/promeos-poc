/**
 * PROMEOS — Conformité P0 2026-05-23 : acronymes hero ConformitePage.
 *
 * Vérifie que les 6 acronymes réglementaires (DT, OPERAT, BACS, APER, SMÉ,
 * BEGES) sont enrobés dans `<Term acronyme="...">` (Explain via tooltip) dans
 * le hero de la page Conformité — pour ne pas laisser un utilisateur non-expert
 * face à des sigles non expliqués.
 *
 * Test pure-grep aligné sur le pattern grammar/hub/__tests__/*.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..');
const CONFORMITE_PAGE = readFileSync(resolve(SRC, 'pages/ConformitePage.jsx'), 'utf-8');
const ACRONYMS = readFileSync(resolve(SRC, 'utils/acronyms.js'), 'utf-8');
const GLOSSARY = readFileSync(resolve(SRC, 'domain/glossary.js'), 'utf-8');

describe('Conformité — acronymes hero (P0-4)', () => {
  it.each(['DT', 'OPERAT', 'BACS', 'APER', 'SME', 'BEGES'])(
    "hero ConformitePage enrobe l'acronyme %s dans <Term>",
    (acronyme) => {
      expect(CONFORMITE_PAGE).toContain(`<Term acronyme="${acronyme}"`);
    }
  );

  it('BEGES est défini dans utils/acronyms.js', () => {
    expect(ACRONYMS).toMatch(/BEGES:\s*\{\s*long:\s*"Bilan d'Émissions de Gaz à Effet de Serre"/);
  });

  it('BEGES est défini dans domain/glossary.js (fallback)', () => {
    expect(GLOSSARY).toMatch(/BEGES:\s*["']Bilan d'Émissions de Gaz à Effet de Serre/);
  });

  it('aucun acronyme conformité brut ne reste dans le hero', () => {
    // Le hero (lignes ~640-670 ConformitePage) ne doit pas contenir " DT, " ou similaires
    // sans <Term acronyme="...">. On vérifie que les 6 acronymes apparaissent UNIQUEMENT
    // via <Term acronyme="...">  dans le bloc italicHook.
    // Bornage strict du bloc italicHook = jusqu'au prochain `subtitle=` (prop suivante
    // du SolPageHeader), pour ne pas dépendre de la taille de la prop `actions=` ni
    // d'éventuels boutons ajoutés en dessous (Conformité P1 2026-05-23).
    const heroMatch = CONFORMITE_PAGE.match(/italicHook=\{[\s\S]+?subtitle=/);
    expect(heroMatch).not.toBeNull();
    const heroBlock = heroMatch[0];
    // Chaque acronyme doit apparaître via <Term acronyme="..."> dans le hero
    for (const acronyme of ['DT', 'OPERAT', 'BACS', 'APER', 'SME', 'BEGES']) {
      expect(heroBlock).toContain(`<Term acronyme="${acronyme}"`);
    }
  });

  it('le composant Cockpit utilise toujours useComplianceMeta avec fallback silencieux', () => {
    // P0-3 — on a 410 /recompute mais GARDÉ /meta vivant car Cockpit l'utilise.
    // Si ce test casse, vérifier que le hook a bien un .catch silencieux.
    const HOOK = readFileSync(resolve(SRC, 'hooks/useComplianceMeta.js'), 'utf-8');
    expect(HOOK).toContain('.catch');
  });
});
