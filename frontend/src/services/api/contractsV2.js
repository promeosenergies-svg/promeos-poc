/**
 * PROMEOS - Contracts V2 API (Cadre + Annexes)
 */
import api from './core';

// === Cadres ===

export const listCadres = (params = {}) =>
  api.get('/contracts/v2/cadres', { params }).then((r) => r.data);

export const getCadreKpis = () => api.get('/contracts/v2/cadres/kpis').then((r) => r.data);

export const getSuppliers = () => api.get('/contracts/v2/cadres/suppliers').then((r) => r.data);

export const getCadre = (id) => api.get(`/contracts/v2/cadres/${id}`).then((r) => r.data);

export const createCadre = (data) => api.post('/contracts/v2/cadres', data).then((r) => r.data);

export const updateCadre = (id, data) =>
  api.patch(`/contracts/v2/cadres/${id}`, data).then((r) => r.data);

export const deleteCadre = (id) => api.delete(`/contracts/v2/cadres/${id}`).then((r) => r.data);

// === Annexes ===

export const getAnnexe = (cadreId, annexeId) =>
  api.get(`/contracts/v2/cadres/${cadreId}/annexes/${annexeId}`).then((r) => r.data);

export const createAnnexe = (cadreId, data) =>
  api.post(`/contracts/v2/cadres/${cadreId}/annexes`, data).then((r) => r.data);

export const updateAnnexe = (annexeId, data) =>
  api.patch(`/contracts/v2/annexes/${annexeId}`, data).then((r) => r.data);

export const deleteAnnexe = (annexeId) =>
  api.delete(`/contracts/v2/annexes/${annexeId}`).then((r) => r.data);

// === Events ===

export const addEvent = (cadreId, event) =>
  api.post(`/contracts/v2/cadres/${cadreId}/events`, event).then((r) => r.data);

// === Analyses ===

export const getCoherence = (cadreId) =>
  api.get(`/contracts/v2/cadres/${cadreId}/coherence`).then((r) => r.data);

export const getShadowGap = (annexeId) =>
  api.get(`/contracts/v2/annexes/${annexeId}/shadow-gap`).then((r) => r.data);

// === Import ===

export const importCsv = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api
    .post('/contracts/v2/import/csv', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((r) => r.data);
};

export const getImportTemplate = () =>
  api.get('/contracts/v2/import/template', { responseType: 'blob' }).then((r) => r.data);
