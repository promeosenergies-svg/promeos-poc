/**
 * M2-5.4 — Matrice des transitions lifecycle V4 côté client.
 *
 * Duplique délibérément la matrice backend (services/v4/lifecycle_validator.py)
 * — pas de partage de code BE/FE en MV3. Validation client = UX rapide
 * (filtrage des options, affichage conditionnel de closure_reason). Le backend
 * reste l'autorité finale (re-validation à chaque PATCH /lifecycle).
 *
 * ⚠️ À garder synchro avec `_ALLOWED_TRANSITIONS` backend. Un test contractuel
 * M3 pourra vérifier la synchro des deux matrices.
 */

// (from, to) → requiresReason. Reflète backend _ALLOWED_TRANSITIONS.
const ALLOWED_TRANSITIONS = [
  { from: 'new', to: 'triaged', requiresReason: false },
  { from: 'new', to: 'closed', requiresReason: true },
  { from: 'triaged', to: 'planned', requiresReason: false },
  { from: 'triaged', to: 'closed', requiresReason: true },
  { from: 'planned', to: 'in_progress', requiresReason: false },
  { from: 'planned', to: 'closed', requiresReason: true },
  { from: 'in_progress', to: 'closed', requiresReason: true },
];

// closure_reasons acceptées sur un PATCH /lifecycle user-driven (les 3
// system-only — merged_duplicate / resolved_via_recurrence / expired — sont
// refusées par le backend en 422).
export const USER_FACING_CLOSURE_REASONS = ['resolved', 'dismissed', 'not_applicable'];

/**
 * Liste des états cibles autorisés depuis l'état courant.
 * @param {string} currentState
 * @returns {Array<{to: string, requiresReason: boolean}>}
 */
export function getAvailableTransitions(currentState) {
  return ALLOWED_TRANSITIONS.filter((t) => t.from === currentState).map(
    ({ to, requiresReason }) => ({ to, requiresReason })
  );
}

/**
 * Indique si la transition (current → new) requiert un closure_reason.
 * @returns {boolean | null} null si la transition est inconnue (sera 422 backend)
 */
export function transitionRequiresReason(currentState, newState) {
  const match = ALLOWED_TRANSITIONS.find((t) => t.from === currentState && t.to === newState);
  return match ? match.requiresReason : null;
}

/** True si l'item est dans un état terminal (closed) — aucune transition possible. */
export function isTerminalState(state) {
  return state === 'closed';
}
