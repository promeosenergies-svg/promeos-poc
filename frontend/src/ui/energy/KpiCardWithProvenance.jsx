/**
 * PROMEOS — KpiCardWithProvenance (Sprint P1.S3a UI Courbe de charge).
 *
 * Carte KPI normalisée pour consommer un EnergyKpi du backend
 * (`/api/energy/*`). Affiche valeur + unité + état + tooltip provenance.
 *
 * DOCTRINE : ne recalcule rien. Affiche uniquement les valeurs fournies
 * par le backend. Si `value` est null → état "inactif" auto.
 *
 * Props :
 * - label        : string (depuis kpi.label)
 * - value        : number | string | null
 * - unit         : string (ex: '€', 'kWh', '/100', 'kW')
 * - state        : 'sain' | 'vigilance' | 'critique' | 'inactif'
 * - provenance   : { source, service, formula, period, confidence, assumptions[] }
 * - helperText   : string optionnel
 */
import { HelpCircle } from 'lucide-react';

const STATE_TINT = {
  sain: 'text-emerald-600 bg-emerald-50 border-emerald-100',
  vigilance: 'text-amber-700 bg-amber-50 border-amber-100',
  critique: 'text-red-700 bg-red-50 border-red-100',
  inactif: 'text-gray-400 bg-gray-50 border-gray-100',
};

const STATE_DOT = {
  sain: 'bg-emerald-500',
  vigilance: 'bg-amber-500',
  critique: 'bg-red-500',
  inactif: 'bg-gray-300',
};

/** Format display d'une valeur — purement cosmétique (separateurs FR).
 *  L'unité est rendue séparément en JSX, pas dans cette fonction. */
function fmtValue(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (Number.isFinite(value)) {
    return value.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
  }
  return String(value);
}

function ProvenanceTooltip({ provenance, helperText }) {
  if (!provenance) {
    return helperText ? <p className="text-xs text-gray-500">{helperText}</p> : null;
  }
  const confidencePct =
    typeof provenance.confidence === 'number' ? Math.round(provenance.confidence * 100) : null;
  return (
    <div className="space-y-1.5 text-xs text-gray-700">
      {helperText && <p className="text-gray-500 italic mb-1">{helperText}</p>}
      <Row label="Source" value={provenance.source} />
      <Row label="Service" value={provenance.service} mono />
      <Row label="Formule" value={provenance.formula} mono />
      <Row label="Période" value={provenance.period} />
      {confidencePct != null && <Row label="Confiance" value={`${confidencePct}%`} />}
      {Array.isArray(provenance.assumptions) && provenance.assumptions.length > 0 && (
        <div className="pt-1">
          <p className="text-gray-500">Hypothèses :</p>
          <ul className="list-disc list-inside text-gray-600 ml-1">
            {provenance.assumptions.slice(0, 4).map((a, i) => (
              <li key={i} className="break-words">
                {a}
              </li>
            ))}
            {provenance.assumptions.length > 4 && (
              <li className="italic text-gray-400">+{provenance.assumptions.length - 4} autres…</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, mono }) {
  if (!value) return null;
  return (
    <p>
      <span className="text-gray-500">{label} : </span>
      <span className={mono ? 'font-mono text-[11px]' : ''}>{value}</span>
    </p>
  );
}

export default function KpiCardWithProvenance({
  label,
  value,
  unit = '',
  state,
  provenance,
  helperText,
  className = '',
  testId,
}) {
  const effectiveState = state || (value === null || value === undefined ? 'inactif' : 'sain');
  const tint = STATE_TINT[effectiveState] || STATE_TINT.inactif;

  return (
    <div
      className={`rounded-xl border bg-white p-4 flex flex-col gap-2 ${className}`}
      data-testid={testId || 'kpi-card-with-provenance'}
      data-state={effectiveState}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs text-gray-500 font-medium">
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${
              STATE_DOT[effectiveState] || STATE_DOT.inactif
            }`}
            aria-hidden="true"
          />
          <span>{label}</span>
        </div>
        {provenance ? (
          <details className="relative">
            <summary
              className="cursor-help list-none text-gray-400 hover:text-gray-600"
              aria-label="Voir la provenance"
            >
              <HelpCircle size={13} aria-hidden="true" />
            </summary>
            <div
              className="absolute right-0 top-5 z-10 w-72 rounded-lg border border-gray-200 bg-white p-3 shadow-lg"
              data-testid="kpi-provenance-tooltip"
            >
              <ProvenanceTooltip provenance={provenance} helperText={helperText} />
            </div>
          </details>
        ) : helperText ? (
          <span className="text-xs text-gray-400">{helperText}</span>
        ) : null}
      </div>
      <div className="flex items-baseline gap-1">
        <p className="text-2xl font-bold text-gray-900" data-testid="kpi-value">
          {fmtValue(value)}
        </p>
        {unit && (
          <p className="text-xs text-gray-500 font-medium" data-testid="kpi-unit">
            {unit}
          </p>
        )}
      </div>
      <p
        className={`inline-flex w-fit px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide border ${tint}`}
      >
        {effectiveState}
      </p>
    </div>
  );
}
