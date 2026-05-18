/**
 * M2-5.4 — Classification des erreurs API V4 pour l'UI (inline vs toast).
 *
 * Décision Q3 :
 *  - 422 corrigeable par l'utilisateur dans la modal → erreur inline.
 *  - 422 transition interdite / 401 / 403 / 429 / 5xx → toast + fermeture modal.
 */

const INLINE_ERROR_CODES = new Set([
  'CLOSURE_REASON_REQUIRED',
  'CLOSURE_REASON_UNEXPECTED',
  'CLOSURE_REASON_SYSTEM_ONLY',
]);

/**
 * Classifie une erreur normalisée (`error.promeos`).
 * @param {{code?: string, status?: number}|null} err
 * @returns {'inline' | 'toast' | null}
 */
export function classifyError(err) {
  if (!err) return null;
  if (err.code && INLINE_ERROR_CODES.has(err.code)) return 'inline';
  return 'toast';
}

/**
 * Message toast FR selon le code métier ou le status HTTP.
 * @param {{code?: string, message?: string, status?: number}|null} err
 * @returns {string}
 */
export function toastMessageForError(err) {
  if (!err) return 'Erreur inconnue';

  if (err.code === 'LIFECYCLE_TRANSITION_FORBIDDEN') {
    return err.message || 'Transition non autorisée selon le cycle de vie';
  }

  switch (err.status) {
    case 401:
      return 'Session expirée, veuillez vous reconnecter';
    case 403:
      return 'Action non autorisée';
    case 429:
      return 'Trop de requêtes, réessayez dans quelques instants';
    case 500:
    case 502:
    case 503:
    case 504:
      return 'Erreur serveur, réessayez plus tard';
    default:
      return err.message || 'Erreur inconnue';
  }
}
