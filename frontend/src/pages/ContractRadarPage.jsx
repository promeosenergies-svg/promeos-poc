/**
 * PROMEOS — V99 Contract Renewal Radar Page
 * /renouvellements
 * Portfolio-level renewal radar for DAF / Direction Achats.
 * Table + ScenarioDrawer + ScenarioSummaryModal.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import {
  CalendarRange,
  ChevronRight,
  Printer,
  AlertTriangle,
  CheckCircle,
  XCircle,
  UserCheck,
  HelpCircle,
} from 'lucide-react';
import { PageShell, Badge, Button, EmptyState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SkeletonTable } from '../ui/Skeleton';
import Drawer from '../ui/Drawer';
import Modal from '../ui/Modal';
import {
  getContractRadar,
  getContractPurchaseScenarios,
  createActionsFromScenario,
  getContractScenarioSummary,
  getSegmentationProfile,
} from '../services/api';
import { track } from '../services/tracker';
import { fmtDateFR } from '../utils/format';
import { useScope } from '../contexts/ScopeContext';
import SegmentationQuestionnaireModal from '../components/SegmentationQuestionnaireModal';

/* ── Urgency mapping ── */
const URGENCY_CFG = {
  red: { badge: 'crit', label: 'Critique' },
  orange: { badge: 'warn', label: 'Urgent' },
  yellow: { badge: 'info', label: 'Attention' },
  green: { badge: 'ok', label: 'OK' },
  gray: { badge: 'neutral', label: 'Serein' },
};

const STATUS_CFG = {
  expired: { icon: XCircle, color: 'text-red-500', label: 'Expiré' },
  expiring: { icon: AlertTriangle, color: 'text-amber-500', label: 'Bientôt' },
  active: { icon: CheckCircle, color: 'text-green-500', label: 'Actif' },
};

const RISK_CFG = {
  faible: { badge: 'ok', label: 'Faible' },
  modéré: { badge: 'warn', label: 'Modéré' },
  élevé: { badge: 'crit', label: 'Élevé' },
};

const HORIZON_OPTIONS = [
  { value: 30, label: '30 j' },
  { value: 60, label: '60 j' },
  { value: 90, label: '90 j' },
  { value: 180, label: '180 j' },
  { value: 365, label: '1 an' },
];

/* ── RadarFilterBar ── */
function RadarFilterBar({ horizon, onHorizonChange, stats, total }) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="flex items-center gap-1.5 bg-white border border-gray-200 rounded-lg px-1 py-0.5">
        {HORIZON_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onHorizonChange(opt.value)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              horizon === opt.value
                ? 'bg-blue-50 text-blue-700'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3 ml-auto text-xs font-medium">
        <span className="text-gray-500">
          {total} contrat{total > 1 ? 's' : ''}
        </span>
        {stats && (
          <>
            <span className="text-red-600">
              {stats.expired} expiré{stats.expired > 1 ? 's' : ''}
            </span>
            <span className="text-amber-600">{stats.expiring} bientôt</span>
            <span className="text-green-600">
              {stats.active} actif{stats.active > 1 ? 's' : ''}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

/* ── ScenarioCard ── */
function ScenarioCard({ scenario, onCreateActions, creating }) {
  const risk = RISK_CFG[scenario.risk_level] || RISK_CFG.faible;
  return (
    <div
      className={`p-4 rounded-xl border ${
        scenario.is_current ? 'border-blue-300 bg-blue-50/30' : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="font-semibold text-sm text-gray-900">{scenario.label}</h4>
            <Badge status={risk.badge}>{risk.label}</Badge>
            {scenario.is_current && <Badge status="info">Contrat actuel</Badge>}
          </div>
          <p className="text-xs text-gray-500 mt-1">{scenario.description}</p>
        </div>
        {scenario.estimate_eur != null && (
          <span className="text-sm font-semibold text-gray-700 whitespace-nowrap ml-3">
            ~{Math.round(scenario.estimate_eur).toLocaleString('fr-FR')} EUR/an
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
        <div>
          <p className="font-medium text-green-700 mb-1">Avantages</p>
          <ul className="space-y-0.5 text-gray-600">
            {scenario.avantages?.map((a, i) => (
              <li key={i}>+ {a}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="font-medium text-red-700 mb-1">Inconvénients</p>
          <ul className="space-y-0.5 text-gray-600">
            {scenario.inconvenients?.map((a, i) => (
              <li key={i}>- {a}</li>
            ))}
          </ul>
        </div>
      </div>

      {scenario.prerequis?.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          <span className="font-medium">Prérequis :</span> {scenario.prerequis.join(' · ')}
        </div>
      )}

      <div className="mt-3 flex justify-end">
        <Button size="sm" onClick={() => onCreateActions(scenario.id)} disabled={creating}>
          {creating ? 'Création...' : "Créer plan d'actions"}
        </Button>
      </div>
    </div>
  );
}

/* ── ScenarioDrawer ── */
function ScenarioDrawer({ contract, open, onClose, segProfile }) {
  const [scenarios, setScenarios] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(null);
  const [toast, setToast] = useState(null);
  const [showSummary, setShowSummary] = useState(false);

  useEffect(() => {
    if (open && contract?.contract_id) {
      setLoading(true);
      setScenarios(null);
      getContractPurchaseScenarios(contract.contract_id)
        .then(setScenarios)
        .catch(() => setScenarios(null))
        .finally(() => setLoading(false));
    }
  }, [open, contract?.contract_id]);

  const handleCreateActions = useCallback(
    async (scenarioId) => {
      if (!contract?.contract_id) return;
      setCreating(scenarioId);
      try {
        const result = await createActionsFromScenario(contract.contract_id, scenarioId);
        track('v99_actions_from_scenario', {
          contract_id: contract.contract_id,
          scenario: scenarioId,
        });
        setToast(
          `${result.actions_created} action${result.actions_created > 1 ? 's' : ''} créée${result.actions_created > 1 ? 's' : ''}${result.actions_existing ? ` (${result.actions_existing} existante${result.actions_existing > 1 ? 's' : ''})` : ''}`
        );
        setTimeout(() => setToast(null), 4000);
      } catch {
        setToast('Erreur lors de la création');
        setTimeout(() => setToast(null), 3000);
      } finally {
        setCreating(null);
      }
    },
    [contract?.contract_id]
  );

  return (
    <>
      <Drawer open={open} onClose={onClose} title="Scénarios d'achat" wide>
        {/* Contract header */}
        {contract && (
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 mb-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-900">{contract.supplier_name}</p>
                <p className="text-xs text-gray-500">
                  {contract.site_nom} · {contract.energy_type || 'N/A'} · Fin :{' '}
                  {fmtDateFR(contract.end_date)}
                </p>
              </div>
              <Button variant="secondary" size="sm" onClick={() => setShowSummary(true)}>
                <Printer size={14} className="mr-1" /> Résumé 1 page
              </Button>
            </div>
          </div>
        )}

        {/* V100: Segmentation context */}
        {segProfile?.has_profile && (
          <div className="mb-3 p-2.5 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2">
            <UserCheck size={14} className="text-blue-600 flex-shrink-0" />
            <span className="text-xs text-blue-700">
              Profil <strong>{segProfile.segment_label || segProfile.typologie}</strong> — les
              scénarios ci-dessous sont adaptés à votre activité.
            </span>
          </div>
        )}

        {/* Toast */}
        {toast && (
          <div className="mb-3 p-2.5 bg-green-50 border border-green-200 rounded-lg text-xs text-green-700 font-medium">
            {toast}
          </div>
        )}

        {loading && (
          <div className="py-12 text-center text-sm text-gray-400">Chargement des scénarios...</div>
        )}

        {!loading && scenarios?.scenarios && (
          <div className="space-y-4">
            {scenarios.scenarios.map((sc) => (
              <ScenarioCard
                key={sc.id}
                scenario={sc}
                onCreateActions={handleCreateActions}
                creating={creating === sc.id}
              />
            ))}
          </div>
        )}

        {!loading && !scenarios && (
          <div className="py-12 text-center text-sm text-gray-400">Aucun scénario disponible</div>
        )}
      </Drawer>

      {showSummary && contract && (
        <ScenarioSummaryModal
          contractId={contract.contract_id}
          siteName={contract.site_nom}
          onClose={() => setShowSummary(false)}
        />
      )}
    </>
  );
}

/* ── ScenarioSummaryModal ── */
function ScenarioSummaryModal({ contractId, siteName, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getContractScenarioSummary(contractId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [contractId]);

  return (
    <Modal open onClose={onClose} title={`Résumé scénarios — ${siteName || 'Contrat'}`} wide>
      <div className="print-content">
        {loading && <div className="py-8 text-center text-sm text-gray-400">Chargement...</div>}

        {!loading && data && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Fournisseur : {data.supplier_name}</span>
              <span>Fin : {fmtDateFR(data.end_date)}</span>
            </div>

            {data.scenarios?.map((sc) => {
              const risk = RISK_CFG[sc.risk_level] || RISK_CFG.faible;
              return (
                <div key={sc.id} className="p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-sm">{sc.label}</span>
                    <Badge status={risk.badge}>{risk.label}</Badge>
                    {sc.is_current && <Badge status="info">Actuel</Badge>}
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{sc.description}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="font-medium text-green-700">Avantages</p>
                      {sc.avantages?.map((a, i) => (
                        <p key={i} className="text-gray-600">
                          + {a}
                        </p>
                      ))}
                    </div>
                    <div>
                      <p className="font-medium text-red-700">Inconvénients</p>
                      {sc.inconvenients?.map((a, i) => (
                        <p key={i} className="text-gray-600">
                          - {a}
                        </p>
                      ))}
                    </div>
                  </div>
                  {sc.estimate_eur != null && (
                    <p className="mt-1 text-xs font-medium text-gray-700">
                      Estimation : ~{Math.round(sc.estimate_eur).toLocaleString('fr-FR')} EUR/an
                    </p>
                  )}
                </div>
              );
            })}

            <div className="flex justify-end gap-2 pt-2 print:hidden">
              <Button variant="secondary" onClick={onClose}>
                Fermer
              </Button>
              <Button onClick={() => window.print()}>
                <Printer size={14} className="mr-1" /> Imprimer
              </Button>
            </div>
          </div>
        )}

        {!loading && !data && (
          <div className="py-8 text-center text-sm text-gray-400">
            Impossible de charger le résumé
          </div>
        )}
      </div>
    </Modal>
  );
}

/* ── SegmentationBadge (inline) ── */
function SegmentationBadge({ profile }) {
  if (!profile?.has_profile) return null;
  const label = profile.segment_label || profile.typologie;
  const score = Math.round(profile.confidence_score);
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg">
      <UserCheck size={14} className="text-blue-600" />
      <span className="text-xs font-medium text-blue-700">{label}</span>
      <Badge status={score >= 70 ? 'ok' : score >= 40 ? 'warn' : 'crit'}>{score}%</Badge>
    </div>
  );
}

/* ── Main Page ── */
export default function ContractRadarPage() {
  const { selectedSiteId } = useScope();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [horizon, setHorizon] = useState(90);
  const [selectedContract, setSelectedContract] = useState(null);
  const [segProfile, setSegProfile] = useState(null);
  const [showSegModal, setShowSegModal] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = { days: horizon };
    if (selectedSiteId) params.site_id = selectedSiteId;
    getContractRadar(params)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
    track('v99_radar_view', { horizon, site_id: selectedSiteId });
  }, [horizon, selectedSiteId]);

  // V100: load segmentation profile once
  useEffect(() => {
    getSegmentationProfile()
      .then(setSegProfile)
      .catch(() => {});
  }, []);

  const contracts = useMemo(() => data?.contracts || [], [data]);

  return (
    <PageShell
      icon={CalendarRange}
      title="Renouvellements contrats"
      subtitle="Radar des échéances et scénarios d'achat"
    >
      <div className="flex items-center gap-3 mb-1">
        <RadarFilterBar
          horizon={horizon}
          onHorizonChange={setHorizon}
          stats={data?.stats}
          total={data?.total || 0}
        />
        <SegmentationBadge profile={segProfile} />
      </div>

      {/* V101: Segmentation confidence nudge */}
      {segProfile?.has_profile && segProfile.confidence_score < 50 && (
        <div className="mb-3 flex items-center gap-2 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-lg">
          <HelpCircle size={16} className="text-amber-500 flex-shrink-0" />
          <span className="text-sm text-amber-800 flex-1">
            Profil à {Math.round(segProfile.confidence_score)}% — répondez à 2 questions pour
            affiner vos scénarios
          </span>
          <button
            onClick={() => setShowSegModal(true)}
            className="px-3 py-1 text-xs font-medium text-amber-700 bg-amber-100 border border-amber-300 rounded-lg hover:bg-amber-200 transition"
          >
            Affiner
          </button>
        </div>
      )}

      {loading && <SkeletonTable rows={6} cols={7} />}

      {!loading && contracts.length === 0 && (
        <EmptyState
          icon={CalendarRange}
          title="Aucun contrat dans l'horizon"
          description="Aucun contrat ne nécessite d'attention sur cette période."
        />
      )}

      {!loading && contracts.length > 0 && contracts.length < 5 && (
        <div className="text-center py-4 text-gray-400 text-sm">
          Seuls les contrats arrivant à échéance dans les {horizon} prochains jours sont affichés.
        </div>
      )}

      {!loading && contracts.length > 0 && (
        <Table>
          <Thead>
            <Tr>
              <Th>Site</Th>
              <Th>Fournisseur</Th>
              <Th>Fin</Th>
              <Th>Jours</Th>
              <Th>Indexation</Th>
              <Th>État données</Th>
              <Th>Payeur</Th>
              <Th></Th>
            </Tr>
          </Thead>
          <Tbody>
            {contracts.map((ct) => {
              const urg = URGENCY_CFG[ct.urgency] || URGENCY_CFG.gray;
              const st = STATUS_CFG[ct.contract_status] || STATUS_CFG.active;
              const StIcon = st.icon;
              return (
                <Tr
                  key={ct.contract_id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => setSelectedContract(ct)}
                >
                  <Td>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{ct.site_nom}</p>
                      {ct.portfolio_nom && (
                        <p className="text-[11px] text-gray-400">{ct.portfolio_nom}</p>
                      )}
                    </div>
                  </Td>
                  <Td className="text-sm text-gray-700">{ct.supplier_name || '—'}</Td>
                  <Td>
                    <div className="flex items-center gap-1.5">
                      <StIcon size={14} className={st.color} />
                      <span className="text-xs text-gray-600">{fmtDateFR(ct.end_date)}</span>
                    </div>
                  </Td>
                  <Td>
                    <Badge status={urg.badge}>
                      {ct.days_to_end != null ? `${ct.days_to_end}j` : '—'}
                    </Badge>
                  </Td>
                  <Td className="text-xs text-gray-600">{ct.indexation_label || '—'}</Td>
                  <Td>
                    {ct.readiness_score != null ? (
                      <div className="flex items-center gap-1.5">
                        <div
                          className={`h-1.5 w-8 rounded-full ${
                            ct.readiness_score >= 80
                              ? 'bg-green-400'
                              : ct.readiness_score >= 50
                                ? 'bg-amber-400'
                                : 'bg-red-400'
                          }`}
                        >
                          <div
                            className="h-full bg-current rounded-full"
                            style={{ width: `${ct.readiness_score}%` }}
                          />
                        </div>
                        <span className="text-[11px] text-gray-500">{ct.readiness_score}%</span>
                      </div>
                    ) : (
                      '—'
                    )}
                  </Td>
                  <Td className="text-xs text-gray-600">{ct.payer_entity || '—'}</Td>
                  <Td>
                    <button className="p-1 rounded hover:bg-gray-100 transition-colors">
                      <ChevronRight size={16} className="text-gray-400" />
                    </button>
                  </Td>
                </Tr>
              );
            })}
          </Tbody>
        </Table>
      )}

      <ScenarioDrawer
        contract={selectedContract}
        open={!!selectedContract}
        onClose={() => setSelectedContract(null)}
        segProfile={segProfile}
      />

      {/* V101: Segmentation questionnaire modal */}
      {showSegModal && (
        <SegmentationQuestionnaireModal
          onClose={() => setShowSegModal(false)}
          onComplete={() => {
            getSegmentationProfile()
              .then(setSegProfile)
              .catch(() => {});
          }}
        />
      )}
    </PageShell>
  );
}
