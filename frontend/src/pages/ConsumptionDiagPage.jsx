/**
 * PROMEOS — Diagnostic Consommation V2
 * Boucle operationnelle: detecter → prouver → agir.
 * Evidence Drawer, prix editable, workflow ACK/Resolve, cross-page nav.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RTooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  getConsumptionInsights,
  runConsumptionDiagnose,
  seedDemoConsumption,
  patchConsumptionInsight,
  getFlexMini,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { normalizeId } from './consumption/helpers';
import {
  Card,
  CardBody,
  Badge,
  Button,
  PageShell,
  Drawer,
  Tooltip,
  Tabs,
  SkeletonCard,
  EmptyState,
} from '../ui';
import { useToast } from '../ui/ToastProvider';
import { track } from '../services/tracker';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import { fmtEur, fmtKwh, fmtCo2, fmtDateFR, scopeKicker } from '../utils/format';
import SolPageHeader from '../ui/sol/SolPageHeader';
// Sprint 2 Vague B ét8'-bis — HOC SolBriefingHead/Footer factorise grammaire §5.
import SolBriefingHead from '../ui/sol/SolBriefingHead';
import SolBriefingFooter from '../ui/sol/SolBriefingFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';
import { deepLinkWithContext } from '../services/deepLink';
import { toConsoExplorer, toMonitoring, toUsages, toBillIntel } from '../services/routes';
import usePeriodParams from '../hooks/usePeriodParams';
import { SEVERITY_TINT } from '../ui/colorTokens';
import { useElecCo2Factor } from '../contexts/EmissionFactorsContext';
import {
  Zap,
  Info,
  ExternalLink,
  UserCheck,
  CheckCircle2,
  XCircle,
  BarChart3,
  Activity,
} from 'lucide-react';

// ---- Constants ----

const SEVERITY_BADGE = {
  critical: 'crit',
  high: 'warn',
  medium: 'info',
  low: 'neutral',
};

const TYPE_LABELS = {
  hors_horaires: 'Hors horaires',
  base_load: 'Talon élevé',
  pointe: 'Pointe anormale',
  derive: 'Dérive consommation',
  data_gap: 'Lacunes données',
};

const EFFORT_COLOR = {
  high: 'bg-red-50 text-red-700',
  medium: 'bg-amber-50 text-amber-700',
  low: 'bg-green-50 text-green-700',
};

const WORKFLOW_CONFIG = {
  open: { label: 'À traiter', color: 'bg-red-50 text-red-700' },
  ack: { label: 'En cours', color: 'bg-amber-50 text-amber-700' },
  resolved: { label: 'Résolu', color: 'bg-green-50 text-green-700' },
  false_positive: { label: 'Faux positif', color: 'bg-gray-100 text-gray-500' },
};

const DRAWER_TABS = [
  { id: 'evidence', label: 'Évidence' },
  { id: 'methode', label: 'Méthode' },
  { id: 'actions', label: 'Actions' },
  { id: 'flex', label: 'Flex' },
];

// ---- Exported helpers (testable) ----

export function recalcLosses(kWh, customPrice, defaultPrice = 0.15) {
  return Math.round((kWh || 0) * (customPrice ?? defaultPrice));
}

export function computeSummaryFromInsights(insights) {
  if (!insights?.length)
    return {
      total_insights: 0,
      sites_with_insights: 0,
      total_loss_kwh: 0,
      total_loss_eur: 0,
      by_type: {},
    };
  return {
    total_insights: insights.length,
    sites_with_insights: new Set(insights.map((i) => i.site_id).filter(Boolean)).size,
    total_loss_kwh: insights.reduce((s, i) => s + (i.estimated_loss_kwh || 0), 0),
    total_loss_eur: insights.reduce((s, i) => s + (i.estimated_loss_eur || 0), 0),
    by_type: insights.reduce((acc, i) => ({ ...acc, [i.type]: (acc[i.type] || 0) + 1 }), {}),
  };
}

export function generateComparisonChart(insight) {
  const type = insight.type;
  const excessKwh = insight.estimated_loss_kwh || 100;
  const seed = insight.id || 1;
  const data = [];

  for (let h = 0; h < 24; h++) {
    const isOffice = h >= 8 && h <= 19;
    const baseline = isOffice ? 40 + Math.sin(((h - 8) / 11) * Math.PI) * 30 : 8;

    let actual = baseline;
    // Deterministic pseudo-random based on seed + hour
    const noise = (((seed * 31 + h * 17) % 100) / 100) * 3;

    if (type === 'hors_horaires' && !isOffice) {
      actual = baseline + (excessKwh / 14) * 0.8 + noise;
    } else if (type === 'base_load') {
      actual = baseline + (excessKwh / 24) * 0.3 + noise * 0.5;
    } else if (type === 'pointe' && h >= 10 && h <= 14) {
      actual = baseline + excessKwh / 4 + noise * 2;
    } else if (type === 'derive') {
      actual = baseline * (1 + excessKwh / 500) + noise;
    } else {
      actual = baseline + noise * 0.3;
    }

    data.push({
      hour: `${h}h`,
      baseline: Math.round(baseline * 10) / 10,
      actual: Math.round(actual * 10) / 10,
    });
  }
  return data;
}

// ---- Sub-components ----

function SeverityBadge({ severity }) {
  const s = SEVERITY_TINT[severity] || SEVERITY_TINT.info;
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.chipBg} ${s.chipText}`}>
      {s.label || severity}
    </span>
  );
}

function DiagHeader({ insights, summary, customPrice, onPriceChange }) {
  const co2Factor = useElecCo2Factor();
  const periods = insights.filter((i) => i.period_start && i.period_end);
  const from = periods.length
    ? periods.reduce((m, i) => (i.period_start < m ? i.period_start : m), periods[0].period_start)
    : null;
  const to = periods.length
    ? periods.reduce((m, i) => (i.period_end > m ? i.period_end : m), periods[0].period_end)
    : null;
  const nbJours = from && to ? Math.round((new Date(to) - new Date(from)) / 86400000) : null;

  const defaultPrice =
    insights.find((i) => i.metrics?.price_ref_eur_kwh)?.metrics.price_ref_eur_kwh || 0.15;
  const price = customPrice ?? defaultPrice;
  const totalKwh = summary?.total_loss_kwh || 0;
  const recalcEur = recalcLosses(totalKwh, customPrice, defaultPrice);

  return (
    <Card className="mb-4">
      <CardBody>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="text-sm text-gray-600">
            <span className="font-medium text-gray-800">Période : </span>
            {from ? fmtDateFR(from) : '—'} → {to ? fmtDateFR(to) : '—'}
            {nbJours != null && <span className="text-gray-400 ml-2">({nbJours} jours)</span>}
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-500">Prix :</label>
            <input
              type="number"
              step="0.01"
              min="0"
              className="w-20 border rounded px-2 py-1 text-sm text-right"
              defaultValue={price}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                onPriceChange(Number.isFinite(v) ? v : null);
              }}
            />
            <span className="text-sm text-gray-500">EUR/kWh</span>
            <Tooltip text="Pertes = kWh excédentaires × prix EUR/kWh" position="bottom">
              <Info size={14} className="text-gray-400 cursor-help" />
            </Tooltip>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="text-xs text-gray-400">Pertes estimées</p>
              <p className="text-lg font-bold text-red-600">{fmtEur(recalcEur)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Excès kWh</p>
              <p className="text-lg font-bold text-orange-600">{fmtKwh(Math.round(totalKwh))}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">CO₂e évitable</p>
              <p className="text-lg font-bold text-emerald-600">{fmtCo2(totalKwh * co2Factor)}</p>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function SummaryCards({ summary, customPrice }) {
  const co2Factor = useElecCo2Factor();
  if (!summary) return null;
  const defaultPrice = 0.15;
  const lossEur =
    customPrice != null
      ? recalcLosses(summary.total_loss_kwh, customPrice, defaultPrice)
      : Math.round(summary.total_loss_eur || 0);

  const totalCo2eKg = Math.round((summary.total_loss_kwh || 0) * co2Factor);
  const cards = [
    {
      label: 'Analyses détectées',
      value: summary.total_insights,
      color: 'text-blue-700',
      bg: 'bg-blue-50',
    },
    {
      label: 'Sites analysés',
      value: summary.sites_with_insights,
      color: 'text-indigo-700',
      bg: 'bg-indigo-50',
    },
    { label: 'Pertes estimées', value: fmtEur(lossEur), color: 'text-red-700', bg: 'bg-red-50' },
    {
      label: 'Pertes kWh',
      value: fmtKwh(Math.round(summary.total_loss_kwh || 0)),
      color: 'text-orange-700',
      bg: 'bg-orange-50',
    },
    {
      label: 'CO₂e évitable',
      value: fmtCo2(totalCo2eKg),
      color: 'text-emerald-700',
      bg: 'bg-emerald-50',
    },
  ];

  return (
    <div className="grid grid-cols-5 gap-4 mb-6">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardBody className={c.bg}>
            <p className="text-xs text-gray-500 mb-1">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function ByTypeBreakdown({ byType }) {
  if (!byType || Object.keys(byType).length === 0) return null;
  return (
    <Card className="mb-6">
      <CardBody>
        <h3 className="font-semibold text-gray-800 mb-3">Répartition par type</h3>
        <div className="grid grid-cols-5 gap-3">
          {Object.entries(byType).map(([type, count]) => (
            <div key={type} className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-lg font-bold text-gray-800">{count}</p>
              <p className="text-xs text-gray-500">{TYPE_LABELS[type] || type}</p>
            </div>
          ))}
        </div>
      </CardBody>
    </Card>
  );
}

function RecommendedAction({ action }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
      <Zap size={16} className="text-blue-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">{action.title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{action.rationale}</p>
        <div className="flex items-center gap-3 mt-2">
          {action.expected_gain_eur > 0 && (
            <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded">
              +{fmtEur(action.expected_gain_eur)}/an
            </span>
          )}
          {action.effort && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${EFFORT_COLOR[action.priority] || EFFORT_COLOR.medium}`}
            >
              Effort: {action.effort}
            </span>
          )}
          <Badge status={SEVERITY_BADGE[action.priority] || 'neutral'}>{action.priority}</Badge>
        </div>
      </div>
    </div>
  );
}

function InsightRow({ insight, onRowClick, onCreateAction }) {
  const co2Factor = useElecCo2Factor();
  const statusCfg = WORKFLOW_CONFIG[insight.insight_status] || WORKFLOW_CONFIG.open;
  return (
    <tr
      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
      onClick={() => onRowClick(insight)}
    >
      <td className="py-3 px-4 text-sm text-gray-800 font-medium">
        {insight.site_nom || `Site #${insight.site_id}`}
      </td>
      <td className="py-3 px-4 text-sm">
        <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">
          {TYPE_LABELS[insight.type] || insight.type}
        </span>
      </td>
      <td className="py-3 px-4 text-sm">
        <SeverityBadge severity={insight.severity} />
      </td>
      <td className="py-3 px-4 text-sm text-gray-600 max-w-md truncate">{insight.message}</td>
      <td className="py-3 px-4 text-sm text-right text-red-600 font-medium">
        {insight.estimated_loss_eur ? fmtEur(Math.round(insight.estimated_loss_eur)) : '—'}
      </td>
      <td className="py-3 px-4 text-sm text-right text-orange-600">
        {insight.estimated_loss_kwh ? fmtKwh(Math.round(insight.estimated_loss_kwh)) : '—'}
      </td>
      <td className="py-3 px-4 text-sm text-right text-emerald-600">
        {insight.estimated_loss_kwh ? fmtCo2(insight.estimated_loss_kwh * co2Factor) : '—'}
      </td>
      <td className="py-3 px-4 text-sm text-center">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusCfg.color}`}>
          {statusCfg.label}
        </span>
      </td>
      <td className="py-3 px-1 text-center">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCreateAction(insight);
          }}
          className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-400 hover:text-blue-600 transition"
          title="Créer une action"
        >
          <Zap size={14} />
        </button>
      </td>
    </tr>
  );
}

// ---- Drawer helpers ----

function DrawerSection({ title, children }) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-1.5">
      <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider">{title}</h4>
      {children}
    </div>
  );
}

function DrawerRow({ label, children }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-900 font-medium">{children}</span>
    </div>
  );
}

// ---- Flex Tab ----

const LEVER_ICONS = { hvac: '🌡️', irve: '🔌', froid: '❄️' };
const LEVER_COLORS = {
  hvac: 'border-orange-200 bg-orange-50',
  irve: 'border-blue-200 bg-blue-50',
  froid: 'border-cyan-200 bg-cyan-50',
};

function FlexScoreRing({ score }) {
  const r = 28;
  const c = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, score));
  const color = pct >= 60 ? '#22c55e' : pct >= 30 ? '#f59e0b' : '#94a3b8';
  return (
    <svg width="72" height="72" className="shrink-0">
      <circle cx="36" cy="36" r={r} fill="none" stroke="#f1f5f9" strokeWidth="6" />
      <circle
        cx="36"
        cy="36"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct / 100)}
        strokeLinecap="round"
        transform="rotate(-90 36 36)"
      />
      <text x="36" y="40" textAnchor="middle" className="text-base font-bold" fill={color}>
        {pct}
      </text>
    </svg>
  );
}

function FlexTab({ siteId }) {
  const [flex, setFlex] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    getFlexMini(siteId)
      .then(setFlex)
      .catch(() => setFlex(null))
      .finally(() => setLoading(false));
  }, [siteId]);

  if (loading)
    return <p className="text-sm text-gray-400 text-center py-6">Calcul du potentiel flex...</p>;
  if (!flex || flex.error)
    return <p className="text-sm text-gray-400 text-center py-6">Potentiel flex non disponible.</p>;

  return (
    <div className="space-y-4">
      {/* Score header */}
      <div className="flex items-center gap-4">
        <FlexScoreRing score={flex.flex_potential_score} />
        <div>
          <p className="text-sm font-semibold text-gray-800">Potentiel flexibilité</p>
          <p className="text-xs text-gray-500">
            Score {flex.flex_potential_score}/100
            {flex.inputs_used?.insights_count > 0 &&
              ` · ${flex.inputs_used.insights_count} insight(s) analysés`}
            {flex.inputs_used?.archetype && ` · ${flex.inputs_used.archetype}`}
          </p>
        </div>
      </div>

      {/* Levers */}
      {flex.levers.map((lever) => (
        <div
          key={lever.id}
          className={`p-3 rounded-lg border ${LEVER_COLORS[lever.id] || 'border-gray-200 bg-gray-50'}`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{LEVER_ICONS[lever.id] || '⚡'}</span>
            <span className="text-sm font-semibold text-gray-800">{lever.label}</span>
            <span
              className={`ml-auto text-xs font-bold ${
                lever.score >= 50
                  ? 'text-green-700'
                  : lever.score >= 20
                    ? 'text-amber-700'
                    : 'text-gray-400'
              }`}
            >
              {lever.score}/100
            </span>
          </div>
          <p className="text-xs text-gray-600">{lever.justification}</p>
          {(lever.estimate_kw || lever.estimate_kwh_year) && (
            <div className="flex gap-3 mt-1.5">
              {lever.estimate_kw && (
                <span className="text-[10px] text-gray-500 bg-white/60 px-1.5 py-0.5 rounded">
                  ~{lever.estimate_kw} kW effaçable
                </span>
              )}
              {lever.estimate_kwh_year && (
                <span className="text-[10px] text-gray-500 bg-white/60 px-1.5 py-0.5 rounded">
                  ~{fmtKwh(lever.estimate_kwh_year)}/an
                </span>
              )}
            </div>
          )}
        </div>
      ))}

      {flex.levers.every((l) => l.score === 0) && (
        <p className="text-xs text-gray-400 text-center">
          Aucun levier flex identifié pour ce site.
        </p>
      )}
    </div>
  );
}

// ---- Evidence Drawer ----

function EvidenceDrawer({
  insight,
  open,
  onClose,
  onStatusChange,
  onCreateAction,
  onOpenExplorer,
  onViewInvoice,
}) {
  const [tab, setTab] = useState('evidence');
  const co2Factor = useElecCo2Factor();
  if (!insight) return null;

  const metrics = insight.metrics || {};
  const actions = insight.recommended_actions || [];
  const statusCfg = WORKFLOW_CONFIG[insight.insight_status] || WORKFLOW_CONFIG.open;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={`${insight.site_nom} — ${TYPE_LABELS[insight.type] || insight.type}`}
      wide
    >
      <div className="space-y-4">
        {/* Consolidated summary banner */}
        <div className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <SeverityBadge severity={insight.severity} />
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusCfg.color}`}>
              {statusCfg.label}
            </span>
          </div>
          {(insight.estimated_loss_kwh > 0 || insight.estimated_loss_eur > 0) && (
            <span className="text-xs text-gray-600">
              {insight.estimated_loss_kwh > 0 && fmtKwh(insight.estimated_loss_kwh)}
              {insight.estimated_loss_kwh > 0 && insight.estimated_loss_eur > 0 && ' · '}
              {insight.estimated_loss_eur > 0 && fmtEur(Math.round(insight.estimated_loss_eur))}
              {' · '}
              {fmtCo2(insight.estimated_loss_kwh * co2Factor)}
            </span>
          )}
        </div>

        {/* Message */}
        <p className="text-sm text-gray-700">{insight.message}</p>

        {/* Tabs */}
        <Tabs tabs={DRAWER_TABS} active={tab} onChange={setTab} />

        {/* Tab: Evidence — Mini graph */}
        {tab === 'evidence' && <EvidenceTab insight={insight} />}

        {/* Tab: Methode */}
        {tab === 'methode' && (
          <div className="space-y-3">
            <DrawerSection title="Méthode de détection">
              <DrawerRow label="Fenêtre">
                {metrics.window || metrics.schedule_open || '30 jours glissants'}
              </DrawerRow>
              <DrawerRow label="Formule">
                {metrics.formula ||
                  `Écart vs ${insight.type === 'base_load' ? 'talon médian' : 'profil horaire'}`}
              </DrawerRow>
              <DrawerRow label="Seuil">{metrics.threshold || '> 2 écarts-type'}</DrawerRow>
              <DrawerRow label="Confiance">{metrics.confidence || 'Moyenne'}</DrawerRow>
            </DrawerSection>
            <DrawerSection title="Hypothèses">
              <DrawerRow label="Prix ref">
                {metrics.price_ref_eur_kwh
                  ? `${metrics.price_ref_eur_kwh} EUR/kWh`
                  : '0.15 EUR/kWh (défaut)'}
              </DrawerRow>
              <DrawerRow label="Pas de temps">{metrics.granularity || '30 min'}</DrawerRow>
              <DrawerRow label="Couverture data">
                {metrics.coverage ? `${metrics.coverage}%` : '—'}
              </DrawerRow>
              {metrics.schedule_source && (
                <DrawerRow label="Source horaires">{metrics.schedule_source}</DrawerRow>
              )}
            </DrawerSection>
          </div>
        )}

        {/* Tab: Actions recommandees */}
        {tab === 'actions' && (
          <div className="space-y-2">
            {actions.length > 0 ? (
              actions.map((a, i) => <RecommendedAction key={i} action={a} />)
            ) : (
              <p className="text-sm text-gray-400 text-center py-6">Aucune action recommandée.</p>
            )}
          </div>
        )}

        {/* Tab: Flex potential */}
        {tab === 'flex' && <FlexTab siteId={insight.site_id} />}

        {/* CTAs — always visible */}
        <div className="pt-3 border-t border-gray-100 space-y-2">
          <button
            onClick={() => onOpenExplorer(insight)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
          >
            <BarChart3 size={15} className="text-blue-600" />
            Ouvrir dans Explorer
            <ExternalLink size={12} className="ml-auto text-gray-300" />
          </button>
          <button
            onClick={() => onViewInvoice(insight)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-50 transition"
          >
            <ExternalLink size={15} className="text-emerald-600" />
            Voir facture
            <ExternalLink size={12} className="ml-auto text-gray-300" />
          </button>
          <button
            onClick={() => onCreateAction(insight)}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-semibold hover:bg-blue-700 transition"
          >
            <Zap size={15} />
            Créer une action
          </button>

          {/* Workflow buttons */}
          <div className="flex items-center gap-2">
            {insight.insight_status === 'open' && (
              <button
                onClick={() => onStatusChange(insight.id, 'ack')}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-blue-200 text-sm font-medium text-blue-700 hover:bg-blue-50 transition"
              >
                <UserCheck size={14} /> Prendre en charge
              </button>
            )}
            {(insight.insight_status === 'open' || insight.insight_status === 'ack') && (
              <button
                onClick={() => onStatusChange(insight.id, 'resolved')}
                className="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-green-200 text-sm font-medium text-green-700 hover:bg-green-50 transition"
              >
                <CheckCircle2 size={14} /> Résolu
              </button>
            )}
            {(insight.insight_status === 'open' || insight.insight_status === 'ack') && (
              <button
                onClick={() => onStatusChange(insight.id, 'false_positive')}
                className="flex items-center justify-center gap-1 px-3 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-500 hover:bg-gray-50 transition"
              >
                <XCircle size={14} /> FP
              </button>
            )}
          </div>
        </div>

        {/* Metadata */}
        <div className="text-[10px] text-gray-400 pt-1">
          Insight #{insight.id}
          {insight.period_start && ` · ${fmtDateFR(insight.period_start)}`}
          {insight.period_end && ` → ${fmtDateFR(insight.period_end)}`}
        </div>
      </div>
    </Drawer>
  );
}

function EvidenceTab({ insight }) {
  const co2Factor = useElecCo2Factor();
  const chartData = useMemo(() => generateComparisonChart(insight), [insight]);
  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-3">
        <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">
          Profil type : consommation observée vs référence
        </h4>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} unit=" kW" />
            <RTooltip />
            <Area
              type="monotone"
              dataKey="baseline"
              stroke="#94a3b8"
              fill="#e2e8f0"
              name="Référence"
            />
            <Area
              type="monotone"
              dataKey="actual"
              stroke="#ef4444"
              fill="#fee2e2"
              fillOpacity={0.5}
              name="Observée"
            />
          </AreaChart>
        </ResponsiveContainer>
        {insight.estimated_loss_kwh > 0 && (
          <p className="text-xs text-gray-500 mt-1">
            Écart : +{fmtKwh(insight.estimated_loss_kwh)}
            {insight.estimated_loss_eur > 0 &&
              ` (${fmtEur(Math.round(insight.estimated_loss_eur))})`}
            {' · '}
            {fmtCo2(insight.estimated_loss_kwh * co2Factor)}
          </p>
        )}
      </div>
      <p className="text-[10px] text-gray-400 italic">
        Graphe illustratif basé sur le type d'insight et les métriques disponibles.
      </p>
    </div>
  );
}

// ---- Main Page ----

export default function ConsumptionDiagPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { org, selectedSiteId, scopeLabel, sitesCount, scopedSites } = useScope();
  const co2Factor = useElecCo2Factor();

  // Sprint 1.8 — briefing éditorial Sol §5 vue Diagnostic (ADR-001).
  // Pillar §4.2 doctrine (suite Monitoring) : EMS / Performance — détection
  // automatique anomalies + chiffrage € leviers + plan d'actions priorisées.
  // Sert Marie DAF (économies cachées) + Energy Manager (priorisation).
  const {
    briefing: solBriefing,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('diagnostic', { persona: 'daily' });

  // Sprint 1.8bis P0-1 (audit Nav P0-1 — récurrence S1.6/S1.7) : honorer
  // deep-link `?status=open|resolved` + `?insight={id}` venant des week-cards
  // backend. Sans ça, clic week-card → page sans filtre/drawer = trahison UX.
  const [searchParams] = useSearchParams();
  const queryStatus = searchParams.get('status');
  const queryInsightId = searchParams.get('insight');
  // Step 11: unified period from URL (default 90 days for diagnostic)
  const { period, periodQueryString: _periodQueryString } = usePeriodParams(90);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [message, setMessage] = useState(null);
  const [filterType, setFilterType] = useState('');
  const [diagPage, setDiagPage] = useState(0);

  // Evidence Drawer
  const [drawerInsight, setDrawerInsight] = useState(null);

  // Create Action — via unified drawer
  const { openActionDrawer } = useActionDrawer();

  // Editable price
  const [customPrice, setCustomPrice] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getConsumptionInsights(org?.id ?? null);
      setSummary(data);
    } catch {
      toast('Erreur lors du chargement du diagnostic', 'error');
    } finally {
      setLoading(false);
    }
  }, [org?.id, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setMessage(null);
    try {
      const r = await seedDemoConsumption();
      setMessage(`Démo conso générée : ${r.total || r.sites?.length || 0} site(s)`);
      await load();
    } catch (e) {
      setMessage('Erreur: ' + (e.response?.data?.detail || e.message));
    } finally {
      setSeeding(false);
    }
  };

  const handleDiagnose = async () => {
    setDiagnosing(true);
    setMessage(null);
    try {
      const r = await runConsumptionDiagnose();
      setMessage(
        `Diagnostic terminé : ${r.total_insights || 0} insight(s) sur ${r.sites_analyzed || 0} site(s)`
      );
      track('diagnostic_run', { insights: r.total_insights });
      await load();
    } catch (e) {
      setMessage('Erreur: ' + (e.response?.data?.detail || e.message));
    } finally {
      setDiagnosing(false);
    }
  };

  // Drawer
  const openDrawer = useCallback((insight) => {
    setDrawerInsight(insight);
    track('insight_drawer_open', { type: insight.type, id: insight.id });
  }, []);

  // Workflow
  const handleStatusChange = async (insightId, newStatus) => {
    try {
      await patchConsumptionInsight(insightId, { insight_status: newStatus });
      track('insight_workflow', { id: insightId, status: newStatus });
      setSummary((prev) => ({
        ...prev,
        insights: prev.insights.map((i) =>
          i.id === insightId ? { ...i, insight_status: newStatus } : i
        ),
      }));
      setDrawerInsight((prev) =>
        prev?.id === insightId ? { ...prev, insight_status: newStatus } : prev
      );
      toast(`Insight mis à jour : ${WORKFLOW_CONFIG[newStatus]?.label || newStatus}`, 'success');
    } catch {
      toast('Erreur lors de la mise à jour du statut', 'error');
    }
  };

  // Create action
  const handleCreateAction = useCallback(
    (insight) => {
      openActionDrawer(
        {
          prefill: {
            titre: `${TYPE_LABELS[insight.type] || insight.type} — ${insight.site_nom}`,
            type: 'conso',
            site: insight.site_nom,
            impact_eur: Math.round(insight.estimated_loss_eur || 0),
            priorite:
              insight.severity === 'critical'
                ? 'critical'
                : insight.severity === 'high'
                  ? 'high'
                  : 'medium',
            description:
              insight.message +
              (insight.recommended_actions?.length
                ? '\n\nActions recommandées :\n' +
                  insight.recommended_actions.map((a) => `- ${a.title}`).join('\n')
                : ''),
          },
          siteId: insight.site_id || null,
          sourceType: 'consumption',
          sourceId: `insight-${insight.id}`,
          idempotencyKey: `diag-insight-${insight.id}`,
        },
        {
          onSave: (action) => {
            track('action_create_from_diagnostic', { titre: action?.titre });
          },
        }
      );
      track('insight_create_action', { type: insight.type, id: insight.id });
    },
    [openActionDrawer]
  );

  // Open in Explorer — Step 11: use period_start/period_end for unified period
  const handleOpenExplorer = useCallback(
    (insight) => {
      navigate(
        toConsoExplorer({
          site_id: insight.site_id,
          period_start: insight.period_start ? insight.period_start.slice(0, 10) : undefined,
          period_end: insight.period_end ? insight.period_end.slice(0, 10) : undefined,
        })
      );
    },
    [navigate]
  );

  // View invoice (deep-link)
  const handleViewInvoice = useCallback(
    (insight) => {
      const month = insight.period_start ? insight.period_start.slice(0, 7) : null;
      navigate(deepLinkWithContext(insight.site_id, month));
      track('insight_view_invoice', {
        type: insight.type,
        id: insight.id,
        site_id: insight.site_id,
      });
    },
    [navigate]
  );

  const insights = useMemo(() => summary?.insights || [], [summary]);

  // V15-B: scope-aware filtering
  // Sprint 1.8bis P0-1 : ajout filtre `?status=open|resolved` (deep-link week-cards).
  const filteredInsights = useMemo(() => {
    if (!insights.length) return [];
    // V16-D: normalizeId prevents type mismatch (API number vs store number/string)
    let scoped = selectedSiteId
      ? insights.filter((i) => normalizeId(i.site_id) === normalizeId(selectedSiteId))
      : insights;
    if (queryStatus) {
      scoped = scoped.filter((i) => (i.insight_status || 'open') === queryStatus);
    }
    return scoped;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insights, selectedSiteId, queryStatus]);

  // Sprint 1.8bis P0-1 : ouvrir drawer sur `?insight={id}` post-load.
  useEffect(() => {
    if (!queryInsightId || insights.length === 0) return;
    const target = insights.find((i) => String(i.id) === String(queryInsightId));
    if (target && drawerInsight?.id !== target.id) {
      setDrawerInsight(target);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryInsightId, insights]);

  const displayedSummary = useMemo(
    () => computeSummaryFromInsights(filteredInsights),
    [filteredInsights]
  );

  const isSiteScoped = Boolean(selectedSiteId);
  const hasMismatch = isSiteScoped && new Set(insights.map((i) => i.site_id)).size > 1;

  const filtered = filterType
    ? filteredInsights.filter((i) => i.type === filterType)
    : filteredInsights;

  // Sprint 1.8 P0-C : subtitle node Sol — éviter duplication PageShell ↔
  // SolPageHeader (pattern S1.6bis P0-4).
  const diagnosticSubtitleNode = (
    <>
      Identifier vos économies d'énergie cachées : horaires inhabituels, talon excessif, pics de
      puissance, dérives.{' '}
      <span className="text-xs text-[var(--sol-ink-400)] ml-2">
        Période : {period.start} — {period.end} ({period.days}j)
      </span>
    </>
  );

  return (
    <PageShell
      icon={Zap}
      title="Diagnostic"
      editorialHeader={
        <SolPageHeader
          kicker={solBriefing?.kicker || scopeKicker('DIAGNOSTIC', org?.nom, scopedSites?.length)}
          title={solBriefing?.title || "Vos économies d'énergie identifiées"}
          italicHook={solBriefing?.italicHook || "leviers chiffrés · plan d'actions priorisé"}
          subtitle={diagnosticSubtitleNode}
        />
      }
      actions={
        <>
          <Link
            to={toConsoExplorer()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            <BarChart3 size={14} />
            Explorer
          </Link>
          <Link
            to={toMonitoring()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            <Activity size={14} />
            Performance
          </Link>
          <Link
            to={toUsages()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition"
          >
            <BarChart3 size={14} />
            Usages
          </Link>
          <Button variant="secondary" size="sm" onClick={handleSeedDemo} disabled={seeding}>
            {seeding ? 'Génération...' : 'Générer conso démo'}
          </Button>
          <Button size="sm" onClick={handleDiagnose} disabled={diagnosing}>
            <Zap size={14} />
            {diagnosing ? 'Analyse...' : 'Lancer diagnostic'}
          </Button>
        </>
      }
    >
      {/* Sprint 1.8 — préambule éditorial Sol §5 vue Diagnostic (ADR-001).
          Pillar §4.2 : EMS / Performance — détection anomalies + chiffrage
          € leviers + plan d'actions priorisé. Sert Marie DAF (économies
          cachées) + Energy Manager (priorisation) + Investisseur. */}
      {/* Sprint 2 Vague B ét8'-bis — factorisation grammaire §5 via SolBriefingHead. */}
      <SolBriefingHead
        briefing={solBriefing}
        error={solBriefingError}
        onRetry={solBriefingRefetch}
        omitHeader
        onNavigate={navigate}
      />

      {/* V15-B: Scope badge */}
      {/* Sprint 1.8bis P0-10 (audit Espaces P0) : retrait `mb-2` legacy
          qui s'additionnait au `space-y-8` PageShell parent (asymétrie
          32→40px). Pattern leçon S1.7bis. */}
      <div className="flex items-center gap-2 text-xs text-[var(--sol-ink-500)]">
        <span>Périmètre :</span>
        <span className="font-medium text-[var(--sol-ink-700)]">{scopeLabel}</span>
        {isSiteScoped && (
          <span className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">
            Vue filtrée
          </span>
        )}
      </div>

      {/* V15-B: Scope mismatch banner */}
      {hasMismatch && (
        <div
          className="flex items-start gap-2 px-3 py-2 rounded-lg text-xs"
          style={{
            background: 'var(--sol-attention-bg)',
            borderColor: 'var(--sol-attention-line)',
            border: '1px solid var(--sol-attention-line)',
            color: 'var(--sol-attention-fg)',
          }}
        >
          <Info size={14} className="shrink-0 mt-0.5" />
          <span className="flex-1">
            Diagnostic lancé sur{' '}
            <strong>
              {sitesCount} site{sitesCount !== 1 ? 's' : ''}
            </strong>
            . Vue filtrée sur <strong>{scopeLabel}</strong> ({filteredInsights.length} insight
            {filteredInsights.length !== 1 ? 's' : ''}).
          </span>
        </div>
      )}

      {message && (
        <div
          className="p-3 rounded-lg text-sm"
          style={{
            background: 'var(--sol-calme-bg)',
            color: 'var(--sol-calme-fg-hover)',
          }}
        >
          {message}
        </div>
      )}

      {loading ? (
        // Sprint 1.8bis P0-3 (audit CX P0-1 + UX P0-3) : skeleton aligné
        // grammaire Sol §5 (3 KPIs + 3 week-cards) — évite flash legacy
        // 5-cards. Pattern hérité de S1.7bis (MonitoringPage skeleton Sol).
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={`wc-${i}`} />
            ))}
          </div>
        </>
      ) : !summary || filteredInsights.length === 0 ? (
        // Sprint 1.8bis P0-4 (audit UX P0-2 + CX P0-2 + Densité P1) :
        // EmptyState compact + préambule Sol garanti (déjà rendu plus haut
        // via SolNarrative). Pas de plein écran §6.1 — instructions inline
        // sobres, vocabulaire CFO (« données démo » → « jeu de données
        // d'essai »).
        <EmptyState
          icon={Zap}
          title="Aucun gisement détecté"
          text="Lancez le diagnostic sur votre patrimoine pour identifier les leviers d'économies."
          actions={
            <div className="flex gap-3 justify-center">
              <Button variant="secondary" onClick={handleSeedDemo} disabled={seeding}>
                Charger un jeu d'essai
              </Button>
              <Button onClick={handleDiagnose} disabled={diagnosing}>
                Lancer le diagnostic
              </Button>
            </div>
          }
        />
      ) : (
        <>
          {/* Sprint 1.8bis P0-2 (audit UX P0-1 + Visual P0 + Densité P0) :
              card « À retenir » supprimée — dupliquait sémantiquement les
              3 KPIs hero SolNarrative (Leviers / Gisement / Économies)
              + cassait la hiérarchie 36px Stripe-grade avec text-lg
              (~18px) coloré bg-blue-700/red-600/emerald-600. SolNarrative
              KPIs servent désormais de SoT unique above-the-fold. */}

          <DiagHeader
            insights={filteredInsights}
            summary={displayedSummary}
            customPrice={customPrice}
            onPriceChange={setCustomPrice}
          />

          {/* Full KPI breakdown — collapsible */}
          <details className="group mb-4">
            <summary className="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900 flex items-center gap-1 py-2 select-none">
              <span className="transition-transform group-open:rotate-90">▸</span> Détails par
              indicateur
            </summary>
            <SummaryCards summary={displayedSummary} customPrice={customPrice} />
            <ByTypeBreakdown byType={displayedSummary.by_type} />
          </details>

          {/* Filters */}
          <div className="flex items-center gap-3">
            <label className="text-sm text-gray-500">Type:</label>
            <select
              value={filterType}
              onChange={(e) => {
                setFilterType(e.target.value);
                setDiagPage(0);
              }}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tous</option>
              {Object.entries(TYPE_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
            <span className="text-xs text-gray-400 ml-2">{filtered.length} insight(s)</span>
          </div>

          {/* Table with pagination */}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Site
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Type
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Sévérité
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Message
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Perte (EUR)
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Perte (kWh)
                    </th>
                    <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      CO₂e (kg)
                    </th>
                    <th className="text-center py-3 px-4 text-xs font-medium text-gray-500 uppercase">
                      Statut
                    </th>
                    <th className="text-center py-3 px-1 text-xs font-medium text-gray-500 uppercase w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(diagPage * 20, (diagPage + 1) * 20).map((ins, i) => (
                    <InsightRow
                      key={ins.id || i}
                      insight={ins}
                      onRowClick={openDrawer}
                      onCreateAction={handleCreateAction}
                    />
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination controls */}
            {filtered.length > 20 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                <span className="text-xs text-gray-500">
                  {diagPage * 20 + 1}–{Math.min((diagPage + 1) * 20, filtered.length)} sur{' '}
                  {filtered.length}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setDiagPage((p) => Math.max(0, p - 1))}
                    disabled={diagPage === 0}
                    className="px-3 py-1.5 text-xs rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
                  >
                    Précédent
                  </button>
                  <span className="text-xs text-gray-600">
                    Page {diagPage + 1} / {Math.ceil(filtered.length / 20)}
                  </span>
                  <button
                    onClick={() =>
                      setDiagPage((p) => Math.min(Math.ceil(filtered.length / 20) - 1, p + 1))
                    }
                    disabled={diagPage >= Math.ceil(filtered.length / 20) - 1}
                    className="px-3 py-1.5 text-xs rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
                  >
                    Suivant
                  </button>
                </div>
              </div>
            )}
          </Card>
        </>
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer
        insight={drawerInsight}
        open={!!drawerInsight}
        onClose={() => setDrawerInsight(null)}
        onStatusChange={handleStatusChange}
        onCreateAction={handleCreateAction}
        onOpenExplorer={handleOpenExplorer}
        onViewInvoice={handleViewInvoice}
      />

      {/* Cross-module exit: facturation */}
      <div className="flex items-center gap-4 pt-4 mt-4 border-t border-gray-100">
        <Link
          to={toBillIntel()}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 hover:text-amber-700 hover:underline transition"
        >
          Voir la facturation & anomalies
        </Link>
      </div>

      {/* Action creation handled by ActionDrawerContext */}

      {/* Sprint 2 Vague B ét8'-bis — SolPageFooter §5 factorisé via HOC. */}
      <SolBriefingFooter briefing={solBriefing} />
    </PageShell>
  );
}
