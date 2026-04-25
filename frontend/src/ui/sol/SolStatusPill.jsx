/**
 * PROMEOS — SolStatusPill
 * Mini pill mono 10px : {ok, att, risk}. Vient à côté d'un chiffre ou label.
 */
import React from 'react';

const KIND_MAP = {
  ok: { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' },
  att: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  risk: { bg: 'var(--sol-refuse-bg)', fg: 'var(--sol-refuse-fg)' },
};

export default function SolStatusPill({ kind = 'ok', children, className = '' }) {
  const tone = KIND_MAP[kind] || KIND_MAP.ok;
  return (
    <span
      className={`sol-status-pill is-${kind} ${className}`.trim()}
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
        background: tone.bg,
        color: tone.fg,
        lineHeight: 1.2,
      }}
    >
      {children}
    </span>
  );
}
