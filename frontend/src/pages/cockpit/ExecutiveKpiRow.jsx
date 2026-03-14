/**
 * PROMEOS — ExecutiveKpiRow (Cockpit V2)
 * 4 executive KPI tuiles: Conformité / Risque / Maturité / Couverture données.
 * Data from buildExecutiveKpis(kpis, sites) — no hard-coded colors.
 *
 * Props:
 *   kpis       {ExecKpi[]}  — from buildExecutiveKpis()
 *   onNavigate {fn}         — navigate(path)
 */
import { ShieldCheck, TrendingDown, BarChart3, Database, HelpCircle } from 'lucide-react';
import { KPI_ACCENTS } from '../../ui/colorTokens';
import { getKpiMessage } from '../../services/kpiMessaging';

/** KPI ids that support the "Pourquoi ?" evidence button */
const EVIDENCE_KPIS = new Set(['conformite', 'risque', 'maturite', 'couverture']);

// ── Expert source / confidence per KPI ────────────────────────────────────────

const EXPERT_SOURCE = {
  conformite: { source: 'compliance_engine v2', confiance: 'moyenne' },
  risque: { source: 'compliance_engine v2', confiance: 'moyenne' },
  maturite: { source: 'base PROMEOS', confiance: 'haute' },
  couverture: { source: 'factures importées', confiance: 'variable' },
};

// ── Icon map ──────────────────────────────────────────────────────────────────

const KPI_ICONS = {
  conformite: ShieldCheck,
  risque: TrendingDown,
  maturite: BarChart3,
  couverture: Database,
  neutral: Database,
};

// ── Status dot ────────────────────────────────────────────────────────────────

const STATUS_DOT = {
  crit: 'bg-red-500',
  warn: 'bg-amber-400',
  ok: 'bg-emerald-500',
  neutral: 'bg-gray-300',
};

// ── KPI tile ──────────────────────────────────────────────────────────────────

function KpiTile({ kpi, onNavigate, onEvidence, isExpert, scoreTrend }) {
  const acc = KPI_ACCENTS[kpi.accentKey] || KPI_ACCENTS.neutral;
  const Icon = KPI_ICONS[kpi.id] || KPI_ICONS[kpi.accentKey] || Database;
  const dotClass = STATUS_DOT[kpi.status] || STATUS_DOT.neutral;
  const El = kpi.path ? 'button' : 'div';
  const hasEvidence = EVIDENCE_KPIS.has(kpi.id) && onEvidence;

  return (
    <div className="relative">
      <El
        {...(kpi.path ? { onClick: () => onNavigate?.(kpi.path), type: 'button' } : {})}
        className={`rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-start gap-3 transition-shadow w-full
          ${kpi.path ? 'hover:shadow-sm cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500' : ''}`}
      >
        {/* Icon pill */}
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${acc.iconBg}`}
        >
          <Icon size={18} className={acc.iconText} />
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
            {kpi.label}
          </p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <p className="text-lg font-bold text-gray-900 leading-tight break-words">{kpi.value}</p>
            <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} aria-hidden="true" />
          </div>
          {kpi.sub && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{kpi.sub}</p>}
          {kpi.id === 'conformite' &&
            scoreTrend?.length >= 2 &&
            (() => {
              const first = scoreTrend[0]?.score ?? 0;
              // Use current live score instead of last snapshot for coherence
              const currentScore = kpi.rawValue ?? scoreTrend[scoreTrend.length - 1]?.score ?? 0;
              const progressing = currentScore >= first;
              const color = progressing ? '#10b981' : '#ef4444';
              const arrow = progressing ? '\u2191' : '\u2193';
              return (
                <p
                  className="text-[10px] mt-1"
                  style={{ color }}
                  data-testid="conformite-sparkline"
                >
                  {arrow} {Math.round(first)} → {Math.round(currentScore)} en {scoreTrend.length}{' '}
                  mois
                </p>
              );
            })()}
          {(() => {
            const msg = getKpiMessage(kpi.id, kpi.rawValue, kpi.messageCtx);
            if (!msg) return null;
            return (
              <p
                className={`text-[11px] mt-1 leading-snug ${
                  msg.severity === 'crit'
                    ? 'text-red-600'
                    : msg.severity === 'warn'
                      ? 'text-amber-600'
                      : 'text-gray-500'
                }`}
                data-testid={`kpi-message-${kpi.id}`}
              >
                {isExpert ? msg.expert : msg.simple}
              </p>
            );
          })()}
          {isExpert && EXPERT_SOURCE[kpi.id] && (
            <p className="text-[10px] text-gray-400 mt-1 font-mono">
              Source : {EXPERT_SOURCE[kpi.id].source} · Confiance :{' '}
              {EXPERT_SOURCE[kpi.id].confiance}
            </p>
          )}
        </div>
      </El>
      {hasEvidence && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEvidence(kpi.id);
          }}
          className="absolute top-2 right-2 p-1 rounded-md text-gray-300 hover:text-blue-500 hover:bg-blue-50 transition
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label={`Pourquoi ce chiffre : ${kpi.label}`}
          data-testid={`evidence-open-${kpi.id}`}
        >
          <HelpCircle size={14} />
        </button>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ExecutiveKpiRow({
  kpis = [],
  onNavigate,
  onEvidence,
  isExpert,
  scoreTrend,
}) {
  if (!kpis.length) return null;

  return (
    <div
      className={`grid gap-3 grid-cols-2 ${kpis.length >= 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}
    >
      {kpis.map((kpi) => (
        <KpiTile
          key={kpi.id}
          kpi={kpi}
          onNavigate={onNavigate}
          onEvidence={onEvidence}
          isExpert={isExpert}
          scoreTrend={kpi.id === 'conformite' ? scoreTrend : null}
        />
      ))}
    </div>
  );
}
