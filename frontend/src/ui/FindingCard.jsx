/**
 * PROMEOS — FindingCard (Sprint CX 2, item B)
 *
 * Composant unifié pour afficher un "finding" (insight, anomalie, alerte,
 * recommandation, obligation réglementaire) avec une structure cohérente :
 *   - severity + priorité (visuellement dominants)
 *   - title + description optionnelle
 *   - impact (€, kWh, CO₂) affiché avec format unifié
 *   - deadline (J-X, J+X, "Dépassé")
 *   - confidence (0-1, badge optionnel)
 *   - CTA actionLabel + onAction
 *   - onClick sur toute la card (navigation)
 *
 * Remplace progressivement les patterns disparates identifiés par l'audit :
 *   RecommendationsCard, UsageAnomaliesCard, AlertesPrioritaires, AuditSmeCard,
 *   InsightDrawer header, PriorityActions, etc.
 *
 * Convention severity : 'critical' | 'high' | 'medium' | 'low'
 * Convention category : 'compliance' | 'billing' | 'consumption' | 'purchase' | 'flex' | 'audit' | 'insight'
 */

import { ChevronRight, AlertTriangle, Receipt, Zap, ShoppingCart, FileText, Activity, Lightbulb } from 'lucide-react';
import { fmtEur } from '../utils/format';

// ── Severity tokens (colors + labels) ───────────────────────────────────────
const SEVERITY_CONFIG = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-300',
    dot: 'bg-red-500',
    text: 'text-red-700',
    label: 'Critique',
  },
  high: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    dot: 'bg-orange-500',
    text: 'text-orange-700',
    label: 'Élevée',
  },
  medium: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    dot: 'bg-yellow-500',
    text: 'text-yellow-700',
    label: 'Moyenne',
  },
  low: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    dot: 'bg-gray-400',
    text: 'text-gray-600',
    label: 'Info',
  },
};

// ── Category icons ──────────────────────────────────────────────────────────
const CATEGORY_ICONS = {
  compliance: FileText,
  billing: Receipt,
  consumption: Activity,
  purchase: ShoppingCart,
  flex: Zap,
  audit: AlertTriangle,
  insight: Lightbulb,
};

// ── Helpers ─────────────────────────────────────────────────────────────────
function daysUntil(dateStr) {
  if (!dateStr) return null;
  return Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
}

function DeadlineBadge({ days }) {
  if (days == null) return null;
  const cls =
    days <= 0
      ? 'bg-red-50 text-red-700 border-red-200'
      : days <= 30
        ? 'bg-red-50 text-red-700 border-red-200'
        : days <= 90
          ? 'bg-amber-50 text-amber-700 border-amber-200'
          : 'bg-blue-50 text-blue-700 border-blue-200';
  return (
    <span
      className={`text-[10px] font-bold px-2 py-0.5 rounded border whitespace-nowrap ${cls}`}
      data-testid="finding-deadline"
    >
      {days <= 0 ? 'Dépassé' : `J-${days}`}
    </span>
  );
}

function ConfidenceBadge({ score }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const tier = score >= 0.75 ? 'high' : score >= 0.5 ? 'medium' : 'low';
  const cls = {
    high: 'bg-green-50 text-green-700 border-green-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    low: 'bg-gray-50 text-gray-600 border-gray-200',
  }[tier];
  return (
    <span
      className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}
      data-testid="finding-confidence"
      title={`Confiance du calcul : ${pct}%`}
    >
      {pct}%
    </span>
  );
}

function ImpactRow({ impact }) {
  if (!impact) return null;
  const { eur, kwh, co2_kg } = impact;
  if (eur == null && kwh == null && co2_kg == null) return null;
  return (
    <div
      className="mt-2 flex items-center gap-3 text-xs flex-wrap"
      data-testid="finding-impact"
    >
      {eur != null && eur !== 0 && (
        <span className="inline-flex items-center gap-1 text-green-700 font-semibold">
          <Zap size={12} aria-hidden="true" />
          {fmtEur(eur)}
          <span className="text-gray-500 font-normal">/an</span>
        </span>
      )}
      {kwh != null && kwh > 0 && (
        <span className="text-gray-500">
          {Math.round(kwh).toLocaleString('fr-FR')} kWh/an
        </span>
      )}
      {co2_kg != null && co2_kg > 0 && (
        <span className="text-gray-500">
          {Math.round(co2_kg).toLocaleString('fr-FR')} kgCO₂/an
        </span>
      )}
    </div>
  );
}

// ── FindingCard component ───────────────────────────────────────────────────

/**
 * @param {object} props
 * @param {'critical'|'high'|'medium'|'low'} [props.severity='medium']
 * @param {number} [props.priority] - rang 1-99 affiché en #N
 * @param {'compliance'|'billing'|'consumption'|'purchase'|'flex'|'audit'|'insight'} [props.category]
 * @param {string} props.title
 * @param {string} [props.description]
 * @param {{eur?:number, kwh?:number, co2_kg?:number}} [props.impact]
 * @param {string} [props.deadline] - ISO date string
 * @param {number} [props.confidence] - 0..1
 * @param {string} [props.actionLabel]
 * @param {() => void} [props.onAction]
 * @param {() => void} [props.onClick] - clic sur toute la card
 * @param {boolean} [props.compact=false]
 * @param {string} [props.className]
 */
export default function FindingCard({
  severity = 'medium',
  priority,
  category,
  title,
  description,
  impact,
  deadline,
  confidence,
  actionLabel,
  onAction,
  onClick,
  compact = false,
  className = '',
}) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
  const Icon = category && CATEGORY_ICONS[category];
  const days = daysUntil(deadline);

  const isInteractive = typeof onClick === 'function' || typeof onAction === 'function';
  const Wrapper = typeof onClick === 'function' ? 'button' : 'div';

  const handleCardClick = typeof onClick === 'function' ? onClick : undefined;

  const handleActionClick = (e) => {
    e.stopPropagation();
    if (onAction) onAction();
  };

  return (
    <Wrapper
      type={Wrapper === 'button' ? 'button' : undefined}
      onClick={handleCardClick}
      data-testid="finding-card"
      data-severity={severity}
      data-category={category || 'generic'}
      className={`
        w-full text-left border rounded-lg
        ${compact ? 'p-3' : 'p-4'}
        ${cfg.bg} ${cfg.border}
        ${isInteractive ? 'transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-blue-300' : ''}
        ${className}
      `.trim()}
    >
      <div className="flex items-start gap-3">
        {/* Severity dot + priority/icon */}
        <div className="flex flex-col items-center gap-2 flex-shrink-0">
          <span
            className={`w-2.5 h-2.5 rounded-full mt-1.5 ${cfg.dot}`}
            data-testid="finding-severity-dot"
            aria-label={`Sévérité ${cfg.label}`}
          />
          {Icon && (
            <Icon size={16} className={`${cfg.text} opacity-80`} aria-hidden="true" />
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            {priority != null && (
              <span
                className="text-xs font-semibold text-gray-500"
                data-testid="finding-priority"
              >
                #{priority}
              </span>
            )}
            <span className={`text-xs font-medium ${cfg.text}`}>{cfg.label}</span>
            <ConfidenceBadge score={confidence} />
          </div>

          <p className="text-sm font-semibold text-gray-900 line-clamp-2">{title}</p>
          {description && (
            <p className="text-xs text-gray-600 mt-1 line-clamp-2">{description}</p>
          )}

          <ImpactRow impact={impact} />
        </div>

        {/* Right zone: deadline + CTA */}
        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <DeadlineBadge days={days} />
          {actionLabel && onAction && (
            <button
              type="button"
              onClick={handleActionClick}
              className="text-xs font-medium text-blue-700 hover:text-blue-800 inline-flex items-center gap-1"
              data-testid="finding-action"
            >
              {actionLabel}
              <ChevronRight size={14} />
            </button>
          )}
          {onClick && !actionLabel && (
            <ChevronRight size={16} className="text-gray-400 mt-1" aria-hidden="true" />
          )}
        </div>
      </div>
    </Wrapper>
  );
}
