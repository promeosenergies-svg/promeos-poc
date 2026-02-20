/**
 * PROMEOS — Levier Engine V1+V35 (logique pure, aucun import React)
 *
 * Agrege les leviers activables a partir des donnees deja presentes
 * dans le state du Cockpit (kpis + billingSummary).
 * V35: enrichissement optionnel via complianceSignals / billingInsights.
 * Aucune nouvelle API.
 *
 * Export:
 *   computeActionableLevers({ kpis, billingSummary, complianceSignals?, billingInsights? }) → LeverResult
 */

import { isComplianceAvailable } from './complianceSignalsContract';
import { isBillingInsightsAvailable } from './billingInsightsContract';

/**
 * @typedef {object} Lever
 * @property {'conformite'|'facturation'|'optimisation'} type
 * @property {string}  actionKey  — cle unique pour idempotency + deep-link
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
 * V35: si complianceSignals ou billingInsights sont fournis, enrichit les leviers.
 *
 * @param {{ kpis?: object, billingSummary?: object, complianceSignals?: object, billingInsights?: object }} input
 * @returns {LeverResult}
 */
export function computeActionableLevers({ kpis = {}, billingSummary = {}, complianceSignals, billingInsights } = {}) {
  const levers = [];
  const hasCompliance = isComplianceAvailable(complianceSignals);
  const hasBilling = isBillingInsightsAvailable(billingInsights);

  // ── Conformite ──────────────────────────────────────────────────────────────
  const nonConformes = kpis.nonConformes ?? 0;
  const aRisque = kpis.aRisque ?? 0;
  const risqueTotal = kpis.risqueTotal ?? 0;
  const totalRisqueSites = nonConformes + aRisque;

  // V35: enrichissement conformite via signals contract
  const compSignals = hasCompliance ? complianceSignals.signals : [];
  const compHighCount = compSignals.filter((s) => s.severity === 'critical' || s.severity === 'high').length;
  const compProofHint = compSignals.length > 0 && compSignals[0].proof_expected
    ? compSignals[0].proof_expected
    : null;

  if (nonConformes > 0) {
    const enrichedLabel = hasCompliance && compHighCount > 0
      ? `Regulariser ${nonConformes} site${nonConformes > 1 ? 's' : ''} non conforme${nonConformes > 1 ? 's' : ''} (${compHighCount} signal${compHighCount > 1 ? 's' : ''} critique${compHighCount > 1 ? 's' : ''})`
      : `Regulariser ${nonConformes} site${nonConformes > 1 ? 's' : ''} non conforme${nonConformes > 1 ? 's' : ''}`;
    levers.push({
      type: 'conformite',
      actionKey: 'lev-conf-nc',
      label: enrichedLabel,
      impactEur: risqueTotal > 0
        ? Math.round(risqueTotal * (nonConformes / (totalRisqueSites || 1)))
        : null,
      ctaPath: '/conformite',
      proofHint: compProofHint,
    });
  }

  if (aRisque > 0) {
    levers.push({
      type: 'conformite',
      actionKey: 'lev-conf-ar',
      label: `Prevenir ${aRisque} site${aRisque > 1 ? 's' : ''} a risque`,
      impactEur: risqueTotal > 0
        ? Math.round(risqueTotal * (aRisque / (totalRisqueSites || 1)))
        : null,
      ctaPath: '/conformite',
      proofHint: compProofHint,
    });
  }

  // ── Facturation ─────────────────────────────────────────────────────────────
  const anomalies = billingSummary.invoices_with_anomalies ?? billingSummary.total_insights ?? 0;
  const totalLoss = Math.max(0, billingSummary.total_loss_eur ?? 0);

  // V35: enrichissement facturation via billingInsights contract
  const biAnom = hasBilling ? billingInsights.anomalies_count : 0;
  const biLoss = hasBilling ? billingInsights.total_loss_eur : 0;
  const biConf = hasBilling ? billingInsights.confidence : null;
  const biProofs = hasBilling && billingInsights.proof_links?.length > 0
    ? billingInsights.proof_links
    : null;

  const effectiveAnomalies = hasBilling ? biAnom : anomalies;
  const effectiveLoss = hasBilling ? Math.max(biLoss, totalLoss) : totalLoss;
  const confLabel = biConf === 'high' ? ' (confiance haute)' : biConf === 'medium' ? ' (confiance moyenne)' : '';

  if (effectiveAnomalies > 0) {
    levers.push({
      type: 'facturation',
      actionKey: 'lev-fact-anom',
      label: `Corriger ${effectiveAnomalies} anomalie${effectiveAnomalies > 1 ? 's' : ''} facture${confLabel}`,
      impactEur: effectiveLoss > 0 ? effectiveLoss : null,
      ctaPath: '/bill-intel',
      proofLinks: biProofs,
    });
  } else if (effectiveLoss > 0) {
    levers.push({
      type: 'facturation',
      actionKey: 'lev-fact-loss',
      label: 'Recuperer le surcout facture detecte',
      impactEur: effectiveLoss,
      ctaPath: '/bill-intel',
      proofLinks: biProofs,
    });
  }

  // ── Optimisation ────────────────────────────────────────────────────────────
  const totalEur = billingSummary.total_eur ?? 0;

  if (totalEur > 0) {
    levers.push({
      type: 'optimisation',
      actionKey: 'lev-optim-ener',
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
