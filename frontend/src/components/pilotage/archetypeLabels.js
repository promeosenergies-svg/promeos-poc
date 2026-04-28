/**
 * PROMEOS - Labels humains des archetypes Pilotage.
 *
 * Mapping des codes canoniques backend (`ARCHETYPE_CALIBRATION_2024`) vers
 * leurs libelles humains FR affiches cote client. Source : Barometre Flex 2026
 * + GLOSSAIRE Pilotage `docs/pilotage-usages/GLOSSAIRE.md` §4.
 *
 * Regle doctrine : les codes SCREAMING_SNAKE (BUREAU_STANDARD, COMMERCE_
 * ALIMENTAIRE...) ne doivent PAS etre exposes brut cote UI (audit wording
 * 17/04/2026 a flag 4 FAIL sur ce point).
 */
export const ARCHETYPE_LABELS = {
  BUREAU_STANDARD: 'Bureau standard',
  COMMERCE_ALIMENTAIRE: 'Commerce alimentaire',
  COMMERCE_SPECIALISE: 'Commerce spécialisé',
  LOGISTIQUE_FRIGO: 'Logistique frigorifique',
  ENSEIGNEMENT: 'Enseignement',
  SANTE: 'Santé',
  HOTELLERIE: 'Hôtellerie',
  INDUSTRIE_LEGERE: 'Industrie légère',
};

/**
 * Phase 0.7 (sprint Cockpit dual sol2) — DEMO_SITE_LABELS supprimé.
 *
 * Audit Amine 2026-04-28 : « Card Hypermarché Montreuil en scope HELIOS
 * (leak slug retail-001) » → anti-pattern §6.3. Quand le scope est HELIOS
 * (5 sites Paris/Toulouse/Lyon/Nice/...), la production ne doit jamais
 * afficher un site démo legacy ('retail-001' = Hypermarché Montreuil,
 * 'bureau-001' = Bureau Haussmann, 'entrepot-001' = Entrepôt Rungis).
 *
 * Source-guard `test_helios_no_demo_sites_leak` (pilotage_archetype_labels.test.js)
 * verrouille l'absence de ces 3 slugs dans les composants Pilotage.
 *
 * Si un siteId n'est pas dans `scopedSites`, retourner '' et laisser le
 * composant rendre un empty state propre (« Sélectionnez un site »).
 */
export function humaniseArchetype(code) {
  if (!code) return 'Indéterminé';
  return ARCHETYPE_LABELS[code] || code;
}

export function humaniseSiteId(siteId) {
  if (!siteId) return '';
  return siteId;
}
