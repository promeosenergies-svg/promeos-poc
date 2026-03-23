/**
 * AlertesPrioritaires — Top 3 alertes/actions urgentes pour le cockpit exécutif.
 *
 * RÈGLE : display-only. Sources : GET /api/actions/list (P0) + notifications.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Receipt, ShoppingCart, AlertTriangle } from 'lucide-react';
import { getActionsList } from '../../services/api';
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
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getActionsList({ status: 'open,in_progress', limit: 3 })
      .then((data) => {
        const actions = data?.actions ?? data?.items ?? data ?? [];
        setItems(Array.isArray(actions) ? actions.slice(0, 3) : []);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

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
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        days <= 7
                          ? 'bg-red-50 text-red-700'
                          : days <= 30
                            ? 'bg-amber-50 text-amber-700'
                            : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {days <= 0 ? 'Échu' : `${days} j`}
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
