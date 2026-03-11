/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Scoring — Explainable scores (4 axes)
 *
 * BudgetRisk / Transparency / ContractRisk / DataReadiness
 * Each returns ScoreResult { score0to100, level, reasons[], evidence[] }
 */
import { ScoreLevel, OfferStructure } from './types.js';

// ── Helpers ────────────────────────────────────────────────────────

function level(score) {
  if (score >= 70) return ScoreLevel.GREEN;
  if (score >= 40) return ScoreLevel.ORANGE;
  return ScoreLevel.RED;
}

function evidence(ruleId, field, value, source = 'USER') {
  return { ruleId, field, value, source };
}

// ── Budget Risk Score ──────────────────────────────────────────────

/**
 * Score budget risk: lower = more risk
 * @param {Object} params
 * @param {import('./engine.js').OfferResult} params.offerResult
 * @param {import('./types.js').Offer} params.offer
 * @param {number|null} params.budgetEur
 * @param {import('./types.js').Anomaly[]} params.anomalies - B2 anomalies
 * @returns {import('./types.js').ScoreResult}
 */
export function scoreBudgetRisk({ offerResult, offer, budgetEur, anomalies = [] }) {
  let score = 80;
  const reasons = [];
  const evs = [];

  // Structure risk
  if (offer.structure === OfferStructure.SPOT) {
    score -= 30;
    reasons.push('Structure Spot = exposition maximale au marche');
    evs.push(evidence('BR01', 'structure', 'SPOT'));
  } else if (offer.structure === OfferStructure.INDEXE) {
    score -= 15;
    reasons.push('Structure Indexee = exposition partielle au marche');
    evs.push(evidence('BR02', 'structure', 'INDEXE'));
  } else if (offer.structure === OfferStructure.HYBRIDE) {
    const spotShare = offer.pricing.spotSharePct || 0;
    const penalty = Math.round(spotShare * 25);
    score -= penalty;
    if (spotShare > 0.3) {
      reasons.push(`Hybride avec ${Math.round(spotShare * 100)}% spot = risque élevé`);
      evs.push(evidence('BR03', 'spotSharePct', spotShare));
    }
  }

  // Volatility
  const vol = offerResult.volatility || 0;
  const tcoP50 = offerResult.corridor?.tcoP50 || 0;
  const relVol = tcoP50 > 0 && isFinite(vol) ? vol / tcoP50 : 0;
  if (relVol > 0.2) {
    score -= 15;
    reasons.push(`Volatilité élevée (${(relVol * 100).toFixed(0)}% du TCO)`);
    evs.push(evidence('BR04', 'relativeVolatility', relVol));
  } else if (relVol > 0.1) {
    score -= 8;
    reasons.push(`Volatilite moderee (${(relVol * 100).toFixed(0)}% du TCO)`);
  }

  // Cap absent on indexed/spot
  if (
    (offer.structure === OfferStructure.INDEXE || offer.structure === OfferStructure.HYBRIDE) &&
    offer.pricing.capEurPerMwh == null
  ) {
    score -= 10;
    reasons.push('Pas de cap (plafond) de prix');
    evs.push(evidence('BR05', 'capEurPerMwh', null));
  }

  // Budget exceedance
  if (
    budgetEur != null &&
    offerResult.probExceedBudget != null &&
    offerResult.probExceedBudget > 0.2
  ) {
    score -= 15;
    reasons.push(
      `Probabilite de depasser le budget: ${(offerResult.probExceedBudget * 100).toFixed(0)}%`
    );
    evs.push(evidence('BR06', 'probExceedBudget', offerResult.probExceedBudget));
  }

  // B2 anomalies
  const highAnomalies = anomalies.filter((a) => a.severity === 'high' || a.severity === 'critical');
  if (highAnomalies.length > 0) {
    score -= Math.min(highAnomalies.length * 5, 15);
    reasons.push(`${highAnomalies.length} anomalie(s) facturation critique(s) (B2)`);
    evs.push(evidence('BR07', 'anomalyCount', highAnomalies.length, 'B2'));
  }

  score = Math.max(0, Math.min(100, score));
  return { score0to100: score, level: level(score), reasons, evidence: evs };
}

// ── Transparency Score ─────────────────────────────────────────────

/**
 * Score transparency: decomposition, intermediation, data terms
 * @param {Object} params
 * @param {import('./types.js').Offer} params.offer
 * @returns {import('./types.js').ScoreResult}
 */
export function scoreTransparency({ offer }) {
  let score = 85;
  const reasons = [];
  const evs = [];

  // Breakdown completeness
  const breakdown = offer.breakdown || [];
  const knownCount = breakdown.filter((b) => b.status === 'KNOWN').length;
  if (knownCount < 7) {
    score -= (7 - knownCount) * 10;
    reasons.push(`Decomposition incomplete: ${knownCount}/8 composantes connues`);
    evs.push(evidence('TR01', 'knownBreakdownCount', knownCount));
  }

  // Intermediation
  if (offer.intermediation) {
    if (offer.intermediation.passThroughPolicy === 'UNLIMITED') {
      score -= 20;
      reasons.push('Pass-through illimite (risque de couts caches)');
      evs.push(evidence('TR02', 'passThroughPolicy', 'UNLIMITED'));
    }
    if (!offer.intermediation.feeDisclosed) {
      score -= 15;
      reasons.push("Frais d'intermediation non divulgues");
      evs.push(evidence('TR03', 'feeDisclosed', false));
    }
    if (offer.intermediation.hasIntermediary && offer.intermediation.feeEurPerMwh > 5) {
      score -= 10;
      reasons.push(`Frais intermédiaires élevés: ${offer.intermediation.feeEurPerMwh} EUR/MWh`);
      evs.push(evidence('TR04', 'feeEurPerMwh', offer.intermediation.feeEurPerMwh));
    }
  }

  // Indexation clause clarity
  if (offer.contractTerms?.indexationClause === 'VAGUE') {
    score -= 15;
    reasons.push("Clause d'indexation floue");
    evs.push(evidence('TR05', 'indexationClause', 'VAGUE'));
  } else if (offer.contractTerms?.indexationClause === 'ABSENT') {
    score -= 10;
    reasons.push("Pas de clause d'indexation explicite");
    evs.push(evidence('TR06', 'indexationClause', 'ABSENT'));
  }

  score = Math.max(0, Math.min(100, score));
  return { score0to100: score, level: level(score), reasons, evidence: evs };
}

// ── Contract Risk Score ────────────────────────────────────────────

/**
 * Score contract risk: clauses, penalties, SLA
 * @param {Object} params
 * @param {import('./types.js').Offer} params.offer
 * @returns {import('./types.js').ScoreResult}
 */
export function scoreContractRisk({ offer }) {
  let score = 85;
  const reasons = [];
  const evs = [];
  const terms = offer.contractTerms || {};

  // Early termination
  if (terms.earlyTerminationPenalty === 'HIGH') {
    score -= 20;
    reasons.push('Pénalité de résiliation élevée');
    evs.push(evidence('CR01', 'earlyTerminationPenalty', 'HIGH'));
  } else if (terms.earlyTerminationPenalty === 'MODERATE') {
    score -= 10;
    reasons.push('Penalite de resiliation moderee');
    evs.push(evidence('CR02', 'earlyTerminationPenalty', 'MODERATE'));
  }

  // Notice period
  if (terms.noticePeriodDays > 180) {
    score -= 15;
    reasons.push(`Preavis tres long: ${terms.noticePeriodDays} jours`);
    evs.push(evidence('CR03', 'noticePeriodDays', terms.noticePeriodDays));
  } else if (terms.noticePeriodDays > 90) {
    score -= 8;
    reasons.push(`Preavis long: ${terms.noticePeriodDays} jours`);
  }

  // SLA
  if (terms.slaLevel === 'NONE') {
    score -= 15;
    reasons.push('Aucun SLA de service');
    evs.push(evidence('CR04', 'slaLevel', 'NONE'));
  }

  // Duration
  if (terms.durationMonths > 36) {
    score -= 10;
    reasons.push(`Duree longue: ${terms.durationMonths} mois`);
    evs.push(evidence('CR05', 'durationMonths', terms.durationMonths));
  }

  // Clause flags
  if (terms.clauseFlags?.length > 0) {
    score -= Math.min(terms.clauseFlags.length * 5, 20);
    reasons.push(`${terms.clauseFlags.length} clause(s) suspecte(s) detectee(s)`);
    evs.push(evidence('CR06', 'clauseFlags', terms.clauseFlags));
  }

  score = Math.max(0, Math.min(100, score));
  return { score0to100: score, level: level(score), reasons, evidence: evs };
}

// ── Data Readiness Score ───────────────────────────────────────────

/**
 * Score data readiness: quality and completeness of available data
 * @param {Object} params
 * @param {import('./types.js').Offer} params.offer
 * @param {import('./types.js').ConsumptionProfile} params.consumption
 * @param {import('./types.js').BillSummary} [params.billing]
 * @returns {import('./types.js').ScoreResult}
 */
export function scoreDataReadiness({ offer, consumption, billing }) {
  let score = 80;
  const reasons = [];
  const evs = [];
  const dataTerms = offer.dataTerms || {};

  // Curves access
  if (!dataTerms.curvesAccess) {
    score -= 15;
    reasons.push("Pas d'acces aux courbes de charge");
    evs.push(evidence('DR01', 'curvesAccess', false));
  }

  // D+1
  if (!dataTerms.dplus1) {
    score -= 10;
    reasons.push('Pas de données J+1');
    evs.push(evidence('DR02', 'dplus1', false));
  }

  // CSV/API export
  if (!dataTerms.csvExport && !dataTerms.apiAccess) {
    score -= 15;
    reasons.push('Aucun export CSV ni accès API');
    evs.push(evidence('DR03', 'exportAccess', false));
  }

  // Consumption granularity
  if (consumption?.granularity === 'monthly') {
    score -= 10;
    reasons.push('Limite : données mensuelles uniquement (pas horaire/journalier)');
    evs.push(evidence('DR04', 'granularity', 'monthly'));
  }

  // Consumption source
  if (consumption?.source === 'DEMO' || consumption?.source === 'DEFAULT') {
    score -= 15;
    reasons.push('Consommation basée sur données démo/estimées');
    evs.push(evidence('DR05', 'consumptionSource', consumption.source, consumption.source));
  }

  // Billing data
  if (!billing || billing.invoiceCount === 0) {
    score -= 15;
    reasons.push('Aucune facture historique disponible');
    evs.push(evidence('DR06', 'invoiceCount', 0, 'B2'));
  } else if (billing.invoiceCount < 12) {
    score -= 8;
    reasons.push(`Historique factures insuffisant: ${billing.invoiceCount} factures`);
    evs.push(evidence('DR07', 'invoiceCount', billing.invoiceCount, 'B2'));
  }

  score = Math.max(0, Math.min(100, score));
  return { score0to100: score, level: level(score), reasons, evidence: evs };
}

// ── Aggregate Score ────────────────────────────────────────────────

/**
 * Compute all 4 scores for an offer
 * @param {Object} params
 * @returns {{ budgetRisk: ScoreResult, transparency: ScoreResult, contractRisk: ScoreResult, dataReadiness: ScoreResult, overall: number }}
 */
export function scoreOffer(params) {
  const budgetRisk = scoreBudgetRisk(params);
  const transparency = scoreTransparency(params);
  const contractRisk = scoreContractRisk(params);
  const dataReadiness = scoreDataReadiness(params);

  // Weighted overall (equal by default — persona weighting done in recommend.js)
  const overall = Math.round(
    budgetRisk.score0to100 * 0.3 +
      transparency.score0to100 * 0.25 +
      contractRisk.score0to100 * 0.25 +
      dataReadiness.score0to100 * 0.2
  );

  return { budgetRisk, transparency, contractRisk, dataReadiness, overall };
}
