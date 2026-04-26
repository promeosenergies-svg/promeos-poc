/**
 * CockpitTabs — wrapper sticky autour du composant Tabs partagé du DS.
 *
 * Délègue le rendu des onglets à <Tabs> (`ui/Tabs.jsx`) — pas de duplication
 * du design system. Ajoute juste :
 *   - le wrapping sticky `top-0 z-10 bg-white -mx-6 px-6 pt-2` propre aux tabs
 *     cockpit (collées au top du contenu PageShell quand on scrolle)
 *   - le routing client-side via `useNavigate` (Tabs émet l'id, on le mappe)
 */
import { useNavigate } from 'react-router-dom';
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
  return (
    <div className="sticky top-0 z-10 bg-white -mx-6 px-6 pt-2 mb-4">
      <Tabs
        tabs={COCKPIT_TABS}
        active={active}
        onChange={(id) => navigate(ROUTE_BY_ID[id] ?? '/')}
      />
    </div>
  );
}
