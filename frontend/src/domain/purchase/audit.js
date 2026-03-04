/**
 * PROMEOS — Brique 3 "Achat post-ARENH"
 * Audit — Append-only decision trail
 *
 * Stores decisions in localStorage as JSONL (one JSON per line).
 * Append-only: no update, no delete. Exportable as JSONL or JSON.
 */
import { BRIQUE3_VERSION } from './types.js';

const STORAGE_KEY = 'promeos_b3_audit_log';

// ── Core API ───────────────────────────────────────────────────────

/**
 * Append a decision record to the audit trail
 * @param {Object} params
 * @param {Object} params.inputs - Wizard inputs (sites, energy, persona, horizon, etc.)
 * @param {Object} params.params - Engine params (mcIterations, mcSeed, scenarioPreset)
 * @param {import('./engine.js').OfferResult[]} params.offerResults
 * @param {Object} params.scores - Per-offer scores
 * @param {import('./types.js').Recommendation} params.recommendation
 * @param {string} params.action - 'COMPUTE'|'ACCEPT'|'REJECT'|'EXPORT'
 * @param {string} [params.userId]
 * @param {string[]} [params.limits]
 * @returns {DecisionRecord}
 */
export function appendDecision({
  inputs,
  params,
  offerResults,
  scores,
  recommendation,
  action,
  userId = 'anonymous',
  limits = [],
}) {
  const record = {
    decisionId: generateId(),
    timestamp: new Date().toISOString(),
    version: BRIQUE3_VERSION,
    action,
    userId,
    inputs: sanitizeForAudit(inputs),
    params: sanitizeForAudit(params),
    outputs: {
      offerCount: offerResults?.length || 0,
      bestOfferId: recommendation?.bestOfferId || null,
      confidence: recommendation?.confidence || null,
      offerResults: (offerResults || []).map((r) => ({
        offerId: r.offerId,
        supplierName: r.supplierName,
        structure: r.structure,
        priceP50: r.corridor?.p50,
        tcoP50: r.corridor?.tcoP50,
        volatility: r.volatility,
        cvar90: r.cvar90,
      })),
    },
    scores: sanitizeForAudit(scores),
    recommendation: recommendation
      ? {
          bestOfferId: recommendation.bestOfferId,
          confidence: recommendation.confidence,
          confidenceReason: recommendation.confidenceReason,
          rationaleBullets: recommendation.rationaleBullets,
          tradeoffs: recommendation.tradeoffs,
          missingData: recommendation.missingDataToImproveConfidence,
        }
      : null,
    limits: [
      ...limits,
      `Version moteur: ${BRIQUE3_VERSION}`,
      'Simulation Monte Carlo — valeur indicative',
    ],
  };

  // Append to localStorage
  const existing = getAuditLog();
  existing.push(record);
  saveAuditLog(existing);

  return record;
}

/**
 * Get all audit records
 * @returns {DecisionRecord[]}
 */
export function getAuditLog() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

/**
 * Get audit record count
 * @returns {number}
 */
export function getAuditCount() {
  return getAuditLog().length;
}

/**
 * Get the last N audit records (most recent first)
 * @param {number} n
 * @returns {DecisionRecord[]}
 */
export function getRecentDecisions(n = 10) {
  const log = getAuditLog();
  return log.slice(-n).reverse();
}

/**
 * Get a specific decision by ID
 * @param {string} decisionId
 * @returns {DecisionRecord|null}
 */
export function getDecisionById(decisionId) {
  const log = getAuditLog();
  return log.find((r) => r.decisionId === decisionId) || null;
}

// ── Export ──────────────────────────────────────────────────────────

/**
 * Export audit trail as JSONL string (one JSON object per line)
 * @returns {string}
 */
export function exportAsJsonl() {
  const log = getAuditLog();
  return log.map((r) => JSON.stringify(r)).join('\n');
}

/**
 * Export audit trail as JSON array string
 * @returns {string}
 */
export function exportAsJson() {
  const log = getAuditLog();
  return JSON.stringify(log, null, 2);
}

/**
 * Download audit trail as a file
 * @param {'jsonl'|'json'} format
 */
export function downloadAuditFile(format = 'jsonl') {
  const content = format === 'json' ? exportAsJson() : exportAsJsonl();
  const mimeType = format === 'json' ? 'application/json' : 'application/x-ndjson';
  const filename = `promeos_b3_audit_${new Date().toISOString().slice(0, 10)}.${format}`;

  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── Internal ───────────────────────────────────────────────────────

function saveAuditLog(log) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(log));
  } catch {
    // localStorage full — keep last 100 records
    try {
      const trimmed = log.slice(-100);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // localStorage completely unavailable (private browsing, sandbox)
    }
  }
}

function generateId() {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `b3-${ts}-${rand}`;
}

function sanitizeForAudit(obj) {
  if (!obj) return null;
  try {
    // Deep clone and remove circular refs / functions
    return JSON.parse(
      JSON.stringify(obj, (key, value) => {
        if (key === '_scoredOffers') return undefined; // strip large internal data
        if (key === 'distribution') return undefined; // strip MC distribution arrays
        if (typeof value === 'function') return undefined;
        return value;
      })
    );
  } catch {
    return null;
  }
}

/**
 * Clear audit log (for testing only)
 * @private
 */
export function _clearAuditLog() {
  localStorage.removeItem(STORAGE_KEY);
}
