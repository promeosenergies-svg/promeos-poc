/**
 * PROMEOS V40 — Fiche détaillée EFA
 * Route: /conformite/tertiaire/efa/:id
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Building2, AlertTriangle, CheckCircle2, Clock, FileText, Download,
  Loader2, ArrowRight, ShieldAlert, Users, Calendar, Zap, Link2, Plus,
} from 'lucide-react';
import { PageShell, Card, CardBody, Button, Badge } from '../../ui';
import {
  getTertiaireEfa, runTertiaireControls, precheckTertiaireDeclaration,
  exportTertiairePack, getTertiaireEfaProofs, createAction,
} from '../../services/api';
import { buildOperatActionPayload, buildOperatActionDeepLink } from '../../models/operatActionModel';
import ProofDepositCTA from './components/ProofDepositCTA';

const SEVERITY_VARIANTS = {
  critical: 'crit',
  high: 'risque',
  medium: 'warn',
  low: 'neutral',
};

const STATUS_LABELS = {
  active: 'Active',
  draft: 'Brouillon',
  closed: 'Fermée',
};

export default function TertiaireEfaDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [efa, setEfa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [controlsRunning, setControlsRunning] = useState(false);
  const [precheckResult, setPrecheckResult] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [proofsStatus, setProofsStatus] = useState(null);
  const [actionFeedback, setActionFeedback] = useState(null);
  const [creatingActionFor, setCreatingActionFor] = useState(null);

  const handleCreateAction = async (issue) => {
    setCreatingActionFor(issue.code);
    setActionFeedback(null);
    try {
      const year = new Date().getFullYear();
      const payload = buildOperatActionPayload({
        efa, issue, year,
        kb_open_url: issue.proof_links?.[0] || null,
        proof_type: issue.proof_required?.type || null,
      });
      const { data } = await createAction(payload);
      if (data?.status === 'existing') {
        setActionFeedback({ type: 'info', text: 'Action déjà existante dans le plan d\u2019actions' });
      } else {
        setActionFeedback({ type: 'ok', text: 'Action créée dans le plan d\u2019actions' });
      }
    } catch {
      setActionFeedback({ type: 'error', text: 'Erreur lors de la création de l\u2019action' });
    }
    setCreatingActionFor(null);
  };

  const fetchEfa = () => {
    setLoading(true);
    getTertiaireEfa(id)
      .then(setEfa)
      .catch(() => setEfa(null))
      .finally(() => setLoading(false));
  };

  const fetchProofsStatus = () => {
    getTertiaireEfaProofs(id)
      .then(setProofsStatus)
      .catch(() => setProofsStatus(null));
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { fetchEfa(); fetchProofsStatus(); }, [id]);

  const handleRunControls = async () => {
    setControlsRunning(true);
    try {
      await runTertiaireControls(id, new Date().getFullYear());
      fetchEfa();
    } finally {
      setControlsRunning(false);
    }
  };

  const handlePrecheck = async () => {
    const year = new Date().getFullYear();
    const result = await precheckTertiaireDeclaration(id, year);
    setPrecheckResult(result);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const year = new Date().getFullYear();
      const result = await exportTertiairePack(id, year);
      setExportResult(result);
      fetchEfa();
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <PageShell title="Fiche EFA" subtitle="Chargement…" backPath="/conformite/tertiaire">
        <div className="flex items-center justify-center gap-2 py-16 text-gray-400">
          <Loader2 size={20} className="animate-spin" />
        </div>
      </PageShell>
    );
  }

  if (!efa) {
    return (
      <PageShell title="EFA introuvable" backPath="/conformite/tertiaire">
        <Card><CardBody className="text-center py-8 text-gray-400">EFA non trouvée</CardBody></Card>
      </PageShell>
    );
  }

  const totalSurface = (efa.buildings || []).reduce((s, b) => s + (b.surface_m2 || 0), 0);
  const qualif = efa.qualification || {};

  return (
    <PageShell
      title={efa.nom}
      subtitle={`EFA #${efa.id} — ${STATUS_LABELS[efa.statut] || efa.statut}`}
      backPath="/conformite/tertiaire"
    >
      {/* Status card (feu tricolore) */}
      <Card>
        <CardBody className="p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                qualif.status === 'complete' ? 'bg-emerald-100' :
                qualif.status === 'partielle' ? 'bg-amber-100' : 'bg-red-100'
              }`}>
                {qualif.status === 'complete' ? (
                  <CheckCircle2 size={24} className="text-emerald-600" />
                ) : qualif.status === 'partielle' ? (
                  <AlertTriangle size={24} className="text-amber-600" />
                ) : (
                  <ShieldAlert size={24} className="text-red-600" />
                )}
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">
                  Complétude : {qualif.completeness_pct ?? 0}%
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{qualif.explanation}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="xs" variant="secondary" onClick={handleRunControls} disabled={controlsRunning}>
                {controlsRunning ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                Contrôles
              </Button>
              <Button size="xs" variant="secondary" onClick={handlePrecheck}>
                <CheckCircle2 size={14} /> Pré-vérification
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* Bâtiments */}
        <Card>
          <CardBody>
            <div className="flex items-center gap-2 mb-3">
              <Building2 size={16} className="text-gray-500" />
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                Bâtiments ({(efa.buildings || []).length})
              </h4>
            </div>
            {(efa.buildings || []).length === 0 ? (
              <p className="text-sm text-gray-400">Aucun bâtiment associé</p>
            ) : (
              <div className="space-y-2">
                {(efa.buildings || []).map((b) => (
                  <div key={b.id} className="flex justify-between text-sm border-b border-gray-100 pb-2">
                    <span className="text-gray-700">{b.usage_label || 'Usage non défini'}</span>
                    <span className="font-medium text-gray-900">{b.surface_m2 ? `${Math.round(b.surface_m2)} m²` : '—'}</span>
                  </div>
                ))}
                <div className="flex justify-between text-sm font-semibold pt-1">
                  <span className="text-gray-700">Total</span>
                  <span className="text-gray-900">{Math.round(totalSurface)} m²</span>
                </div>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Responsables */}
        <Card>
          <CardBody>
            <div className="flex items-center gap-2 mb-3">
              <Users size={16} className="text-gray-500" />
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                Responsables ({(efa.responsibilities || []).length})
              </h4>
            </div>
            {(efa.responsibilities || []).length === 0 ? (
              <p className="text-sm text-gray-400">Aucun responsable défini</p>
            ) : (
              <div className="space-y-2">
                {(efa.responsibilities || []).map((r) => (
                  <div key={r.id} className="text-sm border-b border-gray-100 pb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral" size="xs">{r.role}</Badge>
                      <span className="text-gray-700">{r.entity_value || '—'}</span>
                    </div>
                    {r.contact_email && (
                      <p className="text-xs text-gray-400 mt-0.5">{r.contact_email}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Événements périmètre */}
        <Card>
          <CardBody>
            <div className="flex items-center gap-2 mb-3">
              <Calendar size={16} className="text-gray-500" />
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                Événements périmètre ({(efa.events || []).length})
              </h4>
            </div>
            {(efa.events || []).length === 0 ? (
              <p className="text-sm text-gray-400">Aucun événement</p>
            ) : (
              <div className="space-y-2">
                {(efa.events || []).map((e) => (
                  <div key={e.id} className="flex items-start gap-2 text-sm border-b border-gray-100 pb-2">
                    <Clock size={14} className="text-gray-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-gray-700">{e.description || e.type}</p>
                      <p className="text-xs text-gray-400">{e.effective_date}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Preuves + Memobox */}
        <Card>
          <CardBody>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText size={16} className="text-gray-500" />
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Preuves documentaires ({(efa.proofs || []).length})
                </h4>
              </div>
              <ProofDepositCTA
                hint={[
                  `EFA:${efa.nom}`,
                  `efa_id:${efa.id}`,
                  (efa.responsibilities || []).length > 0
                    ? `Responsable:${efa.responsibilities[0].entity_value || efa.responsibilities[0].role}`
                    : null,
                  totalSurface > 0 ? `Surface:${Math.round(totalSurface)} m²` : null,
                ].filter(Boolean).join(' | ')}
              />
            </div>
            {(efa.proofs || []).length === 0 ? (
              <p className="text-sm text-gray-400">Aucune preuve déposée</p>
            ) : (
              <div className="space-y-2">
                {(efa.proofs || []).map((p) => (
                  <div key={p.id} className="flex items-center gap-2 text-sm border-b border-gray-100 pb-2">
                    <FileText size={14} className="text-gray-400 shrink-0" />
                    <span className="text-gray-700 truncate">{p.type}</span>
                    {p.kb_doc_id && <Badge variant="neutral" size="xs">Memobox</Badge>}
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* V45: Statut des preuves */}
      {proofsStatus && (
        <div className="mt-4" data-testid="proofs-status-bloc">
          <Card>
            <CardBody className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={16} className="text-indigo-500" />
                  <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                    Statut des preuves
                  </h4>
                </div>
                <Button
                  size="xs"
                  variant="secondary"
                  onClick={() => navigate(`/kb?context=proof&efa_id=${efa.id}`)}
                >
                  <FileText size={12} /> Voir dans la Mémobox
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-2 rounded-lg bg-blue-50">
                  <p className="text-lg font-bold text-blue-700">{proofsStatus.expected_count ?? 0}</p>
                  <p className="text-xs text-blue-600">Attendues</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-amber-50">
                  <p className="text-lg font-bold text-amber-700">{proofsStatus.deposited_count ?? 0}</p>
                  <p className="text-xs text-amber-600">Déposées</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-emerald-50">
                  <p className="text-lg font-bold text-emerald-700">{proofsStatus.validated_count ?? 0}</p>
                  <p className="text-xs text-emerald-600">Validées</p>
                </div>
              </div>
              {proofsStatus.coverage_pct != null && (
                <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>Couverture</span>
                    <span className="font-medium">{proofsStatus.coverage_pct}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${
                        proofsStatus.coverage_pct >= 80 ? 'bg-emerald-500' :
                        proofsStatus.coverage_pct >= 40 ? 'bg-amber-500' : 'bg-red-400'
                      }`}
                      style={{ width: `${Math.min(proofsStatus.coverage_pct, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {/* Issues ouvertes — V45: enrichi avec title_fr + proof_required */}
      {(efa.open_issues || []).length > 0 && (
        <div className="mt-4">
          <Card>
            <CardBody>
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle size={16} className="text-amber-500" />
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Anomalies ouvertes ({(efa.open_issues || []).length})
                </h4>
              </div>
              <div className="space-y-2">
                {(efa.open_issues || []).map((issue) => (
                  <div key={issue.id} className="rounded-md border border-gray-100 p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={SEVERITY_VARIANTS[issue.severity] || 'neutral'} size="xs">
                            {issue.severity}
                          </Badge>
                          <span className="text-xs text-gray-400">{issue.code}</span>
                        </div>
                        {issue.title_fr && (
                          <p className="text-sm font-semibold text-gray-900 mt-1">{issue.title_fr}</p>
                        )}
                        <p className="text-sm text-gray-700 mt-0.5">{issue.message_fr}</p>
                        {issue.impact_fr && (
                          <p className="text-xs text-gray-500 mt-0.5">{issue.impact_fr}</p>
                        )}
                        {issue.action_fr && (
                          <p className="text-xs text-indigo-600 mt-0.5">{issue.action_fr}</p>
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
                      {/* V45+V46: CTA Mémobox + Créer action */}
                      <div className="flex flex-col gap-1 shrink-0">
                        {issue.proof_links && issue.proof_links.length > 0 && (
                          <Button
                            size="xs"
                            variant="secondary"
                            onClick={() => navigate(issue.proof_links[0])}
                            data-testid="btn-deposit-proof"
                          >
                            <FileText size={12} /> Déposer la preuve
                          </Button>
                        )}
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => handleCreateAction(issue)}
                          disabled={creatingActionFor === issue.code}
                          data-testid="btn-create-action"
                        >
                          {creatingActionFor === issue.code
                            ? <Loader2 size={12} className="animate-spin" />
                            : <Plus size={12} />}
                          Créer une action
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* V46: Feedback toast */}
      {actionFeedback && (
        <div className={`mt-4 rounded-lg px-4 py-3 text-sm flex items-center justify-between ${
          actionFeedback.type === 'ok' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
          actionFeedback.type === 'info' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
          'bg-red-50 text-red-700 border border-red-200'
        }`} data-testid="action-feedback">
          <span>{actionFeedback.text}</span>
          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="secondary"
              onClick={() => navigate(buildOperatActionDeepLink(
                buildOperatActionPayload({ efa, issue: (efa.open_issues || [])[0], year: new Date().getFullYear() })
              ))}
            >
              Ouvrir le plan d&apos;actions
            </Button>
            <button onClick={() => setActionFeedback(null)} className="text-gray-400 hover:text-gray-600">
              &times;
            </button>
          </div>
        </div>
      )}

      {/* V46: Mini-bloc Plan d'actions OPERAT */}
      {(efa.open_issues || []).length > 0 && (
        <div className="mt-4" data-testid="operat-actions-bloc">
          <Card>
            <CardBody className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Plus size={16} className="text-indigo-500" />
                  <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                    Plan d&apos;actions OPERAT
                  </h4>
                </div>
                <Button
                  size="xs"
                  variant="secondary"
                  onClick={() => navigate(`/actions?source=operat&efa_id=${efa.id}`)}
                  data-testid="btn-view-action-plan"
                >
                  <ArrowRight size={12} /> Voir dans le plan d&apos;actions
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* EFA liées */}
      {(efa.links || []).length > 0 && (
        <div className="mt-4">
          <Card>
            <CardBody>
              <div className="flex items-center gap-2 mb-3">
                <Link2 size={16} className="text-gray-500" />
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  EFA liées ({(efa.links || []).length})
                </h4>
              </div>
              <div className="space-y-2">
                {(efa.links || []).map((link) => {
                  const linkedId = link.child_efa_id === efa.id ? link.parent_efa_id : link.child_efa_id;
                  return (
                    <button
                      key={link.id}
                      onClick={() => navigate(`/conformite/tertiaire/efa/${linkedId}`)}
                      className="w-full text-left flex items-center gap-2 text-sm p-2 rounded hover:bg-gray-50"
                    >
                      <Building2 size={14} className="text-gray-400" />
                      <span className="text-gray-700">EFA #{linkedId}</span>
                      <Badge variant="neutral" size="xs">{link.reason}</Badge>
                      <ArrowRight size={12} className="text-gray-400 ml-auto" />
                    </button>
                  );
                })}
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Actions OPERAT — export pack toujours accessible */}
      <div className="mt-4">
        <Card>
          <CardBody className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                  Actions OPERAT
                </h4>
                <p className="text-xs text-gray-400 mt-0.5">
                  Pré-vérification et export du dossier déclaratif
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button size="xs" variant="secondary" onClick={handlePrecheck}>
                  <CheckCircle2 size={14} /> Pré-vérifier
                </Button>
                <Button
                  size="xs"
                  data-testid="btn-export-pack"
                  onClick={handleExport}
                  disabled={exporting}
                >
                  {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                  Exporter le pack
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Precheck result */}
      {precheckResult && (
        <div className="mt-4">
          <Card>
            <CardBody>
              <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-3">
                Pré-vérification {precheckResult.year}
              </h4>
              <div className="flex items-center gap-2 mb-3">
                <Badge variant={
                  precheckResult.status === 'pret' ? 'ok' :
                  precheckResult.status === 'bloque' ? 'crit' : 'warn'
                }>
                  {precheckResult.status === 'pret' ? 'Prêt' :
                   precheckResult.status === 'bloque' ? 'Bloqué' : 'Incomplet'}
                </Badge>
                <span className="text-xs text-gray-400">
                  {precheckResult.ok_count}/{precheckResult.total} critères validés
                </span>
              </div>
              <div className="space-y-1">
                {(precheckResult.checklist || []).map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    {item.ok ? (
                      <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />
                    ) : (
                      <AlertTriangle size={14} className="text-amber-500 shrink-0" />
                    )}
                    <span className="text-gray-700">{item.label}</span>
                    <span className="text-gray-400 ml-auto">{item.detail}</span>
                  </div>
                ))}
              </div>
              {precheckResult.status === 'pret' && (
                <Button size="sm" className="mt-4" onClick={handleExport} disabled={exporting}>
                  {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                  Générer le pack export (simulation)
                </Button>
              )}
            </CardBody>
          </Card>
        </div>
      )}

      {/* Export info + lien Mémobox V40 */}
      {(efa.declarations || []).some((d) => d.status === 'exported') && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50/30 p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">Pack export généré (simulation)</p>
              <p className="text-xs text-gray-500 mt-0.5">
                Ce pack est une simulation PROMEOS. Il ne constitue pas une soumission officielle sur OPERAT.
              </p>
              {exportResult?.kb_doc_id && (
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-amber-200">
                  <Badge variant="ok" size="xs">Mémobox</Badge>
                  <span className="text-xs text-gray-600">
                    Document enregistré : {exportResult.kb_doc_display_name || exportResult.kb_doc_id}
                  </span>
                  <Button
                    size="xs"
                    variant="secondary"
                    onClick={() => navigate(exportResult.kb_open_url)}
                    aria-label="Ouvrir le pack dans la Mémobox"
                  >
                    <FileText size={12} />
                    Ouvrir dans la Mémobox
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </PageShell>
  );
}
