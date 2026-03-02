/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Recommend — Persona-based recommendation engine
 *
 * Produces a Recommendation with confidence + explainability.
 */
import { Persona, Confidence, OfferStructure } from './types.js';
import { PERSONA_PROFILES } from './assumptions.js';
import { scoreOffer } from './scoring.js';

// ── Confidence Computation ─────────────────────────────────────────

/**
 * Determine confidence level based on data quality and score spread
 * @param {Object} params
 * @param {Object[]} scoredOffers
 * @param {import('./types.js').ConsumptionProfile} consumption
 * @param {import('./types.js').BillSummary} [billing]
 * @returns {{ confidence: string, reason: string, missingData: string[] }}
 */
function computeConfidence(scoredOffers, consumption, billing) {
  const missingData = [];
  let confidenceScore = 100;

  // Data completeness checks
  if (!consumption || consumption.source === 'DEMO') {
    confidenceScore -= 25;
    missingData.push('Donnees de consommation reelles (non demo)');
  }
  if (consumption?.granularity === 'monthly') {
    confidenceScore -= 10;
    missingData.push('Courbes de charge horaires ou journalieres');
  }
  if (!billing || billing.invoiceCount === 0) {
    confidenceScore -= 20;
    missingData.push('Historique de facturation');
  }
  if (billing && billing.anomalyCount > 5) {
    confidenceScore -= 10;
    missingData.push('Resolution des anomalies de facturation');
  }

  // Score differentiation
  if (scoredOffers.length > 1) {
    const scores = scoredOffers.map(s => s.weightedScore);
    const spread = Math.max(...scores) - Math.min(...scores);
    if (spread < 5) {
      confidenceScore -= 15;
      missingData.push('Offres tres similaires — ajoutez des criteres differenciants');
    }
  }

  // Breakdown completeness
  const avgBreakdown = scoredOffers.reduce((sum, s) => sum + (s.scores.transparency.score0to100 || 0), 0) / (scoredOffers.length || 1);
  if (avgBreakdown < 50) {
    confidenceScore -= 15;
    missingData.push('Decompositions tarifaires completes');
  }

  let confidence, reason;
  if (confidenceScore >= 70) {
    confidence = Confidence.HIGH;
    reason = 'Donnees suffisantes pour une recommandation fiable';
  } else if (confidenceScore >= 40) {
    confidence = Confidence.MEDIUM;
    reason = 'Recommandation indicative — donnees partiellement disponibles';
  } else {
    confidence = Confidence.LOW;
    reason = 'Confiance faible — donnees insuffisantes ou estimees';
  }

  return { confidence, reason, missingData };
}

// ── Persona-Weighted Scoring ───────────────────────────────────────

/**
 * Score an offer using persona-specific weights
 * @param {Object} scores - { budgetRisk, transparency, contractRisk, dataReadiness }
 * @param {string} persona - Persona key
 * @returns {number} weighted score 0-100
 */
function personaWeightedScore(scores, persona) {
  const profile = PERSONA_PROFILES[persona] || PERSONA_PROFILES[Persona.DAF];
  const w = profile.weights;
  return Math.round(
    scores.budgetRisk.score0to100 * w.budgetRisk +
    scores.transparency.score0to100 * w.transparency +
    scores.contractRisk.score0to100 * w.contractRisk +
    scores.dataReadiness.score0to100 * w.dataReadiness
  );
}

// ── Main Recommend Function ────────────────────────────────────────

/**
 * Generate a recommendation from scored offer results
 * @param {Object} params
 * @param {import('./engine.js').OfferResult[]} params.offerResults
 * @param {import('./types.js').Offer[]} params.offers
 * @param {string} params.persona
 * @param {number|null} params.budgetEur
 * @param {import('./types.js').ConsumptionProfile} params.consumption
 * @param {import('./types.js').BillSummary} [params.billing]
 * @param {import('./types.js').Anomaly[]} [params.anomalies]
 * @returns {import('./types.js').Recommendation}
 */
export function recommend({ offerResults, offers, persona, budgetEur, consumption, billing, anomalies = [] }) {
  const profile = PERSONA_PROFILES[persona] || PERSONA_PROFILES[Persona.DAF];

  // Score each offer
  const scoredOffers = offerResults.map(result => {
    const offer = offers.find(o => o.id === result.offerId);
    if (!offer) return null;

    const scores = scoreOffer({
      offerResult: result,
      offer,
      budgetEur,
      anomalies,
      consumption,
      billing,
    });

    const weightedScore = personaWeightedScore(scores, persona);

    return {
      offerId: offer.id,
      supplierName: offer.supplierName,
      structure: offer.structure,
      scores,
      weightedScore,
      result,
    };
  }).filter(Boolean);

  if (scoredOffers.length === 0) {
    return {
      bestOfferId: null,
      rationaleBullets: ['Aucune offre a evaluer'],
      tradeoffs: [],
      whyNotOthers: {},
      confidence: Confidence.LOW,
      confidenceReason: 'Aucune offre disponible',
      missingDataToImproveConfidence: ['Ajouter des offres pour la comparaison'],
    };
  }

  // Sort by weighted score descending
  scoredOffers.sort((a, b) => b.weightedScore - a.weightedScore);
  const best = scoredOffers[0];

  // Confidence
  const { confidence, reason: confidenceReason, missingData } = computeConfidence(scoredOffers, consumption, billing);

  // Rationale bullets (max 5)
  const rationaleBullets = [];

  // Price
  const bestPrice = best.result.corridor.p50;
  rationaleBullets.push(`Prix moyen P50: ${bestPrice.toFixed(1)} EUR/MWh — meilleur compromis ${profile.label}`);

  // Corridor width
  const corridorWidth = best.result.corridor.p90 - best.result.corridor.p10;
  if (corridorWidth < 30) {
    rationaleBullets.push(`Corridor serre (P10-P90: ${corridorWidth.toFixed(0)} EUR/MWh) = bonne visibilite budgetaire`);
  }

  // Budget risk
  if (best.scores.budgetRisk.level === 'GREEN') {
    rationaleBullets.push('Risque budgetaire faible (score vert)');
  }

  // Transparency
  if (best.scores.transparency.level === 'GREEN') {
    rationaleBullets.push('Transparence tarifaire satisfaisante');
  } else if (best.scores.transparency.level === 'RED') {
    rationaleBullets.push('Attention: transparence insuffisante — verifier la decomposition');
  }

  // Persona-specific
  if (persona === Persona.DG && best.structure === OfferStructure.FIXE) {
    rationaleBullets.push('Prix fixe = simplicite et previsibilite pour la Direction');
  }
  if (persona === Persona.RESP_ENERGIE && best.structure === OfferStructure.HYBRIDE) {
    rationaleBullets.push('Structure hybride = optimisation technique avec couverture partielle');
  }

  // Tradeoffs (max 3)
  const tradeoffs = [];
  if (best.result.volatility > 0) {
    tradeoffs.push(`Volatilite residuelle: ${best.result.volatility.toFixed(0)} EUR`);
  }
  if (best.scores.contractRisk.level !== 'GREEN' && best.scores.contractRisk.reasons?.length > 0) {
    tradeoffs.push('Risque contractuel a negocier: ' + best.scores.contractRisk.reasons[0]);
  }
  if (best.scores.dataReadiness.level !== 'GREEN' && best.scores.dataReadiness.reasons?.length > 0) {
    tradeoffs.push('Donnees incompletes: ' + best.scores.dataReadiness.reasons[0]);
  }

  // Why not others
  const whyNotOthers = {};
  for (const other of scoredOffers.slice(1)) {
    const diff = best.weightedScore - other.weightedScore;
    const reasons = [];
    if (other.result.corridor.p50 > best.result.corridor.p50 * 1.05) {
      reasons.push('Prix P50 plus eleve');
    }
    if (other.scores.budgetRisk.score0to100 < best.scores.budgetRisk.score0to100 - 10) {
      reasons.push('Risque budgetaire superieur');
    }
    if (other.scores.transparency.score0to100 < best.scores.transparency.score0to100 - 10) {
      reasons.push('Transparence inferieure');
    }
    whyNotOthers[other.offerId] = reasons.length > 0
      ? reasons.join(' ; ')
      : `Score global inferieur de ${diff} pts`;
  }

  return {
    bestOfferId: best.offerId,
    rationaleBullets: rationaleBullets.slice(0, 5),
    tradeoffs: tradeoffs.slice(0, 3),
    whyNotOthers,
    confidence,
    confidenceReason,
    missingDataToImproveConfidence: missingData,
    // Extra data for UI
    _scoredOffers: scoredOffers,
  };
}
