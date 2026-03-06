/**
 * PROMEOS — FreshnessIndicator (D.2)
 * Badge compact montrant la fraîcheur des données d'un site.
 *
 * Props :
 *   freshness : { status, label_fr, staleness_days, last_reading, last_invoice, recommendations }
 *   size      : 'sm' | 'md' (default: 'sm')
 *   showBanner: boolean — affiche un bandeau "Données périmées" si expired (default: false)
 *   onImport  : function — callback CTA "Importer des données"
 */
import { useState, useRef, useEffect } from 'react';
import { Clock, AlertTriangle, CheckCircle, RefreshCw, Upload } from 'lucide-react';
import Explain from '../ui/Explain';

const STATUS_CONFIG = {
  fresh: {
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    icon: CheckCircle,
    dot: 'bg-green-500',
  },
  recent: {
    color: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    icon: Clock,
    dot: 'bg-blue-500',
  },
  stale: {
    color: 'text-amber-600',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    icon: RefreshCw,
    dot: 'bg-amber-500',
  },
  expired: {
    color: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-200',
    icon: AlertTriangle,
    dot: 'bg-red-500',
  },
  no_data: {
    color: 'text-gray-400',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    icon: Upload,
    dot: 'bg-gray-400',
  },
};

function formatDate(isoStr) {
  if (!isoStr) return null;
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return isoStr;
  }
}

export default function FreshnessIndicator({ freshness, size = 'sm', showBanner = false, onImport }) {
  const [popoverOpen, setPopoverOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!popoverOpen) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setPopoverOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [popoverOpen]);

  if (!freshness) return null;

  const cfg = STATUS_CONFIG[freshness.status] || STATUS_CONFIG.no_data;
  const Icon = cfg.icon;

  // ── sm: dot + label only ──
  if (size === 'sm') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 text-xs ${cfg.color}`}
        title={`Fraîcheur : ${freshness.label_fr} (${freshness.staleness_days}j)`}
        data-testid="freshness-sm"
      >
        <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
        {freshness.label_fr}
      </span>
    );
  }

  // ── md: icon + label + popover ──
  return (
    <div ref={ref} className="relative inline-block" data-testid="freshness-md">
      <button
        onClick={() => setPopoverOpen((o) => !o)}
        className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${cfg.color} ${cfg.bg} border ${cfg.border} hover:opacity-80 transition`}
      >
        <Icon size={12} />
        {freshness.label_fr}
        {freshness.staleness_days < 999 && (
          <span className="text-[10px] opacity-70">({freshness.staleness_days}j)</span>
        )}
      </button>

      {popoverOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden">
          <div className={`px-4 py-2.5 border-b ${cfg.bg}`}>
            <div className="flex items-center gap-2">
              <Icon size={14} className={cfg.color} />
              <h4 className={`text-sm font-semibold ${cfg.color}`}>
                <Explain term="freshness">{freshness.label_fr}</Explain>
              </h4>
            </div>
          </div>

          <div className="px-4 py-3 space-y-2 text-xs text-gray-600">
            {freshness.last_reading && (
              <div className="flex justify-between">
                <span>Dernier relevé</span>
                <span className="font-medium text-gray-800">{formatDate(freshness.last_reading)}</span>
              </div>
            )}
            {freshness.last_invoice && (
              <div className="flex justify-between">
                <span>Dernière facture</span>
                <span className="font-medium text-gray-800">{formatDate(freshness.last_invoice)}</span>
              </div>
            )}
            {!freshness.last_reading && !freshness.last_invoice && (
              <p className="text-gray-400 italic">Aucune donnée disponible</p>
            )}
          </div>

          {freshness.recommendations?.length > 0 && (
            <div className="px-4 py-2 border-t border-gray-100">
              <ul className="space-y-1">
                {freshness.recommendations.map((r, i) => (
                  <li key={i} className="text-[11px] text-gray-600 flex items-start gap-1.5">
                    <span className="text-amber-500 mt-0.5">•</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {onImport && (freshness.status === 'expired' || freshness.status === 'no_data') && (
            <div className="px-4 py-2.5 border-t border-gray-100 bg-gray-50/50">
              <button
                onClick={() => { onImport(); setPopoverOpen(false); }}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                <Upload size={12} />
                Importer des données
              </button>
            </div>
          )}
        </div>
      )}

      {/* Banner for expired data */}
      {showBanner && (freshness.status === 'expired' || freshness.status === 'no_data') && (
        <div
          className="mt-2 flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg"
          data-testid="freshness-expired-banner"
        >
          <AlertTriangle size={14} className="text-red-600 shrink-0" />
          <span className="text-xs text-red-800">
            Données périmées ({freshness.staleness_days > 900 ? 'aucune donnée' : `${freshness.staleness_days} jours`}) — les KPIs affichés peuvent être obsolètes.
          </span>
          {onImport && (
            <button
              onClick={onImport}
              className="ml-auto text-xs font-semibold text-red-700 hover:text-red-900 whitespace-nowrap"
            >
              Importer
            </button>
          )}
        </div>
      )}
    </div>
  );
}
