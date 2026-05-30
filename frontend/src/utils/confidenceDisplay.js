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
 * (livré P0.S1b). En P1.S3b, la nouvelle vue
 * `MonitoringSynthesisStrip` consomme directement
 * `synthesis.kpis.data_quality_score.value` (déjà borné [0,100] backend
 * via `clamp_score_0_100`) et ne passe PAS par `computeConfidence` —
 * cf. `frontend/src/ui/energy/MonitoringSynthesisStrip.jsx`.
 *
 * STATUT P1.S7 (Polish transverse — 2026-05-30)
 * ──────────────────────────────────────────────
 * `computeConfidence` reste utilisé uniquement par MonitoringPage.jsx
 * (lignes 1905-1908 `climateConf` + 1915-1919 `qualityConf`) pour le
 * climate scatter (r² + n_points) et la card qualité legacy.
 *
 * Le climate scatter n'est PAS encore couvert par
 * `/api/energy/synthesis` (hors scope synthesis-vue-30s). Migrer
 * `climateConf` vers un endpoint backend dédié = scope P2.1
 * (MonitoringPage split + endpoint `/api/energy/climate-scatter`).
 *
 * Décision P1.S7 — **Option B** (conservation justifiée) : ne PAS
 * retirer de la HELPER_WHITELIST. La modification massive de
 * MonitoringPage est explicitement interdite par le brief P1.S7 ; le
 * retrait sera traité en P2.1 (climate scatter backend + MonitoringPage
 * refactor).
 *
 * Cible de suppression : P2.1 MonitoringPage split (climate scatter
 * backend + retrait `computeConfidence`/`confidenceDisplay.js` +
 * HELPER_WHITELIST applicative ramenée à 2 entrées : `co2.js` +
 * `scopedAggregates.js`).
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
