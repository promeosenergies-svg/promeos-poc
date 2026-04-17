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
 * Labels humains des cles DEMO_SITES (fallback quand scope = "Tous les sites").
 * Source : `backend/routes/pilotage.py` DEMO_SITES (clef `nom`).
 */
export const DEMO_SITE_LABELS = {
  'retail-001': 'Hypermarché Montreuil',
  'bureau-001': 'Bureau Haussmann',
  'entrepot-001': 'Entrepôt Rungis',
};

export function humaniseArchetype(code) {
  if (!code) return 'Indéterminé';
  return ARCHETYPE_LABELS[code] || code;
}

export function humaniseSiteId(siteId) {
  if (!siteId) return '';
  return DEMO_SITE_LABELS[siteId] || siteId;
}
