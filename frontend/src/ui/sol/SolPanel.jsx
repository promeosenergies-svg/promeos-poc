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
import {
  resolveModule,
  getSectionsForModule,
  getVisibleItems,
  NAV_MODULES,
} from '../../layout/NavRegistry';

export default function SolPanel({
  desc,
  badges = {},
  isExpert = false,
  rightSlot = null,
  className = '',
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const currentModule = resolveModule(location.pathname);
  const moduleMeta = NAV_MODULES.find((m) => m.key === currentModule);
  const sections = getSectionsForModule(currentModule);

  return (
    <aside
      className={`sol-panel sol-app-panel ${className}`.trim()}
      aria-label="Navigation contextuelle"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRight: '1px solid var(--sol-rule)',
        padding: '20px 18px',
        overflowY: 'auto',
      }}
    >
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
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
          margin: '0 0 22px 0',
        }}
      >
        {desc || moduleMeta?.desc || ''}
      </p>

      {sections.map((section) => {
        const items = getVisibleItems(section.items || [], isExpert);
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
              return (
                <button
                  key={item.to}
                  type="button"
                  onClick={() => navigate(item.to)}
                  aria-current={isActive ? 'page' : undefined}
                  className={`sol-panel-item ${isActive ? 'is-active' : ''}`.trim()}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '7px 8px',
                    borderRadius: 4,
                    color: isActive ? 'var(--sol-calme-fg)' : 'var(--sol-ink-700)',
                    background: isActive ? 'var(--sol-calme-bg)' : 'transparent',
                    fontSize: 13,
                    fontWeight: isActive ? 500 : 400,
                    cursor: 'pointer',
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
    </aside>
  );
}
