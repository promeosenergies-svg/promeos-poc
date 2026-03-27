/**
 * PROMEOS - API Market Data
 * Endpoints /api/market/* — spot, forwards, tarifs, décomposition
 */
import api from './core';

// ── Spot ──
export const getMarketSpotLatest = (zone = 'FR') =>
  api.get('/market/spot/latest', { params: { zone } }).then((r) => r.data);

export const getMarketSpotStats = (days = 7, zone = 'FR') =>
  api.get('/market/spot/stats', { params: { days, zone } }).then((r) => r.data);

export const getMarketSpotHistory = (days = 7, zone = 'FR') =>
  api.get('/market/spot/history', { params: { days, zone } }).then((r) => r.data);

// ── Forwards ──
export const getMarketForwards = (zone = 'FR', product = 'BASELOAD') =>
  api.get('/market/forwards', { params: { zone, product } }).then((r) => r.data);

// ── Tarifs réglementaires ──
export const getMarketTariffsCurrent = (profile = 'C4') =>
  api.get('/market/tariffs/current', { params: { profile } }).then((r) => r.data);

// ── Décomposition prix ──
export const getMarketDecomposition = (profile = 'C4', energy_price = null, method = null) =>
  api
    .get('/market/decomposition/compute', { params: { profile, energy_price, method } })
    .then((r) => r.data);

export const getMarketDecompositionCompare = (energy_price = null) =>
  api.get('/market/decomposition/compare', { params: { energy_price } }).then((r) => r.data);

// ── Fraîcheur ──
export const getMarketFreshness = () => api.get('/market/freshness').then((r) => r.data);
