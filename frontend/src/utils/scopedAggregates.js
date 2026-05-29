/**
 * PROMEOS — Helpers d'agrégation post-filtre scope FE (Sprint P1.S2b).
 *
 * DOCTRINE
 * ────────
 * Ce module est explicitement whitelisté dans le source-guard
 * `test_frontend_no_business_calc_source_guards.py` (HELPER_WHITELIST).
 *
 * Justification :
 * Ces fonctions agrègent des `estimated_*_eur` issus de payloads
 * backend (ConsumptionInsight, AlertItem) APRÈS un filtre scope
 * appliqué côté frontend (selectedSiteId, queryStatus). Tant que les
 * endpoints backend n'acceptent pas ces filtres comme query params
 * (planifié P1.S3 — branchement `getEnergySynthesis({scope, scope_id})`
 * fait remonter la valeur agrégée backend `kpis.estimated_impact_eur`),
 * on doit agréger côté FE pour respecter le filtre UI.
 *
 * Préférence forte : utiliser `getEnergySynthesis()` (cf.
 * `services/api/energy.js`) quand le scope correspond exactement à un
 * site (synthesis.kpis.estimated_impact_eur.value est pré-calculé
 * backend post-filtre scope). Ne tomber sur ces helpers que pour les
 * filtres UI fines (queryStatus, multi-site composite) non encore
 * exposés côté endpoint.
 *
 * Migration cible :
 * 1. Étendre /api/consumption/insights pour accepter site_id +
 *    insight_status query params (déjà partiel, à généraliser).
 * 2. Brancher ConsumptionDiagPage.jsx et MonitoringPage.jsx sur
 *    /api/energy/synthesis.kpis.estimated_impact_eur pour le total.
 * 3. Supprimer ce helper.
 */

/**
 * Somme estimated_loss_eur d'une liste d'insights filtrés côté FE.
 *
 * @param {Array<{estimated_loss_eur?: number}>} insights
 * @returns {number} somme en euros arrondie à l'entier.
 */
export function sumInsightsLossEur(insights = []) {
  if (!Array.isArray(insights)) return 0;
  let total = 0;
  for (const i of insights) {
    const v = Number(i?.estimated_loss_eur);
    if (Number.isFinite(v)) total += v;
  }
  return Math.round(total);
}

/**
 * Somme estimated_loss_kwh d'une liste d'insights filtrés.
 *
 * @param {Array<{estimated_loss_kwh?: number}>} insights
 * @returns {number} somme en kWh arrondie à l'entier.
 */
export function sumInsightsLossKwh(insights = []) {
  if (!Array.isArray(insights)) return 0;
  let total = 0;
  for (const i of insights) {
    const v = Number(i?.estimated_loss_kwh);
    if (Number.isFinite(v)) total += v;
  }
  return Math.round(total);
}

/**
 * Somme estimated_impact_eur d'une liste d'alertes filtrées côté FE.
 *
 * @param {Array<{estimated_impact_eur?: number}>} alerts
 * @returns {number} somme en euros arrondie à l'entier.
 */
export function sumAlertsImpactEur(alerts = []) {
  if (!Array.isArray(alerts)) return 0;
  let total = 0;
  for (const a of alerts) {
    const v = Number(a?.estimated_impact_eur);
    if (Number.isFinite(v)) total += v;
  }
  return Math.round(total);
}
