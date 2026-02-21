/**
 * PROMEOS V47 — Action ↔ Preuve : logique pure (aucun import React)
 *
 * Ferme la boucle Issue OPERAT → Action → Preuve → Clôture.
 * Parse le source_id OPERAT pour reconstituer le contexte EFA/preuve,
 * construit les deep-links Mémobox, et évalue la clôturabilité.
 *
 * Exports:
 *   parseOperatSourceId(sourceId)           → { efa_id, year, issue_code } | null
 *   isOperatAction(action)                  → boolean
 *   buildActionProofLink(action)            → URL string (/kb?context=proof&…)
 *   buildActionProofContext(action)          → { hint, domain, efa_id, year, issue_code, action_id }
 *   isActionClosable(action, proofsSummary) → { closable: boolean, raisons: string[] }
 *   PROOF_STATUS_LABELS                     → mapping état → label FR
 */

// ── Constantes ───────────────────────────────────────────────────────────────

export const PROOF_STATUS_LABELS = Object.freeze({
  none:      'Aucune preuve liée',
  draft:     'Preuve en brouillon',
  review:    'En revue',
  validated: 'Preuve validée',
});

const PROOF_STATUS_BADGE = Object.freeze({
  none:      'neutral',
  draft:     'warn',
  review:    'warn',
  validated: 'ok',
});

export { PROOF_STATUS_BADGE };

// ── Parseur source_id OPERAT ─────────────────────────────────────────────────

/**
 * Parse un source_id au format "operat:{efa_id}:{year}:{issue_code}".
 *
 * @param {string} sourceId
 * @returns {{ efa_id: string, year: string, issue_code: string } | null}
 */
export function parseOperatSourceId(sourceId) {
  if (!sourceId || typeof sourceId !== 'string') return null;
  const parts = sourceId.split(':');
  if (parts.length < 4 || parts[0] !== 'operat') return null;
  return {
    efa_id: parts[1],
    year: parts[2],
    issue_code: parts.slice(3).join(':'),
  };
}

// ── Détection action OPERAT ──────────────────────────────────────────────────

/**
 * @param {object} action — action backend (source_type, source_id)
 * @returns {boolean}
 */
export function isOperatAction(action) {
  if (!action) return false;
  return action.source_type === 'insight' && (action.source_id || '').startsWith('operat:');
}

// ── Deep-link Mémobox avec contexte preuve ───────────────────────────────────

/**
 * Construit un lien Mémobox pré-filtré pour déposer une preuve
 * dans le contexte d'une action OPERAT.
 *
 * @param {object} action — action backend complète
 * @returns {string} URL path
 */
export function buildActionProofLink(action) {
  if (!action) return '/kb';

  const parsed = parseOperatSourceId(action.source_id);
  if (!parsed) return '/kb?context=proof';

  const params = new URLSearchParams();
  params.set('context', 'proof');
  params.set('domain', 'reglementaire');
  params.set('efa_id', parsed.efa_id);
  if (action.id) params.set('action_id', String(action.id));

  // Hint FR pour la bannière Mémobox
  const hint = `Action OPERAT #${action.id || '—'} — EFA ${parsed.efa_id} — ${parsed.issue_code}`;
  params.set('hint', hint.slice(0, 120));

  return `/kb?${params.toString()}`;
}

// ── Contexte preuve pour une action ──────────────────────────────────────────

/**
 * Construit le contexte preuve complet à partir d'une action OPERAT.
 *
 * @param {object} action — action backend complète
 * @returns {{ hint: string, domain: string, efa_id: string|null, year: string|null, issue_code: string|null, action_id: number|string|null }}
 */
export function buildActionProofContext(action) {
  const base = {
    hint: '',
    domain: 'reglementaire',
    efa_id: null,
    year: null,
    issue_code: null,
    action_id: action?.id || null,
  };

  if (!action) return base;

  const parsed = parseOperatSourceId(action.source_id);
  if (!parsed) return { ...base, hint: action.title || '' };

  return {
    ...base,
    efa_id: parsed.efa_id,
    year: parsed.year,
    issue_code: parsed.issue_code,
    hint: `EFA #${parsed.efa_id} | ${parsed.issue_code} | ${action.title || ''}`,
  };
}

// ── Évaluation de clôturabilité ──────────────────────────────────────────────

/**
 * Détermine si une action OPERAT peut être marquée "terminée".
 *
 * Conditions (au moins une suffit) :
 *   1) proofsSummary.validated_count > 0  (preuve validée côté EFA)
 *   2) evidenceCount > 0                  (pièce jointe sur l'action)
 *   3) action.notes contient "[justifié]" (justification manuelle)
 *
 * @param {object} action          — action backend
 * @param {{ validated_count?: number, deposited_count?: number, expected_count?: number }} [proofsSummary]
 * @param {number} [evidenceCount] — nombre de pièces jointes sur l'action
 * @returns {{ closable: boolean, raisons: string[] }}
 */
export function isActionClosable(action, proofsSummary, evidenceCount = 0) {
  const raisons = [];

  if (!action) {
    raisons.push('Action non trouvée');
    return { closable: false, raisons };
  }

  // Déjà terminée
  if (action.status === 'done' || action.status === 'false_positive') {
    return { closable: true, raisons: ['Action déjà clôturée'] };
  }

  let hasProof = false;

  // Condition 1: preuve validée côté EFA
  if (proofsSummary && proofsSummary.validated_count > 0) {
    hasProof = true;
  }

  // Condition 2: pièce jointe présente sur l'action
  if (evidenceCount > 0) {
    hasProof = true;
  }

  // Condition 3: justification manuelle dans les notes
  const hasJustification = (action.notes || '').includes('[justifié]');
  if (hasJustification) {
    hasProof = true;
  }

  if (hasProof) {
    return { closable: true, raisons: [] };
  }

  // Non clôturable — raisons FR
  raisons.push('Aucune preuve validée sur l\u2019EFA');
  if (evidenceCount === 0) {
    raisons.push('Aucune pièce jointe sur l\u2019action');
  }
  raisons.push('Ajoutez [justifié] dans les notes pour clôturer sans preuve');

  return { closable: false, raisons };
}

// ── Helper: résoudre le statut preuve d'une action ───────────────────────────

/**
 * Déduit le statut preuve agrégé à partir du résumé EFA.
 *
 * @param {{ validated_count?: number, deposited_count?: number, expected_count?: number }} [proofsSummary]
 * @returns {'none'|'draft'|'review'|'validated'}
 */
export function resolveProofStatus(proofsSummary) {
  if (!proofsSummary) return 'none';
  if (proofsSummary.validated_count > 0) return 'validated';
  if (proofsSummary.deposited_count > 0) return 'draft';
  return 'none';
}
