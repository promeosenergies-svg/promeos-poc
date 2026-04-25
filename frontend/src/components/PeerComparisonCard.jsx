/**
 * PROMEOS — PeerComparisonCard
 *
 * Wow-card wedge anti-fournisseur "tout sauf la fourniture" :
 * compare le €/kWh moyen du patrimoine vs benchmark pairs OID/CEREN
 * de l'archétype NAF dominant.
 *
 * Différenciateur PROMEOS : Metron/Advizeo affichent les chiffres
 * factures bruts, PROMEOS affiche LE GAP vs pairs sectoriels — angle
 * commercial fort pour la démo et le wedge low-end.
 */
import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus, Users } from 'lucide-react';
import { getPeerComparison } from '../services/api/sol';

function formatEur(eur) {
  if (eur == null || isNaN(eur)) return '—';
  return Math.round(eur).toLocaleString('fr-FR') + ' €';
}

function formatPriceKwh(eur) {
  if (eur == null || isNaN(eur)) return '—';
  return eur.toFixed(3).replace('.', ',') + ' €/kWh';
}

export default function PeerComparisonCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPeerComparison()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading || !data || data.my_avg_kwh_price_eur == null) return null;

  const surpaie = data.spread_pct > 0;
  const isPair = Math.abs(data.spread_pct || 0) < 2;
  const isUnder = data.spread_pct < -2;

  // Couleurs sémantiques
  const accentBg = isPair
    ? 'var(--sol-ink-100, #f3f4f6)'
    : surpaie
      ? 'var(--sol-afaire-bg, #fee2e2)'
      : 'var(--sol-calme-bg, #ecfdf5)';
  const accentFg = isPair
    ? 'var(--sol-ink-700)'
    : surpaie
      ? 'var(--sol-afaire-fg, #b91c1c)'
      : 'var(--sol-calme-fg, #047857)';
  const Icon = isPair ? Minus : surpaie ? TrendingUp : TrendingDown;
  const borderLeft = surpaie
    ? 'var(--sol-afaire-fg, #b91c1c)'
    : isUnder
      ? 'var(--sol-calme-fg, #047857)'
      : 'var(--sol-ink-300)';

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: `3px solid ${borderLeft}`,
        borderRadius: 8,
        padding: '20px 22px',
        animation: 'slideInUp 600ms cubic-bezier(0.16, 1, 0.3, 1) backwards',
      }}
    >
      {/* Chip */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 9.5,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: accentFg,
          fontWeight: 600,
          background: accentBg,
          padding: '3px 8px',
          borderRadius: 99,
          marginBottom: 12,
        }}
      >
        <Users size={10} />
        Vs pairs · {data.archetype_label}
      </div>

      {/* Big numbers : VOUS / PAIRS / ÉCART */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr auto 1fr',
          gap: 16,
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        {/* Vous */}
        <div>
          <div
            style={{
              fontSize: 10,
              color: 'var(--sol-ink-500)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontFamily: 'var(--sol-font-mono)',
              marginBottom: 4,
              fontWeight: 600,
            }}
          >
            Vous payez
          </div>
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 26,
              color: 'var(--sol-ink-900)',
              lineHeight: 1,
              fontWeight: 600,
            }}
          >
            {formatPriceKwh(data.my_avg_kwh_price_eur)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
            moyenne facture · {data.sites_count_in_scope} sites
          </div>
        </div>

        {/* Vs separator */}
        <div
          style={{
            color: 'var(--sol-ink-400)',
            fontSize: 11,
            fontFamily: 'var(--sol-font-mono)',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          vs
        </div>

        {/* Pairs */}
        <div>
          <div
            style={{
              fontSize: 10,
              color: 'var(--sol-ink-500)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontFamily: 'var(--sol-font-mono)',
              marginBottom: 4,
              fontWeight: 600,
            }}
          >
            Pairs paient
          </div>
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 26,
              color: 'var(--sol-ink-700)',
              lineHeight: 1,
              fontWeight: 600,
            }}
          >
            {formatPriceKwh(data.peer_avg_kwh_price_eur)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
            benchmark OID/CEREN
          </div>
        </div>

        {/* Arrow separator */}
        <div style={{ color: 'var(--sol-ink-400)', fontSize: 18 }}>→</div>

        {/* Écart */}
        <div>
          <div
            style={{
              fontSize: 10,
              color: accentFg,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              fontFamily: 'var(--sol-font-mono)',
              marginBottom: 4,
              fontWeight: 600,
            }}
          >
            Écart
          </div>
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 32,
              color: accentFg,
              lineHeight: 1,
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Icon size={20} />
            {data.spread_pct > 0 ? '+' : ''}
            {(data.spread_pct || 0).toFixed(1)}%
          </div>
          {data.annual_overpayment_eur > 0 && (
            <div
              style={{
                fontSize: 11,
                color: accentFg,
                marginTop: 4,
                fontWeight: 600,
              }}
            >
              ≈ {formatEur(data.annual_overpayment_eur)}/an
            </div>
          )}
        </div>
      </div>

      {/* Interpretation */}
      <div
        style={{
          fontSize: 13,
          color: 'var(--sol-ink-700)',
          lineHeight: 1.5,
          padding: '10px 14px',
          background: 'var(--sol-bg-canvas, #fafaf6)',
          borderRadius: 6,
          marginTop: 4,
        }}
      >
        {data.interpretation}
      </div>

      {/* Source footer */}
      <div
        style={{
          marginTop: 8,
          fontSize: 10,
          color: 'var(--sol-ink-400)',
          fontFamily: 'var(--sol-font-mono)',
          letterSpacing: '0.04em',
        }}
      >
        {data.peer_source} · confiance {data.confidence}
      </div>
    </div>
  );
}
