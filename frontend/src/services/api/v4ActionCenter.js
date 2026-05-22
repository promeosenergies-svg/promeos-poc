/**
 * M2-5.1 — Wrappers des 14 endpoints V4 Action Center.
 *
 * 1 fonction par endpoint. Pas de transformation data (laissé aux hooks).
 * Retourne directement la response axios (ou throw error.promeos normalisé).
 */
import apiClientV4 from './apiClientV4';

const BASE = '/v4/action-center';

// ── READ ───────────────────────────────────────────────────────

export function fetchItems({ offset = 0, limit = 50 } = {}) {
  return apiClientV4.get(`${BASE}/items`, { params: { offset, limit } });
}

export function fetchItem(itemId) {
  return apiClientV4.get(`${BASE}/items/${itemId}`);
}

export function fetchItemEvents(itemId, { offset = 0, limit = 50 } = {}) {
  return apiClientV4.get(`${BASE}/items/${itemId}/events`, {
    params: { offset, limit },
  });
}

export function fetchItemEvidences(itemId, { offset = 0, limit = 50 } = {}) {
  return apiClientV4.get(`${BASE}/items/${itemId}/evidences`, {
    params: { offset, limit },
  });
}

export function fetchItemBlockers(itemId, { offset = 0, limit = 50 } = {}) {
  return apiClientV4.get(`${BASE}/items/${itemId}/blockers`, {
    params: { offset, limit },
  });
}

export function fetchItemLinks(itemId, { offset = 0, limit = 50 } = {}) {
  return apiClientV4.get(`${BASE}/items/${itemId}/links`, {
    params: { offset, limit },
  });
}

// M2-5.10.C — Impact financier 4 quadrants (doctrine §8.5).
// Lecture seule MV3 ; engine de scoring économique = M3+.
export function fetchItemImpact(itemId) {
  return apiClientV4.get(`${BASE}/items/${itemId}/impact`);
}

// M2-5.11.C — Summary org : 5 compteurs agrégés pour la NarrativeBar Sol.
export function fetchActionCenterSummary() {
  return apiClientV4.get(`${BASE}/summary`);
}

// M2-5.10.D — File prioritaire pilotage (top N items P0/P1 actifs).
export function fetchPilotageFilePrioritaire({ limit = 5 } = {}) {
  return apiClientV4.get(`${BASE}/pilotage/file-prioritaire`, { params: { limit } });
}

// M2-6.B.pdf — Export PDF COMEX (active le CTA M2-5.12 disabled).
// Renvoie la response axios avec `data` = Blob PDF + `headers` Content-Disposition
// pour extraire le filename serveur (Content-Disposition est exposé en CORS via
// `expose_headers` dans main.py — M2-6.B.pdf).
export function exportComexPdf() {
  return apiClientV4.post(`${BASE}/export/comex.pdf`, null, { responseType: 'blob' });
}

// M2-5.10.E — Journal org-wide cross-items (fenêtre N jours).
export function fetchPilotageJournal({ sinceDays = 7, limit = 100 } = {}) {
  return apiClientV4.get(`${BASE}/pilotage/journal`, {
    params: { since_days: sinceDays, limit },
  });
}

// ── WRITE (mutations) ──────────────────────────────────────────

export function createItem(payload, { idempotencyKey } = {}) {
  const headers = idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {};
  return apiClientV4.post(`${BASE}/items`, payload, { headers });
}

export function updateItem(itemId, payload) {
  return apiClientV4.patch(`${BASE}/items/${itemId}`, payload);
}

export function transitionLifecycle(itemId, payload) {
  return apiClientV4.patch(`${BASE}/items/${itemId}/lifecycle`, payload);
}

// M2-5.11.E — Assignation du pilote (owner_id + owner_display_name snapshot).
// `payload.owner_id = null` désassigne ; `owner_display_name` ignoré dans ce
// cas et systématiquement remis à null côté BE (pas de label fantôme).
export function assignOwner(itemId, payload) {
  return apiClientV4.patch(`${BASE}/items/${itemId}/assign`, payload);
}

export function uploadEvidence(itemId, file, { description } = {}) {
  const formData = new FormData();
  formData.append('file', file);
  if (description) {
    formData.append('description', description);
  }
  return apiClientV4.post(`${BASE}/items/${itemId}/evidences`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function verifyEvidence(evidenceId, payload) {
  return apiClientV4.patch(`${BASE}/evidences/${evidenceId}/verify`, payload);
}

export function addBlocker(itemId, payload) {
  return apiClientV4.post(`${BASE}/items/${itemId}/blockers`, payload);
}

export function resolveBlocker(blockerId, payload) {
  return apiClientV4.patch(`${BASE}/blockers/${blockerId}/resolve`, payload);
}

export function createLink(itemId, payload) {
  return apiClientV4.post(`${BASE}/items/${itemId}/links`, payload);
}
