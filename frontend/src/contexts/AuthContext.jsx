/**
 * PROMEOS - Auth Context
 * Manages user authentication state, JWT tokens, and permissions.
 */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import api from '../services/api';

const TOKEN_KEY = 'promeos_token';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [org, setOrg] = useState(null);
  const [role, setRole] = useState(null);
  const [orgs, setOrgs] = useState([]);
  const [permissions, setPermissions] = useState(null);
  const [scopes, setScopes] = useState([]);
  const [loading, setLoading] = useState(true);

  const isAuthenticated = !!user;

  const _applyLoginResponse = useCallback((data) => {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
    setOrg(data.org);
    setRole(data.role);
    setOrgs(data.orgs || []);
    setPermissions(data.permissions || null);
    setScopes(data.scopes || []);
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    _applyLoginResponse(res.data);
    return res.data;
  }, [_applyLoginResponse]);

  const logout = useCallback(() => {
    api.post('/auth/logout').catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    setOrg(null);
    setRole(null);
    setOrgs([]);
    setPermissions(null);
    setScopes([]);
  }, []);

  const switchOrg = useCallback(async (orgId) => {
    const res = await api.post('/auth/switch-org', { org_id: orgId });
    _applyLoginResponse(res.data);
    return res.data;
  }, [_applyLoginResponse]);

  const refreshToken = useCallback(async () => {
    try {
      const res = await api.post('/auth/refresh');
      if (res.data.access_token) {
        localStorage.setItem(TOKEN_KEY, res.data.access_token);
      }
    } catch {
      logout();
    }
  }, [logout]);

  // Check permission helper
  const hasPermission = useCallback((action, module) => {
    if (!permissions) return false;
    if (action === 'admin' || action === 'export' || action === 'sync' || action === 'approve') {
      return permissions[action] === true;
    }
    const allowed = permissions[action];
    if (allowed === '__all__') return true;
    if (Array.isArray(allowed)) {
      return module ? allowed.includes(module) : allowed.length > 0;
    }
    return false;
  }, [permissions]);

  // On mount: try to restore session from token
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    api.get('/auth/me')
      .then((res) => {
        _applyLoginResponse(res.data);
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
      })
      .finally(() => setLoading(false));
  }, [_applyLoginResponse]);

  // Auto-refresh token every 20 minutes
  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = setInterval(refreshToken, 20 * 60 * 1000);
    return () => clearInterval(interval);
  }, [isAuthenticated, refreshToken]);

  const value = {
    user, org, role, orgs, permissions, scopes,
    isAuthenticated, loading,
    login, logout, switchOrg, refreshToken, hasPermission,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
