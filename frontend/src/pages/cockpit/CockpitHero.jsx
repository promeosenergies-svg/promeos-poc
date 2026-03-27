/**
 * CockpitHero — Hero block du cockpit exécutif.
 *
 * 4 cards horizontales : Score santé | Risque financier | Réduction DT | Actions en cours
 *
 * RÈGLE : Ce composant ne calcule RIEN. Il affiche les valeurs du hook.
 * Tout calcul métier est fait backend (P0).
 */
import { useNavigate } from 'react-router-dom';
import { HelpCircle, AlertTriangle } from 'lucide-react';
import { Skeleton, ErrorState } from '../../ui';
import { fmtEur } from '../../utils/format';

// ── Gauge helpers (display-only) ─────────────────────────────────────

const CIRCUMFERENCE = Math.PI * 45;

function gaugeColor(score) {
  if (score == null) return '#9ca3af';
  if (score >= 80) return '#3B6D11';
  if (score >= 60) return '#BA7517';
  if (score >= 40) return '#E24B4A';
  return '#A32D2D';
}

function gaugeLabel(score) {
  if (score == null) return 'Non évalué';
  if (score >= 80) return 'Excellent';
  if (score >= 60) return 'Satisfaisant';
  if (score >= 40) return 'À risque';
  return 'Critique';
}

// ── Component ────────────────────────────────────────────────────────

export default function CockpitHero({
  kpis,
  trajectoire,
  actions,
  billing,
  loading,
  error,
  orgNom,
  onEvidence,
}) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <ErrorState
        title="Données cockpit indisponibles"
        message="Impossible de charger les KPIs exécutifs."
      />
    );
  }

  const score = kpis?.conformiteScore;
  const dashOffset = score != null ? CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE : CIRCUMFERENCE;
  const color = gaugeColor(score);
  const label = gaugeLabel(score);
  const reductionPct = trajectoire?.reductionPctActuelle;
  const isRetard =
    reductionPct != null &&
    trajectoire?.objectifPremierJalonPct != null &&
    reductionPct > trajectoire.objectifPremierJalonPct;

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl grid grid-cols-2 md:grid-cols-4 divide-x divide-gray-100"
      data-testid="cockpit-hero"
    >
      {/* ── Card 1 : Conformité réglementaire (jauge + détails) ── */}
      <div
        className="p-4 flex flex-col gap-1.5 cursor-pointer hover:bg-blue-50/30 transition-colors rounded-l-xl"
        data-testid="gauge-conformite"
        onClick={() => navigate('/conformite')}
        role="button"
        tabIndex={0}
      >
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
            Conformité réglementaire
          </span>
          {onEvidence && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEvidence('conformite');
              }}
              className="text-gray-400 hover:text-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              aria-label="Pourquoi ce chiffre ?"
            >
              <HelpCircle size={14} />
            </button>
          )}
        </div>
        <div className="flex items-center gap-3">
          {/* Jauge SVG conservée */}
          <svg viewBox="0 0 120 70" width={48} height={28} className="shrink-0">
            <path
              d="M 15 60 A 45 45 0 0 1 105 60"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={10}
              strokeLinecap="round"
            />
            <path
              d="M 15 60 A 45 45 0 0 1 105 60"
              fill="none"
              stroke={color}
              strokeWidth={10}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              className="transition-all duration-700"
            />
          </svg>
          <div className="flex items-center gap-1.5">
            <span className="text-xl font-bold text-gray-900">{score ?? '—'} / 100</span>
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500">
          DT {kpis?.weightDt ?? 45}% · BACS {kpis?.weightBacs ?? 30}% · APER{' '}
          {kpis?.weightAper ?? 25}% · {kpis?.totalSites ?? 0} sites
        </p>
        <p className="text-[10px] text-gray-400">
          Source :{' '}
          {kpis?.conformiteSource === 'RegAssessment'
            ? 'Moteur conformité'
            : (kpis?.conformiteSource ?? 'Moteur conformité')}{' '}
          · Confiance : {kpis?.conformiteConfidence ?? 'moyenne'}
        </p>
      </div>

      {/* ── Card 2 : Risque financier (détaillé) ── */}
      <div
        className="p-4 flex flex-col gap-1.5 cursor-pointer hover:bg-amber-50/30 transition-colors"
        data-testid="kpi-risque"
        onClick={() => navigate('/actions')}
        role="button"
        tabIndex={0}
      >
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
            Risque financier
          </span>
          {onEvidence && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEvidence('risque');
              }}
              className="text-gray-400 hover:text-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              aria-label="Détail risque"
            >
              <HelpCircle size={14} />
            </button>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xl font-bold text-amber-600">{fmtEur(kpis?.risqueTotal)}</span>
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${(kpis?.risqueTotal ?? 0) > 0 ? 'bg-amber-500' : 'bg-green-500'}`}
          />
        </div>
        <p className="text-xs text-gray-500">
          {kpis?.totalSites ?? 0} sites concernés (périmètre sélectionné)
        </p>
        {(kpis?.risqueTotal ?? 0) > 0 && (
          <p className="text-[10px] text-red-600">
            Risque total {fmtEur(kpis?.risqueTotal)}. Actions correctives urgentes.
          </p>
        )}
        <p className="text-[10px] text-gray-400">
          Source :{' '}
          {kpis?.conformiteSource === 'RegAssessment'
            ? 'Moteur conformité'
            : (kpis?.conformiteSource ?? 'Moteur conformité')}{' '}
          · Confiance : {kpis?.conformiteConfidence ?? 'moyenne'}
        </p>
      </div>

      {/* ── Card 3 : Réduction DT cumulée ── */}
      <div className="p-4 flex flex-col gap-2" data-testid="kpi-reduction-dt">
        <span className="text-xs text-gray-500">Réduction DT cumulée</span>
        <span
          className={`text-2xl font-bold ${reductionPct == null ? 'text-gray-400' : isRetard ? 'text-red-600' : 'text-green-700'}`}
        >
          {reductionPct != null ? `${reductionPct}%` : trajectoire?.partial ? 'En attente' : '—'}
        </span>
        <span className="text-[10px] text-gray-400">
          {trajectoire?.partial ? (
            'Données annuelles en cours de collecte'
          ) : (
            <>
              Objectif 2030 :{' '}
              <span className="text-blue-600">{trajectoire?.objectifPremierJalonPct ?? -40}%</span>
              {isRetard && <span className="text-red-500 ml-1">· retard</span>}
            </>
          )}
        </span>
      </div>

      {/* ── Card 4 : Actions en cours ── */}
      <div className="p-4 flex flex-col gap-2 rounded-r-xl" data-testid="kpi-actions-encours">
        <span className="text-xs text-gray-500">Actions en cours</span>
        <span className="text-2xl font-bold text-gray-900">
          {actions?.enCours != null ? actions.enCours : '—'}
          {actions?.total != null && (
            <span className="text-lg font-normal text-gray-400"> / {actions.total}</span>
          )}
        </span>
        <span className="text-[10px] text-green-700 font-medium">
          {actions?.potentielEur > 0
            ? `+${fmtEur(actions.potentielEur)}/an potentiel`
            : "Plan d'actions"}
        </span>
      </div>
    </div>
  );
}
