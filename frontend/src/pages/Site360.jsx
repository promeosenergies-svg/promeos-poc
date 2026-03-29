/**
 * PROMEOS - Site 360 (/sites/:siteId)
 * Header + badges + 3 mini KPIs + tabs (Resume, Conso, Factures, Conformite, Actions)
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  Zap,
  BadgeEuro,
  AlertTriangle,
  MapPin,
  Ruler,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  ClipboardCheck,
  CheckCircle,
  XCircle,
  Download,
  History,
  Wrench,
  Eye,
  FileText,
  Sparkles,
  X,
  ChevronRight,
  Briefcase,
  BarChart3,
} from 'lucide-react';
import {
  Card,
  CardBody,
  Badge,
  Button,
  Tabs,
  EmptyState,
  TrustBadge,
  Explain,
  PageShell,
} from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonCard, SkeletonTable } from '../ui/Skeleton';
import ErrorState from '../ui/ErrorState';
import { useScope } from '../contexts/ScopeContext';
import {
  applyKB,
  getPatrimoineAnomalies,
  getSitePaymentInfo,
  getReconciliation,
  applyReconciliationFix,
  getReconciliationHistory,
  getReconciliationEvidenceCsv,
  getReconciliationEvidenceSummary,
  patrimoineDeliveryPoints,
} from '../services/api';
import {
  getStatusBadgeProps,
  SEV_BADGE,
  getComplianceScoreColor,
  getComplianceGrade,
  COMPLIANCE_SCORE_THRESHOLDS as _COMPLIANCE_SCORE_THRESHOLDS,
} from '../lib/constants'; // eslint-disable-line no-unused-vars
import IntakeWizard from '../components/IntakeWizard';
import BacsWizard from '../components/BacsWizard';
import BacsRegulatoryPanel from '../components/BacsRegulatoryPanel';
import { FlexPotentialCard, BacsFlexLink } from '../components/flex';
import SiteBillingMini from '../components/SiteBillingMini';
import SiteContractsSummary from '../components/SiteContractsSummary';
import SegmentationWidget from '../components/SegmentationWidget';
import SegmentationQuestionnaireModal from '../components/SegmentationQuestionnaireModal';
import TabConsoSite from '../components/TabConsoSite';
import TabActionsSite from '../components/TabActionsSite';
import { fmtNum, fmtEurFull, fmtArea } from '../utils/format';
import DataQualityBadge from '../components/DataQualityBadge';
import FreshnessIndicator from '../components/FreshnessIndicator';
import { getDataQualityScore, getSiteFreshness, getSiteCompleteness } from '../services/api';

const _sb = (k) => {
  const { variant, label } = getStatusBadgeProps(k);
  return { status: variant, label };
};
const STATUT_BADGE = {
  conforme: _sb('conforme'),
  non_conforme: _sb('non_conforme'),
  a_risque: _sb('a_risque'),
  a_evaluer: _sb('a_evaluer'),
};

const TABS = [
  { id: 'resume', label: 'Résumé' },
  { id: 'conso', label: 'Consommation' },
  { id: 'factures', label: 'Factures' },
  { id: 'reconciliation', label: 'Réconciliation' },
  { id: 'conformite', label: 'Conformité' },
  { id: 'actions', label: 'Actions' },
];

function MiniKpi({ icon: Icon, label, value, color }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-lg">
      <Icon size={18} className={color} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-bold text-gray-800">{value}</p>
      </div>
    </div>
  );
}

function TabResume({ site, onSegmentationClick }) {
  const [anomalies, setAnomalies] = useState([]);
  const [anomLoading, setAnomLoading] = useState(true);
  const [deliveryPoints, setDeliveryPoints] = useState([]);
  const [dpLoading, setDpLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    setAnomLoading(true);
    getPatrimoineAnomalies(site.id)
      .then((data) => {
        if (!stale) setAnomalies(data.anomalies || []);
      })
      .catch(() => {
        if (!stale) setAnomalies([]);
      })
      .finally(() => {
        if (!stale) setAnomLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [site.id]);

  // B2-4: Fetch delivery points
  useEffect(() => {
    let stale = false;
    setDpLoading(true);
    patrimoineDeliveryPoints(site.id)
      .then((data) => {
        if (!stale) setDeliveryPoints(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (!stale) setDeliveryPoints([]);
      })
      .finally(() => {
        if (!stale) setDpLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [site.id]);

  return (
    <div className="space-y-4 pt-6">
      {/* B2-1: Hierarchy bar — Org > EJ > Portefeuille > Site */}
      {(site.organisation_nom || site.entite_juridique_nom || site.portefeuille_nom) && (
        <div className="flex items-center gap-2 text-xs text-gray-500 bg-gray-50 rounded-lg px-4 py-2.5 border border-gray-100">
          <Briefcase size={13} className="text-indigo-500 shrink-0" />
          {site.organisation_nom && (
            <span className="font-medium text-gray-700">{site.organisation_nom}</span>
          )}
          {site.entite_juridique_nom && (
            <>
              <ChevronRight size={12} className="text-gray-300" />
              <span className="text-gray-600">{site.entite_juridique_nom}</span>
            </>
          )}
          {site.portefeuille_nom && (
            <>
              <ChevronRight size={12} className="text-gray-300" />
              <span className="text-gray-600">{site.portefeuille_nom}</span>
            </>
          )}
          <ChevronRight size={12} className="text-gray-300" />
          <span className="font-medium text-gray-800">{site.nom}</span>
          <span className="ml-auto text-gray-400">
            {site.surface_m2 ? `${(site.surface_m2 / 1000).toFixed(1)}k m²` : ''}
            {site.siret ? ` · SIRET ${site.siret}` : ''}
          </span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Left: KPIs + anomalies */}
        <div className="space-y-4">
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">Indicateurs clés</h3>
            </div>
            <CardBody>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-gray-500">Conso annuelle</p>
                  <p className="text-lg font-bold text-blue-700">
                    {fmtNum((site.conso_kwh_an || 0) / 1000, 0, 'MWh')}
                  </p>
                </div>
                <div className="p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-gray-500">Risque financier</p>
                  <p className="text-lg font-bold text-red-700">{fmtEurFull(site.risque_eur)}</p>
                </div>
                <div className="p-3 bg-amber-50 rounded-lg">
                  <p className="text-xs text-gray-500">
                    <Explain term="anomalie">Anomalies</Explain>
                  </p>
                  <p className="text-lg font-bold text-amber-700">{site.anomalies_count ?? 0}</p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-gray-500">Compteurs</p>
                  <p className="text-lg font-bold text-green-700">{site.nb_compteurs}</p>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* V96: Payment info */}
          <PaymentInfoCard siteId={site.id} />

          {/* Reco principale */}
          <Card className="border-l-4 border-l-blue-500">
            <CardBody>
              <p className="text-xs text-gray-500 uppercase font-semibold mb-1">
                Recommandation principale
              </p>
              <p className="text-sm text-gray-800 font-medium">
                {site.statut_conformite === 'non_conforme'
                  ? 'Déclarer vos consommations sur OPERAT avant le 30/09/2026'
                  : site.statut_conformite === 'a_risque'
                    ? 'Planifier la mise en conformité BACS pour ce site'
                    : 'Maintenir la surveillance et optimiser la consommation'}
              </p>
              <Button size="sm" className="mt-3">
                Créer une action
              </Button>
            </CardBody>
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Anomalies list */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">
                <Explain term="anomalie">Anomalies</Explain> détectées
              </h3>
            </div>
            {anomLoading ? (
              <div className="p-4">
                <SkeletonCard />
              </div>
            ) : anomalies.length === 0 ? (
              <EmptyState
                title="Aucune anomalie"
                text="Ce site ne présente aucune anomalie détectée."
              />
            ) : (
              <Table>
                <Thead>
                  <tr>
                    <Th>Type</Th>
                    <Th>Sévérité</Th>
                    <Th>Message</Th>
                    <Th className="text-right">Perte</Th>
                  </tr>
                </Thead>
                <Tbody>
                  {anomalies.map((a, idx) => (
                    <Tr key={a.id || idx}>
                      <Td>
                        <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                          {a.anomaly_type}
                        </span>
                      </Td>
                      <Td>
                        <Badge status={SEV_BADGE[a.severity] || 'info'}>{a.severity}</Badge>
                      </Td>
                      <Td className="text-sm">{a.title_fr}</Td>
                      <Td className="text-right text-red-600 font-medium">
                        {fmtEurFull(a.business_impact?.estimated_risk_eur)}
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            )}
          </Card>

          {/* B2-4: Points de livraison (PDL) */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">Points de livraison</h3>
            </div>
            {dpLoading ? (
              <div className="p-4">
                <SkeletonCard />
              </div>
            ) : deliveryPoints.length === 0 ? (
              <EmptyState
                icon={Zap}
                title="Aucun PDL"
                text="Aucun point de livraison rattaché à ce site."
              />
            ) : (
              <CardBody>
                <div className="space-y-2">
                  {deliveryPoints.map((dp) => (
                    <div
                      key={dp.id}
                      className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0"
                    >
                      <div className="flex items-center gap-2">
                        <Zap
                          size={13}
                          className={
                            dp.energy_type === 'electricity' ? 'text-blue-500' : 'text-orange-500'
                          }
                        />
                        <span className="font-mono text-xs text-gray-700">{dp.code}</span>
                        <Badge status={dp.energy_type === 'electricity' ? 'info' : 'warning'}>
                          {dp.energy_type === 'electricity'
                            ? 'Élec'
                            : dp.energy_type === 'gas'
                              ? 'Gaz'
                              : dp.energy_type}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        {dp.compteurs_count > 0 && (
                          <span>
                            {dp.compteurs_count} compteur{dp.compteurs_count > 1 ? 's' : ''}
                          </span>
                        )}
                        <Badge status={dp.status === 'active' ? 'ok' : 'neutral'}>
                          {dp.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </CardBody>
            )}
          </Card>

          {/* V100: Segmentation profile & recommendations */}
          <SegmentationWidget onSegmentationClick={onSegmentationClick} />

          {/* V-registre: Cross-module links */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">Accès rapide</h3>
            </div>
            <CardBody>
              <div className="space-y-2">
                <Link
                  to={`/billing?site_id=${site.id}`}
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >
                  <BadgeEuro size={14} /> Bill Intelligence
                </Link>
                <Link
                  to="/conformite"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >
                  <ShieldCheck size={14} /> Conformité réglementaire
                </Link>
                <Link
                  to={`/contract-radar?site_id=${site.id}`}
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >
                  <FileText size={14} /> Radar contrats
                </Link>
                <Link
                  to="/actions"
                  className="flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
                >
                  <Wrench size={14} /> Actions
                </Link>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
      {/* /grid-cols-2 */}

      {/* Flex potential */}
      <FlexPotentialCard siteId={site.id} />
    </div>
  );
}

function PaymentInfoCard({ siteId }) {
  const navPay = useNavigate();
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stale = false;
    getSitePaymentInfo(siteId)
      .then((data) => {
        if (!stale) setInfo(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [siteId]);

  if (loading) return <SkeletonCard />;

  if (!info?.resolved) {
    return (
      <Card className="border-l-4 border-l-gray-300">
        <CardBody>
          <p className="text-xs text-gray-500 uppercase font-semibold mb-1">
            Paiement & Refacturation
          </p>
          <p className="text-sm text-gray-500">Aucune règle de paiement configurée</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => navPay('/payment-rules')}
          >
            Configurer
          </Button>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className="border-l-4 border-l-emerald-500">
      <CardBody>
        <p className="text-xs text-gray-500 uppercase font-semibold mb-2">
          Paiement & Refacturation
        </p>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-gray-500">Facturé :</span>{' '}
            <span className="font-medium">{info.invoice_entity_name || '—'}</span>
          </div>
          <div>
            <span className="text-gray-500">Payeur :</span>{' '}
            <span className="font-medium">{info.payer_entity_name || '(même)'}</span>
          </div>
          <div>
            <span className="text-gray-500">Centre de coût :</span>{' '}
            <span className="font-medium">{info.rule?.cost_center || '—'}</span>
          </div>
          <div>
            <span className="text-gray-500">Source :</span>{' '}
            <Badge status="info">{info.source_level}</Badge>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

const RECON_STATUS_ICON = {
  ok: { icon: CheckCircle, color: 'text-green-600' },
  warn: { icon: AlertTriangle, color: 'text-amber-500' },
  fail: { icon: XCircle, color: 'text-red-600' },
};
const RECON_STATUS_BADGE = { ok: 'success', warn: 'warning', fail: 'error' };

function EvidenceSummaryModal({ site, onClose }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getReconciliationEvidenceSummary(site.id)
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [site.id]);

  const STATUS_LABEL = { ok: 'Conforme', warn: 'Attention', fail: 'À corriger' };
  const STATUS_COLOR = {
    ok: 'text-green-700 bg-green-50',
    warn: 'text-amber-700 bg-amber-50',
    fail: 'text-red-700 bg-red-50',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="font-bold text-gray-900">Résumé 1 page — {site.nom}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        {loading ? (
          <div className="p-6">
            <SkeletonCard />
          </div>
        ) : !summary ? (
          <div className="p-6 text-sm text-gray-500">Impossible de charger le résumé.</div>
        ) : (
          <div className="p-6 space-y-5 text-sm print:text-xs" id="evidence-summary-print">
            <div className="flex items-center gap-4">
              <div
                className={`px-3 py-1 rounded-full font-bold ${STATUS_COLOR[summary.status] || ''}`}
              >
                {STATUS_LABEL[summary.status] || summary.status}
              </div>
              <div className="flex-1">
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${summary.score >= 80 ? 'bg-green-500' : summary.score >= 50 ? 'bg-amber-400' : 'bg-red-500'}`}
                    style={{ width: `${summary.score}%` }}
                  />
                </div>
              </div>
              <span className="font-bold text-gray-700">{summary.score}%</span>
            </div>

            <div>
              <h3 className="font-semibold text-gray-800 mb-2">Points clés</h3>
              {summary.key_checks.map((c) => (
                <div key={c.id} className="flex items-center gap-2 py-1">
                  {c.status === 'ok' ? (
                    <CheckCircle size={14} className="text-green-600" />
                  ) : c.status === 'fail' ? (
                    <XCircle size={14} className="text-red-600" />
                  ) : (
                    <AlertTriangle size={14} className="text-amber-500" />
                  )}
                  <span className="font-medium">{c.title}</span>
                  {c.impact && <Badge status="info">{c.impact}</Badge>}
                </div>
              ))}
            </div>

            {summary.recent_fixes.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-800 mb-2">Corrections récentes</h3>
                {summary.recent_fixes.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 py-1 text-gray-600">
                    <Wrench size={12} className="text-blue-500" />
                    <span>{f.action}</span>
                    {f.applied_at && (
                      <span className="text-xs text-gray-400 ml-auto">
                        {new Date(f.applied_at).toLocaleDateString('fr-FR')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {summary.remaining_actions.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-800 mb-2">Actions restantes</h3>
                {summary.remaining_actions.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 py-1 text-gray-600">
                    <AlertTriangle size={12} className="text-amber-500" />
                    <span>{a.label}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-2 border-t text-xs text-gray-400">
              Généré le {new Date(summary.generated_at).toLocaleString('fr-FR')}
            </div>
          </div>
        )}
        <div className="px-6 py-3 border-t flex justify-end gap-2">
          <Button size="sm" variant="outline" onClick={() => window.print()}>
            Imprimer
          </Button>
          <Button size="sm" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}

function TabReconciliation({ site }) {
  const [recon, setRecon] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fixingAction, setFixingAction] = useState(null);
  const [toast, setToast] = useState(null);
  const [history, setHistory] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  const [mode, setMode] = useState('simple');
  const [showSummaryModal, setShowSummaryModal] = useState(false);
  const [scoreGain, setScoreGain] = useState(null);

  const loadRecon = () => {
    setLoading(true);
    getReconciliation(site.id)
      .then((data) => setRecon(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRecon();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site.id]);

  const handleFix = async (checkId, action) => {
    setFixingAction(action.action);
    const prevScore = recon?.score || 0;
    try {
      await applyReconciliationFix(site.id, { action: action.action, params: action.params || {} });
      setToast({
        type: 'success',
        message: `Correction appliquée : ${action.label_simple || action.label_fr}`,
      });
      const fresh = await getReconciliation(site.id);
      setRecon(fresh);
      const gain = fresh.score - prevScore;
      if (gain > 0) setScoreGain(gain);
      setTimeout(() => setScoreGain(null), 4000);
    } catch (e) {
      setToast({
        type: 'error',
        message: e?.response?.data?.detail || 'Erreur lors de la correction',
      });
    } finally {
      setFixingAction(null);
      setTimeout(() => setToast(null), 4000);
    }
  };

  const handleNbaFix = async () => {
    const nba = recon?.next_best_action;
    if (!nba) return;
    await handleFix(nba.check_id, {
      action: nba.action,
      params: nba.payload?.params || {},
      label_simple: nba.action_label,
      label_fr: nba.action_label,
    });
  };

  const handleDownloadCsv = async () => {
    try {
      const blob = await getReconciliationEvidenceCsv(site.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `evidence_site_${site.id}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      /* ignore */
    }
  };

  const loadHistory = async () => {
    if (history) {
      setShowHistory(!showHistory);
      return;
    }
    try {
      const data = await getReconciliationHistory(site.id);
      setHistory(data.logs || []);
      setShowHistory(true);
    } catch {
      setHistory([]);
      setShowHistory(true);
    }
  };

  if (loading)
    return (
      <div className="pt-6">
        <SkeletonCard />
      </div>
    );
  if (!recon) return <EmptyState title="Erreur" text="Impossible de charger la réconciliation." />;

  const nonOkChecks = (recon.checks || []).filter((c) => c.status !== 'ok');
  const nba = recon.next_best_action;

  return (
    <div className="space-y-4 pt-6">
      {/* Toast */}
      {toast && (
        <div
          className={`px-4 py-2 rounded-lg text-sm font-medium ${toast.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}
        >
          {toast.message}
          {scoreGain > 0 && (
            <span className="ml-2 font-bold text-green-700">Score +{scoreGain}</span>
          )}
        </div>
      )}

      {/* Mode switch */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          <button
            onClick={() => setMode('simple')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${mode === 'simple' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Simple
          </button>
          <button
            onClick={() => setMode('expert')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${mode === 'expert' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Expert
          </button>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowSummaryModal(true)}>
            <FileText size={14} className="mr-1" /> Résumé 1 page
          </Button>
          {mode === 'expert' && (
            <>
              <Button size="sm" variant="outline" onClick={handleDownloadCsv}>
                <Download size={14} className="mr-1" /> CSV
              </Button>
              <Button size="sm" variant="outline" onClick={loadHistory}>
                <History size={14} className="mr-1" /> Journal
              </Button>
            </>
          )}
        </div>
      </div>

      {/* ═══ SIMPLE MODE ═══ */}
      {mode === 'simple' && (
        <>
          {/* Bloc 1: État du site */}
          <Card>
            <CardBody>
              <p className="text-xs text-gray-500 uppercase font-semibold mb-2">État du site</p>
              <div className="flex items-center gap-4">
                <div
                  className={`text-3xl font-bold ${recon.score >= 80 ? 'text-green-600' : recon.score >= 50 ? 'text-amber-500' : 'text-red-600'}`}
                >
                  {recon.score}%
                </div>
                <div className="flex-1">
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className={`h-4 rounded-full transition-all ${recon.score >= 80 ? 'bg-green-500' : recon.score >= 50 ? 'bg-amber-400' : 'bg-red-500'}`}
                      style={{ width: `${recon.score}%` }}
                    />
                  </div>
                </div>
                <Badge
                  status={RECON_STATUS_BADGE[recon.status] || 'info'}
                  className="text-sm px-3 py-1"
                >
                  {recon.status === 'ok'
                    ? 'Conforme'
                    : recon.status === 'warn'
                      ? 'Attention'
                      : 'À corriger'}
                </Badge>
              </div>
            </CardBody>
          </Card>

          {/* Bloc 2: Ce qui bloque (max 3 items) */}
          {nonOkChecks.length > 0 && (
            <Card>
              <div className="px-5 py-3 border-b border-gray-100">
                <h3 className="font-semibold text-gray-800">Ce qui bloque</h3>
              </div>
              <div className="divide-y divide-gray-100">
                {nonOkChecks.slice(0, 3).map((check) => {
                  const cfg = RECON_STATUS_ICON[check.status] || RECON_STATUS_ICON.warn;
                  const Icon = cfg.icon;
                  return (
                    <div key={check.id} className="px-5 py-4">
                      <div className="flex items-start gap-3">
                        <Icon size={20} className={cfg.color + ' mt-0.5 shrink-0'} />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-semibold text-gray-900">
                              {check.title_simple || check.label_fr}
                            </p>
                            {check.impact_label && (
                              <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                                {check.impact_label}
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1">
                            {check.why_it_matters || check.reason_fr}
                          </p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          )}

          {/* Bloc 3: NBA — Prochaine action recommandée */}
          {nba && (
            <Card className="border-l-4 border-l-blue-500">
              <CardBody>
                <div className="flex items-start gap-3">
                  <Sparkles size={20} className="text-blue-500 mt-0.5 shrink-0" />
                  <div className="flex-1">
                    <p className="text-xs text-blue-600 uppercase font-semibold">
                      Prochaine action recommandée
                    </p>
                    <p className="text-sm font-semibold text-gray-900 mt-1">{nba.action_label}</p>
                    <p className="text-sm text-gray-600 mt-1">{nba.reason}</p>
                    <p className="text-xs text-green-600 mt-1 font-medium">
                      Score attendu : +{nba.expected_score_gain} points
                    </p>
                    <Button
                      size="sm"
                      className="mt-3"
                      disabled={fixingAction === nba.action}
                      onClick={handleNbaFix}
                    >
                      <Wrench size={14} className="mr-1" />
                      {fixingAction === nba.action ? 'En cours...' : 'Appliquer'}
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          {recon.status === 'ok' && (
            <Card className="border-l-4 border-l-green-500">
              <CardBody>
                <div className="flex items-center gap-3">
                  <CheckCircle size={24} className="text-green-600" />
                  <div>
                    <p className="font-semibold text-green-800">Tout est en ordre</p>
                    <p className="text-sm text-gray-600">
                      Votre site est entièrement réconcilié. Aucune action requise.
                    </p>
                  </div>
                </div>
              </CardBody>
            </Card>
          )}

          {/* Link to expert mode */}
          <button
            onClick={() => setMode('expert')}
            className="text-xs text-blue-600 hover:underline flex items-center gap-1"
          >
            <Eye size={12} /> Voir détails (mode expert)
          </button>
        </>
      )}

      {/* ═══ EXPERT MODE ═══ */}
      {mode === 'expert' && (
        <>
          {/* Header */}
          <Card>
            <CardBody>
              <div className="flex items-center gap-4">
                <Badge
                  status={RECON_STATUS_BADGE[recon.status] || 'info'}
                  className="text-base px-3 py-1"
                >
                  {recon.status === 'ok'
                    ? 'OK'
                    : recon.status === 'warn'
                      ? 'Attention'
                      : 'Incomplet'}
                </Badge>
                <div className="flex-1">
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full ${recon.score >= 80 ? 'bg-green-500' : recon.score >= 50 ? 'bg-amber-400' : 'bg-red-500'}`}
                      style={{ width: `${recon.score}%` }}
                    />
                  </div>
                </div>
                <span className="text-sm font-bold text-gray-700">{recon.score}%</span>
              </div>
              <p className="text-sm text-gray-600 mt-2">{recon.summary_fr}</p>
            </CardBody>
          </Card>

          {/* Full checks list with fix_actions */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="font-semibold text-gray-800">Vérifications</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {(recon.checks || []).map((check) => {
                const cfg = RECON_STATUS_ICON[check.status] || RECON_STATUS_ICON.warn;
                const Icon = cfg.icon;
                return (
                  <div key={check.id} className="px-5 py-3 flex items-start gap-3">
                    <Icon size={18} className={cfg.color + ' mt-0.5 shrink-0'} />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800">{check.label_fr}</p>
                      <p className="text-xs text-gray-500">{check.reason_fr}</p>
                      {check.suggestion_fr && (
                        <p className="text-xs text-amber-600 mt-1">{check.suggestion_fr}</p>
                      )}
                      {check.fix_actions && check.fix_actions.length > 0 && (
                        <div className="flex gap-2 mt-2">
                          {check.fix_actions.map((fa) => (
                            <Button
                              key={fa.action}
                              size="sm"
                              variant="outline"
                              disabled={fixingAction === fa.action}
                              onClick={() => handleFix(check.id, fa)}
                            >
                              <Wrench size={12} className="mr-1" />
                              {fixingAction === fa.action ? 'En cours...' : fa.label_fr}
                            </Button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Fix history journal */}
          {showHistory && (
            <Card>
              <div className="px-5 py-3 border-b border-gray-100">
                <h3 className="font-semibold text-gray-800">Journal des corrections</h3>
              </div>
              {!history || history.length === 0 ? (
                <div className="px-5 py-4 text-sm text-gray-500">Aucune correction appliquée</div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {history.map((log) => (
                    <div key={log.id} className="px-5 py-3 flex items-center gap-3 text-sm">
                      <Wrench size={14} className="text-blue-500 shrink-0" />
                      <div className="flex-1">
                        <span className="font-medium">{log.action}</span>
                        <span className="text-gray-400 mx-2">—</span>
                        <Badge status={RECON_STATUS_BADGE[log.status_before] || 'info'}>
                          {log.status_before}
                        </Badge>
                        <span className="mx-1">→</span>
                        <Badge status={RECON_STATUS_BADGE[log.status_after] || 'info'}>
                          {log.status_after}
                        </Badge>
                      </div>
                      <span className="text-xs text-gray-400">
                        {log.applied_at ? new Date(log.applied_at).toLocaleString('fr-FR') : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}
        </>
      )}

      {/* Evidence Summary Modal */}
      {showSummaryModal && (
        <EvidenceSummaryModal site={site} onClose={() => setShowSummaryModal(false)} />
      )}
    </div>
  );
}

const KB_SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

function TabConformite({ site }) {
  const [kbResult, setKbResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    const estHvacKw = Math.round((site.surface_m2 || 0) * 0.1);
    const estParkingM2 = (site.surface_m2 || 0) >= 2000 ? Math.round(site.surface_m2 * 0.6) : 0;

    applyKB({
      site_context: {
        surface_m2: site.surface_m2 || 0,
        hvac_kw: estHvacKw,
        building_type: site.usage || 'bureau',
        parking_area_m2: estParkingM2,
        tertiaire_area_m2: site.surface_m2 || 0,
      },
      allow_drafts: true,
    })
      .then((data) => {
        setKbResult(data);
        setError(false);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [site]);

  if (loading) {
    return (
      <div className="pt-6">
        <Card>
          <CardBody className="text-center py-8">
            <BookOpen size={28} className="text-blue-300 mx-auto mb-2 animate-pulse" />
            <p className="text-sm text-gray-400">
              Évaluation réglementaire en cours pour {site.nom}...
            </p>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (error || !kbResult) {
    return (
      <div className="pt-6">
        <EmptyState
          icon={ShieldCheck}
          title="Analyse indisponible"
          text="Impossible de contacter le moteur KB. Vérifiez que le backend est démarré."
        />
      </div>
    );
  }

  const items = kbResult.applicable_items || [];
  const missing = kbResult.missing_fields || [];
  const suggestions = kbResult.suggestions || [];
  const validated = items.filter((i) => i.status === 'validated');
  const drafts = items.filter((i) => i.status !== 'validated');

  return (
    <div className="pt-6 space-y-4">
      {/* Summary */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">
            {items.length} obligations applicables
          </h3>
        </div>
        {validated.length > 0 && <Badge status="ok">{validated.length} validées</Badge>}
        {drafts.length > 0 && <Badge status="neutral">{drafts.length} exploration</Badge>}
        <Link
          to="/kb"
          className="ml-auto text-xs text-blue-600 hover:underline flex items-center gap-1"
        >
          <BookOpen size={12} /> Explorer la KB
        </Link>
      </div>

      {/* B2-3: Fallback when KB returns no items */}
      {items.length === 0 && (
        <Card>
          <CardBody className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                <ShieldCheck size={20} className="text-blue-500" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-gray-800">Statut conformité du site</h4>
                <p className="text-xs text-gray-500">
                  {site.statut_decret_tertiaire
                    ? `Décret tertiaire : ${site.statut_decret_tertiaire}`
                    : 'Aucune obligation identifiée automatiquement'}
                </p>
              </div>
              {site.statut_decret_tertiaire && (
                <Badge
                  status={
                    site.statut_decret_tertiaire === 'conforme'
                      ? 'ok'
                      : site.statut_decret_tertiaire === 'non_conforme'
                        ? 'error'
                        : 'warning'
                  }
                  className="ml-auto"
                >
                  {site.statut_decret_tertiaire}
                </Badge>
              )}
            </div>

            {/* Site context summary */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">Surface</p>
                <p className="text-sm font-semibold text-gray-800">
                  {site.surface_m2 ? `${site.surface_m2.toLocaleString('fr-FR')} m²` : '—'}
                </p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">Type</p>
                <p className="text-sm font-semibold text-gray-800">{site.type || '—'}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg text-center">
                <p className="text-xs text-gray-500">Avancement</p>
                <p className="text-sm font-semibold text-gray-800">
                  {site.avancement_decret_pct != null
                    ? `${Math.round(site.avancement_decret_pct)} %`
                    : '—'}
                </p>
              </div>
            </div>

            <p className="text-xs text-gray-400">
              Le moteur réglementaire n'a identifié aucune obligation pour ce profil de site.
              Complétez les données du site ou explorez la base de connaissances pour une analyse
              manuelle.
            </p>

            <div className="flex gap-3">
              <Link
                to="/conformite"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
              >
                <ShieldCheck size={13} /> Ouvrir la brique conformité
              </Link>
              <Link
                to="/kb"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
              >
                <BookOpen size={13} /> Explorer la KB
              </Link>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Validated items */}
      {validated.length > 0 && (
        <div className="space-y-2">
          {validated
            .sort((a, b) => (KB_SEV_ORDER[a.severity] ?? 9) - (KB_SEV_ORDER[b.severity] ?? 9))
            .map((item) => (
              <Card key={item.id} className="border-l-4 border-l-blue-400">
                <CardBody className="py-3">
                  <div
                    className="flex items-start gap-3 cursor-pointer"
                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <Badge status={SEV_BADGE[item.severity] || 'neutral'}>
                          {item.severity}
                        </Badge>
                        <Badge status="ok">Valide</Badge>
                        {item.domain && <Badge status="crit">{item.domain}</Badge>}
                      </div>
                      <h4 className="text-sm font-semibold text-gray-900">{item.title}</h4>
                      {expandedId !== item.id && item.summary && (
                        <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.summary}</p>
                      )}
                      {item.why && expandedId !== item.id && (
                        <p className="text-xs text-blue-600 mt-1">{item.why}</p>
                      )}
                    </div>
                    <button className="p-1 text-gray-400 hover:text-gray-600 shrink-0">
                      {expandedId === item.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>

                  {expandedId === item.id && (
                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
                      {item.why && (
                        <div className="p-3 bg-blue-50 rounded-lg">
                          <p className="text-xs font-semibold text-blue-600 uppercase mb-1">
                            Pourquoi applicable
                          </p>
                          <p className="text-sm text-gray-700">{item.why}</p>
                        </div>
                      )}
                      {item.logic?.then?.outputs && (
                        <div className="p-3 bg-amber-50 rounded-lg">
                          <p className="text-xs font-semibold text-amber-700 uppercase mb-1">
                            Obligations
                          </p>
                          {item.logic.then.outputs.map((o, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-xs text-amber-800 mt-1"
                            >
                              <span
                                className={`w-2 h-2 rounded-full ${o.severity === 'critical' ? 'bg-red-500' : o.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'}`}
                              />
                              <span className="font-medium">{o.label}</span>
                              {o.deadline && (
                                <span className="text-amber-600 flex items-center gap-1">
                                  <Clock size={11} /> {o.deadline}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      {item.sources && item.sources.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold text-gray-500 mb-1">Sources</p>
                          {item.sources.map((src, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                              <ExternalLink size={12} />
                              <span>
                                {src.label}
                                {src.section ? ` - ${src.section}` : ''}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                      {item.tags && (
                        <div className="flex flex-wrap gap-1">
                          {Object.entries(item.tags).map(
                            ([cat, values]) =>
                              Array.isArray(values) &&
                              values.map((v) => (
                                <span
                                  key={`${cat}-${v}`}
                                  className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                                >
                                  {cat}:{v}
                                </span>
                              ))
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </CardBody>
              </Card>
            ))}
        </div>
      )}

      {/* Draft items (exploration) */}
      {drafts.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-gray-400 font-medium">Items en exploration (drafts)</p>
          {drafts.slice(0, 5).map((item) => (
            <Card key={item.id} className="border-l-4 border-l-gray-200 opacity-80">
              <CardBody className="py-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge status="neutral">draft</Badge>
                  {item.domain && (
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-50 text-gray-600">
                      {item.domain}
                    </span>
                  )}
                  <span className="text-sm text-gray-700">{item.title}</span>
                </div>
                {item.summary && (
                  <p className="text-xs text-gray-400 mt-1 line-clamp-1">{item.summary}</p>
                )}
              </CardBody>
            </Card>
          ))}
          {drafts.length > 5 && (
            <p className="text-xs text-gray-400 text-center">
              +{drafts.length - 5} autres items en exploration
            </p>
          )}
        </div>
      )}

      {/* Missing fields */}
      {missing.length > 0 && (
        <Card className="border-l-4 border-l-amber-300">
          <CardBody className="py-3">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} className="text-amber-500" />
              <p className="text-xs font-semibold text-amber-700">Données manquantes</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {missing.map((f) => (
                <Badge key={f} status="warn">
                  {f}
                </Badge>
              ))}
            </div>
            {suggestions.length > 0 && (
              <p className="text-xs text-gray-500 mt-2">{suggestions.join(' ')}</p>
            )}
          </CardBody>
        </Card>
      )}

      <TrustBadge source="PROMEOS KB" period={`Analyse pour ${site.nom}`} confidence="high" />

      {/* BACS Regulatory Panel */}
      <div className="mt-6">
        <Card>
          <CardBody className="p-4">
            <BacsRegulatoryPanel siteId={site.id} />
          </CardBody>
        </Card>
      </div>

      {/* Flex pilotability link */}
      <BacsFlexLink siteId={site.id} />
    </div>
  );
}

export default function Site360() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { scopedSites, sitesLoading } = useScope();
  // Persist active tab in URL hash so it survives navigation
  const [activeTab, setActiveTab] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    return hash || 'resume';
  });
  const handleSetTab = useCallback((tab) => {
    setActiveTab(tab);
    window.history.replaceState(null, '', `#${tab}`);
  }, []);
  const [showIntake, setShowIntake] = useState(false);
  const [showBacs, setShowBacs] = useState(false);
  const [showSegModal, setShowSegModal] = useState(false);
  const [siteComplianceScore, setSiteComplianceScore] = useState(null); // A.2
  const [dataQuality, setDataQuality] = useState(null); // D.1
  const [freshness, setFreshness] = useState(null); // D.2
  const [completeness, setCompleteness] = useState(null); // V-registre

  const site = scopedSites.find((s) => String(s.id) === String(id));

  // A.2: Fetch site-level unified compliance score
  useEffect(() => {
    if (!id) return;
    fetch(`/api/compliance/sites/${id}/score`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setSiteComplianceScore(data))
      .catch(() => setSiteComplianceScore(null));
  }, [id]);

  // D.1: Fetch site data quality score
  useEffect(() => {
    if (!id) return;
    getDataQualityScore(id)
      .then(setDataQuality)
      .catch(() => setDataQuality(null));
  }, [id]);

  // D.2: Fetch site freshness
  useEffect(() => {
    if (!id) return;
    getSiteFreshness(id)
      .then(setFreshness)
      .catch(() => setFreshness(null));
  }, [id]);

  // V-registre: Fetch site completeness
  useEffect(() => {
    if (!id) return;
    getSiteCompleteness(id)
      .then(setCompleteness)
      .catch(() => setCompleteness(null));
  }, [id]);

  if (sitesLoading) {
    return (
      <PageShell icon={Zap} title="Fiche site" subtitle="Chargement...">
        <div className="flex gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
        <SkeletonTable rows={5} cols={4} />
      </PageShell>
    );
  }

  if (!site) {
    return (
      <PageShell icon={Zap} title="Fiche site">
        <ErrorState
          message={`Aucun site avec l'identifiant ${id} dans votre périmètre.`}
          onRetry={() => navigate('/patrimoine')}
        />
      </PageShell>
    );
  }

  const badge = STATUT_BADGE[site.statut_conformite] || STATUT_BADGE.a_evaluer;

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Breadcrumb — Patrimoine > [Portefeuille] > Site */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500">
        <button
          onClick={() => navigate('/patrimoine')}
          className="hover:text-gray-700 transition flex items-center gap-1"
        >
          <ArrowLeft size={14} /> Patrimoine
        </button>
        {site.portefeuille_nom && (
          <>
            <span className="text-gray-300">/</span>
            <span className="text-gray-600">{site.portefeuille_nom}</span>
          </>
        )}
        <span className="text-gray-300">/</span>
        <span className="font-medium text-gray-800">{site.nom}</span>
      </nav>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-gray-900">{site.nom}</h2>
            <Badge status={badge.status}>{badge.label}</Badge>
            {siteComplianceScore?.score != null &&
              (() => {
                const s = Math.round(siteComplianceScore.score);
                const grade = getComplianceGrade(s);
                return (
                  <span className="flex items-center gap-1.5" data-testid="compliance-score-badge">
                    <span className={`text-sm font-bold ${getComplianceScoreColor(s)}`}>
                      {s}/100
                    </span>
                    <span
                      className={`text-xs font-bold px-1.5 py-0.5 rounded ${grade.color} bg-gray-50 border border-gray-200`}
                    >
                      {grade.letter}
                    </span>
                  </span>
                );
              })()}
            {dataQuality && (
              <DataQualityBadge
                score={dataQuality.score}
                dimensions={dataQuality.dimensions}
                recommendations={dataQuality.recommendations}
                size="md"
              />
            )}
            {completeness && (
              <span
                data-testid="completeness-badge"
                className={`text-xs font-medium px-2 py-0.5 rounded ${
                  completeness.level === 'complet'
                    ? 'bg-green-50 text-green-700'
                    : completeness.level === 'partiel'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-red-50 text-red-700'
                }`}
                title={
                  completeness.missing?.length
                    ? `Manquant : ${completeness.missing.join(', ')}`
                    : 'Registre complet'
                }
              >
                {completeness.score}% complet
              </span>
            )}
            <span className="capitalize text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
              {site.usage}
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <MapPin size={14} /> {site.adresse}, {site.code_postal} {site.ville}
            </span>
            <span className="flex items-center gap-1">
              <Ruler size={14} /> {fmtArea(site.surface_m2)}
            </span>
            {freshness && <FreshnessIndicator freshness={freshness} size="sm" />}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setShowBacs(true)}>
            <ShieldCheck size={14} className="mr-1" />
            Évaluer <Explain term="decret_bacs">BACS</Explain>
          </Button>
          <Button variant="outline" onClick={() => setShowIntake(true)}>
            <ClipboardCheck size={14} className="mr-1" />
            Compléter les données
          </Button>
          <Button variant="secondary" onClick={() => navigate(`/regops/${site.id}`)}>
            Evaluation RegOps
          </Button>
        </div>
      </div>

      {/* D.1: Bandeau données partielles */}
      {dataQuality && dataQuality.score < 50 && (
        <div
          className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg"
          data-testid="dq-partial-banner"
        >
          <AlertTriangle size={14} className="text-amber-600 shrink-0" />
          <span className="text-xs text-amber-800">
            Données partielles (score {Math.round(dataQuality.score)}/100) — les KPIs peuvent être
            imprécis.
          </span>
          <button
            onClick={() => setShowIntake(true)}
            className="ml-auto text-xs font-semibold text-amber-700 hover:text-amber-900"
          >
            Compléter les données
          </button>
        </div>
      )}

      {/* D.2: Bandeau données périmées */}
      {freshness && (freshness.status === 'expired' || freshness.status === 'no_data') && (
        <div
          className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg"
          data-testid="freshness-expired-banner"
        >
          <AlertTriangle size={14} className="text-red-600 shrink-0" />
          <span className="text-xs text-red-800">
            Données périmées (
            {freshness.staleness_days > 900 ? 'aucune donnée' : `${freshness.staleness_days} jours`}
            ) — les KPIs affichés peuvent être obsolètes.
          </span>
          <button
            onClick={() => setShowIntake(true)}
            className="ml-auto text-xs font-semibold text-red-700 hover:text-red-900"
          >
            Importer
          </button>
        </div>
      )}

      {/* 3 Mini KPIs */}
      <div
        className={`flex gap-4${(dataQuality && dataQuality.score < 50) || (freshness && freshness.status === 'expired') ? ' opacity-60' : ''}`}
      >
        <MiniKpi
          icon={Zap}
          label="Conso annuelle"
          value={fmtNum((site.conso_kwh_an || 0) / 1000, 0, 'MWh')}
          color="text-blue-600"
        />
        <MiniKpi
          icon={BadgeEuro}
          label="Risque €"
          value={fmtEurFull(site.risque_eur)}
          color="text-red-600"
        />
        <MiniKpi
          icon={AlertTriangle}
          label="Anomalies"
          value={`${site.anomalies_count ?? 0}`}
          color="text-amber-600"
        />
        <MiniKpi
          icon={BarChart3}
          label="Intensité"
          value={
            site.surface_m2 > 0
              ? `${Math.round((site.conso_kwh_an || 0) / site.surface_m2)} kWh/m²`
              : '—'
          }
          color="text-indigo-600"
        />
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={activeTab} onChange={handleSetTab} />

      {/* Tab content */}
      {activeTab === 'resume' && (
        <TabResume site={site} onSegmentationClick={() => setShowSegModal(true)} />
      )}
      {activeTab === 'conso' && <TabConsoSite siteId={site.id} siteName={site.nom} />}
      {activeTab === 'factures' && (
        <div className="space-y-4 pt-6">
          <SiteContractsSummary siteId={site.id} />
          <SiteBillingMini siteId={site.id} />
          <div className="flex justify-end mt-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`/achat-assistant?site_id=${site.id}`)}
            >
              Créer scénario d&apos;achat
            </Button>
            <button
              className="text-xs text-amber-600 hover:underline"
              onClick={() => navigate(`/billing?site_id=${site.id}`)}
            >
              Voir timeline complète
            </button>
          </div>
        </div>
      )}
      {activeTab === 'reconciliation' && <TabReconciliation site={site} />}
      {activeTab === 'conformite' && <TabConformite site={site} />}
      {activeTab === 'actions' && <TabActionsSite siteId={site.id} />}

      {/* BACS Wizard modal */}
      {showBacs && <BacsWizard siteId={site.id} onClose={() => setShowBacs(false)} />}

      {/* Smart Intake Wizard modal */}
      {showIntake && <IntakeWizard siteId={site.id} onClose={() => setShowIntake(false)} />}

      {/* Segmentation Questionnaire modal */}
      {showSegModal && <SegmentationQuestionnaireModal onClose={() => setShowSegModal(false)} />}
    </div>
  );
}
