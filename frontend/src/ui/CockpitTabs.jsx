/**
 * CockpitTabs — tabs sticky [Tableau de bord | Vue exécutive].
 *
 * Extrait depuis CommandCenter.jsx + Cockpit.jsx (où le composant était
 * dupliqué inline à l'identique). Source unique pour éviter le drift.
 *
 * Audit Navigation Phase 1 (sol2) : duplication identifiée comme P1.
 */
import { useNavigate } from 'react-router-dom';

export default function CockpitTabs({ active }) {
  const nav = useNavigate();
  return (
    <div className="flex gap-6 border-b border-gray-200 mb-4 sticky top-0 z-10 bg-white -mx-6 px-6 pt-2">
      <button
        onClick={() => nav('/')}
        className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
          active === 'dashboard'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'
        }`}
      >
        Tableau de bord
      </button>
      <button
        onClick={() => nav('/cockpit')}
        className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
          active === 'cockpit'
            ? 'border-blue-600 text-blue-600'
            : 'border-transparent text-gray-500 hover:text-gray-700'
        }`}
      >
        Vue exécutive
      </button>
    </div>
  );
}
