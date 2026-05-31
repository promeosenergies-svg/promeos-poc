/**
 * PROMEOS — OffHoursAnalysisCard (Sprint Énergie P3.2).
 *
 * Affiche la synthèse « Consommation hors horaires » :
 * - 4 KPI cards (off_hours_kwh, off_hours_share_pct, weekend_off_hours_kwh,
 *   night_baseload_kw) ;
 * - résumé horaires déclarés (badge source + plages) ;
 * - liste recommandations FR métier ;
 * - CTA Centre d'action.
 *
 * Doctrine zéro calcul métier frontend : KPI, status, recommandations
 * arrivent prêts du backend `/api/energy/off-hours-analysis`.
 *
 * Props :
 * - payload     : OffHoursAnalysisResponse (schema P3.2)
 * - loading     : bool
 */
import React from 'react';
import { ArrowRight, Clock, HelpCircle, Info, Triangle, Zap } from 'lucide-react';
import KpiCardWithProvenance from './KpiCardWithProvenance';

const SOURCE_BADGE = {
  declared: {
    label: 'Horaires déclarés',
    tint: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  },
  default: { label: 'Horaires par défaut', tint: 'bg-blue-50 text-blue-700 border-blue-100' },
  missing: { label: 'Horaires non renseignés', tint: 'bg-gray-100 text-gray-600 border-gray-200' },
};

const SEVERITY_ICON = {
  info: { icon: Info, color: 'text-blue-500' },
  warning: { icon: Triangle, color: 'text-amber-500' },
  critical: { icon: Triangle, color: 'text-red-500' },
};

function ProvenanceDot({ provenance, testId = 'off-hours-recommendation-provenance' }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid={testId}>
      <HelpCircle size={11} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <span className="absolute right-0 top-4 z-10 hidden group-hover:block w-64 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-700 shadow-lg">
        <span className="block text-gray-500">Service</span>
        <span className="block font-mono break-words">{provenance.service}</span>
        {provenance.formula && (
          <>
            <span className="block text-gray-500 mt-1">Formule</span>
            <span className="block font-mono break-words">{provenance.formula}</span>
          </>
        )}
      </span>
    </span>
  );
}

function ScheduleSummary({ schedule }) {
  if (!schedule) return null;
  const badge = SOURCE_BADGE[schedule.source] || SOURCE_BADGE.missing;
  return (
    <div className="flex items-start gap-3 text-xs" data-testid="off-hours-schedule-summary">
      <span
        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-medium ${badge.tint}`}
        data-source={schedule.source}
      >
        <Clock size={11} aria-hidden="true" />
        {badge.label}
      </span>
      {schedule.source !== 'missing' && (
        <ul className="flex-1 flex flex-wrap gap-x-3 gap-y-1 text-gray-600">
          {(schedule.weekly_schedule || []).map((day) => (
            <li
              key={day.day_of_week}
              className={day.is_open ? 'text-gray-700' : 'text-gray-400 line-through'}
              data-testid={`off-hours-day-${day.day_of_week}`}
            >
              <span className="font-medium">{day.label.slice(0, 3)}.</span>{' '}
              {day.is_open && day.ranges?.length
                ? day.ranges.map((r) => `${r.start_time}-${r.end_time}`).join(', ')
                : 'fermé'}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function RecommendationItem({ rec }) {
  const { icon: Icon, color } = SEVERITY_ICON[rec.severity] || SEVERITY_ICON.info;
  return (
    <li
      className="flex items-start gap-2 text-xs"
      data-testid={`off-hours-recommendation-${rec.severity}`}
    >
      <Icon size={14} className={`shrink-0 mt-0.5 ${color}`} aria-hidden="true" />
      <div className="flex-1">
        <p className="font-semibold text-gray-800">{rec.title}</p>
        <p className="text-gray-600 leading-snug">{rec.description}</p>
        {rec.cta_label && rec.cta_to && (
          <a
            href={rec.cta_to}
            className="inline-flex items-center gap-1 mt-1 text-blue-700 hover:underline font-medium"
            data-testid="off-hours-recommendation-cta"
          >
            {rec.cta_label}
            <ArrowRight size={11} aria-hidden="true" />
          </a>
        )}
      </div>
      <ProvenanceDot provenance={rec.provenance} />
    </li>
  );
}

export default function OffHoursAnalysisCard({
  payload,
  loading = false,
  className = '',
  testId = 'off-hours-analysis-card',
}) {
  if (loading) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid="off-hours-loading"
      >
        <div className="animate-pulse h-32 bg-gray-100 rounded" />
      </div>
    );
  }

  if (!payload) return null;

  const { schedule, kpis = {}, recommendations = [], empty_state: emptyState } = payload;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 space-y-4 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
            <Zap size={14} className="text-blue-600" aria-hidden="true" />
            Consommation hors horaires
          </h3>
          <p className="text-[11px] text-gray-500 italic">
            Comparez la consommation mesurée aux horaires déclarés du site.
          </p>
        </div>
      </div>

      <ScheduleSummary schedule={schedule} />

      {emptyState ? (
        <div
          className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-4 text-center text-xs text-gray-600"
          data-testid="off-hours-empty-state"
        >
          {emptyState}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCardWithProvenance
              label={kpis.off_hours_kwh?.label || 'Conso hors horaires'}
              value={kpis.off_hours_kwh?.value}
              unit={kpis.off_hours_kwh?.unit || 'kWh'}
              state={kpis.off_hours_kwh?.state}
              provenance={kpis.off_hours_kwh?.provenance}
              testId="kpi-off-hours-kwh"
            />
            <KpiCardWithProvenance
              label={kpis.off_hours_share_pct?.label || 'Part hors horaires'}
              value={kpis.off_hours_share_pct?.value}
              unit={kpis.off_hours_share_pct?.unit || '%'}
              state={kpis.off_hours_share_pct?.state}
              provenance={kpis.off_hours_share_pct?.provenance}
              testId="kpi-off-hours-share-pct"
            />
            <KpiCardWithProvenance
              label={kpis.weekend_off_hours_kwh?.label || 'Week-end hors horaires'}
              value={kpis.weekend_off_hours_kwh?.value}
              unit={kpis.weekend_off_hours_kwh?.unit || 'kWh'}
              state={kpis.weekend_off_hours_kwh?.state}
              provenance={kpis.weekend_off_hours_kwh?.provenance}
              testId="kpi-weekend-off-hours-kwh"
            />
            <KpiCardWithProvenance
              label={kpis.night_baseload_kw?.label || 'Talon nuit'}
              value={kpis.night_baseload_kw?.value}
              unit={kpis.night_baseload_kw?.unit || 'kW'}
              state={kpis.night_baseload_kw?.state}
              provenance={kpis.night_baseload_kw?.provenance}
              testId="kpi-night-baseload-kw"
            />
          </div>

          {recommendations.length > 0 && (
            <ul
              className="space-y-2 border-t border-gray-100 pt-3"
              data-testid="off-hours-recommendations"
            >
              {recommendations.map((rec, idx) => (
                <RecommendationItem key={`${rec.title}-${idx}`} rec={rec} />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
