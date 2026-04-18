/**
 * PROMEOS — SolCartouche
 * Badge bas-droit fixed : 5 états default / proposing / pending / executing / done.
 * Pulse selon état. Max 340 px. Click → ouvre un drawer Sol (géré par parent).
 */
import React from 'react';

const STATE_COPY = {
  default: { chip: 'Sol · en veille', message: null, pulse: false },
  proposing: { chip: 'Sol · propose', message: 'Une action attend votre aval.', pulse: true },
  pending: { chip: 'Sol · en attente', message: 'Envoi programmé, réversible.', pulse: true },
  executing: { chip: 'Sol · exécute', message: 'Action en cours.', pulse: true },
  done: { chip: 'Sol · terminé', message: 'Action envoyée · trace archivée.', pulse: false },
};

export default function SolCartouche({ state = 'default', onClick, className = '' }) {
  const tone = STATE_COPY[state] || STATE_COPY.default;
  const interactive = typeof onClick === 'function';
  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={interactive ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(e); } : undefined}
      className={`sol-cartouche ${className}`.trim()}
      style={{
        position: 'fixed',
        bottom: 48,
        right: 24,
        zIndex: 50,
        maxWidth: 340,
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        borderRadius: 6,
        padding: '14px 18px',
        boxShadow: '0 6px 20px rgba(15, 23, 42, 0.08)',
        cursor: interactive ? 'pointer' : 'default',
      }}
    >
      <span
        className="sol-cartouche-chip"
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
          marginBottom: tone.message ? 6 : 0,
        }}
      >
        <span
          className="sol-cartouche-dot"
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--sol-calme-fg)',
            animation: tone.pulse ? 'sol-pulse 2.5s ease-in-out infinite' : 'none',
          }}
        />
        {tone.chip}
      </span>
      {tone.message && (
        <p
          className="sol-cartouche-message"
          style={{ fontSize: 13, color: 'var(--sol-ink-700)', lineHeight: 1.45, margin: 0 }}
        >
          {tone.message}
        </p>
      )}
    </div>
  );
}
