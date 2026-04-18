/**
 * PROMEOS — SolSourceChip
 *
 * Chip de provenance mono 9.5px uppercase avec dot coloré selon kind.
 * Source maquette : .source-chip pattern (src-enedis, src-facture, src-estime).
 */

const KIND_COLOR = {
  enedis: 'var(--sol-calme-fg)',
  factures: 'var(--sol-calme-fg)',
  'enedis + grdf': 'var(--sol-calme-fg)',
  calcul: 'var(--sol-ink-500)',
  estime: 'var(--sol-attention-fg)',
  grdf: 'var(--sol-calme-fg)',
};

export default function SolSourceChip({ kind, ref: refLabel, freshness }) {
  const dotColor = KIND_COLOR[(kind || '').toLowerCase()] || 'var(--sol-calme-fg)';
  const parts = ['Source'];
  if (kind) parts.push(kind);
  if (refLabel) parts.push(refLabel);
  if (freshness) parts.push(freshness);

  return (
    <span
      className="sol-source-chip"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontFamily: 'var(--sol-font-mono)',
        fontSize: 9.5,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: 'var(--sol-ink-500)',
        border: '1px solid var(--sol-rule)',
        borderRadius: 2,
        padding: '2px 6px',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: dotColor,
          display: 'inline-block',
        }}
      />
      {parts.join(' · ')}
    </span>
  );
}
