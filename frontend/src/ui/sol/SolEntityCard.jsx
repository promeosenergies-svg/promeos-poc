/**
 * PROMEOS — SolEntityCard (Pattern C Lot 3)
 *
 * Card latérale « fiche entité » : title Fraunces + subtitle DM Sans + status
 * pill optionnelle en haut à droite, grid 2 colonnes (label mono uppercase /
 * value DM Sans ou mono tabular), actions footer optionnelles.
 *
 * Props :
 *   - title:    string
 *   - subtitle?: string
 *   - status?:  { label: string, tone: 'calme'|'attention'|'afaire'|'succes'|'refuse' }
 *   - fields:   Array<{ label: string, value: React.ReactNode, mono?: boolean }>
 *   - actions?: React.ReactNode
 *
 * Largeur : 280px par défaut, propagée via parent (SolDetailPage grid).
 */
import React from 'react';

const STATUS_TONE_MAP = {
  calme: { bg: 'var(--sol-calme-bg)', fg: 'var(--sol-calme-fg)' },
  attention: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  afaire: { bg: 'var(--sol-afaire-bg)', fg: 'var(--sol-afaire-fg)' },
  succes: { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' },
  refuse: { bg: 'var(--sol-refuse-bg)', fg: 'var(--sol-refuse-fg)' },
};

function StatusPill({ label, tone = 'calme' }) {
  const style = STATUS_TONE_MAP[tone] || STATUS_TONE_MAP.calme;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontFamily: 'var(--sol-font-mono)',
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        fontWeight: 600,
        padding: '2px 6px',
        borderRadius: 2,
        background: style.bg,
        color: style.fg,
        lineHeight: 1.2,
      }}
    >
      {label}
    </span>
  );
}

export default function SolEntityCard({ title, subtitle, status, fields = [], actions }) {
  return (
    <aside
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderRadius: 6,
        padding: '18px 20px',
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.03)',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 12,
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h3
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 18,
              fontWeight: 600,
              color: 'var(--sol-ink-900)',
              margin: 0,
              lineHeight: 1.2,
              letterSpacing: '-0.005em',
            }}
          >
            {title}
          </h3>
          {subtitle && (
            <p
              style={{
                fontFamily: 'var(--sol-font-body)',
                fontSize: 13,
                color: 'var(--sol-ink-500)',
                margin: '4px 0 0',
                lineHeight: 1.4,
              }}
            >
              {subtitle}
            </p>
          )}
        </div>
        {status && <StatusPill label={status.label} tone={status.tone} />}
      </header>

      {fields.length > 0 && (
        <dl
          style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr)',
            rowGap: 10,
            margin: 0,
            padding: 0,
          }}
        >
          {fields.map((f, i) => (
            <div
              key={`${f.label}-${i}`}
              style={{ display: 'flex', flexDirection: 'column', gap: 2 }}
            >
              <dt
                style={{
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10.5,
                  letterSpacing: '0.1em',
                  textTransform: 'uppercase',
                  color: 'var(--sol-ink-500)',
                  margin: 0,
                }}
              >
                {f.label}
              </dt>
              <dd
                style={{
                  fontFamily: f.mono ? 'var(--sol-font-mono)' : 'var(--sol-font-body)',
                  fontSize: 13.5,
                  color: 'var(--sol-ink-900)',
                  margin: 0,
                  fontVariantNumeric: f.mono ? 'tabular-nums' : undefined,
                  wordBreak: 'break-word',
                }}
              >
                {f.value}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {actions && (
        <footer
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            paddingTop: 12,
            borderTop: '1px solid var(--sol-ink-200)',
          }}
        >
          {actions}
        </footer>
      )}
    </aside>
  );
}
