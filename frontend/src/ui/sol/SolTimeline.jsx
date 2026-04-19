/**
 * PROMEOS — SolTimeline (Pattern C Lot 3)
 *
 * Timeline verticale append-only (inspirée journal maquette) : rail gauche
 * 2px ink-200, dots colorés selon tone, contenu à droite (datetime mono +
 * title DM Sans + description).
 *
 * Le dernier événement est mis en emphase (dot 10px + glow) pour signaler
 * « most recent ». Si `deeplink` fourni, le bloc devient cliquable et
 * appelle `onNavigate(deeplink)` (déléguer React Router à l'appelant).
 *
 * Props :
 *   - events:     Array<{ datetime, type?, title, description?, tone?, deeplink? }>
 *   - onNavigate?: (deeplink: string) => void
 *   - emptyLabel?: string  — affiché si events vide (défaut "Aucun événement")
 */
import React from 'react';

const TONE_FG = {
  calme: 'var(--sol-calme-fg)',
  attention: 'var(--sol-attention-fg)',
  afaire: 'var(--sol-afaire-fg)',
  succes: 'var(--sol-succes-fg)',
  refuse: 'var(--sol-refuse-fg)',
  neutral: 'var(--sol-ink-400)',
};

const RAIL_WIDTH = 2;
const DOT_SIZE = 8;
const DOT_LAST_SIZE = 10;
const RAIL_LEFT = 6;

export default function SolTimeline({ events = [], onNavigate, emptyLabel = 'Aucun événement' }) {
  if (!Array.isArray(events) || events.length === 0) {
    return (
      <p
        style={{
          fontFamily: 'var(--sol-font-body)',
          fontSize: 13,
          color: 'var(--sol-ink-500)',
          fontStyle: 'italic',
          margin: 0,
        }}
      >
        {emptyLabel}
      </p>
    );
  }

  return (
    <ol
      style={{
        position: 'relative',
        listStyle: 'none',
        margin: 0,
        paddingLeft: RAIL_LEFT + 18,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: 4,
          bottom: 4,
          left: RAIL_LEFT + DOT_SIZE / 2 - RAIL_WIDTH / 2,
          width: RAIL_WIDTH,
          background: 'var(--sol-ink-200)',
        }}
      />
      {events.map((ev, idx) => {
        const tone = ev.tone || 'neutral';
        const isLast = idx === events.length - 1;
        const size = isLast ? DOT_LAST_SIZE : DOT_SIZE;
        const clickable = Boolean(ev.deeplink && onNavigate);
        const handleClick = clickable ? () => onNavigate(ev.deeplink) : undefined;
        const handleKey = clickable
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onNavigate(ev.deeplink);
              }
            }
          : undefined;
        return (
          <li
            key={ev.id ?? `${ev.datetime}-${idx}`}
            role={clickable ? 'button' : undefined}
            tabIndex={clickable ? 0 : undefined}
            onClick={handleClick}
            onKeyDown={handleKey}
            style={{
              position: 'relative',
              paddingBottom: idx < events.length - 1 ? 18 : 0,
              cursor: clickable ? 'pointer' : 'default',
            }}
          >
            <span
              aria-hidden="true"
              style={{
                position: 'absolute',
                left: -(RAIL_LEFT + 18 - (RAIL_LEFT + DOT_SIZE / 2 - size / 2)),
                top: 6,
                width: size,
                height: size,
                borderRadius: '50%',
                background: TONE_FG[tone] || TONE_FG.neutral,
                boxShadow: isLast
                  ? `0 0 0 3px var(--sol-bg-paper), 0 0 0 4px ${TONE_FG[tone] || TONE_FG.neutral}22`
                  : '0 0 0 3px var(--sol-bg-paper)',
              }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {ev.datetime && (
                <span
                  style={{
                    fontFamily: 'var(--sol-font-mono)',
                    fontSize: 10.5,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: 'var(--sol-ink-500)',
                  }}
                >
                  {ev.datetime}
                  {ev.type && (
                    <>
                      {' · '}
                      <span style={{ color: TONE_FG[tone] || TONE_FG.neutral, fontWeight: 600 }}>
                        {ev.type}
                      </span>
                    </>
                  )}
                </span>
              )}
              <span
                style={{
                  fontFamily: 'var(--sol-font-body)',
                  fontSize: 14,
                  fontWeight: 500,
                  color: 'var(--sol-ink-900)',
                  lineHeight: 1.35,
                }}
              >
                {ev.title}
              </span>
              {ev.description && (
                <span
                  style={{
                    fontFamily: 'var(--sol-font-body)',
                    fontSize: 13,
                    color: 'var(--sol-ink-700)',
                    lineHeight: 1.4,
                  }}
                >
                  {ev.description}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
