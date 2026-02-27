/**
 * PROMEOS — HorairesAnomaliesTab
 * Tab 2: Horaires d'activité + Anomalies + behavior_score.
 */
import { Card, CardBody, Badge, KpiCard } from '../../ui';
import { AlertTriangle, Clock, Building2, Calendar } from 'lucide-react';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

const SEV_VARIANT = { critical: 'crit', high: 'warn', medium: 'info', low: 'neutral' };

function ScheduleDisplay({ schedule }) {
  if (!schedule) return null;

  const openDays = (schedule.open_days || '0,1,2,3,4').split(',').map(Number);
  const openH = parseInt((schedule.open_time || '08:00').split(':')[0], 10);
  const closeH = parseInt((schedule.close_time || '19:00').split(':')[0], 10);

  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-indigo-500" />
          <h3 className="text-sm font-semibold text-gray-700">Horaires d'activité</h3>
          <Badge variant="neutral">{schedule.source || 'default'}</Badge>
          {schedule.is_24_7 && <Badge variant="info">24/7</Badge>}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {DAY_LABELS.map((label, d) => {
            const isOpen = openDays.includes(d);
            return (
              <div key={d} className="text-center">
                <div className="text-[10px] text-gray-400 mb-1">{label}</div>
                <div className={`h-6 rounded text-[10px] flex items-center justify-center ${isOpen ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'}`}>
                  {isOpen ? `${openH}h-${closeH}h` : 'Fermé'}
                </div>
              </div>
            );
          })}
        </div>
      </CardBody>
    </Card>
  );
}

function ArchetypeCard({ archetype, nafCode }) {
  if (!archetype) {
    return (
      <Card>
        <CardBody>
          <div className="flex items-center gap-2 mb-2">
            <Building2 className="w-4 h-4 text-indigo-500" />
            <h3 className="text-sm font-semibold text-gray-700">Archétype</h3>
          </div>
          <p className="text-xs text-gray-400">
            {nafCode ? `NAF ${nafCode} — aucun archétype trouvé` : 'Aucun code NAF renseigné'}
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-2 mb-2">
          <Building2 className="w-4 h-4 text-indigo-500" />
          <h3 className="text-sm font-semibold text-gray-700">Archétype</h3>
        </div>
        <p className="text-sm font-medium">{archetype.title}</p>
        <p className="text-xs text-gray-500 mt-1">
          Benchmark : {archetype.kwh_m2_min}–{archetype.kwh_m2_max} kWh/m² (moy. {archetype.kwh_m2_avg})
        </p>
        {archetype.segment_tags?.length > 0 && (
          <div className="flex gap-1 mt-2 flex-wrap">
            {archetype.segment_tags.map((t) => <Badge key={t} variant="neutral">{t}</Badge>)}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function ScoreBadge({ score, breakdown }) {
  if (score == null) return null;

  const items = [
    { label: 'Hors horaires', value: breakdown?.offhours_penalty ?? 0, max: 40 },
    { label: 'Talon', value: breakdown?.baseload_penalty ?? 0, max: 25 },
    { label: 'Dérive', value: breakdown?.drift_penalty ?? 0, max: 20 },
    { label: 'Weekend', value: breakdown?.weekend_penalty ?? 0, max: 15 },
  ];

  const color = score >= 80 ? 'text-emerald-600' : score >= 50 ? 'text-amber-600' : 'text-red-600';
  const ring = score >= 80 ? 'ring-emerald-200' : score >= 50 ? 'ring-amber-200' : 'ring-red-200';

  return (
    <Card>
      <CardBody>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-full ring-4 ${ring} flex items-center justify-center`}>
            <span className={`text-2xl font-bold ${color}`}>{score}</span>
          </div>
          <div className="flex-1 space-y-1">
            {items.map((it) => (
              <div key={it.label} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-24">{it.label}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-indigo-400 h-2 rounded-full"
                    style={{ width: `${Math.min(100, (it.value / it.max) * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-8 text-right">-{it.value}</span>
              </div>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function AnomalyList({ insights }) {
  const top5 = (insights || []).slice(0, 5);
  if (!top5.length) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-gray-400 text-center py-4">Aucune anomalie détectée</p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card>
      <CardBody>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          Anomalies ({insights.length})
        </h3>
        <div className="space-y-2">
          {top5.map((ins, i) => (
            <div key={ins.id || i} className="flex items-start gap-3 p-2 rounded bg-gray-50">
              <Badge variant={SEV_VARIANT[ins.severity] || 'neutral'}>{ins.severity}</Badge>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-700">{ins.message || ins.type}</p>
                {ins.estimated_loss_eur != null && (
                  <p className="text-xs text-gray-400 mt-0.5">Perte estimée : {ins.estimated_loss_eur} €</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function WeekendActiveAlert({ weekendActive }) {
  if (!weekendActive?.detected) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center gap-2 mb-1">
        <Calendar className="w-4 h-4 text-amber-600" />
        <span className="text-sm font-semibold text-amber-700">Activité weekend détectée</span>
        <Badge variant={weekendActive.severity === 'high' ? 'crit' : 'warn'}>{weekendActive.severity}</Badge>
      </div>
      <p className="text-xs text-amber-600">{weekendActive.message}</p>
    </div>
  );
}

export default function HorairesAnomaliesTab({ activity, anomalies, siteId, loading }) {
  if (loading) return <Card><CardBody><div className="h-64 animate-pulse bg-gray-100 rounded" /></CardBody></Card>;

  return (
    <div className="space-y-6">
      <ScheduleDisplay schedule={activity?.schedule} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ArchetypeCard archetype={activity?.archetype} nafCode={activity?.naf_code} />
        <ScoreBadge score={anomalies?.behavior_score} breakdown={anomalies?.score_breakdown} />
      </div>

      <WeekendActiveAlert weekendActive={anomalies?.weekend_active} />

      <AnomalyList insights={anomalies?.insights} />
    </div>
  );
}
