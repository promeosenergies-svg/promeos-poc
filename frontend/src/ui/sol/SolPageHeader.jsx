/**
 * PROMEOS — SolPageHeader
 *
 * Header de page éditorial dans l'esprit maquette V2 raw :
 * kicker mono uppercase + title Fraunces 600 italic-hook + narrative
 * + subNarrative + slot droit optionnel (period selector, actions).
 *
 * Source : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *   .page-head + .page-title + .sol-headline + .sol-subline
 */

export default function SolPageHeader({
  kicker,
  title,
  titleEm = '',
  narrative,
  subNarrative,
  rightSlot,
}) {
  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        paddingTop: 12,
        paddingBottom: 14,
        borderBottom: '1px solid var(--sol-rule)',
        marginBottom: 18,
        gap: 24,
        flexWrap: 'wrap',
        // Sticky header — reste visible au scroll, fond canvas pour
        // ne pas voir le contenu derrière (audit user round 5).
        position: 'sticky',
        top: 0,
        zIndex: 20,
        background: 'var(--sol-bg-canvas)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        {kicker && <div className="sol-page-kicker">{kicker}</div>}
        {title && (
          <h1 className="sol-page-title">
            {title}
            {titleEm && <em>{titleEm}</em>}
          </h1>
        )}
        {narrative && (
          <p className="sol-headline" style={{ marginTop: 14 }}>
            {narrative}
          </p>
        )}
        {subNarrative && <p className="sol-subline">{subNarrative}</p>}
      </div>
      {rightSlot && <div style={{ flexShrink: 0 }}>{rightSlot}</div>}
    </header>
  );
}
