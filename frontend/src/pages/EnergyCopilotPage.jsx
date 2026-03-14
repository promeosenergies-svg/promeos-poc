/**
 * PROMEOS — Energy Copilot Page (Chantier 3)
 * Route: /energy-copilot
 * Monthly automated action proposals with validate/reject workflow.
 */
import { useState, useEffect, useCallback } from 'react';
import {
  Brain,
  Play,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  TrendingDown,
  Moon,
  Calendar,
  FileWarning,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useScope } from '../contexts/ScopeContext';
import {
  getCopilotActions,
  runCopilot,
  validateCopilotAction,
  rejectCopilotAction,
} from '../services/api';
import { PageShell, Card, CardBody, Button, Badge } from '../ui';
import { fmtKwh, fmtEur } from '../utils/format';

const RULE_ICONS = {
  R1_MONTHLY_DRIFT: TrendingDown,
  R2_NIGHT_BASELOAD: Moon,
  R3_WEEKEND_EXCESS: Calendar,
  R4_INVOICE_GAP: FileWarning,
};

const STATUS_CONFIG = {
  proposed: { label: 'À valider', variant: 'warn', icon: AlertTriangle },
  validated: { label: 'Valide', variant: 'ok', icon: CheckCircle },
  rejected: { label: 'Rejete', variant: 'neutral', icon: XCircle },
  converted: { label: 'Converti', variant: 'ok', icon: CheckCircle },
};

function ActionCard({ action, onValidate, onReject, loading }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = RULE_ICONS[action.rule_code] || AlertTriangle;
  const statusCfg = STATUS_CONFIG[action.status] || STATUS_CONFIG.proposed;
  const isProposed = action.status === 'proposed';

  return (
    <Card>
      <CardBody className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center shrink-0 mt-0.5">
              <Icon size={16} className="text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">{action.title}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {action.rule_label} · Site #{action.site_id} · {action.period_month}/
                {action.period_year}
              </p>
            </div>
          </div>
          <Badge variant={statusCfg.variant}>{statusCfg.label}</Badge>
        </div>

        {/* Impact */}
        {(action.estimated_savings_kwh || action.estimated_savings_eur) && (
          <div className="flex gap-4 text-xs">
            {action.estimated_savings_kwh && (
              <span className="text-emerald-600 font-medium">
                -{fmtKwh(action.estimated_savings_kwh)}
              </span>
            )}
            {action.estimated_savings_eur && (
              <span className="text-emerald-600 font-medium">
                -{fmtEur(action.estimated_savings_eur)}
              </span>
            )}
          </div>
        )}

        {/* Description + Evidence toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Masquer' : 'Voir le détail'}
        </button>

        {expanded && (
          <div className="space-y-2 pt-1">
            {action.description && (
              <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded">{action.description}</p>
            )}
            {action.evidence && Object.keys(action.evidence).length > 0 && (
              <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded space-y-1">
                <p className="font-medium text-gray-600">Metriques :</p>
                {Object.entries(action.evidence).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span>{k.replace(/_/g, ' ')}</span>
                    <span className="font-medium text-gray-700">
                      {typeof v === 'number' ? v.toLocaleString('fr-FR') : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        {isProposed && (
          <div className="flex gap-2 pt-1">
            <Button size="sm" onClick={() => onValidate(action.id)} disabled={loading}>
              <CheckCircle size={14} className="mr-1" /> Valider
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => onReject(action.id)}
              disabled={loading}
            >
              <XCircle size={14} className="mr-1" /> Rejeter
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function EnergyCopilotPage() {
  const { org } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState(null);

  const fetchActions = useCallback(() => {
    if (!org?.id) return;
    setLoading(true);
    setError(null);
    const params = statusFilter ? { status: statusFilter } : {};
    getCopilotActions(org.id, params)
      .then(setData)
      .catch((err) => {
        setData(null);
        setError(err?.message || 'Erreur chargement des actions');
      })
      .finally(() => setLoading(false));
  }, [org?.id, statusFilter]);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  const handleRun = async () => {
    if (!org?.id) return;
    setRunning(true);
    setError(null);
    try {
      await runCopilot(org.id);
      fetchActions();
    } catch (err) {
      setError(err?.message || "Erreur lors de l'analyse");
    } finally {
      setRunning(false);
    }
  };

  const handleValidate = async (id) => {
    setActionLoading(true);
    try {
      await validateCopilotAction(id);
      fetchActions();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Erreur lors de la validation');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (id) => {
    const reason = window.prompt('Motif de rejet (obligatoire) :');
    if (!reason || !reason.trim()) return;
    setActionLoading(true);
    try {
      await rejectCopilotAction(id, reason.trim());
      fetchActions();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Erreur lors du rejet');
    } finally {
      setActionLoading(false);
    }
  };

  const actions = data?.actions || [];
  const proposedCount = actions.filter((a) => a.status === 'proposed').length;
  const totalSavings = actions
    .filter((a) => a.status === 'proposed' || a.status === 'converted')
    .reduce((sum, a) => sum + (a.estimated_savings_eur || 0), 0);

  return (
    <PageShell
      icon={Brain}
      title="Energy Copilot"
      subtitle="Actions automatiques mensuelles"
      actions={
        <Button size="sm" onClick={handleRun} disabled={running}>
          {running ? (
            <Loader2 size={14} className="animate-spin mr-1" />
          ) : (
            <Play size={14} className="mr-1" />
          )}
          Lancer l'analyse
        </Button>
      }
    >
      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardBody className="text-center">
            <p className="text-2xl font-bold text-amber-600">{proposedCount}</p>
            <p className="text-xs text-gray-500">À valider</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-2xl font-bold text-gray-900">{actions.length}</p>
            <p className="text-xs text-gray-500">Total propositions</p>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="text-center">
            <p className="text-2xl font-bold text-emerald-600">
              {totalSavings > 0 ? `${Math.round(totalSavings).toLocaleString('fr-FR')} €` : '-'}
            </p>
            <p className="text-xs text-gray-500">Economies potentielles</p>
          </CardBody>
        </Card>
      </div>

      {/* Filter chips */}
      <div className="flex gap-2">
        {[null, 'proposed', 'converted', 'rejected'].map((s) => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition ${
              statusFilter === s
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {s === null ? 'Tous' : STATUS_CONFIG[s]?.label || s}
          </button>
        ))}
      </div>

      {/* Actions list */}
      {loading ? (
        <div className="flex items-center justify-center py-12 text-gray-400">
          <Loader2 size={20} className="animate-spin mr-2" />
          Chargement...
        </div>
      ) : actions.length === 0 ? (
        <Card>
          <CardBody className="text-center py-8">
            <Brain size={32} className="mx-auto text-gray-300 mb-2" />
            <p className="text-sm text-gray-500">
              Aucune proposition pour le moment. Lancez l'analyse pour détecter les opportunités.
            </p>
          </CardBody>
        </Card>
      ) : (
        <div className="space-y-3">
          {actions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onValidate={handleValidate}
              onReject={handleReject}
              loading={actionLoading}
            />
          ))}
        </div>
      )}
    </PageShell>
  );
}
