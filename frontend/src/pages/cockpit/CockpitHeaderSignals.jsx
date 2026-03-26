import { Zap, Leaf, Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useCockpitSignals } from '../../hooks/useCockpitSignals';

/**
 * Pills de signaux marché affichées dans le header du cockpit.
 * Zéro calcul — display-only depuis le hook.
 */
export default function CockpitHeaderSignals() {
  const { epexEurMwh, co2GKwh, alertesCount, loading } = useCockpitSignals();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex items-center gap-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-6 w-20 bg-gray-100 rounded-full animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs">
      {/* EPEX Spot */}
      {epexEurMwh != null && (
        <button
          onClick={() => navigate('/achat-energie')}
          className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 font-medium border border-amber-200 hover:bg-amber-100 transition focus-visible:ring-2 focus-visible:ring-amber-500"
          title="Prix EPEX Spot FR — cliquer pour les scénarios d'achat"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          EPEX {Math.round(epexEurMwh)} €/MWh
        </button>
      )}

      {/* CO₂ réseau */}
      <span
        className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 font-medium border border-teal-200"
        title="Intensité CO₂ réseau électrique"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
        CO₂ {co2GKwh != null ? `${Math.round(co2GKwh)} g/kWh` : '— g/kWh'}
      </span>

      {/* Badge alertes */}
      {alertesCount != null && alertesCount > 0 && (
        <button
          onClick={() => navigate('/notifications')}
          className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-50 text-red-700 font-medium border border-red-200 hover:bg-red-100 transition focus-visible:ring-2 focus-visible:ring-red-500"
          title={`${alertesCount} alerte${alertesCount > 1 ? 's' : ''} active${alertesCount > 1 ? 's' : ''}`}
        >
          <Bell size={11} />
          {alertesCount} alerte{alertesCount > 1 ? 's' : ''}
        </button>
      )}
    </div>
  );
}
