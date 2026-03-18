/**
 * Bloc "Fenêtres tarifaires utiles" dans facture / achat.
 */
import { useState, useEffect } from 'react';
import { getTariffWindows } from '../../services/api';

const PERIOD_LABELS = {
  HC_NUIT: 'HC Nuit',
  HC_SOLAIRE: 'HC Solaire',
  HP: 'Heures pleines',
  POINTE: 'Pointe',
  SUPER_POINTE: 'Super-pointe',
};
const PERIOD_COLORS = {
  HC_NUIT: 'bg-blue-100 text-blue-700',
  HC_SOLAIRE: 'bg-yellow-100 text-yellow-700',
  HP: 'bg-gray-100 text-gray-700',
  POINTE: 'bg-red-100 text-red-700',
  SUPER_POINTE: 'bg-red-200 text-red-800',
};

export default function TariffWindowsCard({ segment }) {
  const [windows, setWindows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = {};
    if (segment) params.segment = segment;
    getTariffWindows(params)
      .then((r) => setWindows(r?.windows || []))
      .catch(() => setWindows([]))
      .finally(() => setLoading(false));
  }, [segment]);

  if (loading) return null;
  if (windows.length === 0)
    return (
      <div className="border rounded-lg p-3 text-xs text-gray-400">
        Aucune fenêtre tarifaire configurée. Ajoutez une grille TURPE 7 pour activer l'optimisation.
      </div>
    );

  // Group by season
  const bySeason = {};
  windows.forEach((w) => {
    if (!bySeason[w.season]) bySeason[w.season] = [];
    bySeason[w.season].push(w);
  });

  return (
    <div className="border rounded-lg p-3">
      <h4 className="text-sm font-semibold text-gray-700 mb-2">Fenêtres tarifaires</h4>
      {Object.entries(bySeason).map(([season, wins]) => (
        <div key={season} className="mb-2">
          <div className="text-xs font-medium text-gray-500 mb-1 capitalize">{season}</div>
          <div className="space-y-0.5">
            {wins.map((w, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span
                  className={`px-1.5 py-0.5 rounded ${PERIOD_COLORS[w.period_type] || 'bg-gray-100'}`}
                >
                  {PERIOD_LABELS[w.period_type] || w.period_type}
                </span>
                <span className="text-gray-600">
                  {w.start_time} – {w.end_time}
                </span>
                {w.source && <span className="text-gray-400">{w.source}</span>}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
