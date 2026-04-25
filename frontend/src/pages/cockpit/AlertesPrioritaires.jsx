/**
 * AlertesPrioritaires — Top 3 alertes/actions urgentes pour le cockpit exécutif.
 *
 * Sprint CX 2 item B.2 : migration vers <FindingCard> unifié.
 * RÈGLE : display-only. Source : GET /api/actions/list (P0/P1).
 *
 * Principe "Rule of 3" — max 3 items, numérotés #1/#2/#3 pour Exception-first.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getActionsList } from '../../services/api';
import { useScope } from '../../contexts/ScopeContext';
import { Skeleton, FindingCard } from '../../ui';

// Severity résolu depuis priority + severity backend
function resolveSeverity(item) {
  if (item.severity === 'critical' || item.priority === 1) return 'critical';
  if (item.severity === 'high' || item.priority === 2) return 'high';
  if (item.severity === 'medium' || item.priority === 3) return 'medium';
  return 'low';
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
        // C6 FIX : ne garder que les alertes urgentes (P0/P1, severity critical/high)
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
    <div data-testid="alertes-prioritaires">
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-xs text-gray-400 text-center py-4">
          Aucune alerte active — tout est sous contrôle.
        </p>
      ) : (
        <div className="space-y-2" data-testid="alertes-list">
          {items.map((item, idx) => (
            <FindingCard
              key={item.id}
              compact
              priority={idx + 1}
              severity={resolveSeverity(item)}
              category={item.source_type || 'compliance'}
              title={item.title}
              description={item.rationale}
              deadline={item.due_date}
              impact={{ eur: item.estimated_gain_eur }}
              onClick={() => navigate(item.source_deeplink ?? `/actions?id=${item.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
