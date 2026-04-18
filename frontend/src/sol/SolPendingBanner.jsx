/**
 * PROMEOS — SolPendingBanner
 *
 * Bannière en haut de la page cockpit affichant une action Sol
 * schedulée (grace period). Countdown live + CTA annuler / éditer.
 *
 * Maquette référence : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *   ".pending-banner" class, apparaît en remplacement du sol-hero après
 *   confirmation user.
 */
import { useEffect, useState } from 'react';

function formatRemaining(ms) {
  if (ms <= 0) return 'dans un instant';
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  if (h > 0) return `${h} h ${String(m).padStart(2, '0')} min`;
  return `${m} min`;
}

export default function SolPendingBanner({
  title,
  scheduledFor,           // ISO string ou Date
  onCancel,
  onEdit = null,
}) {
  const target = scheduledFor instanceof Date ? scheduledFor : new Date(scheduledFor);
  const [remainingMs, setRemainingMs] = useState(() => target.getTime() - Date.now());

  useEffect(() => {
    const tick = () => setRemainingMs(target.getTime() - Date.now());
    tick();
    const id = setInterval(tick, 60_000);
    return () => clearInterval(id);
  }, [target]);

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-calme-fg)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        borderRadius: '4px',
        padding: '12px 18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        marginBottom: '20px',
      }}
    >
      <div style={{ fontSize: '13.5px', color: 'var(--sol-ink-700)' }}>
        <strong style={{ color: 'var(--sol-ink-900)', fontWeight: 600 }}>{title}</strong>
        {' '}programmée — envoi dans{' '}
        <span
          style={{
            fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
            fontSize: '12px',
            color: 'var(--sol-calme-fg)',
            fontWeight: 600,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {formatRemaining(remainingMs)}
        </span>
        . Vous pouvez annuler jusque-là.
      </div>
      <div style={{ display: 'flex', gap: '8px' }}>
        {onEdit && (
          <button
            type="button"
            onClick={onEdit}
            style={{
              fontSize: '13px',
              padding: '6px 12px',
              background: 'transparent',
              color: 'var(--sol-ink-500)',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            Modifier
          </button>
        )}
        <button
          type="button"
          onClick={onCancel}
          style={{
            fontSize: '13px',
            padding: '6px 12px',
            background: 'var(--sol-bg-paper)',
            color: 'var(--sol-ink-900)',
            border: '1px solid var(--sol-rule)',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          Annuler
        </button>
      </div>
    </div>
  );
}
