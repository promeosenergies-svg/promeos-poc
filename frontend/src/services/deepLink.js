/**
 * PROMEOS — Deep Link Helper (V70)
 * Construit des URL contextuelles pour la navigation interne.
 *
 * Usage:
 *   import { deepLinkWithContext } from '../services/deepLink';
 *   navigate(deepLinkWithContext(siteId, '2025-03', invoiceId));
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
