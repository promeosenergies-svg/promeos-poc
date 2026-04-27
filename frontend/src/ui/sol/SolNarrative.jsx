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
 * Sprint 1.3bis P0-B : prop optionnelle `error` — quand le hook
 * usePageBriefing échoue, on affiche un ErrorState dédié au lieu de
 * masquer silencieusement le préambule (audit CX fin S1).
 *
 * Cf. ADR-001 grammaire Sol industrialisée.
 */
import { HelpCircle, AlertCircle } from 'lucide-react';

function KpiTile({ kpi }) {
  const showTooltip = Boolean(kpi.tooltip);
  return (
    <div
      className="flex flex-col gap-2 px-5 py-4 bg-white border border-[var(--sol-line)] rounded-lg sol-card"
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
            className="text-[var(--sol-ink-500)] hover:text-[var(--sol-ink-700)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded-sm p-1.5 -m-1.5 cursor-help"
            title={kpi.tooltip}
            aria-label={`Définition : ${kpi.tooltip}`}
          >
            <HelpCircle size={12} aria-hidden="true" />
          </button>
        )}
      </div>
      {/* Sprint 1.5bis P0-6 — Hero KPI hierarchy Stripe Atlas / Linear Insights :
          24px → 36px tabular-nums tight leading. Echelle exécutive premium. */}
      <div className="flex items-baseline gap-1.5">
        <span
          className="sol-numeric text-[var(--sol-ink-900)] font-semibold tabular-nums"
          style={{ fontSize: '2.25rem', lineHeight: '1.05', letterSpacing: '-0.01em' }}
        >
          {kpi.value}
        </span>
        {kpi.unit && (
          <span className="text-sm text-[var(--sol-ink-500)] font-medium">{kpi.unit}</span>
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
  error = null,
  onRetry,
  className = '',
}) {
  // Doctrine §5 : "3 KPIs max". Tronquer silencieusement si backend
  // renvoie davantage — c'est un bug backend mais on tient l'invariant frontend.
  const safeKpis = kpis.slice(0, 3);

  // Sprint 1.3bis P0-B (audit CX) : si le briefing backend échoue, on
  // remplace le préambule par un ErrorState explicite plutôt que de
  // masquer silencieusement (page mutilée sans signal user).
  if (error) {
    return (
      <section
        data-testid="sol-narrative-error"
        className={`flex items-start gap-3 p-4 rounded-lg border border-[var(--sol-refuse-line)] bg-[var(--sol-refuse-bg)] ${className}`}
        role="alert"
        aria-live="polite"
      >
        <AlertCircle
          size={18}
          className="text-[var(--sol-refuse-fg)] shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div className="flex-1">
          <p className="text-sm font-semibold text-[var(--sol-refuse-fg)]">Briefing indisponible</p>
          <p className="text-xs text-[var(--sol-ink-700)] mt-1">
            {typeof error === 'string' ? error : 'Erreur de chargement du briefing éditorial.'}
          </p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="mt-2 text-xs font-medium text-[var(--sol-calme-fg)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded px-1 py-0.5 -mx-1"
            >
              Réessayer
            </button>
          )}
        </div>
      </section>
    );
  }

  return (
    <section
      data-testid="sol-narrative"
      // Sprint 1.6bis P0-9 (audit Espaces) : `mt-2` retire 8px du rythme
      // 32px du PageShell space-y-8 (effet 24/32/32). Le parent gère le rhythm.
      className={`flex flex-col gap-5 ${className}`}
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
          // Sprint 1.6bis (audit Espaces P1-1) : gap-3 (12px) désaccordé
          // avec sections gap-4 (16px). Harmonisation 16px standard
          // 3-col Stripe/Linear.
          className="grid grid-cols-1 sm:grid-cols-3 gap-4"
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
