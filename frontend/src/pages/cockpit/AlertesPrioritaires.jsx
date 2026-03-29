/**
 * AlertesPrioritaires — Top 3 alertes/actions urgentes pour le cockpit exécutif.
 *
 * RÈGLE : display-only. Sources : GET /api/actions/list (P0) + notifications.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Receipt, ShoppingCart, AlertTriangle } from 'lucide-react';
import { getActionsList } from '../../services/api';
import { useScope } from '../../contexts/ScopeContext';
import { fmtEur } from '../../utils/format';
import { Skeleton } from '../../ui';

const SOURCE_ICONS = {
  compliance: { icon: FileText, cls: 'text-red-500 bg-red-50' },
  billing: { icon: Receipt, cls: 'text-amber-500 bg-amber-50' },
  purchase: { icon: ShoppingCart, cls: 'text-blue-500 bg-blue-50' },
  consumption: { icon: AlertTriangle, cls: 'text-teal-500 bg-teal-50' },
};

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

export default function AlertesPrioritaires() {
  const navigate = useNavigate();
  const { org } = useScope();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!org?.id) return;
    setItems([]);
    setLoading(true);
    getActionsList({ status: 'open,in_progress', limit: 10 })
      .then((data) => {
        const actions = data?.actions ?? data?.items ?? data ?? [];
        const list = Array.isArray(actions) ? actions : [];
        // C6 FIX: ne garder que les alertes urgentes (P0/P1, severity critical/high)
        // pour éviter le doublon avec ActionsImpact qui affiche toutes les actions
        const urgent = list.filter(
          (a) =>
            (a.priority != null && a.priority <= 2) ||
            a.severity === 'critical' ||
            a.severity === 'high'
        );
        setItems(urgent.slice(0, 3));
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [org?.id]);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4"
      data-testid="alertes-prioritaires"
    >
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
        Alertes prioritaires
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 rounded" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">Aucune alerte active.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => {
            const src = SOURCE_ICONS[item.source_type] ?? SOURCE_ICONS.compliance;
            const Icon = src.icon;
            const days = daysUntil(item.due_date);

            return (
              <div
                key={item.id}
                className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => navigate(item.source_deeplink ?? `/actions?id=${item.id}`)}
              >
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${src.cls}`}
                >
                  <Icon size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-gray-800 truncate">{item.title}</div>
                  {item.rationale && (
                    <div className="text-[10px] text-gray-500 truncate">{item.rationale}</div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {item.estimated_gain_eur > 0 && (
                    <span className="text-[10px] font-medium text-amber-700">
                      {fmtEur(item.estimated_gain_eur)}
                    </span>
                  )}
                  {days != null && (
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        days <= 0
                          ? 'bg-red-50 text-red-700 border-red-200'
                          : days <= 30
                            ? 'bg-red-50 text-red-700 border-red-200'
                            : days <= 90
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-blue-50 text-blue-700 border-blue-200'
                      }`}
                    >
                      {days <= 0 ? 'Dépassé' : `J-${days}`}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
