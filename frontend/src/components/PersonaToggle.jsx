/**
 * PROMEOS — PersonaToggle (F.25 doctrine v1.0).
 *
 * Dropdown topbar pour switcher entre les 3 personas du scoring de priorisation.
 * Pondère le calcul backend `compute_finding_priority` via ?persona=... .
 *
 * Différentiant cardinal PROMEOS : "Le même patrimoine, 3 audiences,
 * 3 priorités calculées" (cf ADR-022 §Personas + doctrine v1.0).
 */
import { useEffect, useState } from 'react';
import {
  PERSONAS,
  PERSONA_DESCRIPTIONS,
  PERSONA_LABELS,
  usePersona,
} from '../contexts/PersonaContext';

/**
 * F.28 — Toggle DAF/DG-COMEX conditionnel : désactivé si la qualité données
 * passée en prop est insuffisante (< 80 %). Doctrine v1.4.3 §V8 :
 * "Mode Direction disponible quand tous les chiffres sont vérifiables."
 *
 * @param {Object} props
 * @param {number} [props.dataQualityPct] - 0-100. Si < 80, DAF + DG-COMEX désactivés
 *                                          et un tooltip explique pourquoi.
 */
export default function PersonaToggle({ className = '', dataQualityPct }) {
  const { persona, setPersona, dataQualityPct: contextQuality } = usePersona();
  // F.28 — priorité au prop explicite, sinon valeur du contexte (publiée
  // par la page courante via setDataQualityPct).
  const effectiveQuality = dataQualityPct ?? contextQuality ?? 100;
  const verifiable = effectiveQuality >= 80;

  // F.28 — auto-revert vers RESPONSABLE_ENERGIE si la data quality chute
  // sous 80 % alors qu'un persona Direction est sélectionné.
  useEffect(() => {
    if (!verifiable && persona !== PERSONAS.RESPONSABLE_ENERGIE) {
      setPersona(PERSONAS.RESPONSABLE_ENERGIE);
    }
  }, [verifiable, persona, setPersona]);

  const disabledTooltip = verifiable
    ? (PERSONA_DESCRIPTIONS[persona] ?? '')
    : `Mode Direction disponible quand la qualité données ≥ 80 % (actuelle ${effectiveQuality} %). Doctrine v1 §14.4.3.`;

  return (
    <label
      className={`flex items-center gap-2 ${className}`}
      style={{ fontSize: '12px', color: 'var(--sol-ink-500)' }}
      title={disabledTooltip}
    >
      <span
        className="font-mono uppercase"
        style={{
          fontSize: '10px',
          letterSpacing: '0.08em',
          color: 'var(--sol-ink-400)',
        }}
      >
        Vue
      </span>
      <select
        data-component="PersonaToggle"
        data-persona={persona}
        data-verifiable={verifiable}
        value={persona}
        onChange={(e) => setPersona(e.target.value)}
        className="font-mono"
        style={{
          fontSize: '11.5px',
          fontWeight: 500,
          color: 'var(--sol-ink-700)',
          background: 'var(--sol-bg-paper)',
          border: '1px solid var(--sol-rule)',
          borderRadius: '6px',
          padding: '4px 8px',
          cursor: 'pointer',
        }}
      >
        {Object.values(PERSONAS).map((p) => {
          // F.28 — DAF + DG-COMEX désactivés si data quality < 80 %.
          const disabled = !verifiable && p !== PERSONAS.RESPONSABLE_ENERGIE;
          return (
            <option key={p} value={p} disabled={disabled}>
              {PERSONA_LABELS[p]}
              {disabled ? ' (indisponible — données < 80 %)' : ''}
            </option>
          );
        })}
      </select>
    </label>
  );
}
