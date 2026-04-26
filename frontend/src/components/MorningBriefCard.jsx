import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Sunrise, Bell, Receipt, CheckCircle, ArrowRight, X } from 'lucide-react';

const LAST_VISIT_KEY = 'promeos_last_visit';

function getLastVisit() {
  try {
    const v = localStorage.getItem(LAST_VISIT_KEY);
    return v ? new Date(v) : null;
  } catch {
    return null;
  }
}

function ackVisit() {
  try {
    localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString());
  } catch {
    /* noop */
  }
}

function formatAgo(date) {
  if (!date) return null;
  const diff = Date.now() - date.getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "moins d'une heure";
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  return `${d}j`;
}

// Phase 4 quick win — Marie revient lundi 8h45 avec sitesCount > 0 et
// dernière visite récente : pas besoin de re-saluer, on laisse l'ATF au
// contenu décisionnel (Priority + KPIs J-1). Cf. audit CX 26/04/2026.
const RECENT_VISIT_HOURS = 168; // 7 jours

export default function MorningBriefCard({
  alerts = 0,
  invoices = 0,
  actionsClosed = 0,
  sitesCount = 0,
}) {
  const [lastVisit] = useState(() => getLastVisit());
  const [dismissed, setDismissed] = useState(false);

  // Don't sum positive + negative news
  const hasNews = alerts > 0 || invoices > 0 || actionsClosed > 0;
  const ago = formatAgo(lastVisit);
  const hoursSinceVisit = lastVisit ? (Date.now() - lastVisit.getTime()) / 3_600_000 : null;
  const isRecentReturnWithSites =
    sitesCount > 0 && hoursSinceVisit !== null && hoursSinceVisit < RECENT_VISIT_HOURS;

  // Auto-hide : utilisateur récurrent (<7j) avec patrimoine peuplé et aucune
  // news → on supprime le bandeau plutôt que d'écraser l'ATF.
  if (dismissed || (isRecentReturnWithSites && !hasNews)) return null;

  const handleAck = () => {
    ackVisit();
    setDismissed(true);
  };

  // Phase 3.2 — Compact strip mode : pas de news + pas d'historique de visite
  // → bandeau 32px de bienvenue plutôt que 80px. Audit UX : ~50px gagnés ATF.
  if (!hasNews && ago == null) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-blue-50 border border-blue-100 text-xs text-blue-700 max-w-sol-strip">
        <Sunrise size={13} className="text-amber-500 shrink-0" aria-hidden="true" />
        <span className="font-medium">Bienvenue sur PROMEOS</span>
        <span className="text-blue-500">— vos prochaines actions seront listées ici.</span>
        <button
          type="button"
          onClick={handleAck}
          aria-label="Masquer"
          className="ml-auto p-0.5 text-blue-400 hover:text-blue-700 transition"
        >
          <X size={11} aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className="relative bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-2xl p-4 max-w-sol-strip">
      <button
        type="button"
        onClick={handleAck}
        aria-label="Marquer comme vu"
        className="absolute top-2 right-2 p-1 text-gray-400 hover:text-gray-600 hover:bg-white/60 rounded transition"
      >
        <X size={14} aria-hidden="true" />
      </button>

      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 bg-white/80 rounded-lg shrink-0">
          <Sunrise size={18} className="text-amber-500" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-gray-900">
            {ago == null
              ? 'Bienvenue sur PROMEOS'
              : hasNews
                ? 'Depuis votre dernière visite'
                : 'Rien de neuf depuis votre dernière visite'}
          </h3>
          {ago != null && <p className="text-[11px] text-gray-500 mt-0.5">Il y a {ago}</p>}
        </div>
      </div>

      {hasNews && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {alerts > 0 && (
            <Link
              to="/anomalies?tab=actions"
              aria-label={`${alerts} nouvelles alertes`}
              className="flex items-center gap-2 p-2 bg-white/70 hover:bg-white border border-red-100 rounded-lg text-xs group transition"
            >
              <Bell size={14} className="text-red-500 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-gray-700">
                <span className="font-semibold text-red-600">{alerts}</span> alertes
              </span>
              <ArrowRight
                size={12}
                className="text-gray-400 group-hover:text-gray-600"
                aria-hidden="true"
              />
            </Link>
          )}
          {invoices > 0 && (
            <Link
              to="/bill-intel"
              aria-label={`${invoices} nouvelles factures`}
              className="flex items-center gap-2 p-2 bg-white/70 hover:bg-white border border-amber-100 rounded-lg text-xs group transition"
            >
              <Receipt size={14} className="text-amber-500 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-gray-700">
                <span className="font-semibold text-amber-600">{invoices}</span> factures
              </span>
              <ArrowRight
                size={12}
                className="text-gray-400 group-hover:text-gray-600"
                aria-hidden="true"
              />
            </Link>
          )}
          {actionsClosed > 0 && (
            <Link
              to="/anomalies?tab=actions&status=done"
              aria-label={`${actionsClosed} actions closées`}
              className="flex items-center gap-2 p-2 bg-white/70 hover:bg-white border border-emerald-100 rounded-lg text-xs group transition"
            >
              <CheckCircle size={14} className="text-emerald-500 shrink-0" aria-hidden="true" />
              <span className="flex-1 text-gray-700">
                <span className="font-semibold text-emerald-600">{actionsClosed}</span> closées
              </span>
              <ArrowRight
                size={12}
                className="text-gray-400 group-hover:text-gray-600"
                aria-hidden="true"
              />
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
