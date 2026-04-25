/**
 * PROMEOS — SolJournal
 * Journal append-only (actions Sol). Grid 160/100/1fr/120.
 * Présentation pure : rows pré-triées + formatées par le parent.
 *
 * Props :
 *   entries : [{ key, date, actor, action, status, statusKind }]
 *     - date  : string déjà formatée (ex "15 avr · 14 h 32")
 *     - actor : "SOL" ou nom utilisateur
 *     - action: phrase FR naturelle
 *     - status: "envoyé" / "annulé" / "en attente"
 *     - statusKind : 'ok' | 'att' | 'risk'
 */
import React from 'react';
import SolStatusPill from './SolStatusPill';

export default function SolJournal({ entries = [], className = '' }) {
  if (entries.length === 0) {
    return (
      <p
        style={{
          fontSize: 13,
          color: 'var(--sol-ink-400)',
          fontStyle: 'italic',
          textAlign: 'center',
          padding: '18px 0',
          margin: 0,
        }}
      >
        Aucune action Sol enregistrée pour l'instant.
      </p>
    );
  }
  return (
    <div
      className={`sol-journal ${className}`.trim()}
      style={{ borderTop: '1px solid var(--sol-ink-100)' }}
    >
      {entries.map((e) => (
        <div
          key={e.key}
          className="sol-journal-row"
          style={{
            display: 'grid',
            gridTemplateColumns: '160px 100px 1fr 120px',
            gap: 16,
            padding: '10px 0',
            borderBottom: '1px solid var(--sol-ink-100)',
            fontSize: 12.5,
            alignItems: 'baseline',
          }}
        >
          <span
            className="sol-journal-date"
            style={{
              fontFamily: 'var(--sol-font-mono)',
              color: 'var(--sol-ink-500)',
              fontSize: 11,
            }}
          >
            {e.date}
          </span>
          <span
            className="sol-journal-actor"
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 10.5,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--sol-calme-fg)',
              fontWeight: 600,
            }}
          >
            {e.actor}
          </span>
          <span
            className="sol-journal-action"
            style={{ color: 'var(--sol-ink-700)', lineHeight: 1.45 }}
          >
            {e.action}
          </span>
          <span className="sol-journal-status" style={{ textAlign: 'right' }}>
            <SolStatusPill kind={e.statusKind || 'ok'}>{e.status}</SolStatusPill>
          </span>
        </div>
      ))}
    </div>
  );
}
