import { A11Y_COPY, DOMAIN_LABELS, DOMAIN_SOL_VARIANTS } from '../../constants';

/**
 * M2-5.10.A — Chip MONO uppercase pour le domaine (maquette §8.3 lignes
 * 508-521). Couleur Sol par domaine, sinon panel neutre + dashed pour
 * « domaine inconnu ».
 *
 * Le composant rend `null` si le domaine est absent : la cellule du tableau
 * affichera alors « — » côté `ItemsTable` (cardinal vide explicite §13.5).
 */
export function DomainChip({ domain }) {
  if (!domain) return null;

  const variant = DOMAIN_SOL_VARIANTS[domain];
  const label = DOMAIN_LABELS[domain] || A11Y_COPY.unknownDomainLabel;

  // Domaine inconnu : style neutre dashed pour signaler explicitement.
  const style = variant
    ? { background: variant.bg, color: variant.color }
    : {
        background: 'var(--sol-bg-panel)',
        color: 'var(--sol-ink-500)',
        border: '1px dashed var(--sol-ink-300)',
      };

  return (
    <span
      className="inline-block whitespace-nowrap rounded-[2px] px-1.5 py-px font-mono text-[9.5px] font-medium uppercase tracking-[0.08em]"
      style={style}
    >
      {label}
    </span>
  );
}
