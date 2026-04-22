/**
 * PROMEOS — SolDetailPage (Pattern C Lot 3 wrapper)
 *
 * Wrapper « fiche détail » : breadcrumb + header (kicker + title + narrative)
 * + grid 2 colonnes (entityCard 280px sticky + mainContent 1fr), avec rightRail
 * optionnel rendu sous le mainContent sur mobile.
 *
 * Contrairement à SolPageHeader, la fiche commence par un breadcrumb pour
 * situer l'entité dans sa hiérarchie (Patrimoine › Site X, Conformité › EFA Y…).
 *
 * Props :
 *   - breadcrumb:   { segments, backTo?, backLabel? }
 *   - kicker?:      string  — texte mono au-dessus du titre (ex. "FICHE SITE · ID 3")
 *   - title:        string
 *   - titleEm?:     string  — compléments italiques dans h1 (alignés SolPageHeader)
 *   - narrative?:   string
 *   - subNarrative?: string
 *   - entityCard:   React.ReactNode  — SolEntityCard déjà rendu
 *   - kpiRow?:      React.ReactNode  — SolKpiRow rendu en haut du mainContent
 *   - mainContent:  React.ReactNode  — corps principal (timeline, trajectoire, etc.)
 *   - rightRail?:   React.ReactNode  — slot additionnel rendu sous le main sur mobile
 *   - layerToggle?: React.ReactNode  — SolLayerToggle Surface/Inspect/Expert
 *
 * Layout CSS-in-JS (grid 2 colonnes desktop, empilé mobile).
 */
import React from 'react';
import SolBreadcrumb from './SolBreadcrumb';

export default function SolDetailPage({
  breadcrumb,
  kicker,
  title,
  titleEm,
  narrative,
  subNarrative,
  entityCard,
  kpiRow,
  mainContent,
  rightRail,
  layerToggle,
}) {
  return (
    <article style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {breadcrumb && <SolBreadcrumb {...breadcrumb} />}

      <header style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {kicker && (
          <span
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 10.5,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: 'var(--sol-ink-500)',
            }}
          >
            {kicker}
          </span>
        )}
        <h1
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 34,
            fontWeight: 500,
            color: 'var(--sol-ink-900)',
            margin: 0,
            lineHeight: 1.1,
            letterSpacing: '-0.01em',
          }}
        >
          {title}
          {titleEm && (
            <em
              style={{
                fontStyle: 'italic',
                color: 'var(--sol-ink-700)',
                fontWeight: 400,
              }}
            >
              {' '}
              {titleEm}
            </em>
          )}
        </h1>
        {narrative && (
          <p
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 15.5,
              color: 'var(--sol-ink-700)',
              margin: 0,
              lineHeight: 1.5,
              maxWidth: '70ch',
            }}
          >
            {narrative}
          </p>
        )}
        {subNarrative && (
          <p
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13.5,
              color: 'var(--sol-ink-500)',
              margin: 0,
              lineHeight: 1.4,
              maxWidth: '70ch',
            }}
          >
            {subNarrative}
          </p>
        )}
        {layerToggle && <div style={{ marginTop: 4 }}>{layerToggle}</div>}
      </header>

      <div
        className="sol-detail-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(260px, 280px) minmax(0, 1fr)',
          gap: 32,
          alignItems: 'flex-start',
        }}
      >
        <div style={{ position: 'sticky', top: 16, alignSelf: 'flex-start' }}>{entityCard}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, minWidth: 0 }}>
          {kpiRow}
          {mainContent}
          {rightRail}
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          .sol-detail-grid {
            grid-template-columns: 1fr !important;
          }
          .sol-detail-grid > div:first-child {
            position: static !important;
          }
        }
      `}</style>
    </article>
  );
}
