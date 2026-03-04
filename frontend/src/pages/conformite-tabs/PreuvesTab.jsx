/**
 * PreuvesTab — Extracted from ConformitePage (V92 split)
 * Tab "Preuves & Rapports" with ProofSection per obligation.
 */
import { FileText, Upload, FolderOpen } from 'lucide-react';
import { Card, CardBody, Badge, EmptyState, TrustBadge } from '../../ui';
import { STATUT_LABELS } from '../../domain/compliance/complianceLabels.fr';

const STATUT_CONFIG = {
  non_conforme: { label: STATUT_LABELS.non_conforme, border: 'border-red-200' },
  a_risque: { label: STATUT_LABELS.a_risque, border: 'border-amber-200' },
  a_qualifier: { label: STATUT_LABELS.a_qualifier, border: 'border-blue-200' },
  conforme: { label: STATUT_LABELS.conforme, border: 'border-green-200' },
  hors_perimetre: { label: STATUT_LABELS.hors_perimetre, border: 'border-gray-200' },
};

function ProofSection({ obligation, files, onUpload }) {
  const cfg = STATUT_CONFIG[obligation.statut] || STATUT_CONFIG.a_qualifier;

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
        {files.length > 0 && (
          <div className="space-y-1 mb-3">
            {files.map((f, i) => (
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
        {files.length === 0 && (
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
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <FolderOpen size={16} className="text-indigo-600" />
        <h3 className="text-sm font-semibold text-gray-700">
          Preuves par obligation ({obligations.length})
        </h3>
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
