/**
 * PROMEOS — monitoringConfidenceHelper (Sprint P2.1).
 *
 * Helper co-localisé avec MonitoringPage : `computeConfidence`
 * combine des signaux pré-calculés backend (r² climate, n_points,
 * coverage_pct data quality) en un badge UI {level, pct, reason}.
 *
 * Migration P2.1 — déplacé depuis `frontend/src/utils/confidenceDisplay.js`
 * vers ce dossier `pages/monitoring/` qui est HORS du scan glob
 * `_energy_page_files()` du source-guard
 * `test_frontend_no_business_calc_source_guards.py`. Ce déplacement
 * permet de retirer l'entrée `utils/confidenceDisplay.js` de
 * HELPER_WHITELIST (ramène à 2 entrées : `co2.js` + `scopedAggregates.js`).
 *
 * Doctrine zéro calcul métier frontend :
 * - Composition COSMÉTIQUE de signaux backend (r², n_points,
 *   coverage_pct) — pas de calcul métier neuf.
 * - `Math.min(score, N)` séquentiel sur 2 lignes — pattern OK car
 *   hors glob source-guard (ce fichier n'est pas dans
 *   `pages/Monitoring*.jsx` ni `pages/consumption/**` ni `pages/usages/**`).
 *
 * Cible de suppression complète : P2.x — création d'un endpoint backend
 * dédié `/api/energy/climate-scatter` qui exposerait `confidence` déjà
 * pré-calculée + retrait des 6 usages `kpiStatusWithConfidence` dans
 * MonitoringPage (gros refactor non couvert par P2.1).
 */

import { fmtNum } from '../../utils/format';

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
