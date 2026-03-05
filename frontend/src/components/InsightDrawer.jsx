/**
 * PROMEOS — InsightDrawer (V70)
 * Drawer "Comprendre l'écart" : breakdown facturé vs attendu + cause probable.
 * Props: { open, onClose, insightId }
 */
import { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Badge } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getInsightDetail } from '../services/api';
import { useExpertMode } from '../contexts/ExpertModeContext';

const TYPE_LABELS = {
  shadow_gap: 'Écart shadow billing',
  unit_price_high: 'Prix unitaire élevé',
  duplicate_invoice: 'Doublon facture',
  missing_period: 'Période manquante',
  period_too_long: 'Période longue',
  negative_kwh: 'kWh négatifs',
  zero_amount: 'Montant zéro',
  lines_sum_mismatch: 'Écart lignes/total',
  consumption_spike: 'Pic de consommation',
  price_drift: 'Dérive de prix',
  ttc_coherence: 'Cohérence TTC',
  contract_expiry: 'Contrat expiré',
  reseau_mismatch: 'Écart réseau / TURPE',
  taxes_mismatch: 'Écart taxes / accise',
};

const SEVERITY_LABELS = {
  critical: 'Critique',
  high: 'Élevé',
  medium: 'Moyen',
  low: 'Faible',
};

const SEVERITY_BADGE = {
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
};

function fmt(v) {
  if (v == null) return '—';
  return Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 });
}

const CAUSE_LABELS = {
  shadow_gap: (m) =>
    m.expected_ttc != null
      ? `L'écart entre le montant facturé (${fmt(m.actual_ttc)} €) et le shadow billing (${fmt(m.expected_ttc)} €) dépasse le seuil de ${m.threshold_pct || 10}%.`
      : `L'écart entre le montant facturé (${fmt(m.actual_total_eur)} €) et le shadow billing (${fmt(m.shadow_total_eur)} €) dépasse le seuil de ${m.threshold_pct || 10}%.`,
  unit_price_high: (m) =>
    `Le prix unitaire (${m.unit_price?.toFixed(4) || '?'} €/kWh) dépasse le seuil de ${m.threshold || 0.3} €/kWh pour ce type d'énergie.`,
  duplicate_invoice: () => `Cette facture est un doublon (même site, même période, même montant).`,
  missing_period: () =>
    `Aucune facture ne couvre cette période. Vérifiez l'import ou contactez le fournisseur.`,
  period_too_long: (m) =>
    `La période de facturation (${m.days || '?'} jours) est anormalement longue.`,
  negative_kwh: () =>
    `La consommation est négative — possible erreur de relevé ou inversion d'index.`,
  zero_amount: () =>
    `Le montant facturé est nul — vérifiez s'il s'agit d'un avoir ou d'une erreur.`,
  lines_sum_mismatch: (m) =>
    `La somme des lignes (${fmt(m.lines_total)} €) ne correspond pas au total facturé (${fmt(m.invoice_total)} €).`,
  consumption_spike: (m) =>
    `La consommation (${m.kwh?.toLocaleString() || '?'} kWh) dépasse ${m.threshold_ratio || 2}× la moyenne des 6 derniers mois.`,
  price_drift: (m) =>
    `Le prix unitaire a dérivé de ${m.drift_pct?.toFixed(1) || '?'}% par rapport à la période précédente.`,
  reseau_mismatch: (m) =>
    `L'écart réseau/TURPE (${fmt(m.delta_reseau)} €) dépasse le seuil de 10%.`,
  taxes_mismatch: (m) => `L'écart taxes/accise (${fmt(m.delta_taxes)} €) dépasse le seuil de 5%.`,
};

function getBreakdownRows(energyType) {
  const et = (energyType || '').toUpperCase();
  const taxLabel =
    et === 'ELEC'
      ? 'Accise électricité'
      : et === 'GAZ'
        ? 'Accise gaz (TICGN)'
        : 'Taxes & contributions';
  return [
    { key: 'fourniture', label: 'Énergie (fourniture)' },
    { key: 'reseau', label: 'Réseau (TURPE)' },
    { key: 'taxes', label: taxLabel },
    { key: 'tva', label: 'TVA' },
  ];
}

export default function InsightDrawer({ open, onClose, insightId }) {
  const { isExpert } = useExpertMode();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !insightId) {
      setDetail(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    getInsightDetail(insightId)
      .then((data) => {
        setDetail(data);
        setError(null);
      })
      .catch((err) => {
        setDetail(null);
        setError({
          method: 'GET',
          status: err?.response?.status,
          message: err?.response?.data?.detail || err?.message || 'Erreur inconnue',
          endpoint: `/billing/insights/${insightId}`,
        });
      })
      .finally(() => setLoading(false));
  }, [open, insightId]);

  const m = detail?.metrics || {};
  const hasBreakdown = m.expected_ttc != null || m.expected_fourniture_ht != null;
  const causeGen = CAUSE_LABELS[detail?.type];
  const cause = causeGen ? causeGen(m) : detail?.message || '';

  return (
    <Drawer open={open} onClose={onClose} title="Comprendre l'écart" wide>
      {loading ? (
        <div className="space-y-3">
          <SkeletonCard lines={2} />
          <SkeletonCard lines={4} />
        </div>
      ) : !detail ? (
        <div className="text-center py-8">
          <p className="text-sm text-gray-500">
            {error
              ? `Impossible de charger le détail (${error.status || 'réseau'}). Veuillez réessayer ou contacter le support.`
              : 'Détail non disponible.'}
          </p>
          {isExpert && error && (
            <div className="mt-4 bg-red-50 rounded-lg p-3 text-left">
              <p className="text-xs font-semibold text-red-600">Debug</p>
              <p className="text-xs text-red-500 mt-1">Method : {error.method}</p>
              <p className="text-xs text-red-500">Endpoint : {error.endpoint}</p>
              <p className="text-xs text-red-500">Status : {error.status || 'N/A'}</p>
              <p className="text-xs text-red-500">Message : {error.message}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* En-tête */}
          <div className="flex items-center gap-3">
            <AlertTriangle
              size={20}
              className={
                detail.severity === 'critical'
                  ? 'text-red-600'
                  : detail.severity === 'high'
                    ? 'text-orange-600'
                    : 'text-amber-500'
              }
            />
            <div>
              <h3 className="text-sm font-semibold text-gray-900">
                {TYPE_LABELS[detail.type] || detail.type}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge status={SEVERITY_BADGE[detail.severity] || 'neutral'}>
                  {SEVERITY_LABELS[detail.severity] || detail.severity}
                </Badge>
                {detail.estimated_loss_eur > 0 && (
                  <span className="text-sm font-bold text-red-600">
                    {detail.estimated_loss_eur.toLocaleString()} €
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Message */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-700">{detail.message}</p>
          </div>

          {/* Cause probable */}
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Cause probable</h4>
            <p className="text-sm text-gray-800">{cause}</p>
          </div>

          {/* Confiance & Hypothèses */}
          {m.confidence && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Confiance</h4>
              <div className="flex items-center gap-2">
                <Badge
                  status={
                    m.confidence === 'high' ? 'ok' : m.confidence === 'medium' ? 'info' : 'warn'
                  }
                >
                  {m.confidence === 'high'
                    ? 'Élevée'
                    : m.confidence === 'medium'
                      ? 'Moyenne'
                      : 'Faible'}
                </Badge>
              </div>
              {m.assumptions?.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {m.assumptions.map((a, i) => (
                    <li key={i} className="text-xs text-gray-600 flex items-center gap-1.5">
                      <span className="w-1 h-1 rounded-full bg-gray-400 shrink-0" />
                      {a}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Tableau Facturé vs Attendu */}
          {hasBreakdown && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Facturé vs Attendu
              </h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 text-xs font-medium text-gray-500">Composante</th>
                    <th className="text-right py-2 text-xs font-medium text-gray-500">Facturé</th>
                    <th className="text-right py-2 text-xs font-medium text-gray-500">Attendu</th>
                    <th className="text-right py-2 text-xs font-medium text-gray-500">Écart</th>
                  </tr>
                </thead>
                <tbody>
                  {getBreakdownRows(m.energy_type).map((row) => {
                    const actual = m[`actual_${row.key}_ht`] ?? m[`actual_${row.key}`];
                    const expected = m[`expected_${row.key}_ht`] ?? m[`expected_${row.key}`];
                    const delta = m[`delta_${row.key}`];
                    // TVA fallback: show "non disponible" when TTC exists but TVA is null
                    if (actual == null && expected == null) {
                      if (row.key === 'tva' && m.actual_ttc != null) {
                        return (
                          <tr key={row.key} className="border-b border-gray-100">
                            <td className="py-2 text-gray-700">{row.label}</td>
                            <td colSpan={3} className="py-2 text-right text-xs text-gray-400 italic">
                              TVA non disponible
                            </td>
                          </tr>
                        );
                      }
                      return null;
                    }
                    return (
                      <tr key={row.key} className="border-b border-gray-100">
                        <td className="py-2 text-gray-700">{row.label}</td>
                        <td className="py-2 text-right font-medium">{fmt(actual)} €</td>
                        <td className="py-2 text-right">{fmt(expected)} €</td>
                        <td
                          className={`py-2 text-right font-medium ${delta > 0 ? 'text-red-600' : delta < 0 ? 'text-green-600' : 'text-gray-500'}`}
                        >
                          {delta != null ? `${delta > 0 ? '+' : ''}${fmt(delta)} €` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                  {/* Total */}
                  <tr className="border-t-2 border-gray-300 font-semibold">
                    <td className="py-2 text-gray-900">Total TTC</td>
                    <td className="py-2 text-right">{fmt(m.actual_ttc)} €</td>
                    <td className="py-2 text-right">{fmt(m.expected_ttc)} €</td>
                    <td
                      className={`py-2 text-right ${m.delta_ttc > 0 ? 'text-red-600' : m.delta_ttc < 0 ? 'text-green-600' : 'text-gray-500'}`}
                    >
                      {m.delta_ttc != null
                        ? `${m.delta_ttc > 0 ? '+' : ''}${fmt(m.delta_ttc)} €`
                        : '—'}
                      {m.delta_pct != null && (
                        <span className="ml-1 text-xs font-normal">
                          ({m.delta_pct > 0 ? '+' : ''}
                          {m.delta_pct.toFixed(1)}%)
                        </span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Écart détecté (types sans breakdown V2) */}
          {!hasBreakdown && detail.estimated_loss_eur > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Écart détecté</h4>
              <p className="text-lg font-bold text-red-600">{fmt(detail.estimated_loss_eur)} €</p>
            </div>
          )}

          {/* Mode Expert */}
          {isExpert && (
            <div className="bg-slate-50 rounded-lg p-3 text-xs text-gray-500 space-y-1">
              <p className="font-semibold text-gray-600">Expert</p>
              {m.rule_id && <p>Règle : {m.rule_id}</p>}
              {m.method && <p>Méthode : {m.method}</p>}
              {m.energy_type && <p>Énergie : {m.energy_type}</p>}
              {m.price_ref != null && <p>Prix ref : {m.price_ref} €/kWh</p>}
              {m.kwh != null && <p>kWh : {m.kwh.toLocaleString()}</p>}
              {m.threshold_pct != null && <p>Seuil : {m.threshold_pct}%</p>}
              {detail.recommended_actions?.length > 0 && (
                <div>
                  <p className="font-semibold text-gray-600 mt-2">Actions recommandées</p>
                  <ul className="list-disc list-inside mt-1">
                    {detail.recommended_actions.map((a, i) => (
                      <li key={i}>{typeof a === 'string' ? a : a.label || JSON.stringify(a)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}
