/**
 * DashboardHeroFeatured — Hero 1+3 du Tableau de bord.
 *
 * Pattern issu de CockpitHero (asymétrie 5/7 col-span-12) porté sur la home
 * pour homogénéiser la signature Sol entre /Tableau de bord (Marie) et
 * /cockpit (Jean-Marc). Quick win Phase 4 audit CX 26/04/2026.
 *
 *   Featured (col-span-5)   : Sites en dérive (gauge ratio sains/total)
 *   Secondary (col-span-7)  : Conso hier · Conso mois · Pic max horaire
 *
 * Display-only : aucun calcul métier ici, tout vient des hooks parents.
 */
import { useNavigate } from 'react-router-dom';
import { fmtKwh } from '../../utils/format';

const GAUGE_RADIUS = 48;
const CIRCUMFERENCE = Math.PI * GAUGE_RADIUS;

const SCORE_TEXT_STYLE = Object.freeze({
  fontSize: '56px',
  fontWeight: 600,
  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
  fontVariantNumeric: 'tabular-nums',
  letterSpacing: '-0.02em',
});

const SCORE_UNIT_STYLE = Object.freeze({
  fontSize: '14px',
  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
});

const KPI_VALUE_STYLE = Object.freeze({
  fontSize: '30px',
  fontWeight: 700,
  fontFamily: 'JetBrains Mono, ui-monospace, monospace',
  fontVariantNumeric: 'tabular-nums',
  letterSpacing: '-0.02em',
  lineHeight: 1,
});

function gaugeColor(score) {
  if (score == null) return '#9ca3af';
  if (score >= 80) return '#3B6D11';
  if (score >= 60) return '#BA7517';
  if (score >= 40) return '#E24B4A';
  return '#A32D2D';
}

function gaugeLabel(score) {
  if (score == null) return 'Non évalué';
  if (score >= 80) return 'Patrimoine sain';
  if (score >= 60) return 'Vigilance';
  if (score >= 40) return 'À risque';
  return 'Critique';
}

function formatMonthLabel() {
  return new Date().toLocaleDateString('fr-FR', { month: 'long' });
}

export default function DashboardHeroFeatured({ kpis, kpisJ1, loading = false, sitesCount = 0 }) {
  const navigate = useNavigate();

  const total = kpis?.total ?? 0;
  const enDerive = (kpis?.nonConformes ?? 0) + (kpis?.aRisque ?? 0);
  const sains = Math.max(0, total - enDerive);
  // Score = % de sites SAINS (higher_is_good, cohérent avec gauge cockpit).
  const score = total > 0 ? Math.round((sains / total) * 100) : null;
  const dashOffset = score != null ? CIRCUMFERENCE * (1 - score / 100) : CIRCUMFERENCE;
  const color = gaugeColor(score);
  const label = gaugeLabel(score);

  const consoHier = kpisJ1?.consoHierKwh != null ? fmtKwh(kpisJ1.consoHierKwh) : '—';
  const consoHierSub = kpisJ1?.consoDate
    ? `${sitesCount} sites · ${kpisJ1.consoDate.slice(5).replace('-', '/')}`
    : kpisJ1?.consoHierKwh != null
      ? `${sitesCount} sites · données réelles`
      : 'Aucune donnée EMS disponible';

  const consoMois = kpisJ1?.consoMoisMwh != null ? `${kpisJ1.consoMoisMwh} MWh` : '—';
  const consoMoisDelta = kpisJ1?.consoMoisDeltaPct;
  const consoMoisSub =
    consoMoisDelta != null
      ? `${consoMoisDelta > 0 ? '+' : ''}${consoMoisDelta}% vs mois préc.`
      : kpisJ1?.consoMoisMwh != null
        ? `${kpisJ1.consoMoisSites ?? sitesCount} sites`
        : 'Données mensuelles à venir';
  const consoMoisTone =
    consoMoisDelta == null
      ? 'neutral'
      : consoMoisDelta > 5
        ? 'bad'
        : consoMoisDelta < -5
          ? 'good'
          : 'neutral';

  const picKw = kpisJ1?.picKw != null ? `${kpisJ1.picKw} kW` : '—';
  const picSub =
    kpisJ1?.picKw != null ? `Agrégé sur ${sitesCount} sites` : 'Pas de données horaires';
  const picTone = kpisJ1?.picKw > 40 ? 'warn' : 'neutral';

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl grid grid-cols-12 overflow-hidden sol-card"
      data-testid="dashboard-hero"
    >
      {/* ── Card 1 FEATURED : Patrimoine (41% width) ── */}
      <button
        type="button"
        className="col-span-12 md:col-span-5 p-5 md:p-6 border-b md:border-b-0 md:border-r border-gray-100 flex flex-col gap-2 cursor-pointer hover:bg-blue-50/30 transition-colors text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        data-testid="gauge-patrimoine"
        onClick={() => navigate('/conformite')}
        aria-label="Voir la conformité du patrimoine"
      >
        <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
          Patrimoine — sites sains
        </span>
        <div className="flex items-center gap-3">
          <svg viewBox="0 0 120 80" width={180} height={120} className="shrink-0">
            <path
              d="M 12 64 A 48 48 0 0 1 108 64"
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={8}
              strokeLinecap="round"
            />
            <path
              d="M 12 64 A 48 48 0 0 1 108 64"
              fill="none"
              stroke={color}
              strokeWidth={8}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              className="transition-all duration-1000 ease-out"
            />
            <text
              x="60"
              y="58"
              textAnchor="middle"
              className="fill-gray-900"
              style={SCORE_TEXT_STYLE}
            >
              {sains}
            </text>
            <text
              x="60"
              y="75"
              textAnchor="middle"
              className="fill-gray-400"
              style={SCORE_UNIT_STYLE}
            >
              /{total}
            </text>
          </svg>
          <div className="flex flex-col gap-1">
            <span className="text-base font-semibold text-gray-900">{label}</span>
            <span
              className={`w-2.5 h-2.5 rounded-full shrink-0 ${score == null ? 'bg-gray-300' : score >= 80 ? 'bg-green-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500'}`}
              aria-hidden="true"
            />
          </div>
        </div>
        <p className="text-xs text-gray-500">
          {enDerive > 0
            ? `${enDerive} site${enDerive > 1 ? 's' : ''} en dérive · ${kpis?.risque ? `${Math.round(kpis.risque / 1000)} k€ d'exposition` : 'aucune exposition chiffrée'}`
            : 'Aucun site à risque immédiat'}
        </p>
      </button>

      {/* ── Cards 2-3-4 SECONDARY : sous-grid 3 cols (59%) ── */}
      <div className="col-span-12 md:col-span-7 grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">
        <KpiTile
          label="Conso hier (J-1)"
          value={consoHier}
          sub={consoHierSub}
          loading={loading}
          tone="neutral"
        />
        <KpiTile
          label={`Conso ${formatMonthLabel()}`}
          value={consoMois}
          sub={consoMoisSub}
          loading={loading}
          tone={consoMoisTone}
        />
        <KpiTile
          label="Pic max horaire J-1"
          value={picKw}
          sub={picSub}
          loading={loading}
          tone={picTone}
        />
      </div>
    </div>
  );
}

const TONE_VALUE_CLASS = Object.freeze({
  neutral: 'text-gray-900',
  good: 'text-emerald-700',
  warn: 'text-amber-600',
  bad: 'text-red-600',
});

function KpiTile({ label, value, sub, loading, tone = 'neutral' }) {
  const valueCls = TONE_VALUE_CLASS[tone] ?? TONE_VALUE_CLASS.neutral;
  return (
    <div className="p-4 flex flex-col gap-1.5" data-testid={`kpi-tile-${label}`}>
      <span className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
        {label}
      </span>
      {loading ? (
        <div className="h-8 w-24 bg-gray-100 rounded animate-pulse" />
      ) : (
        <span className={`sol-numeric ${valueCls}`} style={KPI_VALUE_STYLE}>
          {value}
        </span>
      )}
      <p className="text-xs text-gray-500 mt-1 truncate">{sub}</p>
    </div>
  );
}
