import { PRIORITY_LABELS, PRIORITY_SOL_BG } from '../../constants';

/**
 * M2-5.8.B / M2-5.10.A — Tag de priorité (maquette §8.3 lignes 523-536).
 *
 * Format pixel-perfect maquette : `P0 · 92` (bracket + score visible),
 * pleins coloriés (texte clair sur fond). Le score est masqué si absent
 * (item sans `priority_score` — défensif).
 *
 * Bracket absent → `null` (la cellule de tableau reste vide ; doctrine
 * §13.5 : pas de placeholder factice pour donnée absente sur priorité).
 */
export function PriorityBadge({ bracket, score }) {
  if (!bracket) return null;

  const bg = PRIORITY_SOL_BG[bracket] || 'var(--sol-ink-400)';
  const label = PRIORITY_LABELS[bracket] || bracket;
  // Score affichable si nombre fini ∈ [0, 100]. Round entier (doctrine
  // tableau : 1 chiffre maquette suffit, fraction = bruit visuel).
  const showScore =
    typeof score === 'number' && Number.isFinite(score) && score >= 0 && score <= 100;

  // M2-5.11.H : tooltip enrichi avec le score (audit polish CS +0.1).
  // Sans le score, « Critique » seul ne disait pas pourquoi le score 92 à
  // côté est le score — lecteurs d'écran n'avaient pas le contexte.
  const tooltip = showScore ? `${label} (score ${Math.round(score)} / 100)` : label;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-[3px] px-2 py-px font-mono text-[10px] font-bold tracking-[0.06em]"
      style={{ background: bg, color: 'var(--sol-bg-paper)' }}
      title={tooltip}
    >
      <span>{bracket}</span>
      {showScore && (
        <>
          <span aria-hidden="true" className="opacity-70">
            ·
          </span>
          <span className="font-medium tracking-normal opacity-90">{Math.round(score)}</span>
        </>
      )}
    </span>
  );
}
