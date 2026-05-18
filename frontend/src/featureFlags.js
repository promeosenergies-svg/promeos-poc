/**
 * M2-5.1 — Feature flags V4.
 *
 * Simple module — pas de runtime tracking, pas de bibliothèque externe.
 * Pattern : 1 export par flag, lecture depuis import.meta.env.
 *
 * Pour ajouter un flag :
 * 1. Ajouter VITE_FEATURE_XXX=false dans .env.example
 * 2. Créer un export isXxxEnabled() ici
 */

/**
 * Active la nouvelle interface Centre d'Action V4.
 * @returns {boolean}
 */
export function isActionCenterV4Enabled() {
  return import.meta.env.VITE_FEATURE_ACTION_CENTER_V4 === 'true';
}
