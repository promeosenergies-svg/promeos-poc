/**
 * PROMEOS — scopeLabel (Sprint P2.5 audit visuel + intègre hotfix
 * 2026-05-31).
 *
 * Helper unique de formatage des labels métier pour les vues Énergie.
 *
 * INTERDIT (jamais visible utilisateur) :
 * - Site avec id technique entre crochets
 * - Compteur avec id technique entre crochets
 * - Organisation avec id technique entre crochets
 * - Entité avec id technique entre crochets
 *
 * Doctrine : si une vue Énergie a besoin d'un fallback parce que le
 * nom métier est absent, utiliser `formatSiteLabel(site)` qui retourne
 * un libellé FR métier (« Site sélectionné » / « Sélectionner un site »).
 *
 * Doctrine zéro calcul métier frontend : ce helper est pur affichage —
 * choix entre champs déjà fournis par le backend ou fallback FR.
 */

const FALLBACK_SITE_SELECTED = 'Site sélectionné';
const FALLBACK_NO_SITE = 'Sélectionner un site';

/**
 * Retourne le label métier d'un site, avec fallback FR jamais technique.
 *
 * Ordre de priorité :
 *   1. site.nom (champ canonique backend)
 *   2. site.name (alias anglais)
 *   3. site.label
 *   4. site.display_name
 *   5. si un id est connu : 'Site sélectionné'
 *   6. : 'Sélectionner un site'
 *
 * @param {object|null|undefined} site
 * @returns {string} label métier FR, jamais technique
 */
export function formatSiteLabel(site) {
  if (site?.nom) return site.nom;
  if (site?.name) return site.name;
  if (site?.label) return site.label;
  if (site?.display_name) return site.display_name;
  if (site?.id != null) return FALLBACK_SITE_SELECTED;
  return FALLBACK_NO_SITE;
}

export { FALLBACK_SITE_SELECTED, FALLBACK_NO_SITE };
