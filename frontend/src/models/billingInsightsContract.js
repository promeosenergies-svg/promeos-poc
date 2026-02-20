/**
 * PROMEOS — BillingInsightsContract V35
 * Contract pour les insights factures (PDF parsing → anomalies → preuves).
 *
 * Definit la structure attendue pour enrichir le Lever Engine.
 * Pas d'implementation parsing ici — juste le contrat.
 *
 * Exports:
 *   normalizeBillingInsights(raw)  → BillingInsights | null
 *   EMPTY_BILLING_INSIGHTS         → valeur par defaut (safe)
 *   isBillingInsightsAvailable(insights) → boolean
 */

/**
 * @typedef {object} BillingInsights
 * @property {number}  anomalies_count     — nombre d'anomalies detectees
 * @property {number}  total_loss_eur      — perte totale estimee
 * @property {number}  invoices_impacted   — factures concernees
 * @property {'high'|'medium'|'low'} confidence — confiance dans le resultat
 * @property {string[]} [proof_links]      — liens vers preuves (URLs ou refs)
 */

export const EMPTY_BILLING_INSIGHTS = Object.freeze({
  anomalies_count: 0,
  total_loss_eur: 0,
  invoices_impacted: 0,
  confidence: 'low',
  proof_links: [],
});

/**
 * Normalise un objet brut en BillingInsights.
 * Retourne EMPTY_BILLING_INSIGHTS si input invalide.
 *
 * @param {any} raw
 * @returns {BillingInsights}
 */
export function normalizeBillingInsights(raw) {
  if (!raw || typeof raw !== 'object') return EMPTY_BILLING_INSIGHTS;

  const anomalies_count = typeof raw.anomalies_count === 'number' ? Math.max(0, raw.anomalies_count) : 0;
  const total_loss_eur = typeof raw.total_loss_eur === 'number' ? Math.max(0, raw.total_loss_eur) : 0;
  const invoices_impacted = typeof raw.invoices_impacted === 'number' ? Math.max(0, raw.invoices_impacted) : 0;

  if (anomalies_count === 0 && total_loss_eur === 0) return EMPTY_BILLING_INSIGHTS;

  const confidence = ['high', 'medium', 'low'].includes(raw.confidence) ? raw.confidence : 'low';
  const proof_links = Array.isArray(raw.proof_links) ? raw.proof_links.filter((l) => typeof l === 'string') : [];

  return { anomalies_count, total_loss_eur, invoices_impacted, confidence, proof_links };
}

/**
 * Verifie si des insights facturation sont disponibles et non vides.
 *
 * @param {BillingInsights|null|undefined} insights
 * @returns {boolean}
 */
export function isBillingInsightsAvailable(insights) {
  return !!(insights && (insights.anomalies_count > 0 || insights.total_loss_eur > 0));
}
