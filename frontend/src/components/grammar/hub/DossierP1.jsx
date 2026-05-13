/**
 * grammar/hub/DossierP1 — Bloc dossier P1 cardinal de la Synthèse Stratégique.
 *
 * Composition complète (ADR-023 §3 dossier_p1) :
 *  - badge tier (P1) + category + question + recommendation
 *  - proof_pills (5 axes : gravité/impact/délai/confiance/réversibilité)
 *  - body_html (HTML court)
 *  - scenarios (3 cartes A/B/C, B canonique = recommended)
 *  - timeline (5 étapes décision/charges/audit/travaux/ROI)
 *  - proof_sidebar (CAPEX, gain, payback, CEE)
 *  - why_promeos (HTML court)
 *  - links (routes contextuelles)
 *
 * Display-only — provient de payload.dossier_p1.
 */

export default function DossierP1(props) {
  const {
    priority = 'P1',
    urgency_label,
    category,
    question,
    recommendation,
    proof_pills = [],
    body_html,
    scenarios = [],
    timeline = [],
    proof_sidebar = [],
    why_promeos,
    links = [],
  } = props;

  return (
    <section
      data-component="DossierP1"
      className="mb-5 rounded-lg border bg-white p-6"
      style={{
        background: 'var(--sol-bg-card, #FFFFFF)',
        borderColor: 'var(--sol-ink-200, #E5DDD0)',
        boxShadow: '0 1px 2px rgba(26,22,18,.04), 0 4px 12px rgba(26,22,18,.06)',
      }}
    >
      <header className="mb-3 flex items-start justify-between gap-4">
        <div>
          <span
            style={{
              fontFamily: 'var(--sol-font-mono, monospace)',
              fontSize: '10.5px',
              letterSpacing: '0.16em',
              color: 'var(--sol-ink-500, #7A6E5C)',
            }}
          >
            {category}
          </span>
          <h2
            style={{
              fontFamily: 'var(--sol-font-display, serif)',
              fontSize: '24px',
              lineHeight: 1.25,
              color: 'var(--sol-ink-900, #1A1612)',
              margin: '6px 0 8px',
            }}
          >
            {question}
          </h2>
          {recommendation && (
            <p
              style={{
                fontSize: '15px',
                color: 'var(--sol-ink-700, #3D362C)',
                lineHeight: 1.55,
                margin: '0 0 16px',
              }}
            >
              {recommendation}
            </p>
          )}
        </div>
        <span
          className="sol-dossier-tier"
          style={{
            fontFamily: 'var(--sol-font-mono, monospace)',
            fontSize: '11px',
            letterSpacing: '0.14em',
            padding: '4px 10px',
            background: 'var(--sol-refuse, #9C3F3F)',
            color: '#fff',
            borderRadius: '4px',
            whiteSpace: 'nowrap',
          }}
        >
          {priority}
        </span>
      </header>

      {/* Proof pills */}
      {proof_pills.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {proof_pills.map((pill, idx) => (
            <ProofPill key={`${pill.axis}-${idx}`} {...pill} />
          ))}
        </div>
      )}

      {/* Body court */}
      {body_html && (
        <div
          className="mb-4 sol-prose"
          style={{ fontSize: '14px', color: 'var(--sol-ink-700, #3D362C)', lineHeight: 1.55 }}
          dangerouslySetInnerHTML={{ __html: body_html }}
        />
      )}

      {/* Scenarios A/B/C */}
      {scenarios.length > 0 && (
        <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          {scenarios.map((s, idx) => (
            <ScenarioCard key={`${s.label}-${idx}`} {...s} />
          ))}
        </div>
      )}

      {/* Timeline */}
      {timeline.length > 0 && <Timeline steps={timeline} />}

      {/* Proof sidebar (4 valeurs) */}
      {proof_sidebar.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          {proof_sidebar.map((p, idx) => (
            <div
              key={`${p.label}-${idx}`}
              className="rounded-md border p-3"
              style={{
                background: 'var(--sol-bg-paper, #FAF7F2)',
                borderColor: 'var(--sol-ink-200, #E5DDD0)',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--sol-font-mono, monospace)',
                  fontSize: '10.5px',
                  letterSpacing: '0.10em',
                  color: 'var(--sol-ink-500, #7A6E5C)',
                  display: 'block',
                  marginBottom: '4px',
                }}
              >
                {p.label}
              </span>
              <span
                style={{
                  fontFamily: 'var(--sol-font-display, serif)',
                  fontSize: '20px',
                  color: 'var(--sol-ink-900, #1A1612)',
                }}
              >
                {p.value}
              </span>
              {p.detail && (
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--sol-ink-500, #7A6E5C)',
                    display: 'block',
                    marginTop: '2px',
                  }}
                >
                  {p.detail}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Why PROMEOS */}
      {why_promeos && (
        <div
          className="mt-4 sol-prose"
          style={{
            fontSize: '13px',
            color: 'var(--sol-ink-700, #3D362C)',
            lineHeight: 1.6,
            fontStyle: 'italic',
          }}
          dangerouslySetInnerHTML={{ __html: why_promeos }}
        />
      )}

      {/* Liens */}
      {links.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3" style={{ fontSize: '12.5px' }}>
          {links.map((l) => (
            <a
              key={l}
              href={l}
              style={{
                color: 'var(--sol-ink-700, #3D362C)',
                textDecoration: 'underline',
                textUnderlineOffset: '3px',
                fontWeight: 500,
              }}
            >
              {l}
            </a>
          ))}
        </div>
      )}
    </section>
  );
}

function ProofPill({ axis, tier = 'neutral', value }) {
  const styleMap = {
    refuse: { bg: 'var(--sol-bg-error-soft, #F4E0E0)', color: '#7A2C2C', border: '#D9A4A4' },
    warn: { bg: 'var(--sol-bg-warn-soft, #FBF1E0)', color: '#7B5320', border: '#E8C896' },
    ok: { bg: 'var(--sol-bg-success-soft, #E5F0E8)', color: '#2F5C44', border: '#A4D9B5' },
    neutral: {
      bg: 'var(--sol-bg-paper, #FAF7F2)',
      color: 'var(--sol-ink-700, #3D362C)',
      border: 'var(--sol-ink-200, #E5DDD0)',
    },
  };
  const s = styleMap[tier] || styleMap.neutral;
  return (
    <span
      style={{
        fontSize: '11.5px',
        padding: '5px 10px',
        borderRadius: '14px',
        border: `1px solid ${s.border}`,
        background: s.bg,
        color: s.color,
      }}
      data-axis={axis}
      data-tier={tier}
    >
      <strong style={{ textTransform: 'capitalize' }}>{axis}</strong> · {value}
    </span>
  );
}

function ScenarioCard({ label, title, figs = {}, recommended = false, verdict }) {
  const accent = recommended ? 'var(--sol-succes, #3F7C5A)' : 'var(--sol-ink-200, #E5DDD0)';
  const bg = recommended ? 'var(--sol-bg-success-soft, #EAF2EB)' : 'var(--sol-bg-paper, #FAF7F2)';
  return (
    <div
      className="rounded-md border p-4"
      style={{
        background: bg,
        borderColor: accent,
        borderWidth: recommended ? '2px' : '1px',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--sol-font-mono, monospace)',
          fontSize: '10.5px',
          letterSpacing: '0.14em',
          color: 'var(--sol-ink-500, #7A6E5C)',
          display: 'block',
        }}
      >
        {label}
      </span>
      <h4
        style={{
          fontFamily: 'var(--sol-font-display, serif)',
          fontSize: '14.5px',
          color: 'var(--sol-ink-900, #1A1612)',
          margin: '4px 0 8px',
        }}
      >
        {title}
      </h4>
      <ul
        style={{
          fontFamily: 'var(--sol-font-mono, monospace)',
          fontSize: '11.5px',
          color: 'var(--sol-ink-700, #3D362C)',
          lineHeight: 1.6,
          listStyle: 'none',
          padding: 0,
          margin: 0,
        }}
      >
        {Object.entries(figs).map(([k, v]) => (
          <li key={k}>
            <span style={{ color: 'var(--sol-ink-500, #7A6E5C)' }}>{k}</span> : <strong>{v}</strong>
          </li>
        ))}
      </ul>
      {verdict && (
        <p
          style={{
            fontSize: '11.5px',
            color: 'var(--sol-ink-700, #3D362C)',
            margin: '8px 0 0',
            fontStyle: 'italic',
          }}
        >
          {verdict}
        </p>
      )}
    </div>
  );
}

function Timeline({ steps }) {
  return (
    <div className="mt-2 flex items-start gap-0">
      {steps.map((step, idx) => {
        const isCurrent = step.status === 'current';
        const isFuture = step.status === 'future';
        return (
          <div
            key={`${step.step}-${idx}`}
            className="relative flex-1 text-center"
            style={{ minWidth: 0 }}
          >
            {idx < steps.length - 1 && (
              <div
                style={{
                  position: 'absolute',
                  top: '9px',
                  left: '50%',
                  right: '-50%',
                  height: '2px',
                  background: isCurrent
                    ? 'var(--sol-afaire, #B8612E)'
                    : 'var(--sol-ink-200, #E5DDD0)',
                }}
              />
            )}
            <div
              style={{
                width: '20px',
                height: '20px',
                borderRadius: '50%',
                margin: '0 auto',
                background: isCurrent
                  ? 'var(--sol-afaire, #B8612E)'
                  : isFuture
                    ? '#fff'
                    : 'var(--sol-ink-200, #E5DDD0)',
                border: isFuture ? '2px solid var(--sol-ink-300, #CFC4B2)' : 'none',
                boxShadow: isCurrent ? '0 0 0 4px var(--sol-bg-warn-soft, #FBF1E0)' : 'none',
                position: 'relative',
                zIndex: 1,
              }}
            />
            <span
              style={{
                fontSize: '11.5px',
                fontWeight: 500,
                color: 'var(--sol-ink-700, #3D362C)',
                display: 'block',
                marginTop: '6px',
              }}
            >
              {step.name}
            </span>
            <span
              style={{
                fontFamily: 'var(--sol-font-mono, monospace)',
                fontSize: '10.5px',
                color: 'var(--sol-ink-500, #7A6E5C)',
                display: 'block',
                marginTop: '2px',
              }}
            >
              {step.date}
            </span>
          </div>
        );
      })}
    </div>
  );
}
