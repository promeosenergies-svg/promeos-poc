/**
 * PROMEOS — SolHero
 *
 * Card "Sol propose" signature éditoriale : chip pulse + title + description
 * + 3 metrics horizontales mono + CTA primaire agentique + CTA secondaire ghost.
 *
 * Source maquette : .sol-hero / .sol-chip-inline / .sol-hero-title / .sol-hero-metrics
 */

export default function SolHero({
  chip = 'Sol propose · action agentique',
  title,
  description,
  metrics = [],
  primaryLabel = "Voir ce que j'enverrai",
  onPrimary,
  secondaryLabel = 'Plus tard',
  onSecondary,
}) {
  if (!title) return null;

  return (
    <section
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-rule)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        padding: '24px 28px',
        borderRadius: 3,
        margin: '24px 0 32px',
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'center',
      }}
    >
      <div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 10.5,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-calme-fg)',
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: '50%',
              background: 'var(--sol-calme-fg)',
              animation: 'sol-pulse 3s ease-in-out infinite',
            }}
          />
          {chip}
        </div>

        <h3
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 20,
            fontWeight: 500,
            color: 'var(--sol-ink-900)',
            marginBottom: 6,
            lineHeight: 1.3,
            letterSpacing: '-0.015em',
          }}
        >
          {title}
        </h3>

        {description && (
          <p
            style={{
              fontSize: 13.5,
              color: 'var(--sol-ink-500)',
              lineHeight: 1.55,
              maxWidth: 520,
              margin: 0,
            }}
          >
            {description}
          </p>
        )}

        {metrics.length > 0 && (
          <div style={{ display: 'flex', gap: 24, marginTop: 14 }}>
            {metrics.map((m, i) => (
              <div key={i}>
                <div
                  style={{
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 16,
                    fontWeight: 600,
                    color: 'var(--sol-ink-900)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--sol-ink-500)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  {m.label}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 180 }}>
        {onPrimary && (
          <button
            type="button"
            onClick={onPrimary}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13.5,
              fontWeight: 500,
              padding: '9px 16px',
              borderRadius: 3,
              border: '1px solid transparent',
              background: 'var(--sol-calme-fg)',
              color: 'white',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 120ms ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#245047')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--sol-calme-fg)')}
          >
            {primaryLabel}
          </button>
        )}
        {onSecondary && (
          <button
            type="button"
            onClick={onSecondary}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13.5,
              fontWeight: 500,
              padding: '9px 16px',
              borderRadius: 3,
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--sol-ink-500)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--sol-ink-900)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--sol-ink-500)')}
          >
            {secondaryLabel}
          </button>
        )}
      </div>
    </section>
  );
}
