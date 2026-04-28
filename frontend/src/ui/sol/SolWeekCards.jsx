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
import { useMemo } from 'react';
import { Eye, AlertCircle, Sparkles, TrendingDown, ArrowRight } from 'lucide-react';

/**
 * Sprint 1.4bis P0 (audit UI/Visual) : Tailwind v4 ne compile pas les classes
 * arbitraires `bg-[var(--sol-*-bg)]` + `border-[var(--sol-*-line)]` à la
 * volée → bordures fantômes en runtime, palette warm Sol invisible.
 *
 * Workaround : `style={{ background, borderColor }}` inline qui consomme
 * directement les CSS variables tokens.css. Performance équivalente,
 * runtime garanti.
 */
const CARD_TYPE_CONFIG = Object.freeze({
  watch: {
    label: 'À regarder',
    Icon: Eye,
    iconCls: 'text-[var(--sol-attention-fg)]',
    style: {
      background: 'var(--sol-attention-bg)',
      borderColor: 'var(--sol-attention-line)',
    },
  },
  todo: {
    label: 'À faire',
    Icon: AlertCircle,
    iconCls: 'text-[var(--sol-afaire-fg)]',
    style: {
      background: 'var(--sol-afaire-bg)',
      borderColor: 'var(--sol-afaire-line)',
    },
  },
  good_news: {
    label: 'Bonne nouvelle',
    Icon: Sparkles,
    iconCls: 'text-[var(--sol-succes-fg)]',
    style: {
      background: 'var(--sol-succes-bg)',
      borderColor: 'var(--sol-succes-line)',
    },
  },
  drift: {
    label: 'Dérive détectée',
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
        // Sprint 1.5bis P0-5 — focus ring migré token calme Sol (audit Visual 26/04).
        className: `text-left w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sol-calme-fg)] rounded-lg`,
      }
    : {};

  return (
    <Wrapper data-testid={`sol-week-card-${card.type}`} role="listitem" {...wrapperProps}>
      <article
        className="flex flex-col gap-2.5 p-5 rounded-lg border h-full sol-card transition-colors hover:brightness-[0.98]"
        style={cfg.style}
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
            <span className="text-xs text-[var(--sol-ink-700)] font-medium">{urgency}</span>
          )}
        </header>
        <h3 className="text-sm font-semibold text-[var(--sol-ink-900)] leading-snug">
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
 * Densification §4 : si backend renvoie <3 cards, on remplit AVEC DES
 * TITRES DISTINCTS et un TYPE COHÉRENT avec le ton de la narrative
 * principale (audit Sprint 1.1 + fin S1).
 *
 * Sprint 1.3bis P0-D : `tone` reflète la narrative_tone backend
 * (positive / neutral / tension / critical). Si la narrative dit
 * "3 sites en dérive 26 k€", afficher "Aucune dérive détectée" en
 * good_news = contradiction éditoriale → on type le fallback en watch
 * neutre ("À surveiller cette semaine") plutôt qu'en good_news menteur.
 *
 * 4 catalogues distincts par tone, sélection séquentielle sans
 * répétition de type intra-page.
 *
 * JAMAIS un empty state pleine largeur (anti-pattern §6.1).
 */
const FALLBACK_CATALOGS = Object.freeze({
  positive: [
    { type: 'good_news', title: 'Patrimoine stable cette semaine' },
    { type: 'good_news', title: 'Aucune dérive détectée' },
    { type: 'good_news', title: 'Conformité tenue' },
    { type: 'good_news', title: 'Données à jour' },
  ],
  neutral: [
    { type: 'watch', title: 'Suivre la trajectoire 2030' },
    { type: 'good_news', title: 'Données à jour' },
    { type: 'watch', title: 'Préparer le prochain CODIR' },
    { type: 'good_news', title: 'Activité régulière' },
  ],
  // Tone tension/critical : pas de "Bonne nouvelle" générique pour
  // éviter contradiction avec narrative négative.
  tension: [
    { type: 'watch', title: 'Patrimoine sous tension' },
    { type: 'watch', title: 'Vigilance trajectoire 2030' },
    { type: 'watch', title: 'Prochaine échéance à anticiper' },
    { type: 'watch', title: 'Anticiper l’échéance trimestrielle' },
  ],
  critical: [
    { type: 'watch', title: 'Patrimoine en alerte' },
    { type: 'watch', title: 'Provisionnement à anticiper' },
    { type: 'watch', title: 'Plan de remédiation prioritaire' },
  ],
});

function applyFallbackDensification(cards, fallbackBody, tone = 'positive') {
  if (cards.length >= 3) return cards.slice(0, 3);
  const filled = [...cards];
  const catalog = FALLBACK_CATALOGS[tone] ?? FALLBACK_CATALOGS.positive;
  // Pour tone tension/critical, on ne saute pas par type (toutes les
  // variantes sont watch). Pour positive/neutral on déduplique.
  const dedupByType = tone === 'positive' || tone === 'neutral';
  const usedTypes = new Set(filled.map((c) => c.type));
  let idx = 0;
  while (filled.length < 3 && idx < catalog.length) {
    const variant = catalog[idx];
    idx += 1;
    if (dedupByType && usedTypes.has(variant.type) && idx < catalog.length) {
      continue;
    }
    filled.push({
      ...variant,
      body: fallbackBody || 'Aucun signal critique détecté — votre patrimoine est sous contrôle.',
      _fallback: true,
    });
    usedTypes.add(variant.type);
  }
  return filled;
}

export default function SolWeekCards({
  cards = [],
  fallbackBody,
  tone = 'positive',
  onNavigate,
  className = '',
}) {
  // Sprint 1.4bis /simplify Efficiency P1 : memoize la densification —
  // évite ré-exécution algorithme O(n×m) à chaque render parent.
  const displayedCards = useMemo(
    () => applyFallbackDensification(cards, fallbackBody, tone),
    [cards, fallbackBody, tone]
  );

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
