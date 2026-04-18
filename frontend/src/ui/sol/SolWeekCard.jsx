/**
 * PROMEOS — SolWeekCard
 *
 * Card catégorielle "Cette semaine chez vous" : tag attention/afaire/succes
 * + title Fraunces + body DM Sans + footer dashed border mono.
 *
 * Source maquette : .week-card / .week-card-tag / .week-card-title /
 *                   .week-card-body / .week-card-footer
 */

const TAG_STYLE = {
  attention: { bg: 'var(--sol-attention-bg)', fg: 'var(--sol-attention-fg)' },
  afaire: { bg: 'var(--sol-afaire-bg)', fg: 'var(--sol-afaire-fg)' },
  succes: { bg: 'var(--sol-succes-bg)', fg: 'var(--sol-succes-fg)' },
};

export default function SolWeekCard({
  tagKind = 'attention',
  tagLabel,
  title,
  body,
  footerLeft,
  footerRight,
  onClick,
}) {
  const style = TAG_STYLE[tagKind] || TAG_STYLE.attention;

  return (
    <div
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick(e); } } : undefined}
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-rule)',
        borderRadius: 3,
        padding: '18px 20px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 120ms ease',
        position: 'relative',
      }}
      onMouseEnter={onClick ? (e) => (e.currentTarget.style.borderColor = 'var(--sol-ink-500)') : undefined}
      onMouseLeave={onClick ? (e) => (e.currentTarget.style.borderColor = 'var(--sol-rule)') : undefined}
    >
      <div
        style={{
          display: 'inline-block',
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 9.5,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          fontWeight: 600,
          padding: '2px 6px',
          borderRadius: 2,
          marginBottom: 12,
          background: style.bg,
          color: style.fg,
        }}
      >
        {tagLabel}
      </div>

      <h4
        style={{
          fontFamily: 'var(--sol-font-display)',
          fontSize: 16,
          fontWeight: 500,
          color: 'var(--sol-ink-900)',
          marginBottom: 6,
          lineHeight: 1.3,
          margin: 0,
        }}
      >
        {title}
      </h4>

      {body && (
        <div
          style={{
            fontSize: 13,
            color: 'var(--sol-ink-500)',
            lineHeight: 1.5,
            marginTop: 6,
          }}
        >
          {body}
        </div>
      )}

      {(footerLeft || footerRight) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: 14,
            paddingTop: 12,
            borderTop: '1px dashed var(--sol-ink-200)',
            fontSize: 11,
            color: 'var(--sol-ink-500)',
            fontFamily: 'var(--sol-font-mono)',
          }}
        >
          <span>{footerLeft}</span>
          <span>{footerRight}</span>
        </div>
      )}
    </div>
  );
}
