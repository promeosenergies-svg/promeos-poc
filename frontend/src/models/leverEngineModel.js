/**
 * PROMEOS — Levier Engine V1+V35+V36 (logique pure, aucun import React)
 *
 * Agrege les leviers activables a partir des donnees deja presentes
 * dans le state du Cockpit (kpis + billingSummary).
 * V35: enrichissement optionnel via complianceSignals / billingInsights.
 * V36: leviers achat d'energie via purchaseSignals.
 * Aucune nouvelle API.
 *
 * Export:
 *   computeActionableLevers({ kpis, billingSummary, complianceSignals?, billingInsights?, purchaseSignals? }) → LeverResult
 */

import { isComplianceAvailable } from './complianceSignalsContract';
import { isBillingInsightsAvailable } from './billingInsightsContract';
import { isPurchaseAvailable } from './purchaseSignalsContract';
import { computeActivatedCount, ACTIVATION_THRESHOLD } from './dataActivationModel';

/**
 * @typedef {object} Lever
 * @property {'conformite'|'facturation'|'optimisation'|'achat'} type
 * @property {string}  actionKey  — cle unique pour idempotency + deep-link
 * @property {string}  label      — description FR du levier
 * @property {number|null} impactEur — impact estime en euros (null si inconnu)
 * @property {string}  ctaPath    — route cible
 */

/**
 * @typedef {object} LeverResult
 * @property {number}  totalLevers
 * @property {{ conformite: number, facturation: number, optimisation: number, achat: number }} leversByType
 * @property {number}  estimatedImpactEur — somme risque + surcoût (si dispo)
 * @property {Lever[]} topLevers          — tries par impactEur desc (null en dernier)
 */

/**
 * Calcule les leviers activables a partir des donnees deja en scope.
 * V35: si complianceSignals ou billingInsights sont fournis, enrichit les leviers.
 *
 * @param {{ kpis?: object, billingSummary?: object, complianceSignals?: object, billingInsights?: object, purchaseSignals?: object }} input
 * @returns {LeverResult}
 */
export function computeActionableLevers({ kpis = {}, billingSummary = {}, complianceSignals, billingInsights, purchaseSignals } = {}) {
  const levers = [];
  const hasCompliance = isComplianceAvailable(complianceSignals);
  const hasBilling = isBillingInsightsAvailable(billingInsights);
  const hasPurchase = isPurchaseAvailable(purchaseSignals);

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

  // ── Achat d'energie V36 ────────────────────────────────────────────────────
  if (hasPurchase) {
    const expCount = purchaseSignals.expiringSoonCount;
    const missingCount = purchaseSignals.missingContractsCount;
    const expSites = purchaseSignals.expiringSoonSites;

    if (expCount > 0) {
      levers.push({
        type: 'achat',
        actionKey: 'lev-achat-renew',
        label: `Renouveler ${expCount} contrat${expCount > 1 ? 's' : ''} d'energie (${expSites.length} site${expSites.length > 1 ? 's' : ''})`,
        impactEur: purchaseSignals.estimatedExposureEur,
        ctaPath: '/achat-energie?filter=renewal',
        proofHint: 'Contrat de fourniture / avenants / echeancier',
      });
    }

    if (missingCount > 0) {
      levers.push({
        type: 'achat',
        actionKey: 'lev-achat-data',
        label: `Completer ${missingCount} site${missingCount > 1 ? 's' : ''} sans contrat energie`,
        impactEur: null,
        ctaPath: '/achat-energie?filter=missing',
      });
    }
  }

  // ── Tertiaire / OPERAT V39 ─────────────────────────────────────────────────
  const tertiaireIssues = kpis._tertiaireIssues ?? 0;
  const tertiaireCritical = kpis._tertiaireCritical ?? 0;
  if (tertiaireIssues > 0) {
    const severityLabel = tertiaireCritical > 0
      ? ` (${tertiaireCritical} critique${tertiaireCritical > 1 ? 's' : ''})`
      : '';
    levers.push({
      type: 'conformite',
      actionKey: 'lev-tertiaire-efa',
      label: `Corriger ${tertiaireIssues} anomalie${tertiaireIssues > 1 ? 's' : ''} Décret tertiaire${severityLabel}`,
      impactEur: risqueTotal > 0 && totalRisqueSites > 0
        ? Math.round(risqueTotal * (tertiaireIssues / (totalRisqueSites + tertiaireIssues)))
        : null,
      ctaPath: '/conformite/tertiaire/anomalies',
      proofHint: 'Attestation OPERAT ou dossier de modulation — Estimation V1',
    });
  }

  // ── Tertiaire / Site signals V42 ──────────────────────────────────────────
  const tertiaireSiteSignals = kpis._tertiaireSiteSignals ?? {};
  const uncoveredProbable = tertiaireSiteSignals.uncovered_probable ?? 0;
  const incompleteData = tertiaireSiteSignals.incomplete_data ?? 0;

  if (uncoveredProbable > 0) {
    levers.push({
      type: 'conformite',
      actionKey: 'lev-tertiaire-create-efa',
      label: `Créer une EFA pour ${uncoveredProbable} site${uncoveredProbable > 1 ? 's' : ''} assujetti${uncoveredProbable > 1 ? 's' : ''} probable${uncoveredProbable > 1 ? 's' : ''}`,
      impactEur: null,
      ctaPath: '/conformite/tertiaire',
      proofHint: 'Attestation OPERAT ou justificatif de surface',
    });
  }

  if (incompleteData > 0) {
    levers.push({
      type: 'data_activation',
      actionKey: 'lev-tertiaire-complete-patrimoine',
      label: `Compléter les données de ${incompleteData} site${incompleteData > 1 ? 's' : ''} pour qualifier l'assujettissement`,
      impactEur: null,
      ctaPath: '/patrimoine',
    });
  }

  // ── Activation donnees V37 ──────────────────────────────────────────────────
  const activatedCount = computeActivatedCount({ kpis, billingSummary, purchaseSignals });
  if ((kpis.total ?? 0) > 0 && activatedCount < ACTIVATION_THRESHOLD) {
    const missing = 5 - activatedCount;
    levers.push({
      type: 'data_activation',
      actionKey: 'lev-data-cover',
      label: `Completer ${missing} brique${missing > 1 ? 's' : ''} de donnees manquante${missing > 1 ? 's' : ''}`,
      impactEur: null,
      ctaPath: '/activation',
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
    achat: levers.filter((l) => l.type === 'achat').length,
    data_activation: levers.filter((l) => l.type === 'data_activation').length,
  };

  const estimatedImpactEur =
    (risqueTotal > 0 ? risqueTotal : 0) + (totalLoss > 0 ? totalLoss : 0);

  return { totalLevers: levers.length, leversByType, estimatedImpactEur, topLevers };
}
