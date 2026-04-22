/**
 * PROMEOS — SolLayerToggle
 * Segmented control Surface/Inspect/Expert. Controlled : value + onChange.
 *
 * Accessibilité : role="group" + aria-pressed sur chaque bouton (pattern
 * existant sur Achat cockpit card, PR #246).
 */
import React from 'react';

const DEFAULT_MODES = [
  { value: 'surface', label: 'Surface' },
  { value: 'inspect', label: 'Inspect' },
  { value: 'expert', label: 'Expert' },
];

export default function SolLayerToggle({
  value = 'surface',
  onChange,
  modes = DEFAULT_MODES,
  className = '',
}) {
  return (
    <div
      role="group"
      aria-label="Mode d'affichage"
      className={`sol-layer-toggle ${className}`.trim()}
      style={{
        display: 'inline-flex',
        background: 'var(--sol-bg-panel)',
        border: '1px solid var(--sol-rule)',
        borderRadius: 4,
        padding: 2,
      }}
    >
      {modes.map((m) => {
        const isActive = m.value === value;
        return (
          <button
            key={m.value}
            type="button"
            aria-pressed={isActive}
            onClick={() => onChange?.(m.value)}
            className={`sol-layer-btn ${isActive ? 'is-active' : ''}`.trim()}
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 10.5,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontWeight: 600,
              color: isActive ? 'var(--sol-ink-900)' : 'var(--sol-ink-500)',
              background: isActive ? 'var(--sol-bg-paper)' : 'transparent',
              padding: '5px 12px',
              borderRadius: 3,
              border: 'none',
              cursor: 'pointer',
              boxShadow: isActive ? '0 1px 2px rgba(15, 23, 42, 0.06)' : 'none',
            }}
          >
            {m.label}
          </button>
        );
      })}
    </div>
  );
}
