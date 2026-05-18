/**
 * M2-5.8.A — Wrapper d'authentification démo V4.
 *
 * `demoLogin()` appelle POST /api/auth/demo-login et stocke le JWT dans
 * localStorage['promeos_token'] — même clé que `apiClientV4` et le client
 * legacy (SSO transparent). L'endpoint backend est disponible uniquement en
 * DEMO_MODE (sinon 404). `hasValidToken()` / `clearToken()` complètent le cycle.
 */
import apiClientV4 from './apiClientV4';

const TOKEN_KEY = 'promeos_token';

/**
 * Connecte le pilote comme Marie Dupont (energy_manager HELIOS).
 * @returns {Promise<{user_email: string, organisation_id: number, expires_in: number}>}
 */
export async function demoLogin() {
  const response = await apiClientV4.post('/auth/demo-login');
  const { access_token, user_email, organisation_id, expires_in } = response.data;

  localStorage.setItem(TOKEN_KEY, access_token);

  return { user_email, organisation_id, expires_in };
}

/** True si un token est présent dans le localStorage. */
export function hasValidToken() {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

/** Purge le token (déconnexion / expiration). */
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}
