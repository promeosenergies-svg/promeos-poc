/**
 * PROMEOS — SolInspectDoc
 * Container prose éditoriale pour mode Inspect : max-width 760, Fraunces 15/1.7.
 * Accepte du MD-like via enfants déjà rendus (pas de parsing ici).
 */
import React from 'react';

export default function SolInspectDoc({ children, className = '' }) {
  return (
    <div
      className={`sol-inspect-doc ${className}`.trim()}
      style={{
        maxWidth: 760,
        fontFamily: 'var(--sol-font-display)',
        fontSize: 15,
        lineHeight: 1.7,
        color: 'var(--sol-ink-700)',
        padding: '8px 0',
      }}
    >
      {children}
    </div>
  );
}
