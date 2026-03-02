/**
 * DonneesTab — Extracted from ConformitePage (V92 split)
 * Tab "Données & Qualité" with DataQualityGate per site + intake questions.
 */
import { useState, useEffect } from 'react';
import {
  ShieldCheck, AlertTriangle, ChevronDown, ChevronUp,
  ClipboardList, Database, Clock,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, EmptyState, Progress } from '../../ui';
import { getDataQuality } from '../../services/api';
import { track } from '../../services/tracker';
import { REG_LABELS, DONNEES_ENHANCED_LABELS } from '../../domain/compliance/complianceLabels.fr';

function DataQualityGate({ siteId, siteName }) {
  const [dq, setDq] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [dqError, setDqError] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    getDataQuality('site', siteId)
      .then((data) => { setDq(data); setDqError(false); })
      .catch(() => { setDqError(true); });
  }, [siteId]);

  if (dqError) {
    return (
      <Card className="border-l-4 border-gray-200">
        <CardBody className="bg-gray-50 py-3">
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <AlertTriangle size={14} className="text-gray-400" />
            <span>{siteName || 'Site'} — Qualité indisponible</span>
          </div>
        </CardBody>
      </Card>
    );
  }

  if (!dq) return null;

  const statusColors = {
    OK: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', badge: 'bg-green-100 text-green-800' },
    WARNING: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', badge: 'bg-amber-100 text-amber-800' },
    BLOCKED: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', badge: 'bg-red-100 text-red-800' },
  };
  const sc = statusColors[dq.gate_status] || statusColors.WARNING;

  return (
    <Card className={`border-l-4 ${sc.border}`}>
      <CardBody className={sc.bg}>
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center gap-3">
            <ShieldCheck size={18} className={sc.text} />
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-gray-900">
                  {siteName ? `${siteName} — Qualité` : 'Qualité des données'}
                </span>
                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${sc.badge}`}>{dq.gate_status}</span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Couverture : {dq.coverage_pct}% &middot; Confiance : {dq.confidence_score}%
              </p>
            </div>
          </div>
          <button className="p-1 text-gray-400 hover:text-gray-600">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
            {dq.per_regulation && Object.entries(dq.per_regulation).map(([reg, info]) => (
              <div key={reg} className="flex items-center gap-3">
                <span className="text-xs font-medium text-gray-600 w-32 truncate">{REG_LABELS[`decret_${reg}`] || reg}</span>
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${info.status === 'OK' ? 'bg-green-500' : info.status === 'WARNING' ? 'bg-amber-500' : 'bg-red-500'}`}
                    style={{ width: `${info.critical_total > 0 ? (info.critical_ok / info.critical_total) * 100 : 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500 w-16 text-right">{info.critical_ok}/{info.critical_total}</span>
              </div>
            ))}

            {dq.missing_critical && dq.missing_critical.length > 0 && (
              <div className="p-3 bg-red-50 rounded-lg">
                <p className="text-xs font-semibold text-red-700 uppercase mb-1">Données critiques manquantes</p>
                <div className="flex flex-wrap gap-1.5">
                  {dq.missing_critical.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs font-medium">
                      {m.field} ({m.regulation})
                    </span>
                  ))}
                </div>
              </div>
            )}

            {dq.missing_optional && dq.missing_optional.length > 0 && (
              <div className="p-3 bg-amber-50 rounded-lg">
                <p className="text-xs font-semibold text-amber-700 uppercase mb-1">Données optionnelles manquantes</p>
                <div className="flex flex-wrap gap-1.5">
                  {dq.missing_optional.map((m, i) => (
                    <span key={i} className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs font-medium">
                      {m.field}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export default function DonneesTab({ scopedSites, intakeQuestions, navigate, donneesMetrics }) {
  return (
    <div className="space-y-4">
      {scopedSites.length === 0 ? (
        <EmptyState icon={Database} title="Aucun site dans le périmètre" text="Ajoutez des sites pour analyser la qualité des données." />
      ) : (
        <>
          {donneesMetrics && (
            <div className="grid grid-cols-3 gap-3 mb-4" data-testid="donnees-kpis">
              {/* Complétude */}
              <Card>
                <CardBody className="py-3">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                    {DONNEES_ENHANCED_LABELS.completude}
                  </p>
                  <p className="text-lg font-bold text-gray-900 mb-1">{Math.round(donneesMetrics.completude_pct)}%</p>
                  <Progress value={donneesMetrics.completude_pct} size="sm"
                    color={donneesMetrics.completude_pct >= 80 ? 'green' : donneesMetrics.completude_pct >= 50 ? 'amber' : 'red'} />
                </CardBody>
              </Card>

              {/* Confiance données */}
              <Card>
                <CardBody className="py-3">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                    {DONNEES_ENHANCED_LABELS.confiance}
                  </p>
                  <div className="flex items-center gap-2">
                    <p className="text-lg font-bold text-gray-900">{donneesMetrics.confiance_label}</p>
                    <Badge status={donneesMetrics.confiance_level === 'high' ? 'ok' : donneesMetrics.confiance_level === 'medium' ? 'warn' : 'crit'}>
                      {donneesMetrics.confiance_level === 'high' ? 'Fiable' : donneesMetrics.confiance_level === 'medium' ? 'Partielle' : 'Insuffisante'}
                    </Badge>
                  </div>
                </CardBody>
              </Card>

              {/* Couverture factures */}
              <Card>
                <CardBody className="py-3">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">
                    {DONNEES_ENHANCED_LABELS.couverture_factures}
                  </p>
                  <p className="text-lg font-bold text-gray-900 mb-1">
                    {donneesMetrics.couverture_factures_mois}<span className="text-xs font-normal text-gray-400">/{donneesMetrics.couverture_factures_cible} mois</span>
                  </p>
                  <Progress value={(donneesMetrics.couverture_factures_mois / donneesMetrics.couverture_factures_cible) * 100} size="sm"
                    color={donneesMetrics.couverture_factures_mois >= donneesMetrics.couverture_factures_cible ? 'green' : 'amber'} />
                </CardBody>
              </Card>
            </div>
          )}

          {donneesMetrics?.gaps?.length > 0 && (
            <Card className="mb-4 border-l-4 border-amber-300">
              <CardBody className="bg-amber-50">
                <p className="text-xs font-semibold text-amber-700 uppercase mb-2">Points d'amélioration</p>
                <div className="space-y-2">
                  {donneesMetrics.gaps.map(gap => (
                    <div key={gap.id} className="flex items-center justify-between p-2 bg-white rounded-lg">
                      <span className="text-sm text-gray-700">{gap.label}</span>
                      <Button size="sm" variant="secondary"
                        onClick={() => { navigate(gap.ctaPath); track('donnees_gap_cta', { gap: gap.id }); }}>
                        {gap.ctaLabel}
                      </Button>
                    </div>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}

          <div className="flex items-center gap-2 mb-2">
            <Database size={16} className="text-blue-600" />
            <h3 className="text-sm font-semibold text-gray-700">Qualité des données par site ({scopedSites.length})</h3>
          </div>
          {scopedSites.map(site => (
            <DataQualityGate key={site.id} siteId={site.id} siteName={site.nom} />
          ))}

          {intakeQuestions.length > 0 && (
            <Card>
              <CardBody>
                <div className="flex items-center gap-2 mb-3">
                  <ClipboardList size={16} className="text-indigo-600" />
                  <h3 className="text-sm font-semibold text-gray-700">Questions en attente ({intakeQuestions.length})</h3>
                </div>
                <div className="space-y-2">
                  {intakeQuestions.slice(0, 5).map((q, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                      <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                        q.severity === 'critical' ? 'bg-red-500' : q.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'
                      }`} />
                      <div className="flex-1">
                        <p className="text-sm text-gray-800">{q.question}</p>
                        {q.help && <p className="text-xs text-gray-500 mt-0.5">{q.help}</p>}
                        <div className="flex items-center gap-2 mt-1">
                          {q.regulations?.map(r => (
                            <span key={r} className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">{REG_LABELS[r] || r}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                {intakeQuestions.length > 5 && (
                  <p className="text-xs text-gray-400 mt-2">+ {intakeQuestions.length - 5} autres questions</p>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => { navigate(`/intake/${scopedSites[0]?.id}`); track('conformite_goto_intake'); }}
                >
                  Compléter le questionnaire
                </Button>
              </CardBody>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
