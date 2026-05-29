/**
 * PROMEOS — Helper d'affichage du niveau de confiance KPI (Sprint P1.S2b).
 *
 * DOCTRINE
 * ────────
 * Ce module est whitelisté dans le source-guard
 * `test_frontend_no_business_calc_source_guards.py` (HELPER_WHITELIST).
 *
 * Justification :
 * `computeConfidence` est un helper de COMPOSITION COSMÉTIQUE des
 * valeurs déjà calculées par le backend (r² climate, n_points,
 * coverage_pct data quality). Il combine ces signaux en un badge
 * d'affichage {level, pct, reason} et NE CALCULE PAS de nouvelle
 * donnée métier — seulement la couleur / texte du badge à afficher.
 *
 * Le SoT canonique du score reste
 * `backend/services/data_freshness_service.compute_meter_freshness`
 * (livré P0.S1b). En P1.S3, ce helper sera supprimé au profit du
 * payload `/api/energy/synthesis.kpis.data_quality_score.value` qui
 * exposera directement le score + level pré-calculés backend
 * (cf. _kpi_data_quality dans services/energy_orchestration/synthesis.py).
 *
 * En attendant cette extension P1.S3, le helper survit ici pour
 * permettre aux 2 useMemo `climateConf` / `qualityConf` de MonitoringPage
 * de rendre les badges sans appel API supplémentaire à chaque rerender.
 */

import { fmtNum } from './format';

/**
 * Compute confidence level for a KPI display.
 *
 * @param {object} opts - { r2, nPoints, coveragePct, reason }
 * @returns {{ level: 'low'|'medium'|'high', pct: number, reason: string }}
 */
export function computeConfidence({ r2, nPoints, coveragePct, reason } = {}) {
  if (reason) return { level: 'low', pct: 0, reason };

  let score = 50; // baseline
  if (r2 != null) score = r2 * 100; // R² dominates for climate
  if (nPoints != null) {
    if (nPoints < 10) score = Math.min(score, 15);
    else if (nPoints < 30) score = Math.min(score, 40);
  }
  if (coveragePct != null) score = Math.min(score, coveragePct);

  score = Math.max(0, Math.min(100, Math.round(score)));
  const level = score >= 60 ? 'high' : score >= 30 ? 'medium' : 'low';
  const reasons = [];
  if (r2 != null && r2 < 0.3) reasons.push(`R² faible (${fmtNum(r2, 2)})`);
  if (nPoints != null && nPoints < 30) reasons.push(`${nPoints} jours de données`);
  if (coveragePct != null && coveragePct < 60) reasons.push(`Couverture ${coveragePct}%`);
  return { level, pct: score, reason: reasons.join(' · ') || 'Données suffisantes' };
}
