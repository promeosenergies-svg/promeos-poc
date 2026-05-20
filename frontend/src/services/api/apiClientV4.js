/**
 * M2-5.1 — Client API V4 (isolé du legacy core.js).
 *
 * Doctrine: instance axios séparée du legacy pour isolation stricte, aucun
 * intercepteur partagé. Gère un unique interceptor JWT Bearer
 * (localStorage['promeos_token']), la normalisation des erreurs en
 * `err.promeos`, et la purge du token sur 401.
 *
 * AUCUN scope header (X-Org-Id / X-Site-Id) n'est envoyé : le backend V4
 * dérive l'organisation du claim `org_id` du JWT (populate_org_context).
 */
import axios from 'axios';

const apiClientV4 = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  withCredentials: false,
});

// Interceptor: JWT depuis localStorage (même clé que legacy pour SSO transparent)
apiClientV4.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('promeos_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor: normalisation erreurs + propagation 401
apiClientV4.interceptors.response.use(
  (response) => response,
  (error) => {
    // 401 → purge token (cohérent avec legacy)
    if (error.response?.status === 401) {
      localStorage.removeItem('promeos_token');
    }

    // Normalisation: error.promeos contient le détail PROMEOS si présent
    const detail = error.response?.data?.detail;
    if (detail && typeof detail === 'object' && detail.code) {
      error.promeos = {
        code: detail.code,
        message: detail.message,
        hint: detail.hint,
        status: error.response.status,
      };
    }

    return Promise.reject(error);
  }
);

export default apiClientV4;
