/**
 * anomalyActions.js — V65
 * Helpers localStorage pour les actions locales sur anomalies.
 * Front-only (pas de DB). V66 migrera vers backend.
 *
 * Clé de stockage : "promeos_anomaly_actions"
 * Format interne : { "${orgId}:${siteId}:${anomalyCode}": ActionRecord }
 */

const STORAGE_KEY = 'promeos_anomaly_actions';

export const ACTION_STATUS = {
  TODO:        'todo',
  IN_PROGRESS: 'in_progress',
  RESOLVED:    'resolved',
};

export const ACTION_STATUS_LABEL = {
  todo:        'À traiter',
  in_progress: 'En cours',
  resolved:    'Résolu',
};

export const ACTION_STATUS_COLOR = {
  todo:        'bg-gray-100 text-gray-600',
  in_progress: 'bg-amber-100 text-amber-700',
  resolved:    'bg-green-100 text-green-700',
};

/* ── Helpers internes ── */

function _key(orgId, siteId, anomalyCode) {
  return `${orgId ?? 'demo'}:${siteId}:${anomalyCode}`;
}

function _load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function _save(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // silently ignore (private browsing, storage full, etc.)
  }
}

/* ── API publique ── */

/**
 * Charge l'action locale pour une anomalie donnée.
 * @returns {object|null}
 */
export function getAnomalyAction(orgId, siteId, anomalyCode) {
  return _load()[_key(orgId, siteId, anomalyCode)] ?? null;
}

/**
 * Sauvegarde (crée ou met à jour) une action locale.
 * @param {object} record - { title, status, owner, due_date, notes }
 */
export function saveAnomalyAction(orgId, siteId, anomalyCode, record) {
  const data = _load();
  data[_key(orgId, siteId, anomalyCode)] = {
    ...record,
    anomaly_code: anomalyCode,
    site_id:      siteId,
    org_id:       orgId ?? 'demo',
    updated_at:   new Date().toISOString(),
  };
  _save(data);
}

/**
 * Supprime l'action locale pour une anomalie.
 */
export function deleteAnomalyAction(orgId, siteId, anomalyCode) {
  const data = _load();
  delete data[_key(orgId, siteId, anomalyCode)];
  _save(data);
}

/**
 * Retourne toutes les actions locales pour un site.
 * @returns {object[]}
 */
export function getAllActionsForSite(orgId, siteId) {
  const data = _load();
  return Object.values(data).filter(
    r => r.org_id === (orgId ?? 'demo') && r.site_id === siteId
  );
}

/**
 * Retourne toutes les actions locales pour une organisation.
 * @returns {object[]}
 */
export function getAllActionsForOrg(orgId) {
  const data = _load();
  return Object.values(data).filter(
    r => r.org_id === (orgId ?? 'demo')
  );
}
