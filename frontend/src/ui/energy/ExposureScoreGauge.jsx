/**
 * PROMEOS — ExposureScoreGauge (Sprint P1.S6).
 *
 * Jauge score d'exposition spot [0, 100] borné backend (clamp_score_0_100)
 * avec état canonique `ExposureScoreState` ∈ sain | vigilance | critique
 * | inactif. Tooltip provenance complète.
 *
 * Doctrine : ne recalcule jamais le state — utilise celui fourni par
 * l'API. Si score null/undefined → état 'inactif' par défaut.
 */
import { HelpCircle, Gauge } from 'lucide-react';

const STATE_TINT = {
  sain: 'from-emerald-100 to-emerald-50 border-emerald-200 text-emerald-700',
  vigilance: 'from-amber-100 to-amber-50 border-amber-200 text-amber-700',
  critique: 'from-red-100 to-red-50 border-red-200 text-red-700',
  inactif: 'from-gray-100 to-gray-50 border-gray-200 text-gray-500',
};

const STATE_LABEL = {
  sain: 'Sain',
  vigilance: 'Vigilance',
  critique: 'Critique',
  inactif: 'Inactif',
};

function fmtScore(v) {
  if (v === null || v === undefined) return '—';
  return Math.round(Number(v));
}

function ProvenanceTooltip({ provenance }) {
  if (!provenance) return null;
  return (
    <span className="relative inline-block group" data-testid="exposure-score-provenance">
      <HelpCircle size={13} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <div className="absolute right-0 top-5 z-10 hidden group-hover:block w-72 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700 shadow-lg">
        <p className="text-gray-500">Source</p>
        <p className="font-mono break-words">{provenance.source || '—'}</p>
        <p className="text-gray-500 mt-1">Service</p>
        <p className="font-mono text-[11px] break-words">{provenance.service || '—'}</p>
        {provenance.formula && (
          <>
            <p className="text-gray-500 mt-1">Formule</p>
            <p className="font-mono text-[11px] break-words">{provenance.formula}</p>
          </>
        )}
        {provenance.period && (
          <>
            <p className="text-gray-500 mt-1">Période</p>
            <p>{provenance.period}</p>
          </>
        )}
        {typeof provenance.confidence === 'number' && (
          <>
            <p className="text-gray-500 mt-1">Confiance</p>
            <p>{Math.round(provenance.confidence * 100)} %</p>
          </>
        )}
      </div>
    </span>
  );
}

export default function ExposureScoreGauge({
  score,
  state,
  provenance,
  label = "Score d'exposition spot",
  className = '',
  testId = 'exposure-score-gauge',
}) {
  const effectiveState = state || (score === null || score === undefined ? 'inactif' : 'sain');
  const tint = STATE_TINT[effectiveState] || STATE_TINT.inactif;
  return (
    <div
      className={`rounded-xl border bg-gradient-to-br p-4 flex flex-col gap-2 ${tint} ${className}`}
      data-testid={testId}
      data-state={effectiveState}
      data-score={score ?? ''}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide">
          <Gauge size={13} aria-hidden="true" />
          <span>{label}</span>
        </div>
        <ProvenanceTooltip provenance={provenance} />
      </div>
      <p className="text-4xl font-bold font-mono" data-testid="exposure-score-value">
        {fmtScore(score)}
        <span className="text-base font-medium opacity-60">/100</span>
      </p>
      <p
        className="text-[10px] uppercase tracking-wide font-semibold opacity-80"
        data-testid="exposure-score-state-label"
      >
        {STATE_LABEL[effectiveState] || effectiveState}
      </p>
    </div>
  );
}
