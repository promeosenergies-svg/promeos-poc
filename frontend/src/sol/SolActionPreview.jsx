/**
 * PROMEOS — SolActionPreview
 *
 * Drawer de prévisualisation avant exécution Sol. Affiche :
 * - Plan complet (title, summary, sources, confidence)
 * - Preview payload (courrier markdown, pièces jointes, etc.)
 * - 4 garanties d'exécution (délai de grâce, logique déterministe, audit, DKIM)
 * - CTA "Valider — envoi dans 24h" + "Éditer" + "Annuler"
 *
 * Réutilise `ui/Drawer.jsx` existant (ESC + tab trap + focus trap inclus).
 */
import Drawer from '../ui/Drawer';

export default function SolActionPreview({
  open,
  onClose,
  plan,
  onConfirm,
  onEdit = null,
  confirming = false,
}) {
  if (!plan) return null;

  const previewLetter = plan?.preview_payload?.letter_markdown || '';
  const attachments = plan?.preview_payload?.attachments || [];
  const graceHours = Math.round((plan?.grace_period_seconds || 0) / 3600);

  return (
    <Drawer open={open} onClose={onClose} title="Prévisualisation Sol" wide noPadding>
      <div
        className="sol-surface"
        style={{
          padding: '20px 28px',
          background: 'var(--sol-bg-paper)',
          color: 'var(--sol-ink-900)',
          overflowY: 'auto',
          height: '100%',
        }}
      >
        {/* Kicker + subtitle */}
        <div style={{ marginBottom: '14px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '10.5px',
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              color: 'var(--sol-calme-fg)',
              fontWeight: 600,
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--sol-calme-fg)',
                animation: 'sol-pulse 2.5s ease-in-out infinite',
              }}
            />
            Sol · prévisualisation avant exécution
          </span>
          <h3
            style={{
              fontSize: '20px',
              fontWeight: 600,
              color: 'var(--sol-ink-900)',
              margin: '8px 0 0 0',
              letterSpacing: '-0.015em',
              lineHeight: 1.2,
            }}
          >
            {plan.title_fr}
          </h3>
          <p
            style={{
              fontSize: '13.5px',
              color: 'var(--sol-ink-500)',
              margin: '10px 0 0 0',
              lineHeight: 1.5,
            }}
          >
            {plan.summary_fr}
          </p>
        </div>

        {/* Confidence */}
        <div
          style={{
            background: 'var(--sol-bg-panel)',
            padding: '12px 16px',
            borderRadius: '4px',
            borderLeft: '3px solid var(--sol-calme-fg)',
            marginBottom: '18px',
          }}
        >
          <div
            style={{
              fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
              fontSize: '12px',
              color: 'var(--sol-ink-700)',
              lineHeight: 1.5,
            }}
          >
            Confiance calcul :{' '}
            <strong style={{ color: 'var(--sol-calme-fg)' }}>
              {Math.round((plan.confidence || 0) * 100)} %
            </strong>
            {graceHours > 0 && (
              <>
                {' · Délai de grâce : '}
                <strong style={{ color: 'var(--sol-ink-900)' }}>{graceHours} h</strong>
              </>
            )}
          </div>
        </div>

        {/* Preview letter markdown */}
        {previewLetter && (
          <div style={{ marginBottom: '18px' }}>
            <div
              style={{
                fontSize: '10.5px',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: 'var(--sol-ink-500)',
                fontWeight: 600,
                marginBottom: '8px',
              }}
            >
              Courrier qui sera envoyé
            </div>
            <div
              style={{
                background: 'var(--sol-bg-canvas)',
                border: '1px solid var(--sol-ink-200)',
                borderRadius: '4px',
                padding: '16px 18px',
                fontSize: '13.5px',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                fontFamily: 'Georgia, serif',
              }}
            >
              {previewLetter}
            </div>
          </div>
        )}

        {/* Pièces jointes */}
        {attachments.length > 0 && (
          <div style={{ marginBottom: '18px' }}>
            <div
              style={{
                fontSize: '10.5px',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: 'var(--sol-ink-500)',
                fontWeight: 600,
                marginBottom: '8px',
              }}
            >
              Pièces jointes générées
            </div>
            <ul
              style={{
                listStyle: 'none',
                padding: 0,
                margin: 0,
                fontFamily: 'ui-monospace, "JetBrains Mono", monospace',
                fontSize: '12px',
                color: 'var(--sol-ink-700)',
                lineHeight: 1.8,
              }}
            >
              {attachments.map((att, idx) => (
                <li key={idx}>
                  {att.name}{' '}
                  {att.size_bytes && (
                    <span style={{ color: 'var(--sol-ink-500)' }}>
                      · {(att.size_bytes / 1024).toFixed(0)} ko
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Garanties d'exécution */}
        <div style={{ marginBottom: '18px' }}>
          <div
            style={{
              fontSize: '10.5px',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--sol-ink-500)',
              fontWeight: 600,
              marginBottom: '8px',
            }}
          >
            Garanties d'exécution
          </div>
          <ol style={{ margin: 0, padding: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {[
              `Délai de grâce ${graceHours} h — annulable d'un clic, sans frais.`,
              'Logique déterministe — calcul issu du moteur métier, pas une estimation LLM.',
              'Audit complet — chaque étape tracée dans le journal, exportable.',
              'Mail signé PROMEOS — DKIM/SPF depuis votre domaine, pas depuis un tiers.',
            ].map((text, idx) => (
              <li
                key={idx}
                style={{
                  background: 'var(--sol-bg-panel)',
                  borderRadius: '4px',
                  padding: '10px 14px',
                  fontSize: '13px',
                  color: 'var(--sol-ink-700)',
                  display: 'flex',
                  gap: '12px',
                }}
              >
                <span style={{ color: 'var(--sol-calme-fg)', fontWeight: 600, flexShrink: 0 }}>
                  {idx + 1}.
                </span>
                <span>{text}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Footer CTAs */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingTop: '16px',
            borderTop: '1px solid var(--sol-rule)',
            gap: '10px',
          }}
        >
          <button
            type="button"
            onClick={onClose}
            disabled={confirming}
            style={{
              fontSize: '13.5px',
              padding: '9px 16px',
              background: 'transparent',
              color: 'var(--sol-ink-500)',
              border: 'none',
              cursor: confirming ? 'not-allowed' : 'pointer',
            }}
          >
            Annuler
          </button>
          <div style={{ display: 'flex', gap: '8px' }}>
            {onEdit && (
              <button
                type="button"
                onClick={onEdit}
                disabled={confirming}
                style={{
                  fontSize: '13.5px',
                  padding: '9px 16px',
                  background: 'var(--sol-bg-paper)',
                  color: 'var(--sol-ink-900)',
                  border: '1px solid var(--sol-rule)',
                  borderRadius: '4px',
                  cursor: confirming ? 'not-allowed' : 'pointer',
                }}
              >
                Éditer le courrier
              </button>
            )}
            <button
              type="button"
              onClick={onConfirm}
              disabled={confirming}
              style={{
                fontSize: '13.5px',
                fontWeight: 500,
                padding: '9px 16px',
                background: confirming ? 'var(--sol-ink-300)' : 'var(--sol-ink-900)',
                color: '#FFFFFF',
                border: '1px solid transparent',
                borderRadius: '4px',
                cursor: confirming ? 'not-allowed' : 'pointer',
              }}
            >
              {confirming ? 'Envoi…' : `Valider — envoi dans ${graceHours || 24} h`}
            </button>
          </div>
        </div>
      </div>
    </Drawer>
  );
}
