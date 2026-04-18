/**
 * PROMEOS — SolHeadline
 * Phrase narrative Sol : Fraunces 18/1.35, ink-700, italic em possible.
 * Présentation pure. Reçoit le texte déjà composé par un presenter.
 */
import React from 'react';

export default function SolHeadline({ children, as: Tag = 'p', maxWidth = 680, className = '' }) {
  return (
    <Tag
      className={`sol-headline ${className}`.trim()}
      style={{
        fontFamily: 'var(--sol-font-body)',
        fontWeight: 500,
        fontSize: 16,
        lineHeight: 1.4,
        letterSpacing: '-0.015em',
        color: 'var(--sol-ink-700)',
        maxWidth,
        margin: '0 0 8px 0',
      }}
    >
      {children}
    </Tag>
  );
}
