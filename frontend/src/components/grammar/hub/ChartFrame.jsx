/**
 * grammar/hub/ChartFrame — Wrapper question/reponse pour zone chart.
 *
 * Composant enveloppe L11 Hub Page (doctrine §12 Loi L11.4).
 * Pose la question metier en Fraunces, la reponse narrative en prose,
 * accueille le chart enfant dans une zone min-height 165px, et affiche
 * le footer SCM (Source · Confiance · Mis a jour).
 *
 * Display-only — zero calcul metier.
 * Le chart enfant (SVG, Recharts, canvas) est fourni par la page parente.
 *
 * @param {Object} props
 * @param {string} props.question - Question metier (Fraunces 16px)
 * @param {React.ReactNode} props.answer - Reponse narrative (peut contenir <b>)
 * @param {{ source: string, confidence: string, updatedAt: string }} props.source
 * @param {React.ReactNode} props.children - Zone chart (SVG/Recharts/canvas)
 * @param {string} [props.className='']
 */
export default function ChartFrame({ question, answer, source = {}, children, className = '' }) {
  const { source: sourceName, confidence, updatedAt } = source;

  return (
    <div
      data-component="ChartFrame"
      className={`rounded-xl border p-4 ${className}`}
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      {/* Question — display Fraunces */}
      {question && (
        <h3
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: '16px',
            fontWeight: 500,
            lineHeight: 1.3,
            color: 'var(--sol-ink-900)',
            margin: '0 0 4px 0',
          }}
        >
          {question}
        </h3>
      )}

      {/* Reponse narrative */}
      {answer && (
        <p
          className="chart-frame-answer"
          style={{
            fontSize: '12.5px',
            color: 'var(--sol-ink-500)',
            lineHeight: 1.45,
            margin: '0 0 16px 0',
          }}
        >
          {answer}
        </p>
      )}

      {/* Zone chart enfant */}
      <div style={{ minHeight: '165px' }}>{children}</div>

      {/* Footer SCM */}
      {(sourceName || confidence || updatedAt) && (
        <div
          className="font-mono"
          style={{
            fontSize: '10px',
            color: 'var(--sol-ink-400)',
            borderTop: '1px solid var(--sol-rule)',
            paddingTop: '8px',
            marginTop: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '4px',
          }}
        >
          <span>{sourceName}</span>
          <span>
            {updatedAt && `MAJ ${updatedAt}`}
            {updatedAt && confidence && ' · '}
            {confidence && `Confiance ${confidence}`}
          </span>
        </div>
      )}
    </div>
  );
}
