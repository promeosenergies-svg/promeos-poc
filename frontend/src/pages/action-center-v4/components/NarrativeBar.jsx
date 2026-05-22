import { useActionCenterV4Summary } from '../../../hooks/v4';
import { formatEuros } from '../../../utils/money';
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

  // M2-5.12 — 5 tuiles alignées sur la maquette Sophie Marin 2026-05-22 :
  // Décisions P0/P1 (combinée) · Sans responsable · Bloqués · Preuvés ·
  // SLA en retard (placeholder MV3). Le breakdown P0/P1 reste sous-ligne
  // de « Sans responsable » (CFO actionability M2-5.11.J préservée).
  //
  // M2-6.B.frontend — sums € sous tuile « Décisions P0/P1 » (Q16=B
  // compact strict). Source : `sums_eur_by_priority.P0 + .P1` agrégés
  // backend (jamais recalculés FE — cf. test contractuel).
  // Tooltip cohérent colonne « Impact estimé » (même texte Q16).
  const sumsByPriority = data.sums_eur_by_priority ?? {};
  const sumP0P1 = (sumsByPriority.P0 ?? 0) + (sumsByPriority.P1 ?? 0);
  const tiles = [
    {
      key: 'decisions',
      value: (data.count_p0 ?? 0) + (data.count_p1 ?? 0),
      label: NARRATIVE_BAR_COPY.decisionsLabel,
      tooltip: NARRATIVE_BAR_COPY.decisionsTooltip,
      variant: NARRATIVE_BAR_VARIANTS.decisions,
      // sub-ligne sum € compact MV3 — affichée uniquement si > 0 (anti-bruit
      // §6.6 : `0 €` parasiterait la lecture rapide CFO sur org vierge).
      sumEur: sumP0P1 > 0 ? formatEuros(sumP0P1, 'compact') : null,
      sumTooltip: NARRATIVE_BAR_COPY.sumImpactTooltip,
    },
    {
      key: 'without_owner',
      value: data.count_without_owner ?? 0,
      label: NARRATIVE_BAR_COPY.withoutOwnerLabel,
      tooltip: NARRATIVE_BAR_COPY.withoutOwnerTooltip,
      variant: NARRATIVE_BAR_VARIANTS.without_owner,
      // M2-5.11.J — breakdown CFO : « 3 Sans responsable » ne dit pas si
      // c'est urgent. La sous-ligne expose la décomposition P0/P1 (signal
      // le plus actionnable). Affichée uniquement quand au moins 1 P0/P1
      // sans pilote — sinon ferme silencieusement (anti bruit §6.6).
      breakdown:
        (data.count_p0_without_owner ?? 0) + (data.count_p1_without_owner ?? 0) > 0
          ? formatOwnerBreakdown(data.count_p0_without_owner ?? 0, data.count_p1_without_owner ?? 0)
          : null,
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
    {
      // M2-5.12 — placeholder SLA en retard (maquette). MV3 affiche « — »
      // ink-400, tooltip explique l'arrivée M2-6 (endpoint /summary étendu +
      // seed sla_due_date populé). Doctrine §6.6 « pas de chiffre menteur ».
      key: 'sla_overdue',
      value: NARRATIVE_BAR_COPY.slaOverduePlaceholder,
      label: NARRATIVE_BAR_COPY.slaOverdueLabel,
      tooltip: NARRATIVE_BAR_COPY.slaOverdueTooltip,
      variant: NARRATIVE_BAR_VARIANTS.sla_overdue,
    },
  ];

  return (
    <div
      className="mb-3 grid grid-cols-2 gap-2 md:grid-cols-5"
      role="list"
      aria-label="Synthèse du Centre d'action"
      data-testid="narrative-bar"
    >
      {tiles.map(({ key, ...tileProps }) => (
        <StatTile key={key} {...tileProps} />
      ))}
    </div>
  );
}

/**
 * Tuile élémentaire (chiffre MONO + libellé court). Palette injectée via
 * `variant.bg` / `variant.accent` (cf. NARRATIVE_BAR_VARIANTS).
 */
function StatTile({ value, label, tooltip, variant, breakdown, sumEur, sumTooltip }) {
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
      {/* M2-5.11.J — sous-ligne breakdown CFO (P0/P1 sans pilote). MONO
          italique petite pour rester sub-text vs le chiffre principal. */}
      {breakdown && (
        <span
          className="font-mono text-[10px] italic tracking-[0.04em]"
          style={{ color: 'var(--sol-ink-500)', fontFamily: 'var(--sol-font-mono)' }}
          data-testid="stat-tile-breakdown"
        >
          {breakdown}
        </span>
      )}
      {/* M2-6.B.frontend — sum € compact (Q16) sous tuile « Décisions P0/P1 ».
          Style Sol sobre crème/brun (Q17=B) : ink-500 + border-top dashed
          ink-300 pour signaler tooltip help. Pas de couleur gain/coût/sanction
          (M3 classification sémantique). Source backend, jamais recalculée. */}
      {sumEur && (
        <span
          className="mt-1 cursor-help border-t border-dashed pt-1 font-mono text-[11px] tracking-[0.04em]"
          style={{
            color: 'var(--sol-ink-500)',
            borderColor: 'var(--sol-ink-300)',
            fontFamily: 'var(--sol-font-mono)',
          }}
          title={sumTooltip}
          data-testid="stat-tile-sum-eur"
        >
          {sumEur}
        </span>
      )}
    </div>
  );
}

/**
 * M2-5.11.J — formate le breakdown P0/P1 sans pilote.
 * Exemples :
 *  - (2, 3) → "2 P0 · 3 P1"
 *  - (0, 3) → "3 P1"
 *  - (2, 0) → "2 P0"
 *  - (0, 0) → null (consommateur teste avant d'appeler)
 */
function formatOwnerBreakdown(p0Count, p1Count) {
  const parts = [];
  if (p0Count > 0) parts.push(`${p0Count} P0`);
  if (p1Count > 0) parts.push(`${p1Count} P1`);
  return parts.join(' · ');
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
