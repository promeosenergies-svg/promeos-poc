/**
 * CockpitTabs — wrapper sticky autour du composant Tabs partagé du DS.
 *
 * Délègue le rendu des onglets à <Tabs> (`ui/Tabs.jsx`) — pas de duplication
 * du design system. Ajoute :
 *   - sticky `top-0 z-10 bg-white -mx-6 px-6 pt-2` propre aux tabs cockpit
 *   - routing client-side via `useNavigate`
 *   - Phase 3.5 : préservation de `?tab=...` & autres query params au switch,
 *     pour deep-link partageable (ex. `/cockpit?tab=trajectoire`).
 */
import { useNavigate, useLocation } from 'react-router-dom';
import Tabs from './Tabs';

const COCKPIT_TABS = [
  { id: 'dashboard', label: 'Tableau de bord' },
  { id: 'cockpit', label: 'Vue exécutive' },
];

const ROUTE_BY_ID = {
  dashboard: '/',
  cockpit: '/cockpit',
};

export default function CockpitTabs({ active }) {
  const navigate = useNavigate();
  const location = useLocation();
  // Guard tab actif : éviter navigate() inutile (perte focus + scroll-to-top)
  const handleChange = (id) => {
    if (id === active) return;
    const path = ROUTE_BY_ID[id] ?? '/';
    // Préserver les query params actuels pour le deep-link inter-tabs.
    navigate({ pathname: path, search: location.search });
  };
  return (
    <div className="sticky top-0 z-10 bg-white -mx-6 px-6 pt-2 mb-4">
      <Tabs tabs={COCKPIT_TABS} active={active} onChange={handleChange} />
    </div>
  );
}
