/**
 * PROMEOS — evidenceRules.js (Étape 4.1)
 * Centralized evidence requirement rules.
 * Pure functions — no React imports, fully testable.
 *
 * Exports:
 *   EVIDENCE_RULES             → { force: Rule[], recommend: Rule[] }
 *   computeEvidenceRequirement → ({ sourceType, severity }) → { required, lock, labelFR }
 *   SOURCE_DEEP_LINKS          → { [sourceType]: (sourceId) → URL }
 *   SOURCE_LABELS_FR           → { [sourceType]: string }
 */

// ── Evidence Rules ──────────────────────────────────────────────────────────

/**
 * FORCE: evidence_required=true, non-désactivable par l'utilisateur.
 * RECOMMEND: evidence_required=true par défaut, désactivable par l'utilisateur.
 *
 * Matching: sourceType + severity (null severity = any).
 */
export const EVIDENCE_RULES = {
  force: [
    { sourceType: 'compliance', severity: 'critical', labelFR: 'Requis (conformité critique)' },
  ],
  recommend: [
    { sourceType: 'compliance', severity: 'high',     labelFR: 'Recommandé (conformité élevée)' },
    { sourceType: 'billing',   severity: 'critical',  labelFR: 'Recommandé (anomalie critique)' },
    { sourceType: 'billing',   severity: 'high',      labelFR: 'Recommandé (anomalie élevée)' },
    { sourceType: 'insight',   severity: 'critical',  labelFR: 'Recommandé (diagnostic critique)' },
  ],
};

/**
 * Compute the evidence requirement for an action based on source + severity.
 *
 * Priority: FORCE > RECOMMEND > severity fallback.
 *
 * @param {{ sourceType?: string, severity?: string }} params
 * @returns {{ required: boolean, lock: boolean, labelFR: string }}
 *   - required: should the toggle be ON
 *   - lock: if true, the user cannot disable the toggle
 *   - labelFR: French label to display next to the toggle
 */
export function computeEvidenceRequirement({ sourceType, severity } = {}) {
  // 1. Check FORCE rules
  const forceMatch = EVIDENCE_RULES.force.find(
    (r) => r.sourceType === sourceType && (r.severity === null || r.severity === severity),
  );
  if (forceMatch) {
    return { required: true, lock: true, labelFR: forceMatch.labelFR };
  }

  // 2. Check RECOMMEND rules
  const recMatch = EVIDENCE_RULES.recommend.find(
    (r) => r.sourceType === sourceType && (r.severity === null || r.severity === severity),
  );
  if (recMatch) {
    return { required: true, lock: false, labelFR: recMatch.labelFR };
  }

  // 3. Severity fallback
  if (severity === 'critical') {
    return { required: true, lock: false, labelFR: 'Recommandé (priorité critique)' };
  }
  if (severity === 'high') {
    return { required: true, lock: false, labelFR: 'Recommandé (priorité élevée)' };
  }

  return { required: false, lock: false, labelFR: '' };
}

// ── Source Labels (FR) ──────────────────────────────────────────────────────

export const SOURCE_LABELS_FR = {
  compliance:  'Conformité',
  consumption: 'Consommation',
  billing:     'Facturation',
  purchase:    'Achats',
  manual:      'Manuelle',
  insight:     'Diagnostic',
  lever_engine: 'Levier',
};

// ── Source Deep Links ───────────────────────────────────────────────────────

/**
 * Build a deep-link URL to navigate back to the source object.
 * Returns null if no deep-link is available.
 *
 * @param {string} sourceType
 * @param {string} sourceId
 * @returns {string|null}
 */
export function buildSourceDeepLink(sourceType, sourceId) {
  if (!sourceType || !sourceId) return null;

  switch (sourceType) {
    case 'compliance':
      return '/conformite';
    case 'billing':
      return '/bill-intel';
    case 'consumption':
      return '/consommations';
    case 'purchase':
      return '/performance';
    case 'insight': {
      // readiness:xxx → /activation, operat:xxx → /conformite/tertiaire/efa
      if (sourceId.startsWith('readiness:')) return '/activation';
      if (sourceId.startsWith('operat:')) return '/conformite/tertiaire/efa';
      return '/anomalies';
    }
    case 'lever_engine':
      return '/actions';
    default:
      return null;
  }
}
