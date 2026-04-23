/**
 * PROMEOS — SolPanel (240px)
 * Titre module + description + sections avec items (depuis NavRegistry).
 * Lit le registry, la route courante. Zéro fetch.
 *
 * Props :
 *   desc       : override description (sinon lit NAV_MODULES.desc)
 *   badges     : { [route]: string } — compteurs contextuels (ex. notifications)
 *   isExpert   : filtre items expertOnly
 *   rightSlot  : optionnel (ex. bouton "Réduire panel")
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Lock } from 'lucide-react';
import {
  resolveModule,
  getPanelSections,
  NAV_MODULES,
  ROUTE_MODULE_MAP,
} from '../../layout/NavRegistry';
import { resolveBackendPermissionKey } from '../../layout/permissionMap';
import { useAuth } from '../../contexts/AuthContext';

const LOCKED_TOOLTIP = 'Module non inclus dans votre rôle. Contactez votre administrateur.';

export default function SolPanel({
  desc,
  badges = {},
  isExpert = false,
  rightSlot = null,
  headerSlot = null,
  footerSlot = null,
  className = '',
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, hasPermission } = useAuth();
  const currentModule = resolveModule(location.pathname);
  const moduleMeta = NAV_MODULES.find((m) => m.key === currentModule);
  // V2 : panelSections par route (maquette) avec fallback sur NAV_SECTIONS
  const rawSections = getPanelSections(location.pathname, isExpert);

  // Permissions (Sprint 1 Vague A phases A2+A3) — parité NavPanel legacy.
  // Chaque item est enrichi avec `locked: boolean` plutôt que masqué.
  // A3 rend un cadenas + tooltip au lieu de disparaître silencieusement
  // → UX transparente + upsell potentiel.
  //
  // Logique :
  //   - requireAdmin && !hasPermission('admin') → locked
  //   - basePath hors ROUTE_MODULE_MAP → toujours visible (deep-links Raccourcis)
  //   - sinon → locked si !hasPermission('view', PERMISSION_KEY_MAP[module])
  //             && !hasPermission('admin')
  //   - non authentifié → rien de locké (avant login tout passe)
  const sections = React.useMemo(() => {
    if (!isAuthenticated) {
      return rawSections.map((section) => ({
        ...section,
        items: (section.items || []).map((item) => ({ ...item, locked: false })),
      }));
    }
    return rawSections
      .map((section) => ({
        ...section,
        items: (section.items || []).map((item) => {
          if (item.requireAdmin) {
            return { ...item, locked: !hasPermission('admin') };
          }
          const basePath = item.to.split('?')[0].split('#')[0];
          const navModule = ROUTE_MODULE_MAP[basePath];
          if (navModule === undefined) return { ...item, locked: false };
          const backendKey = resolveBackendPermissionKey(navModule);
          const allowed = hasPermission('view', backendKey) || hasPermission('admin');
          return { ...item, locked: !allowed };
        }),
      }))
      .filter((section) => section.items.length > 0);
  }, [rawSections, isAuthenticated, hasPermission]);

  return (
    <aside
      className={`sol-panel sol-app-panel ${className}`.trim()}
      aria-label="Navigation contextuelle"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRight: '1px solid var(--sol-rule)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0, // critical pour laisser l'enfant scroll dans un flex parent
      }}
    >
      {/* Header slot — reste visible (pas sticky — naturellement au-dessus
          du flex:1 scroll area, donc toujours accessible). */}
      {headerSlot}
      {/* Scroll zone : sections navigation, flex:1 + overflowY auto */}
      <div
        className="sol-panel-body"
        style={{
          padding: '16px 14px 0',
          flex: 1,
          minHeight: 0,
          overflowY: 'auto',
        }}
      >
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginBottom: 4,
          }}
        >
          <h2
            className="sol-panel-module"
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 18,
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
              letterSpacing: '-0.015em',
              margin: 0,
            }}
          >
            {moduleMeta?.label || 'Navigation'}
          </h2>
          {rightSlot}
        </header>
        <p
          className="sol-panel-desc"
          style={{
            fontSize: 12.5,
            color: 'var(--sol-ink-500)',
            lineHeight: 1.45,
            margin: '0 0 18px 0',
          }}
        >
          {desc || moduleMeta?.desc || ''}
        </p>

        {sections.map((section) => {
          const items = section.items || [];
          if (items.length === 0) return null;
          return (
            <div key={section.key} className="sol-panel-section" style={{ marginBottom: 20 }}>
              <p
                className="sol-panel-section-label"
                style={{
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 9.5,
                  textTransform: 'uppercase',
                  letterSpacing: '0.14em',
                  fontWeight: 600,
                  color: 'var(--sol-ink-400)',
                  margin: '0 0 8px 2px',
                }}
              >
                {section.label}
              </p>
              {items.map((item) => {
                const basePath = item.to.split('?')[0].split('#')[0];
                const isActive =
                  basePath === location.pathname ||
                  (basePath !== '/' && location.pathname.startsWith(basePath + '/'));
                const badge = badges[basePath] ?? badges[item.to];
                const locked = item.locked === true;
                return (
                  <button
                    key={item.to}
                    type="button"
                    onClick={locked ? undefined : () => navigate(item.to)}
                    disabled={locked}
                    aria-current={isActive ? 'page' : undefined}
                    aria-disabled={locked || undefined}
                    aria-label={locked ? `${item.label} — ${LOCKED_TOOLTIP}` : undefined}
                    title={locked ? LOCKED_TOOLTIP : undefined}
                    data-locked={locked || undefined}
                    className={`sol-panel-item ${isActive ? 'is-active' : ''}${locked ? ' is-locked' : ''}`.trim()}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '7px 8px',
                      borderRadius: 4,
                      color: locked
                        ? 'var(--sol-ink-400)'
                        : isActive
                          ? 'var(--sol-calme-fg)'
                          : 'var(--sol-ink-700)',
                      background: isActive && !locked ? 'var(--sol-calme-bg)' : 'transparent',
                      fontSize: 13,
                      fontWeight: isActive && !locked ? 500 : 400,
                      cursor: locked ? 'not-allowed' : 'pointer',
                      opacity: locked ? 0.55 : 1,
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      transition: 'background 120ms ease',
                    }}
                  >
                    <span style={{ flex: 1, lineHeight: 1.3 }}>
                      {item.label}
                      {item.desc && (
                        <span
                          className="sol-panel-item-desc"
                          style={{
                            display: 'block',
                            fontSize: 11,
                            color: 'var(--sol-ink-400)',
                            marginTop: 1,
                            lineHeight: 1.35,
                            fontWeight: 400,
                          }}
                        >
                          {item.desc}
                        </span>
                      )}
                    </span>
                    {locked && (
                      <Lock
                        size={12}
                        aria-hidden="true"
                        data-testid="sol-panel-item-lock"
                        style={{ color: 'var(--sol-ink-400)', flexShrink: 0 }}
                      />
                    )}
                    {badge != null && (
                      <span
                        className="sol-panel-item-badge"
                        style={{
                          fontFamily: 'var(--sol-font-mono)',
                          fontSize: 10,
                          background: 'var(--sol-afaire-bg)',
                          color: 'var(--sol-afaire-fg)',
                          padding: '1px 5px',
                          borderRadius: 2,
                          fontWeight: 600,
                        }}
                      >
                        {badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
      {footerSlot}
    </aside>
  );
}
