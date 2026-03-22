/**
 * PROMEOS — PerformanceSnapshot v2
 * 5-KPI compact sticky banner for ConsumptionExplorer.
 * Each card clickable → navigates to /monitoring with context.
 * Handles single-site, multi-site, and no-data states.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, CheckCircle, Zap, Clock, Thermometer, TrendingUp, PlayCircle } from 'lucide-react';
import { Card, CardBody } from '../ui';
import { getMonitoringKpis } from '../services/api';
import { fmtNum } from '../utils/format';
import ConsoSourceBadge from './ConsoSourceBadge';

// Legacy severity color map — prefer SEVERITY_TINT from ui/colorTokens for new code
export const SEVERITY_COLOR = {
  critical: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  high: 'bg-orange-50 text-orange-700 ring-1 ring-orange-200',
  warning: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  info: 'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

export function fmtN(v, d = 0) {
  const r = fmtNum(v, d);
  return r === '—' ? '-' : r;
}

export const PERF_KEYS = ['pmax_kw', 'risk', 'quality', 'off_hours', 'climate'];

function PerfCard({ icon: Icon, iconColor, title, value, sub, onClick }) {
  return (
    <Card
      className="cursor-pointer hover:ring-2 hover:ring-blue-200 transition-all"
      onClick={onClick}
    >
      <CardBody className="py-2.5 px-3">
        <div className="flex items-center gap-2">
          <Icon size={14} className={iconColor} />
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">
              {title}
            </p>
            <p className="text-sm font-bold text-slate-800">{value}</p>
            {sub && <p className="text-[10px] text-slate-400 truncate">{sub}</p>}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

export default function PerformanceSnapshot({ siteId, siteIds, dateFrom, dateTo, className = '' }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);

  const isMulti = siteIds && siteIds.length > 1;
  const targetId = isMulti ? null : siteId || (siteIds && siteIds[0]);

  useEffect(() => {
    if (!targetId) {
      setLoading(false);
      setHasData(false);
      return;
    }
    setLoading(true);
    getMonitoringKpis(targetId)
      .then((kpiRes) => {
        if (kpiRes && kpiRes.kpis) {
          setData(kpiRes);
          setHasData(true);
        } else {
          setHasData(false);
        }
      })
      .catch(() => setHasData(false))
      .finally(() => setLoading(false));
  }, [targetId]);

  const goToMonitoring = () => {
    const params = new URLSearchParams();
    if (targetId) params.set('site_id', targetId);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    navigate(`/monitoring?${params.toString()}`);
  };

  if (loading) {
    return (
      <div className={`animate-pulse flex gap-2 ${className}`}>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex-1 h-16 bg-slate-100 rounded-lg" />
        ))}
      </div>
    );
  }

  // Multi-site: portfolio badge
  if (isMulti) {
    return (
      <Card className={className}>
        <CardBody className="py-3 px-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-50">
            <TrendingUp size={16} className="text-indigo-500" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-700">Performance Portfolio</p>
            <p className="text-xs text-slate-400">
              {siteIds.length} sites — Analyse individuelle requise
            </p>
          </div>
          <button
            onClick={goToMonitoring}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 transition flex items-center gap-1 whitespace-nowrap"
          >
            Voir Performance <TrendingUp size={10} />
          </button>
        </CardBody>
      </Card>
    );
  }

  // No data: CTA to launch analysis
  if (!hasData) {
    return (
      <Card className={className}>
        <CardBody className="py-3 px-4 flex items-center gap-3">
          <div className="p-2 rounded-lg bg-slate-100">
            <PlayCircle size={16} className="text-slate-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-slate-700">Aucune analyse de performance</p>
            <p className="text-xs text-slate-400">
              Lancez une analyse pour obtenir les KPI de risque, qualité et consommation.
            </p>
          </div>
          <button
            onClick={goToMonitoring}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 transition flex items-center gap-1 whitespace-nowrap"
          >
            <PlayCircle size={10} /> Lancer analyse
          </button>
        </CardBody>
      </Card>
    );
  }

  // Single site with data: 5 KPI cards
  const kpis = data.kpis || {};
  const riskScore = data.risk_power_score;
  const qualityScore = data.data_quality_score;
  const climate = data.climate;
  const offHoursRatio = kpis.off_hours_ratio;
  const schedule = data.schedule;

  return (
    <div className={`grid grid-cols-2 md:grid-cols-5 gap-2 ${className}`}>
      <PerfCard
        icon={Zap}
        iconColor="text-amber-500"
        title="Pmax"
        value={kpis.pmax_kw != null ? `${fmtN(kpis.pmax_kw)} kW` : '-'}
        sub={
          kpis.pmax_kw != null ? (
            <span className="flex items-center gap-1">
              {kpis.p95_kw != null && `P95: ${fmtN(kpis.p95_kw)} kW`}
              <ConsoSourceBadge source="metered" />
            </span>
          ) : null
        }
        onClick={goToMonitoring}
      />
      <PerfCard
        icon={Shield}
        iconColor={
          riskScore >= 60 ? 'text-red-500' : riskScore >= 35 ? 'text-orange-500' : 'text-green-500'
        }
        title="Risque"
        value={riskScore != null ? `${fmtN(riskScore)}/100` : '-'}
        sub={
          riskScore != null
            ? riskScore < 35
              ? 'Marge OK'
              : riskScore < 60
                ? 'Surveiller'
                : 'Critique'
            : null
        }
        onClick={goToMonitoring}
      />
      <PerfCard
        icon={CheckCircle}
        iconColor={
          qualityScore >= 80
            ? 'text-green-500'
            : qualityScore >= 60
              ? 'text-yellow-500'
              : 'text-red-500'
        }
        title="Qualité"
        value={qualityScore != null ? `${fmtN(qualityScore)}/100` : '-'}
        sub={
          qualityScore != null
            ? qualityScore >= 80
              ? 'Excellente'
              : qualityScore >= 60
                ? 'Correcte'
                : 'Dégradée'
            : null
        }
        onClick={goToMonitoring}
      />
      <PerfCard
        icon={Clock}
        iconColor={
          offHoursRatio != null
            ? offHoursRatio <= 0.2
              ? 'text-green-500'
              : offHoursRatio <= 0.4
                ? 'text-orange-500'
                : 'text-red-500'
            : 'text-slate-400'
        }
        title="Off-Hours"
        value={offHoursRatio != null ? `${fmtN(offHoursRatio * 100)}%` : '-'}
        sub={
          schedule
            ? schedule.is_24_7
              ? '24/7'
              : `${schedule.open_time}-${schedule.close_time}`
            : null
        }
        onClick={goToMonitoring}
      />
      <PerfCard
        icon={Thermometer}
        iconColor={climate?.r_squared >= 0.6 ? 'text-blue-500' : 'text-slate-400'}
        title="Climat"
        value={
          climate?.slope_kw_per_c != null ? `${fmtNum(climate.slope_kw_per_c, 1)} (kWh/j)/°C` : '-'
        }
        sub={climate?.r_squared != null ? `R²: ${fmtNum(climate.r_squared, 2)}` : null}
        onClick={goToMonitoring}
      />
    </div>
  );
}
