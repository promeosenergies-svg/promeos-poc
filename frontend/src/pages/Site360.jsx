/**
 * PROMEOS - Site 360 (/sites/:siteId)
 * Header + badges + 3 mini KPIs + tabs (Resume, Conso, Factures, Conformite, Actions)
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  ShieldCheck,
  Zap,
  AlertTriangle,
  MapPin,
  BookOpen,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
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
  getUnifiedAnomalies,
  getSitePaymentInfo,
  getReconciliation,
  applyReconciliationFix,
  getReconciliationHistory,
  getReconciliationEvidenceCsv,
  getReconciliationEvidenceSummary,
  patrimoineDeliveryPoints,
  getTopRecommendation,
  createAction,
  getEnergyIntensity,
} from '../services/api';
import { buildKbRecoActionPayload } from '../models/kbRecoActionModel';
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
import Site360Sol from './Site360Sol';
import { normalizeCompliance } from './sites/sol_presenters';
import { FlexPotentialCard, BacsFlexLink } from '../components/flex';
import SiteBillingMini from '../components/SiteBillingMini';
import SiteContractsSummary from '../components/SiteContractsSummary';
import SegmentationWidget from '../components/SegmentationWidget';
import SegmentationQuestionnaireModal from '../components/SegmentationQuestionnaireModal';
import TabConsoSite from '../components/TabConsoSite';
import LoadProfileCard from '../components/analytics/LoadProfileCard';
import EnergySignatureCard from '../components/analytics/EnergySignatureCard';
import RecommendationsCard from '../components/analytics/RecommendationsCard';
import TabPuissance from '../components/power/TabPuissance';
import TabActionsSite from '../components/TabActionsSite';
import { fmtNum, fmtEurFull, fmtArea as _fmtArea } from '../utils/format';
import { getBenchmark, getIntensityRatio } from '../utils/benchmarks';
import { setActiveSite } from '../utils/activeSite';
import DataQualityBadge from '../components/DataQualityBadge';
import _FreshnessIndicator from '../components/FreshnessIndicator';
import SiteIntelligencePanel from '../components/SiteIntelligencePanel';
import {
  getDataQualityScore,
  getSiteFreshness,
  getSiteCompleteness,
  getEnergySignature,
} from '../services/api';

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
  { id: 'analytics', label: 'Analytics' },
  { id: 'factures', label: 'Factures' },
  { id: 'reconciliation', label: 'Réconciliation' },
  { id: 'conformite', label: 'Conformité' },
  { id: 'actions', label: 'Actions' },
  { id: 'puissance', label: 'Puissance' },
  { id: 'usages', label: 'Usages' },
];

function _MiniKpi({ icon: Icon, label, value, color, children }) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 rounded-lg">
      <Icon size={18} className={color} />
      <div>
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-sm font-bold text-gray-800">{value}</p>
      </div>
      {children}
    </div>
  );
}

function TabResume({
  site,
  orgId,
  unifiedCount,
  anomalies = [],
  anomLoading = false,
  onSegmentationClick,
  topReco,
  intensityData,
}) {
  const [deliveryPoints, setDeliveryPoints] = useState([]);
  const [dpLoading, setDpLoading] = useState(true);
  const [showAllAnomalies, setShowAllAnomalies] = useState(false);
  const [recoActionStatus, setRecoActionStatus] = useState(null); // null | 'creating' | 'created' | 'error'

  // B2-4: Fetch delivery points
  useEffect(() => {
    if (!site?.id) return;
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

  const {
    hasIntensity,
    intensity,
    intensityPrimary,
    benchmark,
    intensityRatio,
    intensityPct,
    confidence,
  } = intensityData;

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
                  <p className="text-lg font-bold text-amber-700">
                    {unifiedCount ?? site.anomalies_count ?? 0}
                  </p>
                </div>
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-gray-500">Points de livraison</p>
                  <p className="text-lg font-bold text-green-700">
                    {deliveryPoints.length || site.nb_compteurs || '—'}
                    <span className="text-sm font-normal text-gray-500 ml-1">actifs</span>
                  </p>
                  {deliveryPoints.length > 0 &&
                    (() => {
                      const elecCount = deliveryPoints.filter(
                        (d) => d.energy_type === 'elec' || d.energy_type === 'electricity'
                      ).length;
                      const gazCount = deliveryPoints.filter(
                        (d) => d.energy_type === 'gaz' || d.energy_type === 'gas'
                      ).length;
                      const parts = [];
                      if (elecCount) parts.push(`${elecCount} élec`);
                      if (gazCount) parts.push(`${gazCount} gaz`);
                      return parts.length > 0 ? (
                        <p className="text-xs text-gray-400 mt-1">{parts.join(' · ')}</p>
                      ) : null;
                    })()}
                </div>
              </div>
              {/* Intensité énergétique — données backend #146 (Yannick) + ratio OID */}
              {hasIntensity && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500">
                    <Explain term="intensite_energetique">Intensité énergétique</Explain>
                  </p>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-lg font-bold text-gray-800">{intensity}</span>
                    <span className="text-sm text-gray-500">kWhEF/m²</span>
                    {intensityPrimary != null && (
                      <span className="text-xs text-gray-400 ml-1">
                        ({Math.round(intensityPrimary)} kWhEP/m²)
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <div className="flex-1 h-1.5 rounded bg-gray-200 overflow-hidden">
                      <div
                        className={`h-full rounded ${
                          intensityRatio <= 1
                            ? 'bg-green-500'
                            : intensityRatio <= 1.5
                              ? 'bg-amber-500'
                              : 'bg-red-500'
                        }`}
                        style={{ width: `${intensityPct}%` }}
                      />
                    </div>
                  </div>
                  <p className="text-[10px] text-gray-400 mt-1">
                    {intensityRatio <= 1 ? '✓ ' : ''}
                    {intensityRatio.toFixed(1)}× benchmark OID ({benchmark} kWh/m²)
                    {confidence && confidence !== 'none' && <> · confiance {confidence}</>}
                  </p>
                </div>
              )}
            </CardBody>
          </Card>

          {/* V96: Payment info */}
          <PaymentInfoCard siteId={site.id} />

          {/* Reco principale — KB-driven */}
          <Card className="border-l-4 border-l-blue-500">
            <CardBody>
              <p className="text-xs text-gray-500 uppercase font-semibold mb-1">
                Recommandation principale
              </p>
              <p className="text-sm text-gray-800 font-medium">
                {topReco?.label || 'Chargement...'}
              </p>
              {topReco?.detail && <p className="text-xs text-gray-500 mt-1">{topReco.detail}</p>}
              {topReco?.source === 'kb' && (
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                  {topReco.ice_score != null && (
                    <span className="px-2 py-0.5 rounded bg-green-50 text-green-700 font-medium">
                      ICE {topReco.ice_score.toFixed(2)}
                    </span>
                  )}
                  {topReco.savings_eur > 0 && (
                    <span>~{Math.round(topReco.savings_eur).toLocaleString('fr-FR')} €/an</span>
                  )}
                  <span>Source : KB</span>
                </div>
              )}
              <Button
                size="sm"
                className="mt-3"
                disabled={recoActionStatus === 'creating' || recoActionStatus === 'created'}
                onClick={async () => {
                  if (!topReco?.code || recoActionStatus === 'created') return;
                  setRecoActionStatus('creating');
                  try {
                    const payload = buildKbRecoActionPayload({
                      orgId,
                      siteId: site.id,
                      siteName: site.nom,
                      reco: {
                        id: 0,
                        recommendation_code: topReco.code,
                        title: topReco.label,
                        ice_score: topReco.ice_score,
                        estimated_savings_eur_year: topReco.savings_eur,
                      },
                      topSeverity: 'medium',
                    });
                    await createAction(payload);
                    setRecoActionStatus('created');
                  } catch {
                    setRecoActionStatus('error');
                  }
                }}
              >
                {recoActionStatus === 'creating'
                  ? 'Création…'
                  : recoActionStatus === 'created'
                    ? '✓ Action créée'
                    : recoActionStatus === 'error'
                      ? 'Réessayer'
                      : 'Créer une action'}
              </Button>
              {topReco?.total_recos > 1 && (
                <Button
                  size="sm"
                  className="ml-2"
                  onClick={() => {
                    const el = document.querySelector('[data-testid="intelligence-panel"]');
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }}
                >
                  Voir {topReco.total_recos} recommandations
                </Button>
              )}
            </CardBody>
          </Card>

          {/* B2-4: Points de livraison (PDL) — déplacé ici pour équilibrer */}
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

          {/* Accès rapide cross-module */}
          <Card>
            <div className="px-5 py-3 border-b border-gray-100">
              <h3 className="text-xs font-semibold text-gray-500 uppercase">Accès rapide</h3>
            </div>
            <CardBody className="py-2">
              <div className="grid grid-cols-2 gap-1">
                {[
                  { to: 'usages', icon: BarChart3, label: 'Usages énergétiques' },
                  { to: 'billing', icon: Zap, label: 'Bill Intelligence' },
                  { to: 'conformite', icon: ShieldCheck, label: 'Conformité' },
                  { to: 'achat-assistant', icon: FileText, label: 'Radar contrats' },
                  { to: 'actions', icon: Wrench, label: 'Actions' },
                ].map(({ to, icon: Icon, label }) => (
                  <Link
                    key={to}
                    to={`/${to}?site_id=${site.id}`}
                    className="flex items-center gap-2 px-2 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded focus-visible:ring-2 focus-visible:ring-blue-400"
                  >
                    <Icon size={14} /> {label}
                  </Link>
                ))}
              </div>
            </CardBody>
          </Card>

          {/* V100: Segmentation profile — déplacé ici pour équilibrer */}
          <SegmentationWidget onSegmentationClick={onSegmentationClick} />
        </div>

        {/* Right column — Intelligence KB en premier (cf maquette) */}
        <div className="space-y-4">
          <SiteIntelligencePanel siteId={site.id} site={site} />

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
              <>
                <div className="overflow-x-auto">
                  <Table className="table-fixed w-full">
                    <Thead>
                      <tr>
                        <Th className="w-[130px]">Type</Th>
                        <Th className="w-[80px]">Sévérité</Th>
                        <Th>Message</Th>
                        <Th className="text-right w-[80px]">Impact</Th>
                      </tr>
                    </Thead>
                    <Tbody>
                      {anomalies.slice(0, showAllAnomalies ? undefined : 8).map((a, idx) => (
                        <Tr key={a.id || idx}>
                          <Td>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                  a.source === 'analytique'
                                    ? 'bg-purple-50 text-purple-600'
                                    : 'bg-blue-50 text-blue-600'
                                }`}
                              >
                                {a.source === 'analytique' ? 'Analyse' : 'Données'}
                              </span>
                              <span className="text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                                {a.code || a.anomaly_type}
                              </span>
                            </div>
                          </Td>
                          <Td>
                            <Badge status={SEV_BADGE[a.severity] || 'info'}>{a.severity}</Badge>
                          </Td>
                          <Td className="text-sm truncate" title={a.title_fr}>
                            {a.title_fr}
                            {a.meter_count > 1 && (
                              <span className="ml-1 text-xs text-gray-400">
                                (×{a.meter_count} compteurs)
                              </span>
                            )}
                          </Td>
                          <Td className="text-right font-medium">
                            {a.business_impact?.estimated_risk_eur ? (
                              <span className="text-red-600">
                                {fmtEurFull(a.business_impact.estimated_risk_eur)}
                              </span>
                            ) : a.deviation_pct != null ? (
                              <span className="text-gray-500">
                                {a.deviation_pct > 0 ? '+' : ''}
                                {a.deviation_pct}%
                              </span>
                            ) : null}
                          </Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </div>
                {anomalies.length > 8 && !showAllAnomalies && (
                  <div className="px-5 py-2 border-t border-gray-100">
                    <button
                      onClick={() => setShowAllAnomalies(true)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Voir les {anomalies.length} anomalies
                    </button>
                  </div>
                )}
              </>
            )}
          </Card>

          {/* Flex potential — intégré dans la colonne droite */}
          <FlexPotentialCard siteId={site.id} />
        </div>
      </div>
      {/* /grid-cols-2 */}

      {/* Trust badge footer */}
      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg mt-2">
        <TrustBadge
          source="PROMEOS KB"
          period={`Analyse pour ${site.nom}`}
          confidence={anomalies.length > 0 ? 'high' : 'medium'}
        />
      </div>
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
    let stale = false;
    getReconciliationEvidenceSummary(site.id)
      .then((data) => {
        if (!stale) setSummary(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
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
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
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

      {/* Exit link → full conformité module */}
      <div className="pt-4 border-t border-gray-100 mt-4">
        <Link
          to="/conformite"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 hover:underline transition"
        >
          <ShieldCheck size={13} /> Voir la conformité complète du portefeuille
          <ExternalLink size={11} />
        </Link>
      </div>
    </div>
  );
}

/** Mini panneau signature énergétique pour l'onglet Usages */
function MiniSignaturePanel({ siteId, navigate }) {
  const [sig, setSig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getEnergySignature(siteId)
      .then(setSig)
      .catch(() => setSig(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading) {
    return (
      <div className="space-y-4 pt-4">
        <div className="rounded-xl border border-gray-100 bg-white p-5 animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4" />
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-gray-100 rounded-lg" />
            <div className="h-16 bg-gray-100 rounded-lg" />
            <div className="h-16 bg-gray-100 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  const data = sig?.signature;
  const benchmark = sig?.benchmark;

  return (
    <div className="space-y-4 pt-4">
      <div className="rounded-xl border border-gray-100 bg-white p-5">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Signature énergétique
        </p>
        {data ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Baseload */}
            <div className="rounded-lg bg-blue-50 px-4 py-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-blue-500 mb-0.5">
                Baseload
              </p>
              <p className="text-lg font-bold text-gray-900">
                {data.baseload_kwh_day?.toLocaleString('fr-FR') ?? '--'}{' '}
                <span className="text-xs font-normal text-gray-500">kWh/j</span>
              </p>
              {benchmark?.baseload_expected != null && (
                <p className="text-[10px] text-gray-400 mt-0.5">
                  réf. {benchmark.baseload_expected} kWh/j
                </p>
              )}
            </div>
            {/* Thermosensibilité */}
            <div className="rounded-lg bg-amber-50 px-4 py-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-amber-500 mb-0.5">
                Thermosensibilité
              </p>
              <p className="text-lg font-bold text-gray-900">
                {data.thermosensitivity_kwh_dju ?? '--'}{' '}
                <span className="text-xs font-normal text-gray-500">kWh/DJU</span>
              </p>
              {benchmark?.thermo_expected != null && (
                <p className="text-[10px] text-gray-400 mt-0.5">
                  réf. {benchmark.thermo_expected} kWh/DJU
                </p>
              )}
            </div>
            {/* R² */}
            <div className="rounded-lg bg-emerald-50 px-4 py-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-emerald-500 mb-0.5">
                R² modèle
              </p>
              <p className="text-lg font-bold text-gray-900">
                {data.r_squared?.toFixed(3) ?? 'N/A'}
              </p>
              <p className="text-[10px] text-gray-400 mt-0.5">
                {data.model_quality ?? 'Qualité inconnue'}
              </p>
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-400 italic py-3">
            Signature non disponible — importez les données de consommation pour activer l'analyse.
          </div>
        )}
      </div>
      <div className="flex justify-end">
        <button
          className="inline-flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800 hover:underline font-medium transition-colors"
          onClick={() => navigate(`/consommations?site_id=${siteId}`)}
        >
          Ouvrir l'analyse complète <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ── TabAnalytics — Profil de charge + Signature énergétique + Recommendations ──
// Les 3 cards exploitent les endpoints Sprint 1-8 :
//   /api/usages/load-profile/{id}
//   /api/usages/energy-signature/{id}/advanced
//   /api/usages/recommendations/generate/{id}
function TabAnalytics({ siteId }) {
  return (
    <div className="space-y-4 pt-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <LoadProfileCard siteId={siteId} />
        <EnergySignatureCard siteId={siteId} />
      </div>
      <RecommendationsCard siteId={siteId} />
    </div>
  );
}

export default function Site360() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { scopedSites, sitesLoading, scope } = useScope();
  // Persist active tab in URL ?tab= so deep links are shareable
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() => {
    return searchParams.get('tab') || window.location.hash.replace('#', '') || 'resume';
  });
  const handleSetTab = useCallback(
    (tab) => {
      setActiveTab(tab);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.set('tab', tab);
          return next;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );
  const [showIntake, setShowIntake] = useState(false);
  const [showBacs, setShowBacs] = useState(false);
  const [showSegModal, setShowSegModal] = useState(false);
  const [siteComplianceScore, setSiteComplianceScore] = useState(null); // A.2
  const [dataQuality, setDataQuality] = useState(null); // D.1
  const [freshness, setFreshness] = useState(null); // D.2
  const [completeness, setCompleteness] = useState(null); // V-registre
  const [unifiedCount, setUnifiedCount] = useState(null);
  const [unifiedPatCount, setUnifiedPatCount] = useState(0);
  const [unifiedKbCount, setUnifiedKbCount] = useState(0);
  const [unifiedAnomalies, setUnifiedAnomalies] = useState([]);
  const [unifiedAnomLoading, setUnifiedAnomLoading] = useState(true);
  const [topReco, setTopReco] = useState(null);
  const [energyIntensity, setEnergyIntensity] = useState(null);

  const site = scopedSites.find((s) => String(s.id) === String(id));

  // Intensité via backend #146 (Yannick), fallback conso_kwh_an/surface_m2
  const intensityFinal =
    energyIntensity?.kWh_m2_final ??
    (site?.surface_m2 > 0 && site?.conso_kwh_an > 0 ? site.conso_kwh_an / site.surface_m2 : null);
  const hasIntensity = intensityFinal != null && intensityFinal > 0;
  const intensity = hasIntensity ? Math.round(intensityFinal) : 0;
  const intensityRatio = hasIntensity ? (getIntensityRatio(intensity, site?.usage) ?? 0) : 0;
  const intensityData = {
    hasIntensity,
    intensity,
    intensityRatio,
    intensityPrimary: energyIntensity?.kWh_m2_primary ?? null,
    benchmark: hasIntensity ? getBenchmark(site.usage) : 0,
    intensityPct: Math.min(intensityRatio / 3, 1) * 100,
    confidence: energyIntensity?.confidence ?? null,
  };

  // Persist active site for contextual nav
  useEffect(() => {
    if (site?.id && site?.nom) setActiveSite(site);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site?.id, site?.nom, site?.statut_conformite]);

  // Unified anomalies (patrimoine + KB) — single fetch, shared by MiniKpi + TabResume
  useEffect(() => {
    if (!site?.id) return;
    let stale = false;
    setUnifiedAnomLoading(true);
    getUnifiedAnomalies(site.id)
      .then((data) => {
        if (!stale) {
          setUnifiedCount(data.total);
          setUnifiedPatCount(data.patrimoine_count || 0);
          setUnifiedKbCount(data.analytique_count || 0);
          setUnifiedAnomalies(data.anomalies || []);
        }
      })
      .catch(() => {
        return getPatrimoineAnomalies(site.id)
          .then((data) => {
            if (!stale) {
              const anoms = (data.anomalies || []).map((a) => ({ ...a, source: 'patrimoine' }));
              setUnifiedAnomalies(anoms);
              setUnifiedCount(anoms.length);
            }
          })
          .catch(() => {
            if (!stale) {
              setUnifiedAnomalies([]);
              setUnifiedCount(0);
            }
          });
      })
      .finally(() => {
        if (!stale) setUnifiedAnomLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [site?.id]);

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

  // Top recommendation (for header KPI card + TabResume)
  useEffect(() => {
    if (!site?.id) return;
    setTopReco(null);
    let stale = false;
    getTopRecommendation(site.id)
      .then((data) => {
        if (!stale) setTopReco(data);
      })
      .catch(() => {
        if (!stale)
          setTopReco({
            available: false,
            source: 'fallback',
            label:
              site.statut_conformite === 'non_conforme'
                ? 'Déclarer vos consommations sur OPERAT avant le 30/09/2026'
                : site.statut_conformite === 'a_risque'
                  ? 'Planifier la mise en conformité BACS pour ce site'
                  : 'Maintenir la surveillance et optimiser la consommation',
          });
      });
    return () => {
      stale = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [site?.id]);

  // Energy intensity — backend #146 (Yannick)
  useEffect(() => {
    if (!site?.id) return;
    setEnergyIntensity(null);
    let stale = false;
    getEnergyIntensity(site.id)
      .then((data) => {
        if (!stale) setEnergyIntensity(data?.error ? null : data);
      })
      .catch(() => {
        if (!stale) setEnergyIntensity(null);
      });
    return () => {
      stale = true;
    };
  }, [site?.id]);

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
  const complianceRounded =
    siteComplianceScore?.score != null ? Math.round(siteComplianceScore.score) : null;
  const complianceGrade = complianceRounded != null ? getComplianceGrade(complianceRounded) : null;

  const _COMPLETENESS_STYLES = {
    complet: 'bg-green-50 text-green-700',
    partiel: 'bg-amber-50 text-amber-700',
  };

  return (
    <div className="px-6 py-6 space-y-4">
      {/* Breadcrumb — Org > Entité > Portefeuille > Site */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-500" aria-label="Fil d'Ariane">
        <Link
          to="/patrimoine"
          className="hover:text-blue-600 hover:underline transition flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 rounded"
        >
          <ArrowLeft size={14} />
          {site.organisation_nom || 'Patrimoine'}
        </Link>
        {site.entite_juridique_nom && (
          <>
            <ChevronRight size={12} className="text-gray-300" />
            <Link
              to="/patrimoine"
              className="hover:text-blue-600 hover:underline focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 rounded"
            >
              {site.entite_juridique_nom}
            </Link>
          </>
        )}
        {site.portefeuille_nom && (
          <>
            <ChevronRight size={12} className="text-gray-300" />
            <Link
              to="/patrimoine"
              className="hover:text-blue-600 hover:underline focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-1 rounded"
            >
              {site.portefeuille_nom}
            </Link>
          </>
        )}
        <ChevronRight size={12} className="text-gray-300" />
        <span className="font-medium text-gray-800">{site.nom}</span>
      </nav>

      {/* ── V3 Header: Titre + 1 badge + boutons ── */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{site.nom}</h1>
            <Badge status={badge.status}>{badge.label}</Badge>
          </div>
          <p className="text-sm text-gray-400 flex items-center gap-2">
            <MapPin size={13} className="shrink-0" />
            {site.adresse}, {site.code_postal} {site.ville}
            {freshness && freshness.status === 'up_to_date' && (
              <span className="text-green-600 font-medium ml-1">● À jour</span>
            )}
          </p>
        </div>
        <div className="flex gap-2 shrink-0 pt-1">
          <Button variant="outline" size="sm" onClick={() => setShowBacs(true)}>
            Évaluer BACS
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowIntake(true)}>
            Compléter les données
          </Button>
          <Button size="sm" onClick={() => navigate(`/regops/${site.id}`)}>
            Evaluation RegOps
          </Button>
        </div>
      </div>

      {/* D.1: Bandeau données partielles */}
      {dataQuality && dataQuality.score < 50 && (
        <div
          className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-lg mb-3"
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
          className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg mb-3"
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

      {/* ── V3: 4 KPI Cards (dominant) ── */}
      <div
        className={`grid grid-cols-4 gap-3 mb-3${(dataQuality && dataQuality.score < 50) || (freshness && freshness.status === 'expired') ? ' opacity-60' : ''}`}
      >
        {/* Conso + intensité intégrée */}
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Consommation annuelle</p>
          <p className="text-xl font-bold text-blue-600">
            {fmtNum((site.conso_kwh_an || 0) / 1000, 0, 'MWh')}
          </p>
          {hasIntensity && (
            <p className="text-[10px] text-gray-400 mt-1">
              {intensity} kWh/m²
              {' · '}
              <span
                className={`font-semibold ${
                  intensityRatio <= 1
                    ? 'text-green-600'
                    : intensityRatio <= 1.5
                      ? 'text-amber-600'
                      : 'text-red-600'
                }`}
              >
                {intensityRatio.toFixed(1)}× OID
              </span>
            </p>
          )}
        </div>

        {/* Risque (accent rouge) */}
        <div className="bg-gray-50 rounded-r-xl p-4 border-l-[2.5px] border-red-600">
          <p className="text-xs text-gray-500 font-medium mb-1">Risque financier</p>
          <p className="text-xl font-bold text-red-600">{fmtEurFull(site.risque_eur)}</p>
          <p className="text-[10px] text-gray-400 mt-1">Pénalité DT estimée</p>
        </div>

        {/* Anomalies */}
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Anomalies</p>
          <p className="text-xl font-bold text-amber-700">
            {unifiedCount ?? site.anomalies_count ?? 0}
          </p>
          {unifiedCount != null && (
            <p className="text-[10px] mt-1">
              <span className="text-blue-700 font-medium">{unifiedPatCount} données</span>
              {' · '}
              <span className="text-purple-700 font-medium">{unifiedKbCount} analyse</span>
            </p>
          )}
        </div>

        {/* Économies potentielles */}
        <div className="bg-gray-50 rounded-xl p-4">
          <p className="text-xs text-gray-500 font-medium mb-1">Économies potentielles</p>
          <p className="text-xl font-bold text-green-700">
            {topReco?.total_savings_eur > 0
              ? `${Math.round(topReco.total_savings_eur / 1000)} k€`
              : '—'}
            <span className="text-sm font-normal text-gray-400">/an</span>
          </p>
          {topReco?.total_recos > 0 && (
            <p className="text-[10px] text-gray-400 mt-1">
              {topReco.total_recos} recommandations KB
            </p>
          )}
        </div>
      </div>

      {/* ── V3: Scores réglementaires (compact mini-badges) ── */}
      <div className="flex gap-2 mb-4">
        {complianceRounded != null && (
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg text-xs"
            data-testid="compliance-score-badge"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                complianceRounded >= 80
                  ? 'bg-green-600'
                  : complianceRounded >= 50
                    ? 'bg-amber-600'
                    : 'bg-red-600'
              }`}
            />
            <span className="text-gray-500">Conformité</span>
            <span
              className={`font-semibold text-[13px] ${getComplianceScoreColor(complianceRounded)}`}
            >
              {complianceRounded}/100
            </span>
            {complianceGrade && (
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${complianceGrade.color} bg-gray-50 border border-gray-200`}
              >
                {complianceGrade.letter}
              </span>
            )}
            <div className="w-12 h-[3px] rounded bg-gray-200 overflow-hidden ml-1">
              <div
                className={`h-full rounded ${
                  complianceRounded >= 80
                    ? 'bg-green-600'
                    : complianceRounded >= 50
                      ? 'bg-amber-600'
                      : 'bg-red-600'
                }`}
                style={{ width: `${complianceRounded}%` }}
              />
            </div>
          </div>
        )}

        {/* DT score from breakdown */}
        {siteComplianceScore?.breakdown?.find((b) => b.framework === 'tertiaire_operat') &&
          (() => {
            const dt = siteComplianceScore.breakdown.find(
              (b) => b.framework === 'tertiaire_operat'
            );
            const dtScore = Math.round(dt.score);
            const dtGrade = dtScore >= 80 ? 'A' : dtScore >= 60 ? 'B' : dtScore >= 40 ? 'C' : 'D';
            return (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg text-xs">
                <span
                  className={`w-2 h-2 rounded-full ${dtScore >= 80 ? 'bg-green-600' : 'bg-amber-600'}`}
                />
                <span className="text-gray-500">Décret Tertiaire</span>
                <span
                  className={`font-semibold text-[13px] ${dtScore >= 80 ? 'text-green-700' : 'text-amber-700'}`}
                >
                  {dtScore}/100
                </span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                    dtScore >= 80 ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  {dtGrade}
                </span>
                <div className="w-12 h-[3px] rounded bg-gray-200 overflow-hidden ml-1">
                  <div
                    className={`h-full rounded ${dtScore >= 80 ? 'bg-green-600' : 'bg-amber-600'}`}
                    style={{ width: `${dtScore}%` }}
                  />
                </div>
              </div>
            );
          })()}

        {/* Complétude */}
        {completeness && (
          <div
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg text-xs"
            data-testid="completeness-badge"
            title={
              completeness.missing?.length
                ? `Manquant : ${completeness.missing.join(', ')}`
                : 'Registre complet'
            }
          >
            <span
              className={`w-2 h-2 rounded-full ${completeness.score >= 80 ? 'bg-green-600' : 'bg-amber-600'}`}
            />
            <span className="text-gray-500">Complétude</span>
            <span
              className={`font-semibold text-[13px] ${completeness.score >= 80 ? 'text-green-700' : 'text-amber-700'}`}
            >
              {completeness.score}%
            </span>
            <div className="w-12 h-[3px] rounded bg-gray-200 overflow-hidden ml-1">
              <div
                className={`h-full rounded ${completeness.score >= 80 ? 'bg-green-600' : 'bg-amber-600'}`}
                style={{ width: `${completeness.score}%` }}
              />
            </div>
          </div>
        )}

        {dataQuality && (
          <DataQualityBadge
            score={dataQuality.score}
            dimensions={dataQuality.dimensions}
            recommendations={dataQuality.recommendations}
            size="sm"
          />
        )}
      </div>

      {/* Tabs */}
      <Tabs tabs={TABS} active={activeTab} onChange={handleSetTab} />

      {/* Tab content */}
      {activeTab === 'resume' && (
        <Site360Sol
          site={site}
          orgId={scope.orgId}
          unifiedCount={unifiedCount}
          anomalies={unifiedAnomalies}
          anomLoading={unifiedAnomLoading}
          topReco={topReco}
          intensityData={intensityData}
          compliance={normalizeCompliance(siteComplianceScore)}
          onOpenTab={handleSetTab}
        />
      )}
      {activeTab === 'conso' && <TabConsoSite siteId={site.id} />}
      {activeTab === 'analytics' && <TabAnalytics siteId={site.id} />}
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
      {activeTab === 'puissance' && <TabPuissance site={site} />}

      {activeTab === 'usages' && <MiniSignaturePanel siteId={site.id} navigate={navigate} />}

      {/* BACS Wizard modal */}
      {showBacs && <BacsWizard siteId={site.id} onClose={() => setShowBacs(false)} />}

      {/* Smart Intake Wizard modal */}
      {showIntake && <IntakeWizard siteId={site.id} onClose={() => setShowIntake(false)} />}

      {/* Segmentation Questionnaire modal */}
      {showSegModal && <SegmentationQuestionnaireModal onClose={() => setShowSegModal(false)} />}
    </div>
  );
}
