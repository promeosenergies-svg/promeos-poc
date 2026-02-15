/**
 * PROMEOS - Command Center (/) V5 — Top Pages WOW
 * Neutral design, scope-aware KPIs, ranked actions, all states handled.
 */
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ArrowRight, Clock, Upload, Scan, RefreshCw,
  FileText, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import { Card, CardBody, Badge, Button, SkeletonCard, PageShell, MetricCard, StatusDot, EmptyState, ErrorState, Progress } from '../ui';
import { Table, Thead, Tbody, Th, Tr, Td } from '../ui';
import {
  getComplianceBundle, getActionsSummary, getActionsList,
  getNotificationsSummary,
} from '../services/api';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';

const PRIORITY_RANK = { critical: 4, high: 3, medium: 2, low: 1 };
const PRIORITY_STATUS = { critical: 'crit', high: 'warn', medium: 'info', low: 'neutral' };

function ActionRow({ action, index, onClick }) {
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
          <span className="text-xs font-medium text-gray-600">{action.impact_eur.toLocaleString()} EUR</span>
        )}
        <StatusDot status={PRIORITY_STATUS[action.priorite] || 'neutral'} />
        <ArrowRight size={14} className="text-gray-300" />
      </div>
    </button>
  );
}

function TodoRow({ item, onClick }) {
  return (
    <button
      type="button"
      className="flex items-center gap-3 w-full px-4 py-3 text-left rounded-lg
        hover:bg-gray-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      onClick={onClick}
    >
      <StatusDot status={PRIORITY_STATUS[item.priorite] || 'neutral'} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate">{item.texte}</p>
        <p className="text-xs text-gray-500 mt-0.5">{item.site}</p>
      </div>
      <div className="flex items-center gap-1.5 text-xs text-gray-400 whitespace-nowrap">
        <Clock size={12} />
        {item.echeance}
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

  // Real data states
  const [compliance, setCompliance] = useState(null);
  const [actionsSummary, setActionsSummary] = useState(null);
  const [actions, setActions] = useState([]);
  const [alertsSummary, setAlertsSummary] = useState(null);

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
    } catch {
      setError('Impossible de charger le tableau de bord');
    } finally {
      setLoading(false);
    }
  }, [org.id]);

  useEffect(() => { loadData(); }, [loadData]);

  // Derived KPIs from scope
  const kpis = useMemo(() => {
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

  // Top actions — merge compliance findings + action plan, rank by priority+impact
  const topActions = useMemo(() => {
    const items = [];

    // From compliance bundle
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

    // From actions list
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

  // Alerts count
  const alertsCount = useMemo(() => {
    if (!alertsSummary) return 0;
    return (alertsSummary.by_severity?.critical || 0) + (alertsSummary.by_severity?.warn || 0);
  }, [alertsSummary]);

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
        <>
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
        </>
      }
    >
      {/* North Star KPIs — neutral MetricCards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          label="Conformite"
          value={`${kpis.pctConf}%`}
          sub={`${kpis.conformes} / ${kpis.total} sites conformes`}
          status={kpis.compStatus}
          onClick={() => navigate('/conformite')}
        />
        <MetricCard
          label="Risque financier"
          value={kpis.risque > 0 ? `${(kpis.risque / 1000).toFixed(0)}k EUR` : '0 EUR'}
          sub={`${kpis.nonConformes + kpis.aRisque} sites a risque`}
          status={kpis.risqueStatus}
          onClick={() => navigate('/actions')}
        />
        <MetricCard
          label="Alertes actives"
          value={alertsCount}
          sub={alertsSummary ? `dont ${alertsSummary.by_severity?.critical || 0} critiques` : 'Chargement...'}
          status={alertsCount > 5 ? 'crit' : alertsCount > 0 ? 'warn' : 'ok'}
          onClick={() => navigate('/notifications')}
        />
      </div>

      {/* Priority #1 action card — neutral */}
      {topActions.length > 0 && (
        <Card>
          <CardBody>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <AlertTriangle size={20} className="text-gray-400 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs text-gray-500 font-medium uppercase">Action prioritaire</p>
                  <p className="text-sm font-semibold text-gray-900 mt-0.5 truncate">{topActions[0].titre}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{topActions[0].source_label}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {topActions[0].impact_eur > 0 && (
                  <span className="text-sm font-medium text-gray-700">{topActions[0].impact_eur.toLocaleString()} EUR</span>
                )}
                <Badge status={PRIORITY_STATUS[topActions[0].priorite] || 'neutral'}>{topActions[0].priorite}</Badge>
                <Button variant="secondary" size="sm" onClick={() => navigate(topActions[0].route)}>
                  Traiter <ArrowRight size={14} />
                </Button>
              </div>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Data coverage */}
      {isExpert && (
        <Card>
          <CardBody className="flex items-center gap-4">
            <div className="flex-1">
              <p className="text-xs text-gray-500 font-medium uppercase mb-2">Couverture donnees</p>
              <Progress
                value={kpis.total > 0 ? Math.round(scopedSites.filter(s => s.conso_kwh_an > 0).length / kpis.total * 100) : 0}
                color="gray"
                size="sm"
                label="Sites avec consommation renseignee"
              />
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-gray-900">
                {kpis.total > 0 ? Math.round(scopedSites.filter(s => s.conso_kwh_an > 0).length / kpis.total * 100) : 0}%
              </p>
              <p className="text-xs text-gray-400">
                {new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })}
              </p>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Two-column: Ranked actions + Quick alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ranked actions */}
        <Card>
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800">Actions recommandees</h3>
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

        {/* Sites at risk — compact list */}
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
                    <Tr key={site.id} onClick={() => navigate(`/sites/${site.id}`)} className="group">
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
                      <Td className="text-right text-sm font-medium text-gray-700">
                        {site.risque_eur > 0 ? `${site.risque_eur.toLocaleString()} EUR` : '-'}
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
