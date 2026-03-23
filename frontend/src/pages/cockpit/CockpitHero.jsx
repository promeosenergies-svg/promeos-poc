/**
 * CockpitHero — Hero block du cockpit exécutif.
 *
 * 3 colonnes : Gauge conformité | 3 KPI cards | Risque décomposé
 *
 * RÈGLE : Ce composant ne calcule RIEN. Il affiche les valeurs du hook.
 * Tout calcul métier est fait backend (P0).
 */
import { useNavigate } from 'react-router-dom';
import { HelpCircle, AlertTriangle, ArrowRight } from 'lucide-react';
import { KPI_ACCENTS } from '../../ui/colorTokens';
import { Skeleton, ErrorState } from '../../ui';
import { fmtEur } from '../../utils/format';

// ── Gauge helpers (display-only) ─────────────────────────────────────

const CIRCUMFERENCE = Math.PI * 45; // ≈ 141.4 — demi-cercle r=45

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

  // ── Loading ──
  if (loading) {
    return (
      <div className="grid grid-cols-[auto_1fr_auto] gap-4 p-4 bg-white border rounded-xl">
        <Skeleton className="w-32 h-24 rounded-lg" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
        <Skeleton className="w-40 h-24 rounded-lg" />
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <ErrorState
        title="Données cockpit indisponibles"
        description="Impossible de charger les KPIs exécutifs."
      />
    );
  }

  const score = kpis?.conformiteScore;
  const dashOffset = score != null ? CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE : CIRCUMFERENCE;
  const color = gaugeColor(score);
  const label = gaugeLabel(score);

  const reductionPct = trajectoire?.reductionPctActuelle;
  const rb = kpis?.risqueBreakdown;

  const freshness = kpis?.conformiteComputedAt
    ? new Date(kpis.conformiteComputedAt).toLocaleDateString('fr-FR')
    : null;

  return (
    <div className="grid grid-cols-[auto_1fr_auto] gap-4 items-start p-4 bg-white border rounded-xl">
      {/* ── Colonne gauche : Gauge conformité ── */}
      <div className="flex flex-col items-center gap-1" data-testid="gauge-conformite">
        <button
          onClick={() => navigate('/conformite')}
          className="relative cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg p-1"
          aria-label="Voir le score de conformité"
        >
          <svg viewBox="0 0 120 70" width={120} height={70}>
            {/* Arc de fond */}
            <path
              d="M 15 60 A 45 45 0 0 1 105 60"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={10}
              strokeLinecap="round"
            />
            {/* Arc progressif */}
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
            {/* Valeur */}
            <text
              x="60"
              y="52"
              textAnchor="middle"
              className="text-2xl font-bold"
              fill={color}
              fontSize="22"
            >
              {score ?? '—'}
            </text>
          </svg>
        </button>

        <span className="text-xs font-medium" style={{ color }}>
          {label}
        </span>

        {/* Pondérations réglementaires — constantes figées */}
        <div className="text-[10px] text-gray-400 text-center mt-0.5 flex items-center gap-1">
          <span className="font-medium text-blue-600">DT 45%</span>
          <span>·</span>
          <span className="font-medium text-blue-500">BACS 30%</span>
          <span>·</span>
          <span className="font-medium text-blue-400">APER 25%</span>
        </div>

        {onEvidence && (
          <button
            onClick={() => onEvidence('conformite')}
            className="text-gray-400 hover:text-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
            aria-label="Pourquoi ce chiffre ?"
            title="Pourquoi ce chiffre ?"
          >
            <HelpCircle size={14} />
          </button>
        )}

        {freshness && (
          <p className="text-[10px] text-gray-400 text-center leading-tight mt-0.5">
            Calculé le {freshness}
            <br />
            Source : {kpis?.conformiteSource ?? 'RegAssessment'}
          </p>
        )}
      </div>

      {/* ── Colonne centrale : 3 KPI cards ── */}
      <div className="grid grid-cols-3 gap-3">
        {/* Réduction DT cumulée */}
        <div
          className="bg-gray-50 rounded-lg p-3 flex flex-col gap-1"
          data-testid="kpi-reduction-dt"
        >
          <span className="text-xs text-gray-500">Réduction DT cumulée</span>
          <span className="text-lg font-semibold text-gray-900">
            {reductionPct != null ? `${reductionPct} %` : '—'}
          </span>
          <span className="text-[10px] text-gray-400">Objectif 2026 : −25 %</span>
        </div>

        {/* Actions en cours */}
        <div
          className="bg-gray-50 rounded-lg p-3 flex flex-col gap-1"
          data-testid="kpi-actions-encours"
        >
          <span className="text-xs text-gray-500">Actions en cours</span>
          <span className="text-lg font-semibold text-gray-900">
            {actions?.enCours != null ? actions.enCours : '—'}
            {actions?.total != null && (
              <span className="text-sm font-normal text-gray-400"> / {actions.total}</span>
            )}
          </span>
          <span className="text-[10px] text-gray-400">
            {actions?.potentielEur > 0
              ? `+${fmtEur(actions.potentielEur)}/an potentiel`
              : "Plan d'actions"}
          </span>
        </div>

        {/* CO₂ évité */}
        <div className="bg-gray-50 rounded-lg p-3 flex flex-col gap-1" data-testid="kpi-co2">
          <span className="text-xs text-gray-500">CO₂ évité (N vs N−1)</span>
          <span className="text-lg font-semibold text-gray-900">—</span>
          <span className="text-[10px] text-gray-400">ADEME 2024 · 0,0569 kgCO₂/kWh élec</span>
        </div>
      </div>

      {/* ── Colonne droite : Risque décomposé ── */}
      <div
        className={`${KPI_ACCENTS.risque.tintBg} border ${KPI_ACCENTS.risque.chipBorder ?? 'border-amber-200'} rounded-lg p-3 min-w-[180px] flex flex-col gap-2`}
        data-testid="risque-breakdown"
      >
        <div className="flex items-center gap-1.5 mb-1">
          <AlertTriangle size={14} className={KPI_ACCENTS.risque.iconText} />
          <span className="text-xs font-semibold text-gray-700">Risque financier total</span>
        </div>
        <span className="text-lg font-bold text-gray-900">{fmtEur(kpis?.risqueTotal)}</span>

        <hr className="border-amber-200" />

        <div className="flex flex-col gap-1 text-xs text-gray-600">
          <div className="flex justify-between">
            <span>Pénalités réglementaires</span>
            <span className="font-medium">{fmtEur(rb?.reglementaire_eur)}</span>
          </div>
          <div className="flex justify-between">
            <span>Anomalies facturation</span>
            <span className="font-medium">{fmtEur(rb?.billing_anomalies_eur)}</span>
          </div>
          <div className="flex justify-between">
            <span>Risque contrat</span>
            <span className="font-medium">{fmtEur(rb?.contract_risk_eur)}</span>
          </div>
        </div>

        <hr className="border-amber-200" />

        <button
          onClick={() => navigate('/actions')}
          className="flex items-center gap-1 text-xs font-medium text-amber-700 hover:text-amber-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          Voir le plan de rattrapage <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
