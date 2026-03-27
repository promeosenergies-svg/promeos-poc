/**
 * PROMEOS — BACS Regulatory Panel
 * Affichage sobre et B2B du statut reglementaire BACS complet.
 * 6 axes : eligibilite, exigences R.175-3, exploitation, inspection, preuves, statut final.
 */
import { useState, useEffect } from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  FileText,
  Loader2,
} from 'lucide-react';
import {
  getBacsRegulatoryAssessment,
  createBacsRemediation,
  listBacsRemediations,
  listBacsExemptions,
  createBacsExemption,
  submitBacsExemption,
  approveBacsExemption,
  rejectBacsExemption,
  deleteBacsExemption,
} from '../services/api';

const STATUS_CONFIG = {
  not_applicable: { label: 'Non concerne', cls: 'bg-gray-100 text-gray-500', icon: null },
  potentially_in_scope: { label: 'A evaluer', cls: 'bg-blue-100 text-blue-700', icon: Clock },
  in_scope_incomplete: {
    label: 'Incomplet',
    cls: 'bg-amber-100 text-amber-700',
    icon: AlertTriangle,
  },
  review_required: { label: 'Revue requise', cls: 'bg-red-100 text-red-700', icon: AlertTriangle },
  ready_for_internal_review: {
    label: 'Pret pour revue',
    cls: 'bg-green-100 text-green-700',
    icon: ShieldCheck,
  },
  not_evaluated: { label: 'Non évalué', cls: 'bg-gray-100 text-gray-500', icon: null },
  exempted: { label: 'Dérogation approuvée', cls: 'bg-blue-100 text-blue-700', icon: ShieldCheck },
};

const REQ_STATUS_ICON = {
  ok: { icon: CheckCircle2, cls: 'text-green-600' },
  partial: { icon: AlertTriangle, cls: 'text-amber-500' },
  absent: { icon: XCircle, cls: 'text-red-500' },
  not_demonstrated: { icon: XCircle, cls: 'text-gray-400' },
};

const ACTION_STATUS = {
  open: { label: 'Ouvert', cls: 'bg-red-100 text-red-700' },
  in_progress: { label: 'En cours', cls: 'bg-amber-100 text-amber-700' },
  ready_for_review: { label: 'A revoir', cls: 'bg-blue-100 text-blue-700' },
  closed: { label: 'Clos', cls: 'bg-green-100 text-green-700' },
};

const PROOF_STATUS = {
  missing: { label: 'Manquante', cls: 'text-red-600' },
  uploaded: { label: 'Fournie', cls: 'text-blue-600' },
  accepted: { label: 'Validée', cls: 'text-green-600' },
  rejected: { label: 'Rejetée', cls: 'text-red-600' },
};

const EXEMPTION_STATUS = {
  draft: { label: 'Brouillon', cls: 'bg-gray-100 text-gray-600' },
  submitted: { label: 'Soumise', cls: 'bg-blue-100 text-blue-700' },
  approved: { label: 'Approuvée', cls: 'bg-green-100 text-green-700' },
  rejected: { label: 'Rejetée', cls: 'bg-red-100 text-red-700' },
  expired: { label: 'Expirée', cls: 'bg-amber-100 text-amber-700' },
};

const EXEMPTION_TYPE_LABELS = {
  tri_non_viable: 'TRI non viable (> 10 ans)',
  impossibilite_technique: 'Impossibilité technique',
  patrimoine_historique: 'Patrimoine historique',
  mise_en_vente: 'Mise en vente / démolition',
};

export default function BacsRegulatoryPanel({ siteId }) {
  const [data, setData] = useState(null);
  const [actions, setActions] = useState([]);
  const [exemptions, setExemptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [errMsg, setErrMsg] = useState(null);
  const [showExemptionForm, setShowExemptionForm] = useState(false);
  const [exemptionForm, setExemptionForm] = useState({
    exemption_type: 'tri_non_viable',
    motif_detaille: '',
    tri_annees: '',
    cout_installation_eur: '',
    economies_annuelles_eur: '',
  });

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    setErrMsg(null);
    Promise.all([
      getBacsRegulatoryAssessment(siteId).catch(() => null),
      listBacsRemediations(siteId).catch(() => ({ actions: [] })),
      listBacsExemptions(siteId).catch(() => ({ exemptions: [] })),
    ])
      .then(([assessment, remActions, exemptionData]) => {
        setData(assessment);
        setActions(remActions?.actions || []);
        setExemptions(exemptionData?.exemptions || []);
      })
      .finally(() => setLoading(false));
  }, [siteId]);

  const handleCreateAction = async (rem) => {
    setCreating(true);
    setErrMsg(null);
    try {
      const result = await createBacsRemediation(siteId, {
        blocker_code: rem.cause.replace(/\s/g, '_').toLowerCase().slice(0, 100),
        blocker_cause: rem.cause,
        expected_action: rem.action,
        expected_proof_type: rem.proof,
        priority: rem.priority,
      });
      setActions((prev) => [result, ...prev]);
    } catch (e) {
      setErrMsg(
        e?.response?.data?.detail || e?.message || "Erreur lors de la création de l'action"
      );
    } finally {
      setCreating(false);
    }
  };

  const handleCreateExemption = async () => {
    setCreating(true);
    setErrMsg(null);
    try {
      const payload = {
        exemption_type: exemptionForm.exemption_type,
        motif_detaille: exemptionForm.motif_detaille,
      };
      if (exemptionForm.tri_annees) payload.tri_annees = parseFloat(exemptionForm.tri_annees);
      if (exemptionForm.cout_installation_eur)
        payload.cout_installation_eur = parseFloat(exemptionForm.cout_installation_eur);
      if (exemptionForm.economies_annuelles_eur)
        payload.economies_annuelles_eur = parseFloat(exemptionForm.economies_annuelles_eur);
      const result = await createBacsExemption(siteId, payload);
      setExemptions((prev) => [result, ...prev]);
      setShowExemptionForm(false);
      setExemptionForm({
        exemption_type: 'tri_non_viable',
        motif_detaille: '',
        tri_annees: '',
        cout_installation_eur: '',
        economies_annuelles_eur: '',
      });
    } catch (e) {
      setErrMsg(
        e?.response?.data?.detail || e?.message || 'Erreur lors de la création de la dérogation'
      );
    } finally {
      setCreating(false);
    }
  };

  const handleExemptionAction = async (exemptionId, action) => {
    setErrMsg(null);
    try {
      let result;
      if (action === 'submit') result = await submitBacsExemption(exemptionId);
      else if (action === 'approve') result = await approveBacsExemption(exemptionId);
      else if (action === 'reject') result = await rejectBacsExemption(exemptionId);
      else if (action === 'delete') {
        await deleteBacsExemption(exemptionId);
        setExemptions((prev) => prev.filter((e) => e.id !== exemptionId));
        return;
      }
      if (result) {
        setExemptions((prev) => prev.map((e) => (e.id === exemptionId ? result : e)));
      }
    } catch (e) {
      setErrMsg(
        e?.response?.data?.detail || e?.message || "Erreur lors de l'action sur la dérogation"
      );
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Loader2 size={20} className="animate-spin mx-auto" />
      </div>
    );
  }

  if (!data || data.final_status === 'not_evaluated') {
    return (
      <div className="p-4 text-center text-sm text-gray-400">Aucun actif BACS pour ce site</div>
    );
  }

  const st = STATUS_CONFIG[data.final_status] || STATUS_CONFIG.not_evaluated;
  const StIcon = st.icon;
  const elig = data.eligibility || {};
  const func = data.functional_requirements || {};
  const expl = data.exploitation || {};
  const insp = data.inspection || {};
  const proofs = data.proofs || {};

  return (
    <div className="space-y-4">
      {/* Bandeau erreur */}
      {errMsg && (
        <div className="flex items-center gap-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
          <AlertTriangle size={14} className="shrink-0" />
          <span>{errMsg}</span>
          <button
            type="button"
            onClick={() => setErrMsg(null)}
            className="ml-auto text-red-400 hover:text-red-600"
          >
            &times;
          </button>
        </div>
      )}
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
          BACS Reglementaire
        </h3>
        <div className="flex items-center gap-2">
          <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${st.cls}`}>
            {StIcon && <StIcon size={12} className="inline mr-1" />}
            {st.label}
          </span>
        </div>
      </div>

      {/* Aide a la conformite banner */}
      <div className="flex items-start gap-2 p-2.5 bg-amber-50 border border-amber-200 rounded-md">
        <AlertTriangle size={14} className="text-amber-600 mt-0.5 shrink-0" />
        <p className="text-[11px] text-amber-700">
          <span className="font-semibold">Aide a la conformite</span> — PROMEOS ne certifie pas la
          conformite BACS. Ce panneau aide a preparer la revue interne.
        </p>
      </div>

      {/* Eligibilite */}
      <Section title="Perimetre">
        <Row
          label="Assujetti"
          value={elig.in_scope === true ? 'Oui' : elig.in_scope === false ? 'Non' : 'A verifier'}
        />
        {elig.tier && <Row label="Seuil" value={elig.tier} />}
        {elig.putile_kw && <Row label="Putile" value={`${Math.round(elig.putile_kw)} kW`} />}
        {elig.deadline && (
          <Row label="Échéance" value={elig.deadline} warn={new Date(elig.deadline) < new Date()} />
        )}
        {elig.tri_exemption_possible && <Row label="Exemption TRI" value="Possible (> 10 ans)" />}
      </Section>

      {/* Exigences fonctionnelles */}
      <Section title={`Exigences R.175-3 (${func.ok_count || 0}/${func.total || 10})`}>
        {func.requirements &&
          Object.entries(func.requirements).map(([key, req]) => {
            const cfg = REQ_STATUS_ICON[req.status] || REQ_STATUS_ICON.not_demonstrated;
            const Icon = cfg.icon;
            return (
              <div key={key} className="flex items-center justify-between py-0.5">
                <span className="text-xs text-gray-600">{req.label}</span>
                <Icon size={14} className={cfg.cls} />
              </div>
            );
          })}
      </Section>

      {/* Exploitation */}
      <Section title="Exploitation / Maintenance">
        {expl.assessed ? (
          <>
            <Row
              label="Consignes ecrites"
              value={expl.written_procedures}
              ok={expl.written_procedures === 'ok'}
            />
            <Row
              label="Formation exploitant"
              value={expl.operator_trained ? `Oui (${expl.training_date || ''})` : 'Non'}
              ok={expl.operator_trained}
            />
            <Row
              label="Points de controle"
              value={expl.control_points_defined ? 'Definis' : 'Non definis'}
              ok={expl.control_points_defined}
            />
          </>
        ) : (
          <p className="text-xs text-red-500">Non evaluee</p>
        )}
      </Section>

      {/* Inspection */}
      <Section title="Inspection">
        {insp.has_inspection ? (
          <>
            <Row label="Derniere" value={insp.last_date || '—'} />
            <Row label="Prochaine" value={insp.next_due || '—'} warn={insp.overdue} />
            {insp.overdue && (
              <p className="text-[11px] text-red-600 font-medium">Inspection en retard</p>
            )}
            <Row
              label="Findings critiques"
              value={String(insp.critical_findings)}
              warn={insp.critical_findings > 0}
            />
            {insp.report_compliant === false && (
              <p className="text-[11px] text-red-600">Rapport non conforme</p>
            )}
          </>
        ) : (
          <p className="text-xs text-red-500">Aucune inspection completee</p>
        )}
      </Section>

      {/* Preuves */}
      <Section title={`Preuves (${proofs.count || 0} / ${proofs.expected_types?.length || 4})`}>
        {proofs.missing_types?.length > 0 ? (
          <div className="space-y-1">
            {proofs.missing_types.map((t) => (
              <div key={t} className="flex items-center gap-1.5 text-xs text-red-600">
                <XCircle size={12} /> {t}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-green-600">Toutes les preuves attendues sont presentes</p>
        )}
      </Section>

      {/* Derogation BACS (Art. R.175-6) */}
      <Section title={`Derogation (${exemptions.length})`}>
        {exemptions.length > 0 ? (
          <div className="space-y-2">
            {exemptions.map((ex) => {
              const statusCfg = EXEMPTION_STATUS[ex.status] || EXEMPTION_STATUS.draft;
              return (
                <div
                  key={ex.id}
                  className="p-2 rounded-md bg-gray-50 border border-gray-100 space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-800">
                      {EXEMPTION_TYPE_LABELS[ex.exemption_type] || ex.exemption_type}
                    </span>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${statusCfg.cls}`}
                    >
                      {statusCfg.label}
                    </span>
                  </div>
                  <p className="text-[11px] text-gray-600 line-clamp-2">{ex.motif_detaille}</p>
                  {ex.tri_annees && (
                    <p className="text-[10px] text-gray-400">
                      TRI: {ex.tri_annees} ans
                      {ex.cout_installation_eur &&
                        ` | Cout: ${Math.round(ex.cout_installation_eur).toLocaleString()} EUR`}
                      {ex.economies_annuelles_eur &&
                        ` | Eco: ${Math.round(ex.economies_annuelles_eur).toLocaleString()} EUR/an`}
                    </p>
                  )}
                  {ex.date_expiration && (
                    <p className="text-[10px] text-gray-400">Expire: {ex.date_expiration}</p>
                  )}
                  {ex.decision_reference && (
                    <p className="text-[10px] text-gray-400">Ref: {ex.decision_reference}</p>
                  )}
                  <div className="flex items-center gap-1.5 pt-1">
                    {ex.status === 'draft' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleExemptionAction(ex.id, 'submit')}
                          className="px-2 py-0.5 text-[10px] font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100"
                        >
                          Soumettre
                        </button>
                        <button
                          type="button"
                          onClick={() => handleExemptionAction(ex.id, 'delete')}
                          className="px-2 py-0.5 text-[10px] font-medium text-red-600 bg-red-50 rounded hover:bg-red-100"
                        >
                          Supprimer
                        </button>
                      </>
                    )}
                    {ex.status === 'submitted' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleExemptionAction(ex.id, 'approve')}
                          className="px-2 py-0.5 text-[10px] font-medium text-green-700 bg-green-50 rounded hover:bg-green-100"
                        >
                          Approuver
                        </button>
                        <button
                          type="button"
                          onClick={() => handleExemptionAction(ex.id, 'reject')}
                          className="px-2 py-0.5 text-[10px] font-medium text-red-600 bg-red-50 rounded hover:bg-red-100"
                        >
                          Rejeter
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-gray-400">Aucune derogation</p>
        )}
        {elig.tri_exemption_possible && !showExemptionForm && (
          <button
            type="button"
            onClick={() => setShowExemptionForm(true)}
            className="mt-2 px-2.5 py-1 text-[11px] font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 w-full"
          >
            Demander une derogation
          </button>
        )}
        {showExemptionForm && (
          <div className="mt-2 p-2.5 bg-blue-50 border border-blue-200 rounded-md space-y-2">
            <p className="text-[11px] font-semibold text-blue-800">Nouvelle derogation</p>
            <select
              value={exemptionForm.exemption_type}
              onChange={(e) => setExemptionForm((f) => ({ ...f, exemption_type: e.target.value }))}
              className="w-full text-xs p-1.5 border rounded"
            >
              <option value="tri_non_viable">TRI non viable (&gt; 10 ans)</option>
              <option value="impossibilite_technique">Impossibilité technique</option>
              <option value="patrimoine_historique">Patrimoine historique</option>
              <option value="mise_en_vente">Mise en vente / démolition</option>
            </select>
            <textarea
              placeholder="Motif détaillé..."
              value={exemptionForm.motif_detaille}
              onChange={(e) => setExemptionForm((f) => ({ ...f, motif_detaille: e.target.value }))}
              className="w-full text-xs p-1.5 border rounded h-16"
            />
            {exemptionForm.exemption_type === 'tri_non_viable' && (
              <div className="grid grid-cols-3 gap-1.5">
                <input
                  type="number"
                  placeholder="TRI (annees)"
                  value={exemptionForm.tri_annees}
                  onChange={(e) => setExemptionForm((f) => ({ ...f, tri_annees: e.target.value }))}
                  className="text-xs p-1.5 border rounded"
                />
                <input
                  type="number"
                  placeholder="Cout install. (EUR)"
                  value={exemptionForm.cout_installation_eur}
                  onChange={(e) =>
                    setExemptionForm((f) => ({
                      ...f,
                      cout_installation_eur: e.target.value,
                    }))
                  }
                  className="text-xs p-1.5 border rounded"
                />
                <input
                  type="number"
                  placeholder="Eco/an (EUR)"
                  value={exemptionForm.economies_annuelles_eur}
                  onChange={(e) =>
                    setExemptionForm((f) => ({
                      ...f,
                      economies_annuelles_eur: e.target.value,
                    }))
                  }
                  className="text-xs p-1.5 border rounded"
                />
              </div>
            )}
            <div className="flex gap-1.5">
              <button
                type="button"
                onClick={handleCreateExemption}
                disabled={creating || !exemptionForm.motif_detaille}
                className="px-2.5 py-1 text-[11px] font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                Creer brouillon
              </button>
              <button
                type="button"
                onClick={() => setShowExemptionForm(false)}
                className="px-2.5 py-1 text-[11px] font-medium text-gray-600 bg-gray-100 rounded hover:bg-gray-200"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </Section>

      {/* Remediation actionnable */}
      {data.remediation?.length > 0 && (
        <Section title={`Remediation (${data.remediation.length} action(s))`}>
          {data.remediation.map((r, i) => {
            const prioColor =
              r.priority === 'critical'
                ? 'bg-red-100 text-red-700'
                : r.priority === 'high'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-gray-100 text-gray-600';
            // Chercher si une action existe deja pour ce blocker
            const existingAction = actions.find(
              (a) => a.blocker_cause === r.cause && a.status !== 'closed'
            );
            return (
              <div key={i} className="p-2 rounded-md bg-gray-50 border border-gray-100 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-800">{r.cause}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${prioColor}`}>
                    {r.priority}
                  </span>
                </div>
                <p className="text-[11px] text-gray-600">{r.action}</p>
                <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
                  <FileText size={10} />
                  <span>Preuve : {r.proof}</span>
                </div>
                {/* CTA ou statut action */}
                {existingAction ? (
                  <div className="flex items-center gap-2 pt-1">
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        ACTION_STATUS[existingAction.status]?.cls || 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {ACTION_STATUS[existingAction.status]?.label || existingAction.status}
                    </span>
                    {existingAction.proof_review_status && (
                      <span
                        className={`text-[10px] ${
                          PROOF_STATUS[existingAction.proof_review_status]?.cls || 'text-gray-400'
                        }`}
                      >
                        Preuve :{' '}
                        {PROOF_STATUS[existingAction.proof_review_status]?.label ||
                          existingAction.proof_review_status}
                      </span>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleCreateAction(r)}
                    disabled={creating}
                    className="mt-1 px-2.5 py-1 text-[11px] font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50"
                  >
                    Creer action corrective
                  </button>
                )}
              </div>
            );
          })}
        </Section>
      )}

      {/* Blockers (residuels) */}
      {data.blockers?.length > 0 && (
        <Section title="Blockers">
          {data.blockers.map((b, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-red-700 py-0.5">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              <span>{b}</span>
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="border-t border-gray-100 pt-2">
      <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
        {title}
      </p>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function Row({ label, value, ok, warn }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-600">{label}</span>
      <span
        className={`font-medium ${warn ? 'text-red-600' : ok ? 'text-green-700' : 'text-gray-700'}`}
      >
        {value}
      </span>
    </div>
  );
}
