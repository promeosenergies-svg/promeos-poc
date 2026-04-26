/**
 * CockpitHero — Hero block du cockpit exécutif.
 *
 * 4 cards horizontales : Score santé | Risque financier | Réduction DT | Actions en cours
 *
 * RÈGLE : Ce composant ne calcule RIEN. Il affiche les valeurs du hook.
 * Tout calcul métier est fait backend (P0).
 */
import { useNavigate } from 'react-router-dom';
import { HelpCircle } from 'lucide-react';
import { Skeleton, ErrorState } from '../../ui';
import { fmtEur } from '../../utils/format';
import { formatRiskEur } from '../../lib/risk/normalizeRisk';

// ── Gauge helpers (display-only) ─────────────────────────────────────

// SVG gauge : viewBox 120×80, radius 48 (path "M 12 64 A 48 48 0 0 1 108 64").
// CIRCUMFERENCE = π × r pour un demi-cercle. Bug fix /simplify Phase 3 :
// avant on avait 45 (mauvaise valeur) → score 100/100 ne remplissait pas
// la totalité de l'arc (~6% manquant).
const GAUGE_RADIUS = 48;
const CIRCUMFERENCE = Math.PI * GAUGE_RADIUS;

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

// ── Trend/Delta helpers ──────────────────────────────────────────────
// Mini-delta sous chaque chiffre-roi (« +3 pts vs N-1 »).

const DELTA_TONE_CLS = Object.freeze({
  good: 'bg-green-50 text-green-700 ring-green-200',
  warn: 'bg-amber-50 text-amber-700 ring-amber-200',
  bad: 'bg-red-50 text-red-700 ring-red-200',
  neutral: 'bg-gray-50 text-gray-600 ring-gray-200',
});

function DeltaPill({ text, tone = 'neutral' }) {
  if (!text) return null;
  const toneCls = DELTA_TONE_CLS[tone] ?? DELTA_TONE_CLS.neutral;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ring-1 ${toneCls}`}
    >
      {text}
    </span>
  );
}

// SVG <text> styles — const module-level (recharts diff inégal sinon, audit
// efficiency 26/04 P1 : objet style recréé à chaque render Hero).
// Phase 3 : taille passée à 32px pour cohérence Hero KPI 30-36px (audit UI
// "Hero KPIs sous-dimensionnés CFO").
const SCORE_TEXT_STYLE = Object.freeze({
  fontSize: '32px',
  fontWeight: 700,
  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
  fontVariantNumeric: 'tabular-nums',
});
const SCORE_UNIT_STYLE = Object.freeze({ fontSize: '11px' });

// ── N-1 helpers ──
// Polarity = direction "souhaitable" : higher_is_good (conformité, actions),
// higher_is_bad (risque, factures). Détermine le tone good/bad du DeltaPill.

const N1_FALLBACK = {
  text: 'Comparaison N-1 disponible après 12 mois de données',
  tone: 'neutral',
};

function formatDelta(absValue, unit) {
  // absValue est toujours positif — le signe est ajouté au call-site
  if (unit === 'eur') return formatRiskEur(absValue);
  if (unit === 'pct') return `${absValue}%`;
  if (unit === 'pts') return `${absValue} pt${absValue > 1 ? 's' : ''}`;
  return `${absValue}`;
}

function buildTrendPill(n1, deltaKey, unit, polarity) {
  if (!n1 || n1.data_status !== 'available' || n1[deltaKey] == null) return N1_FALLBACK;
  const v = n1[deltaKey];
  if (v === 0) return { text: 'stable vs N-1', tone: 'neutral' };
  const isGood = polarity === 'higher_is_good' ? v > 0 : v < 0;
  const tone = isGood ? 'good' : 'bad';
  const sign = v > 0 ? '+' : '−'; // U+2212 minus (typo CFO)
  return { text: `${sign}${formatDelta(Math.abs(v), unit)} vs N-1`, tone };
}

// Fallback dédié à conformité : si N-1 indisponible, on retombe sur le trend
// 6 mois fourni par execV2.sante.conformite.trend (chaîne déjà formatée).
function buildConformiteTrendText(n1, fallbackTrend) {
  const pill = buildTrendPill(n1, 'delta_pts', 'pts', 'higher_is_good');
  if (pill === N1_FALLBACK) return fallbackTrend ?? null;
  return pill.text;
}

// ── Component ────────────────────────────────────────────────────────

export default function CockpitHero({
  kpis,
  trajectoire,
  actions,
  loading,
  error,
  sitesARisque,
  trends,
  n1,
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

  // Trends : N-1 backend prime sur trend 6 mois (fallback execV2.sante).
  const conformiteTrend = buildConformiteTrendText(n1?.conformite, trends?.conformite?.trend);
  const conformiteTrendTone = conformiteTrend?.startsWith('+')
    ? 'good'
    : conformiteTrend?.startsWith('-')
      ? 'bad'
      : 'neutral';
  const risqueTrend = buildTrendPill(n1?.risque, 'delta_eur', 'eur', 'higher_is_bad');
  const actionsTrend = buildTrendPill(n1?.actions, 'delta_pct', 'pct', 'higher_is_good');
  // Math.round (pas de fixed-decimals) — pts entiers pour le delta DT
  const reductionDeltaPts =
    reductionPct != null && trajectoire?.objectifPremierJalonPct != null
      ? Math.round(Math.abs(reductionPct - trajectoire.objectifPremierJalonPct))
      : null;
  const reductionDeltaText =
    reductionDeltaPts == null
      ? null
      : isRetard
        ? `+${reductionDeltaPts} pt vs obj.`
        : `−${reductionDeltaPts} pt vs obj.`;
  const reductionDeltaTone = isRetard ? 'bad' : reductionPct != null ? 'good' : 'neutral';

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
        <div className="flex items-center gap-2">
          {/* Gauge SVG : agrandie Phase 3 pour cohérence Hero KPI Vue exécutive
              (audit UI : score-roi sous-dimensionné CFO/CODIR). */}
          <svg viewBox="0 0 120 80" width={104} height={68} className="shrink-0">
            {/* Track */}
            <path
              d="M 12 64 A 48 48 0 0 1 108 64"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={9}
              strokeLinecap="round"
            />
            {/* Value arc */}
            <path
              d="M 12 64 A 48 48 0 0 1 108 64"
              fill="none"
              stroke={color}
              strokeWidth={9}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              className="transition-all duration-1000 ease-out"
            />
            {/* Score number inside arc — Mono tabular pour identité Sol */}
            <text
              x="60"
              y="56"
              textAnchor="middle"
              className="fill-gray-900"
              style={SCORE_TEXT_STYLE}
            >
              {score != null ? Math.round(score) : '—'}
            </text>
            <text
              x="60"
              y="72"
              textAnchor="middle"
              className="fill-gray-400"
              style={SCORE_UNIT_STYLE}
            >
              /100
            </text>
          </svg>
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold text-gray-900">{label}</span>
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${score == null ? 'bg-gray-300' : score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
            />
          </div>
        </div>
        {conformiteTrend && <DeltaPill text={conformiteTrend} tone={conformiteTrendTone} />}
        <p className="text-xs text-gray-500">
          Pondération standard : DT 45% · BACS 30% · APER 25% · {kpis?.totalSites ?? 0} sites
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
          <span className="text-4xl font-bold text-amber-600 sol-numeric">
            {fmtEur(kpis?.risqueTotal)}
          </span>
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${(kpis?.risqueTotal ?? 0) > 0 ? 'bg-amber-500' : 'bg-green-500'}`}
          />
        </div>
        <DeltaPill text={risqueTrend.text} tone={risqueTrend.tone} />
        <p className="text-xs text-gray-500">
          {sitesARisque ?? 0} site{(sitesARisque ?? 0) > 1 ? 's' : ''} concerné
          {(sitesARisque ?? 0) > 1 ? 's' : ''} (périmètre sélectionné)
        </p>
        {(kpis?.risqueTotal ?? 0) > 0 && (
          <p className="text-[10px] text-red-600">Actions correctives urgentes.</p>
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
          className={`text-4xl font-bold sol-numeric ${reductionPct == null ? 'text-gray-400' : isRetard ? 'text-red-600' : 'text-green-700'}`}
        >
          {reductionPct != null ? `${reductionPct}%` : trajectoire?.partial ? 'En attente' : '—'}
        </span>
        {reductionDeltaText && <DeltaPill text={reductionDeltaText} tone={reductionDeltaTone} />}
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
        <span className="text-4xl font-bold text-gray-900 sol-numeric">
          {actions?.enCours != null ? actions.enCours : '—'}
          {actions?.total != null && (
            <span className="text-xl font-normal text-gray-400"> / {actions.total}</span>
          )}
        </span>
        <DeltaPill text={actionsTrend.text} tone={actionsTrend.tone} />
        <span className="text-[10px] text-green-700 font-medium">
          {actions?.potentielEur > 0
            ? `+${fmtEur(actions.potentielEur)}/an potentiel`
            : "Plan d'actions"}
        </span>
      </div>
    </div>
  );
}
