/**
 * PROMEOS — Deep Link Helper (V71)
 * Construit des URL contextuelles pour la navigation interne.
 *
 * Usage:
 *   import { deepLinkWithContext, deepLinkAction, deepLinkNewAction } from '../services/deepLink';
 *   navigate(deepLinkWithContext(siteId, '2025-03', invoiceId));
 *   navigate(deepLinkAction(42));
 *   navigate(deepLinkNewAction({ type: 'facture', site_id: 5 }));
 */

/**
 * Construit un deep link vers la page factures avec contexte pré-appliqué.
 *
 * @param {number|string|null} siteId   — filtre site (query param site_id)
 * @param {string|null}        month    — filtre mois YYYY-MM (query param month)
 * @param {number|null}        invoiceId — si fourni, pointe vers la facture unique
 * @returns {string} URL relative prête pour navigate()
 */
export function deepLinkWithContext(siteId, month, invoiceId = null) {
  if (invoiceId) {
    const params = new URLSearchParams();
    params.set('invoice_id', String(invoiceId));
    if (siteId) params.set('site_id', String(siteId));
    if (month) params.set('month', month);
    return `/bill-intel?${params.toString()}`;
  }

  const params = new URLSearchParams();
  if (siteId) params.set('site_id', String(siteId));
  if (month) params.set('month', month);
  return `/bill-intel?${params.toString()}`;
}

/**
 * Deep link vers une action existante.
 * @param {number|string} actionId
 * @returns {string} URL relative /actions/:id
 */
export function deepLinkAction(actionId) {
  return `/actions/${actionId}`;
}

/**
 * Deep link vers la création d'action avec contexte pré-rempli.
 * @param {object} opts - { type, site_id, source, ref_id, titre }
 * @returns {string} URL relative /actions/new?...
 */
export function deepLinkNewAction(opts = {}) {
  const params = new URLSearchParams();
  if (opts.type) params.set('type', opts.type);
  if (opts.site_id) params.set('site_id', String(opts.site_id));
  if (opts.source) params.set('source', opts.source);
  if (opts.ref_id) params.set('ref_id', String(opts.ref_id));
  if (opts.titre) params.set('titre', opts.titre);
  const qs = params.toString();
  return `/actions/new${qs ? '?' + qs : ''}`;
}
