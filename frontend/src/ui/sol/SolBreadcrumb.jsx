/**
 * PROMEOS — SolBreadcrumb (Pattern C Lot 3)
 *
 * Fil d'Ariane mono uppercase : segments cliquables avec séparateurs « › ».
 * Le dernier segment est rendu en ink-900 non cliquable (position actuelle).
 * `backTo` optionnel affiche un bouton « ‹ Retour » à gauche du fil.
 *
 * Props :
 *   - segments: Array<{ label: string, to?: string }>  — ordre Org › … › Actuel
 *   - backTo?:  string                                  — route du bouton retour
 *   - backLabel?: string                                — label custom (défaut "Retour")
 */
import React from 'react';
import { Link } from 'react-router-dom';

const KICKER_STYLE = {
  fontFamily: 'var(--sol-font-mono)',
  fontSize: 10.5,
  letterSpacing: '0.14em',
  textTransform: 'uppercase',
  color: 'var(--sol-ink-500)',
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  margin: 0,
  padding: 0,
};

export default function SolBreadcrumb({ segments = [], backTo, backLabel = 'Retour' }) {
  if (!Array.isArray(segments) || segments.length === 0) {
    if (!backTo) return null;
  }

  return (
    <nav aria-label="Fil d'Ariane" style={KICKER_STYLE}>
      {backTo && (
        <Link
          to={backTo}
          style={{
            color: 'var(--sol-ink-700)',
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            paddingRight: 10,
            marginRight: 4,
            borderRight: '1px solid var(--sol-ink-200)',
          }}
        >
          <span aria-hidden="true">‹</span>
          <span>{backLabel}</span>
        </Link>
      )}
      {segments.map((seg, idx) => {
        const isLast = idx === segments.length - 1;
        const separator =
          idx > 0 ? (
            <span key={`sep-${idx}`} aria-hidden="true" style={{ color: 'var(--sol-ink-300)' }}>
              ›
            </span>
          ) : null;
        const content =
          !isLast && seg.to ? (
            <Link
              key={`seg-${idx}`}
              to={seg.to}
              style={{ color: 'var(--sol-ink-500)', textDecoration: 'none' }}
            >
              {seg.label}
            </Link>
          ) : (
            <span
              key={`seg-${idx}`}
              style={{ color: isLast ? 'var(--sol-ink-900)' : 'var(--sol-ink-500)' }}
              aria-current={isLast ? 'page' : undefined}
            >
              {seg.label}
            </span>
          );
        return [separator, content].filter(Boolean);
      })}
    </nav>
  );
}
