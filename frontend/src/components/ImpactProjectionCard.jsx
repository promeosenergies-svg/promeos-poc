/**
 * PROMEOS — ImpactProjectionCard
 *
 * Wow-card visuelle : gap d'économies cumulées sur 3 ans entre 2 scénarios :
 *  - Scénario "sans Sol" : aucun levier activé → 0 € cumul
 *  - Scénario "avec Sol" : 3 leviers activés → impactEurPerYear × 3 cumulé
 *
 * Différenciateur PROMEOS : preuve visuelle de la valeur PROMEOS sur la
 * trajectoire stratégique. Aucun concurrent B2B énergie n'affiche ce gap.
 */
import { useMemo } from 'react';
import { ArrowRight, Sparkles } from 'lucide-react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';

function formatFREur(eur) {
  if (eur == null) return '—';
  if (Math.abs(eur) >= 1_000_000) return `${(eur / 1_000_000).toFixed(1).replace('.', ',')} M€`;
  if (Math.abs(eur) >= 1_000) return `${Math.round(eur / 100) / 10} k€`.replace('.', ',');
  return `${Math.round(eur)} €`;
}

export default function ImpactProjectionCard({
  annualImpactEur,
  actionsCount = 3,
  onPrimary,
}) {
  const cumul3 = useMemo(
    () => Math.round((annualImpactEur || 0) * 3),
    [annualImpactEur]
  );

  const chartData = useMemo(() => {
    const a = annualImpactEur || 0;
    return [
      { year: 'Aujourd\'hui', sansSol: 0, avecSol: 0 },
      { year: 'Année 1', sansSol: 0, avecSol: a },
      { year: 'Année 2', sansSol: 0, avecSol: a * 2 },
      { year: 'Année 3', sansSol: 0, avecSol: a * 3 },
    ];
  }, [annualImpactEur]);

  if (!annualImpactEur || annualImpactEur <= 0) return null;

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-calme-fg)',
        borderRadius: 8,
        padding: '20px 22px',
        animation: 'slideInUp 600ms cubic-bezier(0.16, 1, 0.3, 1) backwards',
      }}
    >
      {/* Chip + headline */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontFamily: 'var(--sol-font-mono)',
          fontSize: 9.5,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: 'var(--sol-calme-fg)',
          fontWeight: 600,
          background: 'var(--sol-calme-bg)',
          padding: '3px 8px',
          borderRadius: 99,
          marginBottom: 12,
        }}
      >
        <Sparkles size={10} />
        Projection Sol · 3 ans
      </div>

      <h3
        style={{
          fontFamily: 'var(--sol-font-body)',
          fontSize: 16,
          fontWeight: 600,
          color: 'var(--sol-ink-900)',
          marginBottom: 6,
          lineHeight: 1.3,
          letterSpacing: '-0.015em',
        }}
      >
        Si vous activez les {actionsCount} leviers Sol
      </h3>

      <p
        style={{
          fontSize: 13,
          color: 'var(--sol-ink-500)',
          lineHeight: 1.55,
          margin: '0 0 16px 0',
        }}
      >
        Sans action, ces opportunités restent latentes. Avec Sol, vous récupérez{' '}
        <strong style={{ color: 'var(--sol-ink-900)' }}>
          {formatFREur(cumul3)}
        </strong>{' '}
        cumulés sur 3 ans.
      </p>

      {/* Two-column : metrics + mini chart */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'auto 1fr',
          gap: 28,
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Sans Sol */}
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
              Sans action
            </div>
            <div
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 28,
                color: 'var(--sol-ink-400)',
                lineHeight: 1,
              }}
            >
              0 €
            </div>
            <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
              opportunités latentes
            </div>
          </div>

          {/* Avec Sol */}
          <div>
            <div
              style={{
                fontSize: 10,
                color: 'var(--sol-calme-fg)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                fontFamily: 'var(--sol-font-mono)',
                marginBottom: 4,
                fontWeight: 600,
              }}
            >
              Avec Sol · {actionsCount} leviers
            </div>
            <div
              style={{
                fontFamily: 'var(--sol-font-display)',
                fontSize: 36,
                color: 'var(--sol-calme-fg)',
                lineHeight: 1,
                fontWeight: 600,
              }}
            >
              {formatFREur(cumul3)}
            </div>
            <div style={{ fontSize: 11, color: 'var(--sol-ink-500)', marginTop: 4 }}>
              cumul économies à 3 ans
            </div>
          </div>
        </div>

        {/* Mini area chart : visualisation du gap */}
        <div style={{ width: '100%', height: 140 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, bottom: 4, left: 0 }}>
              <defs>
                <linearGradient id="solGapFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--sol-calme-fg)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--sol-calme-fg)" stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="year"
                axisLine={false}
                tickLine={false}
                tick={{
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 10,
                  fill: 'var(--sol-ink-500)',
                }}
              />
              <YAxis hide domain={[0, 'dataMax + 5000']} />
              <Tooltip
                contentStyle={{
                  background: 'var(--sol-bg-paper)',
                  border: '1px solid var(--sol-rule)',
                  borderRadius: 4,
                  fontFamily: 'var(--sol-font-mono)',
                  fontSize: 11,
                }}
                formatter={(value, name) => [
                  formatFREur(value),
                  name === 'avecSol' ? 'avec Sol' : 'sans Sol',
                ]}
              />
              <Area
                type="monotone"
                dataKey="sansSol"
                stroke="var(--sol-ink-300)"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                fill="transparent"
                dot={{ r: 2, fill: 'var(--sol-ink-400)' }}
              />
              <Area
                type="monotone"
                dataKey="avecSol"
                stroke="var(--sol-calme-fg)"
                strokeWidth={2.5}
                fill="url(#solGapFill)"
                dot={{ r: 4, fill: 'var(--sol-calme-fg)', strokeWidth: 0 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* CTA */}
      {onPrimary && (
        <div style={{ marginTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={onPrimary}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              fontWeight: 500,
              padding: '8px 14px',
              borderRadius: 6,
              border: '1px solid transparent',
              background: 'var(--sol-calme-fg)',
              color: 'white',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              transition: 'background 120ms ease',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#245047')}
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = 'var(--sol-calme-fg)')
            }
          >
            Activer les leviers <ArrowRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
