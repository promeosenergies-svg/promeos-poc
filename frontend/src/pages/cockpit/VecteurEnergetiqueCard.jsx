/**
 * VecteurEnergetiqueCard — Répartition par vecteur énergétique + CO₂ scopes.
 *
 * RÈGLE : zéro calcul métier. Les données viennent de GET /api/cockpit/co2.
 * Le composant affiche — ne calcule pas.
 */
import { useState, useEffect } from 'react';
import { getCockpitCo2 } from '../../services/api';
import { Skeleton } from '../../ui';

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

  // Agréger les breakdowns par vecteur depuis les sites (données backend)
  const totals = {};
  let totalKwh = 0;
  let totalKgCo2 = 0;
  for (const site of data.sites) {
    for (const b of site.breakdown ?? []) {
      const key = b.energy_type;
      if (!totals[key]) totals[key] = { kwh: 0, kgCo2: 0 };
      totals[key].kwh += b.kwh ?? 0;
      totals[key].kgCo2 += b.kg_co2 ?? 0;
      totalKwh += b.kwh ?? 0;
      totalKgCo2 += b.kg_co2 ?? 0;
    }
  }

  // Identifier scope 1 (gaz, fioul) vs scope 2 (elec, réseau)
  let scope1KgCo2 = 0;
  let scope2KgCo2 = 0;
  for (const [key, val] of Object.entries(totals)) {
    if (key === 'gaz' || key === 'fioul') scope1KgCo2 += val.kgCo2;
    else scope2KgCo2 += val.kgCo2;
  }

  const vectors = Object.entries(totals)
    .map(([key, val]) => ({
      key,
      ...(VECTOR_CONFIG[key] ?? { label: key, color: 'bg-gray-400', scopeLabel: '' }),
      mwh: Math.round(val.kwh / 1000),
      pct: totalKwh > 0 ? Math.round((val.kwh / totalKwh) * 100) : 0,
      tCo2: (val.kgCo2 / 1000).toFixed(1),
    }))
    .sort((a, b) => b.mwh - a.mwh);

  // Grouper les vecteurs mineurs en "Autres" si > 2 vecteurs
  let displayVectors = vectors;
  if (vectors.length > 3) {
    const main = vectors.slice(0, 2);
    const others = vectors.slice(2);
    const othersMwh = others.reduce((s, v) => s + v.mwh, 0);
    const othersPct = others.reduce((s, v) => s + v.pct, 0);
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
              {v.mwh.toLocaleString('fr-FR')} MWh · {v.pct}%
            </span>
          </div>
        ))}
      </div>

      {/* CO₂ totaux */}
      <div className="border-t border-gray-100 pt-3">
        <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-2">
          Émissions CO₂ cumulées
        </div>
        <div className="flex items-baseline gap-4">
          <div>
            <span className="text-lg font-bold text-gray-900">
              {(totalKgCo2 / 1000).toFixed(1)}
            </span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Total</div>
          </div>
          <div>
            <span className="text-base font-semibold text-blue-600">
              {(scope2KgCo2 / 1000).toFixed(1)}
            </span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Scope 2 (élec)</div>
          </div>
          <div>
            <span className="text-base font-semibold text-amber-600">
              {(scope1KgCo2 / 1000).toFixed(1)}
            </span>
            <span className="text-xs text-gray-500 ml-1">tCO₂eq</span>
            <div className="text-[10px] text-gray-400">Scope 1 (gaz)</div>
          </div>
        </div>
      </div>
    </div>
  );
}
