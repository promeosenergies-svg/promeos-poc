/**
 * KB Recommendation → ActionItem bridge model.
 * Pure functions: build payload for POST /api/actions.
 * Pattern: OPERAT V46 (source_type='insight', idempotency_key for dedup).
 *
 * Doctrine PROMEOS (fix P0 QA Guardian 2026-04-15) :
 * - Jamais de facteur CO₂ hardcodé côté frontend pour persistence en DB.
 * - On envoie `estimated_savings_kwh_year` au backend, qui calcule
 *   `co2e_savings_est_kg` via `config.emission_factors.get_emission_factor("ELEC")`.
 * - Si ADEME met à jour le facteur, le recompute est backend-only.
 */

const SEVERITY_TO_PRIORITY = { critical: 1, high: 2, medium: 3, low: 4 };

function computeDueDate(severity) {
  const days = { critical: 14, high: 30, medium: 60, low: 90 }[severity] || 60;
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
}

export function buildKbRecoActionKey(siteId, recommendationCode) {
  return `kb-reco:${siteId}:${recommendationCode}`;
}

export function buildKbRecoActionPayload({
  orgId,
  siteId,
  siteName,
  reco,
  topSeverity = 'medium',
}) {
  const severity = topSeverity || 'medium';
  const savingsEur = reco.estimated_savings_eur_year || null;
  const savingsKwh = reco.estimated_savings_kwh_year || null;

  return {
    org_id: orgId,
    site_id: siteId,
    source_type: 'insight',
    source_id: `kb-reco:${reco.id}`,
    source_key: `${siteId}:${reco.recommendation_code}`,
    idempotency_key: buildKbRecoActionKey(siteId, reco.recommendation_code),
    title: `${reco.title} \u2014 ${siteName}`,
    rationale: buildRationale(reco),
    priority: SEVERITY_TO_PRIORITY[severity] || 3,
    severity,
    estimated_gain_eur: savingsEur,
    // Le backend calcule co2e_savings_est_kg depuis estimated_savings_kwh_year.
    // Ne pas envoyer co2e_savings_est_kg depuis le front : source unique backend.
    estimated_savings_kwh_year: savingsKwh,
    due_date: computeDueDate(severity),
    category: 'energie',
  };
}

function buildRationale(reco) {
  const lines = [];
  if (reco.title) lines.push(`Recommandation : ${reco.title}`);
  if (reco.estimated_savings_kwh_year)
    lines.push(
      `Economie estimee : ${Math.round(reco.estimated_savings_kwh_year).toLocaleString('fr-FR')} kWh/an`
    );
  if (reco.estimated_savings_eur_year)
    lines.push(
      `Soit ~${Math.round(reco.estimated_savings_eur_year).toLocaleString('fr-FR')} \u20ac/an`
    );
  if (reco.ice_score) lines.push(`Score ICE : ${reco.ice_score.toFixed(1)}`);
  return lines.join('\n');
}

export function buildKbRecoActionDeepLink(siteId) {
  return `/actions?source=kb-reco&site_id=${siteId}`;
}
