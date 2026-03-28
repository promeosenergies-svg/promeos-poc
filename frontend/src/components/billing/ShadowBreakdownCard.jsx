/**
 * PROMEOS — ShadowBreakdownCard (V2 Engine)
 * Décomposition reconstitution par composante : fourniture / TURPE / CTA / accise.
 * Barres empilées + écart par composante + statut reconstitution honnête.
 */
import { useExpertMode } from '../../contexts/ExpertModeContext';
import { Explain } from '../../ui';

const STATUS_COLORS = {
  ok: { bar: 'bg-emerald-400', text: 'text-emerald-700', bg: 'bg-emerald-50' },
  warn: { bar: 'bg-amber-400', text: 'text-amber-700', bg: 'bg-amber-50' },
  alert: { bar: 'bg-red-400', text: 'text-red-700', bg: 'bg-red-50' },
  unknown: { bar: 'bg-gray-300', text: 'text-gray-600', bg: 'bg-gray-50' },
};

const RECON_STATUS = {
  RECONSTITUTED: {
    label: 'Reconstitution complète',
    color: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  },
  PARTIAL: {
    label: 'Reconstitution partielle',
    color: 'bg-amber-50 text-amber-700 ring-amber-200',
  },
  READ_ONLY: { label: 'Lecture seule', color: 'bg-gray-100 text-gray-600 ring-gray-200' },
  UNSUPPORTED: { label: 'Segment non supporté', color: 'bg-red-50 text-red-700 ring-red-200' },
};

// V1 legacy confidence mapping (backward compat)
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
    total_expected_ttc,
    total_invoice_ttc,
    total_gap_eur,
    total_gap_pct,
    total_gap_status,
    status,
    // V1 legacy fields
    confidence,
    total_invoice_ht,
    tarif_version,
    segment,
  } = breakdown;

  // V2 engine: use reconstitution status; V1 fallback: use confidence badge
  const isV2 = !!breakdown.engine_version;
  const isFallback = !!breakdown.fallback_used;
  const statusBadge = isV2
    ? RECON_STATUS[status] || RECON_STATUS.PARTIAL
    : isFallback
      ? CONFIDENCE_BADGE.low
      : CONFIDENCE_BADGE[confidence] || CONFIDENCE_BADGE.low;

  // Compute bar widths — handle both V2 (expected_ht) and V1 (expected_eur)
  const totalExpected = components.reduce((s, c) => s + (c.expected_ht ?? c.expected_eur ?? 0), 0);

  return (
    <div className="space-y-4">
      {/* En-tête : totaux + statut reconstitution */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-xs font-semibold text-gray-500 uppercase">
            <Explain term="shadow_breakdown">
              {isV2 ? 'Reconstitution déterministe' : 'Décomposition shadow'}
            </Explain>
          </h4>
          <div className="flex items-baseline gap-3 mt-1">
            <span className="text-sm text-gray-600">
              Attendu HT :{' '}
              <span className="font-semibold text-gray-900">{fmt(total_expected_ht)} €</span>
            </span>
            {isV2 && total_expected_ttc > 0 && (
              <span className="text-sm text-gray-600">
                TTC :{' '}
                <span className="font-semibold text-gray-900">{fmt(total_expected_ttc)} €</span>
              </span>
            )}
            {(total_invoice_ttc > 0 || total_invoice_ht > 0) && (
              <span className="text-sm text-gray-600">
                Facturé :{' '}
                <span className="font-semibold text-gray-900">
                  {fmt(total_invoice_ttc || total_invoice_ht)} €
                </span>
              </span>
            )}
            {total_gap_eur != null && total_gap_eur !== 0 && (
              <span
                className={`text-sm font-bold ${total_gap_eur > 0 ? 'text-red-600' : 'text-green-600'}`}
              >
                {total_gap_eur > 0 ? '+' : ''}
                {fmt(total_gap_eur)} €
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
        <span
          className={`px-2 py-0.5 text-xs font-medium rounded-full ring-1 ${statusBadge.color}`}
        >
          {statusBadge.label}
        </span>
      </div>

      {/* Avertissement fallback V1 */}
      {isFallback && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
          <p className="text-xs font-medium text-orange-800">
            Calcul approximatif (moteur V1) — le moteur V2 n&apos;a pas pu traiter cette facture.
          </p>
        </div>
      )}

      {/* Warnings & données manquantes (V2) */}
      {isV2 && breakdown.missing_inputs?.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <p className="text-xs font-medium text-amber-800">Données manquantes :</p>
          <ul className="text-xs text-amber-700 mt-1 list-disc list-inside">
            {breakdown.missing_inputs.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Barre empilée */}
      <div className="w-full bg-gray-100 rounded-full h-3 flex overflow-hidden">
        {components.map((c) => {
          const val = c.expected_ht ?? c.expected_eur ?? 0;
          const pct = totalExpected > 0 ? (val / totalExpected) * 100 : 25;
          const gapStatus = c.gap_status || c.status || 'unknown';
          const colors = STATUS_COLORS[gapStatus] || STATUS_COLORS.ok;
          return (
            <div
              key={c.code || c.name}
              className={`${colors.bar} h-3 transition-all`}
              style={{ width: `${pct}%` }}
              title={`${c.label}: ${fmt(val)} € attendu`}
            />
          );
        })}
      </div>

      {/* Détail par composante */}
      <div className="space-y-2">
        {components.map((c) => {
          const gapStatus = c.gap_status || c.status || 'unknown';
          const colors = STATUS_COLORS[gapStatus] || STATUS_COLORS.unknown;
          const expectedVal = c.expected_ht ?? c.expected_eur;
          const invoiceVal = c.invoice_ht ?? c.invoice_eur;
          const hasInvoice = invoiceVal != null;
          const formula = c.formula || c.methodology;
          return (
            <div
              key={c.code || c.name}
              className={`rounded-lg p-3 ${colors.bg} border border-gray-100`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-800">{c.label}</span>
                <div className="flex items-center gap-3 text-sm">
                  <span className="text-gray-600">
                    Attendu : <span className="font-medium">{fmt(expectedVal)} €</span>
                  </span>
                  {hasInvoice ? (
                    <>
                      <span className="text-gray-600">
                        Facturé : <span className="font-medium">{fmt(invoiceVal)} €</span>
                      </span>
                      <span
                        className={`font-bold ${c.gap_eur > 0 ? 'text-red-600' : c.gap_eur < 0 ? 'text-green-600' : 'text-gray-500'}`}
                      >
                        {c.gap_eur > 0 ? '+' : ''}
                        {fmt(c.gap_eur)} €
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
              {/* Formule de calcul (mode Expert) */}
              {isExpert && formula && (
                <p className="text-xs text-gray-500 mt-1 font-mono">{formula}</p>
              )}
              {/* Sources des taux (mode Expert, V2 only) */}
              {isExpert && c.rate_sources?.length > 0 && (
                <div className="text-xs text-gray-400 mt-1">
                  {c.rate_sources.map((rs) => (
                    <span key={rs.code} className="mr-3">
                      {rs.code}: {rs.rate} {rs.unit} — {rs.source}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Hypothèses (V2, mode Expert) */}
      {isExpert && isV2 && breakdown.assumptions?.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
          <p className="text-xs font-medium text-blue-800">Hypothèses :</p>
          <ul className="text-xs text-blue-700 mt-1 list-disc list-inside">
            {breakdown.assumptions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings (V2, mode Expert) */}
      {isExpert && isV2 && breakdown.warnings?.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">
          <p className="text-xs font-medium text-orange-800">Avertissements :</p>
          <ul className="text-xs text-orange-700 mt-1 list-disc list-inside">
            {breakdown.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Source tarifs */}
      {breakdown.tariff_source && (
        <div className="flex items-center gap-1.5 pt-2 border-t border-gray-100">
          <span className="text-[10px] text-gray-400">
            {breakdown.tariff_source === 'regulated_tariffs'
              ? 'Tarifs réglementés (base CRE versionnée)'
              : 'Estimation (constantes de secours)'}
          </span>
          {tarif_version && (
            <span className="text-[10px] text-gray-300">&middot; {tarif_version}</span>
          )}
        </div>
      )}

      {/* Meta (mode Expert) */}
      {isExpert && (
        <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 pt-2 border-t border-gray-100">
          {breakdown.engine_version && <span>Engine : {breakdown.engine_version}</span>}
          {breakdown.catalog_version && <span>Catalogue : {breakdown.catalog_version}</span>}
          {tarif_version && !breakdown.catalog_version && <span>Tarifs : {tarif_version}</span>}
          {segment && <span>Segment : {segment}</span>}
          {breakdown.tariff_option && <span>Option : {breakdown.tariff_option}</span>}
          {breakdown.energy_type && <span>Énergie : {breakdown.energy_type}</span>}
          {breakdown.days_in_period && <span>Période : {breakdown.days_in_period} jours</span>}
          {breakdown.subscribed_power_kva > 0 && (
            <span>Puissance : {breakdown.subscribed_power_kva} kVA</span>
          )}
        </div>
      )}
    </div>
  );
}
