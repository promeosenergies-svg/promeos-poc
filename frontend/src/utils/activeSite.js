/**
 * Active Site — persiste le dernier site ouvert pour la nav contextuelle.
 * Stocké dans localStorage pour survivre aux navigations et rafraîchissements.
 * Dispatche un CustomEvent pour notifier NavPanel sans polling.
 */
const KEY = 'promeos.active_site';
const EVENT = 'promeos:activeSite';

function _dispatch(payload) {
  window.dispatchEvent(new CustomEvent(EVENT, { detail: payload }));
}

export function getActiveSite() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setActiveSite(site) {
  if (!site?.id || !site?.nom) return;
  try {
    const payload = {
      id: site.id,
      nom: site.nom,
      statut: site.statut_conformite || 'a_evaluer',
    };
    localStorage.setItem(KEY, JSON.stringify(payload));
    _dispatch(payload);
  } catch {
    // Silently fail
  }
}

export function clearActiveSite() {
  try {
    localStorage.removeItem(KEY);
    _dispatch(null);
  } catch {
    // Silently fail
  }
}

export const ACTIVE_SITE_EVENT = EVENT;
