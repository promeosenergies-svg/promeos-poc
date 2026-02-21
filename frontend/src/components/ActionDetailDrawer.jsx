/**
 * PROMEOS - ActionDetailDrawer (Sprint V5.0)
 * 5-tab drawer: Detail, Impact, Pieces jointes, Commentaires, Historique.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Clock, User, Tag, Paperclip, MessageSquare, History,
  BadgeEuro, CheckCircle, AlertTriangle, ArrowRight, Plus,
  Shield, ExternalLink, FileCheck,
} from 'lucide-react';
import Drawer from '../ui/Drawer';
import { Badge, Button, TrustBadge } from '../ui';
import { useToast } from '../ui/ToastProvider';
import {
  getActionDetail, getActionComments, addActionComment,
  getActionEvidence, addActionEvidence, getActionEvents,
  patchAction, getTertiaireEfaProofs,
} from '../services/api';
import { ACTION_STATUS_LABELS } from '../domain/compliance/complianceLabels.fr';
import {
  isOperatAction, parseOperatSourceId, buildActionProofLink,
  isActionClosable, resolveProofStatus,
  PROOF_STATUS_LABELS, PROOF_STATUS_BADGE,
} from '../models/actionProofLinkModel';

const STATUS_TO_BE = { backlog: 'open', in_progress: 'in_progress', done: 'done', planned: 'blocked' };
const STATUS_TO_FE = { open: 'backlog', in_progress: 'in_progress', done: 'done', blocked: 'planned', false_positive: 'done' };

const TABS = [
  { id: 'detail', label: 'Detail', icon: Tag },
  { id: 'impact', label: 'Impact', icon: BadgeEuro },
  { id: 'evidence', label: 'Pieces jointes', icon: Paperclip },
  { id: 'comments', label: 'Commentaires', icon: MessageSquare },
  { id: 'history', label: 'Historique', icon: History },
];

const PRIORITY_LABEL = { 1: 'P1 — Critique', 2: 'P2 — Haute', 3: 'P3 — Moyenne', 4: 'P4 — Faible', 5: 'P5 — Faible' };
const PRIORITY_BADGE = { 1: 'crit', 2: 'warn', 3: 'info', 4: 'neutral', 5: 'neutral' };

const STATUS_PILL = {
  open:           'bg-gray-100 text-gray-700',
  in_progress:    'bg-amber-100 text-amber-700',
  done:           'bg-green-100 text-green-700',
  blocked:        'bg-blue-100 text-blue-700',
  false_positive: 'bg-red-100 text-red-600',
};

const STATUS_WORKFLOW = [
  { value: 'open', label: 'Ouverte' },
  { value: 'in_progress', label: 'En cours' },
  { value: 'blocked', label: 'Bloquee' },
  { value: 'done', label: 'Terminee' },
  { value: 'false_positive', label: 'Faux positif' },
];

const EVENT_LABELS = {
  created: 'Creee',
  status_change: 'Statut modifie',
  assigned: 'Assignee',
  priority_change: 'Priorite modifiee',
  commented: 'Commentaire ajoute',
  evidence_added: 'Piece ajoutee',
  realized_updated: 'ROI mis a jour',
  field_update: 'Champ modifie',
};

const EVENT_ICONS = {
  created: CheckCircle,
  status_change: ArrowRight,
  assigned: User,
  commented: MessageSquare,
  evidence_added: Paperclip,
  realized_updated: BadgeEuro,
  priority_change: AlertTriangle,
  field_update: Tag,
};

const SOURCE_LABELS = {
  compliance: 'Conformite',
  consumption: 'Consommation',
  billing: 'Facturation',
  purchase: 'Achats',
  manual: 'Manuelle',
  insight: 'Diagnostic',
};

export default function ActionDetailDrawer({ action, open, onClose, onUpdate }) {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [tab, setTab] = useState('detail');
  const [detail, setDetail] = useState(null);
  const [comments, setComments] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  // V47 — Preuves OPERAT
  const [proofsSummary, setProofsSummary] = useState(null);

  // Comment form
  const [commentAuthor, setCommentAuthor] = useState('');
  const [commentBody, setCommentBody] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);

  // Evidence form
  const [evidenceLabel, setEvidenceLabel] = useState('');
  const [evidenceUrl, setEvidenceUrl] = useState('');
  const [submittingEvidence, setSubmittingEvidence] = useState(false);

  // Realized gain edit
  const [editingRealized, setEditingRealized] = useState(false);
  const [realizedValue, setRealizedValue] = useState('');

  const actionId = action?._backend?.id || action?.id;

  const fetchAll = useCallback(async () => {
    if (!actionId) return;
    setLoading(true);
    try {
      const [d, c, e, ev] = await Promise.all([
        getActionDetail(actionId),
        getActionComments(actionId),
        getActionEvidence(actionId),
        getActionEvents(actionId),
      ]);
      setDetail(d);
      setComments(c);
      setEvidence(e);
      setEvents(ev);
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, [actionId]);

  useEffect(() => {
    if (open && actionId) {
      setTab('detail');
      fetchAll();
    }
  }, [open, actionId, fetchAll]);

  // V47 — Fetch preuves EFA si action OPERAT
  useEffect(() => {
    if (!open || !detail) { setProofsSummary(null); return; }
    if (!isOperatAction(detail)) { setProofsSummary(null); return; }
    const parsed = parseOperatSourceId(detail.source_id);
    if (!parsed?.efa_id) return;
    getTertiaireEfaProofs(parsed.efa_id)
      .then(setProofsSummary)
      .catch(() => setProofsSummary(null));
  }, [open, detail]);

  // Status change
  async function handleStatusChange(newStatus) {
    try {
      const resp = await patchAction(actionId, { status: newStatus });
      setDetail(prev => ({ ...prev, ...resp }));
      if (onUpdate) onUpdate(actionId, { status: STATUS_TO_FE[newStatus] || newStatus });
      toast('Statut mis a jour', 'success');
      // Refresh events
      const ev = await getActionEvents(actionId);
      setEvents(ev);
    } catch {
      toast('Erreur lors du changement de statut', 'error');
    }
  }

  // Add comment
  async function handleAddComment(e) {
    e.preventDefault();
    if (!commentBody.trim() || !commentAuthor.trim()) return;
    setSubmittingComment(true);
    try {
      await addActionComment(actionId, { author: commentAuthor.trim(), body: commentBody.trim() });
      setCommentBody('');
      const [c, ev] = await Promise.all([getActionComments(actionId), getActionEvents(actionId)]);
      setComments(c);
      setEvents(ev);
    } catch {
      toast('Erreur lors de l\'ajout du commentaire', 'error');
    } finally {
      setSubmittingComment(false);
    }
  }

  // Add evidence
  async function handleAddEvidence(e) {
    e.preventDefault();
    if (!evidenceLabel.trim()) return;
    setSubmittingEvidence(true);
    try {
      await addActionEvidence(actionId, {
        label: evidenceLabel.trim(),
        file_url: evidenceUrl.trim() || null,
        uploaded_by: commentAuthor.trim() || null,
      });
      setEvidenceLabel('');
      setEvidenceUrl('');
      const [ev, evts] = await Promise.all([getActionEvidence(actionId), getActionEvents(actionId)]);
      setEvidence(ev);
      setEvents(evts);
    } catch {
      toast('Erreur lors de l\'ajout de la piece', 'error');
    } finally {
      setSubmittingEvidence(false);
    }
  }

  // Save realized gain
  async function handleSaveRealized() {
    try {
      const val = parseFloat(realizedValue);
      if (isNaN(val)) return;
      const resp = await patchAction(actionId, { realized_gain_eur: val });
      setDetail(prev => ({ ...prev, ...resp }));
      setEditingRealized(false);
      if (onUpdate) onUpdate(actionId, { realized_gain_eur: val });
      const ev = await getActionEvents(actionId);
      setEvents(ev);
    } catch {
      toast('Erreur lors de la mise a jour du gain realise', 'error');
    }
  }

  if (!action) return null;

  const d = detail || action._backend || {};

  return (
    <Drawer open={open} onClose={onClose} title={d.title || action.titre || 'Detail'} wide>
      {/* Tab bar */}
      <div className="flex gap-1 mb-4 border-b border-gray-100 -mx-6 px-6">
        {TABS.map(t => {
          const Icon = t.icon;
          const count = t.id === 'comments' ? comments.length
            : t.id === 'evidence' ? evidence.length
            : t.id === 'history' ? events.length : null;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition ${
                tab === t.id
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <Icon size={13} />
              {t.label}
              {count != null && count > 0 && (
                <span className="ml-1 text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">{count}</span>
              )}
            </button>
          );
        })}
      </div>

      {loading && !detail ? (
        <div className="flex items-center justify-center py-12 text-gray-400 text-sm">Chargement...</div>
      ) : (
        <>
          {/* ── Tab: Detail ── */}
          {tab === 'detail' && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Type</p>
                  <span className="text-sm font-medium">{SOURCE_LABELS[d.source_type] || d.source_type}</span>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Priorite</p>
                  <Badge status={PRIORITY_BADGE[d.priority] || 'neutral'}>
                    {PRIORITY_LABEL[d.priority] || `P${d.priority}`}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Statut</p>
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${STATUS_PILL[d.status] || STATUS_PILL.open}`}>
                    {ACTION_STATUS_LABELS[STATUS_TO_FE[d.status]] || d.status}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Site</p>
                  <p className="text-sm font-medium">Site {d.site_id || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Categorie</p>
                  <p className="text-sm">{d.category || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Source</p>
                  <p className="text-xs text-gray-600">{d.source_type}:{d.source_id}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Echeance</p>
                  <p className="text-sm flex items-center gap-1">
                    <Clock size={14} /> {d.due_date || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Responsable</p>
                  <p className="text-sm flex items-center gap-1">
                    <User size={14} /> {d.owner || <span className="text-gray-400">Non assigne</span>}
                  </p>
                </div>
              </div>

              {d.description && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Description</p>
                  <p className="text-sm text-gray-700 whitespace-pre-line bg-gray-50 rounded-lg p-3">{d.description}</p>
                </div>
              )}

              {d.rationale && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Justification</p>
                  <p className="text-sm text-gray-700 whitespace-pre-line bg-gray-50 rounded-lg p-3">{d.rationale}</p>
                </div>
              )}

              {d.notes && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Notes</p>
                  <p className="text-sm text-gray-600 whitespace-pre-line">{d.notes}</p>
                </div>
              )}

              {/* V47 — Bloc Preuves OPERAT */}
              {isOperatAction(d) && (() => {
                const proofStatus = resolveProofStatus(proofsSummary);
                const badgeVariant = PROOF_STATUS_BADGE[proofStatus] || 'neutral';
                const closability = isActionClosable(d, proofsSummary, evidence.length);
                const proofLink = buildActionProofLink(d);
                const parsed = parseOperatSourceId(d.source_id);

                return (
                  <div className="border-t border-gray-100 pt-4 space-y-3" data-testid="operat-proof-bloc">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield size={14} className="text-blue-600" />
                      <p className="text-xs font-semibold text-gray-700">Preuves OPERAT</p>
                    </div>

                    {/* Statut preuve */}
                    <div className="flex items-center gap-3">
                      <Badge status={badgeVariant}>{PROOF_STATUS_LABELS[proofStatus]}</Badge>
                      {proofsSummary && (
                        <span className="text-xs text-gray-500">
                          {proofsSummary.validated_count || 0} validée(s) / {proofsSummary.expected_count || '—'} attendue(s)
                        </span>
                      )}
                    </div>

                    {/* Compteurs si disponibles */}
                    {proofsSummary && (
                      <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="p-2 bg-blue-50 rounded-lg">
                          <p className="text-lg font-bold text-blue-700">{proofsSummary.expected_count || 0}</p>
                          <p className="text-[10px] text-gray-500">Attendues</p>
                        </div>
                        <div className="p-2 bg-amber-50 rounded-lg">
                          <p className="text-lg font-bold text-amber-700">{proofsSummary.deposited_count || 0}</p>
                          <p className="text-[10px] text-gray-500">Déposées</p>
                        </div>
                        <div className="p-2 bg-green-50 rounded-lg">
                          <p className="text-lg font-bold text-green-700">{proofsSummary.validated_count || 0}</p>
                          <p className="text-[10px] text-gray-500">Validées</p>
                        </div>
                      </div>
                    )}

                    {/* CTAs */}
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => { onClose(); navigate(proofLink); }}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
                        data-testid="operat-proof-deposit-cta"
                      >
                        <FileCheck size={12} /> Déposer une preuve
                      </button>
                      {parsed?.efa_id && (
                        <button
                          onClick={() => { onClose(); navigate(`/conformite/tertiaire/efa/${parsed.efa_id}`); }}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 transition"
                        >
                          <ExternalLink size={12} /> Fiche EFA
                        </button>
                      )}
                    </div>

                    {/* Aide FR */}
                    <p className="text-[11px] text-gray-400 leading-relaxed bg-gray-50 rounded-lg p-2">
                      Une action OPERAT est considérée clôturable quand une preuve est liée et validée sur l'EFA,
                      ou qu'une pièce jointe est présente, ou que les notes contiennent [justifié].
                    </p>

                    {/* Avertissement si non clôturable */}
                    {!closability.closable && d.status !== 'done' && (
                      <div className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2" data-testid="operat-closability-warning">
                        <p className="font-medium mb-1">Clôture bloquée :</p>
                        <ul className="list-disc list-inside space-y-0.5">
                          {closability.raisons.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Status workflow buttons */}
              <div className="border-t border-gray-100 pt-4">
                <p className="text-xs text-gray-500 mb-2">Changer le statut</p>
                <div className="flex flex-wrap gap-2">
                  {STATUS_WORKFLOW.map(s => {
                    const isDone = s.value === 'done';
                    const operatBlocked = isDone && isOperatAction(d) && !isActionClosable(d, proofsSummary, evidence.length).closable;
                    return (
                      <button
                        key={s.value}
                        disabled={d.status === s.value || operatBlocked}
                        onClick={() => handleStatusChange(s.value)}
                        title={operatBlocked ? 'Preuve requise pour clôturer' : undefined}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                          d.status === s.value || operatBlocked
                            ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                            : 'bg-white border border-gray-200 hover:bg-blue-50 hover:border-blue-300 text-gray-700'
                        }`}
                      >
                        {s.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              {d.closed_at && (
                <p className="text-xs text-gray-400 mt-2">Fermee le {new Date(d.closed_at).toLocaleDateString('fr-FR')}</p>
              )}
            </div>
          )}

          {/* ── Tab: Impact ── */}
          {tab === 'impact' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-red-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Gain estime</p>
                  <p className="text-xl font-bold text-red-700">
                    {d.estimated_gain_eur != null ? `${d.estimated_gain_eur.toLocaleString()} EUR` : '—'}
                  </p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">Gain realise</p>
                  {editingRealized ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={realizedValue}
                        onChange={(e) => setRealizedValue(e.target.value)}
                        className="w-28 px-2 py-1 border border-gray-300 rounded text-sm"
                        autoFocus
                      />
                      <span className="text-xs text-gray-500">EUR</span>
                      <Button size="sm" onClick={handleSaveRealized}>OK</Button>
                      <button onClick={() => setEditingRealized(false)} className="text-xs text-gray-400 hover:text-gray-600">Annuler</button>
                    </div>
                  ) : (
                    <p
                      className="text-xl font-bold text-green-700 cursor-pointer hover:underline"
                      onClick={() => { setRealizedValue(String(d.realized_gain_eur || '')); setEditingRealized(true); }}
                      title="Cliquer pour modifier"
                    >
                      {d.realized_gain_eur != null ? `${d.realized_gain_eur.toLocaleString()} EUR` : '— (cliquer pour saisir)'}
                    </p>
                  )}
                </div>
              </div>

              {/* Delta */}
              {d.estimated_gain_eur != null && d.realized_gain_eur != null && (
                <div className={`p-3 rounded-lg text-sm font-medium ${
                  d.realized_gain_eur >= d.estimated_gain_eur ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                }`}>
                  Delta : {(d.realized_gain_eur - d.estimated_gain_eur).toLocaleString()} EUR
                  ({d.estimated_gain_eur > 0
                    ? `${((d.realized_gain_eur / d.estimated_gain_eur) * 100).toFixed(0)}% du gain estime`
                    : '—'})
                </div>
              )}

              {/* CO₂e savings */}
              {d.co2e_savings_est_kg != null && d.co2e_savings_est_kg > 0 && (
                <div className="p-3 bg-emerald-50 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">CO₂e evite (estimation)</p>
                  <p className="text-lg font-bold text-emerald-700">
                    {Math.round(d.co2e_savings_est_kg).toLocaleString()} kgCO₂e
                    {d.co2e_savings_est_kg >= 1000 && (
                      <span className="text-sm font-normal text-emerald-500 ml-1">
                        ({(d.co2e_savings_est_kg / 1000).toFixed(1)} t)
                      </span>
                    )}
                  </p>
                </div>
              )}

              {d.realized_at && (
                <p className="text-xs text-gray-500">Date de constatation : {d.realized_at}</p>
              )}

              {d.severity && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Severite source</p>
                  <Badge status={d.severity === 'critical' ? 'crit' : d.severity === 'high' ? 'warn' : 'info'}>
                    {d.severity}
                  </Badge>
                </div>
              )}
            </div>
          )}

          {/* ── Tab: Evidence ── */}
          {tab === 'evidence' && (
            <div className="space-y-4">
              {evidence.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Aucune piece jointe</p>
              ) : (
                <div className="space-y-2">
                  {evidence.map(ev => (
                    <div key={ev.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                      <Paperclip size={14} className="text-gray-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{ev.label}</p>
                        <p className="text-xs text-gray-400">
                          {ev.uploaded_by && `par ${ev.uploaded_by} — `}
                          {ev.created_at && new Date(ev.created_at).toLocaleDateString('fr-FR')}
                        </p>
                      </div>
                      {ev.file_url && (
                        <a
                          href={ev.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline shrink-0"
                        >
                          Ouvrir
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Add evidence form */}
              <form onSubmit={handleAddEvidence} className="border-t border-gray-100 pt-4 space-y-2">
                <p className="text-xs font-semibold text-gray-600 flex items-center gap-1"><Plus size={12} /> Ajouter une piece</p>
                <input
                  value={evidenceLabel}
                  onChange={(e) => setEvidenceLabel(e.target.value)}
                  placeholder="Libelle de la piece..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <input
                  value={evidenceUrl}
                  onChange={(e) => setEvidenceUrl(e.target.value)}
                  placeholder="URL du document (optionnel)"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Button size="sm" type="submit" disabled={submittingEvidence || !evidenceLabel.trim()}>
                  {submittingEvidence ? 'Ajout...' : 'Ajouter'}
                </Button>
              </form>
            </div>
          )}

          {/* ── Tab: Comments ── */}
          {tab === 'comments' && (
            <div className="space-y-4">
              {comments.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Aucun commentaire</p>
              ) : (
                <div className="space-y-2">
                  {comments.map(c => (
                    <div key={c.id} className="p-3 bg-gray-50 rounded-lg text-sm">
                      <p className="font-medium text-gray-700">
                        {c.author}
                        <span className="text-gray-400 font-normal ml-2">
                          {c.created_at && new Date(c.created_at).toLocaleDateString('fr-FR')}
                        </span>
                      </p>
                      <p className="text-gray-600 mt-1 whitespace-pre-line">{c.body}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Add comment form */}
              <form onSubmit={handleAddComment} className="border-t border-gray-100 pt-4 space-y-2">
                <input
                  value={commentAuthor}
                  onChange={(e) => setCommentAuthor(e.target.value)}
                  placeholder="Votre nom..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
                <textarea
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  placeholder="Ajouter un commentaire..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  required
                />
                <Button size="sm" type="submit" disabled={submittingComment || !commentBody.trim() || !commentAuthor.trim()}>
                  {submittingComment ? 'Envoi...' : 'Envoyer'}
                </Button>
              </form>
            </div>
          )}

          {/* ── Tab: History ── */}
          {tab === 'history' && (
            <div className="space-y-1">
              {events.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">Aucun evenement</p>
              ) : (
                events.map(ev => {
                  const Icon = EVENT_ICONS[ev.event_type] || Tag;
                  return (
                    <div key={ev.id} className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
                      <div className="mt-0.5 p-1.5 rounded-full bg-gray-100">
                        <Icon size={12} className="text-gray-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-800">
                          <span className="font-medium">{EVENT_LABELS[ev.event_type] || ev.event_type}</span>
                          {ev.actor && <span className="text-gray-500 ml-1">par {ev.actor}</span>}
                        </p>
                        {(ev.old_value || ev.new_value) && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            {ev.old_value && <span className="line-through mr-1">{ev.old_value}</span>}
                            {ev.old_value && ev.new_value && <ArrowRight size={10} className="inline mx-1" />}
                            {ev.new_value && <span className="font-medium">{ev.new_value}</span>}
                          </p>
                        )}
                      </div>
                      <span className="text-[10px] text-gray-400 shrink-0">
                        {ev.created_at && new Date(ev.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </>
      )}
    </Drawer>
  );
}
