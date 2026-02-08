/**
 * PROMEOS - Service API
 * Gestion des appels vers le backend FastAPI
 */
import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ========================================
// SITES
// ========================================

export const getSites = async (params = {}) => {
  const response = await api.get('/sites', { params });
  return response.data;
};

export const getSite = async (id) => {
  const response = await api.get(`/sites/${id}`);
  return response.data;
};

export const getSiteStats = async (id) => {
  const response = await api.get(`/sites/${id}/stats`);
  return response.data;
};

// ========================================
// COMPTEURS
// ========================================

export const getCompteurs = async (params = {}) => {
  const response = await api.get('/compteurs', { params });
  return response.data;
};

export const getCompteur = async (id) => {
  const response = await api.get(`/compteurs/${id}`);
  return response.data;
};

// ========================================
// CONSOMMATIONS
// ========================================

export const getConsommations = async (params = {}) => {
  const response = await api.get('/consommations', { params });
  return response.data;
};

// ========================================
// ALERTES
// ========================================

export const getAlertes = async (params = {}) => {
  const response = await api.get('/alertes', { params });
  return response.data;
};

export const getAlerte = async (id) => {
  const response = await api.get(`/alertes/${id}`);
  return response.data;
};

export const resolveAlerte = async (id) => {
  const response = await api.patch(`/alertes/${id}/resolve`);
  return response.data;
};

export default api;
