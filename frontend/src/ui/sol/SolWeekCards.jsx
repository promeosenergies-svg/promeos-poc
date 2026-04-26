/**
 * SolWeekCards — week-cards sémantiques §5.
 *
 * Doctrine §5 :
 *   « CETTE SEMAINE CHEZ VOUS »
 *   [À regarder] [À faire] [Bonne nouvelle]
 *
 * Doctrine §4 (densité éditoriale impactante) + §6.1 anti-pattern :
 *   Si backend renvoie <3 cards, on densifie avec un fallback
 *   contextuel ("portefeuille stable cette semaine, prochaine
 *   échéance dans 68 jours") — JAMAIS de "Aucune action"
 *   pleine largeur 600px.
 *
 * Card types canoniques (cf ADR-001 + ADR-002 chantier α) :
 *   - watch     → À regarder (dérive, signal faible, échéance proche)
 *   - todo      → À faire (action urgente, contestation, deadline)
 *   - good_news → Bonne nouvelle (audit passé, économie réalisée)
 *   - drift     → Dérive détectée (anomalie, baseline cassée)
 *
 * Display-only. Tout vient backend events_service.
 */
import { Eye, AlertCircle, Sparkles, TrendingDown, ArrowRight } from 'lucide-react';

const CARD_TYPE_CONFIG = Object.freeze({
  watch: {
    label: 'À regarder',
    Icon: Eye,
    iconCls: 'text-[var(--sol-attention-fg)]',
    bgCls: 'bg-[var(--sol-attention-bg)]',
    borderCls: 'border-[var(--sol-attention-line)]',
  },
  todo: {
    label: 'À faire',
    Icon: AlertCircle,
    iconCls: 'text-[var(--sol-afaire-fg)]',
    bgCls: 'bg-[var(--sol-afaire-bg)]',
    borderCls: 'border-[var(--sol-afaire-line)]',
  },
  good_news: {
    label: 'Bonne nouvelle',
    Icon: Sparkles,
    iconCls: 'text-[var(--sol-succes-fg)]',
    bgCls: 'bg-[var(--sol-succes-bg)]',
    borderCls: 'border-[var(--sol-succes-line)]',
  },
  drift: {
    label: 'Dérive détectée',
    Icon: TrendingDown,
    iconCls: 'text-[var(--sol-refuse-fg)]',
    bgCls: 'bg-[var(--sol-refuse-bg)]',
    borderCls: 'border-[var(--sol-refuse-line)]',
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

function WeekCard({ card, onNavigate }) {
  const cfg = CARD_TYPE_CONFIG[card.type] ?? CARD_TYPE_CONFIG.watch;
  const Icon = cfg.Icon;
  const impact = formatImpact(card.impactEur ?? card.impact_eur);
  const urgency = formatUrgency(card.urgencyDays ?? card.urgency_days);
  const ctaPath = card.ctaPath ?? card.cta_path ?? card.cta;
  const ctaLabel = card.ctaLabel ?? card.cta_label ?? 'Ouvrir';

  const Wrapper = ctaPath ? 'button' : 'div';
  const wrapperProps = ctaPath
    ? {
        type: 'button',
        onClick: () => onNavigate?.(ctaPath),
        className: `text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500`,
      }
    : {};

  return (
    <Wrapper data-testid={`sol-week-card-${card.type}`} {...wrapperProps}>
      <article
        className={`flex flex-col gap-2 p-4 rounded-lg border ${cfg.bgCls} ${cfg.borderCls} h-full sol-card transition-colors hover:brightness-[0.98]`}
        data-tone={
          card.type === 'good_news'
            ? 'succes'
            : card.type === 'drift'
              ? 'refuse'
              : card.type === 'todo'
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
              {cfg.label}
            </span>
          </div>
          {urgency && (
            <span className="text-[10px] text-[var(--sol-ink-500)] font-medium">{urgency}</span>
          )}
        </header>
        <h3 className="text-sm font-semibold text-[var(--sol-ink-900)] leading-tight">
          {card.title}
        </h3>
        {card.body && (
          <p className="text-xs text-[var(--sol-ink-700)] leading-relaxed line-clamp-3">
            {card.body}
          </p>
        )}
        {(impact || ctaPath) && (
          <footer className="flex items-center justify-between gap-2 mt-1">
            {impact && (
              <span className="text-xs font-semibold text-[var(--sol-ink-900)] sol-numeric">
                {impact}
              </span>
            )}
            {ctaPath && (
              <span className="inline-flex items-center gap-0.5 text-xs font-medium text-[var(--sol-ink-700)]">
                {ctaLabel}
                <ArrowRight size={11} aria-hidden="true" />
              </span>
            )}
          </footer>
        )}
      </article>
    </Wrapper>
  );
}

/**
 * Densification §4 : si backend renvoie <3 cards, on rend ce qu'on a
 * + on remplit avec une card "Bonne nouvelle" générique densifiée
 * via le `fallbackBody` fourni par le parent (qui le calcule backend).
 *
 * Si fallbackBody absent, on insère une card silence éditorial
 * minimal — JAMAIS un empty state pleine largeur.
 */
function applyFallbackDensification(cards, fallbackBody) {
  if (cards.length >= 3) return cards.slice(0, 3);
  const filled = [...cards];
  while (filled.length < 3) {
    filled.push({
      type: 'good_news',
      title: 'Patrimoine stable cette semaine',
      body: fallbackBody || 'Aucun signal critique détecté — votre patrimoine est sous contrôle.',
      _fallback: true,
    });
  }
  return filled;
}

export default function SolWeekCards({ cards = [], fallbackBody, onNavigate, className = '' }) {
  const displayedCards = applyFallbackDensification(cards, fallbackBody);

  return (
    <section
      data-testid="sol-week-cards"
      className={`flex flex-col gap-3 ${className}`}
      aria-label="Cette semaine chez vous"
    >
      <header>
        <h2 className="sol-page-kicker">Cette semaine chez vous</h2>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" role="list">
        {displayedCards.map((card, idx) => (
          <WeekCard key={card.id || idx} card={card} onNavigate={onNavigate} />
        ))}
      </div>
    </section>
  );
}
