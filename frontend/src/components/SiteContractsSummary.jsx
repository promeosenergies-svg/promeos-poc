/**
 * PROMEOS — SiteContractsSummary (V96 + P0-C 2026-05-23)
 *
 * Affiche les contrats énergie d'un site avec leur couverture sur les points
 * de livraison.
 *
 * P0-C — règle terminologie :
 *  - libellé principal : "Point de livraison"
 *  - détail technique : électricité = "PRM/PDL XXXXX", gaz = "PCE XXXXX"
 *
 * P0-C — règle produit : un site n'est pas prêt facture/achat/audit si ses
 * points de livraison actifs ne sont pas couverts par un contrat actif.
 * La couverture est calculée par `contract_coverage_service` et exposée via
 * `GET /api/patrimoine/sites/{id}/contract-coverage`.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText,
  AlertTriangle,
  BadgeEuro,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import { Card, CardBody, Badge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getPatrimoineContracts } from '../services/api';
import { getSiteContractCoverage } from '../services/api/conformite';

const IDX_BADGE = {
  fixe: 'info',
  indexe: 'warning',
  spot: 'error',
  hybride: 'success',
};
const STATUS_BADGE = {
  active: 'success',
  expiring: 'warning',
  expired: 'error',
};

// P0-C — mapping cardinal status couverture → badge UI + libellé FR
const COVERAGE_BADGE = {
  contrat_rattache: { tone: 'success', label: 'Tous les points sont couverts', icon: CheckCircle2 },
  contrat_partiel: { tone: 'warning', label: 'Couverture partielle', icon: AlertTriangle },
  contrat_manquant: { tone: 'error', label: 'Aucun contrat rattaché', icon: XCircle },
  contrat_expire: { tone: 'error', label: 'Contrat expiré', icon: Clock },
  contrat_incoherent: { tone: 'error', label: 'Incohérence énergie', icon: AlertTriangle },
};

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

// P0-C terminologie : libellé canonique d'un point de livraison
function deliveryPointLabel(dp) {
  if (dp.label_fr) return dp.label_fr; // backend fournit déjà le libellé canonique
  if (dp.energy_type === 'elec') return `Point de livraison électricité — PRM/PDL ${dp.code}`;
  if (dp.energy_type === 'gaz') return `Point de livraison gaz — PCE ${dp.code}`;
  return `Point de livraison — ${dp.code}`;
}

export default function SiteContractsSummary({ siteId, onAttachContract }) {
  const [contracts, setContracts] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    Promise.all([
      getPatrimoineContracts({ site_id: siteId }).then((d) => d.contracts || []),
      getSiteContractCoverage(siteId).catch(() => null),
    ])
      .then(([ctList, cov]) => {
        if (stale) return;
        setContracts(ctList);
        setCoverage(cov);
      })
      .catch(() => {
        if (!stale) {
          setContracts([]);
          setCoverage(null);
        }
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  if (loading) return <SkeletonCard />;

  // Index DP par id pour afficher le détail des points couverts par contrat
  const dpById = {};
  if (coverage) {
    for (const dp of coverage.delivery_points_active || []) dpById[dp.id] = dp;
  }

  if (contracts.length === 0 && coverage && coverage.delivery_points_active.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="Aucun contrat"
        text="Ajoutez un contrat énergie pour activer le suivi."
      />
    );
  }

  return (
    <div className="space-y-3" data-component="SiteContractsSummary">
      {coverage && <CoverageBanner coverage={coverage} onAttachContract={onAttachContract} />}

      <h4 className="text-sm font-semibold text-gray-700">Contrats énergie</h4>

      {contracts.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="Aucun contrat"
          text="Ajoutez un contrat énergie pour activer le suivi."
        />
      ) : (
        contracts.map((ct) => {
          const daysLeft = daysUntil(ct.end_date);
          const alertRenewal =
            ct.renewal_alert_days &&
            daysLeft !== null &&
            daysLeft > 0 &&
            daysLeft <= ct.renewal_alert_days;
          const coveredDps = (ct.delivery_point_ids || []).map((id) => dpById[id]).filter(Boolean);
          return (
            <Card
              key={ct.id}
              className={alertRenewal ? 'border-l-4 border-l-amber-400' : ''}
              data-contract-id={ct.id}
            >
              <CardBody>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-gray-900 text-sm">{ct.supplier_name}</span>
                    <span className="mx-2 text-gray-400">·</span>
                    <span className="text-xs text-gray-500 uppercase">{ct.energy_type}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {ct.offer_indexation && (
                      <Badge status={IDX_BADGE[ct.offer_indexation] || 'info'}>
                        {ct.offer_indexation}
                      </Badge>
                    )}
                    {ct.contract_status && (
                      <Badge status={STATUS_BADGE[ct.contract_status] || 'info'}>
                        {ct.contract_status}
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                  {ct.reference_fournisseur && (
                    <span>
                      Réf: <strong>{ct.reference_fournisseur}</strong>
                    </span>
                  )}
                  {ct.price_ref_eur_per_kwh != null && (
                    <span>
                      Prix ref: <strong>{ct.price_ref_eur_per_kwh} €/kWh</strong>
                    </span>
                  )}
                  {ct.start_date && (
                    <span>
                      {ct.start_date} → {ct.end_date || '...'}
                    </span>
                  )}
                  {daysLeft !== null && daysLeft > 0 && (
                    <span className={daysLeft <= 90 ? 'text-amber-600 font-medium' : ''}>
                      {daysLeft}j restants
                    </span>
                  )}
                  {ct.date_signature && <span>Signé le {ct.date_signature}</span>}
                </div>

                {/* P0-C — liste explicite des points de livraison couverts */}
                {coveredDps.length > 0 ? (
                  <div className="mt-3 border-t border-gray-100 pt-2">
                    <p className="text-xs font-semibold text-gray-600 mb-1">
                      Points de livraison couverts ({coveredDps.length})
                    </p>
                    <ul className="space-y-1">
                      {coveredDps.map((dp) => (
                        <li
                          key={dp.id}
                          className="text-xs text-gray-700"
                          data-delivery-point-id={dp.id}
                        >
                          • {deliveryPointLabel(dp)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  ct.delivery_points_count > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      {ct.delivery_points_count} point
                      {ct.delivery_points_count > 1 ? 's' : ''} de livraison rattaché
                      {ct.delivery_points_count > 1 ? 's' : ''}
                    </div>
                  )
                )}

                {alertRenewal && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                    <AlertTriangle size={12} />
                    <span>
                      Alerte renouvellement — {daysLeft}j avant échéance (seuil:{' '}
                      {ct.renewal_alert_days}j)
                    </span>
                  </div>
                )}
                <div className="mt-2 pt-2 border-t border-gray-100 flex items-center gap-3">
                  <Link
                    to={`/billing?site_id=${siteId}`}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    <BadgeEuro size={12} /> Factures
                  </Link>
                  <Link
                    to={`/bill-intel?site_id=${siteId}`}
                    className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                  >
                    <ExternalLink size={12} /> Facturation théorique
                  </Link>
                </div>
              </CardBody>
            </Card>
          );
        })
      )}
    </div>
  );
}

/**
 * Bandeau de couverture en haut du panneau Contrats — P0-C 2026-05-23.
 * Affiche un badge cardinal + liste des points sans contrat + CTA d'action.
 */
function CoverageBanner({ coverage, onAttachContract }) {
  const cfg = COVERAGE_BADGE[coverage.status] || COVERAGE_BADGE.contrat_partiel;
  const Icon = cfg.icon;
  const hasUncovered = coverage.uncovered_delivery_points.length > 0;
  const hasExpired = coverage.expired_contracts.length > 0;
  const hasMismatch = coverage.energy_mismatches.length > 0;
  const showCorrectCta = hasMismatch || coverage.foreign_delivery_point_links.length > 0;

  return (
    <div
      data-component="ContractCoverageBanner"
      data-coverage-status={coverage.status}
      className="rounded-md border p-3"
      style={{
        background:
          cfg.tone === 'success'
            ? 'var(--sol-bg-success-soft, #EAF2EB)'
            : cfg.tone === 'warning'
              ? 'var(--sol-bg-warn-soft, #FBF1E0)'
              : 'var(--sol-bg-paper, #FAF7F2)',
        borderColor:
          cfg.tone === 'success'
            ? 'var(--sol-succes, #3F7C5A)'
            : cfg.tone === 'warning'
              ? 'var(--sol-attention, #C68A3D)'
              : 'var(--sol-erreur, #B05A3C)',
      }}
    >
      <div className="flex items-start gap-2">
        <Icon size={18} className="shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-semibold" style={{ margin: 0 }}>
            {cfg.label}
          </p>
          {hasUncovered && (
            <ul className="mt-1 space-y-0.5">
              {coverage.uncovered_delivery_points.map((dp) => (
                <li key={dp.id} className="text-xs text-gray-700">
                  • {deliveryPointLabel(dp)} — sans contrat actif
                </li>
              ))}
            </ul>
          )}
          {hasExpired && (
            <ul className="mt-1 space-y-0.5">
              {coverage.expired_contracts.map((ct) => (
                <li key={ct.id} className="text-xs text-gray-700">
                  • {ct.label_fr} — expiré le {ct.end_date || '?'}
                </li>
              ))}
            </ul>
          )}
          {hasMismatch && (
            <ul className="mt-1 space-y-0.5">
              {coverage.energy_mismatches.map((m, i) => (
                <li key={i} className="text-xs text-gray-700">
                  • {m.message_fr}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-col gap-1 shrink-0">
          {hasUncovered && onAttachContract && (
            <button
              type="button"
              onClick={onAttachContract}
              data-action="coverage-cta-attach"
              className="text-[12px] font-medium underline"
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--sol-ink-700, #3D362C)',
              }}
            >
              Rattacher un contrat
            </button>
          )}
          {showCorrectCta && (
            <span
              data-action="coverage-cta-correct"
              className="text-[12px] font-medium text-gray-600"
            >
              Corriger le rattachement
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
