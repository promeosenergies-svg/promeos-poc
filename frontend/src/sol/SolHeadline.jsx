/**
 * PROMEOS — SolHeadline
 *
 * Phrase humaine courte au-dessus d'un KPI ou chart. Voix Sol :
 * vouvoiement, chiffre d'abord, toujours une issue.
 *
 * Maquette référence : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *   ".sol-headline" class dans la section cockpit main.
 */

export default function SolHeadline({ text, subline = '' }) {
  return (
    <div>
      <p
        style={{
          fontSize: '16px',
          fontWeight: 500,
          color: 'var(--sol-ink-700)',
          lineHeight: 1.4,
          letterSpacing: '-0.01em',
          margin: '0 0 8px 0',
          maxWidth: '680px',
        }}
      >
        {text}
      </p>
      {subline && (
        <p
          style={{
            fontSize: '13px',
            color: 'var(--sol-ink-500)',
            lineHeight: 1.55,
            margin: 0,
            maxWidth: '680px',
          }}
        >
          {subline}
        </p>
      )}
    </div>
  );
}
