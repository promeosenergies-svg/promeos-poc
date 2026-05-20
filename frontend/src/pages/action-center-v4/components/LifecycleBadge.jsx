import { LIFECYCLE_LABELS, LIFECYCLE_SOL_VARIANTS } from '../constants';

/**
 * M2-5.2 / M2-5.10.A — Pill d'état lifecycle (maquette §8.3 lignes 492-505).
 *
 * Dot + label MONO uppercase, palette Sol émotionnelle :
 *   new → neutre · triaged → hch (bleu) · planned → calme (vert) ·
 *   in_progress → attention (ambre) · closed → succes (vert forêt).
 *
 * État inconnu : fallback ink-500 + texte brut (cardinal §13.5 — pas de
 * silence).
 */
export function LifecycleBadge({ state }) {
  const variant = LIFECYCLE_SOL_VARIANTS[state] || {
    bg: 'var(--sol-bg-paper)',
    border: 'var(--sol-ink-500)',
    color: 'var(--sol-ink-500)',
  };
  const label = LIFECYCLE_LABELS[state] || state || '—';

  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-px font-mono text-[9.5px] font-medium uppercase tracking-[0.05em]"
      style={{
        background: variant.bg,
        borderColor: variant.border,
        color: variant.color,
      }}
    >
      <span
        className="h-1 w-1 rounded-full"
        style={{ background: 'currentColor' }}
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
