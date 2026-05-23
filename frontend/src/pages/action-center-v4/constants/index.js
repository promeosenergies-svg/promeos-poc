/**
 * M2-6.C.3 (commit 2/4) — Centre d'Action V4 / constants index.
 *
 * Compat layer : re-exporte les constantes des 5 sous-fichiers domaine pour
 * préserver les 34 importeurs existants (`from '../constants'`). Migration
 * M3+ vers imports directs depuis sous-fichiers (Q48=C re-exports autorisés).
 *
 * Sous-fichiers :
 *   - constants/lifecycle.js       (8 exports — cycle de vie)
 *   - constants/classification.js  (9 exports — priorités/kinds/domaines)
 *   - constants/evidence.js        (14 exports — preuves/blocages/liens)
 *   - constants/drawer.js          (16 exports — drawer détail)
 *   - constants/narrative.js       (10 exports — pages + NarrativeBar + Sol)
 */
export * from './lifecycle';
export * from './classification';
export * from './evidence';
export * from './drawer';
export * from './narrative';
