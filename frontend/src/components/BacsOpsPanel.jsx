/**
 * PROMEOS - BacsOpsPanel
 * Operational monitoring panel for BACS: KPIs, consumption chart, heatmap, alerts.
 */
import { useState, useEffect } from 'react';
import { Clock, ShieldCheck, AlertTriangle, TrendingUp, Thermometer, Activity } from 'lucide-react';
import { Card, CardBody, KpiCardInline } from '../ui';
import { getBacsOpsPanel } from '../services/api';
import { fmtNum } from '../utils/format';

const DAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const HOURS = Array.from({ length: 24 }, (_, i) => `${i}h`);

function MonthlyChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-gray-400 text-center py-4">Pas de données mensuelles</p>;
  }

  const maxKwh = Math.max(...data.map((d) => d.kwh), 1);

  return (
    <div className="flex items-end gap-1 h-32 px-2">
      {data.map((d, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div
            className="w-full bg-blue-400 rounded-t transition-all duration-300 hover:bg-blue-500 min-h-[2px]"
            style={{ height: `${(d.kwh / maxKwh) * 100}%` }}
            title={`${d.month}: ${fmtNum(d.kwh, 0)} kWh`}
          />
          <span className="text-[9px] text-gray-400 -rotate-45 origin-top-left whitespace-nowrap">
            {d.month}
          </span>
        </div>
      ))}
    </div>
  );
}

function HeatmapGrid({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-gray-400 text-center py-4">Pas de données heatmap</p>;
  }

  const allValues = data.flat().filter((v) => v > 0);
  const maxVal = Math.max(...allValues, 1);

  const getColor = (val) => {
    if (val === 0) return 'bg-gray-100';
    const intensity = val / maxVal;
    if (intensity > 0.8) return 'bg-red-500';
    if (intensity > 0.6) return 'bg-orange-400';
    if (intensity > 0.4) return 'bg-amber-400';
    if (intensity > 0.2) return 'bg-yellow-300';
    return 'bg-green-200';
  };

  return (
    <div className="overflow-x-auto">
      <div className="grid grid-cols-[auto_repeat(24,1fr)] gap-px text-[9px]">
        {/* Header row */}
        <div />
        {HOURS.map((h) => (
          <div key={h} className="text-center text-gray-400 py-0.5">
            {h}
          </div>
        ))}
        {/* Data rows */}
        {data.map((row, d) => (
          <div key={d} className="contents">
            <div className="text-gray-500 pr-1 flex items-center">{DAYS[d]}</div>
            {row.map((val, h) => (
              <div
                key={h}
                className={`aspect-square rounded-sm ${getColor(val)} transition-colors`}
                title={`${DAYS[d]} ${h}h: ${val} kWh`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BacsOpsPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getBacsOpsPanel(siteId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-lg" />
          ))}
        </div>
        <div className="h-40 bg-gray-100 rounded-lg" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardBody className="text-center py-6 text-gray-400 text-sm">
          <AlertTriangle size={20} className="mx-auto mb-2" />
          Monitoring BACS non disponible pour ce site.
        </CardBody>
      </Card>
    );
  }

  const {
    kpis,
    consumption_findings,
    monthly_consumption,
    hourly_heatmap,
    cvc_alerts_stub: _cvc_alerts_stub,
  } = data;

  return (
    <div className="space-y-4">
      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KpiCardInline
          icon={Clock}
          label="Délai conformité"
          value={kpis.compliance_delay_days !== null ? `${kpis.compliance_delay_days}j` : '—'}
          sub={kpis.compliance_delay_days < 0 ? 'En retard' : 'Restants'}
          color={kpis.compliance_delay_days < 0 ? 'text-red-600' : 'text-green-600'}
        />
        <KpiCardInline
          icon={ShieldCheck}
          label="Prochaine inspection"
          value={
            kpis.inspection_countdown_days !== null ? `${kpis.inspection_countdown_days}j` : '—'
          }
          color={kpis.inspection_countdown_days < 0 ? 'text-red-600' : 'text-blue-600'}
        />
        <KpiCardInline
          icon={AlertTriangle}
          label="Alertes CVC"
          value={`${kpis.cvc_alerts_count}`}
          sub="Simulées"
          color={kpis.cvc_alerts_count > 0 ? 'text-amber-600' : 'text-green-600'}
        />
        <KpiCardInline
          icon={TrendingUp}
          label="Gain vs baseline"
          value={
            kpis.gains_vs_baseline_pct !== null
              ? `${kpis.gains_vs_baseline_pct > 0 ? '+' : ''}${kpis.gains_vs_baseline_pct}%`
              : '—'
          }
          color={kpis.gains_vs_baseline_pct < 0 ? 'text-green-600' : 'text-red-600'}
        />
      </div>

      {/* Monthly consumption */}
      <Card>
        <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
          <Activity size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">Consommation mensuelle</h3>
        </div>
        <CardBody>
          <MonthlyChart data={monthly_consumption} />
        </CardBody>
      </Card>

      {/* Hourly heatmap */}
      <Card>
        <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2">
          <Thermometer size={16} className="text-orange-500" />
          <h3 className="text-sm font-semibold text-gray-700">Heatmap horaire CVC</h3>
        </div>
        <CardBody>
          <HeatmapGrid data={hourly_heatmap} />
          <div className="flex items-center gap-2 mt-2 text-[9px] text-gray-400">
            <span>Faible</span>
            <div className="flex gap-px">
              <div className="w-3 h-3 rounded-sm bg-green-200" />
              <div className="w-3 h-3 rounded-sm bg-yellow-300" />
              <div className="w-3 h-3 rounded-sm bg-amber-400" />
              <div className="w-3 h-3 rounded-sm bg-orange-400" />
              <div className="w-3 h-3 rounded-sm bg-red-500" />
            </div>
            <span>Élevé</span>
          </div>
        </CardBody>
      </Card>

      {/* CVC Alerts — masqué (stub non actionnable, sera activé quand le backend CVC sera prêt) */}

      {/* Linked consumption findings */}
      {consumption_findings && consumption_findings.length > 0 && (
        <Card>
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700">Constats opérationnels liés</h3>
          </div>
          <CardBody className="space-y-2">
            {consumption_findings
              .filter((f) => f.bacs_context)
              .map((f, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 py-1.5 border-b border-gray-50 last:border-0"
                >
                  <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                    {f.type}
                  </span>
                  <p className="text-sm text-gray-700">{f.bacs_context}</p>
                </div>
              ))}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
