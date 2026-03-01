/**
 * PROMEOS — ScheduleDetectionPanel
 * Compare declared vs auto-detected schedule from load curve.
 * Shows confidence badge, per-day mismatch, and "apply detected" action.
 */
import { useState, useCallback } from 'react';
import { Radar, CheckCircle, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';
import { compareSchedules, applyDetectedSchedule } from '../../services/api';
import { Card, CardBody, Badge, Button } from '../../ui';
import { useToast } from '../../ui/ToastProvider';

const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];
const DOW_KEYS = ['0', '1', '2', '3', '4', '5', '6'];

const CONF_COLORS = {
  ELEVEE: 'bg-emerald-100 text-emerald-700',
  MOYEN: 'bg-amber-100 text-amber-700',
  FAIBLE: 'bg-red-100 text-red-700',
};

function intervalsLabel(slots) {
  if (!slots || slots.length === 0) return 'Fermé';
  return slots.map((s) => `${s.start}–${s.end}`).join(', ');
}

export default function ScheduleDetectionPanel({ siteId, onApplied }) {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState(null);

  const handleDetect = useCallback(async () => {
    if (!siteId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await compareSchedules(siteId);
      setData(result);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Impossible de détecter les horaires');
    } finally {
      setLoading(false);
    }
  }, [siteId]);

  const handleApply = useCallback(async () => {
    if (!siteId) return;
    setApplying(true);
    try {
      await applyDetectedSchedule(siteId);
      toast('Horaires détectés appliqués — diagnostic recalculé', 'success');
      setData(null);
      onApplied?.();
    } catch {
      toast('Erreur lors de l\u2019application', 'error');
    } finally {
      setApplying(false);
    }
  }, [siteId, toast, onApplied]);

  return (
    <Card>
      <CardBody>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Radar className="w-4 h-4 text-violet-500" />
            <h3 className="text-sm font-semibold text-gray-700">Détection automatique</h3>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleDetect}
            disabled={loading}
            data-testid="detect-schedule-btn"
          >
            <RefreshCw className={`w-3 h-3 mr-1 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Analyse\u2026' : data ? 'Relancer' : 'Détecter'}
          </Button>
        </div>

        {error && (
          <div className="rounded bg-red-50 border border-red-200 p-3 mb-3" data-testid="detection-error">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {data && (
          <div data-testid="detection-result">
            {/* Confidence badge + global status */}
            <div className="flex items-center gap-3 mb-4">
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${CONF_COLORS[data.confidence_label] || CONF_COLORS.FAIBLE}`}
                data-testid="confidence-badge"
              >
                Confiance : {data.confidence_label} ({Math.round(data.confidence * 100)}%)
              </span>
              {data.comparison?.global_status === 'MISMATCH' && (
                <span
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700"
                  data-testid="mismatch-banner"
                >
                  <AlertTriangle className="w-3 h-3" />
                  Écart détecté
                </span>
              )}
              {data.comparison?.global_status === 'OK' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700">
                  <CheckCircle className="w-3 h-3" />
                  Cohérent
                </span>
              )}
            </div>

            {/* Per-day comparison table */}
            <div className="border rounded overflow-hidden mb-4">
              <table className="w-full text-xs">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left px-2 py-1.5 font-medium text-gray-500">Jour</th>
                    <th className="text-left px-2 py-1.5 font-medium text-gray-500">Déclaré</th>
                    <th className="text-left px-2 py-1.5 font-medium text-gray-500">Détecté</th>
                    <th className="text-right px-2 py-1.5 font-medium text-gray-500">Écart</th>
                  </tr>
                </thead>
                <tbody>
                  {DOW_KEYS.map((k, i) => {
                    const diff = data.comparison?.diff?.[k];
                    const isMismatch = diff?.status === 'MISMATCH';
                    return (
                      <tr
                        key={k}
                        className={isMismatch ? 'bg-amber-50' : ''}
                        data-testid={`compare-row-${k}`}
                      >
                        <td className="px-2 py-1.5 font-medium text-gray-700">{DAY_LABELS[i]}</td>
                        <td className="px-2 py-1.5 text-gray-600">{intervalsLabel(data.declared?.[k])}</td>
                        <td className="px-2 py-1.5 text-gray-600">{intervalsLabel(data.detected?.[k])}</td>
                        <td className="px-2 py-1.5 text-right">
                          {isMismatch ? (
                            <Badge variant="warn">{diff.delta_minutes}min</Badge>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Evidence details */}
            {data.evidence && (
              <div className="grid grid-cols-3 gap-2 text-[10px] text-gray-400 mb-4" data-testid="evidence-details">
                <div>Couverture : {data.evidence.coverage_days}j / {data.evidence.expected_days}j</div>
                <div>Stabilité : {Math.round(data.evidence.stability_score * 100)}%</div>
                <div>Séparation : {data.evidence.separation_ratio}x</div>
              </div>
            )}

            {/* Apply button */}
            {data.comparison?.global_status === 'MISMATCH' && (
              <div className="flex justify-end">
                <Button
                  size="sm"
                  onClick={handleApply}
                  disabled={applying}
                  data-testid="apply-detected-btn"
                >
                  {applying ? (
                    <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                  ) : (
                    <ArrowRight className="w-3 h-3 mr-1" />
                  )}
                  {applying ? 'Application\u2026' : 'Appliquer les horaires détectés'}
                </Button>
              </div>
            )}
          </div>
        )}

        {!data && !error && !loading && (
          <p className="text-xs text-gray-400 text-center py-3">
            Cliquez sur Détecter pour analyser la courbe de charge et comparer avec les horaires déclarés.
          </p>
        )}
      </CardBody>
    </Card>
  );
}
