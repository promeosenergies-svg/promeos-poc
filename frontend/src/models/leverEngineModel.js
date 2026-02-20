/**
 * PROMEOS — Levier Engine V1 (logique pure, aucun import React)
 *
 * Agrege les leviers activables a partir des donnees deja presentes
 * dans le state du Cockpit (kpis + billingSummary).
 * Aucune nouvelle API.
 *
 * Export:
 *   computeActionableLevers({ kpis, billingSummary }) → LeverResult
 */

/**
 * @typedef {object} Lever
 * @property {'conformite'|'facturation'|'optimisation'} type
 * @property {string}  label      — description FR du levier
 * @property {number|null} impactEur — impact estime en euros (null si inconnu)
 * @property {string}  ctaPath    — route cible
 */

/**
 * @typedef {object} LeverResult
 * @property {number}  totalLevers
 * @property {{ conformite: number, facturation: number, optimisation: number }} leversByType
 * @property {number}  estimatedImpactEur — somme risque + surcoût (si dispo)
 * @property {Lever[]} topLevers          — tries par impactEur desc (null en dernier)
 */

/**
 * Calcule les leviers activables a partir des donnees deja en scope.
 *
 * @param {{ kpis?: object, billingSummary?: object }} input
 * @returns {LeverResult}
 */
export function computeActionableLevers({ kpis = {}, billingSummary = {} } = {}) {
  const levers = [];

  // ── Conformite ──────────────────────────────────────────────────────────────
  const nonConformes = kpis.nonConformes ?? 0;
  const aRisque = kpis.aRisque ?? 0;
  const risqueTotal = kpis.risqueTotal ?? 0;
  const totalRisqueSites = nonConformes + aRisque;

  if (nonConformes > 0) {
    levers.push({
      type: 'conformite',
      label: `Regulariser ${nonConformes} site${nonConformes > 1 ? 's' : ''} non conforme${nonConformes > 1 ? 's' : ''}`,
      impactEur: risqueTotal > 0
        ? Math.round(risqueTotal * (nonConformes / (totalRisqueSites || 1)))
        : null,
      ctaPath: '/conformite',
    });
  }

  if (aRisque > 0) {
    levers.push({
      type: 'conformite',
      label: `Prevenir ${aRisque} site${aRisque > 1 ? 's' : ''} a risque`,
      impactEur: risqueTotal > 0
        ? Math.round(risqueTotal * (aRisque / (totalRisqueSites || 1)))
        : null,
      ctaPath: '/conformite',
    });
  }

  // ── Facturation ─────────────────────────────────────────────────────────────
  const anomalies = billingSummary.invoices_with_anomalies ?? billingSummary.total_insights ?? 0;
  const totalLoss = Math.max(0, billingSummary.total_loss_eur ?? 0);

  if (anomalies > 0) {
    levers.push({
      type: 'facturation',
      label: `Corriger ${anomalies} anomalie${anomalies > 1 ? 's' : ''} facture`,
      impactEur: totalLoss > 0 ? totalLoss : null,
      ctaPath: '/bill-intel',
    });
  } else if (totalLoss > 0) {
    levers.push({
      type: 'facturation',
      label: 'Recuperer le surcout facture detecte',
      impactEur: totalLoss,
      ctaPath: '/bill-intel',
    });
  }

  // ── Optimisation ────────────────────────────────────────────────────────────
  const totalEur = billingSummary.total_eur ?? 0;

  if (totalEur > 0) {
    levers.push({
      type: 'optimisation',
      label: 'Lancer l\'optimisation energetique',
      impactEur: Math.round(totalEur * 0.01),
      ctaPath: '/diagnostic-conso',
    });
  }

  // ── Aggregation ─────────────────────────────────────────────────────────────
  const topLevers = [...levers].sort(
    (a, b) => (b.impactEur ?? -1) - (a.impactEur ?? -1),
  );

  const leversByType = {
    conformite: levers.filter((l) => l.type === 'conformite').length,
    facturation: levers.filter((l) => l.type === 'facturation').length,
    optimisation: levers.filter((l) => l.type === 'optimisation').length,
  };

  const estimatedImpactEur =
    (risqueTotal > 0 ? risqueTotal : 0) + (totalLoss > 0 ? totalLoss : 0);

  return { totalLevers: levers.length, leversByType, estimatedImpactEur, topLevers };
}
