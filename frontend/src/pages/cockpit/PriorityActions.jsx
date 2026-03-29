/**
 * PriorityActions — Bannière priorité #1 + cards actions catégorisées.
 * Données 100% backend via /cockpit/executive-v2 → actions.
 */
import { useNavigate } from 'react-router-dom';
import { ArrowRight, CheckCircle2 } from 'lucide-react';
import { fmtEur } from '../../utils/format';

const CATEGORIE_STYLE = {
  conformite: { bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-200' },
  facturation: { bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-200' },
  optimisation: { bg: 'bg-emerald-50', text: 'text-emerald-800', border: 'border-emerald-200' },
  achat: { bg: 'bg-purple-50', text: 'text-purple-800', border: 'border-purple-200' },
};

const PRIORITY_BORDER = {
  conformite: 'border-red-500',
  facturation: 'border-amber-500',
  optimisation: 'border-emerald-500',
  achat: 'border-purple-500',
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
      {/* Bannière priorité #1 */}
      {priority1 && (
        <div
          className={`rounded-xl border bg-white border-l-[3px] ${PRIORITY_BORDER[priority1.categorie] || 'border-red-500'} px-5 py-4 cursor-pointer hover:shadow-sm transition`}
          onClick={() => navigate(priority1.lien)}
        >
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">
                  Priorité #1
                </span>
                <CategoryPill categorie={priority1.categorie} />
              </div>
              <p className="text-base font-semibold text-gray-900">{priority1.titre}</p>
              <p className="text-xs text-gray-500 mt-0.5">{priority1.description}</p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {priority1.impact_eur != null && (
                <span className="text-lg font-bold text-red-700">
                  {fmtEur(priority1.impact_eur)}
                </span>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(priority1.lien);
                }}
                className="px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition flex items-center gap-1"
              >
                {priority1.cta} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Grid actions #2+ */}
      {rest.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {rest.map((action) => (
            <div
              key={action.id}
              className="rounded-xl border border-gray-200 bg-white px-4 py-3.5 cursor-pointer hover:shadow-sm transition"
              onClick={() => navigate(action.lien)}
            >
              <CategoryPill categorie={action.categorie} />
              <p className="text-sm font-semibold text-gray-900 mt-1.5">{action.titre}</p>
              <p className="text-xs text-gray-500 mt-0.5">{action.description}</p>
              <div className="flex items-center justify-between mt-3">
                {action.impact_eur != null ? (
                  <span className="text-sm font-bold text-gray-700">
                    {fmtEur(action.impact_eur)}
                  </span>
                ) : (
                  <span />
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(action.lien);
                  }}
                  className="text-xs font-medium text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  {action.cta} <ArrowRight size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryPill({ categorie }) {
  const style = CATEGORIE_STYLE[categorie] || CATEGORIE_STYLE.conformite;
  const labels = {
    conformite: 'Conformité',
    facturation: 'Facturation',
    optimisation: 'Optimisation',
    achat: 'Achat énergie',
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-medium ${style.bg} ${style.text}`}
    >
      {labels[categorie] || categorie}
    </span>
  );
}
