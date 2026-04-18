/**
 * PROMEOS — NPS trigger helpers (Sprint CX P1 residual)
 *
 * shouldShowNps(userCreatedAt, now) :
 *   - Renvoie true si user > 30j ET pas de submission localStorage < 90j
 *   - Clé localStorage : promeos_nps_last_submit (ISO string)
 *   - Clé localStorage : promeos_nps_dismissed_until (ISO, optionnel)
 *
 * markNpsSubmitted()  : écrit la date courante dans localStorage
 * markNpsDismissed(days) : reporte la re-proposition de N jours
 */

export const NPS_LAST_SUBMIT_KEY = 'promeos_nps_last_submit';
export const NPS_DISMISSED_KEY = 'promeos_nps_dismissed_until';
export const NPS_COOLDOWN_DAYS = 90;
export const NPS_MIN_ACCOUNT_AGE_DAYS = 30;

const DAY_MS = 24 * 60 * 60 * 1000;

function _safeGet(key) {
  try {
    return typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
  } catch {
    return null;
  }
}

function _safeSet(key, value) {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(key, value);
  } catch {
    // ignore (incognito / quota)
  }
}

/**
 * @param {Date|string|null} userCreatedAt — date de création du compte
 * @param {Date} [now] — now override (tests)
 * @returns {boolean}
 */
export function shouldShowNps(userCreatedAt, now = new Date()) {
  if (!userCreatedAt) return false;
  const created = userCreatedAt instanceof Date ? userCreatedAt : new Date(userCreatedAt);
  if (isNaN(created.getTime())) return false;

  // Compte < 30j : non éligible
  const ageDays = (now.getTime() - created.getTime()) / DAY_MS;
  if (ageDays < NPS_MIN_ACCOUNT_AGE_DAYS) return false;

  // Déjà soumis < 90j : non éligible
  const lastSubmit = _safeGet(NPS_LAST_SUBMIT_KEY);
  if (lastSubmit) {
    const last = new Date(lastSubmit);
    if (!isNaN(last.getTime())) {
      const daysSince = (now.getTime() - last.getTime()) / DAY_MS;
      if (daysSince < NPS_COOLDOWN_DAYS) return false;
    }
  }

  // Dismiss explicite non expiré : non éligible
  const dismissedUntil = _safeGet(NPS_DISMISSED_KEY);
  if (dismissedUntil) {
    const until = new Date(dismissedUntil);
    if (!isNaN(until.getTime()) && now.getTime() < until.getTime()) return false;
  }

  return true;
}

export function markNpsSubmitted(now = new Date()) {
  _safeSet(NPS_LAST_SUBMIT_KEY, now.toISOString());
}

export function markNpsDismissed(days = 30, now = new Date()) {
  const until = new Date(now.getTime() + days * DAY_MS);
  _safeSet(NPS_DISMISSED_KEY, until.toISOString());
}
