/**
 * AlertStack — pile de bannières triée par sévérité, masque la queue.
 *
 * Trie critical → warn → info → ok, n'affiche que `maxVisible` (default 2),
 * propose un chip "+N alertes" pour révéler le reste. Évite la saturation
 * cognitive quand 5+ bannières conditionnelles convergent.
 *
 * Display-only : accepte des nodes JSX déjà rendus dans `alerts[]`.
 *
 * Usage :
 *   <AlertStack
 *     alerts={[{ id, severity: 'critical', node: <BannerJSX /> }, ...]}
 *     maxVisible={2}
 *   />
 */
import { useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { SEVERITY_RANK, normalizeSeverity } from './severity';

export default function AlertStack({ alerts = [], maxVisible = 2 }) {
  const [expanded, setExpanded] = useState(false);

  const sorted = useMemo(() => {
    const valid = (alerts ?? []).filter((a) => a && a.node);
    const rank = (sev) => SEVERITY_RANK[normalizeSeverity(sev)] ?? 99;
    return valid.slice().sort((a, b) => rank(a.severity) - rank(b.severity));
  }, [alerts]);

  if (sorted.length === 0) return null;

  const visible = expanded ? sorted : sorted.slice(0, maxVisible);
  const hidden = Math.max(0, sorted.length - maxVisible);

  return (
    <div className="space-y-2" data-testid="alert-stack">
      {visible.map((a) => (
        <div key={a.id}>{a.node}</div>
      ))}
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="inline-flex items-center gap-1.5 px-3 py-1 text-[11px] font-medium text-gray-600 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          {expanded ? (
            <>
              <ChevronUp size={12} aria-hidden="true" />
              Masquer {hidden} alerte{hidden > 1 ? 's' : ''} de plus
            </>
          ) : (
            <>
              <ChevronDown size={12} aria-hidden="true" />+{hidden} alerte{hidden > 1 ? 's' : ''} de
              moindre sévérité
            </>
          )}
        </button>
      )}
    </div>
  );
}
