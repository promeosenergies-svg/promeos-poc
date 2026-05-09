/**
 * grammar/DecisionEvidenceCard — Carte decision avec evidence grille 4-8 cellules.
 *
 * Primitif NOUVEAU extrait du pattern visuel de `/cockpit/strategique`.
 * Represente une decision prioritaire avec rang, categorie, scope, severity,
 * lead narrative et grille evidence sourcee.
 *
 * Doctrine §5.6 : 4 a 8 cellules evidence obligatoires (loi L9).
 * Validation runtime : throw si evidence.length hors [4, 8].
 *
 * Tonalite severity (calme par defaut — "le produit murmure la decision juste") :
 *   - 'critical' : var(--sol-refuse-*)  — utilise parcimonieusement
 *   - 'warning'  : var(--sol-attention-*)
 *   - 'positive' : var(--sol-succes-*)
 *   - 'neutral'  : var(--sol-ink-*) (defaut)
 *
 * Display-only — zero calcul metier.
 *
 * @param {Object} props
 * @param {number} props.rang - Priorite 1, 2, 3 (rendu font-mono)
 * @param {'CONFORMITE'|'INVESTISSEMENT'|'ACHAT'|'PERFORMANCE'|'ANOMALIE'} props.category
 * @param {string} props.scope - Perimetre ex. "SIEGE HELIOS PARIS"
 * @param {'critical'|'warning'|'positive'|'neutral'} [props.severity='neutral']
 * @param {React.ReactNode} props.titre - Titre de la decision
 * @param {string} props.lead - Phrase lead 1-2 lignes max
 * @param {Array<{label:string, value:string|number, unit?:string, helper?:string}>} props.evidence - 4 a 8 cellules
 * @param {{label:string, href:string}} [props.primaryCta] - CTA principal
 * @param {string} [props.methodologyRef] - URL methodologie
 * @param {string} [props.className=''] - Classes CSS supplementaires
 */
import { ExternalLink } from 'lucide-react';

const SEVERITY_STYLES = Object.freeze({
  critical: {
    borderColor: 'var(--sol-refuse-line)',
    headerBg: 'var(--sol-refuse-bg)',
    categoryFg: 'var(--sol-refuse-fg)',
    rangeFg: 'var(--sol-refuse-fg)',
  },
  warning: {
    borderColor: 'var(--sol-attention-line)',
    headerBg: 'var(--sol-attention-bg)',
    categoryFg: 'var(--sol-attention-fg)',
    rangeFg: 'var(--sol-attention-fg)',
  },
  positive: {
    borderColor: 'var(--sol-succes-line)',
    headerBg: 'var(--sol-succes-bg)',
    categoryFg: 'var(--sol-succes-fg)',
    rangeFg: 'var(--sol-succes-fg)',
  },
  neutral: {
    borderColor: 'var(--sol-line)',
    headerBg: 'var(--sol-bg-canvas)',
    categoryFg: 'var(--sol-ink-500)',
    rangeFg: 'var(--sol-ink-900)',
  },
});

/**
 * Valide les evidence (doctrine §5.6 loi L9).
 * @throws {Error} si evidence.length hors [4, 8]
 */
function validateEvidence(evidence) {
  if (!Array.isArray(evidence) || evidence.length < 4 || evidence.length > 8) {
    throw new Error(
      `DecisionEvidenceCard: 4-8 cellules evidence (Loi L9 doctrine §5.6) — recu ${Array.isArray(evidence) ? evidence.length : typeof evidence}`
    );
  }
}

export default function DecisionEvidenceCard({
  rang,
  category,
  scope,
  severity = 'neutral',
  titre,
  lead,
  evidence,
  primaryCta,
  methodologyRef,
  className = '',
}) {
  validateEvidence(evidence);

  const styles = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.neutral;
  // Audit code-reviewer Phase 1.6 : ternaire désormais effective —
  // 5-8 cellules basculent en grille 3-4 colonnes pour préserver la lisibilité
  const gridCols =
    evidence.length <= 4
      ? 'grid-cols-2 sm:grid-cols-4'
      : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4';

  return (
    <article
      data-testid="decision-evidence-card"
      data-severity={severity}
      data-rang={rang}
      className={`rounded-xl border overflow-hidden sol-card ${className}`}
      style={{ borderColor: styles.borderColor }}
    >
      {/* Header — rang + category + scope */}
      <header
        className="flex items-center justify-between gap-3 px-5 py-3"
        style={{ background: styles.headerBg }}
      >
        <div className="flex items-center gap-3 min-w-0">
          {rang != null && (
            <span
              data-testid="decision-evidence-rang"
              className="font-mono text-sm font-bold tabular-nums shrink-0"
              style={{ color: styles.rangeFg }}
            >
              #{rang}
            </span>
          )}
          {category && (
            <span
              data-testid="decision-evidence-category"
              className="font-mono text-[10px] uppercase tracking-[0.1em] font-semibold"
              style={{ color: styles.categoryFg }}
            >
              {category}
            </span>
          )}
          {scope && (
            <span
              className="font-mono text-[10px] uppercase tracking-wider truncate"
              style={{ color: 'var(--sol-ink-500)' }}
            >
              {scope}
            </span>
          )}
        </div>
        <span
          data-testid="decision-evidence-severity"
          className="font-mono text-[9px] uppercase tracking-[0.12em] shrink-0 px-1.5 py-0.5 rounded"
          style={{
            background: styles.borderColor,
            color: styles.categoryFg,
          }}
        >
          {severity}
        </span>
      </header>

      {/* Titre + lead */}
      <div className="px-5 pt-4 pb-3">
        {titre && (
          <h3
            data-testid="decision-evidence-titre"
            className="text-base font-semibold leading-snug mb-1"
            style={{
              fontFamily: 'var(--sol-font-display)',
              color: 'var(--sol-ink-900)',
            }}
          >
            {titre}
          </h3>
        )}
        {lead && (
          <p
            data-testid="decision-evidence-lead"
            className="text-sm leading-relaxed max-w-prose"
            style={{ color: 'var(--sol-ink-700)' }}
          >
            {lead}
          </p>
        )}
      </div>

      {/* Grille evidence */}
      <div
        data-testid="decision-evidence-grid"
        className={`grid ${gridCols} gap-0 border-t`}
        style={{ borderColor: styles.borderColor }}
      >
        {evidence.map((cell, idx) => (
          <div
            key={cell.label || idx}
            data-testid={`evidence-cell-${idx}`}
            className="flex flex-col gap-1 px-4 py-3 border-r last:border-r-0"
            style={{ borderColor: styles.borderColor }}
          >
            <span
              className="font-mono text-[9px] uppercase tracking-[0.1em] leading-none"
              style={{ color: 'var(--sol-ink-400)' }}
            >
              {cell.label}
            </span>
            <div className="flex items-baseline gap-1">
              <span
                className="tabular-nums font-semibold"
                style={{
                  fontFamily: 'var(--sol-font-display)',
                  fontSize: 20,
                  lineHeight: 1,
                  color: 'var(--sol-ink-900)',
                }}
              >
                {cell.value}
              </span>
              {cell.unit && (
                <span className="text-xs" style={{ color: 'var(--sol-ink-500)' }}>
                  {cell.unit}
                </span>
              )}
            </div>
            {cell.helper && (
              <span className="text-[10px] leading-tight" style={{ color: 'var(--sol-ink-500)' }}>
                {cell.helper}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Footer — methodologie + CTA */}
      {(methodologyRef || primaryCta) && (
        <footer
          className="flex items-center justify-between gap-3 px-5 py-3 border-t"
          style={{ borderColor: styles.borderColor }}
        >
          {methodologyRef && (
            <a
              data-testid="decision-evidence-methodology"
              href={methodologyRef}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] font-mono uppercase tracking-wider hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded"
              style={{ color: 'var(--sol-ink-500)' }}
            >
              Methodologie
              <ExternalLink size={10} aria-hidden="true" />
            </a>
          )}
          {primaryCta && (
            <a
              data-testid="decision-evidence-cta"
              href={primaryCta.href}
              className="inline-flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
              style={{
                background: 'var(--sol-calme-fg)',
                color: 'var(--sol-bg-paper)',
              }}
            >
              {primaryCta.label}
            </a>
          )}
        </footer>
      )}
    </article>
  );
}
