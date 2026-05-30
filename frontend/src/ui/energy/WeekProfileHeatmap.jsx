/**
 * PROMEOS — WeekProfileHeatmap (Sprint P1.S4 UI Semaine type).
 *
 * Heatmap 7 jours (Lun → Dim) × 24 heures (0h → 23h) consommant la
 * `matrix` exposée par `/api/energy/week-profile`. La matrix est
 * éventuellement sparse : on remappe vers une grille indexée pour
 * l'affichage sans aucun calcul métier (pas d'agrégation, pas de
 * scoring, pas de détection pic — tout vient du backend).
 *
 * Convention :
 * - cell.day_of_week : 0 = Lun … 6 = Dim
 * - cell.hour        : 0 → 23
 * - cell.status      : 'normal' | 'vigilance' | 'critique' | 'missing'
 * - cell.quality_status : 'measured' | 'estimated' | 'missing'
 *
 * Doctrine :
 * - Aucun `Math.*`, `reduce`, agrégation métier ici.
 * - Couleurs déterminées par `cell.status` (déjà classé backend).
 * - Tooltip = formatage affichage uniquement.
 */
import { useMemo } from 'react';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

// Mapping cosmétique status backend → classes Tailwind.
// Pas de calcul métier : status est déjà fourni par le backend.
const STATUS_CLASS = {
  normal: 'bg-emerald-100 hover:bg-emerald-200 border-emerald-200',
  vigilance: 'bg-amber-200 hover:bg-amber-300 border-amber-300',
  critique: 'bg-red-300 hover:bg-red-400 border-red-400',
  missing: 'bg-gray-100 hover:bg-gray-150 border-gray-200',
};

const STATUS_LABEL = {
  normal: 'Normal',
  vigilance: 'Vigilance',
  critique: 'Critique',
  missing: 'Manquant',
};

const QUALITY_LABEL = {
  measured: 'mesuré',
  estimated: 'estimé',
  missing: 'manquant',
};

function fmtNumber(v) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 });
}

function CellTooltip({ cell }) {
  if (!cell) return null;
  return (
    <div
      className="absolute z-20 -translate-x-1/2 -translate-y-full top-0 left-1/2 mt-[-6px] w-44 rounded-lg border border-gray-200 bg-white p-2 shadow-lg text-[11px] text-gray-700 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"
      data-testid="heatmap-cell-tooltip"
    >
      <p className="font-semibold text-gray-800">
        {DAY_LABELS[cell.day_of_week]} · {String(cell.hour).padStart(2, '0')}h
      </p>
      <p className="mt-1 text-gray-500">
        Conso : <span className="font-mono text-gray-800">{fmtNumber(cell.kwh)} kWh</span>
      </p>
      <p className="text-gray-500">
        kW moyen : <span className="font-mono text-gray-800">{fmtNumber(cell.kw_avg)}</span>
      </p>
      <p className="text-gray-500">
        État : <span className="font-medium">{STATUS_LABEL[cell.status] || cell.status}</span>
      </p>
      <p className="text-gray-500">
        Qualité :{' '}
        <span className="italic">{QUALITY_LABEL[cell.quality_status] || cell.quality_status}</span>
      </p>
    </div>
  );
}

export default function WeekProfileHeatmap({
  matrix,
  loading = false,
  provenance,
  ariaLabel,
  className = '',
  testId = 'week-profile-heatmap',
}) {
  // Remapping affichage : la matrix backend peut être sparse (cellules
  // missing pas forcément générées). On construit une grille indexée
  // [day][hour] pour l'affichage. Pas un calcul métier — pur layout.
  const grid = useMemo(() => {
    const g = Array.from({ length: 7 }, () => Array.from({ length: 24 }, () => null));
    if (!Array.isArray(matrix)) return g;
    for (const cell of matrix) {
      if (
        cell &&
        Number.isInteger(cell.day_of_week) &&
        Number.isInteger(cell.hour) &&
        cell.day_of_week >= 0 &&
        cell.day_of_week <= 6 &&
        cell.hour >= 0 &&
        cell.hour <= 23
      ) {
        g[cell.day_of_week][cell.hour] = cell;
      }
    }
    return g;
  }, [matrix]);

  if (loading) {
    return (
      <div
        className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
        data-testid={`${testId}-loading`}
      >
        <div className="animate-pulse">
          <div className="h-3 bg-gray-100 rounded w-32 mb-3" />
          <div className="grid grid-cols-25 gap-px">
            {Array.from({ length: 7 * 25 }).map((_, i) => (
              <div key={i} className="h-5 bg-gray-100 rounded-sm" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const cells = grid.flat().filter(Boolean);
  const hasData = cells.length > 0;

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-800">Heatmap 7 × 24</h3>
        {provenance?.service && (
          <span className="text-[10px] text-gray-400 font-mono" data-testid="heatmap-provenance">
            {provenance.service}
          </span>
        )}
      </div>

      <div
        role="table"
        aria-label={ariaLabel || 'Semaine type — heatmap consommation lundi à dimanche × 0h à 23h'}
      >
        {/* Header heures */}
        <div className="flex items-center text-[9px] text-gray-400 mb-1 pl-8">
          {Array.from({ length: 24 }).map((_, h) => (
            <div key={h} className="flex-1 text-center" aria-hidden="true">
              {h % 3 === 0 ? `${h}h` : ''}
            </div>
          ))}
        </div>

        {/* Lignes jours */}
        {grid.map((row, dayIdx) => (
          <div
            key={dayIdx}
            role="row"
            className="flex items-center mb-px"
            data-testid={`heatmap-row-${dayIdx}`}
          >
            <div
              className="w-8 text-[11px] font-medium text-gray-600"
              role="rowheader"
              aria-label={`Jour ${DAY_LABELS[dayIdx]}`}
            >
              {DAY_LABELS[dayIdx]}
            </div>
            {row.map((cell, hourIdx) => {
              const effective = cell || {
                day_of_week: dayIdx,
                hour: hourIdx,
                kwh: null,
                kw_avg: null,
                status: 'missing',
                quality_status: 'missing',
              };
              const klass = STATUS_CLASS[effective.status] || STATUS_CLASS.missing;
              return (
                <div
                  key={hourIdx}
                  role="cell"
                  className={`group relative flex-1 h-6 mx-px rounded-sm border cursor-help ${klass}`}
                  data-testid={`heatmap-cell-${dayIdx}-${hourIdx}`}
                  data-status={effective.status}
                  data-quality={effective.quality_status}
                  aria-label={`${DAY_LABELS[dayIdx]} ${String(hourIdx).padStart(2, '0')}h — ${
                    STATUS_LABEL[effective.status] || effective.status
                  } — ${fmtNumber(effective.kwh)} kWh`}
                >
                  <CellTooltip cell={effective} />
                </div>
              );
            })}
          </div>
        ))}
      </div>

      {/* Légende */}
      <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-500">
        <LegendDot klass={STATUS_CLASS.normal} label="Normal" />
        <LegendDot klass={STATUS_CLASS.vigilance} label="Vigilance" />
        <LegendDot klass={STATUS_CLASS.critique} label="Critique" />
        <LegendDot klass={STATUS_CLASS.missing} label="Manquant" />
        {hasData && (
          <span className="ml-auto text-[10px] text-gray-400" data-testid="heatmap-cell-count">
            {cells.length}/168 cellules
          </span>
        )}
      </div>
    </div>
  );
}

function LegendDot({ klass, label }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-block w-3 h-3 rounded-sm border ${klass}`} aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
