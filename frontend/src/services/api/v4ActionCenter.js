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
