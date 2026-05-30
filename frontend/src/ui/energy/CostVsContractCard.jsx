/**
 * PROMEOS — CostVsContractCard (Sprint P1.S5).
 *
 * Affiche les scénarios contractuels simulés renvoyés par
 * `/api/energy/cost-vs-contract` → `scenarios[]`.
 *
 * Chaque scénario expose (depuis le backend, JAMAIS recalculé FE) :
 *   - estimated_cost_eur
 *   - weighted_price_eur_mwh
 *   - risk_level   : 'faible' | 'modéré' | 'élevé'
 *   - status       : 'current' | 'simulation'
 *   - delta_vs_current_eur (signe négatif = économie potentielle)
 *
 * Doctrine :
 * - Aucun calcul de delta FE (utilise delta_vs_current_eur backend) ;
 * - Aucun choix de scénario gagnant FE (utilise recommended_scenario) ;
 * - Warning obligatoire sous les cartes :
 *   « Simulation indicative — ne constitue pas une promesse d'économie. »
 */
import { AlertTriangle, BadgeCheck, Sparkles } from 'lucide-react';

const DEFAULT_WARNING = "Simulation indicative — ne constitue pas une promesse d'économie.";

const RISK_TINT = {
  faible: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  modéré: 'bg-amber-50 text-amber-700 border-amber-200',
  élevé: 'bg-red-50 text-red-700 border-red-200',
};

function fmtEur(v) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });
}

function fmtEurPerMwh(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €/MWh`;
}

function fmtDelta(v) {
  if (v === null || v === undefined) return null;
  const num = Number(v);
  const sign = num > 0 ? '+' : '';
  const colour = num < 0 ? 'text-emerald-700' : num > 0 ? 'text-red-700' : 'text-gray-500';
  return (
    <span className={`font-mono text-xs ${colour}`}>
      {sign}
      {num.toLocaleString('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        maximumFractionDigits: 0,
      })}{' '}
      vs actuel
    </span>
  );
}

function ScenarioCard({ scenario, isRecommended }) {
  const isCurrent = scenario.status === 'current';
  const tint = RISK_TINT[scenario.risk_level] || RISK_TINT.modéré;
  return (
    <div
      className={`rounded-xl border bg-white p-3 flex flex-col gap-2 ${
        isRecommended ? 'border-blue-400 ring-1 ring-blue-200' : 'border-gray-200'
      }`}
      data-testid={`scenario-card-${scenario.key}`}
      data-status={scenario.status}
      data-risk-level={scenario.risk_level}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold text-gray-800">{scenario.label}</p>
        <div className="flex items-center gap-1">
          {isCurrent && (
            <span
              className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700 font-bold inline-flex items-center gap-0.5"
              data-testid="scenario-badge-current"
            >
              <BadgeCheck size={9} aria-hidden="true" />
              Actuel
            </span>
          )}
          {!isCurrent && (
            <span
              className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 font-semibold"
              data-testid="scenario-badge-simulation"
            >
              Simulation
            </span>
          )}
          {isRecommended && (
            <span
              className="text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-blue-600 text-white font-bold inline-flex items-center gap-0.5"
              data-testid="scenario-badge-recommended"
            >
              <Sparkles size={9} aria-hidden="true" />
              Recommandé
            </span>
          )}
        </div>
      </div>
      <p className="text-xl font-bold text-gray-900 font-mono">
        {fmtEur(scenario.estimated_cost_eur)}
      </p>
      <p className="text-[11px] text-gray-500 font-mono">
        {fmtEurPerMwh(scenario.weighted_price_eur_mwh)}
      </p>
      <div className="flex items-center justify-between gap-2 mt-1">
        <span
          className={`text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded-full border font-medium ${tint}`}
          data-testid={`scenario-risk-${scenario.key}`}
        >
          Risque {scenario.risk_level}
        </span>
        {fmtDelta(scenario.delta_vs_current_eur)}
      </div>
      {Array.isArray(scenario.assumptions) && scenario.assumptions.length > 0 && (
        <p className="text-[10px] italic text-gray-400 mt-1 line-clamp-2">
          {scenario.assumptions.slice(0, 2).join(' · ')}
        </p>
      )}
    </div>
  );
}

function RecommendationBanner({ recommendation }) {
  if (!recommendation) return null;
  return (
    <div
      className="rounded-lg border border-blue-100 bg-blue-50/40 p-3 text-xs text-blue-900 flex items-start gap-2"
      data-testid="cost-recommendation"
    >
      <Sparkles size={14} className="text-blue-600 shrink-0 mt-0.5" aria-hidden="true" />
      <div className="space-y-0.5">
        <p>{recommendation.message}</p>
        {typeof recommendation.confidence === 'number' && (
          <p className="text-[10px] text-blue-700">
            Confiance : {Math.round(recommendation.confidence * 100)} %
          </p>
        )}
      </div>
    </div>
  );
}

export default function CostVsContractCard({
  scenarios = [],
  recommendation,
  activeContract,
  className = '',
  testId = 'cost-vs-contract-card',
}) {
  const recommendedKey = recommendation?.recommended_scenario;
  const warning = recommendation?.warning || DEFAULT_WARNING;

  if (!Array.isArray(scenarios) || scenarios.length === 0) {
    return null;
  }

  return (
    <div className={`space-y-3 ${className}`} data-testid={testId}>
      {activeContract?.supplier_name && (
        <div
          className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700 flex items-center gap-2"
          data-testid="active-contract-summary"
        >
          <BadgeCheck size={14} className="text-blue-600 shrink-0" aria-hidden="true" />
          <p>
            Contrat actif : <span className="font-semibold">{activeContract.supplier_name}</span>
            {activeContract.contract_type && (
              <span className="ml-1 text-gray-500">({activeContract.contract_type})</span>
            )}
            {activeContract.end_date && (
              <span className="ml-1 text-gray-500">— échéance {activeContract.end_date}</span>
            )}
          </p>
        </div>
      )}

      <RecommendationBanner recommendation={recommendation} />

      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3"
        data-testid="scenarios-grid"
      >
        {scenarios.map((s) => (
          <ScenarioCard key={s.key} scenario={s} isRecommended={recommendedKey === s.key} />
        ))}
      </div>

      <div
        className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800 flex items-start gap-2"
        role="note"
        data-testid="simulation-warning"
      >
        <AlertTriangle size={14} className="shrink-0 mt-0.5" aria-hidden="true" />
        <p className="font-medium">{warning}</p>
      </div>
    </div>
  );
}
