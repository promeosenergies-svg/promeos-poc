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
import { useEffect, useMemo, useRef, useState } from 'react';
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
  Info,
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
  // ét12e (audit CFO P0 #3) : popover drill-down methodology. Hook AVANT
  // l'early return pour respecter l'ordre des hooks React.
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  // Vague E ét16 (audit EM #3 a11y WCAG) : refs pour focus retour bouton
  // après close popover (norme WCAG 2.4.3 Focus Order + 2.1.2 No Trap).
  const methodologyButtonRef = useRef(null);

  // Vague E ét16 (audit EM #3 a11y) : Escape close popover + focus retour.
  useEffect(() => {
    if (!methodologyOpen) return;
    const handler = (e) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        setMethodologyOpen(false);
        methodologyButtonRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [methodologyOpen]);

  if (!isValid) return null;

  const severityCfg = SEVERITY_CONFIG[event.severity] ?? SEVERITY_CONFIG.watch;
  const Icon = severityCfg.Icon;
  const impactValue = formatImpactValue(event.impact?.value, event.impact?.unit);
  const periodLabel = PERIOD_LABELS[event.impact?.period] ?? '';
  const freshness = FRESHNESS_LABELS[event.source?.freshness_status] ?? null;
  const confidenceLabel = CONFIDENCE_LABELS[event.source?.confidence] ?? null;
  const lastUpdated = formatRelativeTime(event.source?.last_updated_at);
  const methodology = event.source?.methodology;
  const mitigation = event.impact?.mitigation;
  const ownerRole = event.action?.owner_role;
  const route = event.action?.route;

  // Mitigation phrase : « 12 k€ CAPEX · payback 8 mois · NPV 145 k€ »
  // Vague E ét16 (audit CFO P0 #3 28/04/2026) : afficher AU MOINS un
  // placeholder « payback à étudier » pour les events sans mitigation
  // chiffrée. Une carte sans payback = CFO décroche du Cockpit matinal.
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
  // Fallback CFO : si aucune mitigation chiffrée mais event a un impact €
  // > 0, afficher « Mitigation à qualifier » plutôt que de masquer le
  // bandeau (signal au CFO « il faut creuser », pas « rien à faire »).
  const hasFinancialImpact = event.impact?.unit === '€' && (event.impact?.value ?? 0) > 0;
  let mitigationLine = mitigationParts.join(' · ');
  let mitigationVariant = 'chiffree'; // chiffree | aQualifier | none
  if (!mitigationLine && hasFinancialImpact && event.severity !== 'info') {
    mitigationLine = 'Mitigation à qualifier — données financières insuffisantes';
    mitigationVariant = 'aQualifier';
  } else if (!mitigationLine) {
    mitigationVariant = 'none';
  }

  // Vague C ét12d (audit Architecture P0 #1 + UX P0-A) : `<button><article>`
  // est invalide HTML5 (button ne peut pas contenir d'éléments interactifs
  // ni d'éléments avec rôle implicite comme <article>). On utilise un
  // unique <article role="button"> + handlers clavier (Enter/Espace) pour
  // conserver la sémantique "événement" sans casser l'accessibilité.
  const interactiveProps = route
    ? {
        role: 'button',
        tabIndex: 0,
        onClick: () => onNavigate?.(route),
        onKeyDown: (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onNavigate?.(route);
          }
        },
        className:
          'cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]',
      }
    : {};

  // Vague C ét12d (audit EM P0-2 + CFO P0) : afficher le nombre de sites
  // concernés (granularité actionnable terrain).
  const siteIds = event.linked_assets?.site_ids || [];
  const siteCount = siteIds.length;

  // Vague C ét12d (UX P0-C) : aria-label agrégé pour lecteurs d'écran
  // (sinon AT lit chaque micro-zone séparément = bruit sémantique).
  const ariaLabelParts = [
    severityCfg.label,
    event.title,
    impactValue ? `impact ${impactValue}${periodLabel}` : null,
    ownerRole ? `suivi ${ownerRole}` : null,
    route ? `action ${event.action.label}` : null,
  ].filter(Boolean);
  const ariaLabel = ariaLabelParts.join(', ');

  return (
    <article
      data-testid={`sol-event-card-${event.event_type}`}
      data-tone={severityCfg.tone}
      data-severity={event.severity}
      aria-label={route ? ariaLabel : undefined}
      className={`flex flex-col gap-2.5 rounded-lg border h-full sol-card transition-colors hover:brightness-[0.98] ${
        compact ? 'p-4' : 'p-5'
      } ${interactiveProps.className || ''}`}
      style={severityCfg.style}
      {...interactiveProps}
    >
      {/* ── Header : severity badge + freshness ── */}
      <header className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Icon size={13} className={severityCfg.iconCls} aria-hidden="true" />
          <span
            className={`text-xs font-mono uppercase tracking-wider font-semibold truncate ${severityCfg.iconCls}`}
          >
            {severityCfg.label}
          </span>
        </div>
        {freshness && (
          <span
            className="text-xs px-1.5 py-0.5 rounded-full font-medium shrink-0"
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
          {periodLabel && <span className="text-xs text-[var(--sol-ink-700)]">{periodLabel}</span>}
        </div>
      )}

      {/* ── Mitigation (CFO arbitrage CAPEX/payback/NPV) ──
          Vague C ét12e (audit CFO P0 #2) : bandeau dédié 14px sur fond
          --sol-calme-bg pour visibilité présentation Teams 1080p.
          Vague E ét16 (audit CFO P0 #3 28/04/2026) : variant `aQualifier`
          quand impact € > 0 mais aucune mitigation chiffrée — italic gris
          pour signaler « il faut creuser » sans crier comme une vraie
          mitigation chiffrée. Évite le silence CFO qui décroche. */}
      {mitigationLine && (
        <div
          className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 ${
            mitigationVariant === 'aQualifier'
              ? 'text-xs italic text-[var(--sol-ink-700)]'
              : 'text-sm font-medium text-[var(--sol-ink-900)]'
          }`}
          style={{
            background:
              mitigationVariant === 'aQualifier'
                ? 'var(--sol-attention-bg)'
                : 'var(--sol-calme-bg)',
          }}
        >
          <Wallet
            size={mitigationVariant === 'aQualifier' ? 12 : 14}
            className={
              mitigationVariant === 'aQualifier'
                ? 'text-[var(--sol-attention-fg)] shrink-0'
                : 'text-[var(--sol-calme-fg)] shrink-0'
            }
            aria-hidden="true"
          />
          <span className={mitigationVariant === 'aQualifier' ? '' : 'sol-numeric'}>
            {mitigationLine}
          </span>
        </div>
      )}

      {/* ── Footer : source + owner + CTA ── */}
      <footer className="flex flex-col gap-1.5 mt-auto pt-2 border-t border-[var(--sol-ink-100)]">
        {/* Ligne 1 : source + confidence + horodatage + drill-down methodology */}
        <div className="flex items-center justify-between gap-2 text-xs text-[var(--sol-ink-700)]">
          <div className="flex items-center gap-1 min-w-0">
            <ShieldCheck size={11} aria-hidden="true" />
            <span className="truncate">
              Source <strong className="text-[var(--sol-ink-700)]">{event.source.system}</strong>
              {confidenceLabel && (
                <>
                  {' · '}
                  <span title={`Confiance : ${event.source.confidence}`}>{confidenceLabel}</span>
                </>
              )}
            </span>
            {methodology && (
              <button
                ref={methodologyButtonRef}
                type="button"
                id={`sol-event-${event.id}-methodology-btn`}
                onClick={(e) => {
                  e.stopPropagation();
                  setMethodologyOpen((o) => !o);
                }}
                onKeyDown={(e) => e.stopPropagation()}
                aria-label="Voir la méthodologie de calcul"
                aria-expanded={methodologyOpen}
                aria-controls={`sol-event-${event.id}-methodology`}
                title="Voir la méthodologie de calcul (Échap pour fermer)"
                className="ml-1 inline-flex items-center justify-center w-6 h-6 rounded-full hover:bg-[var(--sol-ink-100)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)]"
              >
                <Info size={14} className="text-[var(--sol-calme-fg)]" aria-hidden="true" />
              </button>
            )}
          </div>
          {lastUpdated && (
            <span className="flex items-center gap-0.5 shrink-0">
              <Clock size={11} aria-hidden="true" />
              {lastUpdated}
            </span>
          )}
        </div>

        {/* Popover methodology drill-down (audit CFO P0 #3 + EM ét16 a11y) */}
        {methodology && methodologyOpen && (
          <div
            id={`sol-event-${event.id}-methodology`}
            role="region"
            aria-label="Méthodologie de calcul"
            className="text-xs text-[var(--sol-ink-700)] rounded-md p-2 border border-[var(--sol-ink-200)]"
            style={{ background: 'var(--sol-ink-50)' }}
          >
            <p className="leading-relaxed">{methodology}</p>
          </div>
        )}

        {/* Ligne 2 : owner role + scope sites + CTA */}
        {(ownerRole || siteCount > 0 || route) && (
          <div className="flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-[var(--sol-ink-700)] min-w-0">
              {ownerRole && (
                <span className="flex items-center gap-1">
                  <User size={11} aria-hidden="true" />
                  Suivi <strong className="text-[var(--sol-ink-700)]">{ownerRole}</strong>
                </span>
              )}
              {siteCount > 0 && (
                <span
                  className="text-[var(--sol-ink-700)] font-medium"
                  title={`${siteCount} site${siteCount > 1 ? 's' : ''} concerné${siteCount > 1 ? 's' : ''}`}
                >
                  {siteCount} site{siteCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
            {route && (
              <span className="inline-flex items-center gap-0.5 text-xs font-medium text-[var(--sol-ink-700)] shrink-0">
                {event.action.label}
                <ArrowRight size={11} aria-hidden="true" />
              </span>
            )}
          </div>
        )}
      </footer>
    </article>
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
