/**
 * PROMEOS - API Sirene
 * Recherche referentiel, onboarding from-sirene
 */
import api from './core';

// ── Recherche ──
export const searchSirene = async (q, { page = 1, perPage = 20, etat } = {}) => {
  const params = { q, page, per_page: perPage };
  if (etat) params.etat = etat;
  const response = await api.get('/reference/sirene/search', { params });
  return response.data;
};

export const getUniteLegale = async (siren) => {
  const response = await api.get(`/reference/sirene/unites-legales/${siren}`);
  return response.data;
};

export const getEtablissements = async (siren, { etat } = {}) => {
  const params = {};
  if (etat) params.etat = etat;
  const response = await api.get(`/reference/sirene/unites-legales/${siren}/etablissements`, {
    params,
  });
  return response.data;
};

export const getEtablissement = async (siret) => {
  const response = await api.get(`/reference/sirene/etablissements/${siret}`);
  return response.data;
};

// ── Onboarding from-sirene ──
export const createClientFromSirene = async (data) => {
  const response = await api.post('/onboarding/from-sirene', data);
  return response.data;
};

// ── Admin hydrate (F1 V117) ──
export const hydrateSirenFromApi = async (siren) => {
  const response = await api.post(`/admin/sirene/hydrate/${siren}`);
  return response.data;
};

// ── Admin import ──
export const importSireneFull = async (data) => {
  const response = await api.post('/admin/sirene/import-full', data);
  return response.data;
};

export const importSireneDelta = async (data) => {
  const response = await api.post('/admin/sirene/import-delta', data);
  return response.data;
};

export const getSyncRuns = async (limit = 20) => {
  const response = await api.get('/admin/sirene/sync-runs', { params: { limit } });
  return response.data;
};
