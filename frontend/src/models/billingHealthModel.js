/**
 * PROMEOS — billingHealthModel.js (v2.1)
 * Pure model layer for billing-domain health signals.
 * No React imports — fully testable in isolation.
 *
 * Exports:
 *   buildBillingWatchlist(insights)           → WatchItem[] (max 5, severity-sorted)
 *   computeBillingHealthState(summary, insights) → HealthState
 *   computeHealthTrend(current, previous)     → { direction, label }
 *   buildSnapshotKey(domain, scope?)           → scoped localStorage key
 *   loadHealthSnapshot(domain, scope?)        → snapshot | null (14-day retention)
 *   saveHealthSnapshot(domain, state, scope?) → void (with purge)
 */
import { SEVERITY_RANK } from '../lib/constants';
import { computeHealthState } from './dashboardEssentials';

// ── Business-language label templates ─────────────────────────────────────────
// Zero tech jargon — every label must be understandable by a CFO.

const BILLING_REASON_LABELS = {
  shadow_gap: (n) =>
    `${n} écart${n > 1 ? 's' : ''} détecté${n > 1 ? 's' : ''} entre factures et consommation réelle`,
  unit_price_high: (n) =>
    `${n} écart${n > 1 ? 's' : ''} de prix détecté${n > 1 ? 's' : ''} sur vos factures`,
  duplicate_invoice: (n) =>
    `${n} doublon${n > 1 ? 's' : ''} de facture${n > 1 ? 's' : ''} identifié${n > 1 ? 's' : ''}`,
  missing_period: (n) =>
    `${n} période${n > 1 ? 's' : ''} de facturation manquante${n > 1 ? 's' : ''}`,
  period_too_long: (n) => `${n} facture${n > 1 ? 's' : ''} avec une période anormalement longue`,
  negative_kwh: (n) => `${n} facture${n > 1 ? 's' : ''} avec consommation négative`,
  zero_amount: (n) => `${n} facture${n > 1 ? 's' : ''} à montant zéro`,
  lines_sum_mismatch: (n) => `${n} écart${n > 1 ? 's' : ''} entre le détail et le total facture`,
  consumption_spike: (n) =>
    `${n} pic${n > 1 ? 's' : ''} de consommation inhabituel${n > 1 ? 's' : ''}`,
  price_drift: (n) =>
    `${n} dérive${n > 1 ? 's' : ''} de prix détectée${n > 1 ? 's' : ''} dans le temps`,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

export function isActiveInsight(i) {
  return !i.insight_status || i.insight_status === 'open' || i.insight_status === 'ack';
}

// ── buildBillingWatchlist ─────────────────────────────────────────────────────

/**
 * Build billing-domain watchlist from raw insights array.
 * Groups by type, picks highest severity per group, generates business labels.
 * Filters to active insights only (open, ack).
 *
 * @param {object[]} insights — from getBillingInsights() API
 * @returns {WatchItem[]} — compatible with computeHealthState() watchlist input
 */
export function buildBillingWatchlist(insights = []) {
  const active = insights.filter(isActiveInsight);

  // Group by type
  const groups = new Map();
  for (const ins of active) {
    const type = ins.type || 'unknown';
    if (!groups.has(type)) groups.set(type, []);
    groups.get(type).push(ins);
  }

  // Convert each group to a WatchItem
  const items = [];
  for (const [type, group] of groups) {
    const highestSeverity = group.reduce((best, ins) => {
      return (SEVERITY_RANK[ins.severity] ?? 99) < (SEVERITY_RANK[best] ?? 99)
        ? ins.severity
        : best;
    }, 'low');

    const labelFn = BILLING_REASON_LABELS[type];
    const label = labelFn
      ? labelFn(group.length)
      : `${group.length} anomalie${group.length > 1 ? 's' : ''} de type ${type}`;

    items.push({
      id: `billing-${type}`,
      label,
      severity: highestSeverity,
      path: '/bill-intel',
      cta: 'Voir détails',
      estimatedLoss: group.reduce((sum, ins) => sum + (ins.estimated_loss_eur || 0), 0),
    });
  }

  items.sort((a, b) => (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99));
  return items.slice(0, 5);
}

// ── computeBillingHealthState ─────────────────────────────────────────────────

/**
 * Compute billing-domain health state from billing summary + insights.
 * Delegates to computeHealthState() for consistent HealthState shape.
 * Overrides CTAs to point to billing-specific routes.
 *
 * @param {object}   summary  — from getBillingSummary()
 * @param {object[]} insights — from getBillingInsights()
 * @returns {HealthState}
 */
export function computeBillingHealthState(summary, insights = []) {
  const watchlist = buildBillingWatchlist(insights);
  const active = insights.filter(isActiveInsight);
  const critCount = active.filter((i) => i.severity === 'critical').length;

  const kpis = {
    total: summary?.total_invoices || 0,
    conformes: (summary?.total_invoices || 0) - critCount,
    nonConformes: critCount,
    aRisque: active.filter((i) => i.severity === 'high').length,
    risqueTotal: summary?.total_estimated_loss_eur || 0,
    couvertureDonnees: 100,
  };

  const state = computeHealthState({
    kpis,
    watchlist,
    briefing: [],
    consistency: { ok: true },
    alertsCount: active.filter((i) => i.severity === 'medium').length,
  });

  // Stable billing CTAs — 2 per level, + "Voir tout" overflow
  // Use allReasonCount (same source as subtitle) so numbers stay consistent
  const totalReasons = state.allReasonCount || watchlist.length;
  let primaryCta, secondaryCta;

  if (state.level === 'RED') {
    primaryCta = { label: 'Voir les anomalies critiques', to: '/bill-intel' };
    secondaryCta = { label: "Plan d'action", to: '/actions' };
  } else if (state.level === 'AMBER') {
    primaryCta = { label: 'Analyser les écarts', to: '/bill-intel' };
    secondaryCta = { label: 'Explorer la facturation', to: '/bill-intel' };
  } else {
    primaryCta = { label: 'Explorer la facturation', to: '/bill-intel' };
    secondaryCta = undefined;
  }

  // "Voir tout" overflow — replaces secondaryCta when many signals
  if (totalReasons > 3) {
    secondaryCta = { label: `Voir les ${totalReasons} points`, to: '/bill-intel' };
  }

  return { ...state, primaryCta, secondaryCta };
}

// ── Health Trend ──────────────────────────────────────────────────────────────

const LEVEL_ORDINAL = { GREEN: 0, AMBER: 1, RED: 2 };
const TREND_STORAGE_PREFIX = 'promeos.health.';
const SNAPSHOT_RETENTION_MS = 14 * 24 * 60 * 60 * 1000; // 14 days
const MAX_SNAPSHOTS_PER_DOMAIN = 10;

/**
 * Build a scoped localStorage key for health snapshots.
 * Format: promeos.health.{domain}.{scopeKey}
 *
 * @param {string} domain — e.g. 'billing', 'patrimoine'
 * @param {{ orgId?: number|string, scopeType?: string, scopeId?: number|string }} [scope]
 * @returns {string}
 */
export function buildSnapshotKey(domain, scope) {
  const base = `${TREND_STORAGE_PREFIX}${domain}`;
  if (!scope || !scope.orgId) return base;
  const orgPart = `org-${scope.orgId}`;
  const scopePart =
    scope.scopeType && scope.scopeId ? `${scope.scopeType}-${scope.scopeId}` : 'all-sites';
  return `${base}.${orgPart}.${scopePart}`;
}

/**
 * Compare current health to a previous snapshot.
 *
 * @param {HealthState} current
 * @param {{ level: string, reasonsCount: number } | null} previous
 * @returns {{ direction: 'improving'|'degrading'|'stable', label: string }}
 */
export function computeHealthTrend(current, previous) {
  if (!previous) return { direction: 'stable', label: 'Première analyse' };

  const curOrd = LEVEL_ORDINAL[current.level] ?? 1;
  const prevOrd = LEVEL_ORDINAL[previous.level] ?? 1;

  if (curOrd < prevOrd) return { direction: 'improving', label: 'En amélioration' };
  if (curOrd > prevOrd) return { direction: 'degrading', label: 'En dégradation' };

  // Same level — compare reason counts
  const curCount = current.reasons?.length || 0;
  const prevCount = previous.reasonsCount ?? 0;

  if (curCount < prevCount) {
    const diff = prevCount - curCount;
    return { direction: 'improving', label: `${diff} point${diff > 1 ? 's' : ''} en moins` };
  }
  if (curCount > prevCount) {
    const diff = curCount - prevCount;
    return { direction: 'degrading', label: `${diff} point${diff > 1 ? 's' : ''} en plus` };
  }

  return { direction: 'stable', label: 'Stable' };
}

/**
 * Load previous health snapshot from localStorage.
 * Returns null if snapshot is expired (> 14 days) or missing.
 *
 * @param {string} domain — e.g. 'billing', 'patrimoine'
 * @param {{ orgId?, scopeType?, scopeId? }} [scope] — optional scope for key
 * @returns {{ level: string, reasonsCount: number, timestamp: number } | null}
 */
export function loadHealthSnapshot(domain, scope) {
  try {
    const key = buildSnapshotKey(domain, scope);
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const snapshot = JSON.parse(raw);
    // Enforce retention: ignore snapshots older than 14 days
    if (snapshot.timestamp && Date.now() - snapshot.timestamp > SNAPSHOT_RETENTION_MS) {
      localStorage.removeItem(key);
      return null;
    }
    return snapshot;
  } catch {
    return null;
  }
}

/**
 * Save current health snapshot to localStorage.
 * Purges expired snapshots for the same domain (max 10 per domain).
 *
 * @param {string} domain
 * @param {HealthState} state
 * @param {{ orgId?, scopeType?, scopeId? }} [scope] — optional scope for key
 */
export function saveHealthSnapshot(domain, state, scope) {
  try {
    const key = buildSnapshotKey(domain, scope);
    localStorage.setItem(
      key,
      JSON.stringify({
        level: state.level,
        reasonsCount: state.reasons?.length || 0,
        timestamp: Date.now(),
      })
    );
    // Purge expired snapshots for this domain
    _purgeExpiredSnapshots(domain);
  } catch {
    /* ignore quota errors */
  }
}

/**
 * Remove expired snapshots for a domain and enforce max count.
 * @param {string} domain
 */
function _purgeExpiredSnapshots(domain) {
  const prefix = `${TREND_STORAGE_PREFIX}${domain}`;
  const now = Date.now();
  const keys = [];

  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith(prefix)) keys.push(k);
  }

  // Remove expired
  const valid = [];
  for (const k of keys) {
    try {
      const snap = JSON.parse(localStorage.getItem(k));
      if (snap?.timestamp && now - snap.timestamp > SNAPSHOT_RETENTION_MS) {
        localStorage.removeItem(k);
      } else {
        valid.push({ key: k, timestamp: snap?.timestamp || 0 });
      }
    } catch {
      localStorage.removeItem(k);
    }
  }

  // Enforce max count: keep most recent
  if (valid.length > MAX_SNAPSHOTS_PER_DOMAIN) {
    valid.sort((a, b) => b.timestamp - a.timestamp);
    for (const entry of valid.slice(MAX_SNAPSHOTS_PER_DOMAIN)) {
      localStorage.removeItem(entry.key);
    }
  }
}
