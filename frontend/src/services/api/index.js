/**
 * PROMEOS - API Index
 * Re-exports all domain modules for backward compatibility.
 */

// Core utilities
export {
  default,
  cachedGet,
  clearApiCache,
  getApiCacheSize,
  getLastRequests,
  setApiScope,
  isDemoPath,
  normalizePathFromAxiosConfig,
  isSilentUrl,
} from './core';

// Domain modules
export * from './auth';
export * from './patrimoine';
export * from './conformite';
export * from './billing';
export * from './purchase';
export * from './actions';
export * from './energy';
export * from './cockpit';
export * from './admin';
export * from './market';
export * from './contractsV2';
export * from './pilotage';
export * from './cxDashboard';
