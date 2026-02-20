/**
 * PROMEOS — ComplianceSignalsContract V35
 * Contract pour les signaux conformite (OPERAT / BACS / APER).
 *
 * Ce module definit la structure attendue et fournit des helpers
 * de validation / normalisation. Aucune implementation OPERAT ici —
 * juste le "contrat" pour brancher plus tard.
 *
 * Exports:
 *   normalizeComplianceSignals(raw)  → ComplianceSignals | null
 *   EMPTY_COMPLIANCE_SIGNALS         → valeur par defaut (safe)
 *   isComplianceAvailable(signals)   → boolean
 */

/**
 * @typedef {object} ComplianceSignal
 * @property {string}  source          — ex: 'operat', 'bacs', 'aper', 'decret_tertiaire'
 * @property {string}  code            — ex: 'DT-2030', 'BACS-CL1'
 * @property {'critical'|'high'|'medium'|'low'} severity
 * @property {string}  [due_date]      — ISO date echeance (ex: '2030-12-31')
 * @property {string}  [proof_expected] — description preuve attendue
 * @property {string}  [owner_expected] — role responsable
 * @property {string}  [label]         — description humaine FR
 */

/**
 * @typedef {object} ComplianceSignals
 * @property {ComplianceSignal[]} signals
 * @property {{ total: number, with_proof: number, with_due_date: number }} coverage
 * @property {string[]} missing — champs manquants identifies
 */

export const EMPTY_COMPLIANCE_SIGNALS = Object.freeze({
  signals: [],
  coverage: { total: 0, with_proof: 0, with_due_date: 0 },
  missing: [],
});

/**
 * Normalise un objet brut en ComplianceSignals.
 * Retourne EMPTY_COMPLIANCE_SIGNALS si input invalide.
 *
 * @param {any} raw
 * @returns {ComplianceSignals}
 */
export function normalizeComplianceSignals(raw) {
  if (!raw || typeof raw !== 'object') return EMPTY_COMPLIANCE_SIGNALS;

  const signals = Array.isArray(raw.signals)
    ? raw.signals.filter((s) => s && typeof s.source === 'string' && typeof s.code === 'string')
    : [];

  if (signals.length === 0) return EMPTY_COMPLIANCE_SIGNALS;

  const coverage = {
    total: signals.length,
    with_proof: signals.filter((s) => !!s.proof_expected).length,
    with_due_date: signals.filter((s) => !!s.due_date).length,
  };

  const missing = [];
  if (coverage.with_proof < coverage.total) missing.push('proof_expected');
  if (coverage.with_due_date < coverage.total) missing.push('due_date');

  return { signals, coverage, missing };
}

/**
 * Verifie si des signaux conformite sont disponibles et non vides.
 *
 * @param {ComplianceSignals|null|undefined} signals
 * @returns {boolean}
 */
export function isComplianceAvailable(signals) {
  return !!(signals && signals.signals && signals.signals.length > 0);
}
