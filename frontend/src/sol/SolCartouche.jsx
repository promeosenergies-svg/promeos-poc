/**
 * PROMEOS — SolCartouche
 *
 * Status bar bas-droite persistante Sol V1. 5 états :
 *   repos      — Sol en veille, pas d'action en cours
 *   proposing  — Sol propose une action (accent calme, pulse)
 *   pending    — Action confirmée en grace period (accent attention)
 *   executing  — Action en cours d'exécution (accent calme, pulse rapide)
 *   done       — Action exécutée avec succès (accent succès)
 *
 * Maquette référence : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 * Accessibilité : role=status aria-live=polite, respect prefers-reduced-motion.
 */
import { useMemo } from 'react';

const STATE_STYLES = {
  repos: {
    dotColor: 'var(--sol-ink-400)',
    border: 'var(--sol-rule)',
    bg: 'var(--sol-bg-paper)',
    label: 'Sol',
    pulse: false,
  },
  proposing: {
    dotColor: 'var(--sol-calme-fg)',
    border: 'var(--sol-calme-fg)',
    bg: 'var(--sol-calme-bg)',
    label: 'Sol propose',
    pulse: true,
  },
  pending: {
    dotColor: 'var(--sol-attention-fg)',
    border: 'var(--sol-attention-fg)',
    bg: 'var(--sol-attention-bg)',
    label: 'Sol · en attente',
    pulse: true,
  },
  executing: {
    dotColor: 'var(--sol-calme-fg)',
    border: 'var(--sol-calme-fg)',
    bg: 'var(--sol-bg-paper)',
    label: 'Sol · en cours',
    pulse: true,
  },
  done: {
    dotColor: 'var(--sol-succes-fg)',
    border: 'var(--sol-succes-fg)',
    bg: 'var(--sol-succes-bg)',
    label: 'Sol · validé',
    pulse: false,
  },
};

export default function SolCartouche({ state = 'repos', message = '', onClick = null }) {
  const styles = useMemo(() => STATE_STYLES[state] || STATE_STYLES.repos, [state]);

  return (
    <button
      type="button"
      role="status"
      aria-live="polite"
      aria-label={`${styles.label}. ${message || 'En veille.'}`}
      onClick={onClick}
      disabled={!onClick}
      className="sol-cartouche"
      style={{
        position: 'fixed',
        bottom: '48px',
        right: '24px',
        zIndex: 50,
        padding: '10px 14px',
        borderRadius: '4px',
        border: `1px solid ${styles.border}`,
        background: styles.bg,
        color: 'var(--sol-ink-700)',
        fontSize: '12.5px',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        maxWidth: '340px',
        cursor: onClick ? 'pointer' : 'default',
        boxShadow: '0 2px 8px rgba(15, 23, 42, 0.06)',
        transition: 'all 180ms ease',
      }}
    >
      <span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: styles.dotColor,
          flexShrink: 0,
          animation: styles.pulse ? 'sol-pulse 2.5s ease-in-out infinite' : 'none',
        }}
      />
      <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
        <span
          style={{
            fontSize: '10.5px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: 'var(--sol-ink-500)',
            fontWeight: 600,
          }}
        >
          {styles.label}
        </span>
        {message && (
          <span
            style={{
              fontSize: '13px',
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
              textAlign: 'left',
            }}
          >
            {message}
          </span>
        )}
      </span>
    </button>
  );
}
