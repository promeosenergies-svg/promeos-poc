/**
 * PROMEOS — PerformanceSnapshot
 * Compact KPI strip for ConsumptionExplorer. Shows 3 key metrics + 1 insight + CTA.
 * Fetches latest monitoring data for a given site. Handles "no data" gracefully.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, CheckCircle, Zap, TrendingUp, AlertTriangle, PlayCircle } from 'lucide-react';
import { Card, CardBody, Badge } from '../ui';
import { getMonitoringKpis, getMonitoringAlerts } from '../services/api';

export const SEVERITY_COLOR = {
  critical: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  high:     'bg-orange-50 text-orange-700 ring-1 ring-orange-200',
  warning:  'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  info:     'bg-blue-50 text-blue-700 ring-1 ring-blue-200',
};

export function fmtN(v, d = 0) {
  if (v == null || isNaN(v)) return '-';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: d });
}

export default function PerformanceSnapshot({ siteId, siteIds, className = '' }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [topAlert, setTopAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);

  const isMulti = siteIds && siteIds.length > 1;
  const targetId = isMulti ? null : (siteId || (siteIds && siteIds[0]));

  useEffect(() => {
    if (!targetId) {
      setLoading(false);
      setHasData(false);
      return;
    }
    setLoading(true);
    Promise.all([
      getMonitoringKpis(targetId).catch(() => null),
      getMonitoringAlerts(targetId, 'open', 5).catch(() => []),
    ]).then(([kpiRes, alertsRes]) => {
      if (kpiRes && kpiRes.kpis) {
        setData(kpiRes);
        setHasData(true);
        const alerts = Array.isArray(alertsRes) ? alertsRes : [];
        const top = alerts
          .filter((a) => a.estimated_impact_eur > 0)
          .sort((a, b) => (b.estimated_impact_eur || 0) - (a.estimated_impact_eur || 0))[0];
        setTopAlert(top || null);
      } else {
        setHasData(false);
      }
      setLoading(false);
    });
  }, [targetId]);

  const goToMonitoring = () => {
    const params = new URLSearchParams();
    if (targetId) params.set('site_id', targetId);
    navigate(`/monitoring?${params.toString()}`);
  };

  if (loading) {
    return (
      <div className={`animate-pulse flex gap-3 ${className}`}>
        {[1, 2, 3, 4].map((i) => (
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
            <p className="text-xs text-slate-400">{siteIds.length} sites selectionnes — analyse individuelle requise</p>
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
            <p className="text-xs text-slate-400">Lancez une analyse pour obtenir les KPI de risque, qualite et consommation.</p>
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

  // Single site with data: 3 KPIs + insight + CTA
  const kpis = data.kpis || {};
  const riskScore = data.risk_power_score;
  const qualityScore = data.data_quality_score;

  return (
    <div className={`grid grid-cols-2 md:grid-cols-4 gap-2 ${className}`}>
      {/* Risk */}
      <Card>
        <CardBody className="py-2.5 px-3">
          <div className="flex items-center gap-2">
            <Shield size={14} className={riskScore >= 60 ? 'text-red-500' : riskScore >= 35 ? 'text-orange-500' : 'text-green-500'} />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Risque</p>
              <p className="text-sm font-bold text-slate-800">{riskScore != null ? `${fmtN(riskScore)}/100` : '-'}</p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Quality */}
      <Card>
        <CardBody className="py-2.5 px-3">
          <div className="flex items-center gap-2">
            <CheckCircle size={14} className={qualityScore >= 80 ? 'text-green-500' : qualityScore >= 60 ? 'text-yellow-500' : 'text-red-500'} />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Qualite</p>
              <p className="text-sm font-bold text-slate-800">{qualityScore != null ? `${fmtN(qualityScore)}/100` : '-'}</p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Pmax or Talon */}
      <Card>
        <CardBody className="py-2.5 px-3">
          <div className="flex items-center gap-2">
            <Zap size={14} className="text-amber-500" />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide">Pmax</p>
              <p className="text-sm font-bold text-slate-800">{kpis.pmax_kw != null ? `${fmtN(kpis.pmax_kw)} kW` : '-'}</p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Top insight / CTA */}
      <Card className="bg-slate-50/80">
        <CardBody className="py-2.5 px-3">
          {topAlert ? (
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-orange-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wide truncate">Alerte</p>
                <p className="text-xs text-slate-700 truncate">{fmtN(topAlert.estimated_impact_eur, 0)} EUR/an</p>
              </div>
              <button
                onClick={goToMonitoring}
                className="text-[10px] font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap"
              >
                Voir
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <TrendingUp size={14} className="text-blue-500 shrink-0" />
              <p className="text-xs text-slate-500 flex-1">Aucune alerte</p>
              <button
                onClick={goToMonitoring}
                className="text-[10px] font-medium text-blue-600 hover:text-blue-800 whitespace-nowrap"
              >
                Details
              </button>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
