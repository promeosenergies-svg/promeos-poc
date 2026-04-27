/**
 * PROMEOS — InsightDrawer (V111)
 * Drawer "Comprendre l'écart" : breakdown facturé vs attendu + cause probable.
 * V111 : InvoiceIdentCard, ReconstitutionBanner, hypothèses, CTAs, debug technique collapsible.
 * Props: { open, onClose, insightId }
 */
import { useState, useEffect } from 'react';
import { AlertTriangle, ChevronDown, FileText, Info } from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Badge, Explain } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import {
  getInsightDetail,
  getInvoiceShadowBreakdown,
  createActionFromBillingInsight,
} from '../services/api';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { useScope } from '../contexts/ScopeContext';
import ShadowBreakdownCard from './billing/ShadowBreakdownCard';
import { fmtNum } from '../utils/format';

/* ── helpers ─────────────────────────────────────────── */

/** Convertit "YYYY-MM-DD" → "DD/MM/YYYY" */
function fmtDate(d) {
  if (!d || typeof d !== 'string') return '—';
  const parts = d.split('-');
  if (parts.length !== 3) return d;
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function fmt(v) {
  return fmtNum(v, 2);
}

/* ── maps ────────────────────────────────────────────── */

const CONFIDENCE_STATUS_MAP = {
  elevee: 'ok',
  moyenne: 'info',
  faible: 'warn',
  tres_faible: 'crit',
  high: 'ok',
  medium: 'info',
  low: 'warn',
};

const _RECON_STATUS_COLOR = {
  complete: 'emerald',
  partial: 'amber',
  minimal: 'red',
};

// Sprint 2 Vague A ét2 — δ-2 récit Bill-Intel (doctrine v2 §5 + ADR-004).
// Aligné sur TYPE_LABELS de pages/BillIntelPage.jsx pour cohérence cross-vue.
// TYPE_LABELS_TEXT : version plain-string pour contextes non-JSX (titres
// d'actions générées). TYPE_LABELS : version JSX pour rendu enrichi avec
// <Explain> pédagogique inline.
const TYPE_LABELS_TEXT = {
  shadow_gap: 'Cette facture coûte plus que la facturation théorique',
  unit_price_high: 'Le prix au kWh dépasse vos repères',
  duplicate_invoice: 'Cette facture semble facturée deux fois',
  missing_period: "Une période de facturation n'a pas été couverte",
  period_too_long: 'Cette période dépasse la durée habituelle',
  negative_kwh: 'Une consommation négative en kWh est apparue',
  zero_amount: 'Le montant facturé est nul',
  lines_sum_mismatch: 'Le total ne se reconstitue pas à partir des lignes',
  consumption_spike: 'Pic de consommation inhabituel détecté',
  price_drift: 'Le prix unitaire dérive depuis plusieurs mois',
  ttc_coherence: 'Le total TTC ne se reconstitue pas',
  contract_expiry: 'Votre contrat est arrivé à échéance',
  reseau_mismatch: "L'acheminement réseau dépasse le tarif TURPE attendu",
  taxes_mismatch: "Les taxes dépassent l'accise et la CTA en vigueur",
  reconciliation_mismatch: 'Écart compteur / facture détecté',
};

const TYPE_LABELS = {
  shadow_gap: (
    <>
      Cette facture coûte plus que la <Explain term="shadow_billing">facturation théorique</Explain>
    </>
  ),
  unit_price_high: (
    <>
      Le prix au <Explain term="kwh">kWh</Explain> dépasse vos repères
    </>
  ),
  duplicate_invoice: TYPE_LABELS_TEXT.duplicate_invoice,
  missing_period: TYPE_LABELS_TEXT.missing_period,
  period_too_long: TYPE_LABELS_TEXT.period_too_long,
  negative_kwh: (
    <>
      Une consommation négative en <Explain term="kwh">kWh</Explain> est apparue
    </>
  ),
  zero_amount: TYPE_LABELS_TEXT.zero_amount,
  lines_sum_mismatch: TYPE_LABELS_TEXT.lines_sum_mismatch,
  consumption_spike: TYPE_LABELS_TEXT.consumption_spike,
  price_drift: TYPE_LABELS_TEXT.price_drift,
  ttc_coherence: (
    <>
      Le total <Explain term="ttc">TTC</Explain> ne se reconstitue pas
    </>
  ),
  contract_expiry: TYPE_LABELS_TEXT.contract_expiry,
  reseau_mismatch: (
    <>
      L'acheminement réseau dépasse le tarif <Explain term="turpe">TURPE</Explain> attendu
    </>
  ),
  taxes_mismatch: (
    <>
      Les taxes dépassent l'<Explain term="accise">accise</Explain> et la{' '}
      <Explain term="cta">CTA</Explain> en vigueur
    </>
  ),
  reconciliation_mismatch: (
    <>
      <Explain term="reconciliation_auto">Écart compteur / facture</Explain> détecté
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

const CAUSE_LABELS = {
  shadow_gap: (m) =>
    m.expected_ttc != null ? (
      <>
        L&apos;écart entre le montant facturé ({fmt(m.actual_ttc)} €) et le{' '}
        <Explain term="shadow_billing">facturation théorique</Explain> ({fmt(m.expected_ttc)} €)
        dépasse le seuil de {m.threshold_pct || 10}%.
      </>
    ) : (
      <>
        L&apos;écart entre le montant facturé ({fmt(m.actual_total_eur)} €) et le{' '}
        <Explain term="shadow_billing">facturation théorique</Explain> ({fmt(m.shadow_total_eur)} €)
        dépasse le seuil de {m.threshold_pct || 10}%.
      </>
    ),
  unit_price_high: (m) => (
    <>
      Le prix unitaire ({fmtNum(m.unit_price, 4) === '—' ? '?' : fmtNum(m.unit_price, 4)}{' '}
      <Explain term="eur_kwh">€/kWh</Explain>) dépasse le seuil de {m.threshold || 0.3}{' '}
      <Explain term="eur_kwh">€/kWh</Explain> pour ce type d&apos;énergie.
    </>
  ),
  duplicate_invoice: () => `Cette facture est un doublon (même site, même période, même montant).`,
  missing_period: () =>
    `Aucune facture ne couvre cette période. Vérifiez l&apos;import ou contactez le fournisseur.`,
  period_too_long: (m) =>
    `La période de facturation (${m.days || '?'} jours) est anormalement longue.`,
  negative_kwh: () =>
    `La consommation est négative — possible erreur de relevé ou inversion d&apos;index.`,
  zero_amount: () =>
    `Le montant facturé est nul — vérifiez s&apos;il s&apos;agit d&apos;un avoir ou d&apos;une erreur.`,
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
      L&apos;écart réseau/<Explain term="turpe">TURPE</Explain> ({fmt(m.delta_reseau)} €) dépasse le
      seuil de 10%.
    </>
  ),
  taxes_mismatch: (m) => (
    <>
      L&apos;écart taxes/<Explain term="accise">accise</Explain> ({fmt(m.delta_taxes)} €) dépasse le
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

/* ── InvoiceIdentCard ────────────────────────────────── */

function InvoiceIdentCard({ detail, metrics }) {
  const inv = detail?.invoice || {};
  const m = metrics || {};
  const numero = inv.numero || inv.invoice_number || m.invoice_number;
  const period_start = inv.period_start || m.period_start;
  const period_end = inv.period_end || m.period_end;
  const prm = inv.prm || m.prm;
  const kva = inv.kva || m.kva || m.puissance_souscrite;
  const segment = inv.segment || m.segment;
  const fournisseur = inv.fournisseur || inv.supplier || m.fournisseur || m.supplier;
  const kwh = m.kwh ?? m.conso_kwh ?? inv.kwh;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <FileText size={14} className="text-gray-400" />
        <span className="text-xs font-semibold text-gray-500 uppercase">Facture</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <span className="text-gray-500">N° facture</span>
        <span className="font-medium text-gray-800">
          {numero || <span className="italic text-gray-400">N° non renseigné</span>}
        </span>

        {(period_start || period_end) && (
          <>
            <span className="text-gray-500">Période</span>
            <span className="text-gray-800">
              {fmtDate(period_start)} → {fmtDate(period_end)}
            </span>
          </>
        )}

        {prm && (
          <>
            <span className="text-gray-500">PRM</span>
            <span className="text-gray-800 font-mono text-xs">{prm}</span>
          </>
        )}

        {kva != null && (
          <>
            <span className="text-gray-500">Puissance</span>
            <span className="text-gray-800">{kva} kVA</span>
          </>
        )}

        {segment && (
          <>
            <span className="text-gray-500">Segment</span>
            <span className="text-gray-800">{segment}</span>
          </>
        )}

        {fournisseur && (
          <>
            <span className="text-gray-500">Fournisseur</span>
            <span className="text-gray-800">{fournisseur}</span>
          </>
        )}

        {kwh != null && (
          <>
            <span className="text-gray-500">Consommation</span>
            <span className="text-gray-800">{fmtNum(kwh, 0)} kWh</span>
          </>
        )}
      </div>
    </div>
  );
}

/* ── ReconstitutionBanner ────────────────────────────── */

function ReconstitutionBanner({ breakdown }) {
  if (!breakdown) return null;
  const label = breakdown.reconstitution_label || breakdown.reconstitution_status;
  const confidence = breakdown.confidence;
  const confidence_label = breakdown.confidence_label;
  const confidence_rationale = breakdown.confidence_rationale;
  if (!label && !confidence_label) return null;

  const reconColor =
    breakdown.reconstitution_status === 'complete'
      ? 'emerald'
      : breakdown.reconstitution_status === 'minimal'
        ? 'red'
        : 'amber';
  const confStatus = CONFIDENCE_STATUS_MAP[confidence] || 'neutral';
  const confDisplay = confidence_label || confidence || '—';

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 bg-${reconColor}-50 border border-${reconColor}-200 rounded-lg`}
    >
      <Info size={14} className={`text-${reconColor}-500`} />
      <span className="text-xs text-gray-700">{label || 'Reconstitution'}</span>
      <Badge status={confStatus} title={confidence_rationale || `Confiance : ${confDisplay}`}>
        {confDisplay}
      </Badge>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────── */

export default function InsightDrawer({ open, onClose, insightId }) {
  const { isExpert } = useExpertMode();
  const { org, portefeuille, orgSites, selectedSiteId } = useScope();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [breakdown, setBreakdown] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionDone, setActionDone] = useState(false);

  useEffect(() => {
    if (!open || !insightId) {
      setDetail(null);
      setError(null);
      setActionDone(false);
      return;
    }
    setLoading(true);
    setError(null);
    setBreakdown(null);
    setActionDone(false);
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

  const handleCreateAction = async () => {
    if (!detail || actionLoading || actionDone) return;
    setActionLoading(true);
    try {
      const title = `Action insight : ${TYPE_LABELS_TEXT[detail.type] || detail.type}`;
      await createActionFromBillingInsight(insightId, title, detail.site_id);
      setActionDone(true);
    } catch {
      // silently fail — user can retry
    } finally {
      setActionLoading(false);
    }
  };

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

          {/* Invoice Ident Card */}
          <InvoiceIdentCard detail={detail} metrics={m} />

          {/* Message */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-700">{detail.message}</p>
          </div>

          {/* Cause probable */}
          <div>
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Cause probable</h4>
            <p className="text-sm text-gray-800">{cause}</p>
          </div>

          {/* Reconstitution Banner */}
          <ReconstitutionBanner breakdown={breakdown} />

          {/* Confiance — inline badge (détails dans section diagnostics ci-dessous) */}
          {m.confidence && !m.diagnostics && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-gray-500 uppercase">
                <Explain term="confiance">Confiance</Explain> :
              </span>
              <Badge status={CONFIDENCE_STATUS_MAP[m.confidence] || 'neutral'}>
                {m.confidence === 'high' || m.confidence === 'elevee'
                  ? 'Élevée'
                  : m.confidence === 'medium' || m.confidence === 'moyenne'
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
                              TVA non détaillée sur cette facture
                            </td>
                          </tr>
                        );
                      }
                      return null;
                    }
                    return (
                      <tr key={row.key} className="border-b border-gray-100">
                        <td className="py-2 text-gray-700">{row.label}</td>
                        <td className="py-2 text-right font-medium">
                          {actual != null ? `${fmt(actual)} €` : '—'}
                        </td>
                        <td className="py-2 text-right">
                          {expected != null ? (
                            `${fmt(expected)} €`
                          ) : (
                            <span className="text-xs text-gray-400 italic">Non reconstituable</span>
                          )}
                        </td>
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
                    <td className="py-2 text-right">
                      {m.actual_ttc != null ? `${fmt(m.actual_ttc)} €` : '—'}
                    </td>
                    <td className="py-2 text-right">
                      {m.expected_ttc != null ? (
                        `${fmt(m.expected_ttc)} €`
                      ) : (
                        <span className="text-xs text-gray-400 italic">Non reconstituable</span>
                      )}
                    </td>
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
              <p className="text-xs text-gray-400 mt-1 italic">
                — = non disponible / non reconstituable
              </p>
            </div>
          )}

          {/* Hypothèses du breakdown */}
          {breakdown?.hypotheses?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Hypothèses de reconstitution
              </h4>
              <ul className="space-y-1">
                {breakdown.hypotheses.map((h, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-gray-400 shrink-0 mt-1.5" />
                    {typeof h === 'string' ? h : h.label || h.text || JSON.stringify(h)}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Top contributeurs à l'écart */}
          {m.top_contributors?.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                Principaux contributeurs à l&apos;écart
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
                        {c.explanation_fr} ({Math.abs(c.pct_of_total)}% de l&apos;écart)
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
                <Badge status={CONFIDENCE_STATUS_MAP[m.diagnostics.confidence] || 'neutral'}>
                  <Explain term="confiance">Confiance</Explain> :{' '}
                  {m.diagnostics.confidence === 'high' || m.diagnostics.confidence === 'elevee'
                    ? 'Élevée'
                    : m.diagnostics.confidence === 'medium' ||
                        m.diagnostics.confidence === 'moyenne'
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

          {/* CTAs — Actions */}
          <div className="space-y-2 pt-2 border-t border-gray-100">
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Actions</h4>
            <button
              type="button"
              disabled={actionLoading || actionDone}
              onClick={handleCreateAction}
              className={`w-full text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                actionDone
                  ? 'bg-green-50 text-green-700 border border-green-200 cursor-default'
                  : 'bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50'
              }`}
            >
              {actionDone ? '✓ Action créée' : actionLoading ? 'Création…' : 'Créer une action'}
            </button>
            <button
              type="button"
              className="w-full text-sm font-medium px-4 py-2 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Contester cette facture
            </button>
            <button
              type="button"
              className="w-full text-sm font-medium px-4 py-2 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Compléter les données
            </button>
          </div>

          {/* Debug technique — collapsible (ex Mode Expert) */}
          {isExpert && (
            <details className="group">
              <summary className="flex items-center gap-2 cursor-pointer select-none">
                <ChevronDown
                  size={14}
                  className="text-gray-400 transition-transform group-open:rotate-180"
                />
                <h4 className="text-xs font-semibold text-gray-500 uppercase">Debug technique</h4>
              </summary>
              <div className="mt-2 bg-slate-50 rounded-lg p-3 text-xs text-gray-500 space-y-1">
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
                {/* Breakdown expert fields */}
                {breakdown?.expert && (
                  <div className="mt-2 border-t border-gray-200 pt-2">
                    <p className="font-semibold text-gray-600">Breakdown expert</p>
                    {Object.entries(breakdown.expert).map(([k, v]) => (
                      <p key={k}>
                        {k} : {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </details>
          )}
        </div>
      )}
    </Drawer>
  );
}
