import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoginBackground from './LoginBackground';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // RequireAuth push les deeplinks intercepted dans `state.from`.
  // Après login réussi, restaurer la route demandée (preserve query params).
  const redirectTo = (() => {
    const from = location.state?.from;
    if (!from) return '/';
    const path = from.pathname || '/';
    if (path === '/login') return '/';
    return `${path}${from.search || ''}${from.hash || ''}`;
  })();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Identifiants incorrects');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated background */}
      <LoginBackground />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-[400px] mx-4">
        {/* Header */}
        <div className="text-center mb-6">
          <h1
            style={{
              fontSize: 30,
              fontWeight: 700,
              color: '#ffffff',
              letterSpacing: 3,
            }}
          >
            PROMEOS
          </h1>
          <p
            style={{
              fontSize: 14,
              color: '#5eead4',
              letterSpacing: 1.5,
              fontStyle: 'italic',
              fontWeight: 400,
              marginTop: 8,
            }}
          >
            Votre énergie, votre maîtrise
          </p>
        </div>

        {/* Card */}
        <div
          style={{
            background: 'rgba(22, 48, 82, 0.85)',
            border: '1.5px solid rgba(45, 212, 191, 0.35)',
            borderRadius: 14,
            padding: '2rem 2.25rem',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
          }}
        >
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="login-email"
                style={{
                  display: 'block',
                  fontSize: 12,
                  color: '#94a3b8',
                  letterSpacing: 0.5,
                  fontWeight: 500,
                  marginBottom: 6,
                }}
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@example.com"
                required
                autoFocus
                style={{
                  width: '100%',
                  background: 'rgba(30, 61, 107, 0.7)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: 8,
                  padding: '11px 14px',
                  color: '#e2e8f0',
                  fontSize: 14,
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s',
                }}
                onFocus={(e) => (e.target.style.borderColor = 'rgba(45, 212, 191, 0.6)')}
                onBlur={(e) => (e.target.style.borderColor = 'rgba(56, 189, 248, 0.2)')}
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                style={{
                  display: 'block',
                  fontSize: 12,
                  color: '#94a3b8',
                  letterSpacing: 0.5,
                  fontWeight: 500,
                  marginBottom: 6,
                }}
              >
                Mot de passe
              </label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                style={{
                  width: '100%',
                  background: 'rgba(30, 61, 107, 0.7)',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: 8,
                  padding: '11px 14px',
                  color: '#e2e8f0',
                  fontSize: 14,
                  outline: 'none',
                  boxSizing: 'border-box',
                  transition: 'border-color 0.2s',
                }}
                onFocus={(e) => (e.target.style.borderColor = 'rgba(45, 212, 191, 0.6)')}
                onBlur={(e) => (e.target.style.borderColor = 'rgba(56, 189, 248, 0.2)')}
              />
            </div>

            {error && (
              <div
                style={{
                  fontSize: 13,
                  color: '#fca5a5',
                  background: 'rgba(220, 38, 38, 0.15)',
                  padding: '8px 12px',
                  borderRadius: 8,
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                background: 'linear-gradient(135deg, #0d9488, #0ea5e9)',
                border: 'none',
                borderRadius: 8,
                padding: 12,
                color: '#ffffff',
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: 0.5,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.6 : 1,
                transition: 'opacity 0.2s, transform 0.1s',
              }}
              onMouseEnter={(e) => {
                if (!loading) e.target.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.target.style.transform = 'translateY(0)';
              }}
              onMouseDown={(e) => {
                e.target.style.transform = 'translateY(0)';
              }}
            >
              {loading ? 'Connexion...' : 'Se connecter'}
            </button>
          </form>

          {/* Demo hint */}
          <p
            style={{
              fontSize: 11,
              color: 'rgba(148, 163, 184, 0.5)',
              textAlign: 'center',
              marginTop: '1.25rem',
            }}
          >
            Démo : promeos@promeos.io / promeos2024
          </p>
        </div>
      </div>
    </div>
  );
}
