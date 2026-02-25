/**
 * PROMEOS — EssentialsRow (Sprint WOW Phase 7.0)
 * 4 mini metric cards: Santé data / Consommation / Patrimoine / Maturité
 * Uses KPI_ACCENTS + tint.module() — no hard-coded colors.
 *
 * Props:
 *   kpis           {object}  — from Cockpit useMemo (couvertureDonnees, readinessScore, total, ...)
 *   sites          {object[]} — scopedSites (for derived totals)
 *   onOpenMaturite {fn}      — open maturite modal
 *   onNavigate     {fn}      — navigate(path)
 */
import { Database, Zap, Building2 } from 'lucide-react';
import { KPI_ACCENTS } from '../../ui/colorTokens';
import { tint } from '../../ui/colorTokens';
import { formatPercentFR } from '../../utils/format';

// ── Mini metric card ─────────────────────────────────────────────────────────

function MiniCard({ accentKey, icon: Icon, label, value, sub, ctaLabel, onCta, children }) {
  const acc = KPI_ACCENTS[accentKey] || KPI_ACCENTS.neutral;
  return (
    <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3 hover:shadow-sm transition-shadow">
      {/* Icon pill */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${acc.iconBg}`}>
        {Icon && <Icon size={18} className={acc.iconText} />}
        {children}
      </div>
      {/* Text */}
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">{label}</p>
        <p className="text-lg font-bold text-gray-900 leading-tight truncate">{value}</p>
        {sub && <p className="text-xs text-gray-500 truncate mt-0.5">{sub}</p>}
      </div>
      {/* CTA */}
      {ctaLabel && onCta && (
        <button
          onClick={onCta}
          className="text-xs text-gray-400 hover:text-blue-600 transition shrink-0 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          {ctaLabel} →
        </button>
      )}
    </div>
  );
}

// ── Progress ring (SVG inline for maturite) ──────────────────────────────────

function ProgressRing({ score }) {
  return (
    <div className="relative w-9 h-9 shrink-0">
      <svg viewBox="0 0 36 36" className="w-9 h-9 -rotate-90">
        <circle cx="18" cy="18" r="15.5" fill="none" className="stroke-gray-200" strokeWidth="3" />
        <circle
          cx="18" cy="18" r="15.5" fill="none" className="stroke-blue-500" strokeWidth="3"
          strokeDasharray={`${score * 0.975} 100`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-gray-800">
        {score}%
      </span>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

export default function EssentialsRow({ kpis = {}, sites = [], onOpenMaturite, onNavigate }) {
  const {
    couvertureDonnees = 0,
    readinessScore = 0,
    total = 0,
  } = kpis;

  const totalConsoMWh = Math.round(
    sites.reduce((s, x) => s + (x.conso_kwh_an || 0), 0) / 1000
  );
  const totalSurfaceM2 = Math.round(
    sites.reduce((s, x) => s + (x.surface_m2 || 0), 0)
  );
  const sitesWithConso = sites.filter(s => s.conso_kwh_an > 0).length;

  // Analyse module tint for conso card icon color
  const analyseTint = tint.module('analyse');

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">

      {/* 1 — Couverture données */}
      <MiniCard
        accentKey="neutral"
        icon={Database}
        label="Couverture données"
        value={couvertureDonnees === 0 ? 'Aucune donnée' : formatPercentFR(couvertureDonnees)}
        sub={couvertureDonnees === 0
          ? 'Importez des relevés de consommation'
          : `${sitesWithConso} site${sitesWithConso > 1 ? 's' : ''} avec données`}
        ctaLabel="Importer"
        onCta={() => onNavigate?.('/consommations/import')}
      />

      {/* 2 — Consommation */}
      <div className="rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3 hover:shadow-sm transition-shadow">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${analyseTint.softBg()}`}>
          <Zap size={18} className={analyseTint.icon()} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">Consommation</p>
          {totalConsoMWh > 0 ? (
            <>
              <p className="text-lg font-bold text-gray-900 leading-tight">{totalConsoMWh.toLocaleString('fr-FR')} MWh/an</p>
              <p className="text-xs text-gray-500 truncate mt-0.5">{sitesWithConso} site{sitesWithConso > 1 ? 's' : ''} couverts</p>
            </>
          ) : (
            <>
              <p className="text-sm font-semibold text-gray-400 leading-tight">Données insuffisantes</p>
              <p className="text-xs text-gray-400 mt-0.5">Importez des relevés</p>
            </>
          )}
        </div>
        <button
          onClick={() => onNavigate?.('/consommations/explorer')}
          className="text-xs text-gray-400 hover:text-blue-600 transition shrink-0 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          Explorer →
        </button>
      </div>

      {/* 3 — Patrimoine */}
      <MiniCard
        accentKey="sites"
        icon={Building2}
        label="Patrimoine"
        value={`${total} site${total > 1 ? 's' : ''}`}
        sub={totalSurfaceM2 > 0
          ? `${totalSurfaceM2.toLocaleString('fr-FR')} m² total`
          : 'Surface non renseignée'}
        ctaLabel="Voir"
        onCta={() => onNavigate?.('/patrimoine')}
      />

      {/* 4 — Maturité */}
      <div
        className="rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-center gap-3 hover:shadow-sm transition-shadow cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500"
        onClick={onOpenMaturite}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpenMaturite?.(); } }}
        role="button"
        tabIndex={0}
        aria-label="Ouvrir le détail de maturité"
      >
        <ProgressRing score={readinessScore} />
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">Maturité</p>
          <p className="text-lg font-bold text-gray-900 leading-tight">{formatPercentFR(readinessScore)}</p>
          <p className="text-xs text-gray-500 truncate mt-0.5">Données + conformité + actions</p>
        </div>
        <span className="text-xs text-gray-400 shrink-0">Détail →</span>
      </div>

    </div>
  );
}
