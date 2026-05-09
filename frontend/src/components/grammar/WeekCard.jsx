/**
 * grammar/WeekCard — Wrapper carte hebdomadaire typee grammaire Sol §5.
 *
 * Rend UNE SEULE carte parmi les 4 variantes doctrinales :
 *   - 'a-regarder'    → watch  (derive, signal faible, echeance proche)
 *   - 'a-faire'       → todo   (action urgente, contestation, deadline)
 *   - 'bonne-nouvelle'→ good_news (audit passe, economie realisee)
 *   - 'derive'        → drift  (anomalie, baseline cassee)
 *
 * Delegue vers la WeekCard interne de SolWeekCards en construisant
 * un objet card compatible avec le contrat backend events_service.
 *
 * Tonalite par variante (tokens CSS --sol-*) :
 *   a-regarder    : var(--sol-attention-*)
 *   a-faire       : var(--sol-afaire-*)
 *   bonne-nouvelle: var(--sol-succes-*)
 *   derive        : var(--sol-refuse-*)
 *
 * Display-only — zero calcul metier.
 *
 * @param {Object} props
 * @param {'a-regarder'|'a-faire'|'bonne-nouvelle'|'derive'} props.variant - Variante typee
 * @param {string} [props.kicker] - Kicker courte (optionnel)
 * @param {string} props.titre - Titre de la carte
 * @param {string} [props.resume] - Corps de la carte (1-3 lignes)
 * @param {{label:string, href:string}} [props.cta] - CTA optionnel
 * @param {number} [props.impact] - Impact financier en euros (signe)
 * @param {number} [props.echeance] - Urgence en jours (0=aujourd'hui, negatif=en retard)
 * @param {string} [props.className=''] - Classes CSS supplementaires
 */
import { Eye, AlertCircle, Sparkles, TrendingDown, ArrowRight } from 'lucide-react';

const VARIANT_MAP = Object.freeze({
  'a-regarder': {
    type: 'watch',
    label: 'A regarder',
    Icon: Eye,
    iconCls: 'text-[var(--sol-attention-fg)]',
    style: {
      background: 'var(--sol-attention-bg)',
      borderColor: 'var(--sol-attention-line)',
    },
  },
  'a-faire': {
    type: 'todo',
    label: 'A faire',
    Icon: AlertCircle,
    iconCls: 'text-[var(--sol-afaire-fg)]',
    style: {
      background: 'var(--sol-afaire-bg)',
      borderColor: 'var(--sol-afaire-line)',
    },
  },
  'bonne-nouvelle': {
    type: 'good_news',
    label: 'Bonne nouvelle',
    Icon: Sparkles,
    iconCls: 'text-[var(--sol-succes-fg)]',
    style: {
      background: 'var(--sol-succes-bg)',
      borderColor: 'var(--sol-succes-line)',
    },
  },
  derive: {
    type: 'drift',
    label: 'Derive detectee',
    Icon: TrendingDown,
    iconCls: 'text-[var(--sol-refuse-fg)]',
    style: {
      background: 'var(--sol-refuse-bg)',
      borderColor: 'var(--sol-refuse-line)',
    },
  },
});

function formatImpact(impactEur) {
  if (impactEur == null) return null;
  const abs = Math.abs(impactEur);
  if (abs >= 1000) return `${Math.round(impactEur / 100) / 10} k€`;
  return `${Math.round(impactEur)} €`;
}

function formatUrgency(urgencyDays) {
  if (urgencyDays == null) return null;
  if (urgencyDays === 0) return "aujourd'hui";
  if (urgencyDays === 1) return 'demain';
  if (urgencyDays < 0) return `J+${-urgencyDays}`;
  if (urgencyDays < 7) return `dans ${urgencyDays} j`;
  if (urgencyDays < 90) return `dans ${Math.round(urgencyDays / 7)} sem`;
  return `dans ${Math.round(urgencyDays / 30)} mois`;
}

export default function WeekCard({
  variant = 'a-regarder',
  kicker,
  titre,
  resume,
  cta,
  impact,
  echeance,
  className = '',
}) {
  const cfg = VARIANT_MAP[variant] ?? VARIANT_MAP['a-regarder'];
  const Icon = cfg.Icon;
  const impactFormatted = formatImpact(impact);
  const urgencyFormatted = formatUrgency(echeance);
  const hasCta = Boolean(cta?.href);

  return (
    <div data-testid={`week-card-${cfg.type}`} data-variant={variant} className={className}>
      <article
        className="flex flex-col gap-2.5 p-5 rounded-lg border h-full sol-card transition-colors hover:brightness-[0.98]"
        style={cfg.style}
        data-tone={
          cfg.type === 'good_news'
            ? 'succes'
            : cfg.type === 'drift'
              ? 'refuse'
              : cfg.type === 'todo'
                ? 'afaire'
                : 'attention'
        }
      >
        <header className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5">
            <Icon size={13} className={cfg.iconCls} aria-hidden="true" />
            <span
              className={`text-[10px] font-mono uppercase tracking-wider font-semibold ${cfg.iconCls}`}
            >
              {kicker || cfg.label}
            </span>
          </div>
          {urgencyFormatted && (
            <span className="text-xs text-[var(--sol-ink-700)] font-medium">
              {urgencyFormatted}
            </span>
          )}
        </header>

        {titre && (
          <h3 className="text-sm font-semibold text-[var(--sol-ink-900)] leading-snug">{titre}</h3>
        )}

        {resume && (
          <p className="text-xs text-[var(--sol-ink-700)] leading-relaxed line-clamp-3">{resume}</p>
        )}

        {(impactFormatted || hasCta) && (
          <footer className="flex items-center justify-between gap-2 mt-1">
            {impactFormatted && (
              <span className="text-xs font-semibold text-[var(--sol-ink-900)] sol-numeric">
                {impactFormatted}
              </span>
            )}
            {hasCta && (
              <a
                href={cta.href}
                className="inline-flex items-center gap-0.5 text-xs font-medium text-[var(--sol-ink-700)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded"
              >
                {cta.label || 'Ouvrir'}
                <ArrowRight size={11} aria-hidden="true" />
              </a>
            )}
          </footer>
        )}
      </article>
    </div>
  );
}
