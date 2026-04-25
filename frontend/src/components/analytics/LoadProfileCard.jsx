/**
 * LoadProfileCard — Profil de charge site360.
 *
 * Visualise le profil horaire type 24h + 5 KPIs clés :
 *  baseload P5, load factor, ratios nuit/jour et semaine/WE, score qualité.
 *
 * Source : GET /api/usages/load-profile/{siteId}
 */

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Activity, AlertTriangle, CheckCircle2, Moon } from 'lucide-react';
import { Card, CardBody, CardHeader } from '../../ui';
import { getLoadProfile } from '../../services/api/enedis';
import { fmtNum } from '../../utils/format';

const QUALITY_COLORS = {
  excellent: 'text-green-700 bg-green-100',
  bon: 'text-green-700 bg-green-50',
  acceptable: 'text-yellow-700 bg-yellow-100',
  insuffisant: 'text-red-700 bg-red-100',
};

const VERDICT_COLORS = {
  normal: 'text-green-700 bg-green-100',
  modere: 'text-yellow-700 bg-yellow-100',
  eleve: 'text-red-700 bg-red-100',
};

function KpiTile({ label, value, unit, sublabel, color, icon: Icon }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-1">
        {Icon && <Icon size={14} className="text-gray-400" />}
        <span className="text-xs uppercase tracking-wide text-gray-500 font-medium">{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className={`text-xl font-bold ${color || 'text-gray-800'}`}>{value}</span>
        {unit && <span className="text-xs text-gray-500">{unit}</span>}
      </div>
      {sublabel && <div className="text-xs text-gray-500 mt-0.5">{sublabel}</div>}
    </div>
  );
}

function HourlyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800">
        {String(d.hour).padStart(2, '0')}:00 — {String(d.hour + 1).padStart(2, '0')}:00
      </p>
      <p className="text-gray-600">{fmtNum(d.kwh, 2)} kWh moyen</p>
    </div>
  );
}

export default function LoadProfileCard({ siteId, months = 12 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stale = false;
    setLoading(true);
    setError(null);
    getLoadProfile(siteId, months)
      .then((d) => {
        if (!stale) setData(d);
      })
      .catch((e) => {
        if (!stale) setError(e?.response?.data?.detail || 'Profil de charge indisponible');
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId, months]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-gray-700">Profil de charge</h3>
        </CardHeader>
        <CardBody>
          <div className="animate-pulse h-48 bg-gray-100 rounded" />
        </CardBody>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-gray-700">Profil de charge</h3>
        </CardHeader>
        <CardBody>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle size={16} className="text-gray-400" />
            {error || 'Aucune donnée disponible'}
          </div>
        </CardBody>
      </Card>
    );
  }

  const hourlyData = (data.hourly_profile || []).map((kwh, hour) => ({ hour, kwh }));
  const peakHour = hourlyData.reduce((max, p) => (p.kwh > max.kwh ? p : max), { kwh: 0, hour: 0 });
  const baseload = data.baseload || {};
  const ratios = data.ratios || {};
  const quality = data.data_quality || {};
  const qualityClass = QUALITY_COLORS[quality.label] || QUALITY_COLORS.insuffisant;
  const verdictClass = VERDICT_COLORS[baseload.verdict] || VERDICT_COLORS.normal;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-700">Profil de charge</h3>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${qualityClass}`}
              title={`Données : ${quality.label}`}
            >
              Qualité : {quality.label || '—'}
            </span>
            <span className="text-xs text-gray-500">
              {data.period_days || 0} jours ·{' '}
              <span className="font-mono">{data.data_source || '—'}</span>
            </span>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {/* Chart */}
        <div className="h-48 mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourlyData}>
              <XAxis dataKey="hour" tick={{ fontSize: 10 }} tickFormatter={(h) => `${h}h`} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<HourlyTooltip />} />
              <Bar dataKey="kwh" radius={[2, 2, 0, 0]}>
                {hourlyData.map((entry) => (
                  <Cell
                    key={entry.hour}
                    fill={entry.hour === peakHour.hour ? '#3b82f6' : '#93c5fd'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* KPI grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiTile
            label="Baseload P5"
            value={fmtNum(baseload.p5_kwh, 1)}
            unit="kWh"
            sublabel={`${baseload.baseload_pct_of_mean || 0}% moy · ${baseload.verdict || '-'}`}
            color={verdictClass.split(' ')[0]}
            icon={Moon}
          />
          <KpiTile
            label="Load factor"
            value={fmtNum(data.load_factor, 2)}
            sublabel={data.load_factor < 0.2 ? 'Pics marqués' : 'Usage régulier'}
            icon={Activity}
          />
          <KpiTile
            label="Nuit / Jour"
            value={fmtNum(ratios.night_day, 2)}
            sublabel={
              ratios.night_day > 0.5
                ? 'Conso nocturne élevée'
                : ratios.night_day > 0.2
                  ? 'Modérée'
                  : 'Site vide la nuit'
            }
          />
          <KpiTile
            label="WE / Semaine"
            value={fmtNum(ratios.weekend_weekday, 2)}
            sublabel={
              ratios.weekend_weekday > 0.7
                ? 'Actif 7/7'
                : ratios.weekend_weekday < 0.2
                  ? 'Fermé WE'
                  : 'Réduit WE'
            }
            icon={CheckCircle2}
          />
        </div>

        {/* Peak info */}
        <div className="mt-3 flex items-center gap-2 text-xs text-gray-500">
          <span className="w-2 h-2 rounded-full bg-blue-500" />
          <span>
            Pic moyen à <strong className="text-gray-700">{peakHour.hour}h00</strong> (
            {fmtNum(peakHour.kwh, 1)} kWh)
          </span>
        </div>
      </CardBody>
    </Card>
  );
}
