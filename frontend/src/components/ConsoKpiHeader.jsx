/**
 * PROMEOS — ConsoKpiHeader (QW2 / P1.1 polish)
 * 6-KPI header row for ConsumptionExplorerPage.
 * Reads motor data (tunnel, hphc, progression) to compute:
 *   kWh total, EUR total, EUR/MWh, CO2e, Pic kW (P95), Base nocturne %
 * Respects scope global (site + period) via motor props.
 *
 * P1.1: confidence tooltip "Comment calcule ?", EUR source tooltip.
 */
import { Zap, Euro, TrendingUp, Leaf, Activity, Moon, HelpCircle } from 'lucide-react';
import { TrustBadge } from '../ui';
import { CO2E_FACTOR_KG_PER_KWH } from '../pages/consumption/constants';
import { fmtNum } from '../utils/format';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { getKpiLabel } from '../shared/kpiLabels';

const CONFIDENCE_TOOLTIP = {
  high: 'Haute : > 500 relevés, données homogènes',
  medium: 'Moyenne : entre 100 et 500 relevés',
  low: 'Basse : < 100 relevés — indicatif uniquement',
};

function KpiTile({
  icon: Icon,
  label,
  value,
  sub,
  color = 'text-gray-900',
  tooltip,
  evidenceId,
  onEvidence,
}) {
  return (
    <div
      className="relative flex items-center gap-3 bg-white rounded-xl border border-gray-200 px-4 py-3 min-w-0"
      title={tooltip}
    >
      <div className="w-9 h-9 rounded-lg bg-gray-100 flex items-center justify-center shrink-0">
        <Icon size={18} className="text-gray-500" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] text-gray-400 uppercase tracking-wider font-medium truncate">
          {label}
        </p>
        <p className={`text-lg font-bold ${color} truncate leading-tight`}>{value ?? '—'}</p>
        <div className="min-h-[1.25rem]">
          {sub && <p className="text-[11px] text-gray-400 truncate">{sub}</p>}
        </div>
      </div>
      {evidenceId && onEvidence && (
        <button
          onClick={() => onEvidence(evidenceId)}
          className="absolute top-1.5 right-1.5 p-1 rounded-md text-gray-300 hover:text-blue-500 hover:bg-blue-50 transition
            focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label={`Pourquoi ce chiffre : ${label}`}
          data-testid={`evidence-open-${evidenceId}`}
        >
          <HelpCircle size={13} />
        </button>
      )}
    </div>
  );
}

/** TrendDelta — small N vs N-1 badge shown when compareYoy is active */
function TrendDelta({ deltaPct }) {
  if (deltaPct == null) return null;
  const sign = deltaPct > 0 ? '+' : '';
  const color = deltaPct > 0 ? 'text-red-600' : deltaPct < 0 ? 'text-green-600' : 'text-gray-500';
  return (
    <span className={`text-[10px] font-semibold ${color}`} title={`Variation N vs N-1 : ${sign}${deltaPct}%`}>
      {sign}{deltaPct}% vs N-1
    </span>
  );
}

export default function ConsoKpiHeader({ tunnel, hphc, progression, confidence, onEvidence, compareSummary }) {
  const { isExpert } = useExpertMode();
  // --- kWh total ---
  // Priority: hphc.total_kwh (sum of readings HP+HC, always available when data exists)
  // then tunnel.total_kwh (not returned by current tunnel service)
  // then progression.ytd_actual_kwh (YTD targets — may be null if no targets configured)
  const totalKwh = hphc?.total_kwh ?? tunnel?.total_kwh ?? progression?.ytd_actual_kwh ?? null;
  const kwhLabel = totalKwh != null ? fmtNum(Math.round(totalKwh), 0, 'kWh') : '—';

  // --- EUR total (from hphc or progression) ---
  const totalEur = hphc?.total_cost_eur ?? null;
  const eurLabel = totalEur != null ? fmtNum(Math.round(totalEur), 0, 'EUR') : '—';
  const eurSource = hphc?.total_cost_eur != null ? 'Estime HP/HC' : 'Non disponible';

  // --- EUR/MWh reel ---
  const eurMwh =
    totalEur != null && totalKwh > 0 ? Math.round((totalEur / totalKwh) * 1000 * 100) / 100 : null;
  const eurMwhLabel = eurMwh != null ? fmtNum(eurMwh, 2, 'EUR/MWh') : '—';

  // --- CO2e ---
  const co2Kg = totalKwh != null ? Math.round(totalKwh * CO2E_FACTOR_KG_PER_KWH) : null;
  const co2Label = co2Kg != null ? fmtNum(co2Kg, 0, 'kg') : '—';

  // --- Pic kW (P95 from tunnel envelope) ---
  const p95 = (() => {
    if (!tunnel?.envelope) return null;
    const slots = tunnel.envelope.weekday || tunnel.envelope.weekend || [];
    if (!slots.length) return null;
    return Math.max(...slots.map((s) => s.p95 ?? s.p90 ?? 0));
  })();
  const p95Label = p95 != null ? fmtNum(Math.round(p95), 0, 'kW') : '—';

  // --- Base nocturne % (ratio of night hours P50 vs overall P50) ---
  const basePct = (() => {
    if (!tunnel?.envelope?.weekday) return null;
    const slots = tunnel.envelope.weekday;
    if (slots.length < 24) return null;
    const nightSlots = slots.filter((s) => s.hour < 6 || s.hour >= 22);
    const daySlots = slots.filter((s) => s.hour >= 6 && s.hour < 22);
    const nightAvg = nightSlots.reduce((s, x) => s + (x.p50 || 0), 0) / (nightSlots.length || 1);
    const dayAvg = daySlots.reduce((s, x) => s + (x.p50 || 0), 0) / (daySlots.length || 1);
    if (dayAvg === 0) return null;
    return Math.round((nightAvg / dayAvg) * 100);
  })();
  const basePctLabel = basePct != null ? `${basePct} %` : '—';
  const basePctColor =
    basePct != null
      ? basePct > 60
        ? 'text-red-600'
        : basePct > 40
          ? 'text-amber-600'
          : 'text-green-600'
      : 'text-gray-900';

  const confBadge = confidence
    ? {
        high: { label: 'Haute', variant: 'ok' },
        medium: { label: 'Moyenne', variant: 'warn' },
        low: { label: 'Basse', variant: 'crit' },
      }[confidence] || null
    : null;
  const confTooltip = confidence ? CONFIDENCE_TOOLTIP[confidence] : null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <h3 className="text-sm font-semibold text-gray-600">KPIs Consommation</h3>
        {confBadge && (
          <span
            className="inline-flex items-center gap-1"
            title={`Comment calcule ? ${confTooltip}`}
          >
            <TrustBadge
              level={confBadge.variant}
              label={`Confiance ${confBadge.label}`}
              size="sm"
            />
            <HelpCircle size={12} className="text-gray-400 cursor-help" />
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <KpiTile
          icon={Zap}
          label={getKpiLabel('total_kwh', isExpert)}
          value={kwhLabel}
          sub={compareSummary?.delta_pct != null ? <TrendDelta deltaPct={compareSummary.delta_pct} /> : undefined}
          tooltip="Somme des releves sur la periode selectionnee"
          evidenceId="conso-kwh-total"
          onEvidence={onEvidence}
        />
        <KpiTile
          icon={Euro}
          label="EUR total"
          value={eurLabel}
          sub={eurSource}
          tooltip={`Calcul : ${eurSource}. Basé sur les prix HP/HC du contrat ou estimés.`}
        />
        <KpiTile
          icon={TrendingUp}
          label="Prix unitaire"
          value={eurMwhLabel}
          tooltip="Prix moyen = EUR total / MWh total"
        />
        <KpiTile
          icon={Leaf}
          label={getKpiLabel('total_kgco2e', isExpert)}
          value={co2Label}
          sub="ADEME 2024"
          tooltip="Facteur ADEME 2024 : 0,052 kgCO2e/kWh (mix France)"
          evidenceId="conso-co2e"
          onEvidence={onEvidence}
        />
        <KpiTile
          icon={Activity}
          label={getKpiLabel('p95_kw', isExpert)}
          value={p95Label}
          tooltip="95e percentile de puissance sur les creneaux horaires"
        />
        <KpiTile
          icon={Moon}
          label={getKpiLabel('night_ratio', isExpert)}
          value={basePctLabel}
          color={basePctColor}
          tooltip="Ratio consommation nuit (22h-6h) / jour (6h-22h) en semaine"
        />
      </div>
    </div>
  );
}
