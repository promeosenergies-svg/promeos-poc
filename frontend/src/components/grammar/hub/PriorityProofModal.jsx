/**
 * PROMEOS — PriorityProofModal (F.27 doctrine v1.0).
 *
 * Modal drill-down "Pourquoi P1 ?" affichant la décomposition complète du
 * scoring d'une finding cockpit jour. Différentiant cardinal PROMEOS :
 * la priorité est défendable face à un audit externe.
 *
 * Doctrine v1.4.2 :
 *   PRIORITÉ P1 — Pourquoi ?
 *   GRAVITÉ : 5/5 → Sanction légale immédiate · Source: …
 *   IMPACT  : 3/5 → Économie 15,6 k€/an + sanction 7,5 k€ évitée · Source: …
 *   DÉLAI   : 3/5 → J-154 jusqu'au 01/07/2026 · Source: …
 *   SCORE FINAL : 27/35 (persona Responsable Énergie) = 5·3 + 3·2 + 3·2
 *   OVERRIDE : OV1_GRAVITE_LEGALE_ABSOLUE (G=5 force score ≥ 25)
 *   CLASSEMENT : P1 (seuil ≥ 25)
 */
import { useEffect } from 'react';

const PERSONA_LABELS = {
  responsable_energie: 'Responsable Énergie',
  daf: 'DAF',
  dg_comex: 'DG / COMEX',
};

const PERSONA_FORMULA = {
  responsable_energie: 'G·3 + I·2 + D·2',
  daf: 'G·2 + I·3 + D·2',
  dg_comex: 'G·2 + I·3 + D·3',
};

const PERSONA_MAX = {
  responsable_energie: 35,
  daf: 35,
  dg_comex: 40,
};

const OVERRIDE_DESCRIPTIONS = {
  OV1_GRAVITE_LEGALE_ABSOLUE:
    "G=5 (sanction légale immédiate) force score ≥ 25 — garantit P1 indépendamment de l'impact et du délai.",
  OV2_URGENCE_QUALIFIEE:
    'D=5 (≤ 30 jours) + G ≥ 3 force score ≥ 22 — toute urgence qualifiée monte en haut P2.',
  OV3_IMPACT_ORPHELIN:
    'I=5 (≥ 100 k€/an) + G=0 plafonne score à 15 — un gros impact sans gravité ne peut pas écraser un sujet réglementaire.',
};

export default function PriorityProofModal({ highlight, onClose }) {
  // Fermeture sur Escape.
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  if (!highlight || !highlight._audit) return null;

  const a = highlight._audit;
  const bd = a.score_breakdown || {};
  const sources = a.sources || {};
  const labels = a.axis_labels || {};
  const personaLabel = PERSONA_LABELS[a.persona] ?? a.persona;
  const formula = PERSONA_FORMULA[a.persona] ?? '';
  const maxScore = PERSONA_MAX[a.persona] ?? 35;
  const formulaResolved = `${bd.g}·${formula.match(/G·(\d)/)?.[1] ?? '?'} + ${bd.i}·${formula.match(/I·(\d)/)?.[1] ?? '?'} + ${bd.d}·${formula.match(/D·(\d)/)?.[1] ?? '?'}`;

  return (
    <div
      data-component="PriorityProofModal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="proof-modal-title"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(15, 23, 42, 0.45)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--sol-bg-paper)',
          borderRadius: '14px',
          maxWidth: '640px',
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 24px 64px rgba(0,0,0,0.25)',
          border: '1px solid var(--sol-rule)',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid var(--sol-rule)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div>
            <div
              className="font-mono"
              style={{
                fontSize: '11px',
                letterSpacing: '0.1em',
                color: 'var(--sol-ink-400)',
                textTransform: 'uppercase',
                marginBottom: '4px',
              }}
            >
              {highlight.category} · {highlight.scope}
            </div>
            <h2
              id="proof-modal-title"
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: '20px',
                fontWeight: 500,
                color: 'var(--sol-ink-900)',
                margin: 0,
                lineHeight: 1.25,
              }}
            >
              {highlight.tier} — pourquoi ?
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            style={{
              fontSize: '20px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--sol-ink-500)',
              padding: '4px 8px',
            }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div
          style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '18px' }}
        >
          {/* Axe Gravité */}
          <AxisRow
            label="Gravité"
            value={bd.g}
            weighted={bd.g_weighted}
            interpretation={labels.gravity}
            source={sources.gravity}
            color="var(--sol-refuse-fg)"
          />
          {/* Axe Impact */}
          <AxisRow
            label="Impact"
            value={bd.i}
            weighted={bd.i_weighted}
            interpretation={labels.impact}
            source={sources.impact}
            color="var(--sol-attention-fg)"
          />
          {/* Axe Délai */}
          <AxisRow
            label="Délai"
            value={bd.d}
            weighted={bd.d_weighted}
            interpretation={labels.delay}
            source={sources.delay}
            color="var(--sol-hch-fg)"
          />

          {/* Score final */}
          <div
            style={{
              padding: '14px',
              background: 'var(--sol-bg-canvas)',
              border: '1px solid var(--sol-rule)',
              borderRadius: '8px',
            }}
          >
            <div
              className="font-mono"
              style={{ fontSize: '10.5px', color: 'var(--sol-ink-400)', marginBottom: '6px' }}
            >
              SCORE FINAL · PERSONA {personaLabel.toUpperCase()}
            </div>
            <div
              style={{
                fontSize: '15px',
                fontWeight: 500,
                color: 'var(--sol-ink-900)',
                fontFamily: 'var(--sol-font-display)',
              }}
            >
              {a.score_total}/{maxScore}{' '}
              <span
                className="font-mono"
                style={{ fontSize: '12px', color: 'var(--sol-ink-500)', fontWeight: 400 }}
              >
                = {formulaResolved}
              </span>
            </div>
          </div>

          {/* Overrides appliqués */}
          {a.overrides_applied && a.overrides_applied.length > 0 && (
            <div
              style={{
                padding: '12px',
                background: 'var(--sol-attention-bg)',
                border: '1px solid var(--sol-attention-line)',
                borderRadius: '8px',
                fontSize: '12px',
                lineHeight: 1.5,
                color: 'var(--sol-attention-fg)',
              }}
            >
              <div
                className="font-mono"
                style={{ fontSize: '10.5px', marginBottom: '6px', fontWeight: 500 }}
              >
                ⚡ OVERRIDE DOCTRINAL
              </div>
              {a.overrides_applied.map((ov) => (
                <div key={ov} style={{ marginTop: '4px' }}>
                  <strong>{ov}</strong> — {OVERRIDE_DESCRIPTIONS[ov] ?? ''}
                </div>
              ))}
            </div>
          )}

          {/* Doctrine version footer */}
          <div
            className="font-mono"
            style={{
              fontSize: '10px',
              color: 'var(--sol-ink-400)',
              borderTop: '1px solid var(--sol-rule)',
              paddingTop: '10px',
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <span>Doctrine {a.doctrine_version}</span>
            <span>
              Tier {highlight.tier} · catégorie {a.category} · {a.scope_level}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AxisRow({ label, value, weighted, interpretation, source, color }) {
  return (
    <div>
      <div
        className="font-mono"
        style={{
          fontSize: '10.5px',
          letterSpacing: '0.08em',
          color: 'var(--sol-ink-400)',
          textTransform: 'uppercase',
          marginBottom: '4px',
        }}
      >
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginBottom: '4px' }}>
        <span
          style={{
            fontSize: '24px',
            fontWeight: 500,
            color,
            fontFamily: 'var(--sol-font-display)',
          }}
        >
          {value}/5
        </span>
        <span style={{ fontSize: '13px', color: 'var(--sol-ink-700)' }}>{interpretation}</span>
        <span
          className="font-mono"
          style={{ fontSize: '10.5px', color: 'var(--sol-ink-400)', marginLeft: 'auto' }}
        >
          {weighted} pts
        </span>
      </div>
      {source && (
        <div
          className="font-mono"
          style={{
            fontSize: '10.5px',
            color: 'var(--sol-ink-500)',
            paddingLeft: '8px',
            borderLeft: `2px solid ${color}`,
          }}
        >
          Source · {source}
        </div>
      )}
    </div>
  );
}
