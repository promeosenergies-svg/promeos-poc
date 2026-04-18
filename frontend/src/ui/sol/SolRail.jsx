/**
 * PROMEOS — SolRail (56px)
 * Logo "P." Fraunces + icons modules depuis NavRegistry.
 * Lit le registry + route courante. Zéro fetch, zéro useState de données.
 *
 * Active state basé sur resolveModule(pathname).
 * Ordre modules : getOrderedModules(role, isExpert) du NavRegistry.
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getOrderedModules, resolveModule } from '../../layout/NavRegistry';

const MODULE_FIRST_ROUTE = {
  cockpit: '/',
  conformite: '/conformite',
  energie: '/consommations',
  patrimoine: '/patrimoine',
  achat: '/achat-energie',
  admin: '/admin/users',
};

export default function SolRail({ role = 'default', isExpert = false, className = '' }) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentModule = resolveModule(location.pathname);
  const modules = getOrderedModules(role, isExpert);

  return (
    <nav
      className={`sol-rail sol-app-rail ${className}`.trim()}
      aria-label="Navigation principale"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRight: '1px solid var(--sol-rule)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '18px 0',
        gap: 18,
      }}
    >
      <div
        className="sol-rail-logo"
        aria-label="PROMEOS"
        style={{
          fontFamily: 'var(--sol-font-display)',
          fontWeight: 600,
          fontSize: 22,
          color: 'var(--sol-ink-900)',
          letterSpacing: '-0.04em',
          lineHeight: 1,
          marginBottom: 8,
        }}
      >
        P.
      </div>
      {modules.map((mod) => {
        const Icon = mod.icon;
        const isActive = mod.key === currentModule;
        const target = MODULE_FIRST_ROUTE[mod.key] || '/';
        return (
          <button
            key={mod.key}
            type="button"
            aria-label={mod.label}
            aria-current={isActive ? 'page' : undefined}
            title={mod.label}
            onClick={() => navigate(target)}
            className={`sol-rail-icon ${isActive ? 'is-active' : ''}`.trim()}
            style={{
              width: 34,
              height: 34,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 4,
              background: isActive ? 'var(--sol-calme-bg)' : 'transparent',
              color: isActive ? 'var(--sol-calme-fg)' : 'var(--sol-ink-500)',
              border: 'none',
              cursor: 'pointer',
              transition: 'background 120ms ease, color 120ms ease',
            }}
          >
            {Icon ? <Icon size={18} strokeWidth={1.6} /> : null}
          </button>
        );
      })}
    </nav>
  );
}
