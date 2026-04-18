/**
 * PROMEOS — SolSubline
 * Sous-phrase Sol : 13.5px, ink-500, line-height 1.55.
 * Complément contextuel de SolHeadline.
 */
import React from 'react';

export default function SolSubline({ children, maxWidth = 680, className = '' }) {
  return (
    <p
      className={`sol-subline ${className}`.trim()}
      style={{
        fontSize: 13,
        color: 'var(--sol-ink-500)',
        lineHeight: 1.55,
        maxWidth,
        margin: 0,
      }}
    >
      {children}
    </p>
  );
}
