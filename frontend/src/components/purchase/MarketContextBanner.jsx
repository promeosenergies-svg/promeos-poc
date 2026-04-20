/**
 * PROMEOS — MarketContextBanner (Lot 7 refonte Sol)
 *
 * Affiche le contexte marché en haut de la page Achat. 3 états sémantiques
 * mappés sur les tokens Sol (succes / calme / attention) :
 *   - low       (trend < -5)  : moment favorable (vert)
 *   - stable    (|trend| ≤ 5) : stable (bleu Sol calme)
 *   - high      (trend > 5)   : exposition à couvrir par cap (ambre)
 *
 * Valeurs numériques formatées via fmtNum (FR locale, null-safe).
 * Zéro .toFixed() : migration baseline formatGuard.
 *
 * Props :
 *   marketContext (GET /api/market/context) — null guard interne
 *   isExpert      — affiche la ligne de détails mono (spot30j, moy12m, vol)
 *   onNavigate    — callback route ; bouton CTA affiché sur low/high
 */
import { TrendingDown, TrendingUp, Minus, ArrowRight } from 'lucide-react';
import { fmtNum } from '../../utils/format';

// Style commun sur tous les chiffres affichés (police mono + tabular-nums
// pour que les colonnes de chiffres s'alignent pixel-à-pixel).
const MONO_STYLE = {
  fontFamily: 'var(--sol-font-mono)',
  fontVariantNumeric: 'tabular-nums',
};

// Mapping état → token Sol sémantique. Strings FR exposées côté test
// (step24_market_banner.test.js vérifie "favorable" / "stable" / "cap").
const STATES = {
  low: {
    icon: TrendingDown,
    bgVar: 'var(--sol-succes-bg)',
    fgVar: 'var(--sol-succes-fg)',
  },
  stable: {
    icon: Minus,
    bgVar: 'var(--sol-calme-bg)',
    fgVar: 'var(--sol-calme-fg)',
  },
  high: {
    icon: TrendingUp,
    bgVar: 'var(--sol-attention-bg)',
    fgVar: 'var(--sol-attention-fg)',
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
  const absTrend = fmtNum(Math.abs(trend), 0);
  const spotDisplay = fmtNum(spot, 0);

  return (
    <div
      className={`sol-market-banner is-${state}`}
      data-testid="market-context-banner"
      data-state={state}
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '12px 16px',
        border: `1px solid ${cfg.fgVar}`,
        borderLeft: `3px solid ${cfg.fgVar}`,
        borderRadius: 6,
        background: cfg.bgVar,
      }}
    >
      <div style={{ flexShrink: 0, marginTop: 2, color: cfg.fgVar }}>
        <Icon size={18} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 13,
            color: 'var(--sol-ink-900)',
            lineHeight: 1.45,
            margin: 0,
          }}
        >
          {state === 'low' && (
            <>
              Le marché spot est à <strong style={MONO_STYLE}>{spotDisplay} EUR/MWh</strong>, {absTrend}%
              sous la moyenne 12 mois. Moment favorable pour sécuriser un prix.
            </>
          )}
          {state === 'stable' && (
            <>
              Le marché spot est à <strong style={MONO_STYLE}>{spotDisplay} EUR/MWh</strong>, stable par
              rapport aux 12 derniers mois.
            </>
          )}
          {state === 'high' && (
            <>
              Le marché spot est à <strong style={MONO_STYLE}>{spotDisplay} EUR/MWh</strong>, {absTrend}%
              au-dessus de la moyenne 12 mois. Envisagez un contrat indexé avec cap pour limiter
              l'exposition.
            </>
          )}
        </p>

        {isExpert && (
          <p
            style={{
              ...MONO_STYLE,
              fontSize: 11,
              color: 'var(--sol-ink-500)',
              letterSpacing: '0.02em',
              margin: '4px 0 0 0',
            }}
          >
            Spot 30j : {fmtNum(spot30d, 1)} EUR/MWh · Moy. 12m : {fmtNum(avg12m, 1)} EUR/MWh · Volatilité :{' '}
            {fmtNum(vol, 1)} EUR/MWh · Δ {trend >= 0 ? '+' : ''}
            {fmtNum(trend, 1)}%
          </p>
        )}

        {state !== 'stable' && onNavigate && (
          <button
            type="button"
            onClick={() => onNavigate('/achat-energie?tab=simulation')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              marginTop: 8,
              fontFamily: 'var(--sol-font-body)',
              fontSize: 12,
              fontWeight: 500,
              color: cfg.fgVar,
              background: 'transparent',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
            }}
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
 * Version compacte (Cockpit legacy — 1 ligne, dot + spot + trend).
 * Conservé pour compat tests + callers historiques.
 */
export function MarketContextCompact({ marketContext, onNavigate }) {
  if (!marketContext || marketContext.spot_current_eur_mwh == null) return null;

  const { spot_current_eur_mwh: spot, trend_30d_vs_12m_pct: trend } = marketContext;
  const state = getMarketState(trend);
  const cfg = STATES[state];
  const absTrend = fmtNum(Math.abs(trend), 0);
  const arrow = trend < -2 ? '↓' : trend > 2 ? '↑' : '→';

  const interactive = typeof onNavigate === 'function';
  const navigate = () => onNavigate('/achat-energie');

  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={interactive ? navigate : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                navigate();
              }
            }
          : undefined
      }
      title="Voir les scénarios d'achat"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        fontFamily: 'var(--sol-font-body)',
        fontSize: 12,
        color: 'var(--sol-ink-500)',
        cursor: interactive ? 'pointer' : 'default',
      }}
    >
      <span
        aria-hidden
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: cfg.fgVar,
          flexShrink: 0,
        }}
      />
      <span>
        Marché :{' '}
        <strong style={{ ...MONO_STYLE, color: 'var(--sol-ink-900)' }}>{fmtNum(spot, 0)} EUR/MWh</strong>
      </span>
      <span style={{ ...MONO_STYLE, color: cfg.fgVar }}>
        ({arrow} {absTrend}% vs moy.)
      </span>
    </div>
  );
}
