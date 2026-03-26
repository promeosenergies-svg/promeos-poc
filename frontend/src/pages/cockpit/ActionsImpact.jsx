/**
 * ActionsImpact — Liste actions prioritaires pour le cockpit exécutif.
 *
 * RÈGLE : zéro calcul métier. Les actions viennent de GET /api/actions/list.
 * Le composant affiche — ne calcule pas.
 *
 * Champs API réels :
 *   title, priority (int 1-5), severity, source_type, source_label,
 *   estimated_gain_eur, status, site_id, due_date, source_deeplink
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { getActionsList } from '../../services/api';
import { fmtEur } from '../../utils/format';

// ── PriorityBadge ────────────────────────────────────────────────────

function PriorityBadge({ priority }) {
  // priority: int 1-5 (1=critique, 5=faible)
  const cfg =
    priority <= 2
      ? { label: 'P0', bg: 'bg-red-50', text: 'text-red-700' }
      : priority <= 3
        ? { label: 'P1', bg: 'bg-amber-50', text: 'text-amber-700' }
        : { label: 'P2', bg: 'bg-blue-50', text: 'text-blue-700' };

  return (
    <span
      className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[9px] font-semibold ${cfg.bg} ${cfg.text}`}
    >
      {cfg.label}
    </span>
  );
}

// ── SourceTag ────────────────────────────────────────────────────────

function SourceTag({ sourceType, sourceLabel }) {
  const labels = {
    compliance: { label: 'DT', cls: 'bg-red-50 text-red-700' },
    billing: { label: 'Billing', cls: 'bg-amber-50 text-amber-700' },
    consumption: { label: 'Conso', cls: 'bg-teal-50 text-teal-700' },
    monitoring: { label: 'Monitoring', cls: 'bg-blue-50 text-blue-700' },
    purchase: { label: 'Achat', cls: 'bg-purple-50 text-purple-700' },
    insight: { label: 'Insight', cls: 'bg-indigo-50 text-indigo-700' },
    lever_engine: { label: 'Levier', cls: 'bg-green-50 text-green-700' },
    manual: { label: 'Manuel', cls: 'bg-gray-50 text-gray-600' },
  };
  const cfg = labels[sourceType] ?? { label: sourceLabel ?? '—', cls: 'bg-gray-50 text-gray-600' };
  return (
    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded ${cfg.cls}`}>{cfg.label}</span>
  );
}

// ── ActionRow ────────────────────────────────────────────────────────

function ActionRow({ action, totalGainEur }) {
  const navigate = useNavigate();
  const deeplink = action.source_deeplink ?? `/actions?id=${action.id}`;
  // Barre de progression proportionnelle au gain relatif (présentation, pas un KPI)
  const gainEur = action.estimated_gain_eur ?? 0;
  const barPct = totalGainEur > 0 ? Math.min(100, Math.round((gainEur / totalGainEur) * 100)) : 0;

  return (
    <div
      className="py-3 cursor-pointer hover:bg-gray-50 rounded px-2 -mx-2 transition-colors"
      onClick={() => navigate(deeplink)}
      data-testid="action-row"
    >
      <div className="flex items-start gap-2.5">
        <PriorityBadge priority={action.priority ?? 3} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900">
            {action.title ?? '—'}
            {action.site_nom && (
              <span className="text-gray-400 font-normal ml-1">— {action.site_nom}</span>
            )}
          </div>
          {(action.rationale || action.description) && (
            <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">
              {action.rationale ?? action.description}
            </div>
          )}
          <div className="flex items-center gap-1.5 mt-1">
            <SourceTag sourceType={action.source_type} sourceLabel={action.source_label} />
            {action.due_date && (
              <span className="text-[10px] text-gray-400">
                Éch. {new Date(action.due_date).toLocaleDateString('fr-FR')}
              </span>
            )}
          </div>
          {/* Barre de contribution — proportion relative du gain */}
          {barPct > 0 && (
            <div className="mt-1.5 h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-500 rounded-full transition-all"
                style={{ width: `${barPct}%` }}
              />
            </div>
          )}
        </div>
        <div className="text-right flex-shrink-0">
          {gainEur > 0 && (
            <div className="text-sm font-semibold text-green-700">{fmtEur(gainEur)}</div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── ActionsImpact ────────────────────────────────────────────────────

export default function ActionsImpact({ actions, loading }) {
  const navigate = useNavigate();
  const [actionsList, setActionsList] = useState([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState(null);

  useEffect(() => {
    setListLoading(true);
    getActionsList({ status: 'open,in_progress', limit: 6 })
      .then((data) => {
        const items = data?.actions ?? data?.items ?? data ?? [];
        setActionsList(Array.isArray(items) ? items : []);
      })
      .catch((err) => setListError(err.message))
      .finally(() => setListLoading(false));
  }, []);

  const isLoading = loading || listLoading;
  // Total gain pour la barre de proportion (présentation, pas un KPI)
  const totalGainEur = actionsList.reduce((s, a) => s + (a.estimated_gain_eur ?? 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4" data-testid="actions-impact">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          Actions · impact sur trajectoire
        </span>
        <span className="text-[10px] font-medium text-gray-600 border border-gray-200 px-2.5 py-1 rounded-full">
          {actions?.enCours ?? 0} en cours · {actions?.total ?? 0} planifiées
        </span>
      </div>

      {/* Liste actions */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex gap-2 items-start">
              <div className="w-5 h-5 bg-gray-100 rounded-full animate-pulse" />
              <div className="flex-1 space-y-1">
                <div className="h-3.5 bg-gray-100 rounded animate-pulse w-3/4" />
                <div className="h-2.5 bg-gray-100 rounded animate-pulse w-1/2" />
              </div>
            </div>
          ))}
        </div>
      ) : listError ? (
        <p className="text-xs text-gray-400 text-center py-4">Impossible de charger les actions.</p>
      ) : actionsList.length === 0 ? (
        <p className="text-xs text-gray-500 text-center py-4">
          Aucune action prioritaire en cours.
        </p>
      ) : (
        <div className="divide-y divide-gray-50">
          {actionsList.slice(0, 6).map((action) => (
            <ActionRow key={action.id} action={action} totalGainEur={totalGainEur} />
          ))}
        </div>
      )}

      {/* Footer — toujours visible (maquette) */}
      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
        <span className="text-xs text-gray-500">
          {actions?.potentielEur > 0 ? (
            <>
              Actions planifiées · Économie potentielle :
              <span className="text-green-700 font-medium ml-1">
                {fmtEur(actions.potentielEur)}/an
              </span>
            </>
          ) : (
            'Actions planifiées'
          )}
        </span>
        <button
          onClick={() => navigate('/actions')}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 px-3 py-1.5 border border-blue-200 rounded-lg hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
        >
          Voir toutes les actions <ArrowRight size={12} />
        </button>
      </div>
    </div>
  );
}
