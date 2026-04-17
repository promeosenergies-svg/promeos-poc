/**
 * PROMEOS — ValueCounterCard (CX Gap #6)
 * Widget affichant la valeur cumulée créée par PROMEOS depuis l'abonnement.
 * S'affiche uniquement si total_eur > 0. Zéro calcul frontend.
 */
import { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';
import { getValueSummary } from '../services/api/cockpit';
import { fmtEur } from '../utils/format';

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
  } catch {
    return '';
  }
}

export default function ValueCounterCard({ orgId }) {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!orgId) return;
    getValueSummary(orgId)
      .then(setData)
      .catch(() => setData(null));
  }, [orgId]);

  if (!data || !data.total_eur || data.total_eur <= 0) return null;

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 mb-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-0.5">
            Valeur créée par PROMEOS
          </p>
          <p className="text-2xl font-bold text-emerald-900 truncate">{fmtEur(data.total_eur)}</p>
          <p className="text-xs text-emerald-700 mt-0.5">
            depuis {formatDate(data.since)} — {data.insights_count} insights
          </p>
        </div>
        <TrendingUp className="h-7 w-7 text-emerald-400 flex-shrink-0" />
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-[11px] text-emerald-800">
        <span>Anomalies : {fmtEur(data.anomalies_detected_eur)}</span>
        <span>Pénalités évitées : {fmtEur(data.penalties_avoided_eur)}</span>
      </div>
    </div>
  );
}
