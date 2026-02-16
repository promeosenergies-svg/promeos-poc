/**
 * PROMEOS - Command Center (/) Phase 6 — Dashboard World-Class
 * Neutral-first + controlled accents. KPI accent bars, icon pills,
 * premium priority card, "tout sous controle" state, trust signals.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ArrowRight, Clock, Upload, Scan, RefreshCw,
  FileText, CheckCircle2, AlertTriangle, ShieldCheck, TrendingDown, Bell,
  Database,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, SkeletonCard, PageShell, MetricCard, StatusDot, EmptyState, ErrorState } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import { SEVERITY_TINT, HERO_ACCENTS } from '../ui/colorTokens';
import {
  getComplianceBundle, getActionsSummary, getActionsList,
  getNotificationsSummary,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };

/* ── normalizeDashboardModel: prevent contradictions ── */
export function normalizeDashboardModel({ kpis, topActions, alertsCount }) {
  const norm = { ...kpis };
  // If 100% conforme, risk must be 0
  if (norm.pctConf === 100) {
    norm.risque = 0;
    norm.nonConformes = 0;
    norm.aRisque = 0;
  }
  // If 0 risk sites, risque EUR must be 0
  if (norm.nonConformes + norm.aRisque === 0) {
    norm.risque = 0;
  }
  const isAllClear = norm.pctConf === 100 && norm.risque === 0 && alertsCount === 0;
  const actions = isAllClear ? [] : topActions;
  return { kpis: norm, topActions: actions, alertsCount, isAllClear };
}

function ActionRow({ action, index, onClick }) {
  const sev = SEVERITY_TINT[action.priorite] || SEVERITY_TINT.neutral;
  return (
    <button
      type="button"
      className="flex items-center gap-3 w-full px-4 py-3 text-left rounded-lg
        hover:bg-gray-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      onClick={onClick}
    >
      <span className="w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-bold shrink-0">
        {index + 1}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{action.titre}</p>
        <p className="text-xs text-gray-500 mt-0.5">{action.source_label}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {action.impact_eur > 0 && (
          <span className="text-xs font-medium text-gray-600">
            {action.impact_eur.toLocaleString('fr-FR')} EUR
          </span>
        )}
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${sev.chipBg} ${sev.chipText} ${sev.chipBorder}`}>
          {sev.label}
        </span>
        <ArrowRight size={14} className="text-gray-300" />
      </div>
    </button>
  );
}

export default function CommandCenter() {
  const navigate = useNavigate();
  const { org, scopedSites } = useScope();
  const { isExpert } = useExpertMode();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [compliance, setCompliance] = useState(null);
  const [actionsSummary, setActionsSummary] = useState(null);
  const [actions, setActions] = useState([]);
  const [alertsSummary, setAlertsSummary] = useState(null);
  const [lastSync, setLastSync] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [compBundle, actSummary, actList, notifSummary] = await Promise.all([
        getComplianceBundle({ org_id: org.id }).catch(() => null),
        getActionsSummary(org.id).catch(() => null),
        getActionsList({ limit: 20, status: 'backlog,planned,in_progress' }).catch(() => []),
        getNotificationsSummary(org.id).catch(() => null),
      ]);
      setCompliance(compBundle);
      setActionsSummary(actSummary);
      setActions(Array.isArray(actList) ? actList : actList?.actions || []);
      setAlertsSummary(notifSummary);
      setLastSync(new Date());
    } catch {
      setError('Impossible de charger le tableau de bord');
    } finally {
      setLoading(false);
    }
  }, [org.id]);

  useEffect(() => { loadData(); }, [loadData]);

  // Raw KPIs from scope
  const rawKpis = useMemo(() => {
    const total = scopedSites.length;
    const conformes = scopedSites.filter(s => s.statut_conformite === 'conforme').length;
    const nonConformes = scopedSites.filter(s => s.statut_conformite === 'non_conforme').length;
    const aRisque = scopedSites.filter(s => s.statut_conformite === 'a_risque').length;
    const risque = scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
    const pctConf = total > 0 ? Math.round(conformes / total * 100) : 0;
    const compStatus = nonConformes > 0 ? 'crit' : aRisque > 0 ? 'warn' : total > 0 ? 'ok' : 'neutral';
    const risqueStatus = risque > 50000 ? 'crit' : risque > 10000 ? 'warn' : 'ok';
    return { total, conformes, nonConformes, aRisque, risque, pctConf, compStatus, risqueStatus };
  }, [scopedSites]);

  // Top actions — merge compliance + action plan
  const rawTopActions = useMemo(() => {
    const items = [];
    if (compliance?.sites) {
      const findings = compliance.sites
        .flatMap(s => (s.findings || []).filter(f => f.status !== 'conforme').map(f => ({
          ...f, site_nom: s.site_nom,
        })))
        .slice(0, 5);
      for (const f of findings) {
        items.push({
          id: `comp-${f.id || f.rule_id}`,
          titre: f.description || f.rule_code || 'Non-conformite',
          source_label: `Conformite — ${f.site_nom}`,
          impact_eur: f.impact_eur || 0,
          priorite: f.severity || 'medium',
          route: '/conformite',
        });
      }
    }
    for (const a of actions.slice(0, 5)) {
      items.push({
        id: `act-${a.id}`,
        titre: a.titre || a.title || 'Action',
        source_label: `Plan d'action — ${a.site_nom || ''}`,
        impact_eur: a.impact_eur || 0,
        priorite: a.priorite || a.priority || 'medium',
        route: '/actions',
      });
    }
    return items
      .sort((a, b) => (PRIORITY_RANK[b.priorite] || 0) - (PRIORITY_RANK[a.priorite] || 0) || b.impact_eur - a.impact_eur)
      .slice(0, 5);
  }, [compliance, actions]);

  const rawAlertsCount = useMemo(() => {
    if (!alertsSummary) return 0;
    return (alertsSummary.by_severity?.critical || 0) + (alertsSummary.by_severity?.warn || 0);
  }, [alertsSummary]);

  // Normalized model (no contradictions)
  const { kpis, topActions, alertsCount, isAllClear } = useMemo(
    () => normalizeDashboardModel({ kpis: rawKpis, topActions: rawTopActions, alertsCount: rawAlertsCount }),
    [rawKpis, rawTopActions, rawAlertsCount],
  );

  // Data coverage
  const coveragePct = useMemo(() => {
    return kpis.total > 0 ? Math.round(scopedSites.filter(s => s.conso_kwh_an > 0).length / kpis.total * 100) : 0;
  }, [scopedSites, kpis.total]);

  const hasSites = scopedSites.length > 0;

  if (loading) {
    return (
      <PageShell icon={LayoutDashboard} title="Tableau de bord" subtitle="Chargement...">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      </PageShell>
    );
  }

  if (error) {
    return (
      <PageShell icon={LayoutDashboard} title="Tableau de bord" subtitle={`${org.nom} · ${kpis.total} sites`}>
        <ErrorState title="Erreur de chargement" message={error} onRetry={loadData} />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={LayoutDashboard}
      title="Tableau de bord"
      subtitle={`${org.nom} · ${kpis.total} sites`}
      actions={
        <div className="flex items-center gap-2">
          {/* Trust signals — compact */}
          <div className="hidden sm:flex items-center gap-3 mr-2 text-[11px] text-gray-400">
            {lastSync && (
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {lastSync.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
            <span className="flex items-center gap-1" title="Couverture donnees">
              <Database size={11} />
              {coveragePct}%
            </span>
          </div>
          <Button variant="secondary" size="sm" onClick={() => navigate('/cockpit-2min')}>
            <FileText size={14} /> Briefing
          </Button>
          {isExpert && (
            <Button variant="secondary" size="sm" onClick={loadData}>
              <RefreshCw size={14} /> Actualiser
            </Button>
          )}
          {!hasSites ? (
            <Button onClick={() => navigate('/import')}>
              <Upload size={16} /> Importer
            </Button>
          ) : (
            <Button onClick={() => navigate('/conformite')}>
              <Scan size={16} /> Scanner
            </Button>
          )}
        </div>
      }
    >
      {/* ── KPI Row: 3 MetricCards with accent bars + icon pills ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          accent="conformite"
          icon={ShieldCheck}
          label="Conformite"
          value={`${kpis.pctConf}%`}
          sub={`${kpis.conformes} / ${kpis.total} sites conformes`}
          status={kpis.compStatus}
          onClick={() => navigate('/conformite')}
        />
        <MetricCard
          accent="risque"
          icon={TrendingDown}
          label="Risque financier"
          value={kpis.risque > 0 ? `${(kpis.risque / 1000).toFixed(0)}k EUR` : '0 EUR'}
          sub={`${kpis.nonConformes + kpis.aRisque} sites a risque`}
          status={kpis.risqueStatus}
          onClick={() => navigate('/actions')}
        />
        <MetricCard
          accent="alertes"
          icon={Bell}
          label="Alertes actives"
          value={alertsCount}
          sub={alertsSummary ? `dont ${alertsSummary.by_severity?.critical || 0} critiques` : 'Chargement...'}
          status={alertsCount > 5 ? 'crit' : alertsCount > 0 ? 'warn' : 'ok'}
          onClick={() => navigate('/notifications')}
        />
      </div>

      {/* ── Top Priority #1 — premium card OR "Tout sous controle" ── */}
      {isAllClear ? (
        <div className={`rounded-lg border p-5 ${HERO_ACCENTS.success.bg} ${HERO_ACCENTS.success.border} ${HERO_ACCENTS.success.ring}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 size={20} className="text-emerald-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900">Tout est sous controle</p>
                <p className="text-xs text-gray-500 mt-0.5">Conformite 100%, aucun risque, aucune alerte active.</p>
              </div>
            </div>
            <Button variant="secondary" size="sm" onClick={() => navigate('/conformite')}>
              Voir opportunites <ArrowRight size={14} />
            </Button>
          </div>
        </div>
      ) : topActions.length > 0 && (
        <div className={`rounded-lg border p-5 ${HERO_ACCENTS.priority.bg} ${HERO_ACCENTS.priority.border} ${HERO_ACCENTS.priority.ring}`}>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center shrink-0">
                <AlertTriangle size={20} className="text-amber-600" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider mb-0.5">Action prioritaire</p>
                <p className="text-sm font-semibold text-gray-900 truncate">{topActions[0].titre}</p>
                <p className="text-xs text-gray-500 mt-0.5">{topActions[0].source_label}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              {topActions[0].impact_eur > 0 && (
                <span className="text-sm font-semibold text-gray-700">
                  {topActions[0].impact_eur.toLocaleString('fr-FR')} EUR
                </span>
              )}
              {(() => {
                const sev = SEVERITY_TINT[topActions[0].priorite] || SEVERITY_TINT.neutral;
                return (
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border ${sev.chipBg} ${sev.chipText} ${sev.chipBorder}`}>
                    {sev.label}
                  </span>
                );
              })()}
              <Button size="sm" onClick={() => navigate(topActions[0].route)}>
                Traiter <ArrowRight size={14} />
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ── Two-column: Actions + Sites ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ranked actions */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Priorites</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/actions')}>
              Tout voir <ArrowRight size={14} />
            </Button>
          </div>
          <div className="py-1 divide-y divide-gray-50">
            {topActions.length === 0 ? (
              <div className="px-5 py-8">
                <EmptyState icon={CheckCircle2} title="Aucune action en attente" text="Toutes les actions sont a jour." />
              </div>
            ) : (
              topActions.map((a, i) => (
                <ActionRow key={a.id} action={a} index={i} onClick={() => navigate(a.route)} />
              ))
            )}
          </div>
        </Card>

        {/* Sites at risk — table with accent on risk column */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Sites a traiter</h3>
            <Button variant="ghost" size="sm" onClick={() => navigate('/patrimoine')}>
              Patrimoine <ArrowRight size={14} />
            </Button>
          </div>
          {scopedSites.filter(s => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque').length === 0 ? (
            <div className="px-5 py-8">
              <EmptyState icon={CheckCircle2} title="Tous les sites sont conformes" text="Aucun site ne necessite d'intervention." />
            </div>
          ) : (
            <Table>
              <Thead>
                <tr>
                  <Th>Site</Th>
                  <Th>Statut</Th>
                  <Th className="text-right">Risque</Th>
                </tr>
              </Thead>
              <Tbody>
                {scopedSites
                  .filter(s => s.statut_conformite === 'non_conforme' || s.statut_conformite === 'a_risque')
                  .sort((a, b) => (b.risque_eur || 0) - (a.risque_eur || 0))
                  .slice(0, 8)
                  .map((site) => (
                    <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)} className="group cursor-pointer hover:bg-blue-50/40">
                      <Td>
                        <div className="font-medium text-gray-900">{site.nom}</div>
                        <div className="text-xs text-gray-400">{site.ville}</div>
                      </Td>
                      <Td>
                        <div className="flex items-center gap-1.5">
                          <StatusDot status={site.statut_conformite === 'non_conforme' ? 'crit' : 'warn'} />
                          <span className="text-xs text-gray-600">
                            {site.statut_conformite === 'non_conforme' ? 'Non conforme' : 'A risque'}
                          </span>
                        </div>
                      </Td>
                      <Td className="text-right text-sm font-medium">
                        {site.risque_eur > 0 ? (
                          <span className="text-amber-700">{site.risque_eur.toLocaleString('fr-FR')} EUR</span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </Td>
                    </Tr>
                  ))}
              </Tbody>
            </Table>
          )}
        </Card>
      </div>
    </PageShell>
  );
}
