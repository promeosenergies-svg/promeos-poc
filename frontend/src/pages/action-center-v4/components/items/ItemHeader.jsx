import {
  A11Y_COPY,
  DRAWER_COPY,
  KIND_LABELS,
  KIND_LABELS_UPPER,
  KIND_SOL_VARIANTS,
} from '../../constants';
import { formatDateTimeFR } from '../../utils/date';
import { DomainChip } from './DomainChip';
import { KIND_ICONS } from './kindIcons';
import { LifecycleBadge } from './LifecycleBadge';
import { PriorityBadge } from './PriorityBadge';

/**
 * M2-5.3.A / M2-5.4 / M2-5.10.B — Title block du drawer (maquette §8.4 lignes
 * 234-310 « d-title-block »).
 *
 * H1 Fraunces 25px italique + summary (description) + status row (kind +
 * priority + lifecycle + domain) + métadonnées footer mono uppercase.
 *
 * Restyle pixel-perfect Sol : on s'aligne sur les éléments backend exposés
 * (title, description, kind, priority_bracket, priority_score, lifecycle_state,
 * domain, created_at, updated_at). Le bouton « Transitionner » est désormais
 * porté par `DrawerActions` (les 3 boutons header maquette — Planifier
 * primary / Réassigner secondary / Plus ▾ avec menu).
 *
 * Hors scope M3+ : SLA pair (sla_treatment_at), evidence badge (expected_
 * evidence), owner avatar (owner_id).
 */

/**
 * Kind badge spécifique au header (« Type : Anomalie » MONO uppercase 10.5px,
 * maquette ligne 253-263) — variante plus dense que `KindCell` de la table.
 * Colocated ici car usage unique.
 */
function KindHeaderBadge({ kind }) {
  const variant = KIND_SOL_VARIANTS[kind];
  const Icon = KIND_ICONS[kind];
  const label = KIND_LABELS_UPPER[kind] || A11Y_COPY.unknownKindLabel.toUpperCase();
  if (!variant || !Icon) {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-[3px] border px-2.5 py-1 font-mono text-[10.5px] font-bold uppercase tracking-[0.08em]"
        style={{
          background: 'var(--sol-bg-panel)',
          borderColor: 'var(--sol-ink-300)',
          color: 'var(--sol-ink-500)',
        }}
      >
        {label}
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-[3px] border px-2.5 py-1 font-mono text-[10.5px] font-bold uppercase tracking-[0.08em]"
      style={{
        background: variant.bg,
        borderColor: variant.border,
        borderStyle: variant.borderStyle,
        color: variant.color,
      }}
      title={KIND_LABELS[kind]}
    >
      <Icon width={11} height={11} aria-hidden="true" />
      Type : {KIND_LABELS[kind]}
    </span>
  );
}

export function ItemHeader({ item, loading, error }) {
  if (loading) {
    // M2-5.10.bis clôture (audit UI Sol P1-4) : skeleton sur tokens Sol pour
    // cohérence avec les autres skeletons V4 (PilotagePage, JournalPage,
    // ImpactSection — tous utilisent `--sol-bg-panel`).
    return (
      <header>
        <div
          className="mb-3 h-7 w-2/3 animate-pulse rounded"
          style={{ background: 'var(--sol-bg-panel)' }}
        />
        <div
          className="h-4 w-1/3 animate-pulse rounded"
          style={{ background: 'var(--sol-bg-panel)' }}
        />
      </header>
    );
  }

  if (error || !item) {
    return (
      <header>
        <p className="text-sm" style={{ color: 'var(--sol-refuse-fg)' }}>
          {DRAWER_COPY.headerError}
        </p>
      </header>
    );
  }

  return (
    <header className="pb-3.5" style={{ borderBottom: '1px solid var(--sol-rule)' }}>
      <h1
        className="mb-2 text-[25px] font-medium leading-[1.18] tracking-[-0.018em]"
        style={{
          fontFamily: 'var(--sol-font-display)',
          color: 'var(--sol-ink-900)',
        }}
      >
        {item.title}
      </h1>

      {item.description && (
        <p
          className="text-[13.5px] leading-[1.5]"
          style={{
            fontFamily: 'var(--sol-font-body)',
            color: 'var(--sol-ink-700)',
          }}
        >
          {item.description}
        </p>
      )}

      {/* Status row maquette §8.4 ligne 248-310. SLA pair + evidence badge =
          dette M3+ (champs BE manquants — cf. BACKLOG_M3). */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {item.kind && <KindHeaderBadge kind={item.kind} />}
        <PriorityBadge bracket={item.priority_bracket} score={item.priority_score} />
        <LifecycleBadge state={item.lifecycle_state} />
        {item.domain && <DomainChip domain={item.domain} />}
      </div>

      {/* Métadonnées meta-grid simplifiée (Créé / MAJ uniquement). M2-5.10.B.bis
          — `kind`/`domain` retirés car déjà rendus dans le status row ci-dessus
          (audit UI Sol P1-4 — duplication visuelle). Responsable + Détecté +
          SLA = dette M3+, cardinal owner BE manquant. */}
      <dl
        className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1 font-mono text-[10px] uppercase tracking-[0.14em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        <div>
          <dt className="mb-0.5">{DRAWER_COPY.createdAtLabel}</dt>
          <dd
            className="font-sans text-[12.5px] normal-case tracking-normal"
            style={{ color: 'var(--sol-ink-900)' }}
          >
            {formatDateTimeFR(item.created_at)}
          </dd>
        </div>
        <div>
          <dt className="mb-0.5">{DRAWER_COPY.updatedAtLabel}</dt>
          <dd
            className="font-sans text-[12.5px] normal-case tracking-normal"
            style={{ color: 'var(--sol-ink-900)' }}
          >
            {formatDateTimeFR(item.updated_at)}
          </dd>
        </div>
      </dl>
    </header>
  );
}
