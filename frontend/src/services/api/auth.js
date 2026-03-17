/**
 * PROMEOS - API Auth
 * Authentication, IAM, audit log
 */
import api from './core';

// ── Auth ──
export const loginAuth = (email, password) =>
  api.post('/auth/login', { email, password }).then((r) => r.data);
export const refreshAuth = () => api.post('/auth/refresh').then((r) => r.data);
export const getAuthMe = () => api.get('/auth/me').then((r) => r.data);
export const logoutAuth = () => api.post('/auth/logout').then((r) => r.data);
export const changePassword = (currentPassword, newPassword) =>
  api
    .put('/auth/password', { current_password: currentPassword, new_password: newPassword })
    .then((r) => r.data);
export const switchOrg = (orgId) =>
  api.post('/auth/switch-org', { org_id: orgId }).then((r) => r.data);

// ── Audit Log ──
export const getAuditLogs = (params = {}) => api.get('/auth/audit', { params }).then((r) => r.data);

// ── Impersonate ──
export const impersonateUser = (email) =>
  api.post('/auth/impersonate', { email }).then((r) => r.data);
