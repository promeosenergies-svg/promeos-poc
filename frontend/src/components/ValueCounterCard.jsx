/**
 * PROMEOS — ValueCounterCard (CX Gap #6, refactor round 6)
 * Widget affichant la valeur cumulée créée par PROMEOS depuis l'abonnement.
 *
 * Refactor inline styles + tokens var(--sol-*) pour cohérence design system
 * (audit CX/Ergo round 6 : précédemment Tailwind classes hardcoded en
 * emerald-*, créait une rupture visuelle vs SolHero/PeerComparison voisins).
 *
 * Empty state placeholder dashed (pas return null) pour préserver le grid
 * 2-col PeerComp+ValueCounter sur la home / quand data insuffisante.
 */
import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { getValueSummary } from '../services/api/cockpit';
import { fmtEur } from '../utils/format';

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  } catch {
    return '';
  }
}

export default function ValueCounterCard({ orgId }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!orgId) return;
    getValueSummary(orgId)
      .then(setData)
      .catch(() => setData(null));
  }, [orgId]);

  // Empty state visible — préserve le grid 2-col PeerComp+ValueCounter
  // sur la home / (round 6). Pas de return null.
  if (!data || !data.total_eur || data.total_eur < 1000) {
    return (
      <div
        style={{
          background: 'var(--sol-bg-paper)',
          border: '1px dashed var(--sol-ink-200)',
          borderRadius: 8,
          padding: '20px 22px',
          fontSize: 12,
          color: 'var(--sol-ink-500)',
          fontFamily: 'var(--sol-font-body)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          minHeight: 80,
        }}
      >
        <TrendingUp size={16} style={{ color: 'var(--sol-ink-400)', flexShrink: 0 }} aria-hidden="true" />
        <span>
          <strong style={{ color: 'var(--sol-ink-700)' }}>Valeur créée par PROMEOS</strong>
          {' '}— compteur initialisé · cumul ≥ 1 000 € à venir.
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        background: 'var(--sol-calme-bg, #ecfdf5)',
        border: '1px solid var(--sol-calme-fg, #047857)',
        borderLeft: '3px solid var(--sol-calme-fg, #047857)',
        borderRadius: 8,
        padding: '16px 20px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <p
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 11,
              fontWeight: 600,
              color: 'var(--sol-calme-fg, #047857)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              margin: '0 0 4px 0',
            }}
          >
            Valeur créée par PROMEOS
          </p>
          <p
            style={{
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 22,
              fontWeight: 700,
              color: 'var(--sol-ink-900)',
              fontVariantNumeric: 'tabular-nums',
              margin: 0,
              letterSpacing: '-0.01em',
            }}
          >
            {fmtEur(data.total_eur)}
          </p>
          <p
            style={{
              fontSize: 12,
              color: 'var(--sol-ink-500)',
              margin: '4px 0 0 0',
            }}
          >
            depuis {formatDate(data.since)} — {data.insights_count} insights
          </p>
        </div>
        <TrendingUp
          size={28}
          style={{ color: 'var(--sol-calme-fg, #047857)', flexShrink: 0, opacity: 0.5 }}
          aria-hidden="true"
        />
      </div>
      <div
        style={{
          marginTop: 10,
          display: 'flex',
          flexWrap: 'wrap',
          gap: 14,
          fontSize: 11,
          color: 'var(--sol-ink-700)',
        }}
      >
        <span>Anomalies : {fmtEur(data.anomalies_detected_eur)}</span>
        <span>Pénalités évitées : {fmtEur(data.penalties_avoided_eur)}</span>
      </div>
    </div>
  );
}
