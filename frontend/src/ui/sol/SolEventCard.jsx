/**
 * SolEventCard — rendu natif §10 SolEventCard avec visibilité complète.
 *
 * Sprint 2 Vague C ét12c (27/04/2026). Résout le compromis Marie audit
 * Vague C ét11 : « je ne peux pas savoir d'où vient cette alerte ni à
 * qui je dois la déléguer ». Affiche les 6 champs doctrine §10 dans
 * l'UI :
 *   - title + narrative (récit éditorial §5)
 *   - impact.value + unit + period (chiffre clé)
 *   - mitigation (CAPEX / payback / NPV) si présent — arbitrage CFO
 *   - source.system + confidence + freshness_status (contrat data §7.1)
 *   - action.label + route + owner_role (qui fait quoi)
 *
 * Différence avec SolWeekCards (rétro-compat) : les week-cards condensent
 * en 3 cases sémantiques (À regarder / À faire / Bonne nouvelle) sans
 * révéler la source ni le rôle responsable. SolEventCard expose tout.
 *
 * Display-only (doctrine §8.1) — backend pousse le payload SolEventCard
 * via `/pages/{key}/briefing` champ `events[]`.
 *
 * Props : `event` = objet SolEventCard JSON (cf eventTypes.js isValidEvent),
 * `onNavigate(route)` callback CTA, `compact` (bool) pour densifier.
 */
import { useMemo } from 'react';
import {
  AlertTriangle,
  AlertCircle,
  Eye,
  Sparkles,
  ArrowRight,
  Clock,
  ShieldCheck,
  Wallet,
  User,
} from 'lucide-react';
import {
  EVENT_FRESHNESS_STATUSES,
  EVENT_CONFIDENCES,
  isValidEvent,
} from '../../domain/events/eventTypes';
// Sprint 2 Vague C ét12c /code-review P2 : réutilise utils/format.js (locale
// FR `toLocaleString` + grouping correct) plutôt que dupliquer le format.
import { fmtEur, fmtKwh, fmtMwh, fmtPct } from '../../utils/format';

/**
 * Mapping severity → palette tokens Sol §3 + icône.
 *
 * Aligné avec SolWeekCards CARD_TYPE_CONFIG mais piloté par severity native
 * (pas via SEVERITY_TO_CARD_TYPE) car ici on garde 4 niveaux distincts
 * (info / watch / warning / critical) — pas de remap vers 3 buckets.
 */
const SEVERITY_CONFIG = Object.freeze({
  critical: {
    label: 'Critique',
    Icon: AlertTriangle,
    iconCls: 'text-[var(--sol-refuse-fg)]',
    style: {
      background: 'var(--sol-refuse-bg)',
      borderColor: 'var(--sol-refuse-line)',
    },
    tone: 'refuse',
  },
  warning: {
    label: 'À faire',
    Icon: AlertCircle,
    iconCls: 'text-[var(--sol-afaire-fg)]',
    style: {
      background: 'var(--sol-afaire-bg)',
      borderColor: 'var(--sol-afaire-line)',
    },
    tone: 'afaire',
  },
  watch: {
    label: 'À regarder',
    Icon: Eye,
    iconCls: 'text-[var(--sol-attention-fg)]',
    style: {
      background: 'var(--sol-attention-bg)',
      borderColor: 'var(--sol-attention-line)',
    },
    tone: 'attention',
  },
  info: {
    label: 'Bonne nouvelle',
    Icon: Sparkles,
    iconCls: 'text-[var(--sol-succes-fg)]',
    style: {
      background: 'var(--sol-succes-bg)',
      borderColor: 'var(--sol-succes-line)',
    },
    tone: 'succes',
  },
});

/** Mapping freshness_status → libellé FR + tone visuel (doctrine §7.2). */
const FRESHNESS_LABELS = Object.freeze({
  fresh: null, // pas de badge si frais (cas par défaut, évite bruit)
  stale: { label: 'Données anciennes', tone: 'attention' },
  estimated: { label: 'Estimé', tone: 'attention' },
  incomplete: { label: 'Données partielles', tone: 'attention' },
  demo: { label: 'Démo', tone: 'calme' },
});

/** Mapping confidence → libellé FR (doctrine §7.1 contrat data). */
const CONFIDENCE_LABELS = Object.freeze({
  high: 'fiabilité élevée',
  medium: 'fiabilité moyenne',
  low: 'fiabilité limitée',
});

/** Mapping unit → format affichage. Délégué à utils/format.js pour locale
 * FR + grouping cohérent reste de l'app. Renvoie null si value absent
 * (§6 P13 « pas de KPI magique ») — le caller gère le conditional render.
 *
 * `days` n'a pas d'équivalent dans format.js → géré inline (singulier/pluriel).
 */
function formatImpactValue(value, unit) {
  if (value == null) return null;
  if (unit === '€') return fmtEur(value);
  if (unit === '%') return fmtPct(value, false, 1); // value 0-100, 1 décimale
  if (unit === 'kWh') return fmtKwh(value);
  if (unit === 'MWh') return fmtMwh(value);
  if (unit === 'days') return value === 1 ? '1 jour' : `${Math.round(value)} jours`;
  return `${value} ${unit}`;
}

const PERIOD_LABELS = Object.freeze({
  day: '/jour',
  week: '/semaine',
  month: '/mois',
  year: '/an',
  contract: '/contrat',
  deadline: 'à échéance',
});

/** Format ISO datetime → "il y a X" lisible non-sachant. */
function formatRelativeTime(isoString) {
  if (!isoString) return null;
  const then = new Date(isoString).getTime();
  if (Number.isNaN(then)) return null;
  const diffMs = Date.now() - then;
  if (diffMs < 0) return "à l'instant";
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "à l'instant";
  if (minutes < 60) return `il y a ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `il y a ${hours} h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'hier';
  if (days < 30) return `il y a ${days} j`;
  const months = Math.floor(days / 30);
  if (months === 1) return 'le mois dernier';
  return `il y a ${months} mois`;
}

export default function SolEventCard({ event, onNavigate, compact = false }) {
  // Garde-fou doctrine §6 P13 : si payload invalide, on n'affiche rien
  // plutôt qu'un crash (cohérent avec WeekCard tolérant). En dev, le hook
  // useMemo isole le coût de validation (1 fois par event).
  const isValid = useMemo(() => isValidEvent(event), [event]);
  if (!isValid) return null;

  const severityCfg = SEVERITY_CONFIG[event.severity] ?? SEVERITY_CONFIG.watch;
  const Icon = severityCfg.Icon;
  const impactValue = formatImpactValue(event.impact?.value, event.impact?.unit);
  const periodLabel = PERIOD_LABELS[event.impact?.period] ?? '';
  const freshness = FRESHNESS_LABELS[event.source?.freshness_status] ?? null;
  const confidenceLabel = CONFIDENCE_LABELS[event.source?.confidence] ?? null;
  const lastUpdated = formatRelativeTime(event.source?.last_updated_at);
  const mitigation = event.impact?.mitigation;
  const ownerRole = event.action?.owner_role;
  const route = event.action?.route;

  // Mitigation phrase : « 12 k€ CAPEX, payback 8 mois, NPV 145 k€ »
  const mitigationParts = [];
  if (mitigation?.capex_eur != null) {
    mitigationParts.push(`${formatImpactValue(mitigation.capex_eur, '€')} CAPEX`);
  }
  if (mitigation?.payback_months != null) {
    const m = mitigation.payback_months;
    mitigationParts.push(m === 1 ? 'payback 1 mois' : `payback ${m} mois`);
  }
  if (mitigation?.npv_eur != null) {
    mitigationParts.push(`NPV ${formatImpactValue(mitigation.npv_eur, '€')}`);
  }
  const mitigationLine = mitigationParts.join(' · ');

  const Wrapper = route ? 'button' : 'article';
  const wrapperProps = route
    ? {
        type: 'button',
        onClick: () => onNavigate?.(route),
        className:
          'text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded-lg',
      }
    : {};

  return (
    <Wrapper data-testid={`sol-event-card-${event.event_type}`} {...wrapperProps}>
      <article
        className={`flex flex-col gap-2.5 rounded-lg border h-full sol-card transition-colors hover:brightness-[0.98] ${
          compact ? 'p-4' : 'p-5'
        }`}
        style={severityCfg.style}
        data-tone={severityCfg.tone}
        data-severity={event.severity}
      >
        {/* ── Header : severity badge + freshness ── */}
        <header className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <Icon size={13} className={severityCfg.iconCls} aria-hidden="true" />
            <span
              className={`text-[10px] font-mono uppercase tracking-wider font-semibold ${severityCfg.iconCls}`}
            >
              {severityCfg.label}
            </span>
          </div>
          {freshness && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
              style={{
                background: `var(--sol-${freshness.tone}-bg)`,
                color: `var(--sol-${freshness.tone}-fg)`,
              }}
              title={`Statut donnée : ${freshness.label}`}
            >
              {freshness.label}
            </span>
          )}
        </header>

        {/* ── Title + narrative ── */}
        <h3 className="text-sm font-semibold text-[var(--sol-ink-900)] leading-snug">
          {event.title}
        </h3>
        {event.narrative && (
          <p className="text-xs text-[var(--sol-ink-700)] leading-relaxed line-clamp-3">
            {event.narrative}
          </p>
        )}

        {/* ── Impact value + period ── */}
        {impactValue && (
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-base font-semibold text-[var(--sol-ink-900)] sol-numeric">
              {impactValue}
            </span>
            {periodLabel && (
              <span className="text-[11px] text-[var(--sol-ink-500)]">{periodLabel}</span>
            )}
          </div>
        )}

        {/* ── Mitigation (CFO arbitrage CAPEX/payback/NPV) ── */}
        {mitigationLine && (
          <div className="flex items-center gap-1.5 text-[11px] text-[var(--sol-ink-700)]">
            <Wallet size={11} className="text-[var(--sol-ink-500)]" aria-hidden="true" />
            <span>{mitigationLine}</span>
          </div>
        )}

        {/* ── Footer : source + owner + CTA ── */}
        <footer className="flex flex-col gap-1.5 mt-auto pt-2 border-t border-[var(--sol-ink-100)]">
          {/* Ligne 1 : source + confidence + horodatage */}
          <div className="flex items-center justify-between gap-2 text-[10px] text-[var(--sol-ink-500)]">
            <div className="flex items-center gap-1 min-w-0">
              <ShieldCheck size={10} aria-hidden="true" />
              <span className="truncate">
                Source <strong className="text-[var(--sol-ink-700)]">{event.source.system}</strong>
                {confidenceLabel && (
                  <>
                    {' · '}
                    <span title={`Confiance : ${event.source.confidence}`}>{confidenceLabel}</span>
                  </>
                )}
              </span>
            </div>
            {lastUpdated && (
              <span className="flex items-center gap-0.5 shrink-0">
                <Clock size={10} aria-hidden="true" />
                {lastUpdated}
              </span>
            )}
          </div>

          {/* Ligne 2 : owner role + CTA */}
          {(ownerRole || route) && (
            <div className="flex items-center justify-between gap-2">
              {ownerRole ? (
                <span className="flex items-center gap-1 text-[10px] text-[var(--sol-ink-500)]">
                  <User size={10} aria-hidden="true" />
                  Suivi <strong className="text-[var(--sol-ink-700)]">{ownerRole}</strong>
                </span>
              ) : (
                <span />
              )}
              {route && (
                <span className="inline-flex items-center gap-0.5 text-xs font-medium text-[var(--sol-ink-700)]">
                  {event.action.label}
                  <ArrowRight size={11} aria-hidden="true" />
                </span>
              )}
            </div>
          )}
        </footer>
      </article>
    </Wrapper>
  );
}

/**
 * SolEventStream — wrapper grille pour rendre N événements (default top 3).
 *
 * À utiliser sur les pages-pilotes (Cockpit, Bill-Intel, Conformité) qui
 * veulent exposer la pile §10 native plutôt que le condensé week-cards.
 *
 * Props :
 *   - events : array<SolEventCard JSON>
 *   - max    : nombre max à rendre (défaut 3)
 *   - onNavigate : callback CTA
 *   - title  : surtitre §5 (défaut "Événements détaillés")
 *   - className
 */
export function SolEventStream({
  events = [],
  max = 3,
  onNavigate,
  title = 'Événements détaillés',
  className = '',
}) {
  const visible = useMemo(() => (events ?? []).slice(0, max), [events, max]);
  if (visible.length === 0) return null;

  return (
    <section
      data-testid="sol-event-stream"
      className={`flex flex-col gap-3 ${className}`}
      aria-label={title}
    >
      <header>
        <h2 className="sol-page-kicker">{title}</h2>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" role="list">
        {visible.map((event, idx) => (
          <div role="listitem" key={event.id || idx}>
            <SolEventCard event={event} onNavigate={onNavigate} />
          </div>
        ))}
      </div>
    </section>
  );
}

export { EVENT_FRESHNESS_STATUSES, EVENT_CONFIDENCES };
