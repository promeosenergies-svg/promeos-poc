import { A11Y_COPY, KIND_LABELS, KIND_LABELS_UPPER, KIND_SOL_VARIANTS } from '../../constants';
import { KIND_ICONS } from './kindIcons';

/**
 * M2-5.10.A — Cellule « Classement » de la table referentiel (maquette §8.3).
 *
 * Doctrine V4 cardinale : `kind` est l'axe intrinsèque (≠ priorité, axe
 * dérivé). La signature visuelle doit être immédiate : 1 icône colorée 26×26
 * + 1 label MONO 9px uppercase. Chaque kind a sa palette Sol et son style de
 * bordure (solid / dashed pour signal / dotted pour recommendation).
 *
 * Fallback : kind inconnu → boîte neutre + label « TYPE INCONNU ».
 */
export function KindCell({ kind }) {
  const variant = KIND_SOL_VARIANTS[kind];
  const Icon = KIND_ICONS[kind];
  const label = KIND_LABELS_UPPER[kind] || A11Y_COPY.unknownKindLabel.toUpperCase();

  // Kind inconnu : on rend une coque neutre pour préserver la grille (pas de
  // null silencieux qui désaligne les colonnes).
  if (!variant || !Icon) {
    return (
      <div className="flex items-center gap-[9px] pl-2">
        <span
          className="inline-flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-[4px] border"
          style={{
            background: 'var(--sol-bg-panel)',
            borderColor: 'var(--sol-ink-300)',
            color: 'var(--sol-ink-500)',
          }}
        />
        <span
          className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--sol-ink-500)' }}
        >
          {label}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-[9px] pl-2" data-kind={kind}>
      <span
        className="inline-flex h-[26px] w-[26px] flex-shrink-0 items-center justify-center rounded-[4px] border"
        style={{
          background: variant.bg,
          borderColor: variant.border,
          borderStyle: variant.borderStyle,
          color: variant.color,
        }}
        aria-hidden="true"
      >
        <Icon width={13} height={13} />
      </span>
      <span
        className="font-mono text-[9px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: variant.color }}
        title={KIND_LABELS[kind]}
      >
        {label}
      </span>
    </div>
  );
}
