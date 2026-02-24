/**
 * PROMEOS — BillingTimeline (V67)
 * Liste mensuelle des périodes de facturation.
 * Props: { periods, siteId, onCreateAction, createdActions }
 */
import { useNavigate } from 'react-router-dom';
import { CheckCircle, AlertTriangle, XCircle, FileText, Upload, Zap } from 'lucide-react';
import { Button, Badge } from '../ui';

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
  const [y, m] = monthKey.split('-');
  const d = new Date(parseInt(y), parseInt(m) - 1, 1);
  return d.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
}

function formatEur(amount) {
  if (amount == null) return '—';
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(amount);
}

function MonthRow({ period, siteId, onCreateAction, createdActions, activeMonth }) {
  const navigate = useNavigate();
  const cfg = STATUS_CONFIG[period.coverage_status] || STATUS_CONFIG.missing;
  const Icon = cfg.icon;
  const actionKey = `${siteId}-${period.month_key}`;
  const actionCreated = createdActions?.has(actionKey);
  const isActive = activeMonth && period.month_key === activeMonth;

  const handleView = () => {
    const params = new URLSearchParams();
    if (siteId) params.set('site_id', siteId);
    params.set('month', period.month_key);
    navigate(`/bill-intel?${params.toString()}`);
  };

  const handleImport = () => {
    const params = new URLSearchParams();
    if (siteId) params.set('site_id', siteId);
    params.set('month', period.month_key);
    navigate(`/bill-intel?${params.toString()}`);
  };

  return (
    <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${cfg.bg} ${cfg.border}${isActive ? ' ring-2 ring-amber-400' : ''}`}>
      {/* Statut icon */}
      <Icon size={16} className={`flex-shrink-0 ${cfg.color}`} />

      {/* Mois */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-800 capitalize">
            {formatMonthKey(period.month_key)}
          </span>
          <Badge variant={cfg.badgeVariant} size="xs">{cfg.label}</Badge>
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
      </div>

      {/* CTAs */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {period.coverage_status === 'covered' ? (
          <Button size="xs" variant="ghost" onClick={handleView}>
            Voir
          </Button>
        ) : (
          <Button size="xs" variant="secondary" onClick={handleImport}>
            <Upload size={11} /> Importer
          </Button>
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

export default function BillingTimeline({ periods = [], siteId, onCreateAction, createdActions, activeMonth }) {
  if (periods.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-gray-500">
        Aucune période à afficher.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {periods.map(period => (
        <MonthRow
          key={period.month_key}
          period={period}
          siteId={siteId}
          activeMonth={activeMonth}
          onCreateAction={onCreateAction}
          createdActions={createdActions}
        />
      ))}
    </div>
  );
}
