/**
 * PROMEOS — EnergyCrossLinks (Sprint P1.S7 polish transverse).
 *
 * Composant cross-links sobre placé en pied de vue Énergie pour orienter
 * vers les modules connexes (Facturation, Achat, Centre d'action,
 * Conformité). N'apparaît que si au moins 1 link est fourni.
 *
 * Doctrine :
 * - Pas de promesse d'économie certaine.
 * - Pas de calcul métier — uniquement de la navigation.
 * - Aucune route inventée — les routes cibles doivent exister dans
 *   NavRegistry. Vérifier avant tout ajout.
 */
import { Link } from 'react-router-dom';
import { ArrowUpRight, Receipt, ShoppingCart, Target, Shield } from 'lucide-react';

const ICONS = {
  bill: Receipt,
  achat: ShoppingCart,
  action: Target,
  conformite: Shield,
};

export default function EnergyCrossLinks({
  links = [],
  className = '',
  testId = 'energy-cross-links',
}) {
  const valid = links.filter((l) => l?.to && l?.label);
  if (valid.length === 0) return null;
  return (
    <div
      className={`rounded-lg border border-gray-200 bg-gray-50 p-3 flex flex-wrap items-center gap-2 text-xs ${className}`}
      data-testid={testId}
    >
      <span className="text-gray-500 font-medium mr-1">Aller plus loin :</span>
      {valid.map((l, i) => {
        const Icon = ICONS[l.kind] || ArrowUpRight;
        return (
          <Link
            key={`${l.to}-${i}`}
            to={l.to}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white border border-gray-200 text-gray-700 hover:border-blue-400 hover:text-blue-600 transition"
            data-testid={`cross-link-${l.kind || 'default'}`}
          >
            <Icon size={11} aria-hidden="true" />
            {l.label}
            <ArrowUpRight size={9} className="opacity-50" aria-hidden="true" />
          </Link>
        );
      })}
    </div>
  );
}
