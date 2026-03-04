/**
 * ExecutionTab — Extracted from ConformitePage (V92 split)
 * Tab "Plan d'exécution" with ActionRow per finding.
 */
import { useState } from 'react';
import {
  ChevronRight,
  Plus,
  ExternalLink,
  CheckCircle,
  UserCheck,
  CheckCircle2,
  Eye,
  FileText,
  ClipboardList,
} from 'lucide-react';
import { Button, EmptyState } from '../../ui';
import { useExpertMode } from '../../contexts/ExpertModeContext';
import { track } from '../../services/tracker';
import {
  REG_LABELS,
  WORKFLOW_LABELS,
  RULE_LABELS,
  RULE_NEXT_STEPS,
  RULE_EXPECTED_PROOFS,
} from '../../domain/compliance/complianceLabels.fr';

const WORKFLOW_CONFIG = {
  open: { label: WORKFLOW_LABELS.open, color: 'bg-red-50 text-red-700' },
  ack: { label: WORKFLOW_LABELS.ack, color: 'bg-amber-50 text-amber-700' },
  resolved: { label: WORKFLOW_LABELS.resolved, color: 'bg-green-50 text-green-700' },
  false_positive: { label: WORKFLOW_LABELS.false_positive, color: 'bg-gray-100 text-gray-500' },
};

function WorkflowBadge({ status }) {
  const cfg = WORKFLOW_CONFIG[status] || WORKFLOW_CONFIG.open;
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function ActionRow({ finding, onWorkflowAction, onCreateAction, onAuditFinding }) {
  const { isExpert } = useExpertMode();
  const ruleInfo = RULE_LABELS[finding.rule_id];
  const nextSteps = RULE_NEXT_STEPS[finding.rule_id] || [];
  const expectedProofs = RULE_EXPECTED_PROOFS[finding.rule_id] || [];
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg hover:bg-gray-50/50 transition-colors">
      <div className="flex items-center gap-3 px-4 py-3">
        <span
          className={`w-2.5 h-2.5 rounded-full shrink-0 ${finding.status === 'NOK' ? 'bg-red-500' : finding.status === 'UNKNOWN' ? 'bg-blue-400' : 'bg-amber-500'}`}
        />
        <button onClick={() => setExpanded(!expanded)} className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium text-gray-900 truncate">
            {finding.site_nom} —{' '}
            {ruleInfo?.title_fr || REG_LABELS[finding.regulation] || finding.regulation}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {ruleInfo?.why_fr || finding.evidence || 'Non conforme'}
          </p>
          {isExpert && (
            <p className="text-[10px] text-gray-400 font-mono mt-0.5">{finding.rule_id}</p>
          )}
        </button>
        {isExpert ? (
          <>
            <WorkflowBadge status={finding.insight_status} />
            <button
              onClick={() => onAuditFinding(finding.id)}
              className="text-xs text-indigo-500 hover:text-indigo-700 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
              title="Voir les détails"
            >
              <Eye size={12} /> Détails
            </button>
            {finding.insight_status === 'open' && (
              <button
                onClick={() => onWorkflowAction(finding.id, 'ack')}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
              >
                <UserCheck size={12} /> Prendre en charge
              </button>
            )}
            {finding.insight_status === 'ack' && (
              <button
                onClick={() => onWorkflowAction(finding.id, 'resolved')}
                className="text-xs text-green-600 hover:text-green-800 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-green-50 transition-colors"
              >
                <CheckCircle2 size={12} /> Résolu
              </button>
            )}
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 font-medium shrink-0">
              Recommandation
            </span>
          </>
        ) : (
          <>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                finding.status === 'NOK' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              {finding.status === 'NOK' ? WORKFLOW_LABELS.open : WORKFLOW_LABELS.ack}
            </span>
            <button
              onClick={() => onAuditFinding(finding.id)}
              className="text-xs text-indigo-500 hover:text-indigo-700 font-medium flex items-center gap-1 px-2 py-1 rounded hover:bg-indigo-50 transition-colors"
              title="Voir les détails"
            >
              <Eye size={12} /> Détails
            </button>
          </>
        )}
        {finding.status === 'NOK' && (
          <Button size="sm" variant="secondary" onClick={() => onCreateAction(finding)}>
            <Plus size={12} /> Créer une action
          </Button>
        )}
      </div>

      {expanded && (nextSteps.length > 0 || expectedProofs.length > 0 || isExpert) && (
        <div className="px-4 pb-3 pt-1 border-t border-gray-100 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            {nextSteps.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1">Prochaines étapes</p>
                <ul className="text-xs text-gray-600 space-y-0.5">
                  {nextSteps.map((step, i) => (
                    <li key={i} className="flex items-start gap-1">
                      <ChevronRight size={10} className="shrink-0 mt-0.5 text-blue-400" />
                      {step}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {expectedProofs.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1">Preuves attendues</p>
                <ul className="text-xs text-gray-600 space-y-0.5">
                  {expectedProofs.map((proof, i) => (
                    <li key={i} className="flex items-start gap-1">
                      <FileText size={10} className="shrink-0 mt-0.5 text-indigo-400" />
                      {proof}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          {isExpert && (
            <div className="p-2 bg-gray-50 rounded text-[10px] text-gray-400 space-y-1">
              <p className="font-mono">rule_id: {finding.rule_id}</p>
              {finding.source_ref && <p>source_ref: {finding.source_ref}</p>}
              {finding.inputs && (
                <pre className="whitespace-pre-wrap text-[10px] text-gray-400 max-h-24 overflow-y-auto">
                  {JSON.stringify(finding.inputs, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ExecutionTab({
  actionableFindings,
  emptyReason,
  handleWorkflowAction,
  handleCreateFromFinding,
  setAuditFindingId,
  openActionDrawer,
  navigate,
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ClipboardList size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">
            Recommandations ({actionableFindings.length})
          </h3>
        </div>
        {actionableFindings.length > 0 && (
          <Button variant="secondary" size="sm" onClick={() => openActionDrawer({})}>
            <Plus size={14} /> Nouvelle action
          </Button>
        )}
      </div>

      {actionableFindings.length === 0 ? (
        <EmptyState
          icon={CheckCircle}
          title="Aucune action en attente"
          text={
            emptyReason === 'ALL_COMPLIANT'
              ? 'Toutes les obligations sont conformes. Aucune action requise.'
              : 'Lancez une évaluation pour identifier les actions nécessaires.'
          }
        />
      ) : (
        <div className="space-y-2">
          {actionableFindings.map((f) => (
            <ActionRow
              key={f.id}
              finding={f}
              onWorkflowAction={handleWorkflowAction}
              onCreateAction={handleCreateFromFinding}
              onAuditFinding={setAuditFindingId}
            />
          ))}
        </div>
      )}

      <Button
        variant="secondary"
        size="sm"
        onClick={() => {
          navigate('/anomalies?tab=actions');
          track('conformite_goto_plan_actions');
        }}
      >
        <ExternalLink size={14} /> Voir le plan d'actions complet
      </Button>
    </div>
  );
}
