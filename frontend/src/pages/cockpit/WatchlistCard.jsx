/**
 * PROMEOS — WatchlistCard (Sprint WOW Phase 7.0)
 * "À surveiller" feed — severity-sorted watchlist, max 5 items.
 * Empty state: "Tout va bien ✓".
 *
 * Props:
 *   watchlist    {WatchItem[]}  — from buildWatchlist()
 *   consistency  {{ ok, issues }} — from checkConsistency()
 *   onNavigate   {fn}           — navigate(path)
 */
import { CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardBody, Button, Badge } from '../../ui';
import { SEVERITY_TINT } from '../../ui/colorTokens';

// ── Severity dot ─────────────────────────────────────────────────────────────

function SevDot({ severity }) {
  const s = SEVERITY_TINT[severity] || SEVERITY_TINT.neutral;
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 mt-1 ${s.dot}`} />;
}

// ── Watchlist header badge ─────────────────────────────────────────────────

function HeaderBadge({ count, hasCritical }) {
  if (!count) return null;
  return (
    <span className={`inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-semibold ${
      hasCritical ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-amber-50 text-amber-700 border border-amber-200'
    }`}>
      {count}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function WatchlistCard({ watchlist = [], consistency = { ok: true, issues: [] }, onNavigate }) {
  const hasCritical = watchlist.some(i => i.severity === 'critical');

  return (
    <Card>
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-800">À surveiller</h3>
          <HeaderBadge count={watchlist.length} hasCritical={hasCritical} />
        </div>
      </div>

      <CardBody className="py-2">
        {/* Consistency banner (amber) */}
        {!consistency.ok && consistency.issues.length > 0 && (
          <div className="flex items-start gap-2 px-1 py-2 mb-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />
            <span>{consistency.issues[0].label} — synchronisation recommandée.</span>
          </div>
        )}

        {/* Watchlist items */}
        {watchlist.length > 0 ? (
          <ul className="space-y-0">
            {watchlist.map((item, idx) => (
              <li
                key={item.id}
                className={`flex items-start justify-between gap-3 py-2.5 ${
                  idx < watchlist.length - 1 ? 'border-b border-gray-50' : ''
                }`}
              >
                <div className="flex items-start gap-2.5 min-w-0">
                  <SevDot severity={item.severity} />
                  <span className="text-sm text-gray-700 leading-snug">{item.label}</span>
                </div>
                {item.cta && item.path && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => onNavigate?.(item.path)}
                    className="shrink-0 text-xs"
                  >
                    {item.cta} →
                  </Button>
                )}
              </li>
            ))}
          </ul>
        ) : (
          /* Empty state — all good */
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center mb-3">
              <CheckCircle size={20} className="text-emerald-500" />
            </div>
            <p className="text-sm font-semibold text-gray-700 mb-1">Tout va bien</p>
            <p className="text-xs text-gray-400 mb-3">
              Aucun signal à traiter pour le moment.
            </p>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onNavigate?.('/consommations/import')}
              className="text-xs text-gray-400"
            >
              Synchroniser les données
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
