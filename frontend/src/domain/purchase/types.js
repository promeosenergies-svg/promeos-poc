/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Types & Constants (JSDoc typed)
 *
 * All domain types for the Purchase Assistant.
 * Pure JS — no TS dependency — but documented with JSDoc for IDE support.
 */

// ── Enums / Constants ──────────────────────────────────────────────

export const EnergyType = /** @type {const} */ ({ ELEC: 'ELEC', GAZ: 'GAZ' });

export const OfferStructure = /** @type {const} */ ({
  FIXE: 'FIXE',
  INDEXE: 'INDEXE',
  SPOT: 'SPOT',
  HYBRIDE: 'HYBRIDE',
});

export const ScenarioPreset = /** @type {const} */ ({
  STABLE: 'STABLE',
  VOLATILE: 'VOLATILE',
  DEFENSIVE: 'DEFENSIVE',
});

export const Persona = /** @type {const} */ ({
  DG: 'DG',
  DAF: 'DAF',
  ACHETEUR: 'ACHETEUR',
  RESP_ENERGIE: 'RESP_ENERGIE',
});

export const Confidence = /** @type {const} */ ({
  LOW: 'LOW',
  MEDIUM: 'MEDIUM',
  HIGH: 'HIGH',
});

export const ScoreLevel = /** @type {const} */ ({
  GREEN: 'GREEN',
  ORANGE: 'ORANGE',
  RED: 'RED',
});

export const EvidenceSource = /** @type {const} */ ({
  USER: 'USER',
  B1: 'B1',
  B2: 'B2',
  DEMO: 'DEMO',
  DEFAULT: 'DEFAULT',
});

export const BreakdownComponentType = /** @type {const} */ ({
  FOURNITURE: 'FOURNITURE',
  ACHEMINEMENT: 'ACHEMINEMENT',
  TAXES_CSPE: 'TAXES_CSPE',
  CTA: 'CTA',
  TVA: 'TVA',
  CEE: 'CEE',
  CAPACITE: 'CAPACITE',
  ABONNEMENT: 'ABONNEMENT',
});

export const BREAKDOWN_LABELS = {
  FOURNITURE: 'Fourniture (energie)',
  ACHEMINEMENT: 'Acheminement (TURPE)',
  TAXES_CSPE: 'Taxes & CSPE',
  CTA: 'CTA',
  TVA: 'TVA',
  CEE: 'CEE',
  CAPACITE: 'Capacite',
  ABONNEMENT: 'Abonnement / fixe',
};

export const BREAKDOWN_DEFAULTS_ELEC = {
  FOURNITURE: 0.35,
  ACHEMINEMENT: 0.28,
  TAXES_CSPE: 0.15,
  CTA: 0.03,
  TVA: 0.10,
  CEE: 0.04,
  CAPACITE: 0.03,
  ABONNEMENT: 0.02,
};

export const BREAKDOWN_DEFAULTS_GAZ = {
  FOURNITURE: 0.40,
  ACHEMINEMENT: 0.20,
  TAXES_CSPE: 0.18,
  CTA: 0.02,
  TVA: 0.10,
  CEE: 0.05,
  CAPACITE: 0.00,
  ABONNEMENT: 0.05,
};

// Seasonality coefficients (12 months, normalized to avg=1.0)
export const SEASONALITY_ELEC = [1.15, 1.10, 1.05, 0.95, 0.85, 0.80, 0.78, 0.80, 0.90, 1.00, 1.10, 1.15];
export const SEASONALITY_GAZ  = [1.45, 1.35, 1.15, 0.85, 0.60, 0.45, 0.40, 0.45, 0.65, 0.95, 1.25, 1.45];

// ── Factory Helpers ────────────────────────────────────────────────

/**
 * @typedef {Object} Organization
 * @property {string} id
 * @property {string} name
 * @property {string} [siren]
 * @property {LegalEntity[]} entities
 */

/**
 * @typedef {Object} LegalEntity
 * @property {string} id
 * @property {string} name
 * @property {string} [siret]
 * @property {string} [nafCode]
 * @property {Site[]} sites
 */

/**
 * @typedef {Object} Site
 * @property {number} id
 * @property {string} name
 * @property {string} city
 * @property {string} [usage]
 * @property {number} surfaceM2
 * @property {string} energyType
 * @property {ConsumptionProfile} consumption
 * @property {BillSummary} [billing]
 * @property {Anomaly[]} [anomalies]
 */

/**
 * @typedef {Object} ConsumptionProfile
 * @property {number} annualKwh
 * @property {number[]} [monthlyKwh] - 12 months, nullable
 * @property {string} granularity - 'monthly'|'daily'|'hourly'
 * @property {number} profileFactor
 * @property {number[]} seasonality - 12 coefficients
 * @property {string} source - 'B1'|'B2'|'DEMO'|'USER'
 */

/**
 * @typedef {Object} BillSummary
 * @property {number} invoiceCount
 * @property {number} totalEur
 * @property {number} totalKwh
 * @property {number} avgPricePerKwh
 * @property {number} anomalyCount
 * @property {number} estimatedLossEur
 */

/**
 * @typedef {Object} Anomaly
 * @property {string} type
 * @property {string} severity
 * @property {string} message
 * @property {number} [estimatedLossEur]
 */

/**
 * @typedef {Object} Offer
 * @property {string} id
 * @property {string} supplierName
 * @property {string} structure - FIXE|INDEXE|SPOT|HYBRIDE
 * @property {PricingModel} pricing
 * @property {BreakdownLine[]} breakdown
 * @property {ContractTerms} contractTerms
 * @property {Intermediation} intermediation
 * @property {DataTerms} dataTerms
 * @property {string} [rawContractText] - optional raw text for clause scanning
 */

/**
 * @typedef {Object} PricingModel
 * @property {number} fixedPriceEurPerMwh
 * @property {string} [indexName]
 * @property {number} [spreadEurPerMwh]
 * @property {number} [capEurPerMwh]
 * @property {number} [floorEurPerMwh]
 * @property {number} fixedSharePct - 0..1 for hybride
 * @property {number} indexedSharePct
 * @property {number} spotSharePct
 */

/**
 * @typedef {Object} BreakdownLine
 * @property {string} component - key from BreakdownComponentType
 * @property {number} sharePct - 0..1
 * @property {number} [eurPerMwh]
 * @property {string} status - 'KNOWN'|'ESTIMATED'|'UNKNOWN'
 */

/**
 * @typedef {Object} ContractTerms
 * @property {number} durationMonths
 * @property {number} noticePeriodDays
 * @property {string} earlyTerminationPenalty - 'NONE'|'LOW'|'MODERATE'|'HIGH'
 * @property {string} indexationClause - 'CLEAR'|'VAGUE'|'ABSENT'
 * @property {string} slaLevel - 'NONE'|'BASIC'|'PREMIUM'
 * @property {boolean} greenCertified
 * @property {string[]} [clauseFlags] - red flag clause tags
 */

/**
 * @typedef {Object} Intermediation
 * @property {boolean} hasIntermediary
 * @property {boolean} feeDisclosed
 * @property {number} [feeEurPerMwh]
 * @property {string} passThroughPolicy - 'FULL'|'PARTIAL'|'UNLIMITED'
 */

/**
 * @typedef {Object} DataTerms
 * @property {boolean} curvesAccess
 * @property {boolean} dplus1
 * @property {boolean} csvExport
 * @property {boolean} apiAccess
 */

/**
 * @typedef {Object} ScoreResult
 * @property {number} score0to100
 * @property {'GREEN'|'ORANGE'|'RED'} level
 * @property {string[]} reasons
 * @property {Evidence[]} evidence
 */

/**
 * @typedef {Object} Evidence
 * @property {string} ruleId
 * @property {string} field
 * @property {*} value
 * @property {'USER'|'B1'|'B2'|'DEMO'|'DEFAULT'} source
 */

/**
 * @typedef {Object} Recommendation
 * @property {string} bestOfferId
 * @property {string[]} rationaleBullets - max 5
 * @property {string[]} tradeoffs - max 3
 * @property {Object.<string, string>} whyNotOthers - offerId -> reason
 * @property {'LOW'|'MEDIUM'|'HIGH'} confidence
 * @property {string} confidenceReason
 * @property {string[]} missingDataToImproveConfidence
 */

/**
 * @typedef {Object} CorridorResult
 * @property {number} p10
 * @property {number} p50
 * @property {number} p90
 * @property {number} mean
 * @property {number} tcoP10
 * @property {number} tcoP50
 * @property {number} tcoP90
 * @property {number[]} distribution - all MC samples
 */

/**
 * @typedef {Object} DecisionRecord
 * @property {string} decisionId
 * @property {string} timestamp
 * @property {string} version
 * @property {Object} inputs
 * @property {Object} params
 * @property {Object} outputs
 * @property {Object} scores
 * @property {Object} recommendation
 * @property {string[]} limits
 */

// Version
export const BRIQUE3_VERSION = '3.0.0';
