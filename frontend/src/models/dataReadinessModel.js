/**
 * PROMEOS — dataReadinessModel.js (Step 3.1)
 * Pure model layer for the Data Readiness Gate.
 * Builds ON TOP of buildActivationChecklist() — no duplication.
 * No React imports — fully testable in isolation.
 *
 * Exports:
 *   computeDataReadinessState(activation, signals) → ReadinessState
 *   computeDataConfidence(readinessState) → { label, level, badgeStatus, tooltipFR }
 *   buildReadinessSnapshotKey(scope) → string
 *   loadReadinessSnapshot(scope) → snapshot|null
 *   saveReadinessSnapshot(state, scope) → void
 *   computeReadinessTrend(current, previous) → { delta, labelFR }
 *   LEVEL_BADGE_LABEL, SOFT_GATE_TOOLTIP_FR
 */
import { READINESS_GATE } from '../lib/constants';

// ── Dimension evaluators ────────────────────────────────────────────────────
// Each returns { status: 'ok'|'partial'|'ko', reason? }

function evalConso(activation, _signals) {
  const dim = activation?.dimensions?.find((d) => d.key === 'consommation');
  const coverage = dim?.coverage ?? 0;
  if (coverage === 0) {
    return {
      status: 'ko',
      reason: {
        id: 'conso-ko',
        label: 'Aucune donnée de consommation importée',
        severity: 'critical',
        path: '/consommations/import',
        cta: 'Importer',
      },
    };
  }
  if (coverage < READINESS_GATE.conso.partialPct) {
    return {
      status: 'partial',
      reason: {
        id: 'conso-partial',
        label: `Couverture consommation à ${coverage}% (seuil : ${READINESS_GATE.conso.partialPct}%)`,
        severity: 'high',
        path: '/consommations/import',
        cta: 'Compléter',
      },
    };
  }
  return { status: 'ok' };
}

function evalFacturation(_activation, signals) {
  const months = signals?.billingMonthCount ?? 0;
  if (months < READINESS_GATE.facturation.ko) {
    return {
      status: 'ko',
      reason: {
        id: 'factures-ko',
        label:
          months === 0
            ? 'Aucune facture importée'
            : `Seulement ${months} mois de factures (minimum ${READINESS_GATE.facturation.ko})`,
        severity: 'critical',
        path: '/bill-intel',
        cta: 'Importer',
      },
    };
  }
  if (months < READINESS_GATE.facturation.partial) {
    return {
      status: 'partial',
      reason: {
        id: 'factures-partial',
        label: `${months} mois de factures (historique recommandé : ${READINESS_GATE.facturation.partial} mois)`,
        severity: 'high',
        path: '/bill-intel',
        cta: 'Compléter',
      },
    };
  }
  return { status: 'ok' };
}

function evalOperat(_activation, signals) {
  if (!signals?.operatModuleActive) return { status: 'ok' }; // skip if OPERAT not enabled
  const efa = signals?.efaDashboard;
  const efaCount = efa?.total_sites ?? efa?.total ?? 0;
  if (efaCount === 0) {
    return {
      status: 'ko',
      reason: {
        id: 'operat-ko',
        label: 'Aucune fiche EFA renseignée pour OPERAT',
        severity: 'critical',
        path: '/tertiaire',
        cta: 'Configurer',
      },
    };
  }
  const openIssues = efa?.open_issues ?? efa?.issues_count ?? 0;
  if (openIssues > READINESS_GATE.operat.issueThreshold) {
    return {
      status: 'partial',
      reason: {
        id: 'operat-partial',
        label: `${openIssues} anomalies EFA ouvertes (seuil : ${READINESS_GATE.operat.issueThreshold})`,
        severity: 'high',
        path: '/tertiaire',
        cta: 'Corriger',
      },
    };
  }
  return { status: 'ok' };
}

function evalConnectors(activation, signals) {
  const connectors = signals?.connectors;
  const hasConnector =
    Array.isArray(connectors) && connectors.some((c) => c.status === 'active' || c.enabled);
  const hasData = (activation?.activatedCount ?? 0) > 1;
  const hasImport = signals?.hasManualImport ?? false;

  if (!hasConnector && !hasData && !hasImport) {
    return {
      status: 'ko',
      reason: {
        id: 'connecteurs-ko',
        label: 'Aucun connecteur ni import de données configuré',
        severity: 'critical',
        path: '/activation',
        cta: 'Configurer',
      },
    };
  }
  if (!hasConnector && (hasData || hasImport)) {
    return {
      status: 'partial',
      reason: {
        id: 'connecteurs-partial',
        label: 'Import manuel uniquement — aucun connecteur automatique',
        severity: 'high',
        path: '/activation',
        cta: 'Connecter',
      },
    };
  }
  return { status: 'ok' };
}

// ── Core ─────────────────────────────────────────────────────────────────────

const EVALUATORS = [evalConso, evalFacturation, evalOperat, evalConnectors];

const STATUS_LEVEL = { ko: 'RED', partial: 'AMBER', ok: 'GREEN' };
const LEVEL_BADGE = { GREEN: 'ok', AMBER: 'warn', RED: 'crit' };
const LEVEL_BADGE_LABEL = { GREEN: 'OK', AMBER: 'Partiel', RED: 'Incomplet' };

/**
 * Compute the Data Readiness Gate state.
 * Builds on top of an ActivationResult (from buildActivationChecklist).
 *
 * @param {ActivationResult} activation — from buildActivationChecklist()
 * @param {object} signals — { billingMonthCount, efaDashboard, connectors, operatModuleActive, hasManualImport }
 * @returns {ReadinessState}
 */
export function computeDataReadinessState(activation, signals = {}) {
  const results = EVALUATORS.map((fn) => fn(activation, signals));
  const reasons = results.filter((r) => r.reason).map((r) => r.reason);

  // Worst status wins
  const hasKo = results.some((r) => r.status === 'ko');
  const hasPartial = results.some((r) => r.status === 'partial');
  const worstStatus = hasKo ? 'ko' : hasPartial ? 'partial' : 'ok';
  const level = STATUS_LEVEL[worstStatus];

  // Title & subtitle
  const titles = {
    RED: {
      title: 'Données incomplètes',
      subtitle: 'Certaines briques essentielles manquent pour exploiter pleinement la plateforme.',
    },
    AMBER: {
      title: 'Données partielles',
      subtitle: 'La plateforme est utilisable, mais certaines analyses seront limitées.',
    },
    GREEN: { title: 'Données complètes', subtitle: 'Toutes les briques de données sont en place.' },
  };
  const { title, subtitle } = titles[level];

  // Primary CTA — first reason path, or default to /activation
  const primaryCta =
    reasons.length > 0
      ? { label: reasons[0].cta || 'Compléter', to: reasons[0].path || '/activation' }
      : { label: "Voir l'activation", to: '/activation' };

  // Secondary CTA when overflow (popover shows max 3, full list on /activation)
  const cappedReasons = reasons.slice(0, 3);
  const secondaryCta =
    reasons.length > 3
      ? { label: `Voir les ${reasons.length} points`, to: '/activation' }
      : undefined;

  // Gating flags
  const gating = {
    canExportOperat: !reasons.some((r) => r.id === 'operat-ko'),
    canAuditAll: !reasons.some((r) => r.id === 'factures-ko'),
    canSimulatePurchase: !reasons.some((r) => r.id === 'conso-ko'),
  };

  return {
    level,
    title,
    subtitle,
    reasons: cappedReasons,
    allReasonCount: reasons.length,
    primaryCta,
    secondaryCta,
    gating,
    badgeStatus: LEVEL_BADGE[level],
    badgeLabel: LEVEL_BADGE_LABEL[level],
  };
}

// ── Exported constants ──────────────────────────────────────────────────────

export { LEVEL_BADGE_LABEL };

/** Standard FR tooltip for soft-gated features. */
export const SOFT_GATE_TOOLTIP_FR =
  'Données insuffisantes — corrigez ce point pour débloquer cette fonctionnalité';

// ── Data Confidence (Purchase) ──────────────────────────────────────────────

const CONFIDENCE_LEVELS = {
  high: {
    label: 'Élevée',
    level: 'high',
    badgeStatus: 'ok',
    tooltipFR: 'Consommation et factures complètes — fiabilité maximale',
  },
  medium: {
    label: 'Moyenne',
    level: 'medium',
    badgeStatus: 'warn',
    tooltipFR: 'Données partielles sur une dimension — résultats indicatifs',
  },
  low: {
    label: 'Faible',
    level: 'low',
    badgeStatus: 'crit',
    tooltipFR: 'Données insuffisantes — résultats peu fiables',
  },
};

/**
 * Compute data confidence level for Purchase simulations.
 * Based on readiness of consumption + billing dimensions.
 *
 * @param {ReadinessState} readinessState — from computeDataReadinessState()
 * @returns {{ label: string, level: 'high'|'medium'|'low', badgeStatus: string, tooltipFR: string }}
 */
export function computeDataConfidence(readinessState) {
  if (!readinessState) return CONFIDENCE_LEVELS.low;

  const hasConsoKo = readinessState.reasons?.some((r) => r.id === 'conso-ko');
  const hasFacturesKo = readinessState.reasons?.some((r) => r.id === 'factures-ko');
  const hasConsoPartial = readinessState.reasons?.some((r) => r.id === 'conso-partial');
  const hasFacturesPartial = readinessState.reasons?.some((r) => r.id === 'factures-partial');

  // Any KO → low confidence
  if (hasConsoKo || hasFacturesKo) return CONFIDENCE_LEVELS.low;

  // Any partial → medium
  if (hasConsoPartial || hasFacturesPartial) return CONFIDENCE_LEVELS.medium;

  // All OK → high
  return CONFIDENCE_LEVELS.high;
}

// ── Readiness Trend (snapshot + delta) ──────────────────────────────────────

const SNAPSHOT_PREFIX = 'promeos.readiness';
const RETENTION_DAYS = 14;
const MAX_SNAPSHOTS = 10;

/**
 * Build a localStorage key for readiness snapshots.
 * @param {{ orgId?: number, scopeType?: string, scopeId?: number }} scope
 */
export function buildReadinessSnapshotKey(scope = {}) {
  const org = scope.orgId || 0;
  const st = scope.scopeType || 'all';
  const si = scope.scopeId || 0;
  return `${SNAPSHOT_PREFIX}.org-${org}.${st}-${si}`;
}

/**
 * Load the most recent readiness snapshot from localStorage.
 * Ignores expired snapshots (>14 days).
 */
export function loadReadinessSnapshot(scope = {}) {
  try {
    const key = buildReadinessSnapshotKey(scope);
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const snapshot = JSON.parse(raw);
    const age = Date.now() - (snapshot._ts || 0);
    if (age > RETENTION_DAYS * 86400000) {
      localStorage.removeItem(key);
      return null;
    }
    return snapshot;
  } catch {
    return null;
  }
}

/**
 * Save the current readiness state as a snapshot.
 */
export function saveReadinessSnapshot(readinessState, scope = {}) {
  if (!readinessState) return;
  try {
    const key = buildReadinessSnapshotKey(scope);
    const snapshot = {
      level: readinessState.level,
      reasonCount: readinessState.allReasonCount ?? readinessState.reasons?.length ?? 0,
      okDimensions: 4 - (readinessState.allReasonCount ?? readinessState.reasons?.length ?? 0),
      _ts: Date.now(),
    };
    localStorage.setItem(key, JSON.stringify(snapshot));
    _purgeExpiredSnapshots();
  } catch {
    /* quota exceeded — silent */
  }
}

function _purgeExpiredSnapshots() {
  try {
    const cutoff = Date.now() - RETENTION_DAYS * 86400000;
    const toRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(SNAPSHOT_PREFIX)) {
        try {
          const v = JSON.parse(localStorage.getItem(k));
          if ((v?._ts || 0) < cutoff) toRemove.push(k);
        } catch {
          toRemove.push(k);
        }
      }
    }
    // Keep max snapshots
    const all = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(SNAPSHOT_PREFIX)) {
        try {
          all.push({ k, ts: JSON.parse(localStorage.getItem(k))?._ts || 0 });
        } catch {}
      }
    }
    if (all.length > MAX_SNAPSHOTS) {
      all.sort((a, b) => a.ts - b.ts);
      for (let i = 0; i < all.length - MAX_SNAPSHOTS; i++) toRemove.push(all[i].k);
    }
    toRemove.forEach((k) => localStorage.removeItem(k));
  } catch {
    /* silent */
  }
}

/**
 * Compute a trend label by comparing current state to a previous snapshot.
 *
 * @param {ReadinessState} current
 * @param {object|null} previous — from loadReadinessSnapshot()
 * @returns {{ delta: number, labelFR: string }}
 */
export function computeReadinessTrend(current, previous) {
  if (!previous || !current) return { delta: 0, labelFR: '' };

  const currentOk = 4 - (current.allReasonCount ?? current.reasons?.length ?? 0);
  const prevOk = previous.okDimensions ?? 0;
  const delta = currentOk - prevOk;

  if (delta > 0) return { delta, labelFR: `+${delta} dimension${delta > 1 ? 's' : ''} OK` };
  if (delta < 0) return { delta, labelFR: `${delta} point${Math.abs(delta) > 1 ? 's' : ''}` };
  return { delta: 0, labelFR: '' };
}
