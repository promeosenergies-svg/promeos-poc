/**
 * PROMEOS — PersonaToggle (F.25 doctrine v1.0).
 *
 * Dropdown topbar pour switcher entre les 3 personas du scoring de priorisation.
 * Pondère le calcul backend `compute_finding_priority` via ?persona=... .
 *
 * Différentiant cardinal PROMEOS : "Le même patrimoine, 3 audiences,
 * 3 priorités calculées" (cf ADR-022 §Personas + doctrine v1.0).
 */
import {
  PERSONAS,
  PERSONA_DESCRIPTIONS,
  PERSONA_LABELS,
  usePersona,
} from '../contexts/PersonaContext';

export default function PersonaToggle({ className = '' }) {
  const { persona, setPersona } = usePersona();

  return (
    <label
      className={`flex items-center gap-2 ${className}`}
      style={{ fontSize: '12px', color: 'var(--sol-ink-500)' }}
      title={PERSONA_DESCRIPTIONS[persona] ?? ''}
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
        {Object.values(PERSONAS).map((p) => (
          <option key={p} value={p}>
            {PERSONA_LABELS[p]}
          </option>
        ))}
      </select>
    </label>
  );
}
