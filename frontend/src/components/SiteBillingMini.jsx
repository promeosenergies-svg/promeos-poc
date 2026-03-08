/**
 * PROMEOS - SiteBillingMini
 * V66: Mini billing KPIs for Site360 Factures tab.
 * Props: siteId
 * Calls getSiteBilling(siteId) → shows 3 KPIs + CTA to /bill-intel.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSiteBilling } from '../services/api';
import { Card, CardBody, Button, EmptyState, KpiCardInline } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { FileText, AlertTriangle, Calendar, ExternalLink } from 'lucide-react';

export default function SiteBillingMini({ siteId }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    getSiteBilling(siteId)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        setError('Impossible de charger les données de facturation');
        setLoading(false);
      });
  }, [siteId]);

  if (loading) return <SkeletonCard lines={3} />;

  if (error) {
    return <div className="py-4 text-center text-sm text-red-500">{error}</div>;
  }

  const invoices = data?.invoices || [];
  const insights = data?.insights || [];
  const lastInvoice = invoices.length > 0 ? invoices[invoices.length - 1] : null;
  const openInsights = insights.filter((i) => i.insight_status === 'open' || !i.insight_status);

  if (!data || invoices.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="Aucune facture"
        description="Importer des factures CSV ou PDF dans le module Facturation."
        action={
          <Button size="sm" onClick={() => navigate('/bill-intel')}>
            <ExternalLink size={14} /> Voir Facturation
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-4 pt-4">
      {/* KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <KpiCardInline
          icon={FileText}
          label="Factures"
          value={invoices.length}
          color="text-blue-600"
        />
        <KpiCardInline
          icon={AlertTriangle}
          label="Anomalies"
          value={openInsights.length}
          color={openInsights.length > 0 ? 'text-red-500' : 'text-green-500'}
        />
        <KpiCardInline
          icon={Calendar}
          label="Dernière facture"
          value={lastInvoice?.period_end || lastInvoice?.issue_date || '—'}
          color="text-gray-500"
        />
      </div>

      {/* Anomalies summary */}
      {openInsights.length > 0 && (
        <Card>
          <CardBody>
            <p className="text-xs font-semibold text-red-600 mb-2">
              {openInsights.length} anomalie{openInsights.length > 1 ? 's' : ''} ouverte
              {openInsights.length > 1 ? 's' : ''}
            </p>
            <ul className="space-y-1">
              {openInsights.slice(0, 3).map((ins) => (
                <li key={ins.id} className="text-xs text-gray-600 flex items-center gap-1">
                  <AlertTriangle size={11} className="text-orange-400 flex-shrink-0" />
                  {ins.message || ins.type}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* CTA */}
      <div className="flex justify-end pt-1">
        <Button size="sm" variant="secondary" onClick={() => navigate('/bill-intel')}>
          <ExternalLink size={14} /> Voir toutes les factures
        </Button>
      </div>
    </div>
  );
}
