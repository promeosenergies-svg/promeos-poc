/**
 * grammar/hub/QueueP2P3 — File d'arbitrages secondaires P2/P3 de la
 * Synthèse Stratégique (ADR-023 §3 queue_p2_p3).
 *
 * Affiche une liste compacte d'arbitrages tier P2/P3 (3-5 entrées strictement
 * — verrou source-guard G6). Chaque ligne : badge tier + titre + contexte +
 * valeur (k€/an ou délai).
 *
 * Props :
 *   items  — list[{ tier, title, context, value_label }]
 *
 * Display-only — provient de payload.queue_p2_p3.
 */

export default function QueueP2P3({ items = [] }) {
  if (!Array.isArray(items) || items.length === 0) return null;
  return (
    <section data-component="QueueP2P3" className="mb-5">
      <h3
        style={{
          fontFamily: 'var(--sol-font-display, serif)',
          fontSize: '18px',
          color: 'var(--sol-ink-900, #1A1612)',
          margin: '0 0 12px',
        }}
      >
        Arbitrages secondaires (P2-P3)
      </h3>
      <div className="flex flex-col gap-2">
        {items.map((row, idx) => (
          <div
            key={`${row.tier}-${row.title}-${idx}`}
            className="rounded-md border p-4 flex items-center justify-between"
            style={{
              background: 'var(--sol-bg-card, #FFFFFF)',
              borderColor: 'var(--sol-ink-200, #E5DDD0)',
            }}
            data-tier={row.tier}
          >
            <div className="flex items-baseline gap-3 flex-1 min-w-0">
              <span
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  fontSize: '11px',
                  padding: '3px 8px',
                  background: 'var(--sol-ink-100, #F2EDE5)',
                  borderRadius: '4px',
                  color: 'var(--sol-ink-700, #3D362C)',
                  flexShrink: 0,
                }}
              >
                {row.tier}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <strong
                  style={{
                    color: 'var(--sol-ink-900, #1A1612)',
                    fontSize: '14px',
                  }}
                >
                  {row.title}
                </strong>
                {row.context && (
                  <span
                    style={{
                      color: 'var(--sol-ink-500, #7A6E5C)',
                      fontSize: '12.5px',
                      marginLeft: '8px',
                    }}
                  >
                    · {row.context}
                  </span>
                )}
              </div>
            </div>
            {row.value_label && (
              <span
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  color: 'var(--sol-ink-500, #7A6E5C)',
                  fontSize: '12.5px',
                  marginLeft: '12px',
                  flexShrink: 0,
                }}
              >
                {row.value_label}
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
