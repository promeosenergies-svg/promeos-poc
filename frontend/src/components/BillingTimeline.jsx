/**
 * PROMEOS — BillingTimeline (V70)
 * Liste mensuelle des périodes de facturation.
 * Props: { periods, siteId, onCreateAction, createdActions, activeMonth, onImport }
 *
 * CTA Voir: invoice_ids.length === 1 → détail facture, sinon → /bill-intel filtré.
 * CTA Importer: appelle onImport(siteId, monthKey, type) → file picker parent.
 */
import { useNavigate } from 'react-router-dom';
import { CheckCircle, AlertTriangle, XCircle, FileText, Upload, Zap, Eye } from 'lucide-react';
import { Button, Badge } from '../ui';
import { deepLinkWithContext } from '../services/deepLink';

const STATUS_CONFIG = {
  covered: {
    icon: CheckCircle,
    color: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-200',
    label: 'Couvert',
    badgeVariant: 'success',
  },
  partial: {
    icon: AlertTriangle,
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    label: 'Partiel',
    badgeVariant: 'warning',
  },
  missing: {
    icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    border: 'border-red-200',
    label: 'Manquant',
    badgeVariant: 'danger',
  },
};

function formatMonthKey(monthKey) {
  if (!monthKey) return '—';
  const [y, m] = monthKey.split('-');
  const d = new Date(parseInt(y, 10), parseInt(m, 10) - 1, 1);
  return d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
}

function formatEur(amount) {
  if (amount == null) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatKwh(kwh) {
  if (kwh == null) return null;
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(kwh) + '\u00a0kWh';
}

function MonthRow({ period, siteId, onCreateAction, createdActions, activeMonth, onImport }) {
  const navigate = useNavigate();
  const cfg = STATUS_CONFIG[period.coverage_status] || STATUS_CONFIG.missing;
  const Icon = cfg.icon;
  const actionKey = `${siteId}-${period.month_key}`;
  const actionCreated = createdActions?.has(actionKey);
  const isActive = activeMonth && period.month_key === activeMonth;

  const handleView = () => {
    const ids = period.invoice_ids || [];
    const url = deepLinkWithContext(siteId, period.month_key, ids.length === 1 ? ids[0] : null);
    navigate(url);
  };

  const handleImportCsv = () => {
    if (onImport) onImport(siteId, period.month_key, 'csv');
  };

  const handleImportPdf = () => {
    if (onImport) onImport(siteId, period.month_key, 'pdf');
  };

  return (
    <div
      className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${cfg.bg} ${cfg.border}${isActive ? ' ring-2 ring-amber-400' : ''}`}
    >
      {/* Statut icon */}
      <Icon size={16} className={`flex-shrink-0 ${cfg.color}`} />

      {/* Mois */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-800 capitalize">
            {formatMonthKey(period.month_key)}
          </span>
          <Badge variant={cfg.badgeVariant} size="xs">
            {cfg.label}
          </Badge>
          {period.coverage_ratio > 0 && period.coverage_status !== 'covered' && (
            <span className="text-xs text-gray-500">
              {Math.round(period.coverage_ratio * 100)}%
            </span>
          )}
        </div>
        {period.missing_reason && (
          <p className="text-xs text-gray-500 mt-0.5">{period.missing_reason}</p>
        )}
      </div>

      {/* KPIs */}
      <div className="hidden sm:flex items-center gap-4 text-xs text-gray-600 flex-shrink-0">
        <span className="flex items-center gap-1">
          <FileText size={12} />
          {period.invoices_count} facture{period.invoices_count !== 1 ? 's' : ''}
        </span>
        {period.total_ttc != null && (
          <span className="font-medium">{formatEur(period.total_ttc)}</span>
        )}
        {period.energy_kwh != null && (
          <span className="flex items-center gap-1">
            <Zap size={12} />
            {formatKwh(period.energy_kwh)}
          </span>
        )}
        {period.pdl_prm && (
          <span className="font-mono text-gray-400" title="PDL/PRM">
            {period.pdl_prm}
          </span>
        )}
      </div>

      {/* CTAs */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {period.coverage_status === 'covered' ? (
          <Button size="xs" variant="ghost" onClick={handleView}>
            <Eye size={11} /> Voir
          </Button>
        ) : (
          <>
            <Button size="xs" variant="secondary" type="button" onClick={handleImportCsv}>
              <Upload size={11} /> CSV
            </Button>
            <Button size="xs" variant="secondary" type="button" onClick={handleImportPdf}>
              <Upload size={11} /> PDF
            </Button>
          </>
        )}
        {period.coverage_status !== 'covered' && onCreateAction && (
          <Button
            size="xs"
            variant="ghost"
            onClick={() => onCreateAction(actionKey, period)}
            disabled={actionCreated}
            title={actionCreated ? 'Action déjà créée' : 'Créer une action de suivi'}
          >
            {actionCreated ? '✓' : <Zap size={11} />}
          </Button>
        )}
      </div>
    </div>
  );
}

export default function BillingTimeline({
  periods = [],
  siteId,
  onCreateAction,
  createdActions,
  activeMonth,
  onImport,
}) {
  if (periods.length === 0) {
    return <div className="text-center py-8 text-sm text-gray-500">Aucune période à afficher.</div>;
  }

  return (
    <div className="space-y-2">
      {periods.map((period) => (
        <MonthRow
          key={period.month_key}
          period={period}
          siteId={siteId}
          activeMonth={activeMonth}
          onCreateAction={onCreateAction}
          createdActions={createdActions}
          onImport={onImport}
        />
      ))}
    </div>
  );
}
