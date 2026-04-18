/**
 * PROMEOS — SolHero
 *
 * Carte "Sol propose une action" — signature visuelle de Sol V1.
 *
 * 3 métriques inline : valeur récupérable, confiance calcul, temps pour valider.
 * CTA primaire "Voir ce que j'enverrai" (ouvre drawer).
 * CTA secondaire "Plus tard" (dismiss).
 *
 * Maquette référence : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *   (Sol hero section, background accent-calme-fg left border)
 */

export default function SolHero({
  title,
  summary,
  metrics = [],
  onPreview,
  onDismiss,
  chipLabel = 'Sol propose · action agentique',
}) {
  return (
    <section
      className="sol-hero"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        padding: '20px 24px',
        borderRadius: '6px',
        margin: '20px 0 24px 0',
        display: 'grid',
        gridTemplateColumns: '1fr auto',
        gap: '20px',
        alignItems: 'center',
      }}
    >
      <div>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '10.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-calme-fg)',
            fontWeight: 600,
            marginBottom: '10px',
          }}
        >
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              background: 'var(--sol-calme-fg)',
              animation: 'sol-pulse 2.5s ease-in-out infinite',
            }}
          />
          {chipLabel}
        </span>
        <h2
          style={{
            fontSize: '18px',
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: '0 0 6px 0',
            lineHeight: 1.3,
            letterSpacing: '-0.015em',
          }}
        >
          {title}
        </h2>
        <p
          style={{
            fontSize: '13.5px',
            color: 'var(--sol-ink-500)',
            lineHeight: 1.55,
            margin: 0,
            maxWidth: '520px',
          }}
        >
          {summary}
        </p>
        {metrics.length > 0 && (
          <div style={{ display: 'flex', gap: '24px', marginTop: '14px' }}>
            {metrics.map((m) => (
              <div key={m.label}>
                <div
                  style={{
                    fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
                    fontSize: '16px',
                    fontWeight: 600,
                    color: 'var(--sol-ink-900)',
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    fontSize: '11px',
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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: '180px' }}>
        {onPreview && (
          <button
            type="button"
            onClick={onPreview}
            style={{
              fontSize: '13.5px',
              fontWeight: 500,
              padding: '9px 16px',
              borderRadius: '4px',
              border: '1px solid transparent',
              background: 'var(--sol-calme-fg)',
              color: '#FFFFFF',
              cursor: 'pointer',
              textAlign: 'center',
            }}
          >
            Voir ce que j'enverrai
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            style={{
              fontSize: '13.5px',
              fontWeight: 500,
              padding: '9px 16px',
              borderRadius: '4px',
              border: 'none',
              background: 'transparent',
              color: 'var(--sol-ink-500)',
              cursor: 'pointer',
            }}
          >
            Plus tard
          </button>
        )}
      </div>
    </section>
  );
}
