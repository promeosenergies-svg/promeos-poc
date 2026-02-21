/**
 * PROMEOS V39 — Anomalies Tertiaire / OPERAT
 * Route: /conformite/tertiaire/anomalies
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle, ShieldAlert, CheckCircle2, Loader2, Filter,
  Building2, ArrowRight, FileText, Plus,
} from 'lucide-react';
import { PageShell, Card, CardBody, Button, Badge } from '../../ui';
import { getTertiaireIssues, updateTertiaireIssue, createAction } from '../../services/api';
import { buildOperatActionPayload } from '../../models/operatActionModel';
import ProofDepositCTA from './components/ProofDepositCTA';

const SEVERITY_VARIANTS = {
  critical: 'crit',
  high: 'risque',
  medium: 'warn',
  low: 'neutral',
};

const SEVERITY_LABELS = {
  critical: 'Critique',
  high: 'Haute',
  medium: 'Moyenne',
  low: 'Basse',
};

const STATUS_LABELS = {
  open: 'Ouverte',
  ack: 'Prise en compte',
  resolved: 'Résolue',
  false_positive: 'Faux positif',
};

const STATUS_VARIANTS = {
  open: 'risque',
  ack: 'warn',
  resolved: 'ok',
  false_positive: 'neutral',
};

export default function TertiaireAnomaliesPage() {
  const navigate = useNavigate();
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('open');
  const [creatingActionFor, setCreatingActionFor] = useState(null);
  const [actionFeedback, setActionFeedback] = useState(null);

  const fetchIssues = () => {
    setLoading(true);
    const params = {};
    if (filterSeverity) params.severity = filterSeverity;
    if (filterStatus) params.status = filterStatus;
    getTertiaireIssues(params)
      .then((data) => setIssues(data.issues || []))
      .catch(() => setIssues([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchIssues(); }, [filterSeverity, filterStatus]);

  const handleStatusChange = async (issueId, newStatus) => {
    await updateTertiaireIssue(issueId, { status: newStatus });
    fetchIssues();
  };

  const handleCreateAction = async (issue) => {
    setCreatingActionFor(issue.id);
    setActionFeedback(null);
    try {
      const year = issue.year || new Date().getFullYear();
      const efa = { id: issue.efa_id, nom: issue.efa_nom || `EFA #${issue.efa_id}`, site_id: issue.site_id };
      const payload = buildOperatActionPayload({
        efa, issue, year,
        kb_open_url: issue.proof_links?.[0] || null,
        proof_type: issue.proof_required?.type || null,
      });
      const { data } = await createAction(payload);
      if (data?.status === 'existing') {
        setActionFeedback({ type: 'info', text: 'Action déjà existante' });
      } else {
        setActionFeedback({ type: 'ok', text: 'Action créée' });
      }
    } catch {
      setActionFeedback({ type: 'error', text: 'Erreur lors de la création' });
    }
    setCreatingActionFor(null);
  };

  const severityCounts = issues.reduce((acc, i) => {
    acc[i.severity] = (acc[i.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <PageShell
      title="Anomalies Tertiaire"
      subtitle="Qualité des données EFA — Décret tertiaire"
      backPath="/conformite/tertiaire"
    >
      {/* Filtres */}
      <Card>
        <CardBody className="p-4">
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-gray-400" />
              <span className="text-xs font-semibold text-gray-500 uppercase">Filtres</span>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Sévérité</label>
              <select
                value={filterSeverity}
                onChange={(e) => setFilterSeverity(e.target.value)}
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
              >
                <option value="">Toutes</option>
                <option value="critical">Critique</option>
                <option value="high">Haute</option>
                <option value="medium">Moyenne</option>
                <option value="low">Basse</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Statut</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
              >
                <option value="">Tous</option>
                <option value="open">Ouvertes</option>
                <option value="ack">Prises en compte</option>
                <option value="resolved">Résolues</option>
                <option value="false_positive">Faux positifs</option>
              </select>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* V46: Feedback toast */}
      {actionFeedback && (
        <div className={`mt-3 rounded-lg px-4 py-2 text-xs flex items-center justify-between ${
          actionFeedback.type === 'ok' ? 'bg-emerald-50 text-emerald-700' :
          actionFeedback.type === 'info' ? 'bg-blue-50 text-blue-700' :
          'bg-red-50 text-red-700'
        }`} data-testid="action-feedback">
          <span>{actionFeedback.text}</span>
          <button onClick={() => setActionFeedback(null)} className="text-gray-400 hover:text-gray-600 ml-2">&times;</button>
        </div>
      )}

      {/* Compteurs sévérité */}
      {!loading && issues.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          {['critical', 'high', 'medium', 'low'].map((sev) => (
            <Card key={sev}>
              <CardBody className="p-3 text-center">
                <p className="text-lg font-bold text-gray-900">{severityCounts[sev] || 0}</p>
                <p className="text-xs text-gray-500">{SEVERITY_LABELS[sev]}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Liste des anomalies */}
      <div className="mt-4">
        {loading ? (
          <Card>
            <CardBody className="flex items-center justify-center gap-2 py-16 text-gray-400">
              <Loader2 size={20} className="animate-spin" />
              <span className="text-sm">Chargement des anomalies…</span>
            </CardBody>
          </Card>
        ) : issues.length === 0 ? (
          <Card>
            <CardBody className="text-center py-12">
              <CheckCircle2 size={32} className="text-emerald-400 mx-auto mb-3" />
              <p className="text-sm text-gray-500">Aucune anomalie trouvée avec ces filtres</p>
            </CardBody>
          </Card>
        ) : (
          <div className="space-y-3">
            {issues.map((issue) => (
              <Card key={issue.id}>
                <CardBody className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      {/* En-tête : sévérité + code + EFA */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant={SEVERITY_VARIANTS[issue.severity] || 'neutral'} size="xs">
                          {SEVERITY_LABELS[issue.severity] || issue.severity}
                        </Badge>
                        <Badge variant={STATUS_VARIANTS[issue.status] || 'neutral'} size="xs">
                          {STATUS_LABELS[issue.status] || issue.status}
                        </Badge>
                        <span className="text-xs text-gray-400 font-mono">{issue.code}</span>
                        {issue.year && (
                          <span className="text-xs text-gray-400">Année {issue.year}</span>
                        )}
                      </div>

                      {/* V45: Title */}
                      {issue.title_fr && (
                        <p className="text-sm text-gray-900 mt-2 font-semibold">{issue.title_fr}</p>
                      )}

                      {/* Message */}
                      <p className={`text-sm text-gray-${issue.title_fr ? '700' : '900'} mt-1 ${issue.title_fr ? '' : 'font-medium'}`}>
                        {issue.message_fr}
                      </p>

                      {/* Impact */}
                      {issue.impact_fr && (
                        <p className="text-xs text-gray-500 mt-1">
                          <ShieldAlert size={12} className="inline mr-1 text-amber-500" />
                          {issue.impact_fr}
                        </p>
                      )}

                      {/* Action recommandée */}
                      {issue.action_fr && (
                        <p className="text-xs text-indigo-600 mt-1">
                          <ArrowRight size={12} className="inline mr-1" />
                          {issue.action_fr}
                        </p>
                      )}

                      {/* V45: Preuve attendue */}
                      {issue.proof_required && (
                        <div className="mt-2 p-2 rounded bg-indigo-50 border border-indigo-100" data-testid="issue-proof-required">
                          <p className="text-xs font-medium text-indigo-700">
                            Preuve attendue : {issue.proof_required.label_fr}
                          </p>
                          <p className="text-xs text-indigo-500 mt-0.5">
                            Responsable : {issue.proof_required.owner_role}
                            {issue.proof_required.deadline_hint ? ` · ${issue.proof_required.deadline_hint}` : ''}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex flex-col gap-1 shrink-0">
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => navigate(`/conformite/tertiaire/efa/${issue.efa_id}`)}
                      >
                        <Building2 size={12} />
                        Voir EFA
                      </Button>
                      {issue.status === 'open' && (
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => handleStatusChange(issue.id, 'ack')}
                        >
                          Prendre en compte
                        </Button>
                      )}
                      {issue.status === 'ack' && (
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => handleStatusChange(issue.id, 'resolved')}
                        >
                          Marquer résolue
                        </Button>
                      )}
                      {/* V45: Deep-link Mémobox si proof_links disponible */}
                      {issue.proof_links && issue.proof_links.length > 0 ? (
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => navigate(issue.proof_links[0])}
                          data-testid="btn-deposit-proof"
                        >
                          <FileText size={12} /> Déposer la preuve
                        </Button>
                      ) : (
                        <ProofDepositCTA
                          hint={[
                            `EFA:${issue.efa_nom || `#${issue.efa_id}`}`,
                            `efa_id:${issue.efa_id}`,
                            `Issue:${issue.code}`,
                            `Sévérité:${SEVERITY_LABELS[issue.severity] || issue.severity}`,
                          ].join(' | ')}
                          label="Déposer la preuve"
                        />
                      )}
                      {/* V46: Créer une action */}
                      <Button
                        size="xs"
                        variant="secondary"
                        onClick={() => handleCreateAction(issue)}
                        disabled={creatingActionFor === issue.id}
                        data-testid="btn-create-action"
                      >
                        {creatingActionFor === issue.id
                          ? <Loader2 size={12} className="animate-spin" />
                          : <Plus size={12} />}
                        Créer une action
                      </Button>
                  </div>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
