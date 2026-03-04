/**
 * PROMEOS — Single source of truth for thresholds & status configuration.
 * Replaces all hardcoded magic numbers scattered across Cockpit, Patrimoine,
 * Site360, dashboardEssentials, and CommandCenter.
 */

// ── Risk thresholds (EUR) ────────────────────────────────────────────────────

export const RISK_THRESHOLDS = {
  /** Org-level risk — used in Cockpit, CommandCenter, dashboardEssentials */
  org: { crit: 50_000, warn: 10_000 },
  /** Site-level risk — used in Patrimoine table row colors */
  site: { crit: 10_000, warn: 3_000 },
};

// ── Coverage thresholds (%) ──────────────────────────────────────────────────

export const COVERAGE_THRESHOLDS = {
  /** Below this → suspicious consistency if 100% conforme */
  suspicious: 30,
  /** Below this → 'warn' status on KPI tile */
  warn: 50,
  /** Below this → opportunity/briefing item */
  opportunity: 80,
};

// ── Conformity thresholds (%) ────────────────────────────────────────────────

export const CONFORMITY_THRESHOLDS = {
  /** >= this with 0 non-conformes → 'positive' executive bullet */
  positive: 80,
  /** >= this → 'warn', below → 'negative' */
  warn: 50,
};

// ── Maturity / readiness score thresholds (%) ────────────────────────────────

export const MATURITY_THRESHOLDS = {
  /** Below this → 'crit' */
  crit: 40,
  /** Below this → 'warn', above → 'ok' */
  warn: 70,
};

// ── Readiness score weights ──────────────────────────────────────────────────

export const READINESS_WEIGHTS = {
  data: 0.3,
  conformity: 0.4,
  actions: 0.3,
};

export const ACTIONS_SCORE = {
  withIssues: 55,
  noIssues: 80,
};

// ── Data Readiness Gate thresholds ───────────────────────────────────────────

export const READINESS_GATE = {
  /** Consommation: < partialPct% couverture → PARTIEL, 0 → KO */
  conso: { partialPct: 80 },
  /** Facturation: < ko mois → KO, < partial mois → PARTIEL */
  facturation: { ko: 3, partial: 12 },
  /** OPERAT: > issueThreshold issues ouvertes → PARTIEL */
  operat: { issueThreshold: 2 },
};

// ── Anomaly thresholds ───────────────────────────────────────────────────────

export const ANOMALY_THRESHOLDS = {
  /** >= this → red badge, below → amber */
  critical: 5,
};

// ── Status configuration (conformité) ────────────────────────────────────────

export const STATUS_CONFIG = {
  conforme: { variant: 'ok', label: 'Conforme' },
  non_conforme: { variant: 'crit', label: 'Non conforme' },
  a_risque: { variant: 'warn', label: 'À risque' },
  a_evaluer: { variant: 'neutral', label: 'À évaluer' },
  derogation: { variant: 'info', label: 'Dérogation' },
};

/**
 * Get status badge props for a conformité status string.
 * Returns { variant, label } — compatible with <Badge status={variant}>.
 */
export function getStatusBadgeProps(status) {
  return STATUS_CONFIG[status] || { variant: 'neutral', label: status || 'Non défini' };
}

// ── Risk status helper ───────────────────────────────────────────────────────

/**
 * Compute risk status from EUR amount + threshold config.
 * @param {number} amount
 * @param {{ crit: number, warn: number }} thresholds
 * @returns {'crit' | 'warn' | 'ok'}
 */
export function getRiskStatus(amount, thresholds = RISK_THRESHOLDS.org) {
  if (amount > thresholds.crit) return 'crit';
  if (amount > thresholds.warn) return 'warn';
  return 'ok';
}

// ── Severity ranking & badge mapping ───────────────────────────────────────

/** Severity sort order (lower = more urgent). Used by dashboardEssentials, Site360. */
export const SEVERITY_RANK = {
  critical: 0,
  high: 1,
  warn: 2,
  medium: 3,
  info: 4,
  low: 5,
};

/** API severity → Badge variant mapping. Used by Site360 KB results. */
export const SEV_BADGE = {
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
};
