/**
 * PROMEOS — RegulatoryTimeline (Step 13)
 * Frise chronologique réglementaire : événements positionnés sur un axe temps.
 * Pur CSS/Tailwind, pas de librairie externe.
 *
 * Props :
 *   events   {Array}  — événements triés par deadline
 *   today    {string} — date ISO du jour
 *   loading  {boolean}
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, Clock, Calendar, ChevronRight } from 'lucide-react';
import { Explain } from '../../ui';

// --- Helpers ---

function daysBetween(a, b) {
  return Math.round((new Date(b) - new Date(a)) / 86400000);
}

import SolAcronym from '../../ui/sol/SolAcronym';

const FRAMEWORK_COLORS = {
  DECRET_TERTIAIRE: 'bg-blue-500',
  BACS: 'bg-purple-500',
  APER: 'bg-amber-500',
};

const FRAMEWORK_LABELS = {
  DECRET_TERTIAIRE: 'Décret Tertiaire',
  BACS: 'BACS',
  APER: 'APER',
};

const STATUS_STYLES = {
  passed: {
    dot: 'bg-red-500 border-red-200',
    dotOk: 'bg-green-500 border-green-200',
    text: 'text-red-700',
    bg: 'bg-red-50',
    label: 'Échue',
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
    label: 'À planifier',
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
          className={`px-1.5 py-0.5 rounded text-[11px] font-bold uppercase text-white ${FRAMEWORK_COLORS[evt.framework] || 'bg-gray-500'}`}
        >
          <SolAcronym code={FRAMEWORK_LABELS[evt.framework]}>
            {FRAMEWORK_LABELS[evt.framework] || evt.framework}
          </SolAcronym>
        </span>
        <span className={`text-xs font-medium ${style.text}`}>{style.label}</span>
      </div>
      <p className="text-xs font-semibold text-gray-800 mb-1">{evt.label}</p>
      <p className="text-[11px] text-gray-500 mb-2">{evt.description}</p>
      <div className="flex items-center gap-3 text-xs text-gray-400">
        <span>
          {evt.sites_concerned} site{evt.sites_concerned !== 1 ? 's' : ''} concerné
          {evt.sites_concerned !== 1 ? 's' : ''}
        </span>
        {evt.sites_non_compliant > 0 && (
          <span className="text-red-500 font-semibold">
            {evt.sites_non_compliant} non conforme{evt.sites_non_compliant !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      {evt.penalty_eur != null && (
        <p className="text-xs text-red-500 mt-1">
          Pénalité : {evt.penalty_eur.toLocaleString('fr-FR')} €
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
    Math.max(new Date(dates[dates.length - 1]), new Date(today).getTime() + 365 * 4 * 86400000)
  )
    .toISOString()
    .slice(0, 10);

  const totalDays = Math.max(daysBetween(minDate, maxDate), 1);
  const todayPct = (daysBetween(minDate, today) / totalDays) * 100;

  // Anti-collision: compute stagger levels for events that are too close
  const MIN_GAP_PCT = 20; // minimum % distance before staggering (label ~120px on ~800px axis)
  const eventsWithLayout = events
    .map((evt) => ({
      ...evt,
      leftPct: (daysBetween(minDate, evt.deadline) / totalDays) * 100,
    }))
    .sort((a, b) => a.leftPct - b.leftPct);

  // Assign stagger level: alternate above/below, with overflow levels further out
  for (let i = 0; i < eventsWithLayout.length; i++) {
    const evt = eventsWithLayout[i];
    let level = 0;
    const usedLevels = new Set();
    for (let j = i - 1; j >= 0; j--) {
      const prev = eventsWithLayout[j];
      if (evt.leftPct - prev.leftPct > MIN_GAP_PCT) break;
      usedLevels.add(prev._level);
    }
    while (usedLevels.has(level)) level++;
    evt._level = level;
  }

  const maxLevel = Math.max(0, ...eventsWithLayout.map((e) => e._level));

  // Layout constants per level — 6 levels for dense timelines
  const AXIS_Y = 180;
  const levelOffsets = [
    { labelY: 70, dotY: AXIS_Y - 8 }, // level 0: above axis
    { labelY: AXIS_Y + 28, dotY: AXIS_Y - 8 }, // level 1: below axis
    { labelY: 2, dotY: AXIS_Y - 8 }, // level 2: further above (68px gap from level 0)
    { labelY: AXIS_Y + 96, dotY: AXIS_Y - 8 }, // level 3: further below (68px gap from level 1)
    { labelY: -50, dotY: AXIS_Y - 8 }, // level 4: top
    { labelY: AXIS_Y + 160, dotY: AXIS_Y - 8 }, // level 5: bottom
  ];

  return (
    <div className="relative w-full overflow-x-auto pb-4 px-12">
      {/* Axis — min-w increased for readability with many events */}
      <div
        className="relative min-w-[900px]"
        style={{
          height: `${AXIS_Y + (maxLevel >= 5 ? 160 : maxLevel >= 3 ? 120 : maxLevel >= 1 ? 80 : 60)}px`,
        }}
      >
        {/* Horizontal line */}
        <div className="absolute left-0 right-0 h-0.5 bg-gray-200" style={{ top: `${AXIS_Y}px` }} />

        {/* Today marker */}
        <div
          className="absolute w-px border-l-2 border-dashed border-red-400"
          style={{ left: `${todayPct}%`, top: '30px', height: `${AXIS_Y - 20}px` }}
        >
          <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-xs font-bold text-red-500 whitespace-nowrap bg-white px-1 rounded">
            Aujourd'hui
          </span>
        </div>

        {/* Events */}
        {eventsWithLayout.map((evt) => {
          const style = STATUS_STYLES[evt.status] || STATUS_STYLES.future;
          const isPassedOk = evt.status === 'passed' && evt.sites_non_compliant === 0;
          const dotClass = isPassedOk ? style.dotOk || style.dot : style.dot;
          const layout = levelOffsets[Math.min(evt._level, levelOffsets.length - 1)];
          const isBelow = evt._level % 2 === 1; // odd levels are below axis

          return (
            <div
              key={evt.id}
              className="absolute cursor-pointer group"
              style={{ left: `${evt.leftPct}%`, top: 0, height: '100%' }}
              onMouseEnter={() => setHoveredId(evt.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => navigate(`/conformite?framework=${evt.framework.toLowerCase()}`)}
            >
              {/* Stem line from dot to label */}
              <div
                className="absolute w-px bg-gray-300 left-0 -translate-x-1/2"
                style={{
                  top: isBelow ? `${AXIS_Y + 6}px` : `${layout.labelY + 50}px`,
                  height: isBelow
                    ? `${Math.max(6, layout.labelY - AXIS_Y - 10)}px`
                    : `${Math.max(6, AXIS_Y - layout.labelY - 56)}px`,
                }}
              />

              {/* Label */}
              <div
                className="absolute left-1/2 -translate-x-1/2 w-[130px] text-center"
                style={{ top: `${layout.labelY}px` }}
              >
                <span
                  className={`inline-block px-1.5 py-0.5 rounded text-[7px] font-bold uppercase text-white mb-0.5 leading-none ${FRAMEWORK_COLORS[evt.framework] || 'bg-gray-500'}`}
                >
                  <SolAcronym code={FRAMEWORK_LABELS[evt.framework]}>
                    {FRAMEWORK_LABELS[evt.framework] || evt.framework}
                  </SolAcronym>
                </span>
                <p className="text-[11px] font-semibold text-gray-700 leading-tight line-clamp-2">
                  {evt.label}
                </p>
                <p
                  className={`text-[10px] font-medium ${new Date(evt.deadline) < new Date(today) ? 'text-red-500 font-semibold' : 'text-gray-500'}`}
                >
                  {new Date(evt.deadline) < new Date(today) ? 'Échue · ' : ''}
                  {formatDate(evt.deadline)}
                </p>
              </div>

              {/* Dot on axis */}
              <div
                className={`absolute w-3.5 h-3.5 rounded-full border-2 ${dotClass} -translate-x-1/2`}
                style={{ top: `${AXIS_Y - 6}px` }}
              />

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
                  className="absolute text-xs text-gray-400 font-mono"
                  style={{ left: `${pct}%`, top: `${AXIS_Y}px` }}
                >
                  <div className="w-px h-3 bg-gray-300 mb-0.5" />
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
        const dotClass = isPassedOk ? style.dotOk || style.dot : style.dot;
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
                  <SolAcronym code={FRAMEWORK_LABELS[evt.framework]}>
                    {FRAMEWORK_LABELS[evt.framework] || evt.framework}
                  </SolAcronym>
                </span>
                <span className={`text-xs font-medium ${style.text}`}>{style.label}</span>
              </div>
              <p className="text-sm font-semibold text-gray-800">{evt.label}</p>
              <p
                className={`text-xs mt-0.5 ${isPast ? 'text-red-600 font-medium' : 'text-gray-500'}`}
              >
                {isPast
                  ? `Échéance dépassée depuis le ${formatDate(evt.deadline)}`
                  : `${formatDate(evt.deadline)} — dans ${daysBetween(today, evt.deadline)} jours`}
              </p>
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                <span>
                  {evt.sites_concerned} site{evt.sites_concerned !== 1 ? 's' : ''}
                </span>
                {evt.sites_non_compliant > 0 && (
                  <span className="text-red-500 font-semibold">
                    {evt.sites_non_compliant} non conforme{evt.sites_non_compliant !== 1 ? 's' : ''}
                  </span>
                )}
                {evt.penalty_eur != null && (
                  <span className="text-red-500">{evt.penalty_eur.toLocaleString('fr-FR')} €</span>
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

export default function RegulatoryTimeline({
  events = [],
  today,
  loading = false,
  compact = false,
}) {
  if (loading) return <TimelineSkeleton />;
  if (!events.length) {
    return (
      <div className="text-center py-6 text-sm text-gray-400">
        Aucune échéance réglementaire identifiée.
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
            <Explain term="timeline_reglementaire">Frise réglementaire</Explain>
          </h3>
          <div className="flex items-center gap-2 text-xs">
            {passedNonCompliant.length > 0 && (
              <span className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-50 text-red-600 font-medium">
                <AlertTriangle size={10} />
                {passedNonCompliant.length} échéance{passedNonCompliant.length > 1 ? 's' : ''}{' '}
                dépassée{passedNonCompliant.length > 1 ? 's' : ''}
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
                Exposition : {totalPenalty.toLocaleString('fr-FR')} €
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
