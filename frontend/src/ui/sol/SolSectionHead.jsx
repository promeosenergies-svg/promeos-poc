/**
 * PROMEOS — SolSectionHead
 *
 * En-tête de section Sol : title Fraunces 22px + meta mono uppercase droite
 * + border-bottom subtle.
 *
 * Source maquette : .section-head / .section-title / .section-meta
 */

export default function SolSectionHead({ title, meta }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        justifyContent: 'space-between',
        margin: '18px 0 10px 0',
        paddingBottom: 8,
        borderBottom: '1px solid var(--sol-rule)',
        gap: 16,
        flexWrap: 'wrap',
      }}
    >
      <h2
        style={{
          fontFamily: 'var(--sol-font-body)',
          fontSize: 15,
          fontWeight: 600,
          color: 'var(--sol-ink-900)',
          letterSpacing: '-0.005em',
          margin: 0,
        }}
      >
        {title}
      </h2>
      {meta && (
        <span
          style={{
            fontFamily: 'var(--sol-font-mono)',
            fontSize: 10,
            color: 'var(--sol-ink-500)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          {meta}
        </span>
      )}
    </div>
  );
}
