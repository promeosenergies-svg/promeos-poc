/**
 * PROMEOS — SolListPage (Lot 2 Phase 1, Pattern B wrapper)
 *
 * Wrapper complet pour les pages Pattern B (liste drillable) :
 *   SolBreadcrumb (opt) → header (kicker + title + titleEm + narrative +
 *   subNarrative + rightSlot) → kpiRow (opt) → preludeSlot (opt watchers)
 *   → SolExpertToolbar → SolExpertGridFull → SolPagination (opt)
 *   → drawerSlot (opt).
 *
 * Contrairement à SolDetailPage (Pattern C qui a un entityCard latéral),
 * SolListPage est mono-colonne pleine largeur. Idéal pour listes denses
 * 8+ colonnes.
 *
 * Props :
 *   - breadcrumb?: SolBreadcrumb props        — optionnel si page racine module
 *   - kicker: string
 *   - title: string
 *   - titleEm?: string
 *   - narrative?: string
 *   - subNarrative?: string
 *   - rightSlot?: ReactNode                   — boutons actions header
 *   - kpiRow?: ReactNode                      — SolKpiRow agrégats optionnel
 *   - preludeSlot?: ReactNode                 — cards watchers, banner, etc.
 *   - toolbar: ReactNode                      — SolExpertToolbar monté
 *   - grid: ReactNode                         — SolExpertGridFull monté
 *   - pagination?: ReactNode                  — SolPagination monté
 *   - drawerSlot?: ReactNode                  — drawer legacy rendu contextuel
 */
import React from 'react';
import SolBreadcrumb from './SolBreadcrumb';

export default function SolListPage({
  breadcrumb,
  kicker,
  title,
  titleEm,
  narrative,
  subNarrative,
  rightSlot,
  kpiRow,
  preludeSlot,
  toolbar,
  grid,
  pagination,
  drawerSlot,
}) {
  return (
    <article style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {breadcrumb && <SolBreadcrumb {...breadcrumb} />}

      <header
        style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          gap: 24,
          flexWrap: 'wrap',
          paddingBottom: 18,
          borderBottom: '1px solid var(--sol-rule)',
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
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
          {title && (
            <h1
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 34,
                fontWeight: 500,
                color: 'var(--sol-ink-900)',
                margin: '8px 0 0',
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
          )}
          {narrative && (
            <p
              style={{
                fontFamily: 'var(--sol-font-body)',
                fontSize: 15.5,
                color: 'var(--sol-ink-700)',
                margin: '12px 0 0',
                lineHeight: 1.5,
                maxWidth: '75ch',
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
                margin: '6px 0 0',
                lineHeight: 1.4,
                maxWidth: '75ch',
              }}
            >
              {subNarrative}
            </p>
          )}
        </div>
        {rightSlot && <div style={{ flexShrink: 0 }}>{rightSlot}</div>}
      </header>

      {kpiRow}
      {preludeSlot}
      {toolbar}
      {grid}
      {pagination}
      {drawerSlot}
    </article>
  );
}
