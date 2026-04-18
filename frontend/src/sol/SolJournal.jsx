/**
 * PROMEOS — SolJournal
 *
 * Table append-only du trail d'audit Sol, 4 colonnes :
 *   Date · heure | Action (phase + intent) | Détail (correlation_id + outcome) | Statut
 *
 * Statut coloré selon phase :
 *   proposed/previewed/scheduled → attention (ambre)
 *   executed → succes (vert)
 *   cancelled/refused → afaire/refuse
 */

const PHASE_LABEL_FR = {
  proposed: 'proposée',
  previewed: 'prévisualisée',
  confirmed: 'confirmée',
  scheduled: 'programmée',
  executed: 'exécutée',
  cancelled: 'annulée',
  reverted: 'révertée',
  refused: 'refusée',
};

const PHASE_COLOR = {
  proposed: 'var(--sol-attention-fg)',
  previewed: 'var(--sol-attention-fg)',
  confirmed: 'var(--sol-attention-fg)',
  scheduled: 'var(--sol-attention-fg)',
  executed: 'var(--sol-succes-fg)',
  cancelled: 'var(--sol-ink-500)',
  reverted: 'var(--sol-afaire-fg)',
  refused: 'var(--sol-refuse-fg)',
};

function formatDateFr(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function SolJournal({ items = [], emptyLabel = 'Aucune action agentique enregistrée.' }) {
  if (!items.length) {
    return (
      <div
        style={{
          padding: '24px',
          background: 'var(--sol-bg-panel)',
          borderRadius: '4px',
          fontSize: '13px',
          color: 'var(--sol-ink-500)',
          textAlign: 'center',
        }}
      >
        {emptyLabel}
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-rule)',
        borderRadius: '4px',
        padding: '12px 18px',
        fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
        fontSize: '12px',
      }}
    >
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '130px 150px 1fr 120px',
          gap: '14px',
          paddingBottom: '10px',
          borderBottom: '1px solid var(--sol-rule)',
          color: 'var(--sol-ink-500)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          fontSize: '10px',
          fontWeight: 600,
        }}
      >
        <span>Date · heure</span>
        <span>Action</span>
        <span>Détail</span>
        <span style={{ textAlign: 'right' }}>Statut</span>
      </div>
      {items.map((item) => (
        <div
          key={item.id}
          style={{
            display: 'grid',
            gridTemplateColumns: '130px 150px 1fr 120px',
            gap: '14px',
            padding: '8px 0',
            borderBottom: '1px dashed var(--sol-ink-200)',
            alignItems: 'baseline',
            fontSize: '11.5px',
            color: 'var(--sol-ink-700)',
          }}
        >
          <span style={{ color: 'var(--sol-ink-500)' }}>{formatDateFr(item.created_at)}</span>
          <span style={{ color: 'var(--sol-ink-900)' }}>
            {PHASE_LABEL_FR[item.action_phase] || item.action_phase}{' '}
            <span style={{ color: 'var(--sol-ink-500)', fontWeight: 400 }}>· {item.intent_kind}</span>
          </span>
          <span>
            <code style={{ fontSize: '10.5px', color: 'var(--sol-ink-500)' }}>
              {item.correlation_id.slice(0, 12)}…
            </code>
            {item.outcome_message && (
              <span style={{ marginLeft: '8px', color: 'var(--sol-ink-700)' }}>
                {item.outcome_message}
              </span>
            )}
          </span>
          <span
            style={{
              textAlign: 'right',
              fontWeight: 600,
              color: PHASE_COLOR[item.action_phase] || 'var(--sol-ink-500)',
            }}
          >
            {PHASE_LABEL_FR[item.action_phase] || item.action_phase}
          </span>
        </div>
      ))}
    </div>
  );
}
