/**
 * PriorityActions — Bannière priorité #1 + cards actions catégorisées.
 * Données 100% backend via /cockpit/executive-v2 → actions.
 *
 * Sprint CX UX migration (4/66) : rendu unifié via <FindingCard>.
 * Le banner #1 est une FindingCard non-compact avec CTA actionLabel.
 * Les actions #2+ sont en grid 3-col avec FindingCard compact.
 */
import { useNavigate } from 'react-router-dom';
import { CheckCircle2 } from 'lucide-react';
import { FindingCard } from '../../ui';

// Map categorie backend → FindingCard category + severity
// (priorite #1 = critical toujours, actions #2+ prennent la severity mappée)
const CATEGORIE_TO_CATEGORY = {
  conformite: 'compliance',
  facturation: 'billing',
  optimisation: 'consumption',
  achat: 'purchase',
};

const CATEGORIE_TO_SEVERITY = {
  conformite: 'high',
  facturation: 'high',
  optimisation: 'medium',
  achat: 'medium',
};

export default function PriorityActions({ actions }) {
  const navigate = useNavigate();

  if (!actions || actions.length === 0) {
    return (
      <div className="flex items-center gap-3 px-5 py-4 bg-emerald-50 border border-emerald-200 rounded-xl">
        <CheckCircle2 size={20} className="text-emerald-600 shrink-0" />
        <p className="text-sm font-semibold text-emerald-800">
          Aucune action prioritaire — votre patrimoine est sous contrôle
        </p>
      </div>
    );
  }

  const [priority1, ...rest] = actions;

  return (
    <div className="space-y-3">
      {/* Bannière priorité #1 : FindingCard non-compact, severity=critical toujours */}
      {priority1 && (
        <FindingCard
          priority={1}
          severity="critical"
          category={CATEGORIE_TO_CATEGORY[priority1.categorie]}
          title={priority1.titre}
          description={priority1.description}
          impact={{ eur: priority1.impact_eur }}
          actionLabel={priority1.cta}
          onAction={() => navigate(priority1.lien)}
          onClick={() => navigate(priority1.lien)}
        />
      )}

      {/* Grid actions #2+ : FindingCard compact en 3-col */}
      {rest.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {rest.map((action, idx) => (
            <FindingCard
              key={action.id}
              compact
              priority={idx + 2}
              severity={CATEGORIE_TO_SEVERITY[action.categorie] || 'medium'}
              category={CATEGORIE_TO_CATEGORY[action.categorie]}
              title={action.titre}
              description={action.description}
              impact={{ eur: action.impact_eur }}
              actionLabel={action.cta}
              onAction={() => navigate(action.lien)}
              onClick={() => navigate(action.lien)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
