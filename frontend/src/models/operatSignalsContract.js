/**
 * PROMEOS V39 — operatSignalsContract
 *
 * Normalise les signaux OPERAT/tertiaire pour le cockpit.
 * Pattern identique a complianceSignalsContract (V35) / purchaseSignalsContract (V36).
 *
 * Exports:
 *   normalizeOperatSignals(raw)   → OperatSignals | EMPTY
 *   isOperatAvailable(signals)    → boolean
 *   EMPTY_OPERAT_SIGNALS          → safe fallback
 */

// ── Empty fallback ──────────────────────────────────────────────────────────

export const EMPTY_OPERAT_SIGNALS = Object.freeze({
  totalEfa: 0,
  activeEfa: 0,
  draftEfa: 0,
  closedEfa: 0,
  openIssues: 0,
  criticalIssues: 0,
  _empty: true,
});

// ── Normalizer ──────────────────────────────────────────────────────────────

/**
 * @param {object} raw — reponse de GET /api/tertiaire/dashboard
 * @returns {OperatSignals}
 */
export function normalizeOperatSignals(raw) {
  if (!raw || typeof raw !== 'object') return EMPTY_OPERAT_SIGNALS;

  const totalEfa = Math.max(0, Number(raw.total_efa) || 0);
  const activeEfa = Math.max(0, Number(raw.active) || 0);
  const draftEfa = Math.max(0, Number(raw.draft) || 0);
  const closedEfa = Math.max(0, Number(raw.closed) || 0);
  const openIssues = Math.max(0, Number(raw.open_issues) || 0);
  const criticalIssues = Math.max(0, Number(raw.critical_issues) || 0);

  if (totalEfa === 0 && openIssues === 0) return EMPTY_OPERAT_SIGNALS;

  return {
    totalEfa,
    activeEfa,
    draftEfa,
    closedEfa,
    openIssues,
    criticalIssues,
    _empty: false,
  };
}

// ── Availability check ──────────────────────────────────────────────────────

/**
 * @param {OperatSignals|null|undefined} signals
 * @returns {boolean}
 */
export function isOperatAvailable(signals) {
  if (!signals || signals._empty) return false;
  return signals.totalEfa > 0;
}
