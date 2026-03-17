/**
 * PROMEOS — Action Detail Panel (slide-over / drawer)
 */
export default function ActionDetailPanel({ item, onClose, onResolve, onReopen, isAction }) {
  if (!item) return null;

  const slaColors = {
    on_track: 'text-green-700',
    at_risk: 'text-amber-700',
    overdue: 'text-red-700',
    resolved: 'text-gray-500',
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/20" />
      <div
        className="relative w-full max-w-lg bg-white shadow-xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between z-10">
          <h2 className="text-lg font-semibold text-gray-900">
            {isAction ? 'Détail action' : 'Détail signal'}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
            ×
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {/* Title */}
          <div>
            <div className="text-sm font-medium text-gray-900">{item.issue_label}</div>
            <div className="text-xs text-gray-500 mt-1">{item.issue_id || item.id}</div>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-400">Domaine</div>
              <div className="font-medium">{item.domain}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Priorité</div>
              <div className="font-medium">{item.priority || item.severity}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Site</div>
              <div className="font-medium">{item.site_name || `#${item.site_id}`}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400">Statut</div>
              <div className="font-medium">{item.status || 'signal'}</div>
            </div>
            {item.owner && (
              <div>
                <div className="text-xs text-gray-400">Responsable</div>
                <div className="font-medium">{item.owner}</div>
              </div>
            )}
            {item.due_date && (
              <div>
                <div className="text-xs text-gray-400">Échéance</div>
                <div className="font-medium">
                  {new Date(item.due_date).toLocaleDateString('fr-FR')}
                </div>
              </div>
            )}
            {item.sla_status && (
              <div>
                <div className="text-xs text-gray-400">SLA</div>
                <div className={`font-medium ${slaColors[item.sla_status] || ''}`}>
                  {item.sla_status}
                </div>
              </div>
            )}
            {item.estimated_impact_eur != null && (
              <div>
                <div className="text-xs text-gray-400">Impact estimé</div>
                <div className="font-medium">
                  {Math.round(item.estimated_impact_eur).toLocaleString('fr-FR')} €
                </div>
              </div>
            )}
          </div>

          {/* Reasons */}
          {item.reason_codes?.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Raisons</div>
              <div className="flex flex-wrap gap-1">
                {item.reason_codes.map((r, i) => (
                  <span key={i} className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Evidence */}
          {isAction && (
            <div className="border rounded p-3 bg-gray-50">
              <div className="text-xs text-gray-400 mb-1">Preuve</div>
              <div className="text-sm">
                {item.evidence_required ? (
                  item.evidence_received ? (
                    <span className="text-green-700">✓ Preuve reçue</span>
                  ) : (
                    <span className="text-red-700">⚠ Preuve requise — non fournie</span>
                  )
                ) : (
                  <span className="text-gray-500">Aucune preuve requise</span>
                )}
              </div>
              {item.evidence_note && (
                <div className="text-xs text-gray-600 mt-1">{item.evidence_note}</div>
              )}
            </div>
          )}

          {/* Recommended action */}
          {item.recommended_action && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Action recommandée</div>
              <div className="text-sm text-gray-700 bg-blue-50 p-2 rounded">
                {item.recommended_action}
              </div>
            </div>
          )}

          {/* Resolution */}
          {item.resolution_note && (
            <div>
              <div className="text-xs text-gray-400 mb-1">Note de résolution</div>
              <div className="text-sm text-gray-700 bg-green-50 p-2 rounded">
                {item.resolution_note}
              </div>
              {item.resolved_at && (
                <div className="text-xs text-gray-400 mt-1">
                  Résolu le {new Date(item.resolved_at).toLocaleDateString('fr-FR')} par{' '}
                  {item.resolved_by || 'système'}
                </div>
              )}
            </div>
          )}

          {/* Source ref */}
          {item.source_ref && (
            <div className="text-xs text-gray-400">
              Source : <span className="font-mono">{item.source_ref}</span>
            </div>
          )}

          {/* Timestamps */}
          <div className="text-xs text-gray-400 space-y-0.5 border-t pt-3">
            {item.created_at && (
              <div>Créé : {new Date(item.created_at).toLocaleDateString('fr-FR')}</div>
            )}
            {item.updated_at && (
              <div>MAJ : {new Date(item.updated_at).toLocaleDateString('fr-FR')}</div>
            )}
            {item.last_status_change_at && (
              <div>
                Dernier changement :{' '}
                {new Date(item.last_status_change_at).toLocaleDateString('fr-FR')}
              </div>
            )}
          </div>

          {/* Actions */}
          {isAction && (
            <div className="flex gap-2 pt-2 border-t">
              {item.status !== 'resolved' && (
                <button
                  onClick={() => onResolve(item.id)}
                  className="flex-1 bg-green-600 text-white py-2 rounded text-sm hover:bg-green-700"
                >
                  Résoudre
                </button>
              )}
              {item.status === 'resolved' && (
                <button
                  onClick={() => onReopen(item.id)}
                  className="flex-1 bg-amber-600 text-white py-2 rounded text-sm hover:bg-amber-700"
                >
                  Réouvrir
                </button>
              )}
              <button
                onClick={onClose}
                className="flex-1 border text-gray-600 py-2 rounded text-sm hover:bg-gray-50"
              >
                Fermer
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
