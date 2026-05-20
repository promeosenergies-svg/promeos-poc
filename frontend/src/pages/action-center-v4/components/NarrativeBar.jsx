import { useActionCenterV4Summary } from '../../../hooks/v4';
import { NARRATIVE_BAR_COPY, NARRATIVE_BAR_VARIANTS } from '../constants';

/**
 * M2-5.11.C — NarrativeBar Sol (5 compteurs CFO « état du portefeuille »).
 *
 * Tuile horizontale posée sous le Masthead des pages Référentiel + Pilotage
 * (cf. audit ux/cfo 3.5/10 → cible 5.5/10). Cinq stats agrégées org
 * `GET /api/v4/action-center/summary` :
 * P0 actifs · P1 actifs · Sans pilote · Bloqués · Preuvés.
 *
 * États :
 * - loading : 5 squelettes pulsés (skeleton inoffensif, conserve la hauteur).
 * - error   : bandeau Sol palette refuse + bouton « Réessayer » (action sans
 *             quitter la page).
 * - data    : 5 tuiles colorées Sol émotionnelles. Couleurs N&B-stables
 *             (palette doctrine v0.3 §3.2 — refuse/attention/ink-500/succès).
 *
 * Le composant hydrate son propre hook (auto-fetch au montage). Si une page
 * a besoin de partager le summary avec une autre brique, le hook se réutilise
 * tel quel — la pile de state V4 est sans cache global (volontaire MV3).
 */
export function NarrativeBar() {
  const { data, loading, error, refetch } = useActionCenterV4Summary();

  if (loading) return <NarrativeBarSkeleton />;
  if (error) return <NarrativeBarError message={error.message} onRetry={refetch} />;
  if (!data) return null;

  // Cinq tuiles dans l'ordre canonique de lecture (urgence → preuve).
  const tiles = [
    {
      key: 'p0',
      value: data.count_p0 ?? 0,
      label: NARRATIVE_BAR_COPY.p0Label,
      tooltip: NARRATIVE_BAR_COPY.p0Tooltip,
      variant: NARRATIVE_BAR_VARIANTS.p0,
    },
    {
      key: 'p1',
      value: data.count_p1 ?? 0,
      label: NARRATIVE_BAR_COPY.p1Label,
      tooltip: NARRATIVE_BAR_COPY.p1Tooltip,
      variant: NARRATIVE_BAR_VARIANTS.p1,
    },
    {
      key: 'without_owner',
      value: data.count_without_owner ?? 0,
      label: NARRATIVE_BAR_COPY.withoutOwnerLabel,
      tooltip: NARRATIVE_BAR_COPY.withoutOwnerTooltip,
      variant: NARRATIVE_BAR_VARIANTS.without_owner,
    },
    {
      key: 'at_risk',
      value: data.count_at_risk ?? 0,
      label: NARRATIVE_BAR_COPY.atRiskLabel,
      tooltip: NARRATIVE_BAR_COPY.atRiskTooltip,
      variant: NARRATIVE_BAR_VARIANTS.at_risk,
    },
    {
      key: 'secured',
      value: data.count_secured ?? 0,
      label: NARRATIVE_BAR_COPY.securedLabel,
      tooltip: NARRATIVE_BAR_COPY.securedTooltip,
      variant: NARRATIVE_BAR_VARIANTS.secured,
    },
  ];

  return (
    <div
      className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-5"
      role="list"
      aria-label="Synthèse du Centre d'action"
      data-testid="narrative-bar"
    >
      {tiles.map((tile) => (
        <StatTile key={tile.key} {...tile} />
      ))}
    </div>
  );
}

/**
 * Tuile élémentaire (chiffre MONO + libellé court). Palette injectée via
 * `variant.bg` / `variant.accent` (cf. NARRATIVE_BAR_VARIANTS).
 */
function StatTile({ value, label, tooltip, variant }) {
  return (
    <div
      role="listitem"
      title={tooltip}
      className="flex flex-col items-start gap-0.5 rounded-[8px] border px-3 py-2.5"
      style={{
        background: variant.bg,
        borderColor: 'var(--sol-rule)',
      }}
    >
      <span
        className="font-mono text-[22px] font-semibold leading-none"
        style={{ color: variant.accent, fontFamily: 'var(--sol-font-mono)' }}
        data-testid="stat-tile-value"
      >
        {value}
      </span>
      <span
        className="text-[11.5px] font-medium uppercase tracking-[0.06em]"
        style={{
          color: 'var(--sol-ink-700)',
          fontFamily: 'var(--sol-font-mono)',
        }}
      >
        {label}
      </span>
    </div>
  );
}

function NarrativeBarSkeleton() {
  return (
    <div
      className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-5"
      aria-busy="true"
      aria-label={NARRATIVE_BAR_COPY.loadingLabel}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="h-[64px] animate-pulse rounded-[8px] border"
          style={{
            background: 'var(--sol-bg-panel)',
            borderColor: 'var(--sol-rule)',
          }}
        />
      ))}
    </div>
  );
}

function NarrativeBarError({ message, onRetry }) {
  return (
    <div
      role="alert"
      className="mb-3 flex items-center justify-between gap-3 rounded-[8px] border px-3 py-2"
      style={{
        background: 'var(--sol-refuse-bg)',
        borderColor: 'var(--sol-refuse-line)',
        color: 'var(--sol-refuse-fg)',
      }}
    >
      <div className="flex-1 text-[12.5px]">
        <span className="font-medium">{NARRATIVE_BAR_COPY.errorTitle}</span>
        {message ? <span className="ml-1 opacity-80">· {message}</span> : null}
      </div>
      <button
        type="button"
        onClick={onRetry}
        className="rounded-[6px] border px-2 py-1 font-mono text-[10.5px] font-medium uppercase tracking-[0.08em] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--sol-ink-900)]"
        style={{
          background: 'var(--sol-bg-paper)',
          borderColor: 'var(--sol-refuse-line)',
          color: 'var(--sol-refuse-fg)',
        }}
      >
        {NARRATIVE_BAR_COPY.errorRetry}
      </button>
    </div>
  );
}
