/**
 * PROMEOS — ShadowBreakdownCard (Step 28)
 * Décomposition shadow par composante : fourniture / TURPE / taxes / TVA.
 * Barres empilées + écart par composante + badge confiance.
 */
import { useExpertMode } from '../../contexts/ExpertModeContext';
import { Explain } from '../../ui';

const STATUS_COLORS = {
  ok: { bar: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  warn: { bar: 'bg-amber-400', text: 'text-amber-700', bg: 'bg-amber-50' },
  alert: { bar: 'bg-red-400', text: 'text-red-700', bg: 'bg-red-50' },
};

const CONFIDENCE_BADGE = {
  high: { label: 'Confiance élevée', color: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  medium: { label: 'Confiance moyenne', color: 'bg-amber-50 text-amber-700 ring-amber-200' },
  low: { label: 'Confiance faible', color: 'bg-red-50 text-red-700 ring-red-200' },
};

function fmt(val) {
  if (val == null) return '—';
  return val.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function ShadowBreakdownCard({ breakdown }) {
  const { isExpert } = useExpertMode();

  if (!breakdown || !breakdown.components) {
    return (
      <div className="bg-gray-50 rounded-lg p-4 text-center">
        <p className="text-sm text-gray-500">Décomposition non disponible</p>
      </div>
    );
  }

  const {
    components,
    total_expected_ht,
    total_invoice_ht,
    total_gap_eur,
    total_gap_pct,
    confidence,
    tarif_version,
    segment,
  } = breakdown;
  const confBadge = CONFIDENCE_BADGE[confidence] || CONFIDENCE_BADGE.low;

  // Calcul largeur des barres (proportionnel à expected_eur)
  const totalExpected = components.reduce((s, c) => s + (c.expected_eur || 0), 0);

  return (
    <div className="space-y-4">
      {/* En-tête : totaux + confiance */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase">
            <Explain term="shadow_breakdown">Décomposition shadow</Explain>
          </h4>
          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-sm text-gray-600">
              Attendu HT :{' '}
              <span className="font-semibold text-gray-900">{fmt(total_expected_ht)} EUR</span>
            </span>
            {total_invoice_ht > 0 && (
              <span className="text-sm text-gray-600">
                Facturé :{' '}
                <span className="font-semibold text-gray-900">{fmt(total_invoice_ht)} EUR</span>
              </span>
            )}
            {total_gap_eur != null && total_gap_eur !== 0 && (
              <span
                className={`text-sm font-bold ${total_gap_eur > 0 ? 'text-red-600' : 'text-green-600'}`}
              >
                {total_gap_eur > 0 ? '+' : ''}
                {fmt(total_gap_eur)} EUR
                {total_gap_pct != null && (
                  <span className="ml-1 text-xs font-normal">
                    ({total_gap_pct > 0 ? '+' : ''}
                    {total_gap_pct.toFixed(1)}%)
                  </span>
                )}
              </span>
            )}
          </div>
        </div>
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ring-1 ${confBadge.color}`}>
          {confBadge.label}
        </span>
      </div>

      {/* Barre empilée */}
      <div className="w-full bg-gray-100 rounded-full h-3 flex overflow-hidden">
        {components.map((c) => {
          const pct = totalExpected > 0 ? (c.expected_eur / totalExpected) * 100 : 25;
          const colors = STATUS_COLORS[c.status] || STATUS_COLORS.ok;
          return (
            <div
              key={c.name}
              className={`${colors.bar} h-3 transition-all`}
              style={{ width: `${pct}%` }}
              title={`${c.label}: ${fmt(c.expected_eur)} EUR attendu`}
            />
          );
        })}
      </div>

      {/* Détail par composante */}
      <div className="space-y-2">
        {components.map((c) => {
          const colors = STATUS_COLORS[c.status] || STATUS_COLORS.ok;
          const hasInvoice = c.invoice_eur != null;
          return (
            <div key={c.name} className={`rounded-lg p-3 ${colors.bg} border border-gray-100`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-800">{c.label}</span>
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-gray-600">
                    Attendu : <span className="font-medium">{fmt(c.expected_eur)} EUR</span>
                  </span>
                  {hasInvoice ? (
                    <>
                      <span className="text-gray-600">
                        Facturé : <span className="font-medium">{fmt(c.invoice_eur)} EUR</span>
                      </span>
                      <span
                        className={`font-bold ${c.gap_eur > 0 ? 'text-red-600' : c.gap_eur < 0 ? 'text-green-600' : 'text-gray-500'}`}
                      >
                        {c.gap_eur > 0 ? '+' : ''}
                        {fmt(c.gap_eur)} EUR
                        {c.gap_pct != null && (
                          <span className="ml-1 text-xs font-normal">
                            ({c.gap_pct > 0 ? '+' : ''}
                            {c.gap_pct}%)
                          </span>
                        )}
                      </span>
                    </>
                  ) : (
                    <span className="text-xs text-gray-400 italic">Détail non disponible</span>
                  )}
                </div>
              </div>
              {/* Barre de gap */}
              {hasInvoice && c.gap_pct != null && (
                <div className="w-full bg-gray-200 rounded-full h-1 mt-1">
                  <div
                    className={`h-1 rounded-full transition-all ${c.gap_eur > 0 ? 'bg-red-400' : 'bg-green-400'}`}
                    style={{ width: `${Math.min(Math.abs(c.gap_pct), 100)}%` }}
                  />
                </div>
              )}
              {/* Méthodologie (mode Expert) */}
              {isExpert && c.methodology && (
                <p className="text-xs text-gray-500 mt-1">{c.methodology}</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Meta (mode Expert) */}
      {isExpert && (
        <div className="flex items-center gap-4 text-xs text-gray-400 pt-2 border-t border-gray-100">
          {tarif_version && <span>Tarifs : {tarif_version}</span>}
          {segment && <span>Segment : {segment}</span>}
          {breakdown.energy_type && <span>Energie : {breakdown.energy_type}</span>}
          {breakdown.days_in_period && <span>Période : {breakdown.days_in_period} jours</span>}
        </div>
      )}
    </div>
  );
}
