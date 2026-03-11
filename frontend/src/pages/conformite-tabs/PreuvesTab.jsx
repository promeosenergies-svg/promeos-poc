/**
 * PreuvesTab — Extracted from ConformitePage (V92 split)
 * Tab "Preuves & Rapports" with ProofSection per obligation.
 * B3: Bridge preuves minimal — preuves attendues vs déposées, statut clair.
 */
import { FileText, Upload, FolderOpen, CheckCircle2, AlertCircle, Clock } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState, TrustBadge } from '../../ui';
import { STATUT_LABELS, RULE_EXPECTED_PROOFS } from '../../domain/compliance/complianceLabels.fr';

const STATUT_CONFIG = {
  non_conforme: { label: STATUT_LABELS.non_conforme, border: 'border-red-200' },
  a_risque: { label: STATUT_LABELS.a_risque, border: 'border-amber-200' },
  a_qualifier: { label: STATUT_LABELS.a_qualifier, border: 'border-blue-200' },
  conforme: { label: STATUT_LABELS.conforme, border: 'border-green-200' },
  hors_perimetre: { label: STATUT_LABELS.hors_perimetre, border: 'border-gray-200' },
};

/** B3 — Determine proof status for an obligation */
function getProofStatus(files, expectedCount) {
  if (expectedCount === 0) return { label: 'Non requis', icon: null, color: 'text-gray-400' };
  if (files.length >= expectedCount)
    return { label: 'Complètes', icon: CheckCircle2, color: 'text-green-600' };
  if (files.length > 0) return { label: 'Partielles', icon: Clock, color: 'text-amber-600' };
  return { label: 'Manquantes', icon: AlertCircle, color: 'text-red-600' };
}

function ProofSection({ obligation, files, onUpload }) {
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_qualifier;

  // B3 — Expected proofs from YAML labels
  const mainRuleId = obligation.findings?.[0]?.rule_id;
  const expectedProofs = mainRuleId ? RULE_EXPECTED_PROOFS[mainRuleId] || [] : [];
  const proofStatus = getProofStatus(files, expectedProofs.length);
  const ProofIcon = proofStatus.icon;

  return (
    <Card className={`border-l-4 ${cfg.border}`}>
      <CardBody>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h4 className="text-sm font-semibold text-gray-900">{obligation.regulation}</h4>
            <p className="text-xs text-gray-500">
              {obligation.sites_concernes} site(s) concerné(s)
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* B3 — Proof status badge */}
            {ProofIcon && (
              <span
                className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                  proofStatus.color === 'text-green-600'
                    ? 'bg-green-50'
                    : proofStatus.color === 'text-amber-600'
                      ? 'bg-amber-50'
                      : 'bg-red-50'
                } ${proofStatus.color}`}
              >
                <ProofIcon size={12} />
                {proofStatus.label}
              </span>
            )}
            <Badge
              status={
                obligation.statut === 'conforme'
                  ? 'ok'
                  : obligation.statut === 'non_conforme'
                    ? 'crit'
                    : obligation.statut === 'a_qualifier'
                      ? 'info'
                      : 'warn'
              }
            >
              {cfg.label}
            </Badge>
          </div>
        </div>

        {/* B3 — Expected vs deposited proof matrix */}
        {expectedProofs.length > 0 && (
          <div className="mb-3 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-gray-600 uppercase mb-2">
              Preuves attendues ({files.length}/{expectedProofs.length})
            </p>
            <div className="space-y-1.5">
              {expectedProofs.map((proof, i) => {
                // Simple matching: a file is linked to a proof if names roughly match
                const matched = files.find(
                  (f) =>
                    f.name.toLowerCase().includes(proof.toLowerCase().slice(0, 10)) ||
                    i < files.length
                );
                const isDeposited = i < files.length;
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    {isDeposited ? (
                      <CheckCircle2 size={12} className="text-green-500 shrink-0" />
                    ) : (
                      <AlertCircle size={12} className="text-gray-300 shrink-0" />
                    )}
                    <span className={`flex-1 ${isDeposited ? 'text-gray-700' : 'text-gray-400'}`}>
                      {proof}
                    </span>
                    {isDeposited && files[i] && (
                      <span className="text-green-600 font-medium truncate max-w-[200px]">
                        {files[i].name}
                      </span>
                    )}
                    {!isDeposited && <span className="text-gray-400 italic">Non déposée</span>}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Deposited files (extra, beyond expected) */}
        {files.length > expectedProofs.length && (
          <div className="space-y-1 mb-3">
            <p className="text-xs text-gray-500 font-medium mb-1">Fichiers supplémentaires</p>
            {files.slice(expectedProofs.length).map((f, i) => (
              <div
                key={i}
                className="flex items-center gap-2 text-sm text-gray-700 bg-gray-50 px-3 py-2 rounded"
              >
                <FileText size={14} className="text-indigo-500 shrink-0" />
                <span className="truncate flex-1">{f.name}</span>
                <span className="text-xs text-gray-400 whitespace-nowrap">{f.date}</span>
              </div>
            ))}
          </div>
        )}

        {/* No expected proofs and no files */}
        {expectedProofs.length === 0 && files.length === 0 && (
          <div className="mb-3">
            {obligation.statut === 'conforme' && (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 font-medium mb-1">
                Preuve non jointe
              </span>
            )}
            <p className="text-xs text-gray-400">
              {obligation.statut === 'conforme'
                ? 'Vous pouvez joindre un justificatif pour renforcer la conformité.'
                : 'Aucune preuve jointe pour cette obligation.'}
            </p>
          </div>
        )}

        <label className="inline-flex items-center gap-2 cursor-pointer text-sm text-indigo-600 hover:text-indigo-800 transition font-medium">
          <Upload size={14} />
          Ajouter un fichier
          <input
            type="file"
            className="sr-only"
            onChange={(e) => {
              if (e.target.files[0]) onUpload(obligation.id, e.target.files[0]);
              e.target.value = '';
            }}
          />
        </label>
      </CardBody>
    </Card>
  );
}

export default function PreuvesTab({ obligations, proofFiles, handleUploadProof }) {
  // B3 — Summary counters
  const totalExpected = obligations.reduce((sum, o) => {
    const ruleId = o.findings?.[0]?.rule_id;
    return sum + (ruleId ? (RULE_EXPECTED_PROOFS[ruleId] || []).length : 0);
  }, 0);
  const totalDeposited = Object.values(proofFiles).reduce((s, f) => s + f.length, 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <FolderOpen size={16} className="text-indigo-600" />
        <h3 className="text-sm font-semibold text-gray-700">
          Preuves par obligation ({obligations.length})
        </h3>
        {totalExpected > 0 && (
          <span className="text-xs text-gray-500 ml-auto">
            {totalDeposited}/{totalExpected} preuve{totalExpected > 1 ? 's' : ''} déposée
            {totalDeposited > 1 ? 's' : ''}
          </span>
        )}
      </div>

      {obligations.length === 0 ? (
        <EmptyState
          icon={FolderOpen}
          title="Aucune obligation"
          text="Lancez une évaluation pour voir les obligations et joindre des preuves."
        />
      ) : (
        <>
          {obligations.map((o) => (
            <ProofSection
              key={o.id}
              obligation={o}
              files={proofFiles[o.id] || []}
              onUpload={handleUploadProof}
            />
          ))}
        </>
      )}

      <TrustBadge
        source="Preuves locales"
        period="Téléversement local (non enregistré)"
        confidence="low"
      />
    </div>
  );
}
