/**
 * PROMEOS — API Sol (agentique)
 * Endpoints AI-native : propositions d'actions chiffrées prescriptives.
 */
import { cachedGet } from './core';

/**
 * GET /api/sol/proposal
 * Retourne le plan d'action prescriptif Sol (top 3 actions chiffrées
 * avec impact €/an, ROI, délai, source module).
 *
 * Shape :
 *   {
 *     generated_at, org_id, org_name, scope_label,
 *     headline, headline_severity,
 *     actions: [
 *       { id, title, description, severity, impact_eur_per_year,
 *         impact_kind, roi_months, delay, source_module,
 *         action_path, confidence }
 *     ],
 *     total_impact_eur_per_year, sources: []
 *   }
 */
export const getSolProposal = () =>
  cachedGet('/sol/proposal').then((r) => r.data);

/**
 * GET /api/sol/peer-comparison
 * Comparaison tarif moyen org vs pairs sectoriels (€/kWh).
 *
 * Shape :
 *   { archetype, archetype_label, my_avg_kwh_price_eur, peer_avg_kwh_price_eur,
 *     spread_pct, annual_overpayment_eur, sites_count_in_scope,
 *     confidence, peer_source, interpretation }
 */
export const getPeerComparison = () =>
  cachedGet('/sol/peer-comparison').then((r) => r.data);
