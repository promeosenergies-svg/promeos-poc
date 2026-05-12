/**
 * grammar/hub/HubHighlight — Ligne action-card compacte L11 Hub Page.
 *
 * Composant de priorite PROMEOS (doctrine §12 Loi L11.3).
 * Grille 4 colonnes : rang | corps (meta + titre + evidence) | impact | CTA.
 * Bordure latérale gauche coloree par severity.
 *
 * Validation runtime DEV :
 *   - invitation.verb doit etre dans la liste blanche L11.3 (12 verbes)
 *   Console.error si violation — ne throw pas (rendu se fait avec avertissement).
 *
 * Severity tokens :
 *   crit → sol-refuse-line  (rouge terre cuite)
 *   warn → sol-attention-line (ambre)
 *   pos  → sol-succes-line  (vert foret)
 *   info → sol-ink-400      (gris)
 *
 * Source-guards :
 *   data-component="HubHighlight" data-severity={severity} data-rang={rang}
 *   data-invitation={invitation.verb}
 *
 * Display-only — zero calcul metier.
 *
 * @param {Object} props
 * @param {number} props.rang - Priorite 1, 2, 3 (rendu "P{rang}")
 * @param {'crit'|'warn'|'pos'|'info'} props.severity
 * @param {string} props.category - Ex. "Conformite"
 * @param {string} props.scope - Ex. "Bureau Regional Lyon"
 * @param {string} props.title - Titre de la priorite
 * @param {React.ReactNode} props.evidence - Texte evidence (peut contenir <b>)
 * @param {{ value: string, label: string }} [props.impact] - Impact chiffre
 * @param {{ verb: string, object: string, href: string }} props.invitation - CTA
 * @param {{ score_total: number, score_breakdown: object, tier: string }} [props.priorityProof] -
 *   Phase F.24 : badge transparent doctrinal ADR-022. Affiche la
 *   décomposition du score de priorisation (5 dimensions) sous l'evidence.
 *   Si omis, le badge n'est pas rendu (rétro-compat).
 * @param {string} [props.className='']
 */

/** Liste blanche des verbes d'invitation L11.3 (doctrine §12) */
const INVITATION_VERBS = [
  'voir',
  'lancer',
  'comparer',
  'auditer',
  'ouvrir',
  'vérifier',
  'simuler',
  'arbitrer',
  'programmer',
  'activer',
  'préparer',
  'contester',
];

/** Tokens CSS de bordure par severity */
const SEVERITY_BORDER = Object.freeze({
  crit: 'var(--sol-refuse-line)',
  warn: 'var(--sol-attention-line)',
  pos: 'var(--sol-succes-line)',
  info: 'var(--sol-ink-400)',
});

/**
 * Capitalise la premiere lettre d'une chaine.
 * @param {string} str
 * @returns {string}
 */
function capitalize(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/** Libellés FR pour les dimensions du score doctrinal (ADR-022). */
const PROOF_DIMENSION_LABELS = Object.freeze({
  severity: 'Sévérité',
  impact: 'Impact €',
  urgency: 'Urgence',
  scope: 'Scope',
  domain: 'Domaine',
});

export default function HubHighlight({
  rang,
  severity = 'info',
  category,
  scope,
  title,
  evidence,
  impact,
  invitation,
  priorityProof,
  className = '',
}) {
  /* Validation runtime DEV */
  if (process.env.NODE_ENV !== 'production') {
    if (invitation?.verb && !INVITATION_VERBS.includes(invitation.verb)) {
      // eslint-disable-next-line no-console
      console.error(
        `[HubHighlight] Loi L11.3 : verbe d'invitation "${invitation.verb}" invalide. ` +
          `Verbes autorises : ${INVITATION_VERBS.join(' | ')}. PROMEOS doctrine §12.`
      );
    }
  }

  const borderColor = SEVERITY_BORDER[severity] ?? SEVERITY_BORDER.info;

  return (
    <div
      data-component="HubHighlight"
      data-severity={severity}
      data-rang={rang}
      data-invitation={invitation?.verb}
      className={`relative grid items-center rounded-xl border ${className}`}
      style={{
        gridTemplateColumns: '36px 1fr auto auto',
        gap: '16px',
        padding: '14px 18px',
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      {/* Bordure laterale gauche — severity coloree */}
      <span
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: 0,
          top: '3px',
          bottom: '3px',
          width: '3px',
          borderRadius: '0 2px 2px 0',
          background: borderColor,
        }}
      />

      {/* Rang — badge mono P{n} */}
      <div
        className="font-mono text-center"
        style={{
          fontSize: '10.5px',
          fontWeight: 500,
          background: 'var(--sol-bg-canvas)',
          border: '1px solid var(--sol-rule)',
          borderRadius: '7px',
          padding: '5px 0',
          width: '36px',
          color: 'var(--sol-ink-500)',
        }}
      >
        P{rang}
      </div>

      {/* Corps : meta + titre + evidence */}
      <div style={{ minWidth: 0 }}>
        {/* Meta : category · scope */}
        {(category || scope) && (
          <div
            className="font-mono uppercase"
            style={{
              fontSize: '10px',
              letterSpacing: '0.1em',
              color: 'var(--sol-ink-400)',
              marginBottom: '4px',
            }}
          >
            {category}
            {category && scope && <span style={{ margin: '0 4px' }}>·</span>}
            {scope}
          </div>
        )}

        {/* Titre — Fraunces display */}
        {title && (
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: '16.5px',
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
              lineHeight: 1.3,
              marginBottom: '3px',
            }}
          >
            {title}
          </div>
        )}

        {/* Evidence */}
        {evidence && (
          <div
            style={{
              fontSize: '12px',
              color: 'var(--sol-ink-500)',
              lineHeight: 1.45,
            }}
          >
            {evidence}
          </div>
        )}

        {/* PriorityProof badge — Phase F.24 ADR-022 §Transparence.
            Décomposition du score de priorisation 5 dimensions visible
            sous l'evidence. Différentiant PROMEOS : "Vous savez toujours
            pourquoi PROMEOS dit que c'est important." */}
        {priorityProof && priorityProof.score_breakdown && (
          <div
            data-component="PriorityProof"
            data-score={priorityProof.score_total}
            className="font-mono"
            style={{
              marginTop: '8px',
              paddingTop: '6px',
              borderTop: '1px dashed var(--sol-rule)',
              fontSize: '10px',
              color: 'var(--sol-ink-400)',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '10px',
              alignItems: 'center',
            }}
          >
            <span
              style={{
                fontWeight: 600,
                color: 'var(--sol-ink-700)',
                background: 'var(--sol-bg-canvas)',
                padding: '2px 6px',
                borderRadius: '4px',
                border: '1px solid var(--sol-rule)',
              }}
            >
              Score {priorityProof.score_total}/200
            </span>
            {Object.entries(priorityProof.score_breakdown).map(([dim, pts]) => (
              <span key={dim} title={`${PROOF_DIMENSION_LABELS[dim] ?? dim} : ${pts} points`}>
                {PROOF_DIMENSION_LABELS[dim] ?? dim}{' '}
                <span style={{ color: 'var(--sol-ink-700)', fontWeight: 500 }}>{pts}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Impact chiffre */}
      {impact && (
        <div style={{ textAlign: 'right', lineHeight: 1.2, minWidth: '100px' }}>
          <div
            className="font-mono"
            style={{
              fontSize: '14px',
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
            }}
          >
            {impact.value}
          </div>
          {impact.label && (
            <div
              style={{
                fontSize: '10.5px',
                color: 'var(--sol-ink-400)',
                marginTop: '1px',
              }}
            >
              {impact.label}
            </div>
          )}
        </div>
      )}

      {/* CTA invitation */}
      {invitation && (
        <a
          href={invitation.href}
          className="font-mono whitespace-nowrap"
          style={{
            fontSize: '12.5px',
            fontWeight: 500,
            color: 'var(--sol-ink-700)',
            background: 'var(--sol-bg-canvas)',
            border: '1px solid var(--sol-rule)',
            borderRadius: '7px',
            padding: '6px 11px',
            textDecoration: 'none',
          }}
        >
          {capitalize(invitation.verb)} {invitation.object} →
        </a>
      )}
    </div>
  );
}
