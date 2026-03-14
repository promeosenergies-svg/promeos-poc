/**
 * PROMEOS — MarketContextBanner
 * Affiche le contexte marché en haut de la page Achat.
 * 3 états : marché bas (vert), stable (bleu), haut (orange).
 * Props : marketContext (from GET /api/market/context), isExpert, onNavigate
 */
import { TrendingDown, TrendingUp, Minus, ArrowRight } from 'lucide-react';
import { fmtNum } from '../../utils/format';

const STATES = {
  low: {
    bg: 'bg-green-50 border-green-200',
    icon: TrendingDown,
    iconClass: 'text-green-600',
    dot: 'bg-green-500',
  },
  stable: {
    bg: 'bg-blue-50 border-blue-200',
    icon: Minus,
    iconClass: 'text-blue-600',
    dot: 'bg-blue-500',
  },
  high: {
    bg: 'bg-orange-50 border-orange-200',
    icon: TrendingUp,
    iconClass: 'text-orange-600',
    dot: 'bg-orange-500',
  },
};

function getMarketState(trend) {
  if (trend < -5) return 'low';
  if (trend > 5) return 'high';
  return 'stable';
}

export default function MarketContextBanner({ marketContext, isExpert, onNavigate }) {
  if (!marketContext || marketContext.spot_current_eur_mwh == null) return null;

  const {
    spot_current_eur_mwh: spot,
    spot_avg_12m_eur_mwh: avg12m,
    trend_30d_vs_12m_pct: trend,
    volatility_12m_eur_mwh: vol,
    spot_avg_30d_eur_mwh: spot30d,
  } = marketContext;

  const state = getMarketState(trend);
  const cfg = STATES[state];
  const Icon = cfg.icon;
  const absTrend = Math.abs(trend).toFixed(0);

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 border rounded-lg ${cfg.bg}`}
      data-testid="market-context-banner"
    >
      <div className={`shrink-0 mt-0.5 ${cfg.iconClass}`}>
        <Icon size={18} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">
          {state === 'low' && (
            <>
              Le marché spot est à <strong>{spot.toFixed(0)} EUR/MWh</strong>, {absTrend}% sous la
              moyenne 12 mois. Moment favorable pour sécuriser un prix.
            </>
          )}
          {state === 'stable' && (
            <>
              Le marché spot est à <strong>{spot.toFixed(0)} EUR/MWh</strong>, stable par rapport
              aux 12 derniers mois.
            </>
          )}
          {state === 'high' && (
            <>
              Le marché spot est à <strong>{spot.toFixed(0)} EUR/MWh</strong>, {absTrend}% au-dessus
              de la moyenne 12 mois. Envisagez un contrat indexé avec cap pour limiter l'exposition.
            </>
          )}
        </p>

        {isExpert && (
          <p className="text-xs text-gray-500 mt-1">
            Spot 30j : {fmtNum(spot30d, 1)} EUR/MWh · Moy. 12m : {fmtNum(avg12m, 1)} EUR/MWh ·
            Volatilité : {fmtNum(vol, 1)} EUR/MWh · Δ {trend >= 0 ? '+' : ''}
            {fmtNum(trend, 1)}%
          </p>
        )}

        {state !== 'stable' && onNavigate && (
          <button
            className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 transition"
            onClick={() => onNavigate('/achat-energie?tab=simulation')}
          >
            {state === 'low' ? 'Lancer une simulation' : 'Comparer les stratégies'}
            <ArrowRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Version compacte pour le Cockpit (1 ligne).
 */
export function MarketContextCompact({ marketContext, onNavigate }) {
  if (!marketContext || marketContext.spot_current_eur_mwh == null) return null;

  const { spot_current_eur_mwh: spot, trend_30d_vs_12m_pct: trend } = marketContext;
  const state = getMarketState(trend);
  const cfg = STATES[state];
  const absTrend = Math.abs(trend).toFixed(0);
  const arrow = trend < -2 ? '↓' : trend > 2 ? '↑' : '→';
  const trendColor =
    state === 'low' ? 'text-green-600' : state === 'high' ? 'text-orange-600' : 'text-gray-500';

  return (
    <div
      className="flex items-center gap-2 text-xs text-gray-600 cursor-pointer hover:text-gray-800 transition"
      onClick={() => onNavigate?.('/achat-energie')}
      title="Voir les scénarios d'achat"
    >
      <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
      <span>
        Marché : <strong>{spot.toFixed(0)} EUR/MWh</strong>
      </span>
      <span className={trendColor}>
        ({arrow} {absTrend}% vs moy.)
      </span>
    </div>
  );
}
