/**
 * grammar/hub/VerdictFinal — Bloc « Votre contrainte / opportunité principale ».
 *
 * Affiche deux cartes côte à côte : la contrainte cardinale (rouge/orange)
 * et l'opportunité cardinale (vert/sol-succes).
 *
 * Props :
 *   constraint   — { label, statement, detail }
 *   opportunity  — { label, statement, detail }
 *
 * Display-only — provient de payload.verdict (backend builder).
 */

export default function VerdictFinal({ constraint, opportunity }) {
  if (!constraint || !opportunity) return null;
  return (
    <section data-component="VerdictFinal" className="mb-5 grid grid-cols-1 gap-3 md:grid-cols-2">
      <VerdictCard variant="constraint" {...constraint} />
      <VerdictCard variant="opportunity" {...opportunity} />
    </section>
  );
}

function VerdictCard({ variant, label, statement, detail }) {
  const accent =
    variant === 'constraint' ? 'var(--sol-afaire, #B8612E)' : 'var(--sol-succes, #3F7C5A)';
  return (
    <article
      className="sol-verdict-card rounded-md border bg-white p-5"
      style={{
        background: 'var(--sol-bg-card, #FFFFFF)',
        borderColor: 'var(--sol-ink-200, #E5DDD0)',
        borderLeftWidth: '4px',
        borderLeftColor: accent,
      }}
      data-variant={variant}
    >
      <header
        style={{
          fontFamily: 'var(--sol-font-mono, monospace)',
          fontSize: '10.5px',
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--sol-ink-500, #7A6E5C)',
          marginBottom: '6px',
        }}
      >
        {label}
      </header>
      <p
        style={{
          fontFamily: 'var(--sol-font-display, serif)',
          fontSize: '18px',
          color: 'var(--sol-ink-900, #1A1612)',
          lineHeight: 1.35,
          margin: '0 0 8px',
        }}
      >
        {statement}
      </p>
      <p
        style={{
          fontSize: '13.5px',
          color: 'var(--sol-ink-700, #3D362C)',
          lineHeight: 1.55,
          margin: 0,
        }}
      >
        {detail}
      </p>
    </article>
  );
}
