/**
 * PROMEOS — V96 SiteContractsSummary
 * Affiche les contrats énergie enrichis pour un site.
 */
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, AlertTriangle, BadgeEuro, ExternalLink } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { getPatrimoineContracts } from '../services/api';

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

function daysUntil(dateStr) {
  if (!dateStr) return null;
  const diff = Math.ceil((new Date(dateStr) - new Date()) / (1000 * 60 * 60 * 24));
  return diff;
}

export default function SiteContractsSummary({ siteId }) {
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    getPatrimoineContracts({ site_id: siteId })
      .then((data) => {
        if (!stale) setContracts(data.contracts || []);
      })
      .catch(() => {
        if (!stale) setContracts([]);
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  if (loading) return <SkeletonCard />;

  if (contracts.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="Aucun contrat"
        text="Ajoutez un contrat énergie pour activer le suivi."
      />
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-gray-700">Contrats énergie</h4>
      {contracts.map((ct) => {
        const daysLeft = daysUntil(ct.end_date);
        const alertRenewal =
          ct.renewal_alert_days &&
          daysLeft !== null &&
          daysLeft > 0 &&
          daysLeft <= ct.renewal_alert_days;
        return (
          <Card key={ct.id} className={alertRenewal ? 'border-l-4 border-l-amber-400' : ''}>
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
                {ct.delivery_points_count > 0 && (
                  <span>
                    {ct.delivery_points_count} PDL rattaché{ct.delivery_points_count > 1 ? 's' : ''}
                  </span>
                )}
                {ct.date_signature && <span>Signé le {ct.date_signature}</span>}
              </div>
              {alertRenewal && (
                <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                  <AlertTriangle size={12} />
                  <span>
                    Alerte renouvellement — {daysLeft}j avant échéance (seuil:{' '}
                    {ct.renewal_alert_days}j)
                  </span>
                </div>
              )}
              {/* B2-5: Links to billing & shadow billing */}
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
      })}
    </div>
  );
}
