/**
 * VecteurEnergetiqueCard — Répartition par vecteur énergétique + CO₂ scopes.
 *
 * RÈGLE : zéro calcul métier. Les données viennent de GET /api/cockpit/co2.
 * Le composant affiche — ne calcule pas.
 */
import { useState, useEffect } from 'react';
import { getCockpitCo2 } from '../../services/api';
import { Skeleton } from '../../ui';

/**
 * DeltaLine — Affiche la valeur N-1 et l'écart en % sous un KPI CO₂.
 * Vert ▼ = amélioration (baisse émissions), Rouge ▲ = dégradation (hausse).
 * « — » si données N-1 indisponibles. Zéro calcul : deltaPct vient du backend.
 */
function DeltaLine({ prevValue, deltaPct, co2Factors }) {
  if (prevValue == null || deltaPct == null) {
    return (
      <div className="mt-1.5 pt-1.5 border-t border-gray-100">
        <span className="text-[11px] text-gray-400">—</span>
      </div>
    );
  }

  const isImprovement = deltaPct < 0;
  const colorClass = isImprovement ? 'text-green-600' : 'text-red-500';
  const arrow = isImprovement ? '▼' : '▲';
  const sign = deltaPct > 0 ? '+' : '';

  return (
    <div className="flex items-center gap-1 mt-1.5 pt-1.5 border-t border-gray-100">
      <span className="text-[11px] text-gray-500">
        {prevValue.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} N-1
      </span>
      <span
        className={`text-[11px] font-medium ${colorClass}`}
        title={
          co2Factors
            ? `Comparaison même période calendaire. Facteurs ADEME : élec ${co2Factors.elec_kgco2_per_kwh}, gaz ${co2Factors.gaz_kgco2_per_kwh} kgCO₂/kWh`
            : undefined
        }
      >
        {arrow} {sign}
        {deltaPct.toLocaleString('fr-FR', { maximumFractionDigits: 1 })}%
      </span>
    </div>
  );
}

const VECTOR_CONFIG = {
  elec: { label: 'Électricité', color: 'bg-blue-500', scopeLabel: 'Scope 2 (élec)' },
  gaz: { label: 'Gaz naturel', color: 'bg-amber-500', scopeLabel: 'Scope 1 (gaz)' },
  reseau_chaleur: { label: 'Réseau chaleur', color: 'bg-orange-400', scopeLabel: 'Scope 2' },
  fioul: { label: 'Fioul', color: 'bg-gray-500', scopeLabel: 'Scope 1' },
};

export default function VecteurEnergetiqueCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCockpitCo2()
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="vecteur-energetique"
      >
        <Skeleton className="h-6 w-48 mb-4" />
        <Skeleton className="h-32 rounded" />
      </div>
    );
  }

  if (!data?.sites?.length) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="vecteur-energetique"
      >
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
          Répartition par vecteur énergétique
        </div>
        <p className="text-xs text-gray-400 text-center py-4">Données CO₂ non disponibles.</p>
      </div>
    );
  }

  // Agrégats pré-calculés backend — ZÉRO calcul front (CRIT-5 résolu)
  const backendVectors = data.vectors ?? [];
  const totalTco2 = data.total_t_co2 ?? 0;
  const scope1Tco2 = data.scope1_t_co2 ?? 0;
  const scope2Tco2 = data.scope2_t_co2 ?? 0;

  // Pas de fallback calcul front — si vectors absent, EmptyState
  if (backendVectors.length === 0) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="vecteur-energetique"
      >
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
          Répartition par vecteur énergétique
        </div>
        <p className="text-xs text-gray-400 text-center py-4">Données vecteur non disponibles.</p>
      </div>
    );
  }

  // Enrichir avec les labels/couleurs du design system
  const vectors = backendVectors.map((v) => ({
    ...v,
    ...(VECTOR_CONFIG[v.key] ?? { label: v.key, color: 'bg-gray-400', scopeLabel: '' }),
  }));

  // Grouper les vecteurs mineurs en "Autres" si > 3 vecteurs
  let displayVectors = vectors;
  if (vectors.length > 3) {
    const main = vectors.slice(0, 2);
    const others = vectors.slice(2);
    const othersMwh = others.reduce((s, v) => s + (v.mwh ?? 0), 0);
    const othersPct = others.reduce((s, v) => s + (v.pct ?? 0), 0);
    main.push({
      key: 'autres',
      label: 'Autres',
      color: 'bg-gray-400',
      mwh: othersMwh,
      pct: othersPct,
    });
    displayVectors = main;
  }

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4"
      data-testid="vecteur-energetique"
    >
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-4">
        Répartition par vecteur énergétique
      </div>

      {/* Barres par vecteur */}
      <div className="space-y-2.5 mb-4">
        {displayVectors.map((v) => (
          <div key={v.key} className="flex items-center gap-3">
            <span className="text-xs font-medium text-gray-700 w-24 shrink-0">{v.label}</span>
            <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${v.color}`} style={{ width: `${v.pct}%` }} />
            </div>
            <span className="text-xs text-gray-600 w-32 text-right shrink-0">
              {(v.mwh ?? 0).toLocaleString('fr-FR')} MWh · {v.pct ?? 0}%
            </span>
          </div>
        ))}
      </div>

      {/* CO₂ totaux + comparaison N-1 — données 100% backend */}
      <div className="border-t border-gray-100 pt-3">
        <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-2">
          Émissions CO₂ cumulées {data.year ?? data.annee_ref ?? new Date().getFullYear()}
        </div>
        <div className="flex items-baseline gap-4 flex-wrap">
          <div className="min-w-[100px]">
            <span className="text-lg font-bold text-gray-900">{totalTco2}</span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Total</div>
            <DeltaLine
              prevValue={data.prev_total_tco2}
              deltaPct={data.delta_total_pct}
              co2Factors={data.co2_factors}
            />
          </div>
          <div className="min-w-[100px]">
            <span className="text-base font-semibold text-blue-600">{scope2Tco2}</span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Scope 2 (élec)</div>
            <DeltaLine
              prevValue={data.prev_scope2_tco2}
              deltaPct={data.delta_scope2_pct}
              co2Factors={data.co2_factors}
            />
          </div>
          <div className="min-w-[100px]">
            <span className="text-base font-semibold text-amber-600">{scope1Tco2}</span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Scope 1 (gaz)</div>
            <DeltaLine
              prevValue={data.prev_scope1_tco2}
              deltaPct={data.delta_scope1_pct}
              co2Factors={data.co2_factors}
            />
          </div>
        </div>
        {data.period_label && data.prev_period_label && (
          <div className="text-[10px] text-gray-400 mt-2 leading-relaxed">
            Comparaison {data.period_label} vs {data.prev_period_label}
            {data.co2_factors && (
              <>
                {' '}
                · Facteurs ADEME : élec {data.co2_factors.elec_kgco2_per_kwh} · gaz{' '}
                {data.co2_factors.gaz_kgco2_per_kwh} kgCO₂/kWh
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
