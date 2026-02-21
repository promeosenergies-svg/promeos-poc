/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * RFP — Note Decision + Pack RFP generation
 *
 * Generates structured export data for decision notes and RFP packs.
 * No PDF dependency — returns structured objects for UI rendering.
 */
import { BRIQUE3_VERSION, BREAKDOWN_LABELS, OfferStructure, Persona } from './types.js';
import { PERSONA_PROFILES } from './assumptions.js';

// ── Note Decision (1 page A4) ──────────────────────────────────────

/**
 * Generate a decision note summary
 * @param {Object} params
 * @param {import('./types.js').Recommendation} params.recommendation
 * @param {Object[]} params.scoredOffers - from recommendation._scoredOffers
 * @param {import('./engine.js').OfferResult[]} params.offerResults
 * @param {import('./types.js').Offer[]} params.offers
 * @param {string} params.persona
 * @param {number} params.annualKwh
 * @param {string} params.energyType
 * @param {number} params.horizonMonths
 * @param {string} params.scenarioPreset
 * @param {number|null} params.budgetEur
 * @param {string} [params.organizationName]
 * @returns {Object} structured decision note
 */
export function generateDecisionNote({
  recommendation,
  scoredOffers,
  offerResults,
  offers,
  persona,
  annualKwh,
  energyType,
  horizonMonths,
  scenarioPreset,
  budgetEur,
  organizationName = 'Organisation',
}) {
  const profile = PERSONA_PROFILES[persona] || PERSONA_PROFILES[Persona.DAF];
  const bestOffer = offers.find(o => o.id === recommendation.bestOfferId);
  const bestResult = offerResults.find(r => r.offerId === recommendation.bestOfferId);
  const bestScored = scoredOffers?.find(s => s.offerId === recommendation.bestOfferId);

  return {
    title: `Note de Decision — Achat Energie ${energyType}`,
    version: BRIQUE3_VERSION,
    generatedAt: new Date().toISOString(),
    organization: organizationName,

    // Context
    context: {
      persona: profile.label,
      energyType,
      annualKwh,
      horizonMonths,
      scenarioPreset,
      budgetEur,
      offerCount: offers.length,
    },

    // Recommendation
    recommendation: {
      bestOffer: bestOffer ? {
        id: bestOffer.id,
        supplier: bestOffer.supplierName,
        structure: bestOffer.structure,
        priceP50: bestResult?.corridor?.p50?.toFixed(1),
        tcoP50: bestResult?.corridor?.tcoP50?.toFixed(0),
        annualCostP50: bestResult?.annualCostP50?.toFixed(0),
      } : null,
      confidence: recommendation.confidence,
      confidenceReason: recommendation.confidenceReason,
      rationale: recommendation.rationaleBullets,
      tradeoffs: recommendation.tradeoffs,
    },

    // Comparison table
    comparison: (scoredOffers || []).map(s => ({
      offerId: s.offerId,
      supplier: s.supplierName,
      structure: s.structure,
      weightedScore: s.weightedScore,
      budgetRisk: s.scores.budgetRisk.score0to100,
      transparency: s.scores.transparency.score0to100,
      contractRisk: s.scores.contractRisk.score0to100,
      dataReadiness: s.scores.dataReadiness.score0to100,
      priceP50: s.result.corridor.p50.toFixed(1),
      whyNot: recommendation.whyNotOthers[s.offerId] || null,
    })),

    // Missing data
    missingData: recommendation.missingDataToImproveConfidence,

    // Limits
    limits: [
      'Simulation Monte Carlo (max 200 iterations) — valeur indicative',
      'Prix base sur hypotheses de marche (voir parametres)',
      'Scoring automatise — validation humaine recommandee',
      `Version moteur: ${BRIQUE3_VERSION}`,
    ],
  };
}

// ── Pack RFP (2-3 pages) ───────────────────────────────────────────

/**
 * Generate RFP comparison pack
 * @param {Object} params
 * @param {import('./engine.js').OfferResult[]} params.offerResults
 * @param {import('./types.js').Offer[]} params.offers
 * @param {Object[]} params.scoredOffers
 * @param {number} params.annualKwh
 * @param {string} params.energyType
 * @param {number} params.horizonMonths
 * @param {string} params.scenarioPreset
 * @param {number|null} params.budgetEur
 * @param {string} [params.organizationName]
 * @returns {Object} structured RFP pack
 */
export function generateRfpPack({
  offerResults,
  offers,
  scoredOffers,
  annualKwh,
  energyType,
  horizonMonths,
  scenarioPreset,
  budgetEur,
  organizationName = 'Organisation',
}) {
  return {
    title: `Pack RFP — Comparaison Offres ${energyType}`,
    version: BRIQUE3_VERSION,
    generatedAt: new Date().toISOString(),
    organization: organizationName,

    // Parameters
    parameters: {
      energyType,
      annualKwh,
      annualMwh: (annualKwh / 1000).toFixed(1),
      horizonMonths,
      scenarioPreset,
      budgetEur,
    },

    // Detailed offer sheets
    offerSheets: offers.map(offer => {
      const result = offerResults.find(r => r.offerId === offer.id);
      const scored = scoredOffers?.find(s => s.offerId === offer.id);

      return {
        offerId: offer.id,
        supplier: offer.supplierName,
        structure: offer.structure,

        // Pricing details
        pricing: formatPricingDetails(offer),

        // Corridor
        corridor: result ? {
          p10: result.corridor.p10.toFixed(1),
          p50: result.corridor.p50.toFixed(1),
          p90: result.corridor.p90.toFixed(1),
          tcoP50: result.corridor.tcoP50.toFixed(0),
          annualCostP50: result.annualCostP50.toFixed(0),
        } : null,

        // Risk metrics
        risk: result ? {
          volatility: result.volatility.toFixed(0),
          worstMonthEur: result.worstMonthEur.toFixed(0),
          probExceedBudget: result.probExceedBudget != null
            ? (result.probExceedBudget * 100).toFixed(1) + '%'
            : 'N/A',
          cvar90: result.cvar90.toFixed(0),
        } : null,

        // Breakdown
        breakdown: (offer.breakdown || []).map(b => ({
          component: BREAKDOWN_LABELS[b.component] || b.component,
          sharePct: (b.sharePct * 100).toFixed(1) + '%',
          eurPerMwh: b.eurPerMwh != null ? b.eurPerMwh.toFixed(2) : 'est.',
          status: b.status,
        })),

        // Contract terms
        contract: offer.contractTerms ? {
          duration: `${offer.contractTerms.durationMonths} mois`,
          notice: `${offer.contractTerms.noticePeriodDays} jours`,
          termination: offer.contractTerms.earlyTerminationPenalty,
          sla: offer.contractTerms.slaLevel,
          indexation: offer.contractTerms.indexationClause,
          green: offer.contractTerms.greenCertified ? 'Oui' : 'Non',
          flags: offer.contractTerms.clauseFlags || [],
        } : null,

        // Intermediation
        intermediation: offer.intermediation ? {
          hasIntermediary: offer.intermediation.hasIntermediary,
          feeDisclosed: offer.intermediation.feeDisclosed,
          fee: offer.intermediation.feeEurPerMwh != null
            ? offer.intermediation.feeEurPerMwh.toFixed(2) + ' EUR/MWh'
            : 'Non divulgue',
          passThrough: offer.intermediation.passThroughPolicy,
        } : null,

        // Scores
        scores: scored ? {
          budgetRisk: scored.scores.budgetRisk,
          transparency: scored.scores.transparency,
          contractRisk: scored.scores.contractRisk,
          dataReadiness: scored.scores.dataReadiness,
          weightedScore: scored.weightedScore,
        } : null,
      };
    }),
  };
}

// ── CSV Export ──────────────────────────────────────────────────────

/**
 * Generate CSV string for offer comparison
 * @param {Object[]} scoredOffers
 * @param {import('./engine.js').OfferResult[]} offerResults
 * @returns {string}
 */
export function generateComparisonCsv(scoredOffers, offerResults) {
  const headers = [
    'Fournisseur', 'Structure', 'Prix P50 (EUR/MWh)', 'TCO P50 (EUR)',
    'Cout annuel P50 (EUR)', 'Volatilite (EUR)', 'CVaR90 (EUR)',
    'Score Budget', 'Score Transparence', 'Score Contrat', 'Score Data',
    'Score Global',
  ];

  const rows = (scoredOffers || []).map(s => {
    const result = offerResults.find(r => r.offerId === s.offerId) || s.result;
    return [
      s.supplierName,
      s.structure,
      result.corridor.p50.toFixed(1),
      result.corridor.tcoP50.toFixed(0),
      result.annualCostP50.toFixed(0),
      result.volatility.toFixed(0),
      result.cvar90.toFixed(0),
      s.scores.budgetRisk.score0to100,
      s.scores.transparency.score0to100,
      s.scores.contractRisk.score0to100,
      s.scores.dataReadiness.score0to100,
      s.weightedScore,
    ];
  });

  const csvLines = [headers.join(';')];
  for (const row of rows) {
    csvLines.push(row.join(';'));
  }
  return csvLines.join('\n');
}

// ── Helpers ────────────────────────────────────────────────────────

function formatPricingDetails(offer) {
  const p = offer.pricing;
  switch (offer.structure) {
    case OfferStructure.FIXE:
      return { type: 'Fixe', fixedPrice: p.fixedPriceEurPerMwh + ' EUR/MWh' };
    case OfferStructure.INDEXE:
      return {
        type: 'Indexe',
        index: p.indexName || 'Spot',
        spread: (p.spreadEurPerMwh || 0) + ' EUR/MWh',
        cap: p.capEurPerMwh != null ? p.capEurPerMwh + ' EUR/MWh' : 'Sans',
        floor: p.floorEurPerMwh != null ? p.floorEurPerMwh + ' EUR/MWh' : 'Sans',
      };
    case OfferStructure.SPOT:
      return { type: 'Spot', index: 'Marche spot' };
    case OfferStructure.HYBRIDE:
      return {
        type: 'Hybride',
        fixedShare: (p.fixedSharePct * 100).toFixed(0) + '%',
        fixedPrice: p.fixedPriceEurPerMwh + ' EUR/MWh',
        indexedShare: (p.indexedSharePct * 100).toFixed(0) + '%',
        spotShare: (p.spotSharePct * 100).toFixed(0) + '%',
        cap: p.capEurPerMwh != null ? p.capEurPerMwh + ' EUR/MWh' : 'Sans',
      };
    default:
      return { type: offer.structure };
  }
}
