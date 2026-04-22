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
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        padding: '18px 22px',
        borderRadius: 8,
        margin: '20px 0 24px',
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: 24,
        alignItems: 'center',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
      }}
    >
      <div>
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 9.5,
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-calme-fg)',
            fontWeight: 600,
            background: 'var(--sol-calme-bg)',
            padding: '3px 8px',
            borderRadius: 99,
            marginBottom: 10,
          }}
        >
          <span
            style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: 'var(--sol-calme-fg)',
              animation: 'sol-pulse 3s ease-in-out infinite',
            }}
          />
          {chip}
        </div>

        <h3
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 16,
            fontWeight: 600,
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
              fontSize: 13,
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
          <div style={{ display: 'flex', gap: 18, marginTop: 10 }}>
            {metrics.map((m, i) => (
              <div key={m.label ?? m.value ?? i}>
                <div
                  style={{
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 15,
                    fontWeight: 600,
                    color: 'var(--sol-ink-900)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    fontSize: 10,
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
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 14px',
              borderRadius: 6,
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
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 14px',
              borderRadius: 6,
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
