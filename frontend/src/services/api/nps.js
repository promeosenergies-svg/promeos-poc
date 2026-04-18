/**
 * PROMEOS - API NPS micro-survey (Sprint CX P1 residual)
 *
 * POST /api/nps/submit — envoie une note NPS (0-10) + verbatim optionnel.
 * Le trigger d'affichage est piloté côté front via utils/nps.js::shouldShowNps
 * (localStorage + user.created_at), sans aller-retour réseau.
 *
 * Cible scorecard CX "NPS/CES" (mesure 10% orpheline avant ce sprint).
 */
import api from './core';

/**
 * Soumet une note NPS.
 * @param {object} params
 * @param {number} params.score — note entière 0-10
 * @param {string} [params.verbatim] — commentaire libre optionnel (< 1000 chars)
 * @param {number} [params.orgId] — org_id en query (fallback demo mode)
 * @returns {Promise<{status: 'recorded'|'already_submitted', category?: string}>}
 */
export const submitNps = ({ score, verbatim, orgId } = {}) => {
  const params = orgId != null ? { org_id: orgId } : {};
  return api
    .post('/nps/submit', { score, verbatim: verbatim || null }, { params })
    .then((r) => r.data);
};
