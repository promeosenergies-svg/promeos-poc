/**
 * PROMEOS — SolDrawer
 * Wrapper stylé du Drawer V1 existant (ui/Drawer) : style maquette Sol.
 * Si ui/Drawer n'est pas dispo dans le scope, fallback simple <aside fixed>.
 */
import React from 'react';

export default function SolDrawer({ open, onClose, title, children, width = 480, className = '' }) {
  if (!open) return null;
  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.32)',
          zIndex: 60,
        }}
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title || 'Panneau latéral'}
        className={`sol-drawer ${className}`.trim()}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width,
          maxWidth: '100vw',
          background: 'var(--sol-bg-paper)',
          borderLeft: '1px solid var(--sol-rule)',
          zIndex: 61,
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-8px 0 24px rgba(15, 23, 42, 0.08)',
        }}
      >
        {title && (
          <header
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '18px 24px',
              borderBottom: '1px solid var(--sol-rule)',
            }}
          >
            <h2
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 18,
                fontWeight: 500,
                color: 'var(--sol-ink-900)',
                margin: 0,
                letterSpacing: '-0.015em',
              }}
            >
              {title}
            </h2>
            <button
              type="button"
              onClick={onClose}
              aria-label="Fermer"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--sol-ink-500)',
                cursor: 'pointer',
                fontFamily: 'var(--sol-font-mono)',
                fontSize: 14,
              }}
            >
              ×
            </button>
          </header>
        )}
        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 24px' }}>{children}</div>
      </aside>
    </>
  );
}
