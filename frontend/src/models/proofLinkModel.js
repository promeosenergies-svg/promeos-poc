/**
 * PROMEOS — Proof Link Model V38 (logique pure, aucun import React)
 *
 * Construit un lien profond vers la Memobox (/kb) pre-filtre
 * a partir des donnees d'un levier (proofHint, proofLinks, type).
 *
 * Exports:
 *   buildProofLink(lever)          -> URL string (/kb?context=...)
 *   hasProofData(lever)            -> boolean
 *   getProofLabel(lever)           -> string (FR)
 *   DOC_STATUS_LABELS              -> map status -> FR label
 *   DOC_STATUS_BADGE               -> map status -> badge variant
 */

// ── Constantes ───────────────────────────────────────────────────────────────

/**
 * Labels FR du cycle de vie Memobox (4 etats + deprecated).
 * draft -> review -> validated -> decisional
 */
export const DOC_STATUS_LABELS = Object.freeze({
  draft: 'Brouillon',
  review: 'En revue',
  validated: 'Valid\u00e9',
  decisional: 'D\u00e9cisionnel',
  deprecated: 'Obsol\u00e8te',
});

/**
 * Badge variant par statut (pour ui/Badge).
 */
export const DOC_STATUS_BADGE = Object.freeze({
  draft: 'neutral',
  review: 'warn',
  validated: 'ok',
  decisional: 'crit',
  deprecated: 'neutral',
});

// ── Mapping type levier -> domaine KB ────────────────────────────────────────

const TYPE_TO_DOMAIN = {
  conformite: 'reglementaire',
  facturation: 'facturation',
  optimisation: 'usages',
  achat: 'facturation',
  data_activation: null,
};

// ── Exports ──────────────────────────────────────────────────────────────────

/**
 * Verifie si un levier porte des donnees de preuve (proofHint ou proofLinks).
 *
 * @param {object} lever
 * @returns {boolean}
 */
export function hasProofData(lever) {
  if (!lever) return false;
  return !!(lever.proofHint || (lever.proofLinks && lever.proofLinks.length > 0));
}

/**
 * Construit un deep-link vers la Memobox avec pre-filtrage contextuel.
 *
 * @param {object} lever — levier issu de leverEngineModel
 * @returns {string} URL path + query string
 */
export function buildProofLink(lever) {
  if (!lever) return '/kb';

  const params = new URLSearchParams();
  params.set('context', 'proof');

  const domain = TYPE_TO_DOMAIN[lever.type];
  if (domain) params.set('domain', domain);

  if (lever.actionKey) params.set('lever', lever.actionKey);
  if (lever.proofHint) params.set('hint', lever.proofHint.slice(0, 100));

  return `/kb?${params.toString()}`;
}

/**
 * Retourne un label FR decrivant la preuve attendue pour un levier.
 *
 * @param {object} lever
 * @returns {string}
 */
export function getProofLabel(lever) {
  if (!lever) return '';
  if (lever.proofHint) return lever.proofHint;
  if (lever.proofLinks && lever.proofLinks.length > 0) {
    return `${lever.proofLinks.length} preuve${lever.proofLinks.length > 1 ? 's' : ''} attendue${lever.proofLinks.length > 1 ? 's' : ''}`;
  }
  return '';
}
