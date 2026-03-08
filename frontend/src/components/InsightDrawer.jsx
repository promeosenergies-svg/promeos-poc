/**
 * PROMEOS — InsightDrawer (V70)
 * Drawer "Comprendre l'écart" : breakdown facturé vs attendu + cause probable.
 * Props: { open, onClose, insightId }
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, ChevronDown } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Badge, Explain } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getInsightDetail, getInvoiceShadowBreakdown } from '../services/api';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useScope } from '../contexts/ScopeContext';
import ShadowBreakdownCard from './billing/ShadowBreakdownCard';
import { fmtNum } from '../utils/format';

const TYPE_LABELS = {
  shadow_gap: (
    <>
      Écart <Explain term="shadow_billing">shadow billing</Explain>
    </>
  ),
  unit_price_high: 'Prix unitaire élevé',
  duplicate_invoice: 'Doublon facture',
  missing_period: 'Période manquante',
  period_too_long: 'Période longue',
  negative_kwh: (
    <>
      <Explain term="kwh">kWh</Explain> négatifs
    </>
  ),
  zero_amount: 'Montant zéro',
  lines_sum_mismatch: 'Écart lignes/total',
  consumption_spike: 'Pic de consommation',
  price_drift: 'Dérive de prix',
  ttc_coherence: (
    <>
      Cohérence <Explain term="ttc">TTC</Explain>
    </>
  ),
  contract_expiry: 'Contrat expiré',
  reseau_mismatch: (
    <>
      Écart réseau / <Explain term="turpe">TURPE</Explain>
    </>
  ),
  taxes_mismatch: (
    <>
      Écart taxes / <Explain term="accise">accise</Explain>
    </>
  ),
  reconciliation_mismatch: (
    <>
      <Explain term="reconciliation_auto">Écart compteur / facture</Explain>
    </>
  ),
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
  return fmtNum(v, 2);
}

const CAUSE_LABELS = {
  shadow_gap: (m) =>
    m.expected_ttc != null ? (
      <>
        L'écart entre le montant facturé ({fmt(m.actual_ttc)} €) et le{' '}
        <Explain term="shadow_billing">shadow billing</Explain> ({fmt(m.expected_ttc)} €) dépasse le
        seuil de {m.threshold_pct || 10}%.
      </>
    ) : (
      <>
        L'écart entre le montant facturé ({fmt(m.actual_total_eur)} €) et le{' '}
        <Explain term="shadow_billing">shadow billing</Explain> ({fmt(m.shadow_total_eur)} €)
        dépasse le seuil de {m.threshold_pct || 10}%.
      </>
    ),
  unit_price_high: (m) => (
    <>
      Le prix unitaire ({fmtNum(m.unit_price, 4) === '—' ? '?' : fmtNum(m.unit_price, 4)}{' '}
      <Explain term="eur_kwh">€/kWh</Explain>) dépasse le seuil de {m.threshold || 0.3}{' '}
      <Explain term="eur_kwh">€/kWh</Explain> pour ce type d'énergie.
    </>
  ),
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
  consumption_spike: (m) => (
    <>
      La consommation ({fmtNum(m.kwh, 0) === '—' ? '?' : fmtNum(m.kwh, 0)}{' '}
      <Explain term="kwh">kWh</Explain>) dépasse {m.threshold_ratio || 2}× la moyenne des 6 derniers
      mois.
    </>
  ),
  price_drift: (m) =>
    `Le prix unitaire a dérivé de ${fmtNum(m.drift_pct, 1) === '—' ? '?' : fmtNum(m.drift_pct, 1)}% par rapport à la période précédente.`,
  reseau_mismatch: (m) => (
    <>
      L'écart réseau/<Explain term="turpe">TURPE</Explain> ({fmt(m.delta_reseau)} €) dépasse le
      seuil de 10%.
    </>
  ),
  taxes_mismatch: (m) => (
    <>
      L'écart taxes/<Explain term="accise">accise</Explain> ({fmt(m.delta_taxes)} €) dépasse le
      seuil de 5%.
    </>
  ),
  reconciliation_mismatch: () => (
    <>
      Écart significatif entre la{' '}
      <Explain term="reconciliation_conso">consommation compteur</Explain> et la consommation
      facturée. Vérifiez les relevés ou la facture.
    </>
  ),
};

function getBreakdownRows(energyType) {
  const et = (energyType || '').toUpperCase();
  const taxLabel =
    et === 'ELEC' ? (
      <>
        <Explain term="accise">Accise</Explain> électricité
      </>
    ) : et === 'GAZ' ? (
      <>
        <Explain term="accise">Accise</Explain> gaz (TICGN)
      </>
    ) : (
      'Taxes & contributions'
    );
  return [
    { key: 'fourniture', label: 'Énergie (fourniture)' },
    {
      key: 'reseau',
      label: (
        <>
          Réseau (<Explain term="turpe">TURPE</Explain>)
        </>
      ),
    },
    { key: 'taxes', label: taxLabel },
    { key: 'tva', label: <Explain term="tva">TVA</Explain> },
  ];
}

export default function InsightDrawer({ open, onClose, insightId }) {
  const { isExpert } = useExpertMode();
  const { org, portefeuille, orgSites, selectedSiteId } = useScope();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [breakdown, setBreakdown] = useState(null);

  useEffect(() => {
    if (!open || !insightId) {
      setDetail(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    setBreakdown(null);
    getInsightDetail(insightId)
      .then((data) => {
        setDetail(data);
        setError(null);
        if (data?.invoice_id) {
          getInvoiceShadowBreakdown(data.invoice_id)
            .then(setBreakdown)
            .catch(() => setBreakdown(null));
        }
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
        <div className="space-y-4">
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
                    {fmtNum(detail.estimated_loss_eur, 0)} €
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Scope context */}
          <div className="flex items-center gap-2 px-3 py-2 bg-blue-50/60 rounded-lg border border-blue-100 text-xs text-blue-700">
            <span className="font-medium">{org?.nom || 'Organisation'}</span>
            {portefeuille && (
              <>
                <span className="text-blue-300">/</span>
                <span>{portefeuille.nom}</span>
              </>
            )}
            {selectedSiteId && orgSites?.length > 0 && (
              <>
                <span className="text-blue-300">/</span>
                <span>
                  {orgSites.find((s) => String(s.id) === String(selectedSiteId))?.nom ||
                    `Site ${selectedSiteId}`}
                </span>
              </>
            )}
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

          {/* Confiance — inline badge (détails dans section diagnostics ci-dessous) */}
          {m.confidence && !m.diagnostics && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase">
                <Explain term="confiance">Confiance</Explain> :
              </span>
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
                            <td
                              colSpan={3}
                              className="py-2 text-right text-xs text-gray-400 italic"
                            >
                              <Explain term="tva">TVA</Explain> non disponible
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
                    <td className="py-2 text-gray-900">
                      Total <Explain term="ttc">TTC</Explain>
                    </td>
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
                          {fmtNum(m.delta_pct, 1)}%)
                        </span>
                      )}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {/* Top contributeurs à l'écart */}
          {m.top_contributors?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Principaux contributeurs à l'écart
              </h4>
              <div className="space-y-2">
                {m.top_contributors.map((c) => {
                  const pct = Math.abs(c.pct_of_total || 0);
                  const isPositive = c.delta_eur > 0;
                  return (
                    <div key={c.code} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-800">{c.label}</span>
                        <span
                          className={`text-sm font-bold ${isPositive ? 'text-red-600' : 'text-green-600'}`}
                        >
                          {isPositive ? '+' : ''}
                          {fmt(c.delta_eur)} €
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5 mb-1">
                        <div
                          className={`h-1.5 rounded-full ${isPositive ? 'bg-red-400' : 'bg-green-400'}`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500">
                        {c.explanation_fr} ({Math.abs(c.pct_of_total)}% de l'écart)
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Données & hypothèses — collapsible */}
          {m.diagnostics && (
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer select-none">
                <ChevronDown
                  size={14}
                  className="text-gray-400 transition-transform group-open:rotate-180"
                />
                <h4 className="text-xs font-semibold text-gray-500 uppercase">
                  Données &amp; hypothèses
                </h4>
                <Badge
                  status={
                    m.diagnostics.confidence === 'high'
                      ? 'ok'
                      : m.diagnostics.confidence === 'medium'
                        ? 'info'
                        : 'warn'
                  }
                >
                  <Explain term="confiance">Confiance</Explain> :{' '}
                  {m.diagnostics.confidence === 'high'
                    ? 'Élevée'
                    : m.diagnostics.confidence === 'medium'
                      ? 'Moyenne'
                      : 'Basse'}
                </Badge>
              </summary>
              <div className="mt-2 space-y-2 pl-5">
                {m.diagnostics.assumptions?.length > 0 && (
                  <ul className="space-y-1">
                    {m.diagnostics.assumptions.map((a, i) => (
                      <li key={i} className="text-xs text-gray-600 flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-gray-400 shrink-0" />
                        {a}
                      </li>
                    ))}
                  </ul>
                )}
                {m.diagnostics.missing_fields?.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-2">
                    <p className="text-xs font-semibold text-amber-700 mb-1">Données manquantes</p>
                    <ul className="space-y-0.5">
                      {m.diagnostics.missing_fields.map((f, i) => (
                        <li key={i} className="text-xs text-amber-600 flex items-center gap-1.5">
                          <AlertTriangle size={10} className="shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          )}

          {/* Shadow Breakdown par composante (Step 28) */}
          {breakdown && <ShadowBreakdownCard breakdown={breakdown} />}

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
              {m.price_ref != null && (
                <p>
                  Prix ref : {m.price_ref} <Explain term="eur_kwh">€/kWh</Explain>
                </p>
              )}
              {m.kwh != null && (
                <p>
                  <Explain term="kwh">kWh</Explain> : {fmtNum(m.kwh, 0)}
                </p>
              )}
              {m.threshold_pct != null && <p>Seuil : {m.threshold_pct}%</p>}
              {m.price_source && <p>Source prix : {m.price_source}</p>}
              {m.catalog_trace?.length > 0 && (
                <div className="mt-2">
                  <p className="font-semibold text-gray-600">
                    Catalogue v{m.catalog_trace[0]?.catalog_version || '?'}
                  </p>
                  {m.catalog_trace.map((t, i) => (
                    <p key={i}>
                      {t.code} : {t.used_rate} {t.unit || ''} ({t.source || '?'},{' '}
                      {t.valid_from || '?'})
                    </p>
                  ))}
                </div>
              )}
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
