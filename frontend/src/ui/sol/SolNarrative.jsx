/**
 * SolNarrative — récit éditorial Sol §5.
 *
 * Composant invariant grammaire :
 *   [KICKER]
 *   TITRE FRAUNCES
 *   Narrative 2-3 lignes sourcée et chiffrée
 *   [KPI 1] [KPI 2] [KPI 3]   ← max 3 KPIs avec tooltip
 *
 * Doctrine §5 + §3 P1 (briefing au lieu du dashboard).
 * Display-only — aucune logique métier (cf. règle d'or §8.1).
 *
 * Tout le contenu vient de l'endpoint backend
 * `/api/pages/{page_key}/briefing` via narrative_generator.py.
 *
 * Cf. ADR-001 grammaire Sol industrialisée.
 */
import { HelpCircle } from 'lucide-react';

function KpiTile({ kpi }) {
  const showTooltip = Boolean(kpi.tooltip);
  return (
    <div
      className="flex flex-col gap-1 px-4 py-3 bg-white border border-[var(--sol-line)] rounded-lg sol-card"
      data-testid={`sol-kpi-${kpi.label}`}
      role="listitem"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--sol-ink-500)]">
          {kpi.label}
        </span>
        {showTooltip && (
          <button
            type="button"
            className="text-[var(--sol-ink-500)] hover:text-[var(--sol-ink-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded-sm p-0.5 -m-0.5 cursor-help"
            title={kpi.tooltip}
            aria-label={`Définition : ${kpi.tooltip}`}
          >
            <HelpCircle size={12} aria-hidden="true" />
          </button>
        )}
      </div>
      <div className="flex items-baseline gap-1">
        <span className="sol-numeric text-[var(--sol-ink-900)] text-2xl font-semibold">
          {kpi.value}
        </span>
        {kpi.unit && (
          <span className="text-xs text-[var(--sol-ink-500)] font-medium">{kpi.unit}</span>
        )}
      </div>
      {kpi.source && (
        <span className="text-[10px] text-[var(--sol-ink-500)] font-mono uppercase tracking-wider truncate">
          {kpi.source}
        </span>
      )}
    </div>
  );
}

export default function SolNarrative({
  kicker,
  title,
  italicHook,
  narrative,
  kpis = [],
  className = '',
}) {
  // Doctrine §5 : "3 KPIs max". Tronquer silencieusement si backend
  // renvoie davantage — c'est un bug backend mais on tient l'invariant frontend.
  const safeKpis = kpis.slice(0, 3);

  return (
    <section
      data-testid="sol-narrative"
      className={`flex flex-col gap-5 mt-2 ${className}`}
      aria-label="Briefing éditorial"
    >
      <header className="flex flex-col gap-1">
        {kicker && <p className="sol-page-kicker">{kicker}</p>}
        {title && (
          <h1 className="sol-page-title">
            {title}
            {italicHook && (
              <>
                {' '}
                — <em>{italicHook}</em>
              </>
            )}
          </h1>
        )}
      </header>
      {narrative && (
        <p
          className="text-[15px] leading-relaxed text-[var(--sol-ink-700)] max-w-prose"
          data-testid="sol-narrative-body"
        >
          {narrative}
        </p>
      )}
      {safeKpis.length > 0 && (
        <div
          className="grid grid-cols-1 sm:grid-cols-3 gap-3"
          data-testid="sol-narrative-kpis"
          role="list"
          aria-label="Indicateurs clés"
        >
          {safeKpis.map((kpi, idx) => (
            <KpiTile key={kpi.label || idx} kpi={kpi} />
          ))}
        </div>
      )}
    </section>
  );
}
