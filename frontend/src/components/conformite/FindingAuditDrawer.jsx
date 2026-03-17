/**
 * Finding Audit Drawer — displays detailed finding information in a side panel.
 */
import { useState, useEffect } from 'react';
import { Drawer, Explain } from '../../ui';
import { useExpertMode } from '../../contexts/ExpertModeContext';
import {
  STATUT_LABELS,
  BACKEND_STATUS_MAP,
  WORKFLOW_LABELS,
  SEVERITY_LABELS,
  DRAWER_LABELS,
} from '../../domain/compliance/complianceLabels.fr';
import { getFindingDetail } from '../../services/api';

export default function FindingAuditDrawer({ findingId, onClose }) {
  const { isExpert } = useExpertMode();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!findingId) return;
    setLoading(true);
    getFindingDetail(findingId)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [findingId]);

  return (
    <Drawer
      open={!!findingId}
      onClose={onClose}
      title={<Explain term="finding">{DRAWER_LABELS.finding_title}</Explain>}
      wide
    >
      {loading ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.loading}</div>
      ) : !detail ? (
        <div className="py-12 text-center text-gray-400">{DRAWER_LABELS.not_found}</div>
      ) : (
        <div className="space-y-5">
          {/* Identity */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
              {DRAWER_LABELS.identity}
            </p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {isExpert && (
                <div>
                  <span className="text-gray-500">{DRAWER_LABELS.rule_id} :</span>{' '}
                  <span className="font-mono font-medium">{detail.rule_id}</span>
                </div>
              )}
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.regulation} :</span>{' '}
                <span className="font-medium">{detail.regulation}</span>
              </div>
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.status} :</span>{' '}
                <span className="font-medium">
                  {STATUT_LABELS[BACKEND_STATUS_MAP[detail.status]] || detail.status}
                </span>
              </div>
              <div>
                <span className="text-gray-500">
                  <Explain term="severite">{DRAWER_LABELS.severity}</Explain> :
                </span>{' '}
                <span className="font-medium">
                  {SEVERITY_LABELS[detail.severity] || detail.severity}
                </span>
              </div>
              <div>
                <span className="text-gray-500">{DRAWER_LABELS.site} :</span>{' '}
                <span className="font-medium">{detail.site_nom}</span>
              </div>
              {detail.deadline && (
                <div>
                  <span className="text-gray-500">{DRAWER_LABELS.deadline} :</span>{' '}
                  <span className="font-medium">
                    {new Date(detail.deadline).toLocaleDateString('fr-FR', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                    })}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Inputs */}
          {detail.inputs && Object.keys(detail.inputs).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.inputs}
              </p>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                {Object.entries(detail.inputs).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-gray-600 font-mono">{k}</span>
                    <span className="text-gray-900 font-medium">
                      {v === null ? '-' : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Params */}
          {detail.params && Object.keys(detail.params).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.params}
              </p>
              <div className="bg-blue-50 rounded-lg p-3 space-y-1">
                {Object.entries(detail.params).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm">
                    <span className="text-blue-600 font-mono">{k}</span>
                    <span className="text-gray-900 font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Evidence */}
          {detail.evidence_refs && Object.keys(detail.evidence_refs).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.evidence_refs}
              </p>
              <div className="bg-green-50 rounded-lg p-3 text-sm text-gray-700">
                <pre className="whitespace-pre-wrap">
                  {JSON.stringify(detail.evidence_refs, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Evidence text */}
          {detail.evidence && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
                {DRAWER_LABELS.explanation}
              </p>
              <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3">{detail.evidence}</p>
            </div>
          )}

          {/* Metadata */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase mb-2">
              {DRAWER_LABELS.metadata}
            </p>
            <div className="text-xs text-gray-400 space-y-1">
              {isExpert && detail.engine_version && (
                <div>
                  {DRAWER_LABELS.engine_version} :{' '}
                  <span className="font-mono">{detail.engine_version}</span>
                </div>
              )}
              {detail.created_at && (
                <div>
                  {DRAWER_LABELS.computed_at} :{' '}
                  {new Date(detail.created_at).toLocaleString('fr-FR')}
                </div>
              )}
              {detail.updated_at && (
                <div>
                  {DRAWER_LABELS.updated_at} : {new Date(detail.updated_at).toLocaleString('fr-FR')}
                </div>
              )}
              <div>
                {DRAWER_LABELS.workflow} :{' '}
                {WORKFLOW_LABELS[detail.insight_status] || detail.insight_status}
              </div>
              <div>
                {DRAWER_LABELS.owner} : {detail.owner || '-'}
              </div>
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
}
