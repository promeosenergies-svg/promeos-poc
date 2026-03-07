/**
 * PROMEOS — RegulatoryTimeline (Step 13)
 * Frise chronologique reglementaire : evenements positionnes sur un axe temps.
 * Pur CSS/Tailwind, pas de librairie externe.
 *
 * Props :
 *   events   {Array}  — evenements tries par deadline
 *   today    {string} — date ISO du jour
 *   loading  {boolean}
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck, AlertTriangle, Clock, Calendar, ChevronRight } from 'lucide-react';
import { Explain } from '../../ui';

// --- Helpers ---

function daysBetween(a, b) {
  return Math.round((new Date(b) - new Date(a)) / 86400000);
}

const FRAMEWORK_COLORS = {
  DECRET_TERTIAIRE: 'bg-blue-500',
  BACS: 'bg-purple-500',
  APER: 'bg-amber-500',
};

const FRAMEWORK_LABELS = {
  DECRET_TERTIAIRE: 'Decret Tertiaire',
  BACS: 'BACS',
  APER: 'APER',
};

const STATUS_STYLES = {
  passed: {
    dot: 'bg-red-500 border-red-200',
    dotOk: 'bg-green-500 border-green-200',
    text: 'text-red-700',
    bg: 'bg-red-50',
    label: 'Echue',
  },
  upcoming: {
    dot: 'bg-orange-500 border-orange-200',
    text: 'text-orange-700',
    bg: 'bg-orange-50',
    label: '< 12 mois',
  },
  future: {
    dot: 'bg-blue-500 border-blue-200',
    text: 'text-blue-700',
    bg: 'bg-blue-50',
    label: 'A planifier',
  },
};

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

// --- Tooltip card ---

function EventTooltip({ evt }) {
  const style = STATUS_STYLES[evt.status] || STATUS_STYLES.future;
  return (
    <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 p-3 text-left pointer-events-none">
      <div className="flex items-center gap-2 mb-1">
        <span
          className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase text-white ${FRAMEWORK_COLORS[evt.framework] || 'bg-gray-500'}`}
        >
          {FRAMEWORK_LABELS[evt.framework] || evt.framework}
        </span>
        <span className={`text-[10px] font-medium ${style.text}`}>{style.label}</span>
      </div>
      <p className="text-xs font-semibold text-gray-800 mb-1">{evt.label}</p>
      <p className="text-[11px] text-gray-500 mb-2">{evt.description}</p>
      <div className="flex items-center gap-3 text-[10px] text-gray-400">
        <span>{evt.sites_concerned} site{evt.sites_concerned !== 1 ? 's' : ''} concerne{evt.sites_concerned !== 1 ? 's' : ''}</span>
        {evt.sites_non_compliant > 0 && (
          <span className="text-red-500 font-semibold">
            {evt.sites_non_compliant} non conforme{evt.sites_non_compliant !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      {evt.penalty_eur != null && (
        <p className="text-[10px] text-red-500 mt-1">
          Penalite : {evt.penalty_eur.toLocaleString('fr-FR')} EUR
        </p>
      )}
    </div>
  );
}

// --- Desktop horizontal timeline ---

function HorizontalTimeline({ events, today }) {
  const [hoveredId, setHoveredId] = useState(null);
  const navigate = useNavigate();

  if (!events.length) return null;

  // Compute axis range: min(first event, today-90) to max(last event, today+365*4)
  const dates = events.map((e) => e.deadline);
  const minDate = new Date(Math.min(new Date(dates[0]), new Date(today) - 90 * 86400000))
    .toISOString()
    .slice(0, 10);
  const maxDate = new Date(
    Math.max(
      new Date(dates[dates.length - 1]),
      new Date(today).getTime() + 365 * 4 * 86400000
    )
  )
    .toISOString()
    .slice(0, 10);

  const totalDays = Math.max(daysBetween(minDate, maxDate), 1);
  const todayPct = (daysBetween(minDate, today) / totalDays) * 100;

  return (
    <div className="relative w-full overflow-x-auto pb-2 px-12">
      {/* Axis */}
      <div className="relative h-32 min-w-[600px]">
        {/* Horizontal line */}
        <div className="absolute top-16 left-0 right-0 h-0.5 bg-gray-200" />

        {/* Today marker */}
        <div
          className="absolute top-4 h-24 w-px border-l-2 border-dashed border-red-400"
          style={{ left: `${todayPct}%` }}
        >
          <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[9px] font-bold text-red-500 whitespace-nowrap bg-white px-1">
            Aujourd'hui
          </span>
        </div>

        {/* Events */}
        {events.map((evt) => {
          const leftPct = (daysBetween(minDate, evt.deadline) / totalDays) * 100;
          const style = STATUS_STYLES[evt.status] || STATUS_STYLES.future;
          const isPassedOk = evt.status === 'passed' && evt.sites_non_compliant === 0;
          const dotClass = isPassedOk ? style.dotOk || style.dot : style.dot;

          return (
            <div
              key={evt.id}
              className="absolute cursor-pointer group"
              style={{ left: `${leftPct}%`, top: '8px' }}
              onMouseEnter={() => setHoveredId(evt.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => navigate(`/conformite?framework=${evt.framework.toLowerCase()}`)}
            >
              {/* Label above */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 w-24 text-center">
                <p className="text-[9px] font-medium text-gray-600 truncate">{evt.label}</p>
                <p className="text-[8px] text-gray-400">{formatDate(evt.deadline)}</p>
              </div>

              {/* Dot */}
              <div
                className={`w-3.5 h-3.5 rounded-full border-2 ${dotClass} -translate-x-1/2 relative`}
                style={{ top: '24px' }}
              />

              {/* Framework badge below */}
              <span
                className={`absolute top-10 left-1/2 -translate-x-1/2 px-1 py-0.5 rounded text-[7px] font-bold uppercase text-white whitespace-nowrap ${FRAMEWORK_COLORS[evt.framework] || 'bg-gray-500'}`}
              >
                {FRAMEWORK_LABELS[evt.framework] || evt.framework}
              </span>

              {/* Tooltip */}
              {hoveredId === evt.id && <EventTooltip evt={evt} />}
            </div>
          );
        })}

        {/* Year markers */}
        {(() => {
          const startYear = new Date(minDate).getFullYear();
          const endYear = new Date(maxDate).getFullYear();
          const markers = [];
          for (let y = startYear; y <= endYear; y++) {
            const yDate = `${y}-01-01`;
            const pct = (daysBetween(minDate, yDate) / totalDays) * 100;
            if (pct >= 0 && pct <= 100) {
              markers.push(
                <div
                  key={y}
                  className="absolute top-16 text-[9px] text-gray-300 font-mono"
                  style={{ left: `${pct}%` }}
                >
                  <div className="w-px h-2 bg-gray-200 mb-0.5" />
                  {y}
                </div>
              );
            }
          }
          return markers;
        })()}
      </div>
    </div>
  );
}

// --- Mobile vertical timeline ---

function VerticalTimeline({ events, today }) {
  const navigate = useNavigate();

  return (
    <div className="space-y-3">
      {events.map((evt) => {
        const style = STATUS_STYLES[evt.status] || STATUS_STYLES.future;
        const isPassedOk = evt.status === 'passed' && evt.sites_non_compliant === 0;
        const dotClass = isPassedOk ? (style.dotOk || style.dot) : style.dot;
        const isPast = new Date(evt.deadline) < new Date(today);

        return (
          <div
            key={evt.id}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer hover:shadow-sm transition ${style.bg} border-gray-200`}
            onClick={() => navigate(`/conformite?framework=${evt.framework.toLowerCase()}`)}
          >
            <div className={`w-3 h-3 rounded-full mt-1 shrink-0 ${dotClass}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span
                  className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase text-white ${FRAMEWORK_COLORS[evt.framework] || 'bg-gray-500'}`}
                >
                  {FRAMEWORK_LABELS[evt.framework] || evt.framework}
                </span>
                <span className={`text-[10px] font-medium ${style.text}`}>{style.label}</span>
              </div>
              <p className="text-sm font-semibold text-gray-800">{evt.label}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {formatDate(evt.deadline)}
                {!isPast && ` — dans ${daysBetween(today, evt.deadline)} jours`}
              </p>
              <div className="flex items-center gap-3 mt-1 text-[10px] text-gray-400">
                <span>{evt.sites_concerned} site{evt.sites_concerned !== 1 ? 's' : ''}</span>
                {evt.sites_non_compliant > 0 && (
                  <span className="text-red-500 font-semibold">
                    {evt.sites_non_compliant} non conforme{evt.sites_non_compliant !== 1 ? 's' : ''}
                  </span>
                )}
                {evt.penalty_eur != null && (
                  <span className="text-red-500">{evt.penalty_eur.toLocaleString('fr-FR')} EUR</span>
                )}
              </div>
            </div>
            <ChevronRight size={14} className="text-gray-300 mt-1 shrink-0" />
          </div>
        );
      })}
    </div>
  );
}

// --- Loading skeleton ---

function TimelineSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 bg-gray-100 rounded w-48" />
      <div className="h-32 bg-gray-50 rounded-lg border border-gray-100" />
    </div>
  );
}

// --- Main component ---

export default function RegulatoryTimeline({ events = [], today, loading = false, compact = false }) {
  if (loading) return <TimelineSkeleton />;
  if (!events.length) {
    return (
      <div className="text-center py-6 text-sm text-gray-400">
        Aucune echeance reglementaire identifiee.
      </div>
    );
  }

  const passedNonCompliant = events.filter(
    (e) => e.status === 'passed' && e.sites_non_compliant > 0
  );
  const upcoming = events.filter((e) => e.status === 'upcoming');
  const totalPenalty = events.reduce((s, e) => s + (e.penalty_eur || 0), 0);

  return (
    <div className="space-y-3">
      {/* Header with summary badges */}
      {!compact && (
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
            <Calendar size={16} className="text-blue-500" />
            <Explain term="timeline_reglementaire">Frise reglementaire</Explain>
          </h3>
          <div className="flex items-center gap-2 text-[10px]">
            {passedNonCompliant.length > 0 && (
              <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-50 text-red-600 font-medium">
                <AlertTriangle size={10} />
                {passedNonCompliant.length} echeance{passedNonCompliant.length > 1 ? 's' : ''} depassee{passedNonCompliant.length > 1 ? 's' : ''}
              </span>
            )}
            {upcoming.length > 0 && (
              <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-orange-50 text-orange-600 font-medium">
                <Clock size={10} />
                {upcoming.length} dans les 12 mois
              </span>
            )}
            {totalPenalty > 0 && (
              <span className="px-2 py-1 rounded-full bg-gray-50 text-gray-500 font-medium">
                Exposition : {totalPenalty.toLocaleString('fr-FR')} EUR
              </span>
            )}
          </div>
        </div>
      )}

      {/* Desktop: horizontal / Mobile: vertical */}
      <div className="hidden md:block">
        <HorizontalTimeline events={events} today={today} />
      </div>
      <div className="md:hidden">
        <VerticalTimeline events={events} today={today} />
      </div>
    </div>
  );
}
